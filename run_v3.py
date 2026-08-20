from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import run  # loads .env and preserves the current UI/runtime helpers
import app
from core_v3 import (
    PolicyRegistry, TariffEngine, NetMeteringLedger, parse_load_csv,
    ProjectFinanceInputs, model_project_finance, solve_tariff, debt_capacity_for_dscr,
    PVWattsClient, analyze_hourly_building, validate_net_metering_eligibility,
)

BASE_DIR = Path(__file__).resolve().parent
CORE_V3_VERSION = "3.0.0-alpha.1"
REGISTRY = PolicyRegistry.from_path(BASE_DIR / "data" / "policy_registry.json")
TARIFFS = TariffEngine(REGISTRY)
PVWATTS = PVWattsClient(cache_path=BASE_DIR / ".cache" / "core_v3_pvwatts.json")
BaseHandler = run.RuntimeHandler

POLICY_SNAPSHOT_IDS = [
    "NM_CAPACITY_RANGE", "NM_CUSTOMER_ELIGIBILITY", "NM_CREDIT_SETTLEMENT",
    "DES_TARIFF_A", "DES_TARIFF_B",
]

def _json_safe(value):
    if hasattr(value, "__dataclass_fields__"):
        return {k: _json_safe(v) for k, v in asdict(value).items()}
    if isinstance(value, dict): return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [_json_safe(v) for v in value]
    return value

def _finance_inputs(payload: dict) -> ProjectFinanceInputs:
    allowed = set(ProjectFinanceInputs.__dataclass_fields__)
    values = {k: payload[k] for k in allowed if k in payload}
    return ProjectFinanceInputs(**values)

