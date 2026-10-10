#!/bin/bash
AEROX_MAC="EE:E1:B5:4B:9A:28"
AIRPODS_PRO_MAC="41:42:6B:6B:10:D1"
AIRPODS_MAX_MAC="70:F9:4A:91:B0:BE"
LOG="$HOME/.cache/bt_last_connected.tsv"

declare -A TS
if [ -f "$LOG" ]; then
    while IFS=$'\t' read -r mac ts; do
        [ -n "$mac" ] && TS["$mac"]="$ts"
    done < "$LOG"
fi

row_colors() {
    if [ "$1" = "1" ]; then echo "D8DEE9 AAB8AD"; else echo "65717E 65717E"; fi
}

# Lua evaluates these colours on every redraw; Bluetooth is still polled every 15s.
color_tag() {
    if [ -n "${ROW_Y0:-}" ]; then
        printf '${lua_parse bt_row_color %s %s %s}' "$ROW_Y0" "$ROW_Y1" "$1"
    else
        printf '${color %s}' "$1"
    fi
}

status_tag() {
    local state stamp status colour
    status="disconnected"; colour="74808D"
    [ "$1" = "1" ] && { status="connected"; colour="8B969F"; }
    if IFS=$'\t' read -r state stamp 2>/dev/null < "$HOME/.cache/conky_bt_pending_${ROW_MAC//:/}"; then
        if [[ "$stamp" =~ ^[0-9]+$ ]] && [ "$(( $(date +%s) - stamp ))" -lt 60 ]; then
            case "$state" in
                connecting|disconnecting) status="${state}…"; colour="B3BDC7" ;;
                failed) if [ "$(( $(date +%s) - stamp ))" -lt 4 ]; then status="failed"; colour="D99B94"; fi ;;
            esac
        fi
    fi
    printf ' ${font DejaVu Sans:size=9}${color %s}• %s${font}' "$colour" "$status"
}

render_simple() {
    local name="$1" conn="$2" pct="$3"
    read -r LBLCOLOR VALCOLOR <<< "$(row_colors "$conn")"
    if [ -n "$pct" ]; then
        echo "$(color_tag "$LBLCOLOR")${name}$(status_tag "$conn")\${alignr}$(color_tag "$VALCOLOR")${pct}%\${color}"
        echo "$(color_tag "$VALCOLOR")\${execbar echo ${pct%% *}}\${color}"
    else
        echo "$(color_tag "$LBLCOLOR")${name}$(status_tag "$conn")\${color}"
    fi
}

cache_stale() {
    local f="$1" max_age="$2"
    [ ! -f "$f" ] && return 0
    local age=$(( $(date +%s) - $(stat -c %Y "$f" 2>/dev/null || echo 0) ))
    [ "$age" -ge "$max_age" ]
}

