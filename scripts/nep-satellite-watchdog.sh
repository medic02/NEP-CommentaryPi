#!/usr/bin/env bash
# NEP Satellite Watchdog
# Restarter satellite automatisk etter ping timeout (stuck reconnect)

LOGTAG="nep-satellite-watchdog"
SETTLE=20  # sekunder å vente etter timeout før restart

logger -t "$LOGTAG" "Watchdog startet"

journalctl -u satellite -f --no-pager -n 0 | while read -r line; do
    if echo "$line" | grep -q "ping timeout"; then
        logger -t "$LOGTAG" "Ping timeout oppdaget – venter ${SETTLE}s og restarter satellite"
        sleep "$SETTLE"
        # Sjekk om plugin re-initialiserte seg etter timeout
        if ! journalctl -u satellite --since "-${SETTLE}s" | grep -q "Initializing plugin"; then
            logger -t "$LOGTAG" "Plugin ikke re-initialisert – restarter satellite"
            systemctl restart satellite
        else
            logger -t "$LOGTAG" "Plugin re-initialisert OK – ingen restart nødvendig"
        fi
    fi
done
