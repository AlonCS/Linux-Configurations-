#!/bin/bash
val=$(rivalcfg --battery-level 2>/dev/null | grep -oP '\d+(?=\s*%)')
if [ -n "$val" ]; then
  echo "$val"
  exit 0
fi
dev=$(upower -e 2>/dev/null | grep -i -E "mouse|aerox")
if [ -n "$dev" ]; then
  p=$(upower -i "$dev" 2>/dev/null | grep -oP 'percentage:\s+\K[0-9]+')
  echo "${p:-0}"
  exit 0
fi
echo 0
