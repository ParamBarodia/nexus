"""Retrieve the current system clipboard content."""


def _clipboard_recall() -> str:
    """Return whatever is currently on the system clipboard."""
    # Try pyperclip
    try:
        import pyperclip
        content = pyperclip.paste()
        if content:
            return content
        return "(clipboard is empty)"
    except ImportError:
        pass

    # Fallback: ctypes on Windows
    try:
        import ctypes
        CF_UNICODETEXT = 13
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        if not user32.OpenClipboard(0):
            return "Error: could not open clipboard"

        try:
            handle = user32.GetClipboardData(CF_UNICODETEXT)
            if not handle:
                return "(clipboard is empty or contains non-text data)"
            kernel32.GlobalLock.restype = ctypes.c_wchar_p
            text = kernel32.GlobalLock(handle)
            kernel32.GlobalUnlock(handle)
            return text if text else "(clipboard is empty)"
        finally:
            user32.CloseClipboard()
    except Exception as e:
        return f"Error reading clipboard: {e}"


def get_tools() -> list:
    return [
        {
            "name": "clipboard_recall",
            "description": "Return the current content of the system clipboard.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            },
            "handler": _clipboard_recall
        }
    ]