class CoreV3Handler(BaseHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/v3/status":
            return self.send_json({
                "ok": True, "core_v3_version": CORE_V3_VERSION,
                "policy_registry_version": REGISTRY.registry_version,
                "modules": ["policy", "evidence", "tariffs", "net_metering", "interval_load", "hourly_pv", "project_finance"],
            })
        if parsed.path == "/api/v3/policy/snapshot":
            ids = parse_qs(parsed.query).get("id") or POLICY_SNAPSHOT_IDS
            try: return self.send_json(REGISTRY.snapshot(ids))
            except Exception as exc: return self.send_json({"error": str(exc)}, 400)
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if not path.startswith("/api/v3/"):
            return super().do_POST()
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 12_000_000:
                return self.send_json({"error": "Core v3 request exceeds 12 MB"}, 413)
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            if not isinstance(payload, dict):
                raise ValueError("JSON body must be an object")

            if path == "/api/v3/tariff/calculate":
                tariff = str(payload.get("tariff", "residential"))
                result = TARIFFS.bill(tariff, float(payload.get("consumption_kwh", 0)), payload.get("subscribed_kva"))
                return self.send_json(_json_safe(result))

            if path == "/api/v3/net-metering/settle":
                imports = [float(x) for x in payload.get("imports_kwh", [])]
                exports = [float(x) for x in payload.get("exports_kwh", [])]
                if len(imports) != len(exports): raise ValueError("imports_kwh and exports_kwh must have equal length")
                ledger = NetMeteringLedger(TARIFFS, str(payload.get("tariff", "residential")), subscribed_kva=payload.get("subscribed_kva"), rollover_months=int(payload.get("rollover_months", 12)))
                rows = [ledger.settle(i, e) for i, e in zip(imports, exports)]
                return self.send_json({"settlement": _json_safe(rows), "closing_credit_kwh": ledger.credit_balance_kwh, "cash_payout_bnd": 0.0, "policy_rule": "NM_CREDIT_SETTLEMENT"})

            if path == "/api/v3/interval/parse":
                report = parse_load_csv(str(payload.get("csv", "")), timestamp_column=payload.get("timestamp_column"), value_column=payload.get("value_column"), value_type=payload.get("value_type"))
                return self.send_json({"inferred_interval_minutes": report.inferred_interval_minutes, "source_value_type": report.source_value_type, "valid_points": len(report.points), "duplicate_rows": report.duplicate_rows, "skipped_rows": report.skipped_rows, "missing_intervals_estimate": report.missing_intervals_estimate, "completeness_pct": report.completeness_pct, "annual_kwh_in_file": sum(x.kwh for x in report.points)})

            if path == "/api/v3/building/hourly":
                report = parse_load_csv(str(payload.get("csv", "")), timestamp_column=payload.get("timestamp_column"), value_column=payload.get("value_column"), value_type=payload.get("value_type"))
                capacity = float(payload["capacity_kwp"])
                category = str(payload.get("customer_category", payload.get("tariff", "residential"))).lower()
                eligibility = validate_net_metering_eligibility(REGISTRY, capacity_kw=capacity, is_existing_des_customer=bool(payload.get("is_existing_des_customer", True)), has_outstanding_arrears=bool(payload.get("has_outstanding_arrears", False)), technology="Solar PV", customer_category=category, electricity_act_offence=bool(payload.get("electricity_act_offence", False)))
                nm_requested = bool(payload.get("net_metering", True))
                nm_applied = nm_requested and eligibility["eligible"]
                profile = PVWATTS.profile(lat=float(payload.get("lat", 4.9031)), lon=float(payload.get("lon", 114.9398)), tilt=float(payload.get("tilt", 10)), azimuth=float(payload.get("azimuth", 180)), losses_pct=float(payload.get("losses_pct", 14)), hourly=True)
                result = analyze_hourly_building(load_points=report.points, pv_profile=profile, capacity_kwp=capacity, tariff_engine=TARIFFS, tariff=str(payload.get("tariff", "residential")), subscribed_kva=payload.get("subscribed_kva"), net_metering=nm_applied)
                warnings = []
                if report.completeness_pct < 95: warnings.append("Interval dataset completeness is below 95%; results should be treated as provisional.")
                if nm_requested and not nm_applied: warnings.append("Net-metering was requested but not applied because current eligibility checks did not pass.")
                return self.send_json({"interval_report": {"interval_minutes": report.inferred_interval_minutes, "valid_points": len(report.points), "completeness_pct": report.completeness_pct, "missing_intervals_estimate": report.missing_intervals_estimate}, "pv_source": _json_safe(profile), "net_metering_requested": nm_requested, "net_metering_applied": nm_applied, "net_metering_eligibility": eligibility, "result": _json_safe(result), "warnings": warnings})

            if path == "/api/v3/finance/project":
                inputs = _finance_inputs(payload)
                result = model_project_finance(inputs)
                floors = {"equity_irr": solve_tariff(inputs, "equity_irr"), "p90_dscr": solve_tariff(inputs, "p90_dscr"), "project_npv": solve_tariff(inputs, "npv")}
                finite = [x for x in floors.values() if x is not None]
                return self.send_json({"result": _json_safe(result), "tariff_floors_bnd_per_kwh": floors, "developer_floor_bnd_per_kwh": max(finite) if finite else None, "dscr_debt_capacity_bnd": debt_capacity_for_dscr(inputs), "model_boundary": "Annual cash-flow model with level debt service; DSRA and LLCR included. Construction drawdown, IDC, depreciation and sculpted debt are not yet modeled."})

            return self.send_json({"error": "Unknown Core v3 endpoint"}, 404)
        except KeyError as exc:
            return self.send_json({"error": f"Missing required field: {exc.args[0]}"}, 400)
        except ValueError as exc:
            return self.send_json({"error": str(exc)}, 400)
        except Exception as exc:
            print(f"[CORE V3] {type(exc).__name__}: {exc}")
            return self.send_json({"error": f"Core v3 calculation failed: {exc}"}, 500)

app.SolarPassportHandler = CoreV3Handler

if __name__ == "__main__":
    print(f"Solar Passport Core v3 {CORE_V3_VERSION}")
    print(f"Policy registry: {REGISTRY.registry_version}")
    print("Core v3 API available under /api/v3/*")
    app.run()
