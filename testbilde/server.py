#!/usr/bin/env python3
import glob
import json
import os
import queue
import re
import subprocess
import threading
import time
from flask import Flask, request, jsonify, Response, send_from_directory, render_template

BASE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE, "state.json")
PRESETS_FILE = os.path.join(BASE, "presets.json")
UPLOAD_DIR = os.path.join(BASE, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Keys left out of a saved preset -- the physical output mode is a property
# of the rig/converter, not of the design, so loading a preset must never
# silently flip the signal format.
PRESET_EXCLUDE_KEYS = {"format"}

# Real output modes this HDMI->SDI converter actually advertises
# (from `xrandr --query` on the connected output). Selecting a format
# must change the physical signal (interlace/progressive, Hz), not just
# the canvas's pixel size -- the canvas size follows from the mode here.
FORMATS = {
    "1080i60": {"mode": "1920x1080i", "rate": "59.94", "w": 1920, "h": 1080},
    "1080i50": {"mode": "1920x1080i", "rate": "50.00", "w": 1920, "h": 1080},
    "1080p60": {"mode": "1920x1080",  "rate": "59.94", "w": 1920, "h": 1080},
    "1080p50": {"mode": "1920x1080",  "rate": "50.00", "w": 1920, "h": 1080},
    "720p60":  {"mode": "1280x720",   "rate": "59.94", "w": 1280, "h": 720},
    "720p50":  {"mode": "1280x720",   "rate": "50.00", "w": 1280, "h": 720},
    "576i50":  {"mode": "720x576i",   "rate": "50.00", "w": 720,  "h": 576},
    "576p50":  {"mode": "720x576",    "rate": "50.00", "w": 720,  "h": 576},
}

DEFAULT_STATE = {
    "mode": "bars",
    "format": "1080i60",
    "barsPattern": "smpte",
    "textOn": True,
    "dato": "Sesong 2026",
    "arena": "NEP Kommentatorkit",
    "ekstra": "Testbilde",
    "logoCount": 1,
    "bg": "pitch",
    "solidColor": "#0d3b1e",
    "speed": 4,
    "logoSizePct": 12,
    "logoA": None,
    "logoB": None,
    "screensaver": "dvd",
    "screensaverLogo": None,
    "customBg": "#14171c",
    "customBase": "solid",
    "customElements": [],
    "clockOn": False,
    "clockX": 50,
    "clockY": 88,
    "clockSize": 4,
    "clockColor": "#ffffff",
    "countdownOn": False,
    "countdownTarget": "",
    "countdownLabel": "Tid til kickoff",
    "countdownX": 50,
    "countdownY": 94,
    "countdownLabelSize": 2.5,
    "countdownSize": 3,
    "countdownColor": "#ff9c1a",
}

lock = threading.Lock()
subscribers = []


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                s = json.load(f)
            merged = dict(DEFAULT_STATE)
            merged.update(s)
            if merged.get("format") not in FORMATS:
                merged["format"] = DEFAULT_STATE["format"]
            return merged
        except Exception:
            pass
    return dict(DEFAULT_STATE)


def find_xauth():
    matches = glob.glob("/tmp/serverauth.*")
    return matches[0] if matches else None


def find_output(env):
    try:
        out = subprocess.check_output(["xrandr", "--query"], env=env, timeout=5).decode()
        for line in out.splitlines():
            if " connected" in line:
                return line.split()[0]
    except Exception:
        pass
    return None


def apply_output_mode(format_key):
    f = FORMATS.get(format_key)
    if not f:
        return False, "unknown format"
    xauth = find_xauth()
    if not xauth:
        return False, "no X session found"
    env = dict(os.environ, DISPLAY=":0", XAUTHORITY=xauth)
    output = find_output(env)
    if not output:
        return False, "no connected output found"
    try:
        subprocess.check_call(
            ["xrandr", "--output", output, "--mode", f["mode"], "--rate", f["rate"]],
            env=env, timeout=5,
        )
        return True, f"{output} -> {f['mode']} @ {f['rate']}"
    except Exception as e:
        return False, str(e)


def apply_saved_format_with_retry():
    for _ in range(15):
        ok, msg = apply_output_mode(STATE.get("format"))
        if ok:
            return
        time.sleep(2)


def save_state(s):
    with open(STATE_FILE, "w") as f:
        json.dump(s, f)


def load_presets():
    if os.path.exists(PRESETS_FILE):
        try:
            with open(PRESETS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_presets(p):
    with open(PRESETS_FILE, "w") as f:
        json.dump(p, f)


STATE = load_state()
PRESETS = load_presets()
presets_lock = threading.Lock()

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True

threading.Thread(target=apply_saved_format_with_retry, daemon=True).start()


def broadcast():
    data = f"data: {json.dumps(STATE)}\n\n"
    dead = []
    for q in subscribers:
        try:
            q.put_nowait(data)
        except Exception:
            dead.append(q)
    for q in dead:
        if q in subscribers:
            subscribers.remove(q)


@app.route("/")
def admin():
    return render_template("admin.html")


@app.route("/display")
def display():
    return render_template("display.html")


@app.route("/api/state", methods=["GET"])
def get_state():
    with lock:
        return jsonify(STATE)


def apply_state_update(body):
    with lock:
        old_format = STATE.get("format")
        STATE.update(body)
        save_state(STATE)
        broadcast()
    xrandr_result = None
    if "format" in body and body["format"] != old_format:
        ok, msg = apply_output_mode(body["format"])
        xrandr_result = {"ok": ok, "msg": msg}
    resp = dict(STATE)
    resp["_xrandr"] = xrandr_result
    return resp


@app.route("/api/state", methods=["POST"])
def post_state():
    body = request.get_json(force=True, silent=True) or {}
    return jsonify(apply_state_update(body))


def parse_deck_value(raw):
    if raw is None:
        return None
    low = raw.strip().lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if low in ("null", "none"):
        return None
    if re.match(r"^-?\d+$", raw):
        return int(raw)
    if re.match(r"^-?\d+\.\d+$", raw):
        return float(raw)
    return raw


@app.route("/api/deck")
def deck_help():
    return jsonify({
        "info": "GET-only endpoints meant for Stream Deck / Companion HTTP buttons -- no JSON body needed.",
        "set": "/api/deck/set?key=<state-key>&value=<value> -- set any single field on the testbilde page. "
               "value is auto-typed (true/false -> bool, digits -> number, else text). "
               "Encode '#' in colors as %23.",
        "toggle": "/api/deck/toggle?key=<boolean-key> -- flip a true/false field (textOn, clockOn, countdownOn).",
        "preset": "/api/deck/preset?name=<saved design name> -- load a design saved under 'Mine design'.",
        "screensaver_logo": "/api/deck/screensaver-logo?name=<sslogo_... filename, or 'default'> -- activate a "
                             "saved screensaver logo, or reset to the NEP logo.",
        "state": "/api/deck/state -- read full current state as JSON (for Companion feedback/variables).",
        "examples": [
            "/api/deck/set?key=mode&value=bars",
            "/api/deck/set?key=mode&value=bounce",
            "/api/deck/set?key=mode&value=screensaver",
            "/api/deck/set?key=screensaver&value=matrix",
            "/api/deck/set?key=format&value=1080i50",
            "/api/deck/set?key=barsPattern&value=custom",
            "/api/deck/set?key=countdownColor&value=%23ff9c1a",
            "/api/deck/toggle?key=clockOn",
            "/api/deck/preset?name=Derby%20hjemme",
            "/api/deck/screensaver-logo?name=default",
        ],
        "modes": ["bars", "bounce", "screensaver"],
        "formats": list(FORMATS.keys()),
        "barsPatterns": ["smpte", "full", "ramp", "custom"],
        "screensavers": ["dvd", "matrix", "pong", "pulse", "starfield", "time", "toasters"],
        "savedDesigns": sorted(PRESETS.keys()),
        "savedScreensaverLogos": list_screensaver_logos(),
    })


@app.route("/api/deck/set")
def deck_set():
    key = request.args.get("key")
    if not key:
        return jsonify({"error": "missing key"}), 400
    value = parse_deck_value(request.args.get("value"))
    return jsonify(apply_state_update({key: value}))


@app.route("/api/deck/toggle")
def deck_toggle():
    key = request.args.get("key")
    if not key:
        return jsonify({"error": "missing key"}), 400
    with lock:
        STATE[key] = not bool(STATE.get(key))
        save_state(STATE)
        broadcast()
        resp = dict(STATE)
    return jsonify(resp)


@app.route("/api/deck/preset")
def deck_preset():
    name = request.args.get("name")
    if not name:
        return jsonify({"error": "missing name"}), 400
    return load_preset(name)


@app.route("/api/deck/screensaver-logo")
def deck_screensaver_logo():
    name = request.args.get("name", "")
    if not name or name.lower() in ("default", "none", "nep"):
        return jsonify(apply_state_update({"screensaverLogo": None}))
    return activate_screensaver_logo(name)


@app.route("/api/deck/state")
def deck_state():
    return get_state()


@app.route("/api/formats")
def formats():
    return jsonify(list(FORMATS.keys()))


@app.route("/api/presets", methods=["GET"])
def list_presets():
    with presets_lock:
        return jsonify(sorted(PRESETS.keys()))


@app.route("/api/presets/<name>", methods=["PUT"])
def save_preset(name):
    name = name.strip()
    if not name:
        return jsonify({"error": "empty name"}), 400
    with lock:
        snapshot = {k: v for k, v in STATE.items() if k not in PRESET_EXCLUDE_KEYS}
    with presets_lock:
        PRESETS[name] = snapshot
        save_presets(PRESETS)
    return jsonify({"ok": True, "names": sorted(PRESETS.keys())})


@app.route("/api/presets/<name>/load", methods=["POST"])
def load_preset(name):
    with presets_lock:
        preset = PRESETS.get(name)
    if preset is None:
        return jsonify({"error": "not found"}), 404
    with lock:
        STATE.update(preset)
        save_state(STATE)
        broadcast()
        resp = dict(STATE)
    return jsonify(resp)


@app.route("/api/presets/<name>", methods=["DELETE"])
def delete_preset(name):
    with presets_lock:
        existed = name in PRESETS
        if existed:
            del PRESETS[name]
            save_presets(PRESETS)
    return jsonify({"ok": True, "names": sorted(PRESETS.keys())})


@app.route("/api/telemetry", methods=["POST"])
def telemetry():
    t = request.get_json(force=True, silent=True) or {}
    print(f"TELEMETRY fmt={t.get('format')} interlace={t.get('interlace')} "
          f"n={t.get('n')} avg={t.get('avg')}ms min={t.get('min')}ms "
          f"max={t.get('max')}ms stddev={t.get('stddev')}ms over33ms={t.get('over33ms')} "
          f"| physics={t.get('physics_ms')}ms bgcache={t.get('bgcache_ms')}ms sprites={t.get('sprites_ms')}ms",
          flush=True)
    return jsonify({"ok": True})


@app.route("/api/upload/<which>", methods=["POST"])
def upload(which):
    if which not in ("A", "B"):
        return jsonify({"error": "invalid slot"}), 400
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "no file"}), 400
    ext = os.path.splitext(f.filename)[1].lower() or ".png"
    if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"):
        ext = ".png"
    fname = f"logo{which}{ext}"
    f.save(os.path.join(UPLOAD_DIR, fname))
    url = f"/uploads/{fname}"
    with lock:
        STATE[f"logo{which}"] = url
        save_state(STATE)
        broadcast()
    return jsonify({"url": url})


