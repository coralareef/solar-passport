from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Optional

from .intervals import IntervalPoint, resample_hourly, match_load_and_pv, aggregate_by_month
from .net_metering import NetMeteringLedger
from .tariffs import TariffEngine
from .solar import PVWattsProfile

@dataclass(frozen=True)
class BuildingMonth:
    month: str
    load_kwh: float
    pv_kwh: float
    self_consumed_kwh: float
    grid_import_kwh: float
    grid_export_kwh: float
    baseline_bill_bnd: float
    post_solar_bill_bnd: float
    credit_opening_kwh: float
    credit_closing_kwh: float
    credit_forfeited_kwh: float

@dataclass(frozen=True)
class BuildingEnergyResult:
    capacity_kwp: float
    annual_load_kwh: float
    annual_pv_kwh: float
    self_consumed_kwh: float
    self_consumption_pct: float
    solar_load_coverage_pct: float
    grid_import_kwh: float
    grid_export_kwh: float
    baseline_bill_bnd: float
    post_solar_bill_bnd: float
    annual_saving_bnd: float
    months: tuple[BuildingMonth, ...]
    interval_count: int

def _is_non_leap(year: int) -> bool:
    return not (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))

def pv_profile_to_typical_year_points(profile: PVWattsProfile, capacity_kwp: float, *, year: int = 2025) -> tuple[IntervalPoint, ...]:
    if profile.hourly_kwh_per_kwp is None: raise ValueError("PVWatts profile does not contain hourly output")
    start = datetime(year if len(profile.hourly_kwh_per_kwp) == 8760 and _is_non_leap(year) else (2025 if len(profile.hourly_kwh_per_kwp) == 8760 else 2024), 1, 1)
    return tuple(IntervalPoint(start + timedelta(hours=i), v * capacity_kwp) for i, v in enumerate(profile.hourly_kwh_per_kwp))

def _canonicalize_hourly(points: Iterable[IntervalPoint], canonical_year: int = 2025) -> tuple[IntervalPoint, ...]:
    buckets: dict[datetime, list[float]] = {}
    for p in resample_hourly(points):
        if p.timestamp.month == 2 and p.timestamp.day == 29: continue
        ts = datetime(canonical_year, p.timestamp.month, p.timestamp.day, p.timestamp.hour)
        buckets.setdefault(ts, []).append(p.kwh)
    return tuple(IntervalPoint(ts, sum(vals) / len(vals)) for ts, vals in sorted(buckets.items()))

def analyze_hourly_building(*, load_points: Iterable[IntervalPoint], pv_profile: PVWattsProfile, capacity_kwp: float, tariff_engine: TariffEngine, tariff: str, subscribed_kva: Optional[float] = None, net_metering: bool = True, rollover_months: int = 12) -> BuildingEnergyResult:
    if capacity_kwp <= 0: raise ValueError("capacity_kwp must be > 0")
    load = _canonicalize_hourly(load_points)
    if not load: raise ValueError("No load intervals available after normalization")
    pv = pv_profile_to_typical_year_points(pv_profile, capacity_kwp, year=2025)
    pv_map = {p.timestamp: p for p in pv}
    pv_subset = tuple(pv_map[p.timestamp] for p in load if p.timestamp in pv_map)
    matches = match_load_and_pv(load, pv_subset)
    monthly = aggregate_by_month(matches)
    ledger = NetMeteringLedger(tariff_engine, tariff, subscribed_kva=subscribed_kva, rollover_months=rollover_months)
    months = []
    baseline_total = post_total = 0.0
    for key in sorted(monthly):
        m = monthly[key]
        baseline = tariff_engine.bill(tariff, m["load_kwh"], subscribed_kva).amount_bnd
        if net_metering:
            settlement = ledger.settle(m["grid_import_kwh"], m["grid_export_kwh"])
            post, opening, closing, forfeited = settlement.bill_bnd, settlement.credit_opening_kwh, settlement.credit_closing_kwh, settlement.forfeited_kwh
        else:
            post = tariff_engine.bill(tariff, m["grid_import_kwh"], subscribed_kva).amount_bnd
            opening = closing = forfeited = 0.0
        baseline_total += baseline
        post_total += post
        months.append(BuildingMonth(key, m["load_kwh"], m["pv_kwh"], m["self_consumed_kwh"], m["grid_import_kwh"], m["grid_export_kwh"], baseline, post, opening, closing, forfeited))
    annual_load = sum(x.load_kwh for x in months)
    annual_pv = sum(x.pv_kwh for x in months)
    self_use = sum(x.self_consumed_kwh for x in months)
    imports = sum(x.grid_import_kwh for x in months)
    exports = sum(x.grid_export_kwh for x in months)
    return BuildingEnergyResult(float(capacity_kwp), annual_load, annual_pv, self_use, 100*self_use/annual_pv if annual_pv else 0.0, 100*self_use/annual_load if annual_load else 0.0, imports, exports, baseline_total, post_total, baseline_total-post_total, tuple(months), len(load))
