from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

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

# NLR retired the previous developer.nrel.gov domain in May 2026.
PVWATTS_URL = "https://developer.nlr.gov/api/pvwatts/v8.json"
app.PVWATTS_URL = PVWATTS_URL
app.NREL_API_KEY = os.getenv("NREL_API_KEY", "").strip()

_pvwatts_diag = {
    "configured": bool(app.NREL_API_KEY),
    "connected": False,
    "endpoint": PVWATTS_URL,
    "error": None,
    "station": None,
    "checked_at": None,
}


def _safe_http_error(exc: HTTPError) -> str:
    try:
        raw = exc.read().decode("utf-8", errors="replace")
        body = json.loads(raw)
        errors = body.get("errors") if isinstance(body, dict) else None
        if errors:
            return f"HTTP {exc.code}: {'; '.join(str(x) for x in errors)}"
        return f"HTTP {exc.code}: {raw[:300]}"
    except Exception:
        return f"HTTP {exc.code}: {exc.reason}"


def pvwatts_generation(lat: float, lon: float, capacity_kwp: float, tilt: float, azimuth: float, losses: float, specific_yield: float):
    """PVWatts v8 with visible diagnostics and a safe estimate fallback."""
    global _pvwatts_diag

    if app.NREL_API_KEY and capacity_kwp > 0:
        params = {
            "api_key": app.NREL_API_KEY,
            "lat": lat,
            "lon": lon,
            "system_capacity": capacity_kwp,
            "module_type": 0,
            "array_type": 1,
            "tilt": tilt,
            "azimuth": azimuth,
            "losses": losses,
            "inv_eff": 96,
            "dc_ac_ratio": 1.2,
            "radius": 0,
            "dataset": "nsrdb",
        }
        query = urlencode(params)
        req = Request(
            f"{PVWATTS_URL}?{query}",
            headers={"User-Agent": "SolarPassport-Brunei/0.2"},
        )
        try:
            with urlopen(req, timeout=20) as res:
                body = json.loads(res.read().decode("utf-8"))
            errors = body.get("errors") or []
            if errors:
                raise RuntimeError("; ".join(str(x) for x in errors))
            outputs = body.get("outputs") or {}
            monthly = outputs.get("ac_monthly")
            if not monthly or len(monthly) != 12:
                raise RuntimeError("PVWatts returned no 12-month AC generation series")

            station = body.get("station_info") or {}
            _pvwatts_diag = {
                "configured": True,
                "connected": True,
                "endpoint": PVWATTS_URL,
                "error": None,
                "station": {
                    "lat": station.get("lat"),
                    "lon": station.get("lon"),
                    "weather_data_source": station.get("weather_data_source"),
                    "distance_m": station.get("distance"),
                },
                "checked_at": time.time(),
            }
            return {
                "monthly_kwh": [float(x) for x in monthly],
                "annual_kwh": float(outputs.get("ac_annual", sum(monthly))),
                "capacity_factor": float(outputs.get("capacity_factor", 0.0)),
                "source": "NREL PVWatts v8",
                "source_confidence": "Medium-High",
            }
        except HTTPError as exc:
            error = _safe_http_error(exc)
        except URLError as exc:
            error = f"Network error: {exc.reason}"
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"

        _pvwatts_diag = {
            "configured": True,
            "connected": False,
            "endpoint": PVWATTS_URL,
            "error": error,
            "station": None,
            "checked_at": time.time(),
        }
        print(f"[PVWATTS] Connection failed: {error}")
    else:
        _pvwatts_diag = {
            "configured": bool(app.NREL_API_KEY),
            "connected": False,
            "endpoint": PVWATTS_URL,
            "error": "NREL_API_KEY is missing" if not app.NREL_API_KEY else None,
            "station": None,
            "checked_at": time.time(),
        }

    monthly = app.monthly_generation_fallback(capacity_kwp, specific_yield)
    annual = sum(monthly)
    cf = annual / (capacity_kwp * 8760) * 100 if capacity_kwp > 0 else 0.0
    return {
        "monthly_kwh": monthly,
        "annual_kwh": annual,
        "capacity_factor": cf,
        "source": "MVP specific-yield fallback",
        "source_confidence": "Low-Medium",
    }


app.pvwatts_generation = pvwatts_generation

# Prototype location search using the public OpenStreetMap Nominatim service.
# Keep this lightweight: one request/second maximum and cache repeated searches.
_geocode_cache = {}
_geocode_lock = threading.Lock()
_last_geocode_request = 0.0


def geocode_brunei(query: str):
    global _last_geocode_request
    q = " ".join((query or "").strip().split())[:200]
    if len(q) < 2:
        return []

    cache_key = q.casefold()
    if cache_key in _geocode_cache:
        return _geocode_cache[cache_key]

    with _geocode_lock:
        now = time.monotonic()
        wait = 1.05 - (now - _last_geocode_request)
        if wait > 0:
            time.sleep(wait)
        params = urlencode({
            "q": q,
            "format": "jsonv2",
            "limit": 5,
            "countrycodes": "bn",
            "addressdetails": 1,
        })
        req = Request(
            f"https://nominatim.openstreetmap.org/search?{params}",
            headers={
                "User-Agent": "SolarPassport-Brunei/0.2 (local rooftop assessment prototype)",
                "Referer": "http://127.0.0.1:5000/",
            },
        )
        with urlopen(req, timeout=15) as res:
            raw = json.loads(res.read().decode("utf-8"))
        _last_geocode_request = time.monotonic()

    results = []
    for item in raw[:5]:
        try:
            result = {
                "display_name": item.get("display_name") or q,
                "lat": float(item["lat"]),
                "lon": float(item["lon"]),
                "type": item.get("type"),
            }
            bbox = item.get("boundingbox")
            if isinstance(bbox, list) and len(bbox) == 4:
                result["boundingbox"] = [float(x) for x in bbox]
            results.append(result)
        except (KeyError, TypeError, ValueError):
            continue
    _geocode_cache[cache_key] = results
    return results


BaseHandler = app.SolarPassportHandler


class RuntimeHandler(BaseHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/pvwatts/status":
            # Run a real, small probe so "connected" means the API actually responded.
            pvwatts_generation(4.9031, 114.9398, 0.5, 10.0, 180.0, 14.0, 1420.0)
            return self.send_json(dict(_pvwatts_diag))

        if path == "/api/geocode":
            try:
                q = parse_qs(parsed.query).get("q", [""])[0]
                return self.send_json({"results": geocode_brunei(q)})
            except HTTPError as exc:
                return self.send_json({"error": _safe_http_error(exc)}, 502)
            except Exception as exc:
                return self.send_json({"error": f"Location search failed: {exc}"}, 502)

        if path == "/":
            html_path = BASE_DIR / "templates" / "index.html"
            html = html_path.read_text(encoding="utf-8")
            marker = "</body>"
            script = '<script src="/static/runtime-tools.js"></script>\n'
            if script not in html:
                html = html.replace(marker, script + marker)
            return self.send_bytes(html.encode("utf-8"), 200, "text/html; charset=utf-8")

        return super().do_GET()


app.SolarPassportHandler = RuntimeHandler


if __name__ == "__main__":
    configured = bool(app.NREL_API_KEY)
    print("Solar Passport launcher")
    print(f"Local .env: {'loaded' if loaded_env else 'not found'}")
    print(f"NREL PVWatts API key: {'present' if configured else 'missing — estimate mode'}")
    print(f"PVWatts endpoint: {PVWATTS_URL}")
    print("PVWatts failures will now be printed here instead of silently falling back.")
    app.run()