@app.route("/api/upload-custom/<elid>", methods=["POST"])
def upload_custom(elid):
    import re
    if not re.match(r"^[a-zA-Z0-9_-]+$", elid):
        return jsonify({"error": "invalid id"}), 400
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "no file"}), 400
    ext = os.path.splitext(f.filename)[1].lower() or ".png"
    if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"):
        ext = ".png"
    fname = f"custom_{elid}{ext}"
    f.save(os.path.join(UPLOAD_DIR, fname))
    url = f"/uploads/{fname}"
    return jsonify({"url": url})


@app.route("/uploads/<path:fname>")
def uploads(fname):
    return send_from_directory(UPLOAD_DIR, fname)


SSLOGO_PREFIX = "sslogo_"


def list_screensaver_logos():
    files = sorted(glob.glob(os.path.join(UPLOAD_DIR, SSLOGO_PREFIX + "*")))
    return [os.path.basename(f) for f in files]


@app.route("/api/screensaver-logos", methods=["GET"])
def get_screensaver_logos():
    with lock:
        active = STATE.get("screensaverLogo")
    return jsonify({"files": list_screensaver_logos(), "active": active})


@app.route("/api/screensaver-logos", methods=["POST"])
def upload_screensaver_logo():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "no file"}), 400
    base = os.path.splitext(os.path.basename(f.filename))[0]
    base = re.sub(r"[^a-zA-Z0-9_-]+", "-", base).strip("-") or "logo"
    ext = os.path.splitext(f.filename)[1].lower() or ".png"
    if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"):
        ext = ".png"
    fname = f"{SSLOGO_PREFIX}{base}{ext}"
    i = 2
    while os.path.exists(os.path.join(UPLOAD_DIR, fname)):
        fname = f"{SSLOGO_PREFIX}{base}-{i}{ext}"
        i += 1
    f.save(os.path.join(UPLOAD_DIR, fname))
    url = f"/uploads/{fname}"
    with lock:
        STATE["screensaverLogo"] = url
        save_state(STATE)
        broadcast()
    return jsonify({"url": url, "files": list_screensaver_logos(), "active": url})


