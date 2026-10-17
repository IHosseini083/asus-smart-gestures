#!/usr/bin/env bash
# ==============================================================================
# ASUS Smart Gestures - Universal Installer
# ==============================================================================
set -euo pipefail

# ANSI color codes
_BOLD='\033[1m'
_GREEN='\033[32m'
_BLUE='\033[34m'
_YELLOW='\033[33m'
_RED='\033[31m'
_RESET='\033[0m'

info()    { printf "${_BLUE}${_BOLD}[INFO]${_RESET}  %s\n" "$*"; }
success() { printf "${_GREEN}${_BOLD}[OK]${_RESET}    %s\n" "$*"; }
warn()    { printf "${_YELLOW}${_BOLD}[WARN]${_RESET}  %s\n" "$*"; }
error()   { printf "${_RED}${_BOLD}[ERROR]${_RESET} %s\n" "$*" >&2; }

trap 'error "Installation aborted due to an unexpected error on line $LINENO."' ERR

show_help() {
    cat << EOF
Usage: sudo ./install.sh [OPTIONS]

Options:
    -h, --help             Show this help message and exit
    -y, --non-interactive  Run without interactive prompts
    --no-start             Install files and enable service without starting immediately
EOF
}

NON_INTERACTIVE=false
START_SERVICE=true

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        -y|--non-interactive)
            NON_INTERACTIVE=true
            shift
            ;;
        --no-start)
            START_SERVICE=false
            shift
            ;;
        *)
            error "Unknown argument: $1"
            show_help
            exit 1
            ;;
    esac
done

# 1. Privilege Check
if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root (e.g. sudo ./install.sh)."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DEST="/usr/local/bin/asus-smart-gestures"
SERVICE_DEST="/etc/systemd/system/asus-smart-gestures.service"
MODULE_DEST="/etc/modules-load.d/uinput.conf"
CONF_DEST="/etc/asus-smart-gestures.conf"
LIB_DEST="/usr/local/lib/asus-smart-gestures"

printf "\n${_BOLD}=== Installing ASUS Smart Gestures for Linux ===${_RESET}\n\n"

# 2. Dependency Checks
info "Checking dependencies..."

if ! command -v python3 >/dev/null 2>&1; then
    error "Python 3 is not installed. Please install Python 3 (>= 3.10) and try again."
    exit 1
fi

# Check Python version (>= 3.10 required)
PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

if (( PY_MAJOR < 3 || (PY_MAJOR == 3 && PY_MINOR < 10) )); then
    error "Python version $PY_VERSION detected. Python >= 3.10 is required."
    exit 1
fi
success "Python version $PY_VERSION satisfies requirement (>= 3.10)."

if ! command -v systemctl >/dev/null 2>&1; then
    error "systemd (systemctl) not detected. This installer requires a systemd-based Linux distribution."
    exit 1
fi
success "Systemd detected."

# 3. Copy Python Library
info "Deploying Python package to $LIB_DEST..."
mkdir -p "$LIB_DEST"
rm -rf "$LIB_DEST/asus_smart_gestures"
cp -r "$SCRIPT_DIR/asus_smart_gestures" "$LIB_DEST/"
success "Python package copied."

# 4. Create Launcher Executable
info "Creating executable launcher at $BIN_DEST..."
cat << 'EOF' > "$BIN_DEST"
#!/usr/bin/env python3
import sys
sys.path.insert(0, "/usr/local/lib/asus-smart-gestures")
from asus_smart_gestures.cli import main
if __name__ == "__main__":
    main()
EOF
chmod 755 "$BIN_DEST"
success "Executable launcher created with 755 permissions."

# 5. Configuration File
if [[ ! -f "$CONF_DEST" ]]; then
    info "Installing default configuration template to $CONF_DEST..."
    install -m644 "$SCRIPT_DIR/config/asus-smart-gestures.conf.example" "$CONF_DEST"
    success "Default configuration created."
else
    info "Existing configuration found at $CONF_DEST (preserved)."
fi

# 6. Kernel Module Setup (uinput)
info "Configuring uinput kernel module..."
install -m644 "$SCRIPT_DIR/systemd/uinput.conf" "$MODULE_DEST"

if ! lsmod | grep -q uinput; then
    info "Loading uinput kernel module..."
    modprobe uinput || warn "Could not load uinput with modprobe. It may already be built into the kernel."
fi
success "uinput configured for automatic load at boot."

# 7. Systemd Service Deployment
info "Installing systemd service unit to $SERVICE_DEST..."
install -m644 "$SCRIPT_DIR/systemd/asus-smart-gestures.service" "$SERVICE_DEST"

systemctl daemon-reload
systemctl enable asus-smart-gestures.service
success "Systemd service enabled."

if [[ "$START_SERVICE" = true ]]; then
    info "Starting asus-smart-gestures service..."
    systemctl restart asus-smart-gestures.service
    success "Service started."
fi

printf "\n${_GREEN}${_BOLD}=== Installation Successfully Completed! ===${_RESET}\n\n"
printf "Useful commands:\n"
printf "  • Live logs       : journalctl -u asus-smart-gestures -f\n"
printf "  • Service status  : systemctl status asus-smart-gestures\n"
printf "  • Diagnostics     : asus-smart-gestures --doctor\n"
printf "  • Calibration tool: sudo asus-smart-gestures --calibrate\n"
printf "  • Configuration   : %s\n\n" "$CONF_DEST"
EOF
