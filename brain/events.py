"""Event bus and event sources for Nexus hook system."""

import logging
import threading
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("jarvis.events")

# Dedicated hooks log
HOOKS_LOG = r"C:\jarvis\logs\hooks.log"
_hooks_logger = logging.getLogger("jarvis.hooks_fire")
_fh = logging.FileHandler(HOOKS_LOG, encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s"))
_hooks_logger.addHandler(_fh)
_hooks_logger.setLevel(logging.INFO)


class Event:
    """A single event with type and payload."""
    def __init__(self, event_type: str, payload: dict[str, Any] | None = None):
        self.event_type = event_type
        self.payload = payload or {}
        self.timestamp = time.time()

    def __repr__(self):
        return f"Event({self.event_type}, {self.payload})"


class EventBus:
    """Central publish/subscribe event bus."""
    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, callback: Callable[[Event], None]):
        with self._lock:
            self._subscribers.setdefault(event_type, []).append(callback)
        logger.info("Subscribed to %s: %s", event_type, callback.__name__)

    def unsubscribe(self, event_type: str, callback: Callable):
        with self._lock:
            if event_type in self._subscribers:
                self._subscribers[event_type] = [
                    cb for cb in self._subscribers[event_type] if cb != callback
                ]

    def publish(self, event: Event):
        _hooks_logger.info("Event fired: %s | %s", event.event_type, event.payload)
        with self._lock:
            callbacks = list(self._subscribers.get(event.event_type, []))
            # Also fire for wildcard subscribers
            callbacks += list(self._subscribers.get("*", []))
        for cb in callbacks:
            try:
                cb(event)
            except Exception as e:
                logger.error("Event handler %s failed: %s", cb.__name__, e)

    def subscribe_all(self, callback: Callable[[Event], None]):
        """Subscribe to all events."""
        self.subscribe("*", callback)


# Global event bus
bus = EventBus()


class ClipboardEventSource:
    """Monitors clipboard for large text changes."""
    def __init__(self, min_length: int = 100, poll_interval: float = 2.0):
        self.min_length = min_length
        self.poll_interval = poll_interval
        self._last_text = ""
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()
        logger.info("Clipboard watcher started (min_length=%d)", self.min_length)

    def stop(self):
        self._running = False

    def _poll(self):
        try:
            import pyperclip
        except ImportError:
            logger.warning("pyperclip not installed, clipboard watcher disabled")
            return

        while self._running:
            try:
                text = pyperclip.paste()
                if text and text != self._last_text and len(text) >= self.min_length:
                    self._last_text = text
                    bus.publish(Event("clipboard_changed", {
                        "text": text[:2000],
                        "length": len(text),
                    }))
            except Exception:
                pass
            time.sleep(self.poll_interval)


class IdleEventSource:
    """Fires when no user activity for N minutes."""
    def __init__(self, idle_minutes: int = 30):
        self.idle_minutes = idle_minutes
        self._last_activity = time.time()
        self._running = False
        self._idle_fired = False
        self._thread = None

    def touch(self):
        """Call this on any user activity."""
        self._last_activity = time.time()
        self._idle_fired = False

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._monitor, daemon=True)
        self._thread.start()
        logger.info("Idle watcher started (threshold=%d min)", self.idle_minutes)

    def stop(self):
        self._running = False

    def _monitor(self):
        while self._running:
            elapsed = (time.time() - self._last_activity) / 60
            if elapsed >= self.idle_minutes and not self._idle_fired:
                self._idle_fired = True
                bus.publish(Event("user_idle", {"idle_minutes": int(elapsed)}))
            time.sleep(30)
