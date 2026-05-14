#!/usr/bin/env python3
# NEP Kommentatorkit – Health API
# Kjører på port 8080, eksponerer /health

from flask import Flask, jsonify
import socket, time, subprocess, os
import psutil

APP_ID        = os.environ.get("NEP_ID", "Satellite Pi")
COMPANION_IP  = os.environ.get("COMPANION_IP", "192.168.8.101")
COMPANION_PORT= int(os.environ.get("COMPANION_PORT", "8000"))
LAN_DEV       = os.environ.get("LAN_DEV", "eth0")
TS_DEV        = os.environ.get("TS_DEV", "tailscale0")

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

def http_ok_via_lan():
    try:
        sh([
            "curl", "-sS", "-m", "2", "--connect-timeout", "2",
            "--interface", LAN_DEV, "-o", "/dev/null",
            f"http://{COMPANION_IP}:{COMPANION_PORT}/"
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
    rg = route_get(COMPANION_IP)
    using = "unknown"
    if f"dev {LAN_DEV}" in rg:
        using = "lan"
    elif f"dev {TS_DEV}" in rg:
        using = "tailscale"

    cpu = get_cpu_temp_c()
    lan_ok = http_ok_via_lan()

    return jsonify({
        "id":         APP_ID,
        "hostname":   socket.gethostname(),
        "ip_addrs":   get_ip_addrs(),
        "uptime_sec": int(time.time() - START_TIME),
        "cpu_temp_c": cpu,
        "companion": {
            "ip":       COMPANION_IP,
            "port":     COMPANION_PORT,
            "route":    rg,
            "using":    using,
            "lan_ok":   lan_ok,
        },
        "failover":   failover_state(),
        "ts":         int(time.time())
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
