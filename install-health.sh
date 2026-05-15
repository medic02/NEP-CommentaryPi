#!/usr/bin/env bash
# NEP Health API – minimal installer (companion eller andre Pi-er uten failover)
# Bruk: curl -fsSL https://raw.githubusercontent.com/medic02/NEP-CommentaryPi/main/install-health.sh | bash

set -euo pipefail

GITHUB_RAW="https://raw.githubusercontent.com/medic02/NEP-CommentaryPi/main"

echo ""
echo "================================="
echo " NEP Health API Installer"
echo "================================="
echo ""

read_tty() {
    local varname="$1" prompt="$2" default="${3:-}" val=""
    if [ -t 0 ] && [ -z "${NEP_CHOICE:-}" ]; then
        read -r -p "$prompt" val
    elif [ -e /dev/tty ] && [ -z "${NEP_CHOICE:-}" ]; then
        read -r -p "$prompt" val </dev/tty
    else
        val="$default"
    fi
    printf -v "$varname" "%s" "$val"
}

NEP_ID="${NEP_ID:-}"
if [ -z "$NEP_ID" ]; then
    read_tty NEP_ID "Pi-navn (f.eks. Companion Pi): " "Companion Pi"
fi
NEP_ID="${NEP_ID:-Companion Pi}"

COMPANION_IP="${COMPANION_IP:-192.168.8.101}"
COMPANION_PORT="${COMPANION_PORT:-8000}"
LAN_DEV="${LAN_DEV:-eth0}"
TS_DEV="${TS_DEV:-tailscale0}"

echo ""
echo "Navn:      $NEP_ID"
echo "Companion: $COMPANION_IP:$COMPANION_PORT"
echo ""

# ── Pakker ────────────────────────────────────────────────────────────────────
echo "[1/3] Installerer pakker..."
sudo apt-get update -y -q
sudo apt-get install -y -q python3 python3-venv curl

# ── Health API ────────────────────────────────────────────────────────────────
echo "[2/3] Setter opp Health API..."
sudo systemctl stop nep-health.service 2>/dev/null || true

BASE="/home/pi/health"
mkdir -p "$BASE"
cd "$BASE"

rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install flask psutil -q
deactivate

curl -fsSL "$GITHUB_RAW/health/health.py" -o "$BASE/health.py"
curl -fsSL "$GITHUB_RAW/docs/index.html"  -o "$BASE/dashboard.html"
curl -fsSL "$GITHUB_RAW/assets/nep-logo.png" -o "$BASE/nep-logo.png" 2>/dev/null || true
chmod +x "$BASE/health.py"

sudo tee /etc/systemd/system/nep-health.service > /dev/null <<EOF
[Unit]
Description=NEP Health API
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=$BASE
Environment="NEP_ID=$NEP_ID"
Environment="COMPANION_IP=$COMPANION_IP"
Environment="COMPANION_PORT=$COMPANION_PORT"
Environment="LAN_DEV=$LAN_DEV"
Environment="TS_DEV=$TS_DEV"
ExecStart=$BASE/venv/bin/python $BASE/health.py
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

# ── Start ─────────────────────────────────────────────────────────────────────
echo "[3/3] Starter tjeneste..."
sudo systemctl daemon-reload
sudo systemctl enable --now nep-health.service

echo ""
echo "FERDIG ✅"
echo ""
echo "Health API: http://$(hostname -I | awk '{print $1}'):8080/health"
echo "Dashboard:  http://$(hostname -I | awk '{print $1}'):8080/"
echo ""
