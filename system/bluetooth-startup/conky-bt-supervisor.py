#!/usr/bin/python3
"""Run only the Bluetooth monitor as root; drop privileges for its parser."""
import signal
import subprocess
import time

def stop(signum, frame):
    raise SystemExit(0)

for sig in (signal.SIGTERM, signal.SIGINT):
    signal.signal(sig, stop)

monitor = parser = None
try:
    matches = [
        "type='method_call',interface='org.bluez.Device1',member='Connect'",
        "type='method_call',interface='org.bluez.Device1',member='Disconnect'",
        "type='method_return',sender='org.bluez'",
        "type='error',sender='org.bluez'",
    ]
    monitor = subprocess.Popen(['/usr/bin/stdbuf', '-oL', '/usr/bin/dbus-monitor',
                                '--system', *matches], stdout=subprocess.PIPE)
    parser = subprocess.Popen(['/usr/bin/setpriv', '--reuid=1000', '--regid=1000',
                               '--init-groups', '--reset-env', '--inh-caps=-all', '--ambient-caps=-all', '/usr/bin/python3',
                               '/usr/local/libexec/conky-bt-status.py', '--stdin'],
                              stdin=monitor.stdout)
    monitor.stdout.close()
    while monitor.poll() is None and parser.poll() is None:
        time.sleep(0.5)
    raise SystemExit(1)
finally:
    for child in (parser, monitor):
        if child is not None and child.poll() is None:
            child.terminate()
    for child in (parser, monitor):
        if child is not None:
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
