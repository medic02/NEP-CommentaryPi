#!/bin/bash
set -e
VER=$(grep -oE '^[0-9]+\.[0-9]+' /opt/companion/BUILD)
DISK="/home/companion/.config/companion-nodejs/v${VER}"
RAM="/run/companion-v${VER//./}"
USB_MOUNT="/run/companion-usb"

# Mont USB-disken direkte (unngar propagasjonsproblem)
# Retry: pa kald boot er USB-disken av og til ikke klar enda nar denne
# servicen (Before=companion.service, After=local-fs.target) kjorer,
# som for ServiceResult=exit-code og companion skriver rett til disk.
DEVICE=""
for i in $(seq 1 15); do
  DEVICE=$(findmnt -n -o SOURCE /home/companion 2>/dev/null || true)
  [ -n "$DEVICE" ] && break
  logger -t companion-ramdb "Waiting for /home/companion mount (attempt $i)"
  sleep 1
done
if [ -z "$DEVICE" ]; then
  logger -t companion-ramdb "ERROR: /home/companion never mounted, giving up"
  exit 1
fi

mkdir -p "$USB_MOUNT"
mount -t ext4 "$DEVICE" "$USB_MOUNT"
DISK_HELPER="$USB_MOUNT/.config/companion-nodejs/v${VER}"

# Kopier arbeidsfiler til RAM
mkdir -p "$RAM/backups"
# Never carry -wal/-shm into RAM: the disk copy is a complete snapshot
# (see companion-ramdb-sync.sh), and a stale WAL would be replayed on top
# of it when Companion opens the database.
rsync -a --exclude 'backups' --exclude '*-wal' --exclude '*-shm' --exclude '.*.tmp' "$DISK/" "$RAM/"
chown -R companion:companion "$RAM"

# Bind RAM over hoved-sti
mount --bind "$RAM" "$DISK"

logger -t companion-ramdb "RAM database klar (v$VER)"
