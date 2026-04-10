"""Speech-to-text pipeline: Faster-Whisper + Silero VAD + optional IndicWhisper."""

import io
import logging
import os
import wave
from pathlib import Path
from typing import Any

import numpy as np
from dotenv import load_dotenv

load_dotenv(r"C:\jarvis\.env")

logger = logging.getLogger("jarvis.stt")

STT_MODEL = os.getenv("STT_MODEL", "large-v3-turbo")
STT_INDIC = os.getenv("STT_INDIC", "true").lower() == "true"
STT_LANGUAGE = os.getenv("STT_LANGUAGE", "auto")

# Lazy-loaded models
_whisper_model = None
_vad_model = None
_vad_utils = None


def _get_vad():
    """Load Silero VAD model (lazy)."""
    global _vad_model, _vad_utils
    if _vad_model is None:
        import torch
        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            onnx=True,
        )
        _vad_model = model
        _vad_utils = utils
    return _vad_model, _vad_utils


def _get_whisper():
    """Load Faster-Whisper model (lazy)."""
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        _whisper_model = WhisperModel(
            STT_MODEL,
            device="cuda",
            compute_type="float16",
        )
        logger.info("Faster-Whisper loaded: %s (CUDA)", STT_MODEL)
    return _whisper_model


def has_speech(audio_np: np.ndarray, sample_rate: int = 16000, threshold: float = 0.5) -> bool:
    """Use Silero VAD to check if audio contains speech."""
    try:
        import torch
        model, _ = _get_vad()
        # Ensure correct shape: 1D float32
        if audio_np.dtype != np.float32:
            audio_np = audio_np.astype(np.float32)
        if audio_np.max() > 1.0:
            audio_np = audio_np / 32768.0

        tensor = torch.from_numpy(audio_np)
        # Process in 512-sample chunks for 16kHz
        chunk_size = 512
        speech_probs = []
        for i in range(0, len(tensor) - chunk_size, chunk_size):
            chunk = tensor[i:i + chunk_size]
            prob = model(chunk, sample_rate).item()
            speech_probs.append(prob)

        if not speech_probs:
            return False

        avg_prob = sum(speech_probs) / len(speech_probs)
        max_prob = max(speech_probs)
        # Speech if average > threshold/2 or peak > threshold
        return avg_prob > (threshold / 2) or max_prob > threshold
    except Exception as e:
        logger.error("VAD check failed: %s", e)
        return True  # Fail open — let Whisper decide


def transcribe(audio_bytes: bytes | np.ndarray, language: str = "auto",
               sample_rate: int = 16000) -> dict[str, Any]:
    """Transcribe audio with VAD gate.

    Args:
        audio_bytes: raw PCM int16 bytes or numpy array
        language: language code or 'auto'
        sample_rate: audio sample rate

    Returns:
        {text, confidence, language_detected}
    """
    # Convert to numpy if bytes
    if isinstance(audio_bytes, bytes):
        audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    else:
        audio_np = audio_bytes
        if audio_np.dtype != np.float32:
            audio_np = audio_np.astype(np.float32)
        if audio_np.max() > 1.0:
            audio_np = audio_np / 32768.0

    # VAD gate — prevent Whisper hallucinations on silence
    if not has_speech(audio_np, sample_rate):
        logger.info("VAD: No speech detected, skipping transcription")
        return {"text": "", "confidence": 0.0, "language_detected": "none"}

    # Transcribe with Faster-Whisper
    model = _get_whisper()
    lang_param = None if language == "auto" else language

    segments, info = model.transcribe(
        audio_np,
        language=lang_param,
        beam_size=5,
        vad_filter=True,
    )

    text_parts = []
    confidences = []
    for seg in segments:
        text_parts.append(seg.text.strip())
        confidences.append(seg.avg_logprob)

    full_text = " ".join(text_parts).strip()
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    detected_lang = info.language if info else "unknown"

    logger.info("STT: '%s' (lang=%s, conf=%.2f)", full_text[:100], detected_lang, avg_confidence)

    return {
        "text": full_text,
        "confidence": avg_confidence,
        "language_detected": detected_lang,
    }
