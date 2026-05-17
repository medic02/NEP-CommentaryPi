#!/usr/bin/env bash
# NEP Diagnose – samler alle relevante logger til én fil
# Kjøres på companion Pi eller satellite Pi
# Bruk: curl -fsSL https://raw.githubusercontent.com/medic02/NEP-CommentaryPi/main/scripts/nep-diagnose.sh | bash

OUT="/tmp/nep-diag-$(date +%Y%m%d-%H%M%S).txt"
HR="════════════════════════════════════════════════════════"

log_section() { echo -e "\n$HR\n  $1\n$HR\n" >> "$OUT"; }

echo "NEP Diagnose – samler logger..."
echo "Fil: $OUT"

{
echo "NEP Diagnose – $(date)"
echo "Hostname: $(hostname)  |  IP: $(hostname -I | awk '{print $1}')"

log_section "SYSTEMD TJENESTER"
systemctl status satellite nep-health nep-ts-failover.timer nep-satellite-watchdog nep-watchdog 2>/dev/null || true

log_section "SATELLITE LOGGER (siste 200 linjer)"
journalctl -u satellite -n 200 --no-pager 2>/dev/null || echo "Ikke tilgjengelig"

log_section "COMPANION LOGGER – siste 2 timer (backup + disconnect)"
journalctl -u companion --since "2 hours ago" --no-pager 2>/dev/null \
    | grep -E "backup complete|connection closed|ping timeout|satellite|disconnect" \
    || echo "Ikke tilgjengelig"

log_section "NEP FAILOVER LOGGER"
journalctl -t nep-ts-failover -n 100 --no-pager 2>/dev/null || echo "Ikke tilgjengelig"

log_section "NEP WATCHDOG LOGGER"
journalctl -t nep-watchdog -n 100 --no-pager 2>/dev/null || echo "Ikke tilgjengelig"

log_section "NEP SATELLITE WATCHDOG LOGGER"
journalctl -t nep-satellite-watchdog -n 50 --no-pager 2>/dev/null || echo "Ikke tilgjengelig"

log_section "NETTVERKSINFO"
ip addr show 2>/dev/null || true
echo ""
tailscale status 2>/dev/null || echo "Tailscale ikke tilgjengelig"

log_section "HEALTH API"
curl -s http://localhost:8080/health 2>/dev/null | python3 -m json.tool || echo "Ikke tilgjengelig"

} >> "$OUT" 2>&1

echo "Ferdig! Send meg denne filen:"
echo "  $OUT"
