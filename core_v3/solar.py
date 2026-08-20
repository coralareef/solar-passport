from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PVWATTS_V8_URL = "https://developer.nlr.gov/api/pvwatts/v8.json"

@dataclass(frozen=True)
class PVWattsProfile:
    lat: float
    lon: float
    tilt: float
    azimuth: float
    losses_pct: float
    annual_kwh_per_kwp: float
    monthly_kwh_per_kwp: tuple[float, ...]
    hourly_kwh_per_kwp: tuple[float, ...] | None
    capacity_factor_pct: float
    weather_data_source: str | None
    station_distance_m: float | None
    source: str = "NLR PVWatts v8"

class PVWattsError(RuntimeError): pass

class PVWattsClient:
    """PVWatts v8 client using one-kWp profiles and persistent caching."""
    def __init__(self, api_key: str | None = None, *, cache_path: str | Path | None = None, timeout: float = 30.0):
        self.api_key = (api_key or os.getenv("NREL_API_KEY", "")).strip()
        self.timeout = timeout
        self.cache_path = Path(cache_path) if cache_path else None
        self._cache = self._load_cache()

    def _load_cache(self) -> dict:
        if self.cache_path and self.cache_path.exists():
            try: return json.loads(self.cache_path.read_text(encoding="utf-8"))
            except Exception: return {}
        return {}

    def _save_cache(self) -> None:
        if not self.cache_path: return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.cache_path.with_suffix(self.cache_path.suffix + ".tmp")
        tmp.write_text(json.dumps(self._cache, separators=(",", ":")), encoding="utf-8")
        tmp.replace(self.cache_path)

    @staticmethod
    def _cache_key(params: dict) -> str:
        return hashlib.sha256(json.dumps(params, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def profile(self, *, lat: float, lon: float, tilt: float = 10.0, azimuth: float = 180.0, losses_pct: float = 14.0, array_type: int = 1, module_type: int = 0, dc_ac_ratio: float = 1.2, inv_eff: float = 96.0, gcr: float = 0.4, dataset: str = "nsrdb", hourly: bool = False, force_refresh: bool = False) -> PVWattsProfile:
        if not self.api_key: raise PVWattsError("NREL_API_KEY is not configured")
        params = {"lat": round(float(lat), 5), "lon": round(float(lon), 5), "tilt": float(tilt), "azimuth": float(azimuth), "losses": float(losses_pct), "array_type": int(array_type), "module_type": int(module_type), "dc_ac_ratio": float(dc_ac_ratio), "inv_eff": float(inv_eff), "gcr": float(gcr), "dataset": dataset, "timeframe": "hourly" if hourly else "monthly", "system_capacity": 1.0, "radius": 0}
        key = self._cache_key(params)
        if not force_refresh and key in self._cache: return self._decode(self._cache[key])
        req = Request(f"{PVWATTS_V8_URL}?{urlencode({**params, 'api_key': self.api_key})}", headers={"User-Agent": "SolarPassport-Brunei-CoreV3/1.0"})
        started = time.perf_counter()
        try:
            with urlopen(req, timeout=self.timeout) as response: payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            try: detail = exc.read().decode("utf-8", errors="replace")[:500]
            except Exception: detail = str(exc.reason)
            raise PVWattsError(f"PVWatts HTTP {exc.code}: {detail}") from exc
        except URLError as exc: raise PVWattsError(f"PVWatts network error: {exc.reason}") from exc
        errors = payload.get("errors") or []
        if errors: raise PVWattsError("; ".join(str(x) for x in errors))
        outputs = payload.get("outputs") or {}
        monthly = tuple(float(x) for x in outputs.get("ac_monthly") or ())
        if len(monthly) != 12: raise PVWattsError("PVWatts returned no 12-month AC profile")
        hourly_kwh = None
        if hourly:
            ac_w = outputs.get("ac") or []
            if len(ac_w) not in {8760, 8784}: raise PVWattsError(f"Expected 8760/8784 hourly AC values; got {len(ac_w)}")
            hourly_kwh = tuple(float(w) / 1000.0 for w in ac_w)
        station = payload.get("station_info") or {}
        item = {"lat": float(params["lat"]), "lon": float(params["lon"]), "tilt": float(tilt), "azimuth": float(azimuth), "losses_pct": float(losses_pct), "annual_kwh_per_kwp": float(outputs.get("ac_annual", sum(monthly))), "monthly_kwh_per_kwp": monthly, "hourly_kwh_per_kwp": hourly_kwh, "capacity_factor_pct": float(outputs.get("capacity_factor", 0.0)), "weather_data_source": station.get("weather_data_source"), "station_distance_m": station.get("distance"), "fetched_seconds": time.perf_counter() - started, "cached_at_epoch": time.time()}
        self._cache[key] = item
        self._save_cache()
        return self._decode(item)

    @staticmethod
    def _decode(raw: dict) -> PVWattsProfile:
        hourly = raw.get("hourly_kwh_per_kwp")
        return PVWattsProfile(float(raw["lat"]), float(raw["lon"]), float(raw["tilt"]), float(raw["azimuth"]), float(raw["losses_pct"]), float(raw["annual_kwh_per_kwp"]), tuple(raw["monthly_kwh_per_kwp"]), tuple(hourly) if hourly is not None else None, float(raw["capacity_factor_pct"]), raw.get("weather_data_source"), raw.get("station_distance_m"))
