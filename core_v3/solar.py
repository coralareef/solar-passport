from __future__ import annotations

import calendar
import hashlib
import json
import os
import threading
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
    hourly_annual_reconciliation_error_pct: float | None = None
    hourly_monthly_max_reconciliation_error_pct: float | None = None

class PVWattsError(RuntimeError):
    pass

class PVWattsClient:
    """PVWatts v8 client using one-kWp profiles and persistent caching.

    The client is safe for the current threaded local server: cache reads/writes
    and live fetches are serialized with a re-entrant lock. A future multi-process
    deployment should replace this JSON cache with a shared cache/database.
    """
    def __init__(self, api_key: str | None = None, *, cache_path: str | Path | None = None, timeout: float = 30.0, cache_max_age_days: float | None = None):
        self.api_key = (api_key or os.getenv("NREL_API_KEY", "")).strip()
        self.timeout = float(timeout)
        self.cache_path = Path(cache_path) if cache_path else None
        self.cache_max_age_days = float(cache_max_age_days if cache_max_age_days is not None else os.getenv("PV_CACHE_MAX_AGE_DAYS", "365"))
        if self.cache_max_age_days <= 0:
            raise ValueError("cache_max_age_days must be > 0")
        self._lock = threading.RLock()
        self._cache = self._load_cache()

    def _load_cache(self) -> dict:
        if self.cache_path and self.cache_path.exists():
            try:
                body = json.loads(self.cache_path.read_text(encoding="utf-8"))
                return body if isinstance(body, dict) else {}
            except Exception:
                return {}
        return {}

    def _save_cache(self) -> None:
        if not self.cache_path:
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.cache_path.with_suffix(self.cache_path.suffix + ".tmp")
        tmp.write_text(json.dumps(self._cache, separators=(",", ":")), encoding="utf-8")
        tmp.replace(self.cache_path)

    @staticmethod
    def _cache_key(params: dict) -> str:
        versioned = {"pvwatts_api": "v8", **params}
        return hashlib.sha256(json.dumps(versioned, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def _cache_entry_valid(self, raw: dict) -> bool:
        cached_at = float(raw.get("cached_at_epoch") or 0.0)
        if cached_at <= 0:
            return False
        return (time.time() - cached_at) <= self.cache_max_age_days * 86400

    @staticmethod
    def _reconcile_hourly(hourly_kwh: tuple[float, ...], monthly_kwh: tuple[float, ...], annual_kwh: float) -> tuple[float, float]:
        if len(hourly_kwh) not in {8760, 8784}:
            raise PVWattsError(f"Expected 8760/8784 hourly points; got {len(hourly_kwh)}")
        hourly_total = sum(hourly_kwh)
        annual_denominator = max(abs(annual_kwh), 1e-9)
        annual_error_pct = abs(hourly_total - annual_kwh) / annual_denominator * 100

        year = 2024 if len(hourly_kwh) == 8784 else 2025
        cursor = 0
        monthly_errors = []
        for month in range(1, 13):
            hours = calendar.monthrange(year, month)[1] * 24
            subtotal = sum(hourly_kwh[cursor:cursor + hours])
            cursor += hours
            reported = monthly_kwh[month - 1]
            if abs(reported) < 1e-9:
                error = 0.0 if abs(subtotal) < 1e-9 else 100.0
            else:
                error = abs(subtotal - reported) / abs(reported) * 100
            monthly_errors.append(error)
        max_monthly_error_pct = max(monthly_errors, default=0.0)
        return annual_error_pct, max_monthly_error_pct

    def profile(self, *, lat: float, lon: float, tilt: float = 10.0, azimuth: float = 180.0, losses_pct: float = 14.0, array_type: int = 1, module_type: int = 0, dc_ac_ratio: float = 1.2, inv_eff: float = 96.0, gcr: float = 0.4, dataset: str = "nsrdb", hourly: bool = False, force_refresh: bool = False) -> PVWattsProfile:
        if not self.api_key:
            raise PVWattsError("NREL_API_KEY is not configured")
        if not -90 <= float(lat) <= 90 or not -180 <= float(lon) <= 180:
            raise ValueError("Invalid latitude/longitude")
        if not 0 <= float(losses_pct) < 100:
            raise ValueError("losses_pct must be in [0,100)")
        if float(dc_ac_ratio) <= 0 or float(inv_eff) <= 0 or not 0 < float(gcr) <= 1:
            raise ValueError("dc_ac_ratio, inv_eff and gcr must be positive; gcr must be <= 1")

        params = {
            "lat": round(float(lat), 5), "lon": round(float(lon), 5),
            "tilt": float(tilt), "azimuth": float(azimuth), "losses": float(losses_pct),
            "array_type": int(array_type), "module_type": int(module_type),
            "dc_ac_ratio": float(dc_ac_ratio), "inv_eff": float(inv_eff), "gcr": float(gcr),
            "dataset": dataset, "timeframe": "hourly" if hourly else "monthly",
            "system_capacity": 1.0, "radius": 0,
        }
        key = self._cache_key(params)

        with self._lock:
            cached = self._cache.get(key)
            if not force_refresh and cached and self._cache_entry_valid(cached):
                return self._decode(cached)

            req = Request(
                f"{PVWATTS_V8_URL}?{urlencode({**params, 'api_key': self.api_key})}",
                headers={"User-Agent": "SolarPassport-Brunei-CoreV3/1.0"},
            )
            started = time.perf_counter()
            try:
                with urlopen(req, timeout=self.timeout) as response:
                    payload = json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                try:
                    detail = exc.read().decode("utf-8", errors="replace")[:500]
                except Exception:
                    detail = str(exc.reason)
                raise PVWattsError(f"PVWatts HTTP {exc.code}: {detail}") from exc
            except URLError as exc:
                raise PVWattsError(f"PVWatts network error: {exc.reason}") from exc

            errors = payload.get("errors") or []
            if errors:
                raise PVWattsError("; ".join(str(x) for x in errors))
            outputs = payload.get("outputs") or {}
            monthly = tuple(float(x) for x in outputs.get("ac_monthly") or ())
            if len(monthly) != 12:
                raise PVWattsError("PVWatts returned no 12-month AC profile")
            annual = float(outputs.get("ac_annual", sum(monthly)))

            hourly_kwh = None
            annual_recon = monthly_recon = None
            if hourly:
                ac_w = outputs.get("ac") or []
                if len(ac_w) not in {8760, 8784}:
                    raise PVWattsError(f"Expected 8760/8784 hourly AC values; got {len(ac_w)}")
                hourly_kwh = tuple(float(w) / 1000.0 for w in ac_w)
                annual_recon, monthly_recon = self._reconcile_hourly(hourly_kwh, monthly, annual)
                # This catches unit/timeframe corruption while allowing harmless
                # API rounding differences between hourly and aggregate outputs.
                if annual_recon > 1.0 or monthly_recon > 1.5:
                    raise PVWattsError(
                        f"PVWatts hourly profile did not reconcile with aggregate outputs "
                        f"(annual error {annual_recon:.3f}%, max monthly error {monthly_recon:.3f}%)."
                    )

            station = payload.get("station_info") or {}
            item = {
                "lat": float(params["lat"]), "lon": float(params["lon"]),
                "tilt": float(tilt), "azimuth": float(azimuth), "losses_pct": float(losses_pct),
                "annual_kwh_per_kwp": annual, "monthly_kwh_per_kwp": monthly,
                "hourly_kwh_per_kwp": hourly_kwh,
                "capacity_factor_pct": float(outputs.get("capacity_factor", 0.0)),
                "weather_data_source": station.get("weather_data_source"),
                "station_distance_m": station.get("distance"),
                "hourly_annual_reconciliation_error_pct": annual_recon,
                "hourly_monthly_max_reconciliation_error_pct": monthly_recon,
                "fetched_seconds": time.perf_counter() - started,
                "cached_at_epoch": time.time(),
            }
            self._cache[key] = item
            self._save_cache()
            return self._decode(item)

    @staticmethod
    def _decode(raw: dict) -> PVWattsProfile:
        hourly = raw.get("hourly_kwh_per_kwp")
        return PVWattsProfile(
            float(raw["lat"]), float(raw["lon"]), float(raw["tilt"]), float(raw["azimuth"]),
            float(raw["losses_pct"]), float(raw["annual_kwh_per_kwp"]),
            tuple(raw["monthly_kwh_per_kwp"]), tuple(hourly) if hourly is not None else None,
            float(raw["capacity_factor_pct"]), raw.get("weather_data_source"), raw.get("station_distance_m"),
            "NLR PVWatts v8", raw.get("hourly_annual_reconciliation_error_pct"), raw.get("hourly_monthly_max_reconciliation_error_pct"),
        )
