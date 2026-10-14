#!/bin/bash
# Copies Companion's RAM databases to the USB disk as complete snapshots.
#
# Companion runs SQLite in WAL mode: recent commits live in db.sqlite-wal
# until a checkpoint folds them into db.sqlite. A raw copy of db.sqlite
# alone therefore misses them (and can be torn mid-checkpoint). SQLite's
# backup API gives a consistent snapshot including the WAL contents, so the
# disk copy is always a single self-contained file with no -wal/-shm next
# to it. A stale -wal left on disk was replayed into the database at boot
# and broke Companion's button config on 2026-10-13.
VER=$(grep -oE '^[0-9]+\.[0-9]+' /opt/companion/BUILD)
RAM="/run/companion-v${VER//./}"
DISK_HELPER="/run/companion-usb/.config/companion-nodejs/v${VER}"

[ -d "$RAM" ] || exit 0
[ -d "$DISK_HELPER" ] || exit 0

SNAP=$(mktemp -d /run/companion-ramdb-snap.XXXXXX) || exit 1
chown companion:companion "$SNAP"
trap 'rm -rf "$SNAP"' EXIT

ok=1
for name in db cache; do
    src="$RAM/$name.sqlite"
    [ -f "$src" ] || continue

    # Snapshot into RAM first (fast, short read transaction on the live db),
    # as the companion user so nothing root-owned appears next to its files.
    if ! /usr/sbin/runuser -u companion -- python3 - "$src" "$SNAP/$name.sqlite" <<'PY'
import sqlite3, sys
src = sqlite3.connect(sys.argv[1], timeout=10)
dst = sqlite3.connect(sys.argv[2])
src.backup(dst)
dst.close()
src.close()
PY
    then
        logger -t companion-ramdb "FEIL: snapshot av $name.sqlite feilet, beholder forrige kopi på USB"
        ok=0
        continue
    fi

    # Write next to the target, then rename: a power cut mid-copy leaves the
    # previous good file in place instead of a half-written one.
    tmp="$DISK_HELPER/.$name.sqlite.tmp"
    if cp "$SNAP/$name.sqlite" "$tmp" && chown companion:companion "$tmp" && sync "$tmp" && mv -f "$tmp" "$DISK_HELPER/$name.sqlite"; then
        rm -f "$DISK_HELPER/$name.sqlite-wal" "$DISK_HELPER/$name.sqlite-shm"
    else
        rm -f "$tmp"
        logger -t companion-ramdb "FEIL: kunne ikke skrive $name.sqlite til USB"
        ok=0
    fi

    [ -f "$RAM/$name.sqlite.bak" ] && rsync -a "$RAM/$name.sqlite.bak" "$DISK_HELPER/"
done

[ "$ok" = 1 ] && logger -t companion-ramdb "Synket til USB"
