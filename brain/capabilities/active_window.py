"""Retrieve the currently active (foreground) window title and process."""

import json


def _active_window() -> str:
    """Return the title and process name of the active window."""
    # Try pygetwindow first
    try:
        import pygetwindow as gw
        win = gw.getActiveWindow()
        if win:
            title = win.title or "(untitled)"
            # Try to get process name via psutil + win32
            pid = _get_foreground_pid()
            proc_name = _pid_to_name(pid) if pid else "unknown"
            return json.dumps({"title": title, "process": proc_name, "pid": pid})
        return json.dumps({"title": "(no active window)", "process": "unknown", "pid": None})
    except ImportError:
        pass

    # Fallback: ctypes on Windows
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value or "(untitled)"
        pid = _get_foreground_pid()
        proc_name = _pid_to_name(pid) if pid else "unknown"
        return json.dumps({"title": title, "process": proc_name, "pid": pid})
    except Exception as e:
        return f"Error getting active window: {e}"


def _get_foreground_pid() -> int | None:
    """Get the PID of the foreground window using ctypes."""
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return pid.value
    except Exception:
        return None


def _pid_to_name(pid: int) -> str:
    """Resolve a PID to a process name."""
    try:
        import psutil
        proc = psutil.Process(pid)
        return proc.name()
    except Exception:
        return "unknown"


def get_tools() -> list:
    return [
        {
            "name": "active_window",
            "description": "Return the title and process name of the currently active (foreground) window.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            },
            "handler": _active_window
        }
    ]
