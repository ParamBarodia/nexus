"""Full voice session: mic -> VAD -> wake word -> STT -> chat -> TTS -> speakers."""

import asyncio
import logging
import time
import threading
from datetime import datetime
from pathlib import Path

import numpy as np

logger = logging.getLogger("jarvis.voice")

# Dedicated voice log
VOICE_LOG = Path(r"C:\jarvis\logs\voice.log")
VOICE_LOG.parent.mkdir(parents=True, exist_ok=True)
_vlog = logging.getLogger("jarvis.voice_file")
_fh = logging.FileHandler(VOICE_LOG, encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s"))
_vlog.addHandler(_fh)
_vlog.setLevel(logging.INFO)

SAMPLE_RATE = 16000
SILENCE_TIMEOUT = 2.0  # seconds of silence to stop recording
FOLLOW_UP_WINDOW = 5.0  # seconds to listen for follow-up without wake word


def record_until_silence(max_duration: float = 30.0) -> np.ndarray:
    """Record from microphone until silence detected by VAD."""
    import sounddevice as sd
    from brain.stt import has_speech

    chunks = []
    silence_start = None
    start_time = time.time()

    def callback(indata, frames, time_info, status):
        nonlocal silence_start
        audio = indata[:, 0].copy()
        chunks.append(audio)

        # Check for speech every ~0.5 seconds
        if len(chunks) % 8 == 0:
            recent = np.concatenate(chunks[-8:])
            if has_speech(recent, SAMPLE_RATE, threshold=0.3):
                silence_start = None
            elif silence_start is None:
                silence_start = time.time()

    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=1024,
            callback=callback,
        ):
            while True:
                time.sleep(0.05)
                elapsed = time.time() - start_time
                if elapsed > max_duration:
                    break
                if silence_start and (time.time() - silence_start) > SILENCE_TIMEOUT:
                    break
    except Exception as e:
        logger.error("Recording failed: %s", e)

    if not chunks:
        return np.array([], dtype=np.float32)

    return np.concatenate(chunks)


async def _process_voice_turn(audio: np.ndarray) -> str:
    """Transcribe audio, send to chat, return response text."""
    from brain.stt import transcribe
    from brain.chat import stream_chat

    # STT
    result = transcribe(audio, language="auto", sample_rate=SAMPLE_RATE)
    text = result["text"]
    lang = result["language_detected"]

    if not text:
        return ""

    _vlog.info("Transcript: '%s' (lang=%s, conf=%.2f)", text, lang, result["confidence"])

    # Chat
    response_parts = []
    async for chunk in stream_chat(text):
        if chunk["type"] == "token":
            response_parts.append(chunk["content"])
        elif chunk["type"] == "text":
            response_parts.append(chunk["content"])

    response = "".join(response_parts)
    _vlog.info("Response: '%s'", response[:200])

    return response


