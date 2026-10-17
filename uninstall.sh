#!/usr/bin/env bash
# Universal uninstaller for ASUS Smart Gestures
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root (or with sudo / pkexec)." >&2
    exit 1
fi

echo "=== Uninstalling ASUS Smart Gestures ==="

systemctl disable --now asus-smart-gestures 2>/dev/null || true

rm -f /usr/local/bin/asus-smart-gestures
rm -rf /usr/local/lib/asus-smart-gestures
rm -f /etc/systemd/system/asus-smart-gestures.service
rm -f /etc/modules-load.d/uinput.conf

systemctl daemon-reload

echo "Note: Configuration file /etc/asus-smart-gestures.conf was kept. Delete manually if desired."
echo "=== Uninstalled successfully. Touchpad is back to standard driver behavior. ==="