@app.route("/api/screensaver-logos/<fname>/activate", methods=["POST"])
def activate_screensaver_logo(fname):
    if not re.match(r"^[a-zA-Z0-9_.-]+$", fname) or not fname.startswith(SSLOGO_PREFIX):
        return jsonify({"error": "invalid name"}), 400
    if not os.path.exists(os.path.join(UPLOAD_DIR, fname)):
        return jsonify({"error": "not found"}), 404
    url = f"/uploads/{fname}"
    with lock:
        STATE["screensaverLogo"] = url
        save_state(STATE)
        broadcast()
    return jsonify({"files": list_screensaver_logos(), "active": url})


@app.route("/api/screensaver-logos/<fname>", methods=["DELETE"])
def delete_screensaver_logo(fname):
    if not re.match(r"^[a-zA-Z0-9_.-]+$", fname) or not fname.startswith(SSLOGO_PREFIX):
        return jsonify({"error": "invalid name"}), 400
    path = os.path.join(UPLOAD_DIR, fname)
    if os.path.exists(path):
        os.remove(path)
    with lock:
        if STATE.get("screensaverLogo") == f"/uploads/{fname}":
            STATE["screensaverLogo"] = None
            save_state(STATE)
            broadcast()
        active = STATE.get("screensaverLogo")
    return jsonify({"files": list_screensaver_logos(), "active": active})


