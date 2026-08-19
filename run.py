from __future__ import annotations

import json
import os
import re
import threading
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

BASE_DIR = Path(__file__).resolve().parent

def load_local_env(path: Path) -> bool:
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

import app  # noqa: E402
import model_v2  # noqa: E402

PVWATTS_URL = "https://developer.nlr.gov/api/pvwatts/v8.json"
app.PVWATTS_URL = PVWATTS_URL
app.NREL_API_KEY = os.getenv("NREL_API_KEY", "").strip()

# PVWatts resource-profile cache. One 1-kWp resource profile is fetched per
# site/configuration and then scaled locally for every candidate system size.
CACHE_DIR = BASE_DIR / ".cache"
PV_CACHE_FILE = CACHE_DIR / "pvwatts_profiles.json"
PV_CACHE_MAX_AGE_DAYS = max(1, int(float(os.getenv("PV_CACHE_MAX_AGE_DAYS", "365"))))
CACHE_DIR.mkdir(exist_ok=True)

_pv_cache_lock = threading.Lock()
_pv_cache: dict[str, dict] = {}

def _load_pv_cache() -> None:
    global _pv_cache
    try:
        if PV_CACHE_FILE.exists():
            body = json.loads(PV_CACHE_FILE.read_text(encoding="utf-8"))
            if isinstance(body, dict):
                _pv_cache = body
    except Exception as exc:
        print(f"[PV CACHE] Could not load cache: {exc}")
        _pv_cache = {}

