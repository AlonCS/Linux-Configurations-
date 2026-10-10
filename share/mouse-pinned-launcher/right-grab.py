"""Capture right clicks during a disable-button hold before any GTK startup."""
import ctypes
x = ctypes.CDLL('libX11.so.6')
x.XOpenDisplay.argtypes=[ctypes.c_char_p]; x.XOpenDisplay.restype=ctypes.c_void_p
x.XDefaultRootWindow.argtypes=[ctypes.c_void_p]; x.XDefaultRootWindow.restype=ctypes.c_ulong
x.XGrabButton.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_uint,ctypes.c_ulong,ctypes.c_int,ctypes.c_uint,ctypes.c_int,ctypes.c_int,ctypes.c_ulong,ctypes.c_ulong]
x.XUngrabButton.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_uint,ctypes.c_ulong]
x.XUngrabPointer.argtypes=[ctypes.c_void_p,ctypes.c_ulong]
x.XSync.argtypes=[ctypes.c_void_p,ctypes.c_int]
display=x.XOpenDisplay(None)
if not display: raise RuntimeError('Mouse right-click capture requires X11.')
root=x.XDefaultRootWindow(display)
x.XQueryPointer.argtypes=[ctypes.c_void_p,ctypes.c_ulong,
    ctypes.POINTER(ctypes.c_ulong),ctypes.POINTER(ctypes.c_ulong),
    ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_uint)]
def pointer_position():
    root_return, child = ctypes.c_ulong(), ctypes.c_ulong()
    rx, ry, wx, wy = (ctypes.c_int() for _ in range(4))
    mask = ctypes.c_uint()
    if not x.XQueryPointer(display,root,ctypes.byref(root_return),ctypes.byref(child),
            ctypes.byref(rx),ctypes.byref(ry),ctypes.byref(wx),ctypes.byref(wy),ctypes.byref(mask)):
        return None
    return rx.value, ry.value

def set_left(enabled):
    if enabled:
        x.XGrabButton(display,1,1<<15,root,False,(1<<2)|(1<<3),1,1,0,0)
    else:
        x.XUngrabButton(display,1,1<<15,root)
    x.XSync(display,True)

def set_grab(enabled):
    set_left(enabled)
    if enabled:
        x.XGrabButton(display,3,1<<15,root,False,(1<<2)|(1<<3),1,1,0,0)
    else:
        x.XUngrabButton(display,3,1<<15,root)
        x.XUngrabPointer(display,0)
    x.XSync(display,True)


def set_middle(enabled):
    # Capture native wheel clicks only during a Button 9 hold.
    if enabled:
        x.XGrabButton(display,2,1<<15,root,False,(1<<2)|(1<<3),1,1,0,0)
    else:
        x.XUngrabButton(display,2,1<<15,root)
    x.XSync(display,True)
