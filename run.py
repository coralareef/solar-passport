from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def load_local_env(path: Path) -> bool:
    """Load simple KEY=VALUE pairs from .env without third-party packages.

    For the local launcher, values in .env intentionally override stale Windows
    environment variables so the project folder remains the clear source of
    local configuration.
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
        if key:
            os.environ[key] = value
            loaded = True
    return loaded


loaded_env = load_local_env(BASE_DIR / ".env")

# Import only after .env has been loaded because app.py reads NREL_API_KEY at import time.
import app  # noqa: E402


if __name__ == "__main__":
    configured = bool(os.getenv("NREL_API_KEY", "").strip())
    print("Solar Passport launcher")
    print(f"Local .env: {'loaded' if loaded_env else 'not found'}")
    print(f"NREL PVWatts API key: {'present' if configured else 'missing — estimate mode'}")
    app.run()
