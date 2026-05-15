#!/usr/bin/env python3
# NEP Kommentatorkit – Health API
# Kjører på port 8080, eksponerer /health

from flask import Flask, jsonify, request, Response
import socket, time, subprocess, os, json
import psutil

APP_ID        = os.environ.get("NEP_ID", "Satellite Pi")
LAN_DEV       = os.environ.get("LAN_DEV", "eth0")
TS_DEV        = os.environ.get("TS_DEV", "tailscale0")
COMPANION_PORT= int(os.environ.get("COMPANION_PORT", "8000"))

FAILOVER_FLAG     = "/home/pi/.nep-ts-failover-disabled"
SATELLITE_CONFIG  = "/home/satellite/satellite-config.json"
CARD_CONFIG_FILE  = "/home/pi/health/card-config.json"

DEFAULT_CARD_CONFIG = {
    "logo_pct": 34,
    "font_size": 9,
    "line_spacing": 9,
    "text_x": 4,
    "text_y_offset": 10,
    "show_companion_ip": True,
    "show_conn_fo": True,
    "show_local_ip": True,
    "show_name": True,
}

def get_card_config():
    try:
        with open(CARD_CONFIG_FILE) as f:
            return {**DEFAULT_CARD_CONFIG, **json.load(f)}
    except Exception:
        return dict(DEFAULT_CARD_CONFIG)

def get_companion_ip():
    # Prøv world-readable kopi skrevet av failover-script (root)
    try:
        return open("/run/nep-ts-failover/companion_ip").read().strip()
    except Exception:
        pass
    return os.environ.get("COMPANION_IP", "192.168.8.101")

app = Flask(__name__)
START_TIME = int(time.time())

def sh(cmd, timeout=3):
    return subprocess.check_output(
        cmd, stderr=subprocess.DEVNULL, timeout=timeout
    ).decode(errors="ignore").strip()

def get_ip_addrs():
    ips = []
    for iface, addrs in psutil.net_if_addrs().items():
        for a in addrs:
            if a.family == socket.AF_INET and not a.address.startswith("127."):
                ips.append({"iface": iface, "ip": a.address})
    return ips

def get_cpu_temp_c():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return round(int(f.read().strip()) / 1000.0, 1)
    except Exception:
        pass
    try:
        out = sh(["vcgencmd", "measure_temp"], timeout=2)
        return float(out.split("=")[1].split("'")[0])
    except Exception:
        return None

def route_get(dst):
    try:
        return sh(["ip", "route", "get", dst], timeout=2)
    except Exception:
        return ""

def http_ok_via_lan(companion_ip=None):
    if companion_ip is None:
        companion_ip = get_companion_ip()
    try:
        sh([
            "curl", "-sS", "-m", "2", "--connect-timeout", "2",
            "--interface", LAN_DEV, "-o", "/dev/null",
            f"http://{companion_ip}:{COMPANION_PORT}/"
        ], timeout=3)
        return True
    except Exception:
        return False

def failover_state():
    """Les nåværende failover-tilstand fra state-filer."""
    state_dir = "/run/nep-ts-failover"
    try:
        fail  = int(open(f"{state_dir}/fail.count").read().strip() or 0)
    except Exception:
        fail = 0
    try:
        lanok = int(open(f"{state_dir}/lanok.count").read().strip() or 0)
    except Exception:
        lanok = 0
    return {"fail_count": fail, "lanok_count": lanok}

@app.route("/health")
def health():
    companion_ip = get_companion_ip()
    rg = route_get(companion_ip)
    using = "unknown"
    if f"dev {LAN_DEV}" in rg:
        using = "lan"
    elif f"dev {TS_DEV}" in rg:
        using = "tailscale"

    cpu = get_cpu_temp_c()
    lan_ok = http_ok_via_lan(companion_ip)

    return jsonify({
        "id":         APP_ID,
        "hostname":   socket.gethostname(),
        "ip_addrs":   get_ip_addrs(),
        "uptime_sec": int(time.time() - START_TIME),
        "cpu_temp_c": cpu,
        "companion": {
            "ip":       companion_ip,
            "port":     COMPANION_PORT,
            "route":    rg,
            "using":    using,
            "lan_ok":   lan_ok,
        },
        "failover":   failover_state(),
        "ts":         int(time.time())
    })

