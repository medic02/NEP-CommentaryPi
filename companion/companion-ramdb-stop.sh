#!/bin/bash
VER=$(grep -oE '^[0-9]+\.[0-9]+' /opt/companion/BUILD)
DISK="/home/companion/.config/companion-nodejs/v${VER}"
USB_MOUNT="/run/companion-usb"

/usr/local/sbin/companion-ramdb-sync.sh

umount "$DISK" 2>/dev/null || true
umount "$USB_MOUNT" 2>/dev/null || true

logger -t companion-ramdb "Shutdown sync fullfort"