SCREENSAVER_DIR = os.path.join(BASE, "screensavers")

# Screensavers that load the NEP logo as an <img> (not drawn as text/shapes).
# The logo library only ever rewrites the reference *inside these specific
# pages* -- the shared static file at NEP-Logo-FC-WHITE-RGB.png is left
# completely untouched, since the bars custom editor's "NEP mal" preset (and
# any design saved from it) also points at that same static URL and must
# never be affected by a screensaver-only logo swap.
SCREENSAVER_LOGO_FILENAME = "NEP-Logo-FC-WHITE-RGB.png"
SCREENSAVERS_WITH_LOGO = {"dvd.html", "pulse.html", "toasters.html", "starfield.html"}


@app.route("/screensavers/<path:fname>")
def screensavers(fname):
    if fname in SCREENSAVERS_WITH_LOGO:
        custom = STATE.get("screensaverLogo")
        if custom:
            custom_fname = os.path.basename(custom)
            if os.path.exists(os.path.join(UPLOAD_DIR, custom_fname)):
                path = os.path.join(SCREENSAVER_DIR, fname)
                with open(path, "r", encoding="utf-8") as fh:
                    html = fh.read()
                html = html.replace("./" + SCREENSAVER_LOGO_FILENAME, custom)
                resp = Response(html, mimetype="text/html")
                resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                return resp
    return send_from_directory(SCREENSAVER_DIR, fname)


@app.route("/api/stream")
def stream():
    def gen():
        q = queue.Queue()
        subscribers.append(q)
        try:
            with lock:
                yield f"data: {json.dumps(STATE)}\n\n"
            while True:
                try:
                    data = q.get(timeout=15)
                    yield data
                except queue.Empty:
                    yield ": keepalive\n\n"
        finally:
            if q in subscribers:
                subscribers.remove(q)

    return Response(gen(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    })


def _needs_clock_tick():
    if STATE.get("mode") != "bars":
        return False
    if STATE.get("barsPattern") == "custom":
        return any(e.get("type") in ("clock", "countdown") for e in STATE.get("customElements", []))
    return bool(STATE.get("clockOn")) or bool(STATE.get("countdownOn"))


def clock_ticker():
    # Re-broadcasts current STATE once a second so any clock/countdown
    # element redraws with a fresh timestamp via the already-working
    # SSE -> applyState -> renderBars path, instead of relying on a
    # separate client-side timer.
    while True:
        time.sleep(1)
        with lock:
            if _needs_clock_tick():
                broadcast()


threading.Thread(target=clock_ticker, daemon=True).start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, threaded=True)
