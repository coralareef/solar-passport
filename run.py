from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def load_local_env(path: Path) -> bool:
    """Load simple KEY=VALUE pairs from .env without third-party packages.

    Existing process environment variables win over .env values.
    """
    if not path.exists():
        return False
    loaded = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
            loaded = True
    return loaded


load_local_env(BASE_DIR / ".env")

# Import only after .env has been loaded because app.py reads NREL_API_KEY at import time.
import app  # noqa: E402


if __name__ == "__main__":
    configured = bool(os.getenv("NREL_API_KEY", "").strip())
    print("Solar Passport launcher")
    print(f"NREL PVWatts API: {'configured' if configured else 'not configured — estimate mode'}")
    app.run()
