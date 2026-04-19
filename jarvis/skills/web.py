import logging
import urllib.parse

import requests

_logger = logging.getLogger(__name__)
_TIMEOUT = 8


def search_web(query: str) -> str:
    """Return up to 3 DuckDuckGo results as plain text."""
    try:
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        _logger.error("DuckDuckGo search failed: %s", exc)
        return "Search temporarily unavailable, Sir."

    lines: list[str] = []

    # Direct abstract (e.g. Wikipedia summary)
    abstract = (data.get("AbstractText") or "").strip()
    if abstract:
        source = data.get("AbstractSource") or "Source"
        lines.append(f"{source}: {abstract}")

    # Direct URL results
    for item in data.get("Results", []):
        if len(lines) >= 3:
            break
        text = (item.get("Text") or "").strip()
        url = item.get("FirstURL") or ""
        if text and url:
            lines.append(f"• {text} — {url}")

    # Related topics (flat or grouped)
    for item in data.get("RelatedTopics", []):
        if len(lines) >= 3:
            break
        if "Topics" in item:
            for sub in item["Topics"]:
                if len(lines) >= 3:
                    break
                text = (sub.get("Text") or "").strip()
                url = sub.get("FirstURL") or ""
                if text and url:
                    lines.append(f"• {text} — {url}")
        else:
            text = (item.get("Text") or "").strip()
            url = item.get("FirstURL") or ""
            if text and url:
                lines.append(f"• {text} — {url}")

    return "\n".join(lines) if lines else f"No results found for '{query}', Sir."


def get_weather(city: str) -> str:
    """Return current weather for a city in Portuguese using wttr.in."""
    encoded = urllib.parse.quote(city)
    try:
        resp = requests.get(
            f"https://wttr.in/{encoded}?format=j1",
            timeout=_TIMEOUT,
            headers={"Accept-Language": "pt-BR,pt;q=0.9"},
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        _logger.error("wttr.in request failed: %s", exc)
        return "Dados meteorológicos indisponíveis, Sir."

    try:
        current = data["current_condition"][0]

        # Prefer Portuguese description, fall back to English
        lang_pt = current.get("lang_pt") or current.get("weatherDesc") or [{}]
        desc = lang_pt[0].get("value", "—")

        temp_c = current.get("temp_C", "—")
        feels_like = current.get("FeelsLikeC", "—")
        humidity = current.get("humidity", "—")
        wind_kmph = current.get("windspeedKmph", "—")

        return (
            f"{city.title()}: {desc}, {temp_c}°C "
            f"(sensação térmica {feels_like}°C), "
            f"umidade {humidity}%, vento {wind_kmph} km/h."
        )
    except (KeyError, IndexError) as exc:
        _logger.error("Failed to parse wttr.in response: %s", exc)
        return "Não foi possível interpretar os dados meteorológicos, Sir."
