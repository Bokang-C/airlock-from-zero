import os


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


MAX_HTML_BYTES = 750_000
MAX_SEGMENTS = 500
SCAN_TIMEOUT_SECONDS = 10
ALLOW_URL_SCAN = env_bool("AIRLOCK_ENABLE_URL_SCAN", False)
# Setting false is ONLY suitable for controlled local demonstrations, not for public web hosting.
CHROMIUM_SANDBOX = not env_bool("AIRLOCK_DEV_NO_BROWSER_SANDBOX", False)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
ALLOWED_ORIGINS = os.environ.get("AIRLOCK_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")

CHROMIUM_EXECUTABLE = os.environ.get("AIRLOCK_CHROMIUM_EXECUTABLE", "").strip() or None
