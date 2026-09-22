#!/bin/bash
set -e
VER=$(grep -oE '^[0-9]+\.[0-9]+' /opt/companion/BUILD)
DISK="/home/companion/.config/companion-nodejs/v${VER}"
RAM="/run/companion-v${VER//./}"
USB_MOUNT="/run/companion-usb"

# Mont USB-disken direkte (unngar propagasjonsproblem)
DEVICE=$(findmnt -n -o SOURCE /home/companion)
mkdir -p "$USB_MOUNT"
mount -t ext4 "$DEVICE" "$USB_MOUNT"
DISK_HELPER="$USB_MOUNT/.config/companion-nodejs/v${VER}"

# Kopier arbeidsfiler til RAM
mkdir -p "$RAM/backups"
rsync -a --exclude 'backups' "$DISK/" "$RAM/"
chown -R companion:companion "$RAM"

# Bind RAM over hoved-sti
mount --bind "$RAM" "$DISK"

logger -t companion-ramdb "RAM database klar (v$VER)"
