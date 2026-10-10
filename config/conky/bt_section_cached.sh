#!/bin/bash
# Read the display cache immediately; compare live BlueZ state every second.
CACHE="$HOME/.cache/conky_bt_section${CONKY_BT_ROW_START:+-$CONKY_BT_ROW_START}.txt"
SIGNATURE="$HOME/.cache/conky_bt_snapshot${CONKY_BT_ROW_START:+-$CONKY_BT_ROW_START}.tsv"
mkdir -p "$HOME/.cache"
[ -s "$CACHE" ] && cat "$CACHE"
(
    flock -n 8 || exit 0
    snapshot=$(mktemp "$HOME/.cache/conky_bt_snapshot.XXXXXX")
    tmp=$(mktemp "$HOME/.cache/conky_bt_section.XXXXXX")
    trap 'rm -f "$snapshot" "$tmp"' EXIT
    /usr/bin/python3 /home/lonzo/.config/conky/bt_snapshot.py > "$snapshot" || exit 1
    dirty="$HOME/.cache/conky_bt_dirty"
    now=$(date +%s)
    age=$((now - $(stat -c %Y "$CACHE" 2>/dev/null || echo 0)))
    if [ -s "$CACHE" ] && [ "$age" -lt 15 ] && [ ! -e "$dirty" ] && cmp -s "$snapshot" "$SIGNATURE"; then
        exit 0
    fi
    rm -f "$dirty"
    if CONKY_BT_SNAPSHOT="$snapshot" /home/lonzo/.config/conky/bt_section.sh > "$tmp"; then
        mv "$tmp" "$CACHE"
        mv "$snapshot" "$SIGNATURE"
    fi
) 8>"$HOME/.cache/conky_bt_section${CONKY_BT_ROW_START:+-$CONKY_BT_ROW_START}.lock" >/dev/null 2>&1 &
