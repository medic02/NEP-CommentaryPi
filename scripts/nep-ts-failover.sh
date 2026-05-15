#!/usr/bin/env bash
# NEP Kommentatorkit – Tailscale failover
# Kjøres av systemd timer hvert 5. sekund

COMPANION_LAN_IP="${COMPANION_LAN_IP:-192.168.8.101}"
COMPANION_PORT="${COMPANION_PORT:-8000}"
LAN_DEV="${LAN_DEV:-eth0}"
TS_DEV="${TS_DEV:-tailscale0}"
LOGTAG="${LOGTAG:-nep-ts-failover}"

FAILOVER_FLAG="/home/pi/.nep-ts-failover-disabled"
FORCE_MODE_FILE="$STATE_DIR/force_mode"
SATELLITE_CONFIG="/home/satellite/satellite-config.json"

FAIL_THRESHOLD="${FAIL_THRESHOLD:-4}"
LAN_OK_BEFORE_RESET="${LAN_OK_BEFORE_RESET:-3}"
SETTLE_SECONDS="${SETTLE_SECONDS:-15}"

STATE_DIR="/run/nep-ts-failover"
mkdir -p "$STATE_DIR"
chmod a+w "$STATE_DIR"

# Les Companion IP fra satellite sin config hvis tilgjengelig
if [ -f "$SATELLITE_CONFIG" ]; then
    _ip="$(python3 -c "import json; d=json.load(open('$SATELLITE_CONFIG')); print(d.get('remoteIp',''))" 2>/dev/null || true)"
    if [ -n "$_ip" ]; then
        COMPANION_LAN_IP="$_ip"
        echo "$_ip" > "$STATE_DIR/companion_ip"
        chmod 644 "$STATE_DIR/companion_ip"
    fi
fi

# Tvangsruting overstyrer alt annet
_force="$(cat "$FORCE_MODE_FILE" 2>/dev/null || true)"
if [ "$_force" = "lan" ]; then
    clear_ts_route
    logger -t "$LOGTAG" "Force LAN – rute satt til LAN"
    exit 0
elif [ "$_force" = "ts" ]; then
    force_ts_route
    logger -t "$LOGTAG" "Force TS – rute satt til Tailscale"
    exit 0
fi

# Hopp over hvis failover er deaktivert via webgui
if [ -f "$FAILOVER_FLAG" ]; then
    logger -t "$LOGTAG" "Failover deaktivert – hopper over"
    exit 0
fi

FAIL_FILE="$STATE_DIR/fail.count"
LANOK_FILE="$STATE_DIR/lanok.count"
LAST_SIG_FILE="$STATE_DIR/last.sig"
LOCK_FILE="$STATE_DIR/lock"
RESTART_PENDING_FILE="$STATE_DIR/restart_pending"

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
    logger -t "$LOGTAG" "Flushing route cache for clean reconnect"
    ip route flush cache 2>/dev/null || true
}

schedule_satellite_restart() {
    echo "$(date +%s)" > "$RESTART_PENDING_FILE"
    logger -t "$LOGTAG" "Satellite restart scheduled in ${SETTLE_SECONDS}s"
}

check_pending_satellite_restart() {
    [ -f "$RESTART_PENDING_FILE" ] || return 0
    local ts now elapsed
    ts="$(cat "$RESTART_PENDING_FILE" 2>/dev/null || echo 0)"
    now="$(date +%s)"
    elapsed=$((now - ts))
    if [ "$elapsed" -ge "$SETTLE_SECONDS" ]; then
        rm -f "$RESTART_PENDING_FILE"
        logger -t "$LOGTAG" "Restarting satellite (${elapsed}s after network switch)"
        systemctl kill -s KILL satellite 2>/dev/null || true
        sleep 2
        systemctl start satellite 2>/dev/null || true
    fi
}

check_pending_satellite_restart

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
            schedule_satellite_restart
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
        schedule_satellite_restart
    fi
fi
