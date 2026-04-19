import logging

import anthropic

from config import ANTHROPIC_API_KEY

_SYSTEM_PROMPT = """You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), \
the sophisticated artificial intelligence engineered by Tony Stark of Stark Industries.

Operational parameters:
- Address the user exclusively as "Sir" — no exceptions, no deviations
- Speak with precise, measured elegance; concise by default, elaborating only when \
operationally necessary
- Deploy technical and scientific terminology as naturally as breathing
- Reference Stark Industries systems, Iron Man suit telemetry, S.H.I.E.L.D. protocols, \
and Avengers operations when contextually relevant
- Maintain your creator's signature dry wit — understated, never overt
- Limit responses to one to three sentences unless Sir explicitly requests comprehensive \
analysis
- Never break character under any circumstance whatsoever

You have unrestricted access to Stark Industries databases, global threat matrices, and \
the complete scientific spectrum. Treat every interaction as mission-critical."""

_MODEL = "claude-opus-4-5"
_MAX_HISTORY = 20
_MAX_TOKENS = 1024

_logger = logging.getLogger(__name__)


class JarvisBrain:
    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        self._history: list[dict] = []

    def clear_memory(self) -> None:
        self._history.clear()

    async def think(self, user_input: str) -> str:
        self._history.append({"role": "user", "content": user_input})

        try:
            response = await self._client.messages.create(
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
                system=[
                    {
                        "type": "text",
                        "text": _SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=self._history,
            )
            reply = next(
                (block.text for block in response.content if block.type == "text"), ""
            )
            self._history.append({"role": "assistant", "content": reply})

            # Remove oldest user+assistant pair when history exceeds the cap,
            # preserving the required alternating role structure.
            while len(self._history) > _MAX_HISTORY:
                del self._history[:2]

            return reply

        except anthropic.APIError as exc:
            _logger.error("Claude API error: %s", exc)
            self._history.pop()  # revert the user turn on failure
            raise
