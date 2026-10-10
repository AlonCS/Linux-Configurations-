#!/bin/bash
exec 7>"$HOME/.cache/airpods_max_update.sh.lock"
flock -n 7 || exit 0
CACHE="$HOME/.cache/airpods_max_battery.json"
OUT=$(timeout 10 ~/bin/airpods --json --mac 70:F9:4A:91:B0:BE 2>/dev/null)
[ -n "$OUT" ] && echo "$OUT" > "$CACHE"
