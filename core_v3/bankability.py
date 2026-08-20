from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .finance import ProjectFinanceInputs, model_project_finance, solve_tariff

@dataclass(frozen=True)
class BankabilityAssessment:
    financial_status: str
    readiness_status: str
    combined_status: str
    readiness_score: float
    constraints: dict
    tariff_floors_bnd_per_kwh: dict
    developer_floor_bnd_per_kwh: Optional[float]
    offtaker_ceiling_bnd_per_kwh: Optional[float]
    corridor_exists: Optional[bool]

def assess_bankability(i: ProjectFinanceInputs, *, readiness_scores: Optional[dict[str, float]] = None, offtaker_ceiling_bnd_per_kwh: Optional[float] = None) -> BankabilityAssessment:
    result = model_project_finance(i)
    floors = {
        "equity_irr": solve_tariff(i, "equity_irr"),
        "p90_dscr": solve_tariff(i, "p90_dscr"),
        "project_npv": solve_tariff(i, "npv"),
    }
    active_floors = [x for x in floors.values() if x is not None]
    developer_floor = max(active_floors) if active_floors else None
    constraints = {
        "equity_irr": {"applicable": True, "value": result.equity_irr, "target": i.target_equity_irr, "pass": result.equity_irr is not None and result.equity_irr >= i.target_equity_irr},
        "p90_dscr": {"applicable": result.debt_bnd > 0, "value": result.minimum_p90_dscr, "target": i.minimum_p90_dscr, "pass": True if result.debt_bnd <= 0 else (result.minimum_p90_dscr is not None and result.minimum_p90_dscr >= i.minimum_p90_dscr)},
        "project_npv": {"applicable": True, "value": result.project_npv_bnd, "target": 0.0, "pass": result.project_npv_bnd >= 0},
    }
    financial_pass = all(x["pass"] for x in constraints.values())
    corridor = None
    if offtaker_ceiling_bnd_per_kwh is not None and developer_floor is not None:
        corridor = developer_floor <= float(offtaker_ceiling_bnd_per_kwh)
    financial_status = "PASS" if financial_pass else "FAIL"
    if financial_pass and corridor is False:
        financial_status = "OFFTAKER_GAP"

    scores = readiness_scores or {}
    weights = {"sponsor": 10, "financing": 15, "site_land": 10, "solar_resource": 5, "grid": 15, "ppa_offtake": 15, "approvals_environmental": 5, "execution": 10, "risk_allocation": 15}
    if scores:
        bounded = {k: max(0.0, min(100.0, float(scores.get(k, 0.0)))) for k in weights}
        readiness_score = sum(bounded[k] * weights[k] / 100 for k in weights)
        readiness_status = "GREEN" if readiness_score >= 80 else "AMBER" if readiness_score >= 55 else "RED"
    else:
        readiness_score = 0.0
        readiness_status = "NOT_ASSESSED"

    if not financial_pass:
        combined = "RED — ECONOMICS FAIL"
    elif corridor is False:
        combined = "AMBER — OFFTAKER / TARIFF GAP"
    elif readiness_status == "GREEN":
        combined = "GREEN — ECONOMICS PASS & READY"
    elif readiness_status == "NOT_ASSESSED":
        combined = "ECONOMICS PASS — READINESS NOT ASSESSED"
    else:
        combined = "AMBER — ECONOMICS PASS, READINESS GAPS"
    return BankabilityAssessment(financial_status, readiness_status, combined, readiness_score, constraints, floors, developer_floor, offtaker_ceiling_bnd_per_kwh, corridor)
