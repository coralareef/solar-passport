from __future__ import annotations

"""Deterministic synthetic load profiles for Core v3 pipeline testing.

These are NOT empirical Brunei load profiles and must never be labelled as such.
They exist to test parsing, hourly matching, tariff settlement, edge conditions and
performance before anonymized Brunei meter data is available.
"""

import csv
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class SyntheticArchetype:
    id: str
    label: str
    annual_kwh: float
    notes: str
    hourly_shape: Callable[[datetime], float]


def _seasonal(ts: datetime, amplitude: float = 0.06) -> float:
    # Small deterministic annual modulation. It is a test fixture, not a Brunei
    # climatological calibration.
    return 1.0 + amplitude * math.sin(2 * math.pi * (ts.timetuple().tm_yday - 40) / 365.0)


def _residential(ts: datetime) -> float:
    h = ts.hour + ts.minute / 60
    base = 0.25
    morning = 0.85 * math.exp(-((h - 7.0) / 1.5) ** 2)
    evening = 1.55 * math.exp(-((h - 20.0) / 2.2) ** 2)
    midday = 0.35 * math.exp(-((h - 13.0) / 2.8) ** 2)
    weekend = 1.10 if ts.weekday() >= 5 else 1.0
    return max(0.02, (base + morning + midday + evening) * weekend * _seasonal(ts, 0.04))


def _commercial(ts: datetime) -> float:
    h = ts.hour + ts.minute / 60
    weekday = ts.weekday() < 6  # Saturday remains partly active for the test case.
    if weekday:
        occupied = 1.0 if 8 <= h < 18 else 0.20
        lunch = 0.18 * math.exp(-((h - 12.5) / 1.5) ** 2)
        morning_ramp = 0.20 * math.exp(-((h - 8.5) / 1.2) ** 2)
        value = occupied + lunch + morning_ramp
    else:
        value = 0.16
    return max(0.02, value * _seasonal(ts, 0.07))


def _large_ci(ts: datetime) -> float:
    h = ts.hour + ts.minute / 60
    # Continuous industrial/commercial process with a daytime production uplift.
    base = 0.62
    daytime = 0.42 if 7 <= h < 19 else 0.0
    weekday = 1.0 if ts.weekday() < 6 else 0.82
    return max(0.05, (base + daytime) * weekday * _seasonal(ts, 0.03))


ARCHETYPES = {
    "residential": SyntheticArchetype(
        "residential", "Synthetic residential", 9_600,
        "Evening-peaking household test profile; not empirical Brunei data.", _residential,
    ),
    "commercial": SyntheticArchetype(
        "commercial", "Synthetic commercial", 120_000,
        "Daytime business profile suitable for testing Tariff B and rooftop self-consumption.", _commercial,
    ),
    "large_ci": SyntheticArchetype(
        "large_ci", "Synthetic large C&I", 1_200_000,
        "High-load continuous process profile used for parser/PV-matching stress tests. Tariff applicability must be separately established.", _large_ci,
    ),
}


def generate_hourly(archetype: str, *, year: int = 2025, annual_kwh: float | None = None) -> list[tuple[datetime, float]]:
    spec = ARCHETYPES[archetype]
    start = datetime(year, 1, 1)
    end = datetime(year + 1, 1, 1)
    timestamps: list[datetime] = []
    weights: list[float] = []
    ts = start
    while ts < end:
        timestamps.append(ts)
        weights.append(spec.hourly_shape(ts))
        ts += timedelta(hours=1)
    target = float(annual_kwh if annual_kwh is not None else spec.annual_kwh)
    scale = target / sum(weights)
    return [(t, w * scale) for t, w in zip(timestamps, weights)]


def generate_15min(archetype: str, *, year: int = 2025, annual_kwh: float | None = None) -> list[tuple[datetime, float]]:
    # Split each deterministic hourly value evenly into four intervals. This is
    # intentionally simple because the fixture tests interval parsing/resampling,
    # not intra-hour customer behaviour.
    out: list[tuple[datetime, float]] = []
    for ts, hourly_kwh in generate_hourly(archetype, year=year, annual_kwh=annual_kwh):
        for quarter in range(4):
            out.append((ts + timedelta(minutes=15 * quarter), hourly_kwh / 4.0))
    return out


def write_csv(path: str | Path, points: list[tuple[datetime, float]]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "load_kwh"])
        for ts, kwh in points:
            writer.writerow([ts.strftime("%Y-%m-%d %H:%M:%S"), f"{kwh:.8f}"])
    return path


def build_validation_pack(output_dir: str | Path, *, year: int = 2025) -> list[Path]:
    output = Path(output_dir)
    files = []
    for name in ARCHETYPES:
        files.append(write_csv(output / f"synthetic_{name}_{year}_hourly.csv", generate_hourly(name, year=year)))
    # One 15-minute file proves the higher-resolution ingestion path without
    # committing a large fixture to Git.
    files.append(write_csv(output / f"synthetic_commercial_{year}_15min.csv", generate_15min("commercial", year=year)))
    return files


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate synthetic Solar Passport validation load profiles")
    parser.add_argument("--output", default="validation/generated", help="Output directory")
    parser.add_argument("--year", type=int, default=2025)
    args = parser.parse_args()
    for file in build_validation_pack(args.output, year=args.year):
        print(file)
