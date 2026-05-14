#!/usr/bin/env bash
# NEP Kommentatorkit – Tailscale failover
# Kjøres av systemd timer hvert 5. sekund

COMPANION_LAN_IP="${COMPANION_LAN_IP:-192.168.8.101}"
COMPANION_PORT="${COMPANION_PORT:-8000}"
LAN_DEV="${LAN_DEV:-eth0}"
TS_DEV="${TS_DEV:-tailscale0}"
LOGTAG="${LOGTAG:-nep-ts-failover}"

FAIL_THRESHOLD="${FAIL_THRESHOLD:-4}"
LAN_OK_BEFORE_RESET="${LAN_OK_BEFORE_RESET:-3}"
SETTLE_SECONDS="${SETTLE_SECONDS:-15}"

STATE_DIR="/run/nep-ts-failover"
mkdir -p "$STATE_DIR"

FAIL_FILE="$STATE_DIR/fail.count"
LANOK_FILE="$STATE_DIR/lanok.count"
LAST_SIG_FILE="$STATE_DIR/last.sig"
LOCK_FILE="$STATE_DIR/lock"

touch "$FAIL_FILE" "$LANOK_FILE" "$LAST_SIG_FILE"

# Kun en instans om gangen
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    logger -t "$LOGTAG" "Already running – skipping"
    exit 0
fi

read_count() { cat "$1" 2>/dev/null | tr -d '[:space:]' || echo 0; }

route_is_forced() {
    ip route show "$COMPANION_LAN_IP/32" 2>/dev/null | grep -q "dev $TS_DEV"
}

force_ts_route() {
    ip route replace "$COMPANION_LAN_IP/32" dev "$TS_DEV" 2>/dev/null
}

clear_ts_route() {
    ip route del "$COMPANION_LAN_IP/32" dev "$TS_DEV" 2>/dev/null || true
}

net_sig() {
    local ip4 link forced
    ip4="$(ip -4 addr show dev "$LAN_DEV" 2>/dev/null | awk '/inet /{print $2}' | head -n1 || true)"
    link="$(cat "/sys/class/net/$LAN_DEV/operstate" 2>/dev/null || echo "?")"
    forced=$(route_is_forced && echo 1 || echo 0)
    echo "$LAN_DEV|$link|$ip4|forced=$forced"
}

network_changed() {
    local cur last
    cur="$(net_sig)"
    last="$(cat "$LAST_SIG_FILE" 2>/dev/null || true)"
    if [ "$cur" != "$last" ]; then
        echo "$cur" > "$LAST_SIG_FILE"
        return 0
    fi
    return 1
}

http_ok_via_lan() {
    curl -sS -m 2 --connect-timeout 2 --interface "$LAN_DEV" -o /dev/null \
        "http://$COMPANION_LAN_IP:$COMPANION_PORT/" 2>/dev/null
}

restart_satellite() {
    logger -t "$LOGTAG" "Restarting satellite service for clean reconnect"
    ip route flush cache 2>/dev/null || true
    sleep 1
    systemctl restart satellite 2>/dev/null || true
}

# Nettverksendring: vent og reset tellere
if network_changed; then
    logger -t "$LOGTAG" "Network change detected – settling ${SETTLE_SECONDS}s"
    sleep "$SETTLE_SECONDS"
    echo "0" > "$FAIL_FILE"
    echo "0" > "$LANOK_FILE"
fi

fail_count=$(read_count "$FAIL_FILE")
lanok_count=$(read_count "$LANOK_FILE")

# Pa Tailscale: sjekk om LAN er tilbake
if route_is_forced; then
    if http_ok_via_lan; then
        lanok_count=$((lanok_count + 1))
        echo "$lanok_count" > "$LANOK_FILE"
        logger -t "$LOGTAG" "LAN RETURN OK (${lanok_count}/${LAN_OK_BEFORE_RESET})"

        if [ "$lanok_count" -ge "$LAN_OK_BEFORE_RESET" ]; then
            logger -t "$LOGTAG" "Switching BACK to LAN"
            clear_ts_route
            echo "0" > "$LANOK_FILE"
            restart_satellite
        fi
    else
        echo "0" > "$LANOK_FILE"
        logger -t "$LOGTAG" "RECOVERY FAIL (still on Tailscale)"
    fi
    exit 0
fi

# Normal drift: sjekk LAN
if http_ok_via_lan; then
    if [ "$(read_count "$FAIL_FILE")" -gt 0 ]; then
        logger -t "$LOGTAG" "LAN OK (recovered)"
    fi
    echo "0" > "$FAIL_FILE"
else
    fail_count=$((fail_count + 1))
    echo "$fail_count" > "$FAIL_FILE"
    logger -t "$LOGTAG" "LAN FAIL (${fail_count}/${FAIL_THRESHOLD})"

    if [ "$fail_count" -ge "$FAIL_THRESHOLD" ]; then
        logger -t "$LOGTAG" "FAILOVER -> switching to TAILSCALE"
        force_ts_route
        echo "0" > "$FAIL_FILE"
        restart_satellite
    fi
fi
