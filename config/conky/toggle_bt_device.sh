#!/bin/bash
# Toggle only the selected paired device, using its current BlueZ state.
set -u
MAC="${1:-}"
[[ "$MAC" =~ ^([[:xdigit:]]{2}:){5}[[:xdigit:]]{2}$ ]] || exit 2
mkdir -p "$HOME/.cache"
exec 9>"${XDG_RUNTIME_DIR:-/tmp}/conky-bt-toggle-${MAC//:/}.lock"
flock -n 9 || exit 0
LOG="$HOME/.cache/conky_bt_toggle.log"
export LC_ALL=C
INFO=$(timeout 5 bluetoothctl info "$MAC" 2>>"$LOG") || exit 1
PAIRED=$(awk -F': ' '/^[[:space:]]*Paired:/ {print $2}' <<< "$INFO")
CONNECTED=$(awk -F': ' '/^[[:space:]]*Connected:/ {print $2}' <<< "$INFO")
[ "$PAIRED" = "yes" ] || exit 1
case "$CONNECTED" in
    yes) ACTION=disconnect ;;
    no) ACTION=connect ;;
    *) exit 1 ;;
esac
PENDING="$HOME/.cache/conky_bt_pending_${MAC//:/}"
cleanup() {
    if [ "${RESULT:-0}" -ne 0 ]; then
        printf 'failed\t%s\n' "$(date +%s)" > "$PENDING"
    else
        rm -f "$PENDING"
    fi
    touch "$HOME/.cache/conky_bt_dirty"
    /home/lonzo/.config/conky/bt_section_cached.sh >/dev/null
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
TMP=$(mktemp "$HOME/.cache/conky_bt_pending.XXXXXX")
printf '%sing\t%s\n' "${ACTION%e}" "$(date +%s)" > "$TMP"
mv "$TMP" "$PENDING"
touch "$HOME/.cache/conky_bt_dirty"
/home/lonzo/.config/conky/bt_section_cached.sh >/dev/null
printf '%s %s %s\n' "$(date -Is)" "$ACTION" "$MAC" >> "$LOG"
RESULT=0
timeout 20 bluetoothctl "$ACTION" "$MAC" >>"$LOG" 2>&1 || RESULT=$?
exit "$RESULT"
