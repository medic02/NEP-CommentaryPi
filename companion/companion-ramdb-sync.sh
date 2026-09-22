#!/bin/bash
VER=$(grep -oE '^[0-9]+\.[0-9]+' /opt/companion/BUILD)
RAM="/run/companion-v${VER//./}"
DISK_HELPER="/run/companion-usb/.config/companion-nodejs/v${VER}"

[ -d "$RAM" ] || exit 0
[ -d "$DISK_HELPER" ] || exit 0

rsync -a "$RAM/db.sqlite" "$RAM/db.sqlite.bak" "$RAM/cache.sqlite" "$RAM/cache.sqlite.bak" "$DISK_HELPER/" 2>/dev/null && logger -t companion-ramdb "Synket til USB"
