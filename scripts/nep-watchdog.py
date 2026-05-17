#!/usr/bin/env python3
# NEP Satellite Watchdog
# Overvåker alle Pi-er og sender Pushover-varsler ved disconnect/reconnect

import json, os, time, urllib.request, urllib.parse, subprocess
from datetime import datetime

DASHBOARD_CONFIG  = "/home/pi/health/dashboard-config.json"
NOTIF_CONFIG_FILE = "/home/pi/health/notifications-config.json"
STATE_DIR         = "/tmp/nep-watchdog"
STATE_FILE        = f"{STATE_DIR}/state.json"
CHECK_INTERVAL    = int(os.environ.get("CHECK_INTERVAL", "30"))

# Env vars brukes som fallback hvis config-fil mangler credentials
PUSHOVER_TOKEN    = os.environ.get("PUSHOVER_TOKEN", "")
PUSHOVER_USER     = os.environ.get("PUSHOVER_USER",  "")

DEFAULT_NOTIF_CONFIG = {
    "pushover_token": "",
    "pushover_user":  "",
    "enabled": True,
    "alerts": {
        "pi_offline":            True,
        "pi_online":             True,
        "satellite_disconnect":  True,
        "satellite_reconnect":   True,
        "high_temp":             True,
        "failover_to_ts":        True,
        "failover_to_lan":       False,
    },
    "temp_warn": 75,
    "temp_ok":   65,
}

def log(msg):
    subprocess.run(["logger", "-t", "nep-watchdog", msg], capture_output=True)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def get_notif_config():
    try:
        with open(NOTIF_CONFIG_FILE) as f:
            cfg = json.load(f)
        # Fyll inn defaults for manglende felter
        for k, v in DEFAULT_NOTIF_CONFIG.items():
            cfg.setdefault(k, v)
        for k, v in DEFAULT_NOTIF_CONFIG["alerts"].items():
            cfg["alerts"].setdefault(k, v)
        # Fallback til env vars hvis credentials mangler
        if not cfg.get("pushover_token"):
            cfg["pushover_token"] = PUSHOVER_TOKEN
        if not cfg.get("pushover_user"):
            cfg["pushover_user"] = PUSHOVER_USER
        return cfg
    except Exception:
        return {**DEFAULT_NOTIF_CONFIG,
                "pushover_token": PUSHOVER_TOKEN,
                "pushover_user":  PUSHOVER_USER}

def send_pushover(title, message, priority=0, cfg=None):
    if cfg is None:
        cfg = get_notif_config()
    if not cfg.get("enabled", True):
        return
    token = cfg.get("pushover_token", "")
    user  = cfg.get("pushover_user",  "")
    if not token or not user:
        return
    try:
        data = urllib.parse.urlencode({
            "token":    token,
            "user":     user,
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
    """Returnerer (online, satellite_connected, cpu_temp_c, using_ts) for en Pi."""
    for addr in [p.get("lan"), p.get("ts")]:
        if not addr:
            continue
        try:
            r = urllib.request.urlopen(f"http://{addr}/health", timeout=5)
            data = json.loads(r.read())
            sat      = data.get("satellite_connected")
            temp     = data.get("cpu_temp_c")
            using    = data.get("companion", {}).get("using", "")
            ts_active = using == "tailscale"
            return True, sat, temp, ts_active
        except Exception:
            pass
    return False, None, None, None

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
        notif      = get_notif_config()
        alerts     = notif.get("alerts", {})
        temp_warn  = int(notif.get("temp_warn", 75))
        temp_ok    = int(notif.get("temp_ok",   65))

        devices = load_config()
        for p in devices:
            name  = p.get("name") or p.get("type", "Enhet")
            key   = json.dumps(p, sort_keys=True)
            ptype = p.get("type", "pi")

            if ptype in ("pi", ""):
                online, sat_conn, temp, ts_active = check_pi(p)
            else:
                online    = check_device(p)
                sat_conn  = None
                temp      = None
                ts_active = None

            prev = state.get(key, {})
            if not isinstance(prev, dict):
                prev = {}

            prev_online    = prev.get("online")
            prev_sat       = prev.get("sat")
            prev_hot       = prev.get("hot", False)
            prev_ts_active = prev.get("ts_active")

            # ── Pi offline / online ──────────────────────────────────────────
            if prev_online is not None and prev_online != online:
                if online:
                    log(f"{name}: ONLINE igjen")
                    if alerts.get("pi_online", True):
                        send_pushover(f"✅ NEP – {name} online",
                                      f"{name} er tilbake online", cfg=notif)
                else:
                    log(f"{name}: OFFLINE")
                    if alerts.get("pi_offline", True):
                        send_pushover(f"🔴 NEP – {name} OFFLINE",
                                      f"{name} har mistet tilkobling",
                                      priority=1, cfg=notif)

            # ── Satellite disconnect / reconnect ─────────────────────────────
            if ptype in ("pi", "") and online and sat_conn is not None:
                if prev_sat is True and sat_conn is False:
                    log(f"{name}: Satellite DISCONNECTED")
                    if alerts.get("satellite_disconnect", True):
                        send_pushover(f"⚠️ NEP – {name} satellite frakoblet",
                                      f"{name} mistet satellite-tilkobling til companion",
                                      cfg=notif)
                elif prev_sat is False and sat_conn is True:
                    log(f"{name}: Satellite reconnected")
                    if alerts.get("satellite_reconnect", True):
                        send_pushover(f"✅ NEP – {name} satellite tilkoblet",
                                      f"{name} er koblet til companion igjen",
                                      cfg=notif)

            # ── Høy temperatur ───────────────────────────────────────────────
            if ptype in ("pi", "") and online and temp is not None:
                if not prev_hot and temp >= temp_warn:
                    log(f"{name}: HØYTEMP {temp}°C")
                    if alerts.get("high_temp", True):
                        send_pushover(f"🌡️ NEP – {name} høy temp",
                                      f"{name} er {temp}°C (grense: {temp_warn}°C)",
                                      priority=1, cfg=notif)
                elif prev_hot and temp < temp_ok:
                    log(f"{name}: Temp normal igjen {temp}°C")
                    if alerts.get("high_temp", True):
                        send_pushover(f"✅ NEP – {name} temp normal",
                                      f"{name} er nede på {temp}°C",
                                      cfg=notif)

            # ── Failover: LAN → Tailscale / Tailscale → LAN ─────────────────
            if ptype in ("pi", "") and online and ts_active is not None:
                if prev_ts_active is False and ts_active is True:
                    log(f"{name}: Byttet til Tailscale")
                    if alerts.get("failover_to_ts", True):
                        send_pushover(f"⚡ NEP – {name} bruker Tailscale",
                                      f"{name} mistet LAN og kjører via VPN",
                                      cfg=notif)
                elif prev_ts_active is True and ts_active is False:
                    log(f"{name}: Tilbake på LAN")
                    if alerts.get("failover_to_lan", False):
                        send_pushover(f"✅ NEP – {name} tilbake på LAN",
                                      f"{name} er tilkoblet via LAN igjen",
                                      cfg=notif)

            state[key] = {
                "online":    online,
                "sat":       sat_conn,
                "hot":       (temp >= temp_warn) if temp is not None else prev_hot,
                "ts_active": ts_active if ts_active is not None else prev_ts_active,
            }

        save_state(state)
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
