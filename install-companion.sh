#!/usr/bin/env bash
# NEP Kommentatorkit – Companion Pi installer
# Setter opp alt som er spesifikt for Companion Pi (ikke Satellite Pi-ene):
# Health API + watchdog, RAM-database for Companion sin config-mappe, og
# testbildegeneratoren (fargestolper/sprett-logo/skjermsparer-kiosken).
#
# FORUTSETNINGER (gjøres ikke av dette scriptet):
#   - Bitfocus Companion selv er allerede installert (offisiell installer/image)
#     og kjører som systemd-tjenesten "companion"
#   - En USB-disk er formatert og montert på /home/companion (RAM-db-steget
#     hopper over seg selv med en tydelig advarsel hvis den ikke finner dette)
#   - HDMI->SDI-converteren er fysisk koblet til for testbildegeneratoren
#
# Bruk: curl -fsSL https://raw.githubusercontent.com/medic02/NEP-CommentaryPi/main/install-companion.sh | bash

set -euo pipefail

GITHUB_RAW="https://raw.githubusercontent.com/medic02/NEP-CommentaryPi/main"

echo ""
echo "================================="
echo " NEP Companion Pi Installer"
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

NEP_ID="${NEP_ID:-Companion Pi}"
COMPANION_IP="${COMPANION_IP:-192.168.8.101}"
COMPANION_PORT="${COMPANION_PORT:-8000}"
LAN_DEV="${LAN_DEV:-eth0}"
TS_DEV="${TS_DEV:-tailscale0}"
TESTBILDE_PORT="${TESTBILDE_PORT:-5050}"

echo "Navn:            $NEP_ID"
echo "Companion:       $COMPANION_IP:$COMPANION_PORT"
echo "Testbilde-port:  $TESTBILDE_PORT"
echo ""

# ── [1/6] Pakker ─────────────────────────────────────────────────────────────
echo "[1/6] Installerer pakker..."
sudo apt-get update -y -q
sudo apt-get install -y -q python3 python3-venv curl rsync \
    xserver-xorg xinit matchbox-window-manager chromium x11-xserver-utils

# ── [2/6] Health API + Watchdog (delt med install-health.sh) ────────────────
echo "[2/6] Setter opp Health API og Watchdog..."
PUSHOVER_TOKEN="${PUSHOVER_TOKEN:-}"
PUSHOVER_USER="${PUSHOVER_USER:-}"
if [ -z "$PUSHOVER_TOKEN" ]; then
    read_tty PUSHOVER_TOKEN "Pushover API Token (blank = hopp over varsler): " ""
fi
if [ -z "$PUSHOVER_USER" ]; then
    read_tty PUSHOVER_USER "Pushover User Key (blank = hopp over varsler): " ""
fi
NEP_ID="$NEP_ID" COMPANION_IP="$COMPANION_IP" COMPANION_PORT="$COMPANION_PORT" \
LAN_DEV="$LAN_DEV" TS_DEV="$TS_DEV" \
PUSHOVER_TOKEN="$PUSHOVER_TOKEN" PUSHOVER_USER="$PUSHOVER_USER" \
NEP_CHOICE="skip" \
    bash -c "$(curl -fsSL "$GITHUB_RAW/install-health.sh")"

# ── [3/6] Companion RAM-database ─────────────────────────────────────────────
echo "[3/6] Setter opp Companion RAM-database..."

if ! id companion >/dev/null 2>&1; then
    echo "  ADVARSEL: brukeren 'companion' finnes ikke ennå."
    echo "  Hopper over RAM-db -- installer Bitfocus Companion først, kjør så:"
    echo "    curl -fsSL $GITHUB_RAW/install-companion.sh | bash"
elif [ "$(findmnt -n -o SOURCE /home/companion 2>/dev/null)" = "" ] || \
     [ "$(findmnt -n -o TARGET /home/companion 2>/dev/null)" != "/home/companion" ]; then
    echo "  ADVARSEL: /home/companion er ikke et eget montert filsystem (USB-disk)."
    echo "  RAM-db forutsetter en formatert USB-disk montert der -- hopper over."
    echo "  Se companion/README.md for manuelt oppsett når disken er klar."
else
    sudo systemctl stop companion-ramdb.service 2>/dev/null || true

    for f in companion-ramdb-load.sh companion-ramdb-stop.sh companion-ramdb-sync.sh; do
        curl -fsSL "$GITHUB_RAW/companion/$f" -o "/tmp/$f"
        sudo install -m 755 "/tmp/$f" "/usr/local/sbin/$f"
    done

    for f in companion-ramdb.service companion-ramdb-sync.service companion-ramdb-sync.timer; do
        curl -fsSL "$GITHUB_RAW/companion/$f" -o "/tmp/$f"
        sudo install -m 644 "/tmp/$f" "/etc/systemd/system/$f"
    done

    sudo mkdir -p /etc/systemd/system/companion.service.d
    curl -fsSL "$GITHUB_RAW/companion/ramdb.conf" -o /tmp/ramdb.conf
    sudo install -m 644 /tmp/ramdb.conf /etc/systemd/system/companion.service.d/ramdb.conf

    sudo systemctl daemon-reload
    sudo systemctl enable --now companion-ramdb.service companion-ramdb-sync.timer
    sudo systemctl restart companion 2>/dev/null || true
    echo "  RAM-database installert. Verifiser med: mount | grep companion-nodejs"