render_airpods_pro() {
    local conn="$1" name="$2"
    if [ "$conn" != "1" ]; then
        render_simple "$name" 0 ""
        return
    fi
    echo "$(color_tag D8DEE9)${name}$(status_tag "$conn")\${color}"
    local CACHE="$HOME/.cache/airpods_battery.json"
    cache_stale "$CACHE" 60 && ~/.config/conky/airpods_update.sh >/dev/null 2>&1 &
    for pair in "left:airpods l" "right:airpods r" "case:case"; do
        FIELD="${pair%%:*}"; LABEL="${pair##*:}"
        INFO=$(python3 -c "
import json
try:
    with open('$CACHE') as f:
        d = json.load(f)
    b = d['battery']['$FIELD']
    print(b.get('level', 0), b.get('status', 'unknown'), b.get('available', False))
except Exception:
    print(0, 'unknown', False)
")
        LEVEL=$(echo "$INFO" | awk '{print $1}')
        STATUS=$(echo "$INFO" | awk '{print $2}')
        AVAIL=$(echo "$INFO" | awk '{print $3}')
        CONN2=0; [ "$AVAIL" = "True" ] && CONN2=1
        read -r LBLCOLOR VALCOLOR <<< "$(row_colors "$CONN2")"
        BOLT=""; [ "$STATUS" = "charging" ] && BOLT=" ⚡"
        echo "$(color_tag "$LBLCOLOR")${LABEL}\${alignr}$(color_tag "$VALCOLOR")${LEVEL}%${BOLT}\${color}"
        echo "$(color_tag "$VALCOLOR")\${execbar echo ${LEVEL}}\${color}"
        [ "$FIELD" != "case" ] && echo '${voffset 6}'
    done
}

render_airpods_max() {
    local conn="$1" name="$2"
    if [ "$conn" != "1" ]; then
        render_simple "$name" 0 ""
        return
    fi
    local CACHE="$HOME/.cache/airpods_max_battery.json"
    cache_stale "$CACHE" 60 && ~/.config/conky/airpods_max_update.sh >/dev/null 2>&1 &
    INFO=$(python3 -c "
import json
try:
    with open('$CACHE') as f:
        d = json.load(f)
    b = d['battery']['single']
    print(b.get('level', 0), b.get('status', 'unknown'))
except Exception:
    print(0, 'unknown')
")
    LEVEL=$(echo "$INFO" | awk '{print $1}')
    STATUS=$(echo "$INFO" | awk '{print $2}')
    BOLT=""; [ "$STATUS" = "charging" ] && BOLT=" ⚡"
    render_simple "$name" 1 "${LEVEL}${BOLT}"
}

render_mouse() {
    local conn="$1" name="$2"
    if [ "$conn" != "1" ]; then
        render_simple "$name" 0 ""
        return
    fi
    LEVEL=$(~/.config/conky/mouse_battery.sh)
    RAW=$(rivalcfg --battery-level 2>/dev/null)
    CHARGE=""; echo "$RAW" | grep -qi "^charging" && CHARGE=" ⚡"
    render_simple "$name" "$conn" "${LEVEL}${CHARGE}"
}

render_generic() {
    local mac="$1" name="$2" conn="$3"
    if [ "$conn" != "1" ]; then
        render_simple "$name" 0 ""
        return
    fi
    local dev=$(upower -e 2>/dev/null | grep -i "$(echo "$mac" | tr 'A-F' 'a-f' | tr ':' '_')")
    local pct=""
    [ -n "$dev" ] && pct=$(upower -i "$dev" 2>/dev/null | grep -oP 'percentage:\s+\K[0-9]+')
    render_simple "$name" "$conn" "$pct"
}

# Build the full device list with connection + recency (paired devices only,
# not transient entries seen while Settings had a scan running)
if [ -n "${CONKY_BT_SNAPSHOT:-}" ]; then
    mapfile -t ALL < "$CONKY_BT_SNAPSHOT"
else
    SNAPSHOT=$(mktemp /tmp/conky_bt_snapshot.XXXXXX)
    /usr/bin/python3 /home/lonzo/.config/conky/bt_snapshot.py > "$SNAPSHOT" || { rm -f "$SNAPSHOT"; exit 1; }
    mapfile -t ALL < "$SNAPSHOT"
    rm -f "$SNAPSHOT"
fi
connected=()
disconnected=()
for line in "${ALL[@]}"; do
    IFS='|' read -r mac name conn pending_state <<< "$line"
    if [ "$conn" = "1" ]; then
        connected+=("$mac|$name")
    else
        ts="${TS[$mac]:-0}"
        disconnected+=("$ts|$mac|$name")
    fi
done

render_by_mac() {
    local mac="$1" name="$2" conn="$3"
    ROW_CONNECTED="$conn"
    ROW_MAC="$mac"
    case "$mac" in
        "$AEROX_MAC") render_mouse "$conn" "$name" ;;
        "$AIRPODS_PRO_MAC") render_airpods_pro "$conn" "$name" ;;
        "$AIRPODS_MAX_MAC") render_airpods_max "$conn" "$name" ;;
        *) render_generic "$mac" "$name" "$conn" ;;
    esac
}

# --- Layout map for click-to-device (window-relative y, calibrated by measurement) ---
LAYOUT_MAP="${CONKY_BT_LAYOUT_MAP:-/tmp/conky_bt_layout.tsv}"
LAYOUT_TMP=$(mktemp /tmp/conky_bt_layout.XXXXXX)
trap 'rm -f "$LAYOUT_TMP"' EXIT
Y_CURSOR="${CONKY_BT_ROW_START:-538}"          # top of first device row (just below BLUETOOTH header)
CONN_H=77             # connected device: label + bar
DISC_H=55             # disconnected device: label only
PRO_CONN_H=249        # AirPods Pro connected: 3 sub-rows (l / r / case)

dev_height() {
    local mac="$1" conn="$2"
    if [ "$conn" = "1" ]; then
        if [ "$mac" = "$AIRPODS_PRO_MAC" ]; then echo "$PRO_CONN_H"; else echo "$CONN_H"; fi
    else
        echo "$DISC_H"
    fi
}

emit_map() {
    local name="$1" h="$2" mac="$3" conn="$4"
    ROW_Y0="$Y_CURSOR"
    ROW_Y1=$((Y_CURSOR + h))
    local status_x0 status_x1 name_x1
    read -r status_x0 status_x1 name_x1 < <(/usr/bin/python3 /home/lonzo/.config/conky/bt_click_widths.py "$name" "$conn")
    printf '%d\t%d\t%s\t%s\t%s\t%d\t%d\t%d\n' "$ROW_Y0" "$ROW_Y1" "$name" "$mac" "$conn" "$status_x0" "$status_x1" "$name_x1" >> "$LAYOUT_TMP"
    Y_CURSOR=$((Y_CURSOR + h))
}

first=1
for entry in "${connected[@]}"; do
    IFS='|' read -r mac name <<< "$entry"
    [ $first -eq 0 ] && echo '${voffset 6}'
    emit_map "$name" "$(dev_height "$mac" 1)" "$mac" 1
    render_by_mac "$mac" "$name" 1
    first=0
done

sorted=$(printf '%s\n' "${disconnected[@]}" | sort -t'|' -k1,1 -rn)
while IFS='|' read -r ts mac name; do
    [ -z "$mac" ] && continue
    [ $first -eq 0 ] && echo '${voffset 6}'
    emit_map "$name" "$(dev_height "$mac" 0)" "$mac" 0
    render_by_mac "$mac" "$name" 0
    first=0
done <<< "$sorted"

# Publish the complete map together, avoiding partial hover/click regions.
mv "$LAYOUT_TMP" "$LAYOUT_MAP"
