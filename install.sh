#!/usr/bin/env bash
# NEP Kommentatorkit – Satellite Pi installer
# Bruk: curl -fsSL https://raw.githubusercontent.com/medic02/NEP-CommentaryPi/main/install.sh | bash

set -euo pipefail

GITHUB_RAW="https://raw.githubusercontent.com/medic02/NEP-CommentaryPi/main"

echo ""
echo "================================="
echo " NEP Satellite Pi Installer"
echo "================================="
echo ""

# ── Velg Pi-ID ────────────────────────────────────────────────────────────────
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

echo "Velg hvilken Pi dette er:"
echo "1) Satellite Pi 1"
echo "2) Satellite Pi 2"
echo "3) Satellite Pi 3"
echo "4) Satellite Pi 4"
echo "5) Satellite Pi 5"
echo "6) Satellite Pi 6"
echo "7) Custom"
echo ""

choice="${NEP_CHOICE:-}"
if [ -z "${choice:-}" ]; then
    read_tty choice "> " ""
fi

NEP_ID="Satellite Pi"
case "${choice:-}" in
    1) NEP_ID="Satellite Pi 1" ;;
    2) NEP_ID="Satellite Pi 2" ;;
    3) NEP_ID="Satellite Pi 3" ;;
    4) NEP_ID="Satellite Pi 4" ;;
    5) NEP_ID="Satellite Pi 5" ;;
    6) NEP_ID="Satellite Pi 6" ;;
    7)
        custom=""
        read_tty custom "Skriv navn: " "Satellite Pi"
        NEP_ID="${custom:-Satellite Pi}"
        ;;
    *) NEP_ID="Satellite Pi" ;;
esac

COMPANION_IP="${COMPANION_IP:-192.168.8.101}"
COMPANION_PORT="${COMPANION_PORT:-8000}"
LAN_DEV="${LAN_DEV:-eth0}"
TS_DEV="${TS_DEV:-tailscale0}"

echo ""
echo "Device ID:   $NEP_ID"
echo "Companion:   $COMPANION_IP:$COMPANION_PORT"
echo "LAN:         $LAN_DEV"
echo "Tailscale:   $TS_DEV"
echo ""

# ── [1/7] Pakker ──────────────────────────────────────────────────────────────
echo "[1/7] Installerer pakker..."
sudo apt-get update -y -q
sudo apt-get install -y -q python3 python3-venv curl iproute2 conntrack util-linux

# ── [2/7] Health API ──────────────────────────────────────────────────────────
echo "[2/7] Setter opp Health API..."
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
Environment=NEP_ID=$NEP_ID
Environment=COMPANION_IP=$COMPANION_IP
Environment=COMPANION_PORT=$COMPANION_PORT
Environment=LAN_DEV=$LAN_DEV
Environment=TS_DEV=$TS_DEV
ExecStart=$BASE/venv/bin/python $BASE/health.py
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

# ── [3/7] Failover script ─────────────────────────────────────────────────────
echo "[3/7] Installerer failover script..."
curl -fsSL "$GITHUB_RAW/scripts/nep-ts-failover.sh" -o /tmp/nep-ts-failover.sh
sudo install -m 755 /tmp/nep-ts-failover.sh /usr/local/sbin/nep-ts-failover.sh

# ── [4/7] Systemd services ────────────────────────────────────────────────────
echo "[4/7] Setter opp systemd services..."

sudo tee /etc/systemd/system/nep-iprule.service > /dev/null <<EOF
[Unit]
Description=NEP LAN priority routing rule
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'ip rule add to 192.168.8.0/24 lookup main priority 50 2>/dev/null || true'
ExecStartPost=/bin/bash -c 'ip route flush cache || true'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/nep-ts-failover.service > /dev/null <<EOF
[Unit]
Description=NEP LAN->Tailscale failover
After=network-online.target tailscaled.service
Wants=network-online.target

[Service]
Type=oneshot
Environment=COMPANION_LAN_IP=$COMPANION_IP
Environment=COMPANION_PORT=$COMPANION_PORT
Environment=LAN_DEV=$LAN_DEV
Environment=TS_DEV=$TS_DEV
ExecStart=/usr/local/sbin/nep-ts-failover.sh
EOF

sudo tee /etc/systemd/system/nep-ts-failover.timer > /dev/null <<EOF
[Unit]
Description=Run NEP failover check

[Timer]
OnBootSec=15s
OnUnitActiveSec=5s
AccuracySec=1s

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now nep-iprule.service
sudo systemctl enable --now nep-health.service
sudo systemctl enable --now nep-ts-failover.timer

# ── [5/7] Tailscale ───────────────────────────────────────────────────────────
echo "[5/7] Tailscale..."
if ! command -v tailscale >/dev/null 2>&1; then
    echo "  Installerer Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh
else
    echo "  Tailscale allerede installert."
fi
sudo tailscale set --accept-routes=true --accept-dns=false 2>/dev/null || true

# ── [6/7] NEP logo + cards.js ────────────────────────────────────────────────
echo "[6/7] Installerer NEP logo og cards.js..."

ASSETS_DIR="/opt/companion-satellite/satellite/assets"
CARDS_FILE="/opt/companion-satellite/satellite/dist/graphics/cards.js"

if [ -d "$ASSETS_DIR" ]; then
    sudo curl -fsSL "$GITHUB_RAW/assets/nep-logo.png" -o "$ASSETS_DIR/icon.png"
    echo "  Logo installert."
else
    echo "  ADVARSEL: $ASSETS_DIR ikke funnet – hopper over logo."
fi

if [ -f "$CARDS_FILE" ]; then
    sudo cp -a "$CARDS_FILE" "${CARDS_FILE}.bak.$(date +%s)" 2>/dev/null || true
    sudo curl -fsSL "$GITHUB_RAW/scripts/cards.js" -o "$CARDS_FILE"
    echo "  cards.js installert."
else
    echo "  ADVARSEL: $CARDS_FILE ikke funnet – hopper over cards.js."
fi

sudo systemctl restart satellite 2>/dev/null || true

# ── [7/7] Ferdig ─────────────────────────────────────────────────────────────
echo ""
echo "[7/7] FERDIG ✅"
echo ""
echo "Health API:      http://$(hostname -I | awk '{print $1}'):8080/health"
echo "Failover logg:   journalctl -t nep-ts-failover -f"
echo ""
echo "VIKTIG – første gang: koble til Tailscale:"
echo "  sudo tailscale up"
echo ""
