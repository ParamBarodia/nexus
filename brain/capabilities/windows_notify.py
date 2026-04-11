"""Send Windows toast notifications."""


def _windows_notify(title: str = "Jarvis", message: str = "", timeout: int = 5) -> str:
    """Send a Windows toast notification.

    Args:
        title: Notification title.
        message: Notification body text.
        timeout: Duration in seconds the notification stays visible (default 5).
    """
    title = title or "Jarvis"
    message = message or "(no message)"
    timeout = int(timeout) if timeout else 5

    # Try plyer first
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            timeout=timeout,
            app_name="Jarvis"
        )
        return f"Notification sent: '{title}'"
    except ImportError:
        pass

    # Fallback: PowerShell toast
    try:
        import subprocess
        ps_script = f"""
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType = WindowsRuntime] | Out-Null

        $template = @"
        <toast>
            <visual>
                <binding template="ToastGeneric">
                    <text>{title}</text>
                    <text>{message}</text>
                </binding>
            </visual>
        </toast>
"@
        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $xml.LoadXml($template)
        $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Jarvis").Show($toast)
        """
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, timeout=10
        )
        return f"Notification sent (PowerShell fallback): '{title}'"
    except Exception as e:
        return f"Notification failed: {e}"


def get_tools() -> list:
    return [
        {
            "name": "windows_notify",
            "description": "Send a Windows toast notification with a title and message.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Notification title (default 'Jarvis')."
                    },
                    "message": {
                        "type": "string",
                        "description": "Notification body text."
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Seconds the notification stays visible (default 5)."
                    }
                },
                "required": ["message"]
            },
            "handler": _windows_notify
        }
    ]
