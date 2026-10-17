#!/usr/bin/env bash
# ==============================================================================
# ASUS Smart Gestures - Universal Uninstaller
# ==============================================================================
set -euo pipefail

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

show_help() {
    cat << EOF
Usage: sudo ./uninstall.sh [OPTIONS]

Options:
    -h, --help    Show this help message and exit
    --purge       Also remove configuration files (/etc/asus-smart-gestures.conf)
EOF
}

PURGE_CONFIG=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        --purge)
            PURGE_CONFIG=true
            shift
            ;;
        *)
            error "Unknown argument: $1"
            show_help
            exit 1
            ;;
    esac
done

if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root (e.g. sudo ./uninstall.sh)."
    exit 1
fi

printf "\n${_BOLD}=== Uninstalling ASUS Smart Gestures ===${_RESET}\n\n"

# 1. Stop and Disable Service
if command -v systemctl >/dev/null 2>&1; then
    info "Stopping and disabling asus-smart-gestures systemd service..."
    systemctl disable --now asus-smart-gestures.service 2>/dev/null || true
    rm -f /etc/systemd/system/asus-smart-gestures.service
    systemctl daemon-reload
    success "Systemd service stopped and removed."
fi

# 2. Remove Binary and Library
info "Removing installed binaries and libraries..."
rm -f /usr/local/bin/asus-smart-gestures
rm -rf /usr/local/lib/asus-smart-gestures
rm -f /etc/modules-load.d/uinput.conf
success "Binaries and modules-load files removed."

# 3. Handle Configuration
if [[ "$PURGE_CONFIG" = true ]]; then
    info "Purging configuration file /etc/asus-smart-gestures.conf..."
    rm -f /etc/asus-smart-gestures.conf
    success "Configuration file purged."
else
    if [[ -f /etc/asus-smart-gestures.conf ]]; then
        info "Preserved configuration file: /etc/asus-smart-gestures.conf"
        info "(Use './uninstall.sh --purge' if you wish to delete it)."
    fi
fi

printf "\n${_GREEN}${_BOLD}=== Uninstallation Complete ===${_RESET}\n"
printf "Touchpad has reverted to native Linux multitouch driver behavior.\n\n"
