import asyncio
import logging
import re
import sys

import numpy as np
import sounddevice as sd

from . import stt, tts
from .brain import JarvisBrain
from .skills import system as sys_skill
from .skills import web as web_skill

# ── Logging ───────────────────────────────────────────────────────────────────

def _setup_logging() -> None:
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    fh = logging.FileHandler("jarvis.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter(fmt))
    root.addHandler(fh)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(logging.Formatter(fmt))
    root.addHandler(sh)


_log = logging.getLogger(__name__)

# ── Activation beep ───────────────────────────────────────────────────────────

def _play_beep(freq: float = 440.0, duration: float = 0.15, volume: float = 0.3) -> None:
    sr = 44_100
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    wave = (volume * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    # Fade out last 20 % to avoid click
    fade = len(wave) // 5
    wave[-fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)
    sd.play(wave, samplerate=sr)
    sd.wait()

# ── Skill detection ───────────────────────────────────────────────────────────

# Order matters: more specific patterns first
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(abr(?:ir|e|a)|abre|abra)\b"),       "open_app"),
    (re.compile(r"\b(fech(?:ar|a|e)|fecha|feche)\b"),     "close_app"),
    (re.compile(r"\bvolume\b"),                            "volume"),
    (re.compile(r"\b(clima|tempo|temperatura|weather)\b"), "weather"),
    (re.compile(r"\b(busc(?:ar|a)|pesquis(?:ar|a)|procur(?:ar|a))\b"), "search"),
    (re.compile(r"\bbateria\b"),                           "battery"),
    (re.compile(r"\b(apps?|aplicativos?|programas?)\b"),   "apps"),
]

# Words to strip when extracting the skill argument
_NOISE = re.compile(
    r"\b(abrir?|abre|abra|fechar?|fecha|feche|volume|clima|tempo|temperatura|"
    r"weather|buscar?|busca|pesquisar?|pesquisa|procurar?|procura|o|a|os|as|"
    r"me|pra|para|do|da|de|em|no|na)\b"
)


def _extract_arg(text: str) -> str:
    return _NOISE.sub("", text.lower()).strip()


def _detect_skill(text: str) -> tuple[str, str] | None:
    lower = text.lower()
    for pattern, skill in _PATTERNS:
        if not pattern.search(lower):
            continue
        arg = _extract_arg(lower)
        if skill == "weather":
            m = re.search(r"(?:em|de|para|in)\s+(.+)", lower)
            arg = m.group(1).strip() if m else (arg or "São Paulo")
        elif skill == "volume":
            m = re.search(r"\d+", lower)
            arg = m.group() if m else ""
        return (skill, arg)
    return None


def _run_skill(skill: str, arg: str) -> str:
    try:
        if skill == "open_app":
            return sys_skill.open_app(arg)
        if skill == "close_app":
            return sys_skill.close_app(arg)
        if skill == "volume":
            if arg:
                sys_skill.set_volume(int(arg))
                return f"Volume definido para {arg}%, Sir."
            return f"Volume atual: {sys_skill.get_volume()}%, Sir."
        if skill == "weather":
            return web_skill.get_weather(arg)
        if skill == "search":
            return web_skill.search_web(arg)
        if skill == "battery":
            return sys_skill.get_battery_status()
        if skill == "apps":
            names = sys_skill.get_running_apps()[:10]
            return "Processos ativos: " + ", ".join(names) + "."
    except Exception as exc:
        _log.error("Skill '%s' raised: %s", skill, exc)
        return "Falha ao executar a operação, Sir."
    return ""

# ── Interaction handler ───────────────────────────────────────────────────────

async def _handle(brain: JarvisBrain) -> None:
    user_text = await asyncio.to_thread(stt.listen)

    if not user_text or len(user_text.split()) < 2:
        _log.info("Transcription too short or empty — skipping.")
        return

    _log.info("User  : %s", user_text)

    skill_context = ""
    detected = _detect_skill(user_text)
    if detected:
        skill, arg = detected
        _log.info("Skill : %s(%r)", skill, arg)
        skill_context = await asyncio.to_thread(_run_skill, skill, arg)
        _log.info("Result: %s", skill_context)

    prompt = f"{user_text} [contexto: {skill_context}]" if skill_context else user_text
    response = await brain.think(prompt)
    _log.info("JARVIS: %s", response)

    await tts.speak(response)

# ── Entry point ───────────────────────────────────────────────────────────────

async def main() -> None:
    _setup_logging()
    _log.info("Initializing J.A.R.V.I.S.")

    brain = JarvisBrain()

    _log.info("Calibrating microphone — please remain silent…")
    await asyncio.to_thread(stt.calibrate)
    _log.info("Calibration complete.")

    await tts.speak("Systems online. Ready to assist, Sir.")
    _log.info("J.A.R.V.I.S. online — continuous listen mode.")

    try:
        while True:
            await asyncio.to_thread(_play_beep)
            await _handle(brain)
    except (KeyboardInterrupt, asyncio.CancelledError):
        _log.info("Shutdown signal received.")
    finally:
        _log.info("J.A.R.V.I.S. offline.")


if __name__ == "__main__":
    asyncio.run(main())
