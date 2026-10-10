#!/bin/bash
set -euo pipefail
if [ "$(id -u)" -ne 0 ]; then
    exec sudo /bin/bash "$0"
fi
systemctl disable --now conky-bluetooth-status.service
rm -f /etc/systemd/system/conky-bluetooth-status.service /usr/local/libexec/conky-bt-supervisor.py /usr/local/libexec/conky-bt-status.py
systemctl daemon-reload
printf 'Automatic Bluetooth monitor removed. Mouse shortcuts are unchanged.\n'
