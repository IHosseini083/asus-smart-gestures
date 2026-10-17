#!/usr/bin/env bash
# Universal installer for ASUS Smart Gestures
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root (or with sudo / pkexec)." >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DEST="/usr/local/bin/asus-smart-gestures"
SERVICE_DEST="/etc/systemd/system/asus-smart-gestures.service"
MODULE_DEST="/etc/modules-load.d/uinput.conf"
CONF_DIR="/etc"
CONF_DEST="/etc/asus-smart-gestures.conf"
LIB_DEST="/usr/local/lib/asus-smart-gestures"

echo "=== Installing ASUS Smart Gestures ==="

# 1. Install python module to /usr/local/lib
echo "-> Installing Python package..."
mkdir -p "$LIB_DEST"
cp -r "$SCRIPT_DIR/asus_smart_gestures" "$LIB_DEST/"

# 2. Create wrapper launcher script
echo "-> Creating binary executable in $BIN_DEST..."
cat << 'EOF' > "$BIN_DEST"
#!/usr/bin/env python3
import sys
sys.path.insert(0, "/usr/local/lib/asus-smart-gestures")
from asus_smart_gestures.cli import main
if __name__ == "__main__":
    main()
EOF
chmod 755 "$BIN_DEST"

# 3. Install default configuration if not already present
if [[ ! -f "$CONF_DEST" ]]; then
    echo "-> Creating default config in $CONF_DEST..."
    install -m644 "$SCRIPT_DIR/config/asus-smart-gestures.conf.example" "$CONF_DEST"
else
    echo "-> Config file $CONF_DEST already exists, skipping."
fi

# 4. Install uinput module auto-loader
echo "-> Setting up uinput kernel module..."
install -m644 "$SCRIPT_DIR/systemd/uinput.conf" "$MODULE_DEST"
modprobe uinput 2>/dev/null || true

# 5. Install and enable systemd unit
echo "-> Installing systemd service..."
install -m644 "$SCRIPT_DIR/systemd/asus-smart-gestures.service" "$SERVICE_DEST"

systemctl daemon-reload
systemctl enable --now asus-smart-gestures

echo "=== Installation complete! ==="
systemctl --no-pager status asus-smart-gestures || true
