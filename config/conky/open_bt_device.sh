#!/bin/bash
# Open Bluetooth Settings, find the named device row, and click it directly.
NAME="${1:-}"
exec 9>"${XDG_RUNTIME_DIR:-/tmp}/conky-bt-open.lock"
flock -n 9 || exit 0
LOG="$HOME/.cache/conky_bt_navigation.log"
mkdir -p "$HOME/.cache"
# Cinnamon does not start GNOME's radio-status service. The Bluetooth panel
# needs its BluetoothHasAirplaneMode property or reports no adapter.
RFKILL_SERVICE=org.gnome.SettingsDaemon.Rfkill
RFKILL_PATH=/org/gnome/SettingsDaemon/Rfkill
rfkill_ready() {
    gdbus call --session --dest "$RFKILL_SERVICE" --object-path "$RFKILL_PATH" \
        --method org.freedesktop.DBus.Properties.GetAll "$RFKILL_SERVICE" \
        2>/dev/null | grep -q BluetoothHasAirplaneMode
}
if ! rfkill_ready && [ -x /usr/libexec/gsd-rfkill ]; then
    # Never change power or disconnect devices; this exposes their radio state.
    XDG_CURRENT_DESKTOP=GNOME /usr/libexec/gsd-rfkill >>"$LOG" 2>&1 9>&- &
    disown
    for ((i=0; i<30; i++)); do
        rfkill_ready && break
        sleep 0.1
    done
    rfkill_ready || echo "GNOME Bluetooth radio-status service unavailable" >>"$LOG"
fi
# GNOME Settings rejects Cinnamon's desktop name before opening a window.
# Override it only for this process, preserving the desktop session itself.
# Reuse Settings rather than closing and restarting it for each device.
XDG_CURRENT_DESKTOP=GNOME gnome-control-center bluetooth >>"$LOG" 2>&1 9>&- &
disown
WID=""
for ((i=0; i<160; i++)); do
    WID=$(wmctrl -lx | awk 'tolower($3) ~ /gnome-control-center/ {print $1; exit}')
    [ -n "$WID" ] && break
    sleep 0.05
done
[ -z "$WID" ] && { echo "Settings window unavailable" >> "$LOG"; exit 1; }
xdotool windowactivate --sync "$WID" 2>>"$LOG" || exit 1
[ -z "$NAME" ] && exit 0
/usr/bin/python3 /home/lonzo/.config/conky/select_bt_device.py "$NAME" "$WID" >>"$LOG" 2>&1
