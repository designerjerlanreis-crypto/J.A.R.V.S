import logging
import queue
import threading
import time
from collections.abc import Callable

import numpy as np
import sounddevice as sd

from config import PICOVOICE_KEY

_logger = logging.getLogger(__name__)

_SAMPLE_RATE = 16_000
_CHANNELS = 1


class HotwordDetector:
    def __init__(self, on_detected: Callable[[], None]) -> None:
        self._on_detected = on_detected
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._use_porcupine = bool(PICOVOICE_KEY)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        target = self._porcupine_loop if self._use_porcupine else self._fallback_loop
        self._thread = threading.Thread(
            target=target, daemon=True, name="HotwordDetector"
        )
        self._thread.start()
        mode = "Porcupine" if self._use_porcupine else "energy+Whisper fallback"
        _logger.info("HotwordDetector started (%s)", mode)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._thread = None

    # ── Primary: Picovoice Porcupine ─────────────────────────────────────────

    def _porcupine_loop(self) -> None:
        import pyaudio
        import pvporcupine

        porcupine = pa = stream = None
        try:
            porcupine = pvporcupine.create(
                access_key=PICOVOICE_KEY,
                keywords=["jarvis"],
            )
            pa = pyaudio.PyAudio()
            stream = pa.open(
                rate=porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=porcupine.frame_length,
            )
            _logger.debug("Porcupine listening (frame_length=%d)", porcupine.frame_length)
            while not self._stop_event.is_set():
                pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
                result = porcupine.process(np.frombuffer(pcm, dtype=np.int16))
                if result >= 0:
                    _logger.debug("Hotword detected (keyword_index=%d)", result)
                    self._on_detected()
        except Exception as exc:
            _logger.error("Porcupine loop failed: %s", exc)
        finally:
            if stream:
                stream.stop_stream()
                stream.close()
            if pa:
                pa.terminate()
            if porcupine:
                porcupine.delete()

    # ── Fallback: energy trigger + Whisper verification ───────────────────────

    def _fallback_loop(self) -> None:
        from faster_whisper import WhisperModel

        _CHUNK = 1024
        _WINDOW = int(_SAMPLE_RATE * 2.5)  # accumulate 2.5 s before transcribing
        _THRESHOLD = 0.015                 # RMS to consider as potential speech
        _COOLDOWN = 2.0                    # seconds between detections

        model = WhisperModel("base", device="cpu", compute_type="int8")
        audio_q: queue.Queue[np.ndarray] = queue.Queue()

        def _cb(indata, frames, time_info, status):
            audio_q.put(indata[:, 0].copy())

        accumulated: list[np.ndarray] = []
        accumulated_samples = 0
        triggered = False
        last_detection = 0.0

        with sd.InputStream(
            samplerate=_SAMPLE_RATE,
            channels=_CHANNELS,
            dtype="float32",
            blocksize=_CHUNK,
            callback=_cb,
        ):
            _logger.debug("Fallback hotword listening (energy + Whisper)")
            while not self._stop_event.is_set():
                try:
                    chunk = audio_q.get(timeout=0.1)
                except queue.Empty:
                    continue

                rms = float(np.sqrt(np.mean(chunk**2)))

                if not triggered and rms >= _THRESHOLD:
                    triggered = True
                    accumulated.clear()
                    accumulated_samples = 0

                if triggered:
                    accumulated.append(chunk)
                    accumulated_samples += len(chunk)

                    if accumulated_samples >= _WINDOW:
                        triggered = False
                        now = time.monotonic()
                        if now - last_detection >= _COOLDOWN:
                            audio = np.concatenate(accumulated)
                            segments, _ = model.transcribe(
                                audio, beam_size=3, language=None
                            )
                            text = " ".join(s.text for s in segments).lower()
                            if "jarvis" in text:
                                _logger.debug("Hotword via Whisper: %r", text)
                                last_detection = time.monotonic()
                                self._on_detected()
