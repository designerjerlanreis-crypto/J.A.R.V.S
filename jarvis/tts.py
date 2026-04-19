import asyncio
import io
import logging

import edge_tts
import sounddevice as sd
import soundfile as sf

_voice = "en-GB-RyanNeural"
_logger = logging.getLogger(__name__)


def set_voice(voice_name: str) -> None:
    global _voice
    _voice = voice_name


async def speak(text: str) -> None:
    if not text or not text.strip():
        return
    try:
        communicate = edge_tts.Communicate(text, _voice)
        mp3_chunks: list[bytes] = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                mp3_chunks.append(chunk["data"])
        if not mp3_chunks:
            return
        data, samplerate = sf.read(
            io.BytesIO(b"".join(mp3_chunks)), dtype="float32"
        )
        sd.play(data, samplerate=samplerate)
        await asyncio.to_thread(sd.wait)
    except Exception as exc:
        _logger.debug("TTS playback failed: %s", exc)