fi

# ── [4/6] Testbildegenerator ──────────────────────────────────────────────────
echo "[4/6] Setter opp testbildegenerator..."

TB_BASE="/home/pi/testbilde-server"
sudo systemctl stop nep-testbilde.service 2>/dev/null || true

mkdir -p "$TB_BASE/templates" "$TB_BASE/screensavers" "$TB_BASE/uploads"

curl -fsSL "$GITHUB_RAW/testbilde/server.py" -o "$TB_BASE/server.py"
curl -fsSL "$GITHUB_RAW/testbilde/templates/admin.html" -o "$TB_BASE/templates/admin.html"
curl -fsSL "$GITHUB_RAW/testbilde/templates/display.html" -o "$TB_BASE/templates/display.html"

for f in common.js style.css dvd.html matrix.html pong.html pulse.html \
         starfield.html time.html toasters.html NEP-Logo-FC-WHITE-RGB.png; do
    curl -fsSL "$GITHUB_RAW/testbilde/screensavers/$f" -o "$TB_BASE/screensavers/$f"
done

rm -rf "$TB_BASE/venv"
python3 -m venv "$TB_BASE/venv"
source "$TB_BASE/venv/bin/activate"
pip install --upgrade pip -q
pip install flask -q
deactivate

sudo tee /etc/systemd/system/nep-testbilde.service > /dev/null <<EOF
[Unit]
Description=NEP Testbildegenerator
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=$TB_BASE
ExecStart=$TB_BASE/venv/bin/python $TB_BASE/server.py
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now nep-testbilde.service

# ── [5/6] Kiosk-oppsett (fullskjerm-visning på tty1) ─────────────────────────
echo "[5/6] Setter opp kiosk (fullskjerm-visning av testbildet)..."

cat > /home/pi/.xinitrc <<EOF
#!/bin/sh
xset s off
xset s noblank
xset -dpms
matchbox-window-manager -use_titlebar no &
sleep 1
exec chromium --kiosk --window-size=1920,1080 --window-position=0,0 --start-fullscreen --noerrdialogs --disable-infobars --disable-session-crashed-bubble --disable-translate --check-for-update-interval=31536000 --no-first-run --user-data-dir=/home/pi/.chromium-kiosk http://localhost:$TESTBILDE_PORT/display
EOF
chmod +x /home/pi/.xinitrc

if ! grep -q 'startx -- -nocursor' /home/pi/.bash_profile 2>/dev/null; then
    cat >> /home/pi/.bash_profile <<'EOF'
if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then startx -- -nocursor; fi
EOF
fi

sudo mkdir -p /etc/systemd/system/getty@tty1.service.d
sudo tee /etc/systemd/system/getty@tty1.service.d/autologin.conf > /dev/null <<EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin pi --noclear %I \$TERM
EOF
sudo systemctl daemon-reload

echo "  Kiosk satt opp. IKKE restartet automatisk -- gjelder fra neste boot/login på tty1."
echo "  (Konverter-formatet/xrandr-bytte krever at HDMI->SDI-converteren faktisk er tilkoblet.)"

# ── [6/6] Tailscale accept-routes ─────────────────────────────────────────────
echo "[6/6] Verifiserer Tailscale accept-routes..."

if command -v tailscale >/dev/null 2>&1; then
    sudo tailscale set --accept-routes=true --accept-dns=false || \
        echo "  ADVARSEL: klarte ikke sette accept-routes -- kjør manuelt: sudo tailscale set --accept-routes=true"

    ROUTEALL="$(sudo tailscale debug prefs 2>/dev/null | grep -i '"RouteAll"' | grep -o 'true\|false' || echo "ukjent")"
    if [ "$ROUTEALL" != "true" ]; then
        echo "  ADVARSEL: accept-routes er IKKE skrudd på (RouteAll=$ROUTEALL)."
        echo "  Dette er et kjent hull -- satt feil kan Satellite-failover gå i tomme rør."
        echo "  Fiks manuelt: sudo tailscale set --accept-routes=true"
    else
        echo "  accept-routes bekreftet PÅ."
    fi
else
    echo "  Tailscale ikke installert -- hopper over (installer og kjør 'sudo tailscale up' manuelt)."
fi

# ── Ferdig ────────────────────────────────────────────────────────────────────
echo ""
echo "FERDIG ✅"
echo ""
echo "Health API:        http://$(hostname -I | awk '{print $1}'):8080/health"
echo "Testbilde admin:   http://$(hostname -I | awk '{print $1}'):$TESTBILDE_PORT/"
echo "Testbilde display: http://$(hostname -I | awk '{print $1}'):$TESTBILDE_PORT/display"
echo "Deck API:          http://$(hostname -I | awk '{print $1}'):$TESTBILDE_PORT/api/deck"
echo ""
echo "Husk:"
echo "  - 'sudo tailscale up' første gang hvis ikke allerede innlogget"
echo "  - RAM-db: se companion/README.md hvis USB-disken ikke var klar ennå"
echo "  - Kiosk starter automatisk ved neste innlogging på tty1 (eller: sudo reboot)"
echo ""