@app.route("/failover", methods=["GET", "POST"])
def failover_toggle():
    disabled = os.path.exists(FAILOVER_FLAG)
    if request.method == "POST":
        action = request.form.get("action", "")
        if action == "disable":
            open(FAILOVER_FLAG, "w").close()
            disabled = True
        elif action == "enable":
            try:
                os.remove(FAILOVER_FLAG)
            except FileNotFoundError:
                pass
            disabled = False

    status = "DEAKTIVERT" if disabled else "AKTIV"
    color  = "#ff4444" if disabled else "#00cc44"
    btn_action = "enable" if disabled else "disable"
    btn_label  = "Aktiver failover" if disabled else "Deaktiver failover"
    btn_color  = "#00cc44" if disabled else "#ff4444"

    companion_ip = get_companion_ip()
    html = f"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NEP Failover – {APP_ID}</title>
<style>
body{{font-family:system-ui,sans-serif;background:#0b0f14;color:#e6edf3;
     display:flex;flex-direction:column;align-items:center;padding:40px 20px}}
h1{{margin-bottom:4px}}
.sub{{color:#888;margin-bottom:32px}}
.status{{font-size:2em;font-weight:bold;color:{color};margin-bottom:32px}}
form button{{padding:14px 32px;font-size:1.1em;border:none;border-radius:8px;
             background:{btn_color};color:#fff;cursor:pointer}}
</style></head>
<body>
<h1>Tailscale Failover</h1>
<div class="sub">{APP_ID} · Companion {companion_ip}</div>
<div class="status">{status}</div>
<form method="POST">
  <input type="hidden" name="action" value="{btn_action}">
  <button type="submit">{btn_label}</button>
</form>
</body></html>"""
    return Response(html, mimetype="text/html")


@app.route("/settings", methods=["GET", "POST"])
def settings():
    cfg = get_card_config()
    saved = False
    if request.method == "POST":
        cfg = {
            "logo_pct":        max(10, min(70, int(request.form.get("logo_pct", 34)))),
            "font_size":       max(6,  min(20, int(request.form.get("font_size", 9)))),
            "line_spacing":    max(5,  min(18, int(request.form.get("line_spacing", 9)))),
            "text_x":          max(0,  min(30, int(request.form.get("text_x", 4)))),
            "text_y_offset":   max(2,  min(30, int(request.form.get("text_y_offset", 10)))),
            "show_companion_ip": "show_companion_ip" in request.form,
            "show_conn_fo":      "show_conn_fo"      in request.form,
            "show_local_ip":     "show_local_ip"     in request.form,
            "show_name":         "show_name"         in request.form,
        }
        with open(CARD_CONFIG_FILE, "w") as f:
            json.dump(cfg, f)
        os.chmod(CARD_CONFIG_FILE, 0o644)
        os.chmod("/home/pi/health", 0o755)
        os.chmod("/home/pi", 0o755)
        saved = True

    companion_ip = get_companion_ip()
    chk = lambda k: "checked" if cfg.get(k) else ""

    html = f"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NEP Kortinnstillinger – {APP_ID}</title>
<style>
*{{box-sizing:border-box}}
body{{font-family:system-ui,sans-serif;background:#0b0f14;color:#e6edf3;
     display:flex;flex-direction:column;align-items:center;padding:32px 16px;gap:0}}
h1{{margin-bottom:4px;font-size:1.4em}}
.sub{{color:#888;margin-bottom:24px;font-size:.9em}}
.saved{{color:#00cc44;margin-bottom:16px;font-weight:bold}}
form{{width:100%;max-width:420px;display:flex;flex-direction:column;gap:20px}}
.section{{background:#161b22;border-radius:10px;padding:16px;display:flex;flex-direction:column;gap:12px}}
.section h2{{font-size:.85em;text-transform:uppercase;color:#888;margin:0 0 4px}}
.row{{display:flex;align-items:center;justify-content:space-between;gap:12px}}
.row label{{font-size:.95em;flex:1}}
.row input[type=range]{{flex:2;accent-color:#4f9cf9}}
.val{{min-width:28px;text-align:right;color:#4f9cf9;font-size:.9em}}
.toggle{{display:flex;align-items:center;gap:10px;cursor:pointer;padding:4px 0}}
.toggle input{{width:18px;height:18px;accent-color:#4f9cf9;cursor:pointer}}
.toggle span{{font-size:.95em}}
button{{padding:14px;font-size:1em;border:none;border-radius:8px;
        background:#4f9cf9;color:#fff;cursor:pointer;font-weight:bold;margin-top:4px}}
button:active{{background:#357acc}}
.nav{{margin-top:20px;font-size:.85em;color:#888}}
.nav a{{color:#4f9cf9;text-decoration:none}}
</style></head>
<body>
<h1>Kortinnstillinger</h1>
<div class="sub">{APP_ID} · Companion {companion_ip}</div>
{"<div class='saved'>✓ Lagret – endringer vises innen få sekunder</div>" if saved else ""}
<form method="POST">
  <div class="section">
    <h2>Layout</h2>
    <div class="row">
      <label for="logo_pct">Logostørrelse</label>
      <input type="range" id="logo_pct" name="logo_pct" min="10" max="70" value="{cfg['logo_pct']}"
             oninput="this.nextElementSibling.textContent=this.value+'%'">
      <span class="val">{cfg['logo_pct']}%</span>
    </div>
    <div class="row">
      <label for="font_size">Skriftstørrelse</label>
      <input type="range" id="font_size" name="font_size" min="6" max="20" value="{cfg['font_size']}"
             oninput="this.nextElementSibling.textContent=this.value+'px'">
      <span class="val">{cfg['font_size']}px</span>
    </div>
    <div class="row">
      <label for="line_spacing">Linjeavstand</label>
      <input type="range" id="line_spacing" name="line_spacing" min="5" max="18" value="{cfg['line_spacing']}"
             oninput="this.nextElementSibling.textContent=this.value+'px'">
      <span class="val">{cfg['line_spacing']}px</span>
    </div>
    <div class="row">
      <label for="text_x">Tekst X (venstre)</label>
      <input type="range" id="text_x" name="text_x" min="0" max="30" value="{cfg.get('text_x', 4)}"
             oninput="this.nextElementSibling.textContent=this.value+'px'">
      <span class="val">{cfg.get('text_x', 4)}px</span>
    </div>
    <div class="row">
      <label for="text_y_offset">Tekst Y (fra logo)</label>
      <input type="range" id="text_y_offset" name="text_y_offset" min="2" max="30" value="{cfg.get('text_y_offset', 10)}"
             oninput="this.nextElementSibling.textContent=this.value+'px'">
      <span class="val">{cfg.get('text_y_offset', 10)}px</span>
    </div>
  </div>
  <div class="section">
    <h2>Vis info</h2>
    <label class="toggle"><input type="checkbox" name="show_companion_ip" {chk('show_companion_ip')}>
      <span>Companion IP (C:192.168.8.x)</span></label>
    <label class="toggle"><input type="checkbox" name="show_conn_fo" {chk('show_conn_fo')}>
      <span>Tilkobling &amp; failover (LAN FO:AKT)</span></label>
    <label class="toggle"><input type="checkbox" name="show_local_ip" {chk('show_local_ip')}>
      <span>Lokal IP (IP:192.168.8.x)</span></label>
    <label class="toggle"><input type="checkbox" name="show_name" {chk('show_name')}>
      <span>Pi-navn ({APP_ID})</span></label>
  </div>
  <button type="submit">Lagre</button>
</form>
<div class="nav"><a href="/failover">← Failover</a></div>
</body></html>"""
    return Response(html, mimetype="text/html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
