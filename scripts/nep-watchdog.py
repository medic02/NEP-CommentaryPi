#!/usr/bin/env python3
# NEP Satellite Watchdog
# Overvåker alle Pi-er og sender Pushover-varsler ved disconnect/reconnect

import json, os, time, urllib.request, urllib.parse, subprocess
from datetime import datetime

DASHBOARD_CONFIG = "/home/pi/health/dashboard-config.json"
STATE_DIR        = "/run/nep-watchdog"
STATE_FILE       = f"{STATE_DIR}/state.json"
CHECK_INTERVAL   = int(os.environ.get("CHECK_INTERVAL", "30"))
PUSHOVER_TOKEN   = os.environ.get("PUSHOVER_TOKEN", "")
PUSHOVER_USER    = os.environ.get("PUSHOVER_USER", "")

def log(msg):
    subprocess.run(["logger", "-t", "nep-watchdog", msg], capture_output=True)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def send_pushover(title, message, priority=0):
    if not PUSHOVER_TOKEN or not PUSHOVER_USER:
        return
    try:
        data = urllib.parse.urlencode({
            "token":    PUSHOVER_TOKEN,
            "user":     PUSHOVER_USER,
            "title":    title,
            "message":  message,
            "priority": priority,
        }).encode()
        urllib.request.urlopen(
            urllib.request.Request("https://api.pushover.net/1/messages.json", data=data),
            timeout=10
        )
    except Exception as e:
        log(f"Pushover feil: {e}")

def load_config():
    try:
        with open(DASHBOARD_CONFIG) as f:
            return json.load(f)
    except Exception:
        return []

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

def save_state(state):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def check_pi(p):
    """Returnerer (online, satellite_connected) for en Pi."""
    for addr in [p.get("lan"), p.get("ts")]:
        if not addr:
            continue
        try:
            r = urllib.request.urlopen(f"http://{addr}/health", timeout=5)
            data = json.loads(r.read())
            sat = data.get("satellite_connected")
            return True, sat
        except Exception:
            pass
    return False, None

def check_device(p):
    ip = p.get("ip", "").split(":")[0]
    if not ip:
        return False
    try:
        r = subprocess.run(["ping", "-c", "1", "-W", "1", ip], capture_output=True, timeout=3)
        return r.returncode == 0
    except Exception:
        return False

def main():
    log("Watchdog startet")
    state = load_state()

    while True:
        devices = load_config()
        for p in devices:
            name  = p.get("name") or p.get("type", "Enhet")
            key   = json.dumps(p, sort_keys=True)
            ptype = p.get("type", "pi")

            if ptype in ("pi", ""):
                online, sat_conn = check_pi(p)
            else:
                online = check_device(p)
                sat_conn = None

            prev = state.get(key, {})
            if not isinstance(prev, dict):
                prev = {"online": prev, "sat": None}

            # Varsle ved online/offline-endring
            prev_online = prev.get("online")
            if prev_online is None:
                pass
            elif prev_online != online:
                if online:
                    log(f"{name}: ONLINE igjen")
                    send_pushover(f"✅ NEP – {name} online", f"{name} er tilbake online", priority=0)
                else:
                    log(f"{name}: OFFLINE")
                    send_pushover(f"🔴 NEP – {name} OFFLINE", f"{name} har mistet tilkobling", priority=1)

            # Varsle ved satellite disconnect (kun Pi-er)
            if ptype in ("pi", "") and online and sat_conn is not None:
                prev_sat = prev.get("sat")
                if prev_sat is True and sat_conn is False:
                    log(f"{name}: Satellite DISCONNECTED")
                    send_pushover(
                        f"⚠️ NEP – {name} satellite frakoblet",
                        f"{name} mistet satellite-tilkobling til companion",
                        priority=0
                    )
                elif prev_sat is False and sat_conn is True:
                    log(f"{name}: Satellite reconnected")
                    send_pushover(
                        f"✅ NEP – {name} satellite tilkoblet",
                        f"{name} er koblet til companion igjen",
                        priority=0
                    )

            state[key] = {"online": online, "sat": sat_conn}

        save_state(state)
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
