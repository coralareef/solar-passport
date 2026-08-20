from __future__ import annotations

import csv
import io
import statistics
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional

_TIMESTAMP_NAMES = {"timestamp", "datetime", "date_time", "time", "date/time", "interval_start"}
_ENERGY_NAMES = {"kwh", "energy_kwh", "consumption_kwh", "usage_kwh", "load_kwh"}
_POWER_NAMES = {"kw", "power_kw", "demand_kw", "load_kw"}
_DUPLICATE_POLICIES = {"error", "first", "last", "average", "sum"}

@dataclass(frozen=True)
class IntervalPoint:
    timestamp: datetime
    kwh: float

@dataclass(frozen=True)
class IntervalParseReport:
    points: tuple[IntervalPoint, ...]
    inferred_interval_minutes: float
    source_value_type: str
    duplicate_rows: int
    skipped_rows: int
    missing_intervals_estimate: int
    completeness_pct: float
    duplicate_policy: str

@dataclass(frozen=True)
class EnergyMatch:
    timestamp: datetime
    load_kwh: float
    pv_kwh: float
    self_consumed_kwh: float
    grid_import_kwh: float
    grid_export_kwh: float

def _parse_dt(value: str) -> datetime:
    text = value.strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized timestamp: {value!r}")

def _find_column(fieldnames: list[str], candidates: set[str]) -> Optional[str]:
    normalized = {x.strip().lower(): x for x in fieldnames}
    for key in candidates:
        if key in normalized:
            return normalized[key]
    return None

def _resolve_duplicate(values: list[float], policy: str) -> float:
    if policy == "first": return values[0]
    if policy == "last": return values[-1]
    if policy == "average": return sum(values) / len(values)
    if policy == "sum": return sum(values)
    raise ValueError("Duplicate timestamp found. Choose an explicit duplicate_policy: first, last, average, or sum.")

def parse_load_csv(text: str, *, timestamp_column: Optional[str] = None, value_column: Optional[str] = None, value_type: Optional[str] = None, duplicate_policy: str = "error") -> IntervalParseReport:
    duplicate_policy = duplicate_policy.strip().lower()
    if duplicate_policy not in _DUPLICATE_POLICIES:
        raise ValueError(f"duplicate_policy must be one of {sorted(_DUPLICATE_POLICIES)}")
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    if not reader.fieldnames:
        raise ValueError("CSV has no header row")
    fields = list(reader.fieldnames)
    ts_col = timestamp_column or _find_column(fields, _TIMESTAMP_NAMES)
    if not ts_col:
        raise ValueError("Could not identify timestamp column")
    if value_column:
        val_col = value_column
        kind = (value_type or "kwh").lower()
    else:
        val_col = _find_column(fields, _ENERGY_NAMES)
        kind = "kwh"
        if not val_col:
            val_col = _find_column(fields, _POWER_NAMES)
            kind = "kw"
    if not val_col:
        raise ValueError("Could not identify kWh or kW value column")
    if kind not in {"kwh", "kw"}:
        raise ValueError("value_type must be 'kwh' or 'kw'")

    rows: list[tuple[datetime, float]] = []
    skipped = 0
    for row in reader:
        try:
            ts = _parse_dt(row[ts_col])
            value = float(str(row[val_col]).replace(",", "").strip())
            if value < 0:
                raise ValueError("negative load")
            rows.append((ts, value))
        except Exception:
            skipped += 1
    if len(rows) < 2:
        raise ValueError("At least two valid interval rows are required")
    rows.sort(key=lambda x: x[0])

    grouped: dict[datetime, list[float]] = {}
    for ts, value in rows:
        grouped.setdefault(ts, []).append(value)
    duplicates = sum(max(0, len(v) - 1) for v in grouped.values())
    if duplicates and duplicate_policy == "error":
        duplicate_timestamps = [ts.isoformat() for ts, values in grouped.items() if len(values) > 1]
        preview = ", ".join(duplicate_timestamps[:5])
        suffix = " ..." if len(duplicate_timestamps) > 5 else ""
        raise ValueError(f"CSV contains {duplicates} duplicate row(s) at timestamp(s): {preview}{suffix}. Resolve the source data or choose an explicit duplicate_policy.")

    ordered_raw = []
    for ts in sorted(grouped):
        values = grouped[ts]
        value = values[0] if len(values) == 1 else _resolve_duplicate(values, duplicate_policy)
        ordered_raw.append((ts, value))

    deltas = [(b[0] - a[0]).total_seconds() / 60 for a, b in zip(ordered_raw, ordered_raw[1:]) if b[0] > a[0]]
    interval_minutes = statistics.median(deltas)
    if interval_minutes <= 0 or interval_minutes > 24 * 60:
        raise ValueError("Could not infer a plausible interval duration")
    hours = interval_minutes / 60
    points = tuple(IntervalPoint(ts, value if kind == "kwh" else value * hours) for ts, value in ordered_raw)
    span_minutes = (ordered_raw[-1][0] - ordered_raw[0][0]).total_seconds() / 60
    expected = int(round(span_minutes / interval_minutes)) + 1
    missing = max(0, expected - len(points))
    completeness = 100.0 * len(points) / expected if expected else 100.0
    return IntervalParseReport(points, interval_minutes, kind, duplicates, skipped, missing, completeness, duplicate_policy)

def resample_hourly(points: Iterable[IntervalPoint]) -> tuple[IntervalPoint, ...]:
    buckets: dict[datetime, float] = {}
    for p in points:
        hour = p.timestamp.replace(minute=0, second=0, microsecond=0)
        buckets[hour] = buckets.get(hour, 0.0) + p.kwh
    return tuple(IntervalPoint(ts, buckets[ts]) for ts in sorted(buckets))

def match_load_and_pv(load: Iterable[IntervalPoint], pv: Iterable[IntervalPoint]) -> tuple[EnergyMatch, ...]:
    load_map = {x.timestamp: x.kwh for x in load}
    pv_map = {x.timestamp: x.kwh for x in pv}
    timestamps = sorted(set(load_map) | set(pv_map))
    out = []
    for ts in timestamps:
        l = max(0.0, load_map.get(ts, 0.0))
        s = max(0.0, pv_map.get(ts, 0.0))
        self_use = min(l, s)
        out.append(EnergyMatch(ts, l, s, self_use, max(0.0, l - s), max(0.0, s - l)))
    return tuple(out)

def aggregate_by_month(matches: Iterable[EnergyMatch]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for x in matches:
        key = x.timestamp.strftime("%Y-%m")
        row = out.setdefault(key, {"load_kwh": 0.0, "pv_kwh": 0.0, "self_consumed_kwh": 0.0, "grid_import_kwh": 0.0, "grid_export_kwh": 0.0})
        row["load_kwh"] += x.load_kwh
        row["pv_kwh"] += x.pv_kwh
        row["self_consumed_kwh"] += x.self_consumed_kwh
        row["grid_import_kwh"] += x.grid_import_kwh
        row["grid_export_kwh"] += x.grid_export_kwh
    return out
