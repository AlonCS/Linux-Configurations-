#!/usr/bin/python3
"""Read only paired device aliases and live Connected properties from BlueZ."""
import sys
import time
from pathlib import Path
import gi

gi.require_version('Gio', '2.0')
from gi.repository import Gio
try:
    bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
    reply = bus.call_sync('org.bluez', '/', 'org.freedesktop.DBus.ObjectManager',
                          'GetManagedObjects', None, None,
                          Gio.DBusCallFlags.NONE, 2500, None)
    objects = reply.unpack()[0]
    for path, interfaces in sorted(objects.items()):
        device = interfaces.get('org.bluez.Device1', {})
        if not device.get('Paired', False):
            continue
        mac = device.get('Address', '')
        name = str(device.get('Alias') or device.get('Name') or mac)
        name = name.replace('|', ' ').replace('\n', ' ').replace('\t', ' ')
        pending = ''
        try:
            state, stamp = (Path.home() / '.cache' / ('conky_bt_pending_' + mac.replace(':', ''))).read_text().strip().split('\t')
            if state in ('connecting', 'disconnecting', 'failed') and time.time() - int(stamp) < (4 if state == 'failed' else 60):
                pending = state
        except (OSError, ValueError):
            pass
        print(f"{mac}|{name}|{int(bool(device.get('Connected', False)))}|{pending}")
except Exception as error:
    print(f'BlueZ snapshot failed: {error}', file=sys.stderr)
    sys.exit(1)
