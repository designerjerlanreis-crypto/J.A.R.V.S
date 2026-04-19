import logging
import os
import subprocess

import psutil

_logger = logging.getLogger(__name__)

_APP_MAP: dict[str, str] = {
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "firefox": "firefox.exe",
    "spotify": "Spotify.exe",
    "vscode": "Code.exe",
    "visual studio code": "Code.exe",
    "notepad": "notepad.exe",
    "explorer": "explorer.exe",
    "discord": "Discord.exe",
    "steam": "steam.exe",
    "word": "WINWORD.EXE",
    "excel": "EXCEL.EXE",
    "powerpoint": "POWERPNT.EXE",
    "terminal": "wt.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "calculator": "calc.exe",
    "paint": "mspaint.exe",
    "vlc": "vlc.exe",
    "slack": "slack.exe",
    "teams": "Teams.exe",
}


def get_battery_status() -> str:
    battery = psutil.sensors_battery()
    if battery is None:
        return "No battery detected — running on AC power, Sir."
    pct = int(battery.percent)
    state = "charging" if battery.power_plugged else "discharging"
    return f"{pct}% battery, currently {state}, Sir."


def get_volume() -> int:
    import ctypes
    vol = ctypes.c_uint()
    ctypes.windll.winmm.waveOutGetVolume(0, ctypes.byref(vol))
    return round((vol.value & 0xFFFF) / 0xFFFF * 100)


def set_volume(level: int) -> None:
    import ctypes
    level = max(0, min(100, level))
    word = round(level / 100 * 0xFFFF)
    ctypes.windll.winmm.waveOutSetVolume(0, (word << 16) | word)


def get_running_apps() -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for proc in psutil.process_iter(["name"]):
        name = proc.info.get("name") or ""
        if name and name not in seen:
            seen.add(name)
            result.append(name)
    return sorted(result)


def open_app(app_name: str) -> str:
    key = app_name.strip().lower()
    exe = _APP_MAP.get(key, app_name)
    try:
        os.startfile(exe)
        return f"Opening {app_name}, Sir."
    except (FileNotFoundError, OSError):
        pass
    try:
        subprocess.Popen(exe, shell=True)
        return f"Launching {app_name}, Sir."
    except Exception as exc:
        _logger.error("open_app(%s) failed: %s", app_name, exc)
        return f"Unable to locate {app_name}, Sir."


def close_app(app_name: str) -> str:
    key = app_name.strip().lower()
    exe = _APP_MAP.get(key, app_name)
    target = exe.lower().removesuffix(".exe")

    killed = 0
    for proc in psutil.process_iter(["name"]):
        try:
            name = (proc.info.get("name") or "").lower().removesuffix(".exe")
            if name == target:
                proc.terminate()
                killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if killed:
        return f"Terminated {killed} instance(s) of {app_name}, Sir."
    return f"No running instances of {app_name} found, Sir."
