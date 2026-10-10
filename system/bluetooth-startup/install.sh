#!/bin/bash
set -euo pipefail
if [ "$(id -u)" -ne 0 ]; then
    exec sudo /bin/bash "$0"
fi
SOURCE_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
# Only these fixed files are installed; no sudoers or D-Bus policy is changed.
install -d -o root -g root -m 0755 /usr/local/libexec
install -o root -g root -m 0755 "$SOURCE_DIR/conky-bt-supervisor.py" /usr/local/libexec/conky-bt-supervisor.py
install -o root -g root -m 0644 "$SOURCE_DIR/conky-bt-status.py" /usr/local/libexec/conky-bt-status.py
install -o root -g root -m 0644 "$SOURCE_DIR/conky-bluetooth-status.service" /etc/systemd/system/conky-bluetooth-status.service
systemctl daemon-reload
systemctl enable conky-bluetooth-status.service
systemctl restart conky-bluetooth-status.service
systemctl --no-pager --full status conky-bluetooth-status.service
