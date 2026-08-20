from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from core_v3 import ProjectFinanceInputs, model_project_finance, solve_tariff, debt_capacity_for_dscr

ROOT = Path(__file__).resolve().parents[1]
CASE_FILE = ROOT / "validation" / "finance_reconciliation_case.json"


def load_case(path: Path = CASE_FILE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def annual_schedule(inputs: ProjectFinanceInputs, result) -> list[dict]:
    rows = []
    annual_ds = result.annual_debt_service_bnd
    for year in range(1, inputs.ppa_years + 1):
        p50_cfads = result.p50_cfads[year - 1]
        p90_cfads = result.p90_cfads[year - 1]
        debt_service = annual_ds if year <= inputs.debt_tenor_years else 0.0
        gross_p50_mwh = inputs.year1_p50_mwh * ((1 - inputs.degradation) ** (year - 1))
        sold_p50_mwh = gross_p50_mwh * (1 - inputs.curtailment) * (1 - inputs.other_losses)
        gross_p90_mwh = gross_p50_mwh * inputs.p90_factor
        sold_p90_mwh = gross_p90_mwh * (1 - inputs.curtailment) * (1 - inputs.other_losses)
        tariff = inputs.ppa_bnd_per_kwh * ((1 + inputs.tariff_escalation) ** (year - 1))
        p50_revenue = sold_p50_mwh * 1000 * tariff
        p90_revenue = sold_p90_mwh * 1000 * tariff
        opex = inputs.opex_year1_bnd * ((1 + inputs.opex_escalation) ** (year - 1))
        rows.append({
            "year": year,
            "gross_p50_mwh": gross_p50_mwh,
            "sold_p50_mwh": sold_p50_mwh,
            "gross_p90_mwh": gross_p90_mwh,
            "sold_p90_mwh": sold_p90_mwh,
            "tariff_bnd_per_kwh": tariff,
            "p50_revenue_bnd": p50_revenue,
            "p90_revenue_bnd": p90_revenue,
            "opex_bnd": opex,
            "p50_cfads_bnd": p50_cfads,
            "p90_cfads_bnd": p90_cfads,
            "debt_service_bnd": debt_service,
            "p50_dscr": result.p50_dscr[year - 1],
            "p90_dscr": result.p90_dscr[year - 1],
        })
    return rows


def build_report(case: dict) -> dict:
    inputs = ProjectFinanceInputs(**case["core_v3_inputs"])
    result = model_project_finance(inputs)
    floors = {
        "equity_irr": solve_tariff(inputs, "equity_irr"),
        "p90_dscr": solve_tariff(inputs, "p90_dscr"),
        "project_npv": solve_tariff(inputs, "npv"),
    }
    finite = [x for x in floors.values() if x is not None]
    return {
        "case_id": case["case_id"],
        "inputs": asdict(inputs),
        "summary": {
            "project_irr_pct": None if result.project_irr is None else result.project_irr * 100,
            "equity_irr_pct": None if result.equity_irr is None else result.equity_irr * 100,
            "project_npv_bnd": result.project_npv_bnd,
            "lcoe_bnd_per_kwh": result.lcoe_bnd_per_kwh,
            "debt_bnd": result.debt_bnd,
            "equity_bnd": result.equity_bnd,
            "annual_debt_service_bnd": result.annual_debt_service_bnd,
            "dsra_requirement_bnd": result.dsra_requirement_bnd,
            "minimum_p90_dscr": result.minimum_p90_dscr,
            "llcr_p50": result.llcr_p50,
            "llcr_p90": result.llcr_p90,
            "dscr_debt_capacity_bnd": debt_capacity_for_dscr(inputs),
            "tariff_floor_equity_irr_bnd_per_kwh": floors["equity_irr"],
            "tariff_floor_p90_dscr_bnd_per_kwh": floors["p90_dscr"],
            "tariff_floor_zero_npv_bnd_per_kwh": floors["project_npv"],
            "developer_floor_bnd_per_kwh": max(finite) if finite else None,
        },
        "annual_schedule": annual_schedule(inputs, result),
        "reconciliation_status": "UNVALIDATED_AGAINST_EXTERNAL_BANK_MODEL",
    }


def write_report(output_dir: str | Path = "validation/generated/finance") -> tuple[Path, Path]:
    case = load_case()
    report = build_report(case)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    json_path = output / f"{case['case_id']}_core_v3.json"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    csv_path = output / f"{case['case_id']}_annual_schedule.csv"
    rows = report["annual_schedule"]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    return json_path, csv_path


if __name__ == "__main__":
    for path in write_report():
        print(path)
