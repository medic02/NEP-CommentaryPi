#!/usr/bin/env python3
# NEP Kommentatorkit – Health API
# Kjører på port 8080, eksponerer /health

from flask import Flask, jsonify, request, Response
import socket, time, subprocess, os
import psutil

APP_ID        = os.environ.get("NEP_ID", "Satellite Pi")
LAN_DEV       = os.environ.get("LAN_DEV", "eth0")
TS_DEV        = os.environ.get("TS_DEV", "tailscale0")
COMPANION_PORT= int(os.environ.get("COMPANION_PORT", "8000"))

FAILOVER_FLAG     = "/home/pi/.nep-ts-failover-disabled"
SATELLITE_CONFIG  = "/home/satellite/satellite-config.json"

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
