"""Wake word detection using openWakeWord."""

import logging
import os
import threading
import time
from collections.abc import Callable

import numpy as np
from dotenv import load_dotenv

load_dotenv(r"C:\jarvis\.env")

logger = logging.getLogger("jarvis.wake_word")

WAKE_WORD = os.getenv("WAKE_WORD", "hey_jarvis")
WAKE_THRESHOLD = float(os.getenv("WAKE_WORD_THRESHOLD", "0.5"))

_model = None


def _get_model():
    """Load openWakeWord model (lazy)."""
    global _model
    if _model is None:
        from openwakeword.model import Model
        _model = Model(
            wakeword_models=[WAKE_WORD],
            inference_framework="onnx",
        )
        logger.info("Wake word model loaded: %s (threshold=%.2f)", WAKE_WORD, WAKE_THRESHOLD)
    return _model


class WakeWordDetector:
    """Continuously listens for wake word on a background thread."""

    def __init__(self, on_wake: Callable[[], None], chunk_size: int = 1280):
        """
        Args:
            on_wake: callback fired when wake word detected
            chunk_size: audio chunk size in samples (1280 = 80ms at 16kHz)
        """
        self.on_wake = on_wake
        self.chunk_size = chunk_size
        self._running = False
        self._thread = None
        self._cooldown = 2.0  # seconds between detections
        self._last_detection = 0.0

    def start(self):
        """Start listening for wake word."""
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info("Wake word detector started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        logger.info("Wake word detector stopped")

    def _listen_loop(self):
        import sounddevice as sd

        model = _get_model()

        def callback(indata, frames, time_info, status):
            if not self._running:
                return
            if status:
                logger.warning("Audio status: %s", status)

            # Convert to int16 for openWakeWord
            audio_int16 = (indata[:, 0] * 32768).astype(np.int16)
            prediction = model.predict(audio_int16)

            for wake_name, score in prediction.items():
                if score >= WAKE_THRESHOLD:
                    now = time.time()
                    if now - self._last_detection > self._cooldown:
                        self._last_detection = now
                        logger.info("Wake word detected: %s (score=%.3f)", wake_name, score)
                        self.on_wake()

        try:
            with sd.InputStream(
                samplerate=16000,
                channels=1,
                dtype="float32",
                blocksize=self.chunk_size,
                callback=callback,
            ):
                while self._running:
                    time.sleep(0.1)
        except Exception as e:
            logger.error("Wake word listener failed: %s", e)
            self._running = False
