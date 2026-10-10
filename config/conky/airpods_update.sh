#!/bin/bash
exec 7>"$HOME/.cache/airpods_update.sh.lock"
flock -n 7 || exit 0
CACHE="$HOME/.cache/airpods_battery.json"
OUT=$(timeout 10 "$HOME/bin/airpods" --json --mac 41:42:6B:6B:10:D1 2>/dev/null)
if [ -n "$OUT" ]; then
    echo "$OUT" > "$CACHE"
fi
