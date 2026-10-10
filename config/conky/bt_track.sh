#!/bin/bash
LOG="$HOME/.cache/bt_last_connected.tsv"
touch "$LOG"
NOW=$(date +%s)
mapfile -t CONNECTED < <(LC_ALL=C bluetoothctl devices Connected 2>/dev/null | grep -E '^Device ([[:xdigit:]]{2}:){5}[[:xdigit:]]{2} ' | awk '{print $2}')

declare -A TS
while IFS=$'\t' read -r mac ts; do
    [ -n "$mac" ] && TS["$mac"]="$ts"
done < "$LOG"

for mac in "${CONNECTED[@]}"; do
    TS["$mac"]="$NOW"
done

> "$LOG"
for mac in "${!TS[@]}"; do
    echo -e "${mac}\t${TS[$mac]}" >> "$LOG"
done
