#!/usr/bin/python3
"""Track BlueZ connection requests, including requests from Settings."""
import os
import sys
from pathlib import Path
import re
import subprocess
import time

CACHE = Path.home() / '.cache'
CACHE.mkdir(exist_ok=True)
active = {}

def refresh_overlay():
    (CACHE / 'conky_bt_dirty').touch()
    subprocess.Popen(['/home/lonzo/.config/conky/bt_section_cached.sh'],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def process(header):
    if header.startswith('method call'):
        action = re.search(r'member=(Connect|Disconnect)(?:\s|$)', header)
        device = re.search(r'path=/org/bluez/[^; ]*/dev_([0-9A-Fa-f_]{17})(?:;|\s)', header)
        sender = re.search(r'sender=([^ ]+)', header)
        serial = re.search(r'\bserial=(\d+)', header)
        if not all((action, device, sender, serial)):
            return
        mac = device.group(1).replace('_', ':').upper()
        state = 'connecting' if action.group(1) == 'Connect' else 'disconnecting'
        path = CACHE / ('conky_bt_pending_' + mac.replace(':', ''))
        stamp = f'{state}\t{int(time.time())}\n'
        tmp = path.with_name(path.name + '.monitor-tmp')
        tmp.write_text(stamp)
        os.replace(tmp, path)
        active[(sender.group(1), serial.group(1))] = (path, stamp, time.monotonic())
        refresh_overlay()
    elif header.startswith(('method return', 'error')):
        destination = re.search(r'destination=([^ ]+)', header)
        serial = re.search(r'reply_serial=(\d+)', header)
        if destination and serial:
            item = active.pop((destination.group(1), serial.group(1)), None)
            if item:
                path, stamp, _ = item
                if path.exists() and path.read_text() == stamp:
                    if header.startswith('error'):
                        tmp = path.with_name(path.name + '.monitor-tmp')
                        tmp.write_text(f'failed\t{int(time.time())}\n')
                        os.replace(tmp, path)
                    else:
                        path.unlink()
                refresh_overlay()

if __name__ == '__main__':
    matches = [
        "type='method_call',interface='org.bluez.Device1',member='Connect'",
        "type='method_call',interface='org.bluez.Device1',member='Disconnect'",
        "type='method_return',sender='org.bluez'",
        "type='error',sender='org.bluez'",
    ]
    process_handle = None
    if '--stdin' in sys.argv:
        stream = sys.stdin
    else:
        process_handle = subprocess.Popen(['dbus-monitor', '--system', *matches],
                                          stdout=subprocess.PIPE, text=True, bufsize=1)
        stream = process_handle.stdout
    try:
        for line in stream:
            if line.startswith(('method call', 'method return', 'error')):
                process(line.strip())
    finally:
        if process_handle is not None:
            process_handle.terminate()
