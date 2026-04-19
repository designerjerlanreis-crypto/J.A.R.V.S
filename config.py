import os
import warnings

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_API_KEY:
    warnings.warn(
        "ANTHROPIC_API_KEY não está configurada. "
        "Defina-a no arquivo .env antes de usar o brain.think().",
        stacklevel=1,
    )

PICOVOICE_KEY = os.environ.get("PICOVOICE_KEY", "")
