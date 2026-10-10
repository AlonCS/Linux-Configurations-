#!/usr/bin/env python3
"""Hold an X11 mouse-generated key to show GNOME favorites at the pointer's monitor center."""
import ctypes
import fcntl
import os
import subprocess
import sys
from pathlib import Path

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, Gio, GLib, Gtk

SWITCHER = '--switcher' in sys.argv
EXTERNAL_CLICKS = '--external-clicks' in sys.argv
KEYCODE = int(os.environ.get('MOUSE_LAUNCHER_KEYCODE', '195' if SWITCHER else '194'))
PREVIEW = '--preview' in sys.argv
if not 8 <= KEYCODE <= 255:
    raise SystemExit('Keycode must be between 8 and 255.')
lock = open(Path(os.environ.get('XDG_RUNTIME_DIR', '/tmp')) / 'lonzo-mouse-launcher.lock', 'w')
try:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    raise SystemExit(0)

x11 = ctypes.CDLL('libX11.so.6')
x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
x11.XOpenDisplay.restype = ctypes.c_void_p
x11.XQueryKeymap.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
display = x11.XOpenDisplay(None)
if not display:
    raise SystemExit('This launcher requires an X11 desktop session.')

def held():
    state = ctypes.create_string_buffer(32)
    x11.XQueryKeymap(display, state)
    return bool(state.raw[KEYCODE // 8] & (1 << (KEYCODE % 8)))

if not SWITCHER and not PREVIEW and not held():
    x11.XCloseDisplay(display)
    raise SystemExit(0)

settings = Gio.Settings.new('org.gnome.shell')
apps = [Gio.DesktopAppInfo.new(appid) for appid in (
    'google-chrome.desktop', 'terminator.desktop', 'com.anthropic.Claude.desktop',
    'chatgpt.desktop', 'obsidian_obsidian.desktop',
)]
apps = [app for app in apps if app]
if not apps:
    x11.XCloseDisplay(display)
    raise SystemExit('No pinned applications found.')

window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
window.set_title('Pinned apps')
window.set_wmclass('mouse-pinned-launcher', 'MousePinnedLauncher')
window.set_decorated(False)
window.set_resizable(False)
window.set_keep_above(True)
window.set_skip_taskbar_hint(True)
window.set_skip_pager_hint(True)
window.set_accept_focus(False)
window.set_type_hint(Gdk.WindowTypeHint.UTILITY)
window.set_border_width(10)
window.get_style_context().add_class('mouse-launcher')
css = Gtk.CssProvider()
css.load_from_data(b'''
.mouse-launcher { background: #303030; color: #eeeeee; border: 1px solid #454545; border-radius: 10px; }
.mouse-launcher button { background: transparent; border: none; box-shadow: none; border-radius: 4px; padding: 12px 8px; color: #eeeeee; }
.mouse-launcher button:hover, .mouse-launcher button.selected { background: #515151; }
.mouse-launcher label { color: #eeeeee; font-size: 12px; }
''')
Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
gdk_display = Gdk.Display.get_default()
pointer = gdk_display.get_default_seat().get_pointer()
_, px, py = pointer.get_position()
monitor = gdk_display.get_monitor_at_point(px, py)
area = monitor.get_workarea()
tile_size = max(48, min(112, (area.width - 64) // len(apps) - 4))
icon_size = max(24, min(72, tile_size - 28))
layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
window.add(layout)
grid = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
layout.pack_start(grid, False, False, 0)
status = Gtk.Label()
status.set_no_show_all(True)
layout.pack_start(status, False, False, 0)

def new_window_action(app):
    for action in ('new-window', 'new-empty-window', 'NewWindow'):
        if action in app.list_actions():
            return action
    return None

launched = False
def launch(button, app):
    global launched
    if launched:
        return
    try:
        context = Gdk.Display.get_default().get_app_launch_context()
        context.set_timestamp(Gtk.get_current_event_time())
        action = new_window_action(app)
        # CHROME ALONZO48 PROFILE
        if app.get_id() == 'google-chrome.desktop':
            subprocess.Popen(['/usr/bin/google-chrome-stable', '--profile-directory=Default', '--new-window'], start_new_session=True)
        elif action:
            app.launch_action(action, context)
        elif app.get_id() in ('chatgpt.desktop', 'codex.desktop'):
            helper = Path(__file__).with_name('codex-new-window.py')
            subprocess.Popen([sys.executable, str(helper)], start_new_session=True)
        elif app.get_id() == 'com.anthropic.Claude.desktop':
            # Claude Desktop is single-window; launch a second isolated profile for a real separate window.
            subprocess.Popen(['claude-desktop', '--user-data-dir=/home/lonzo/.config/Claude2'], start_new_session=True)
        elif app.get_id() == 'terminator.desktop':
            subprocess.Popen(['terminator', '--no-dbus'], start_new_session=True)
        else:
            app.launch([], context)
        launched = True
        window.hide()
    except (GLib.Error, OSError) as exc:
        status.set_text('Could not launch: ' + str(exc))
        status.show()

buttons = []
selected = 0
shown = False
def select(button, event, app):
    if SWITCHER:
        return False
    for other in buttons:
        other.get_style_context().remove_class('selected')
    button.get_style_context().add_class('selected')
    return False

for index, app in enumerate(apps):
    button = Gtk.Button()
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
    icon = app.get_icon()
    image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.DIALOG) if icon else Gtk.Image.new_from_icon_name('application-x-executable', Gtk.IconSize.DIALOG)
    image.set_pixel_size(icon_size)
    box.pack_start(image, False, False, 0)
    label = Gtk.Label(label=app.get_display_name())
    label.set_width_chars(max(5, tile_size // 8))
    label.set_max_width_chars(max(5, tile_size // 8))
    label.set_ellipsize(3)
    box.pack_start(label, False, False, 0)
    button.add(box)
    button.set_size_request(tile_size, icon_size + 52)
    supports_new = new_window_action(app) or app.get_id() == 'terminator.desktop'
    button.set_tooltip_text(('New window: ' if supports_new else 'Open app (window behavior depends on app): ') + app.get_display_name())
    button.connect('clicked', launch, app)
    button.connect('enter-notify-event', select, app)
    buttons.append(button)
    if index == 0:
        button.get_style_context().add_class('selected')
    grid.pack_start(button, False, False, 0)

window.connect('destroy', lambda *_: Gtk.main_quit())
if not SWITCHER:
    window.show_all()
_, natural = window.get_preferred_size()
def center():
    _, natural = window.get_preferred_size()
    window.move(area.x + (area.width - natural.width) // 2,
                area.y + (area.height - natural.height) // 2)
center()

# A passive right-button grab intercepts only right clicks during a disable hold.
# Other mouse buttons and motion remain normal while the performance overlay shows.
if SWITCHER:
    x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
    x11.XDefaultRootWindow.restype = ctypes.c_ulong
    x11.XGrabButton.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint,
        ctypes.c_ulong, ctypes.c_int, ctypes.c_uint, ctypes.c_int, ctypes.c_int,
        ctypes.c_ulong, ctypes.c_ulong]
    x11.XUngrabButton.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_ulong]
    x11.XUngrabPointer.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    x11.XFlush.argtypes = [ctypes.c_void_p]
    x11.XPending.argtypes = [ctypes.c_void_p]
    x11.XNextEvent.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    # OUTSIDE CLICK CANCELLATION
    class XButtonEvent(ctypes.Structure):
        _fields_ = [('type', ctypes.c_int), ('serial', ctypes.c_ulong),
            ('send_event', ctypes.c_int), ('display', ctypes.c_void_p),
            ('window', ctypes.c_ulong), ('root', ctypes.c_ulong),
            ('subwindow', ctypes.c_ulong), ('time', ctypes.c_ulong),
            ('x', ctypes.c_int), ('y', ctypes.c_int),
            ('x_root', ctypes.c_int), ('y_root', ctypes.c_int),
            ('state', ctypes.c_uint), ('button', ctypes.c_uint),
            ('same_screen', ctypes.c_int)]
    cancelled = False
    root = x11.XDefaultRootWindow(display)
    # Right clicks are captured immediately by mouseenter and sent over stdin.
    x11.XFlush(display)

    def cycle():
        global shown, selected
        if not shown:
            shown = True
            if '--overlay-pid' in sys.argv:
                import signal
                try:
                    os.kill(int(sys.argv[sys.argv.index('--overlay-pid') + 1]), signal.SIGTERM)
                except (ProcessLookupError, ValueError):
                    pass
            window.show_all()
            center()
            # Grab left clicks only after the middle dock appears.
            if not EXTERNAL_CLICKS:
                x11.XGrabButton(display, 1, 1 << 15, root, False,
                    (1 << 2) | (1 << 3), 1, 1, 0, 0)
            x11.XFlush(display)
        else:
            selected = (selected + 1) % len(apps)
        for index, button in enumerate(buttons):
            context = button.get_style_context()
            if index == selected:
                context.add_class('selected')
            else:
                context.remove_class('selected')

    def release_grab():
        x11.XUngrabButton(display, 1, 1 << 15, root)
        x11.XUngrabButton(display, 3, 1 << 15, root)
        x11.XUngrabPointer(display, 0)
        x11.XFlush(display)

    def left_click(event):
        global cancelled
        if not shown:
            return True
        wx, wy = window.get_position()
        width, height = window.get_size()
        if not (wx <= event.x_root < wx + width and wy <= event.y_root < wy + height):
            cancelled = True
            release_grab()
            window.hide()
            Gtk.main_quit()
            return False
        for index, button in enumerate(buttons):
            point = button.translate_coordinates(window, 0, 0)
            if point is None:
                continue
            bx, by = point
            allocation = button.get_allocation()
            if (wx + bx <= event.x_root < wx + bx + allocation.width and
                    wy + by <= event.y_root < wy + by + allocation.height):
                release_grab()
                launch(button, apps[index])
                Gtk.main_quit()
                return False
        return True

    control_buffer = ''
    def control(source, condition):
        global control_buffer
        data = os.read(sys.stdin.fileno(), 4096)
        if not data:
            release_grab()
            Gtk.main_quit()
            return False
        control_buffer += data.decode()
        while '\n' in control_buffer:
            message, control_buffer = control_buffer.split('\n', 1)
            if message == 'next':
                if not cancelled:
                    cycle()
            elif EXTERNAL_CLICKS and message.startswith('click '):
                try:
                    _, cx, cy = message.split()
                    click = XButtonEvent()
                    click.x_root, click.y_root = int(cx), int(cy)
                except ValueError:
                    continue
                if not left_click(click):
                    return False
            elif message in ('commit', 'cancel'):
                poll()
                release_grab()
                if message == 'commit' and shown and not cancelled:
                    launch(buttons[selected], apps[selected])
                Gtk.main_quit()
                return False
        return True

    GLib.io_add_watch(sys.stdin, GLib.IO_IN | GLib.IO_HUP, control)

def poll():
    if SWITCHER:
        # XEvent is a union of 24 native longs; its first field is the event type.
        event = (ctypes.c_long * 24)()
        while x11.XPending(display):
            x11.XNextEvent(display, ctypes.byref(event))
            if ctypes.cast(ctypes.byref(event), ctypes.POINTER(ctypes.c_int))[0] == 4:
                click = ctypes.cast(ctypes.byref(event), ctypes.POINTER(XButtonEvent)).contents
                if click.button == 3:
                    cycle()
                elif click.button == 1 and not left_click(click):
                    return False
        return True
    if not PREVIEW and not held():
        Gtk.main_quit()
        return False
    return True

GLib.timeout_add(25, poll)
if PREVIEW:
    GLib.timeout_add_seconds(20, lambda: (Gtk.main_quit(), False)[1])
try:
    Gtk.main()
finally:
    if SWITCHER:
        release_grab()
    window.destroy()
    x11.XCloseDisplay(display)
