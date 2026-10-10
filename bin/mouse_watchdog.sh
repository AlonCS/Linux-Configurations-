#!/bin/bash
LOG="$HOME/.local/share/mouse_watchdog.log"
MAPPING="buttons(button1=button1; button2=button2; button3=button3; button4=F16; button5=F17; button6=dpi; button7=F18; button8=disabled; button9=F3; scrollup=scrollup; scrolldown=scrolldown; layout=qwerty)"

if lsusb | grep -q "1038:1852"; then
    OUT=$(rivalcfg --buttons "$MAPPING" 2>&1)
    if [ -z "$OUT" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] dongle present, mapping reapplied ok" >> "$LOG"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] dongle present, rivalcfg said: $OUT" >> "$LOG"
    fi
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] on bluetooth, skipped (rivalcfg needs the dongle)" >> "$LOG"
fi
