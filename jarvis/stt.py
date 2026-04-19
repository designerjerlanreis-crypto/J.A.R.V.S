import logging
import threading
import time

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

_SAMPLE_RATE = 16_000
_CHUNK = 512
_MAX_DURATION = 8.0
_SILENCE_DURATION = 1.5
_DEFAULT_THRESHOLD = 0.01

_model: WhisperModel | None = None
_silence_threshold = _DEFAULT_THRESHOLD
_logger = logging.getLogger(__name__)


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel("base", device="cpu", compute_type="int8")
    return _model


def _rms(data: np.ndarray) -> float:
    return float(np.sqrt(np.mean(data**2)))


def calibrate() -> None:
    """Measure ambient noise for 2 s and set silence threshold to 1.5× that RMS."""
    global _silence_threshold
    frames: list[np.ndarray] = []

    def _cb(indata, frame_count, time_info, status):
        frames.append(indata[:, 0].copy())

    with sd.InputStream(
        samplerate=_SAMPLE_RATE, channels=1, dtype="float32",
        blocksize=_CHUNK, callback=_cb,
    ):
        time.sleep(2.0)

    if frames:
        ambient_rms = _rms(np.concatenate(frames))
        _silence_threshold = max(ambient_rms * 1.5, _DEFAULT_THRESHOLD)
        _logger.debug("Silence threshold calibrated to %.4f", _silence_threshold)


def listen() -> str:
    """Record from the default mic and return a transcription.

    Stops automatically when silence lasts more than 1.5 s after speech
    is detected, or after 8 s total.
    """
    frames: list[np.ndarray] = []
    silence_start: float | None = None
    speech_detected = False
    stop = threading.Event()

    def _cb(indata, frame_count, time_info, status):
        nonlocal silence_start, speech_detected

        if stop.is_set():
            raise sd.CallbackStop()

        chunk = indata[:, 0]
        frames.append(chunk.copy())
        rms = _rms(chunk)
        now = time.monotonic()

        if rms >= _silence_threshold:
            speech_detected = True
            silence_start = None
        elif speech_detected:
            if silence_start is None:
                silence_start = now
            elif now - silence_start >= _SILENCE_DURATION:
                stop.set()
                raise sd.CallbackStop()

    with sd.InputStream(
        samplerate=_SAMPLE_RATE, channels=1, dtype="float32",
        blocksize=_CHUNK, callback=_cb,
    ):
        stop.wait(timeout=_MAX_DURATION)

    if not frames or not speech_detected:
        return ""

    audio = np.concatenate(frames)
    segments, _ = _get_model().transcribe(audio, beam_size=5, language=None)
    return " ".join(seg.text.strip() for seg in segments).strip()