def _play_audio_signature(name: str):
    """Play an audio signature (listening, thinking, done) if available."""
    audio_dir = Path(r"C:\jarvis\data\audio")
    wav_file = audio_dir / f"{name}.wav"
    if not wav_file.exists():
        return
    try:
        import winsound
        winsound.PlaySound(str(wav_file), winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception:
        pass  # Non-critical — skip silently


def _speak(text: str):
    """TTS output using edge-tts (preferred) with pyttsx3 fallback."""
    if not text:
        return

    import os
    tts_backend = os.getenv("TTS_BACKEND", "edge")

    if tts_backend == "edge":
        try:
            import edge_tts
            import tempfile

            voice = os.getenv("TTS_VOICE", "en-GB-RyanNeural")
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name

            async def _edge_speak():
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(tmp_path)

            asyncio.run(_edge_speak())

            # Play with PowerShell MediaPlayer (no extra deps needed)
            import subprocess
            ps_cmd = (
                f'Add-Type -AssemblyName PresentationCore; '
                f'$p = New-Object System.Windows.Media.MediaPlayer; '
                f'$p.Open([Uri]::new("{tmp_path}")); '
                f'$p.Play(); '
                f'Start-Sleep -Milliseconds 500; '
                f'while ($p.Position -lt $p.NaturalDuration.TimeSpan) {{ Start-Sleep -Milliseconds 200 }}; '
                f'$p.Close()'
            )
            try:
                subprocess.run(
                    ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
                    timeout=120, capture_output=True
                )
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
            return
        except Exception as e:
            logger.warning("edge-tts failed: %s, falling back to pyttsx3", e)

    # Fallback: pyttsx3
    try:
        import pyttsx3
        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
        for v in voices:
            if "david" in v.name.lower() or "british" in v.name.lower():
                engine.setProperty("voice", v.id)
                break
        engine.setProperty("rate", 170)
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        logger.warning("TTS failed (pyttsx3): %s, print-only", e)
        print(f"\n[JARVIS]: {text}")


def run_push_to_talk():
    """Push-to-talk mode: press Enter to speak, release to process."""
    from rich.console import Console
    console = Console()

    console.print("[bold cyan]J.A.R.V.I.S.[/bold cyan] — Push-to-Talk Mode")
    console.print("[dim]Press Enter to start recording. Ctrl+C to exit.[/dim]\n")

    try:
        while True:
            input("[Press Enter to speak] ")
            _play_audio_signature("listening")
            console.print("[yellow]Listening...[/yellow]", end=" ")
            audio = record_until_silence(max_duration=30)

            if len(audio) < SAMPLE_RATE * 0.3:  # Less than 0.3s
                console.print("[dim]Too short, skipped.[/dim]")
                continue

            _play_audio_signature("thinking")
            console.print("[green]Processing...[/green]")
            response = asyncio.run(_process_voice_turn(audio))
            if response:
                _speak(response)
                _play_audio_signature("done")
            console.print()
    except KeyboardInterrupt:
        console.print("\n[cyan]Signing off, Sir.[/cyan]")


def run_ambient_listen():
    """Ambient mode: wake word -> record -> process -> follow-up window."""
    from rich.console import Console
    from brain.wake_word import WakeWordDetector

    console = Console()
    console.print("[bold cyan]J.A.R.V.I.S.[/bold cyan] — Ambient Listening Mode")
    console.print("[dim]Say 'Hey Jarvis' to activate. Ctrl+C to exit.[/dim]\n")

    wake_event = threading.Event()

    def on_wake():
        console.print("[green]Wake word detected![/green]")
        wake_event.set()

    detector = WakeWordDetector(on_wake=on_wake)
    detector.start()

    try:
        while True:
            wake_event.wait()
            wake_event.clear()

            # Record until silence
            console.print("[yellow]Listening...[/yellow]")
            audio = record_until_silence(max_duration=30)

            if len(audio) < SAMPLE_RATE * 0.3:
                continue

            console.print("[green]Processing...[/green]")
            response = asyncio.run(_process_voice_turn(audio))
            if response:
                _speak(response)

            # Follow-up window: listen again without wake word
            follow_up_start = time.time()
            while time.time() - follow_up_start < FOLLOW_UP_WINDOW:
                console.print("[dim]Listening for follow-up...[/dim]")
                audio = record_until_silence(max_duration=10)
                if len(audio) >= SAMPLE_RATE * 0.3:
                    from brain.stt import has_speech
                    if has_speech(audio, SAMPLE_RATE):
                        console.print("[green]Processing follow-up...[/green]")
                        response = asyncio.run(_process_voice_turn(audio))
                        if response:
                            _speak(response)
                        follow_up_start = time.time()  # Reset window
                        continue
                break  # No follow-up detected

            console.print("[dim]Returning to ambient listening...[/dim]\n")
    except KeyboardInterrupt:
        detector.stop()
        console.print("\n[cyan]Signing off, Sir.[/cyan]")


def run_voice_session():
    """Full conversation mode: speak and listen alternately."""
    from rich.console import Console
    console = Console()

    console.print("[bold cyan]J.A.R.V.I.S.[/bold cyan] — Voice Conversation Mode")
    console.print("[dim]Speak naturally. Ctrl+C to exit.[/dim]\n")

    _speak("Systems nominal, Sir. Voice session active.")

    try:
        while True:
            console.print("[yellow]Listening...[/yellow]")
            audio = record_until_silence(max_duration=30)

            if len(audio) < SAMPLE_RATE * 0.3:
                time.sleep(0.5)
                continue

            console.print("[green]Processing...[/green]")
            response = asyncio.run(_process_voice_turn(audio))
            if response:
                _speak(response)
            console.print()
    except KeyboardInterrupt:
        console.print("\n[cyan]Signing off, Sir.[/cyan]")
