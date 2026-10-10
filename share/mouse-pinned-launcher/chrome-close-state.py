#!/usr/bin/python3
"""Read Chrome's native dialogs. Never activate controls or inspect page content."""
import gi
from gi.repository import Gio, GLib


def chrome_close_state():
    try:
        session = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        address = session.call_sync('org.a11y.Bus', '/org/a11y/bus',
                                    'org.a11y.Bus', 'GetAddress', None, None,
                                    0, 500, None).unpack()[0]
        bus = Gio.DBusConnection.new_for_address_sync(
            address, Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT |
            Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION, None, None)

        def call(dest, path, method, args=None, interface='org.a11y.atspi.Accessible'):
            return bus.call_sync(dest, path, interface, method, args,
                                 None, 0, 300, None).unpack()[0]

        def name(dest, path):
            return call(dest, path, 'Get',
                        GLib.Variant('(ss)', ('org.a11y.atspi.Accessible', 'Name')),
                        'org.freedesktop.DBus.Properties')

        roots = call('org.a11y.atspi.Registry', '/org/a11y/atspi/accessible/root', 'GetChildren')
        found = False
        incomplete = False
        native_close = False
        seen = set()
        stack = [(d, p) for d, p in roots if 'chrome' in name(d, p).lower()]
        found = bool(stack)
        while stack:
            dest, path = stack.pop()
            if (dest, path) in seen:
                continue
            seen.add((dest, path))
            if len(seen) > 1500 or path.endswith('/null'):
                incomplete = True
                continue
            role = call(dest, path, 'GetRole')
            # Web documents do not contain Chrome's native before-unload dialog.
            if role == 95:
                continue
            if role in (2, 16):  # alert or dialog
                states = call(dest, path, 'GetState')
                if states[0] & (1 << 25):  # AT-SPI SHOWING
                    return 'blocked'
            if role == 43 and name(dest, path) == 'Close':
                native_close = True
            for child_dest, child_path in call(dest, path, 'GetChildren'):
                stack.append((child_dest or dest, child_path))
        return 'clear' if found and native_close and not incomplete else 'unknown'
    except Exception:
        return 'unknown'


if __name__ == '__main__':
    print(chrome_close_state())
