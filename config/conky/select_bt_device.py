#!/usr/bin/python3
"""Open a named Bluetooth row without tabbing through Settings categories."""
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import gi
from PIL import Image

gi.require_version("Atspi", "2.0")
from gi.repository import Atspi


def descendants(node, depth=0):
    if depth > 35:
        return
    yield node
    try:
        count = node.get_child_count()
    except Exception:
        return
    for index in range(count):
        try:
            yield from descendants(node.get_child_at_index(index), depth + 1)
        except Exception:
            continue


def settings():
    desktop = Atspi.get_desktop(0)
    for index in range(desktop.get_child_count()):
        try:
            app = desktop.get_child_at_index(index)
            if app.get_name() == "gnome-control-center":
                yield app
        except Exception:
            continue


def locate_list(image, height):
    """Find the device card's repeated row separators in the current window."""
    image = image.convert("RGB")
    # These columns are within the content panel, away from the category sidebar.
    for fraction in (0.65, 0.60, 0.70):
        x = int(image.width * fraction)
        runs = []
        start = 0
        previous = image.getpixel((x, 0))
        for y in range(1, image.height):
            colour = image.getpixel((x, y))
            if colour != previous:
                if height * 0.8 <= y - start <= height * 1.2:
                    runs.append((start, y, previous))
                start, previous = y, colour
        for i in range(len(runs) - 2):
            a, b, c = runs[i:i + 3]
            if a[2] == b[2] == c[2] and abs(b[0] - a[0] - height) <= 2 and abs(c[0] - b[0] - height) <= 2:
                return x, a[0]
    raise RuntimeError("Cannot identify Bluetooth device card; leaving the list open")


def main(name, window):
    # Escape dismisses a previous device dialog; no Tab/arrow navigation is used.
    subprocess.run(["xdotool", "windowactivate", "--sync", window,
                    "key", "--clearmodifiers", "Escape"], check=True)
    deadline = time.monotonic() + 8
    with tempfile.TemporaryDirectory(prefix="conky-bt-") as directory:
        screenshot = str(Path(directory) / "settings.png")
        while time.monotonic() < deadline:
            try:
                for app in settings():
                    for node in descendants(app):
                        if node.get_role() != Atspi.Role.LIST or node.get_name() != "Devices":
                            continue
                        rows = [node.get_child_at_index(i) for i in range(node.get_child_count())]
                        names = [row.get_name() for row in rows]
                        if name not in names:
                            continue
                        index = names.index(name)
                        heights = [row.get_extents(Atspi.CoordType.SCREEN).height for row in rows]
                        if any(h <= 0 for h in heights[:index + 1]):
                            raise RuntimeError("Invalid Bluetooth row sizes")
                        subprocess.run(["import", "-window", window, screenshot], check=True)
                        with Image.open(screenshot) as image:
                            x, top = locate_list(image, heights[0])
                            y = round(top + sum(heights[:index]) + heights[index] / 2)
                            if y >= image.height - 60:
                                raise RuntimeError("Requested device is outside the visible list")
                        # Abort if scanning reordered the device list while capturing.
                        node.clear_cache()
                        latest = [node.get_child_at_index(i).get_name() for i in range(node.get_child_count())]
                        if latest != names:
                            continue
                        print(f"Click Bluetooth row: {name}; window position {x},{y}", flush=True)
                        subprocess.run(["xdotool", "windowactivate", "--sync", window,
                                        "windowraise", window, "mousemove", "--sync",
                                        "--window", window, str(x), str(y), "click", "1"], check=True)
                        verify_until = time.monotonic() + 2
                        while time.monotonic() < verify_until:
                            labels = set()
                            for control in descendants(app):
                                try:
                                    control.clear_cache()
                                    labels.add(control.get_name())
                                except Exception:
                                    continue
                            if name in labels and "Connection" in labels:
                                print("Opened Bluetooth details: " + name)
                                return 0
                            time.sleep(0.1)
                        print("Device click sent; details need real-click confirmation", file=sys.stderr)
                        return 1
            except Exception as error:
                print(str(error), file=sys.stderr)
            time.sleep(0.1)
    print("Could not locate Bluetooth device: " + name, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
