"""System controls for volume and screen brightness."""

import json


def _volume_set(level: int = 50) -> str:
    """Set the system master volume to a percentage (0-100).

    Args:
        level: Volume percentage (0-100).
    """
    level = max(0, min(100, int(level)))

    # Try pycaw (Windows Core Audio)
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))

        # SetMasterVolumeLevelScalar takes 0.0 - 1.0
        volume.SetMasterVolumeLevelScalar(level / 100.0, None)
        current = round(volume.GetMasterVolumeLevelScalar() * 100)
        return json.dumps({"status": "ok", "volume_percent": current})
    except ImportError:
        return "Error: pycaw is not installed. Run: pip install pycaw"
    except Exception as e:
        return f"Volume control failed: {e}"


def _brightness_set(level: int = 50) -> str:
    """Set the screen brightness to a percentage (0-100).

    Args:
        level: Brightness percentage (0-100).
    """
    level = max(0, min(100, int(level)))

    try:
        import screen_brightness_control as sbc
        sbc.set_brightness(level)
        current = sbc.get_brightness()
        # get_brightness may return a list (one per monitor)
        if isinstance(current, list):
            current = current[0] if current else level
        return json.dumps({"status": "ok", "brightness_percent": current})
    except ImportError:
        return "Error: screen-brightness-control is not installed. Run: pip install screen-brightness-control"
    except Exception as e:
        return f"Brightness control failed: {e}"


def get_tools() -> list:
    return [
        {
            "name": "volume_set",
            "description": "Set the system master volume to a percentage (0-100).",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {
                        "type": "integer",
                        "description": "Volume level as a percentage (0-100)."
                    }
                },
                "required": ["level"]
            },
            "handler": _volume_set
        },
        {
            "name": "brightness_set",
            "description": "Set the screen brightness to a percentage (0-100).",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {
                        "type": "integer",
                        "description": "Brightness level as a percentage (0-100)."
                    }
                },
                "required": ["level"]
            },
            "handler": _brightness_set
        }
    ]