def _save_pv_cache() -> None:
    try:
        tmp = PV_CACHE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(_pv_cache, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
        tmp.replace(PV_CACHE_FILE)
    except Exception as exc:
        print(f"[PV CACHE] Could not save cache: {exc}")

_load_pv_cache()

_pvwatts_diag = {
    "configured": bool(app.NREL_API_KEY), "connected": False, "endpoint": PVWATTS_URL,
    "error": None, "station": None, "checked_at": None, "cache_status": None,
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

def _pv_cache_key(lat: float, lon: float, tilt: float, azimuth: float, losses: float) -> str:
    key = {
        "lat": round(float(lat), 4), "lon": round(float(lon), 4),
        "tilt": round(float(tilt), 2), "azimuth": round(float(azimuth), 2),
        "losses": round(float(losses), 2), "module_type": 0, "array_type": 1,
        "gcr": 0.4, "inv_eff": 96.0, "dc_ac_ratio": 1.2, "dataset": "nsrdb",
    }
    return json.dumps(key, sort_keys=True, separators=(",", ":"))

def _cache_entry_valid(entry: dict) -> bool:
    fetched = float(entry.get("fetched_at") or 0)
    return fetched > 0 and (time.time() - fetched) <= PV_CACHE_MAX_AGE_DAYS * 86400

def _scaled_generation(entry: dict, capacity_kwp: float, cache_status: str) -> dict:
    monthly_per_kwp = [float(x) for x in entry["monthly_per_kwp"]]
    annual_per_kwp = float(entry["annual_per_kwp"])
    return {
        "monthly_kwh": [x * capacity_kwp for x in monthly_per_kwp],
        "annual_kwh": annual_per_kwp * capacity_kwp,
        "capacity_factor": float(entry.get("capacity_factor") or (annual_per_kwp / 8760 * 100)),
        "source": "NREL PVWatts v8", "source_confidence": "Medium-High",
        "cache_status": cache_status,
    }

def pvwatts_generation(lat: float, lon: float, capacity_kwp: float, tilt: float,
                       azimuth: float, losses: float, specific_yield: float):
    global _pvwatts_diag
    capacity_kwp = max(0.0, float(capacity_kwp))
    key = _pv_cache_key(lat, lon, tilt, azimuth, losses)

    with _pv_cache_lock:
        entry = _pv_cache.get(key)
        if entry and _cache_entry_valid(entry):
            _pvwatts_diag = {
                "configured": bool(app.NREL_API_KEY), "connected": True, "endpoint": PVWATTS_URL,
                "error": None, "station": entry.get("station"), "checked_at": time.time(),
                "cache_status": "memory/disk cache",
            }
            return _scaled_generation(entry, capacity_kwp, "cache")

        if app.NREL_API_KEY:
            params = {
                "api_key": app.NREL_API_KEY, "lat": float(lat), "lon": float(lon),
                "system_capacity": 1.0, "module_type": 0, "array_type": 1,
                "tilt": float(tilt), "azimuth": float(azimuth), "losses": float(losses),
                "gcr": 0.4, "inv_eff": 96.0, "dc_ac_ratio": 1.2,
                "radius": 0, "dataset": "nsrdb",
            }
            req = Request(
                f"{PVWATTS_URL}?{urlencode(params)}",
                headers={"User-Agent": "SolarPassport-Brunei/0.4"},
            )
            try:
                started = time.perf_counter()
                with urlopen(req, timeout=20) as res:
                    body = json.loads(res.read().decode("utf-8"))
                elapsed = time.perf_counter() - started
                errors = body.get("errors") or []
                if errors:
                    raise RuntimeError("; ".join(str(x) for x in errors))
                outputs = body.get("outputs") or {}
                monthly = outputs.get("ac_monthly")
                if not monthly or len(monthly) != 12:
                    raise RuntimeError("PVWatts returned no 12-month AC generation series")
                annual = float(outputs.get("ac_annual", sum(monthly)))
                station = body.get("station_info") or {}
                entry = {
                    "monthly_per_kwp": [float(x) for x in monthly], "annual_per_kwp": annual,
                    "capacity_factor": float(outputs.get("capacity_factor", annual / 8760 * 100)),
                    "station": {
                        "lat": station.get("lat"), "lon": station.get("lon"),
                        "weather_data_source": station.get("weather_data_source"),
                        "distance": station.get("distance"),
                    },
                    "fetched_at": time.time(),
                }
                _pv_cache[key] = entry
                _save_pv_cache()
                _pvwatts_diag = {
                    "configured": True, "connected": True, "endpoint": PVWATTS_URL,
                    "error": None, "station": entry["station"], "checked_at": time.time(),
                    "cache_status": f"live API ({elapsed:.2f}s), now cached",
                }
                print(f"[PVWATTS] Resource profile fetched once in {elapsed:.2f}s and cached.")
                return _scaled_generation(entry, capacity_kwp, "live→cache")
            except HTTPError as exc:
                error = _safe_http_error(exc)
            except URLError as exc:
                error = f"Network error: {exc.reason}"
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"

            _pvwatts_diag = {
                "configured": True, "connected": False, "endpoint": PVWATTS_URL,
                "error": error, "station": None, "checked_at": time.time(), "cache_status": None,
            }
            print(f"[PVWATTS] Connection failed: {error}")
        else:
            _pvwatts_diag = {
                "configured": False, "connected": False, "endpoint": PVWATTS_URL,
                "error": "NREL_API_KEY is missing", "station": None,
                "checked_at": time.time(), "cache_status": None,
            }

    annual = capacity_kwp * max(0.0, float(specific_yield))
    shape = getattr(app, "DEFAULT_MONTHLY_SOLAR_SHAPE", [1/12] * 12)
    total_shape = sum(shape) or 1.0
    monthly = [annual * x / total_shape for x in shape]
    cf = annual / (capacity_kwp * 8760) * 100 if capacity_kwp > 0 else 0.0
    return {
        "monthly_kwh": monthly, "annual_kwh": annual, "capacity_factor": cf,
        "source": "MVP specific-yield fallback", "source_confidence": "Low-Medium",
        "cache_status": None,
    }

app.pvwatts_generation = pvwatts_generation
model_v2.configure_generation(pvwatts_generation)

# Location search. Results are cached and requests are user-triggered.
_geocode_cache = {}
_geocode_lock = threading.Lock()
_last_geocode_request = 0.0
BRUNEI_BOUNDS = {"south": 4.0, "north": 5.2, "west": 114.0, "east": 115.6}

def _inside_brunei(lat: float, lon: float) -> bool:
    return BRUNEI_BOUNDS["south"] <= lat <= BRUNEI_BOUNDS["north"] and BRUNEI_BOUNDS["west"] <= lon <= BRUNEI_BOUNDS["east"]

def _coordinate_result(q: str):
    m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)\s*", q)
    if not m:
        return None
    lat, lon = float(m.group(1)), float(m.group(2))
    if -90 <= lat <= 90 and -180 <= lon <= 180:
        return [{"display_name": f"Coordinates {lat:.5f}, {lon:.5f}", "lat": lat, "lon": lon, "type": "coordinates"}]
    return None

def _nominatim_search(q: str):
    params = {"q": q, "format": "jsonv2", "limit": 5, "countrycodes": "bn", "addressdetails": 1}
    contact_email = os.getenv("GEOCODER_CONTACT_EMAIL", "").strip()
    if contact_email:
        params["email"] = contact_email
    req = Request(
        f"https://nominatim.openstreetmap.org/search?{urlencode(params)}",
        headers={
            "User-Agent": "SolarPassport-Brunei/0.4 (local rooftop assessment; github.com/coralareef/solar-passport)",
            "Referer": "http://127.0.0.1:5000/", "Accept": "application/json",
        },
    )
    with urlopen(req, timeout=15) as res:
        raw = json.loads(res.read().decode("utf-8"))
    results = []
    for item in raw[:5]:
        try:
            result = {
                "display_name": item.get("display_name") or q,
                "lat": float(item["lat"]), "lon": float(item["lon"]), "type": item.get("type"),
            }
            bbox = item.get("boundingbox")
            if isinstance(bbox, list) and len(bbox) == 4:
                result["boundingbox"] = [float(x) for x in bbox]
            results.append(result)
        except (KeyError, TypeError, ValueError):
            continue
    return results

def _photon_search(q: str):
    params = urlencode({"q": q, "limit": 8, "lat": 4.9031, "lon": 114.9398, "lang": "en"})
    req = Request(
        f"https://photon.komoot.io/api/?{params}",
        headers={"User-Agent": "SolarPassport-Brunei/0.4", "Accept": "application/json"},
    )
    with urlopen(req, timeout=15) as res:
        raw = json.loads(res.read().decode("utf-8"))
    results = []
    for feature in raw.get("features", []):
        try:
            lon, lat = feature["geometry"]["coordinates"][:2]
            lat, lon = float(lat), float(lon)
            if not _inside_brunei(lat, lon):
                continue
            p = feature.get("properties") or {}
            parts = []
            for field in ("name", "street", "locality", "district", "city", "state", "country"):
                value = p.get(field)
                if value and value not in parts:
                    parts.append(str(value))
            results.append({
                "display_name": ", ".join(parts) or q, "lat": lat, "lon": lon,
                "type": p.get("type") or p.get("osm_value"),
            })
            if len(results) >= 5:
                break
        except (KeyError, TypeError, ValueError, IndexError):
            continue
    return results

def geocode_brunei(query: str):
    global _last_geocode_request
    q = " ".join((query or "").strip().split())[:200]
    if len(q) < 2:
        return {"results": [], "provider": None, "diagnostic": "Enter at least two characters."}
    coords = _coordinate_result(q)
    if coords is not None:
        return {"results": coords, "provider": "coordinates", "diagnostic": None}
    cache_key = q.casefold()
    if cache_key in _geocode_cache:
        return _geocode_cache[cache_key]

    errors = []
    with _geocode_lock:
        wait = 1.05 - (time.monotonic() - _last_geocode_request)
        if wait > 0:
            time.sleep(wait)
        for provider, fn in (("OpenStreetMap Nominatim", _nominatim_search), ("Photon", _photon_search)):
            try:
                results = fn(q)
                _last_geocode_request = time.monotonic()
                if results:
                    response = {"results": results, "provider": provider, "diagnostic": None}
                    _geocode_cache[cache_key] = response
                    return response
                errors.append(f"{provider}: no Brunei matches")
            except HTTPError as exc:
                errors.append(f"{provider}: {_safe_http_error(exc)}")
            except URLError as exc:
                errors.append(f"{provider}: network error: {exc.reason}")
            except Exception as exc:
                errors.append(f"{provider}: {type(exc).__name__}: {exc}")
    diagnostic = " | ".join(errors)
    print(f"[GEOCODE] Search failed for {q!r}: {diagnostic}")
    return {"results": [], "provider": None, "diagnostic": diagnostic}

BaseHandler = app.SolarPassportHandler

class RuntimeHandler(BaseHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/pvwatts/status":
            pvwatts_generation(4.9031, 114.9398, 4.0, 10.0, 180.0, 14.0, 1420.0)
            return self.send_json(dict(_pvwatts_diag))
        if path == "/api/geocode":
            try:
                q = parse_qs(parsed.query).get("q", [""])[0]
                return self.send_json(geocode_brunei(q))
            except Exception as exc:
                print(f"[GEOCODE] Endpoint error: {type(exc).__name__}: {exc}")
                return self.send_json({"results": [], "provider": None, "diagnostic": f"Location search failed: {exc}"}, 502)
        if path == "/":
            html_path = BASE_DIR / "templates" / "index.html"
            html = html_path.read_text(encoding="utf-8")
            marker = "</body>"
            scripts = '<script src="/static/runtime-tools.js"></script>\n<script src="/static/v2-ui.js"></script>\n'
            if "/static/v2-ui.js" not in html:
                html = html.replace(marker, scripts + marker)
            return self.send_bytes(html.encode("utf-8"), 200, "text/html; charset=utf-8")
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 2_000_000:
                return self.send_json({"error": "Request too large"}, 413)
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            if not isinstance(payload, dict):
                raise ValueError("JSON body must be an object")

            if path == "/api/building/calculate":
                if payload.get("site_name") == "Connection test":
                    g = pvwatts_generation(
                        float(payload.get("lat", 4.9031)), float(payload.get("lon", 114.9398)),
                        1.0, float(payload.get("tilt", 10)), float(payload.get("azimuth", 180)),
                        float(payload.get("losses", 14)), float(payload.get("specific_yield", 1420)),
                    )
                    return self.send_json({"recommendation": {"selected": {
                        "generation_source": g["source"], "generation_confidence": g["source_confidence"]
                    }}})
                started = time.perf_counter()
                result = model_v2.api_building(payload)
                elapsed = time.perf_counter() - started
                cache_status = result.get("recommendation", {}).get("selected", {}).get("generation_cache")
                print(f"[MODEL] Building Passport completed in {elapsed:.3f}s (solar profile: {cache_status or 'fallback'}).")
                return self.send_json(result)

            if path == "/api/project/calculate":
                started = time.perf_counter()
                result = model_v2.api_project(payload)
                elapsed = time.perf_counter() - started
                print(f"[MODEL] Project Passport completed in {elapsed:.3f}s.")
                result["readiness"]["readiness_status"] = result["readiness"]["status"]
                result["readiness"]["status"] = result["overall_status"]
                return self.send_json(result)

            return self.send_json({"error": "Not found"}, 404)
        except ValueError as exc:
            return self.send_json({"error": str(exc)}, 400)
        except Exception as exc:
            print(f"[MODEL] Error: {type(exc).__name__}: {exc}")
            return self.send_json({"error": f"Calculation failed: {exc}"}, 500)

app.SolarPassportHandler = RuntimeHandler
app.api_building = model_v2.api_building
app.api_project = model_v2.api_project

if __name__ == "__main__":
    print("Solar Passport launcher")
    print(f"Local .env: {'loaded' if loaded_env else 'not found'}")
    print(f"NREL PVWatts API key: {'present' if app.NREL_API_KEY else 'missing — estimate mode'}")
    print(f"PVWatts endpoint: {PVWATTS_URL}")
    print(f"PV resource cache: {len(_pv_cache)} stored profile(s), max age {PV_CACHE_MAX_AGE_DAYS} days")
    print("Building runs now reuse one cached PV resource profile instead of calling PVWatts for every candidate size.")
    app.run()
