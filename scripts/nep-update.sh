#!/usr/bin/env bash
# NEP trygg oppdatering
# Oppdaterer: health.py, dashboard, watchdog, failover-script
# Rører IKKE: Tailscale, satellite, satellite-config.json, nettverksregler, systemd-units

set -euo pipefail
GITHUB_RAW="https://raw.githubusercontent.com/medic02/NEP-CommentaryPi/main"
BASE="/home/pi/health"
LOG(){ logger -t nep-update "$*"; echo "$*"; }

LOG "Starter oppdatering..."

# ── Health API + dashboard ──────────────────────────────────────────────────
curl -fsSL "$GITHUB_RAW/health/health.py"     -o "$BASE/health.py"
curl -fsSL "$GITHUB_RAW/docs/index.html"      -o "$BASE/dashboard.html"
curl -fsSL "$GITHUB_RAW/assets/nep-logo.png"  -o "$BASE/nep-logo.png" 2>/dev/null || true
curl -fsSL "$GITHUB_RAW/docs/manual.pdf"      -o "$BASE/manual.pdf" 2>/dev/null || true
chmod +x "$BASE/health.py"
LOG "health.py + dashboard + manual oppdatert"

# ── Diagnose script ────────────────────────────────────────────────────────
curl -fsSL "$GITHUB_RAW/scripts/nep-diagnose.sh" -o /tmp/nep-diagnose.sh
sudo install -m 755 /tmp/nep-diagnose.sh /usr/local/sbin/nep-diagnose.sh
LOG "nep-diagnose.sh installert/oppdatert"

# ── Satellite watchdog (kun på Pi-er med satellite.service) ─────────────────
if systemctl list-unit-files satellite.service &>/dev/null 2>&1; then
    curl -fsSL "$GITHUB_RAW/scripts/nep-satellite-watchdog.sh" \
        -o /tmp/nep-satellite-watchdog.sh
    sudo install -m 755 /tmp/nep-satellite-watchdog.sh \
        /usr/local/sbin/nep-satellite-watchdog.sh
    LOG "nep-satellite-watchdog.sh installert/oppdatert"

    sudo tee /etc/systemd/system/nep-satellite-watchdog.service > /dev/null <<'UNIT'
[Unit]
Description=NEP Satellite Watchdog – auto-restart ved stuck reconnect
After=satellite.service

[Service]
Type=simple
ExecStart=/usr/local/sbin/nep-satellite-watchdog.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT
    sudo systemctl daemon-reload
    sudo systemctl enable --now nep-satellite-watchdog.service 2>/dev/null || \
        sudo systemctl restart nep-satellite-watchdog.service 2>/dev/null || true
    LOG "nep-satellite-watchdog.service oppdatert og startet"
else
    LOG "Ingen satellite.service – hopper over watchdog"
fi

# ── Failover script (kun hvis installert) ───────────────────────────────────
# Rører IKKE Tailscale-konfig, ruting eller noen nettverksinnstillinger
if [ -f /usr/local/sbin/nep-ts-failover.sh ]; then
    curl -fsSL "$GITHUB_RAW/scripts/nep-ts-failover.sh" \
        -o /tmp/nep-ts-failover.sh
    sudo install -m 755 /tmp/nep-ts-failover.sh \
        /usr/local/sbin/nep-ts-failover.sh
    LOG "nep-ts-failover.sh oppdatert"
fi

# ── Pushover watchdog (kun companion – kun hvis installert) ─────────────────
if systemctl list-unit-files nep-watchdog.service &>/dev/null 2>&1; then
    curl -fsSL "$GITHUB_RAW/scripts/nep-watchdog.py" \
        -o "$BASE/nep-watchdog.py"
    chmod +x "$BASE/nep-watchdog.py"
    LOG "nep-watchdog.py oppdatert"
fi

# ── Restart tjenester ───────────────────────────────────────────────────────
# IKKE: satellite, tailscaled, nep-iprule, nep-ts-failover.timer
sudo systemctl restart nep-health.service
LOG "nep-health restartet"


if systemctl list-unit-files nep-watchdog.service &>/dev/null 2>&1; then
    sudo systemctl restart nep-watchdog.service 2>/dev/null && LOG "nep-watchdog restartet" || true
fi

LOG "Oppdatering fullført"
