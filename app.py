from __future__ import annotations

import json
import math
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterable, List, Dict, Any, Optional
from urllib.parse import urlencode, urlparse
from urllib.request import urlopen

BASE_DIR = Path(__file__).resolve().parent
PVWATTS_URL = "https://developer.nrel.gov/api/pvwatts/v8.json"
NREL_API_KEY = os.getenv("NREL_API_KEY", "").strip()

# Brunei-facing MVP defaults. These are visible assumptions, not hidden facts.
DEFAULT_MONTHLY_SOLAR_SHAPE = [
    0.081, 0.076, 0.083, 0.083, 0.084, 0.082,
    0.083, 0.084, 0.086, 0.088, 0.084, 0.086,
]

def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def f(value: Any, default: float = 0.0) -> float:
    try:
        x = float(value)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def pct(value: Any, default: float = 0.0) -> float:
    return clamp(f(value, default), 0.0, 100.0) / 100.0


def annuity_payment(principal: float, annual_rate: float, years: int, periods_per_year: int = 12) -> float:
    if principal <= 0 or years <= 0:
        return 0.0
    n = years * periods_per_year
    r = annual_rate / periods_per_year
    if abs(r) < 1e-12:
        return principal / n
    return principal * r / (1 - (1 + r) ** (-n))


def npv(rate: float, cashflows: Iterable[float]) -> float:
    return sum(cf / ((1 + rate) ** i) for i, cf in enumerate(cashflows))


def irr(cashflows: List[float]) -> Optional[float]:
    """Dependency-free IRR. Returns decimal rate, or None if no sign change / no root."""
    if not cashflows or not any(x < 0 for x in cashflows) or not any(x > 0 for x in cashflows):
        return None

    def value(rate: float) -> float:
        if rate <= -0.999999:
            rate = -0.999999
        return npv(rate, cashflows)

    lo, hi = -0.95, 10.0
    vlo, vhi = value(lo), value(hi)
    # Expand high bound if necessary.
    for _ in range(8):
        if vlo == 0:
            return lo
        if vhi == 0:
            return hi
        if vlo * vhi < 0:
            break
        hi *= 2
        vhi = value(hi)
    else:
        return None

    for _ in range(120):
        mid = (lo + hi) / 2
        vm = value(mid)
        if abs(vm) < 1e-8:
            return mid
        if vlo * vm <= 0:
            hi, vhi = mid, vm
        else:
            lo, vlo = mid, vm
    return (lo + hi) / 2


def tariff_a_cost(kwh: float) -> float:
    kwh = max(0.0, kwh)
    tiers = [(600.0, 0.01), (1400.0, 0.08), (2000.0, 0.10)]
    remaining = kwh
    total = 0.0
    for qty, rate in tiers:
        used = min(remaining, qty)
        total += used * rate
        remaining -= used
        if remaining <= 0:
            return total
    return total + remaining * 0.12


def usage_from_tariff_a_bill(bill: float) -> float:
    bill = max(0.0, bill)
    boundaries = [(600.0, 0.01), (1400.0, 0.08), (2000.0, 0.10)]
    remaining = bill
    usage = 0.0
    for qty, rate in boundaries:
        tier_cost = qty * rate
        if remaining <= tier_cost:
            return usage + remaining / rate
        usage += qty
        remaining -= tier_cost
    return usage + remaining / 0.12


def flat_bill(kwh: float, rate: float, fixed_charge: float = 0.0) -> float:
    return max(0.0, kwh) * max(0.0, rate) + max(0.0, fixed_charge)


def calculate_bill(kwh: float, tariff_type: str, flat_rate: float, fixed_charge: float = 0.0) -> float:
    if tariff_type == "tariff_a":
        return tariff_a_cost(kwh) + max(0.0, fixed_charge)
    return flat_bill(kwh, flat_rate, fixed_charge)


def monthly_generation_fallback(capacity_kwp: float, specific_yield: float) -> List[float]:
    annual = max(0.0, capacity_kwp) * max(0.0, specific_yield)
    total_shape = sum(DEFAULT_MONTHLY_SOLAR_SHAPE)
    return [annual * x / total_shape for x in DEFAULT_MONTHLY_SOLAR_SHAPE]


def pvwatts_generation(lat: float, lon: float, capacity_kwp: float, tilt: float, azimuth: float, losses: float, specific_yield: float) -> Dict[str, Any]:
    """Use PVWatts when configured; otherwise use a visible fallback assumption."""
    if NREL_API_KEY and capacity_kwp > 0:
        try:
            params = {
                "api_key": NREL_API_KEY,
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
            }
            query = urlencode(params)
            with urlopen(f"{PVWATTS_URL}?{query}", timeout=12) as res:
                body = json.loads(res.read().decode("utf-8"))
            outputs = body.get("outputs") or {}
            monthly = outputs.get("ac_monthly")
            if monthly and len(monthly) == 12:
                return {
                    "monthly_kwh": [float(x) for x in monthly],
                    "annual_kwh": float(outputs.get("ac_annual", sum(monthly))),
                    "capacity_factor": float(outputs.get("capacity_factor", 0.0)),
                    "source": "NREL PVWatts v8",
                    "source_confidence": "Medium-High",
                }
        except Exception:
            pass

    monthly = monthly_generation_fallback(capacity_kwp, specific_yield)
    annual = sum(monthly)
    cf = annual / (capacity_kwp * 8760) * 100 if capacity_kwp > 0 else 0.0
    return {
        "monthly_kwh": monthly,
        "annual_kwh": annual,
        "capacity_factor": cf,
        "source": "MVP specific-yield fallback",
        "source_confidence": "Low-Medium",
    }


def building_cashflows(
    capex: float,
    year1_savings: float,
    o_and_m_pct: float,
    degradation: float,
    opex_escalation: float,
    inverter_year: int,
    inverter_pct: float,
    years: int = 25,
) -> List[float]:
    flows = [-capex]
    for year in range(1, years + 1):
        saving = year1_savings * ((1 - degradation) ** (year - 1))
        om = capex * o_and_m_pct * ((1 + opex_escalation) ** (year - 1))
        replacement = capex * inverter_pct if year == inverter_year else 0.0
        flows.append(saving - om - replacement)
    return flows


def simple_payback(flows: List[float]) -> Optional[float]:
    if not flows or flows[0] >= 0:
        return 0.0
    cumulative = flows[0]
    for year in range(1, len(flows)):
        prev = cumulative
        cumulative += flows[year]
        if cumulative >= 0 and flows[year] > 0:
            fraction = (-prev) / flows[year]
            return (year - 1) + fraction
    return None


def evaluate_building_capacity(payload: Dict[str, Any], capacity_kwp: float) -> Dict[str, Any]:
    tariff_type = payload.get("tariff_type", "tariff_a")
    flat_rate = f(payload.get("flat_rate"), 0.08)
    fixed_charge = f(payload.get("fixed_charge"), 0.0)
    monthly_bill_input = f(payload.get("monthly_bill"), 50.0)
    annual_kwh_input = f(payload.get("annual_kwh"), 0.0)
    daytime_share = pct(payload.get("daytime_share_pct"), 65.0)
    export_credit = f(payload.get("export_credit"), 0.0)
    specific_yield = f(payload.get("specific_yield"), 1420.0)

    if annual_kwh_input > 0:
        annual_load = annual_kwh_input
        monthly_load = [annual_load / 12] * 12
    elif tariff_type == "tariff_a":
        estimated_monthly = usage_from_tariff_a_bill(monthly_bill_input)
        monthly_load = [estimated_monthly] * 12
        annual_load = estimated_monthly * 12
    else:
        rate = max(flat_rate, 1e-9)
        estimated_monthly = max(0.0, monthly_bill_input - fixed_charge) / rate
        monthly_load = [estimated_monthly] * 12
        annual_load = estimated_monthly * 12

    lat = f(payload.get("lat"), 4.9031)
    lon = f(payload.get("lon"), 114.9398)
    tilt = f(payload.get("tilt"), 10.0)
    azimuth = f(payload.get("azimuth"), 180.0)
    losses = f(payload.get("losses"), 14.0)
    generation = pvwatts_generation(lat, lon, capacity_kwp, tilt, azimuth, losses, specific_yield)
    monthly_pv = generation["monthly_kwh"]

    rows = []
    bill_before_total = 0.0
    bill_after_total = 0.0
    self_consumed_total = 0.0
    export_total = 0.0
    credit_total = 0.0
    for i, (load, solar) in enumerate(zip(monthly_load, monthly_pv)):
        daytime_load = load * daytime_share
        self_consumed = min(solar, daytime_load)
        export = max(0.0, solar - self_consumed)
        import_kwh = max(0.0, load - self_consumed)
        bill_before = calculate_bill(load, tariff_type, flat_rate, fixed_charge)
        gross_after = calculate_bill(import_kwh, tariff_type, flat_rate, fixed_charge)
        export_value = export * export_credit
        bill_after = max(0.0, gross_after - export_value)
        bill_before_total += bill_before
        bill_after_total += bill_after
        self_consumed_total += self_consumed
        export_total += export
        credit_total += min(gross_after, export_value)
        rows.append({
            "month": i + 1,
            "load_kwh": round(load, 1),
            "solar_kwh": round(solar, 1),
            "self_consumed_kwh": round(self_consumed, 1),
            "export_kwh": round(export, 1),
            "grid_import_kwh": round(import_kwh, 1),
            "bill_before": round(bill_before, 2),
            "bill_after": round(bill_after, 2),
        })

    annual_saving = bill_before_total - bill_after_total
    self_consumption_pct = (self_consumed_total / generation["annual_kwh"] * 100) if generation["annual_kwh"] else 0.0
    load_coverage_pct = (self_consumed_total / annual_load * 100) if annual_load else 0.0

    capex_per_kwp = f(payload.get("capex_per_kwp"), 1500.0)
    capex = capacity_kwp * capex_per_kwp + f(payload.get("development_cost"), 0.0)
    o_and_m_pct = pct(payload.get("om_pct"), 1.0)
    degradation = pct(payload.get("degradation_pct"), 0.5)
    escalation = pct(payload.get("opex_escalation_pct"), 2.0)
    inverter_year = int(clamp(f(payload.get("inverter_year"), 12), 1, 25))
    inverter_pct = pct(payload.get("inverter_replacement_pct"), 8.0)
    discount_rate = pct(payload.get("discount_rate_pct"), 8.0)

    flows = building_cashflows(capex, annual_saving, o_and_m_pct, degradation, escalation, inverter_year, inverter_pct)
    project_irr = irr(flows)
    project_npv = npv(discount_rate, flows)
    payback = simple_payback(flows)

    down_payment = pct(payload.get("down_payment_pct"), 20.0)
    loan_rate = pct(payload.get("loan_rate_pct"), 5.5)
    loan_years = int(clamp(f(payload.get("loan_years"), 10), 1, 25))
    financed = max(0.0, capex * (1 - down_payment))
    monthly_debt = annuity_payment(financed, loan_rate, loan_years, 12)
    first_year_om = capex * o_and_m_pct
    monthly_net_cash = annual_saving / 12 - first_year_om / 12 - monthly_debt

    return {
        "capacity_kwp": round(capacity_kwp, 2),
        "annual_load_kwh": round(annual_load, 1),
        "annual_generation_kwh": round(generation["annual_kwh"], 1),
        "capacity_factor_pct": round(generation["capacity_factor"], 2),
        "generation_source": generation["source"],
        "generation_confidence": generation["source_confidence"],
        "self_consumption_pct": round(self_consumption_pct, 1),
        "load_coverage_pct": round(load_coverage_pct, 1),
        "export_kwh": round(export_total, 1),
        "bill_before": round(bill_before_total, 2),
        "bill_after": round(bill_after_total, 2),
        "year1_saving": round(annual_saving, 2),
        "export_credit_realised": round(credit_total, 2),
        "capex": round(capex, 2),
        "simple_payback_years": round(payback, 2) if payback is not None else None,
        "project_irr_pct": round(project_irr * 100, 2) if project_irr is not None else None,
        "npv": round(project_npv, 2),
        "monthly_debt_payment": round(monthly_debt, 2),
        "first_year_net_monthly_cash": round(monthly_net_cash, 2),
        "monthly": rows,
    }


def building_readiness(payload: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    documentation = pct(payload.get("documentation_pct"), 70.0) * 100
    electrical = pct(payload.get("electrical_readiness_pct"), 70.0) * 100
    roof = pct(payload.get("roof_readiness_pct"), 65.0) * 100
    finance = 100.0 if result["project_irr_pct"] is not None and result["project_irr_pct"] >= 8 else max(20.0, 60 + (result["project_irr_pct"] or -10) * 2)
    self_use = min(100.0, result["self_consumption_pct"])
    energy_profile = 90.0 if f(payload.get("annual_kwh"), 0) > 0 else 55.0
    resource = 80.0 if result["generation_source"] == "NREL PVWatts v8" else 55.0
    implementation = pct(payload.get("implementation_readiness_pct"), 60.0) * 100
    net_meter = pct(payload.get("net_metering_readiness_pct"), 50.0) * 100

    blocks = [
        ("Energy profile", 15, energy_profile),
        ("Solar resource", 10, resource),
        ("Roof / site", 15, roof),
        ("Self-consumption", 10, self_use),
        ("Financial attractiveness", 20, finance),
        ("Financing", 10, 80.0 if result["monthly_debt_payment"] > 0 else 60.0),
        ("Net-metering readiness", 5, net_meter),
        ("Electrical readiness", 5, electrical),
        ("Documentation", 5, documentation),
        ("Implementation risk", 5, implementation),
    ]
    score = sum(weight * val / 100 for _, weight, val in blocks)
    model_irr = result["project_irr_pct"]
    model_npv = result["npv"]
    if model_irr is None or model_npv < 0 or model_irr < 3:
        status = "HOLD"
    elif model_irr < 8:
        status = "OPTIMISE FIRST"
    elif score >= 80:
        status = "PROCEED"
    elif score >= 60:
        status = "PROCEED WITH CONDITIONS"
    elif score >= 45:
        status = "OPTIMISE FIRST"
    else:
        status = "HOLD"
    return {
        "score": round(score, 0),
        "status": status,
        "blocks": [{"name": n, "weight": w, "score": round(v, 0)} for n, w, v in blocks],
    }


def recommend_building(payload: Dict[str, Any]) -> Dict[str, Any]:
    roof_area = max(0.0, f(payload.get("roof_area_m2"), 250.0))
    usable_factor = pct(payload.get("usable_roof_pct"), 75.0)
    area_per_kwp = max(3.0, f(payload.get("area_per_kwp"), 6.5))
    max_roof = roof_area * usable_factor / area_per_kwp

    base = evaluate_building_capacity(payload, max(0.1, min(max_roof, f(payload.get("capacity_kwp"), max_roof or 1))))
    annual_load = base["annual_load_kwh"]
    specific_yield = max(1.0, f(payload.get("specific_yield"), 1420.0))
    max_bill_offset = annual_load / specific_yield
    daytime_share = pct(payload.get("daytime_share_pct"), 65.0)
    self_consumption_size = annual_load * daytime_share / specific_yield

    upper = max(1.0, max_roof)
    candidates = []
    steps = 32
    for i in range(1, steps + 1):
        cap = upper * i / steps
        r = evaluate_building_capacity(payload, cap)
        candidates.append(r)

    def irr_key(r: Dict[str, Any]) -> float:
        return r["project_irr_pct"] if r["project_irr_pct"] is not None else -999.0

    best_irr_raw = max(candidates, key=irr_key)
    # When several self-consumed sizes have effectively the same IRR, prefer the
    # largest one rather than an arbitrary tiny first grid point.
    best_irr_value = irr_key(best_irr_raw)
    near_best = [r for r in candidates if irr_key(r) >= best_irr_value - 0.05]
    best_irr = max(near_best, key=lambda r: r["capacity_kwp"]) if near_best else best_irr_raw
    best_npv = max(candidates, key=lambda r: r["npv"])
    best_cash = max(candidates, key=lambda r: r["first_year_net_monthly_cash"])

    selected_mode = payload.get("sizing_mode", "financial_return")
    selected = {
        "maximum_roof": evaluate_building_capacity(payload, max(0.1, max_roof)),
        "bill_offset": evaluate_building_capacity(payload, max(0.1, min(max_roof, max_bill_offset))),
        "self_consumption": evaluate_building_capacity(payload, max(0.1, min(max_roof, self_consumption_size))),
        "financial_return": best_irr,
        "maximum_npv": best_npv,
        "cash_flow": best_cash,
        "custom": evaluate_building_capacity(payload, max(0.1, min(max_roof if max_roof else 1e9, f(payload.get("capacity_kwp"), 5.0)))),
    }.get(selected_mode, best_irr)

    return {
        "max_roof_kwp": round(max_roof, 1),
        "max_bill_offset_kwp": round(min(max_roof, max_bill_offset), 1),
        "self_consumption_kwp": round(min(max_roof, self_consumption_size), 1),
        "financial_return_kwp": best_irr["capacity_kwp"],
        "maximum_npv_kwp": best_npv["capacity_kwp"],
        "cash_flow_kwp": best_cash["capacity_kwp"],
        "selected": selected,
    }


def project_model(payload: Dict[str, Any], tariff: float, use_p90: bool = False, capex_per_mw_override: Optional[float] = None) -> Dict[str, Any]:
    mwp = max(0.001, f(payload.get("mwp"), 120.0))
    mwac = max(0.001, f(payload.get("mwac"), 100.0))
    p50_specific = max(1.0, f(payload.get("p50_specific_yield"), 1500.0))
    p90_factor = clamp(f(payload.get("p90_factor_pct"), 95.0), 50, 100) / 100
    degradation = pct(payload.get("degradation_pct"), 0.45)
    curtailment = pct(payload.get("curtailment_pct"), 2.0)
    other_losses = pct(payload.get("other_losses_pct"), 1.0)
    ppa_years = int(clamp(f(payload.get("ppa_years"), 25), 5, 40))

    capex_per_mw = capex_per_mw_override if capex_per_mw_override is not None else f(payload.get("capex_per_mw"), 1_500_000.0)
    total_capex = mwac * capex_per_mw
    opex_per_mw = f(payload.get("opex_per_mw_year"), 24_000.0)
    opex_escalation = pct(payload.get("opex_escalation_pct"), 2.0)

    debt_pct = pct(payload.get("debt_pct"), 65.0)
    debt_rate = pct(payload.get("debt_rate_pct"), 5.5)
    debt_tenor = int(clamp(f(payload.get("debt_tenor_years"), 15), 1, ppa_years))
    debt = total_capex * debt_pct
    equity = total_capex - debt
    annual_debt_service = annuity_payment(debt, debt_rate, debt_tenor, 1)

    discount_rate = pct(payload.get("discount_rate_pct"), 8.0)
    tariff_escalation = pct(payload.get("tariff_escalation_pct"), 0.0)
    tax_rate = pct(payload.get("tax_rate_pct"), 0.0)

    base_generation_mwh = mwp * p50_specific
    if use_p90:
        base_generation_mwh *= p90_factor

    project_flows = [-total_capex]
    equity_flows = [-equity]
    p90_dscrs = []
    dscrs = []
    energy_series = []
    revenue_series = []
    cfads_series = []

    for year in range(1, ppa_years + 1):
        gross = base_generation_mwh * ((1 - degradation) ** (year - 1))
        sold_mwh = gross * (1 - curtailment) * (1 - other_losses)
        year_tariff = tariff * ((1 + tariff_escalation) ** (year - 1))
        revenue = sold_mwh * 1000 * year_tariff
        opex = mwac * opex_per_mw * ((1 + opex_escalation) ** (year - 1))
        ebitda = revenue - opex
        taxable = max(0.0, ebitda)
        tax = taxable * tax_rate
        cfads = ebitda - tax
        debt_service = annual_debt_service if year <= debt_tenor else 0.0
        dscr = cfads / debt_service if debt_service > 0 else None

        project_flows.append(cfads)
        equity_flows.append(cfads - debt_service)
        energy_series.append(sold_mwh)
        revenue_series.append(revenue)
        cfads_series.append(cfads)
        if dscr is not None:
            dscrs.append(dscr)

    # Always calculate DSCR under P90 cashflow using same tariff.
    if not use_p90:
        p90_payload = dict(payload)
        p90 = project_model(p90_payload, tariff, use_p90=True, capex_per_mw_override=capex_per_mw)
        min_p90_dscr = p90["min_dscr"]
    else:
        min_p90_dscr = min(dscrs) if dscrs else None

    project_irr = irr(project_flows)
    equity_irr = irr(equity_flows)
    project_npv = npv(discount_rate, project_flows)

    discounted_cost = total_capex
    discounted_energy = 0.0
    for year in range(1, ppa_years + 1):
        opex = mwac * opex_per_mw * ((1 + opex_escalation) ** (year - 1))
        discounted_cost += opex / ((1 + discount_rate) ** year)
        discounted_energy += energy_series[year - 1] * 1000 / ((1 + discount_rate) ** year)
    lcoe = discounted_cost / discounted_energy if discounted_energy > 0 else None

    return {
        "tariff": tariff,
        "total_capex": total_capex,
        "debt": debt,
        "equity": equity,
        "year1_energy_mwh": energy_series[0] if energy_series else 0.0,
        "year1_revenue": revenue_series[0] if revenue_series else 0.0,
        "year1_cfads": cfads_series[0] if cfads_series else 0.0,
        "annual_debt_service": annual_debt_service,
        "min_dscr": min(dscrs) if dscrs else None,
        "min_p90_dscr": min_p90_dscr,
        "project_irr_pct": project_irr * 100 if project_irr is not None else None,
        "equity_irr_pct": equity_irr * 100 if equity_irr is not None else None,
        "npv": project_npv,
        "lcoe": lcoe,
    }


def solve_tariff(payload: Dict[str, Any], objective: str) -> Optional[float]:
    target_equity_irr = f(payload.get("target_equity_irr_pct"), 12.0)
    min_dscr = f(payload.get("min_dscr"), 1.25)

    def passes(t: float) -> bool:
        r = project_model(payload, t)
        if objective == "irr":
            return r["equity_irr_pct"] is not None and r["equity_irr_pct"] >= target_equity_irr
        if objective == "dscr":
            return r["min_p90_dscr"] is not None and r["min_p90_dscr"] >= min_dscr
        if objective == "npv":
            return r["npv"] >= 0
        return False

    lo, hi = 0.0, 0.50
    if not passes(hi):
        for _ in range(5):
            hi *= 2
            if passes(hi):
                break
        else:
            return None

    for _ in range(70):
        mid = (lo + hi) / 2
        if passes(mid):
            hi = mid
        else:
            lo = mid
    return hi


def project_readiness(payload: Dict[str, Any], result: Dict[str, Any], bankable_tariff: Optional[float]) -> Dict[str, Any]:
    scores = {
        "Sponsor capability": pct(payload.get("sponsor_score"), 70.0) * 100,
        "Financing": pct(payload.get("financing_score"), 65.0) * 100,
        "Site / land": pct(payload.get("site_score"), 70.0) * 100,
        "Solar resource": pct(payload.get("resource_score"), 70.0) * 100,
        "Grid": pct(payload.get("grid_score"), 55.0) * 100,
        "PPA / offtake": pct(payload.get("ppa_score"), 55.0) * 100,
        "Project economics": 85.0 if bankable_tariff is not None and result["tariff"] >= bankable_tariff else 45.0,
        "Approvals / environmental": pct(payload.get("approvals_score"), 60.0) * 100,
        "Execution": pct(payload.get("execution_score"), 70.0) * 100,
        "Risk allocation": pct(payload.get("risk_score"), 55.0) * 100,
    }
    weights = {
        "Sponsor capability": 10,
        "Financing": 15,
        "Site / land": 10,
        "Solar resource": 5,
        "Grid": 15,
        "PPA / offtake": 15,
        "Project economics": 15,
        "Approvals / environmental": 5,
        "Execution": 5,
        "Risk allocation": 5,
    }
    total = sum(scores[k] * weights[k] / 100 for k in scores)
    status = "GREEN — INVESTMENT-READY" if total >= 80 else "AMBER — GAPS REMAIN" if total >= 55 else "RED — NOT BANKABLE / NOT READY"
    return {
        "score": round(total, 0),
        "status": status,
        "blocks": [{"name": k, "weight": weights[k], "score": round(scores[k], 0)} for k in scores],
    }




def api_building(payload: Dict[str, Any]) -> Dict[str, Any]:
    recommendation = recommend_building(payload)
    selected = recommendation["selected"]
    readiness = building_readiness(payload, selected)

    reasons = []
    if selected["self_consumption_pct"] < 65:
        reasons.append("Export is relatively high; a smaller system or higher daytime load may improve value.")
    if selected["project_irr_pct"] is not None and selected["project_irr_pct"] < 8:
        reasons.append("Financial return is below the MVP 8% screening reference; optimise CAPEX, tariff value or financing.")
    if selected["first_year_net_monthly_cash"] < 0:
        reasons.append("Financing produces negative first-year monthly cash flow under the current assumptions.")
    if selected["generation_source"] != "NREL PVWatts v8":
        reasons.append("Generation currently uses a visible specific-yield fallback; configure NREL_API_KEY or replace with a validated resource study before investment approval.")
    if not reasons:
        reasons.append("The selected sizing case is financially and operationally coherent under the stated assumptions.")

    return {
        "recommendation": recommendation,
        "readiness": readiness,
        "decision_reasons": reasons[:5],
        "assumptions": [
            {"variable": "Electricity tariff", "value": payload.get("tariff_type", "tariff_a"), "source": "User / tariff selection", "confidence": "Medium", "owner": "Customer"},
            {"variable": "PV specific yield", "value": f(payload.get("specific_yield"), 1420.0), "source": selected["generation_source"], "confidence": selected["generation_confidence"], "owner": "Platform"},
            {"variable": "PV CAPEX", "value": f(payload.get("capex_per_kwp"), 1500.0), "source": "User / market assumption", "confidence": "Medium", "owner": "Customer"},
            {"variable": "Daytime load share", "value": f(payload.get("daytime_share_pct"), 65.0), "source": "User estimate", "confidence": "Low-Medium", "owner": "Customer"},
            {"variable": "Export credit", "value": f(payload.get("export_credit"), 0.0), "source": "User assumption", "confidence": "Low-Medium", "owner": "Customer"},
        ],
    }


def api_project(payload: Dict[str, Any]) -> Dict[str, Any]:
    tariff = f(payload.get("ppa_tariff"), 0.07)
    result = project_model(payload, tariff)
    irr_tariff = solve_tariff(payload, "irr")
    dscr_tariff = solve_tariff(payload, "dscr")
    npv_tariff = solve_tariff(payload, "npv")
    floors = [x for x in [irr_tariff, dscr_tariff, npv_tariff] if x is not None]
    developer_floor = max(floors) if floors else None
    ceiling = f(payload.get("offtaker_ceiling"), 0.0)
    corridor_exists = developer_floor is not None and ceiling > 0 and developer_floor <= ceiling

    capex_cases = payload.get("sensitivity_capex_cases") or [1_100_000, 1_300_000, 1_500_000, 1_800_000, 2_000_000]
    tariff_cases = payload.get("sensitivity_tariff_cases") or [0.06, 0.07, 0.08, 0.09, 0.10, 0.12]
    matrix = []
    for capex in capex_cases:
        row = []
        for t in tariff_cases:
            m = project_model(payload, f(t), capex_per_mw_override=f(capex))
            row.append({
                "tariff": f(t),
                "equity_irr_pct": round(m["equity_irr_pct"], 1) if m["equity_irr_pct"] is not None else None,
                "p90_dscr": round(m["min_p90_dscr"], 2) if m["min_p90_dscr"] is not None else None,
                "npv_m": round(m["npv"] / 1_000_000, 1),
            })
        matrix.append({"capex_per_mw": f(capex), "cells": row})

    readiness = project_readiness(payload, result, developer_floor)
    binding = None
    if developer_floor is not None:
        candidates = {"Equity IRR": irr_tariff, "P90 DSCR": dscr_tariff, "Project NPV": npv_tariff}
        binding = max((k for k in candidates if candidates[k] is not None), key=lambda k: candidates[k])

    interventions = []
    if developer_floor is not None and tariff < developer_floor:
        interventions.append("Reduce all-in CAPEX or grid connection scope before increasing tariff.")
        interventions.append("Re-price debt, extend tenor, or improve payment security to reduce the developer floor.")
    if f(payload.get("curtailment_pct"), 2.0) >= 5:
        interventions.append("Resolve curtailment and dispatch assumptions; they materially affect revenue and DSCR.")
    if f(payload.get("grid_score"), 55.0) < 60:
        interventions.append("Complete the grid study and define the interconnection boundary before procurement.")
    if not interventions:
        interventions.append("Proceed to detailed diligence on land, grid, PPA allocation and verified CAPEX assumptions.")

    return {
        "tested": {
            "ppa_tariff": round(tariff, 4),
            "equity_irr_pct": round(result["equity_irr_pct"], 2) if result["equity_irr_pct"] is not None else None,
            "project_irr_pct": round(result["project_irr_pct"], 2) if result["project_irr_pct"] is not None else None,
            "min_p90_dscr": round(result["min_p90_dscr"], 2) if result["min_p90_dscr"] is not None else None,
            "npv": round(result["npv"], 2),
            "lcoe": round(result["lcoe"], 4) if result["lcoe"] is not None else None,
            "total_capex": round(result["total_capex"], 2),
            "year1_energy_mwh": round(result["year1_energy_mwh"], 1),
            "year1_revenue": round(result["year1_revenue"], 2),
            "annual_debt_service": round(result["annual_debt_service"], 2),
        },
        "tariff_solver": {
            "for_target_equity_irr": round(irr_tariff, 4) if irr_tariff is not None else None,
            "for_min_p90_dscr": round(dscr_tariff, 4) if dscr_tariff is not None else None,
            "for_zero_project_npv": round(npv_tariff, 4) if npv_tariff is not None else None,
            "developer_floor": round(developer_floor, 4) if developer_floor is not None else None,
            "binding_constraint": binding,
            "offtaker_ceiling": round(ceiling, 4) if ceiling > 0 else None,
            "corridor_exists": corridor_exists,
        },
        "readiness": readiness,
        "sensitivity": {"tariffs": tariff_cases, "matrix": matrix},
        "interventions": interventions[:5],
        "assumptions": [
            {"variable": "CAPEX / MWac", "value": f(payload.get("capex_per_mw"), 1_500_000), "source": "User / project assumption", "confidence": "Medium", "owner": "Developer"},
            {"variable": "P50 specific yield", "value": f(payload.get("p50_specific_yield"), 1500), "source": "User / resource assumption", "confidence": "Medium", "owner": "Developer"},
            {"variable": "P90 factor", "value": f(payload.get("p90_factor_pct"), 95), "source": "MVP assumption unless replaced", "confidence": "Low-Medium", "owner": "Platform"},
            {"variable": "Debt rate", "value": f(payload.get("debt_rate_pct"), 5.5), "source": "User / financing assumption", "confidence": "Medium", "owner": "Developer"},
            {"variable": "Target equity IRR", "value": f(payload.get("target_equity_irr_pct"), 12), "source": "Investor hurdle rate", "confidence": "Medium", "owner": "Investor"},
        ],
    }


class SolarPassportHandler(BaseHTTPRequestHandler):
    server_version = "SolarPassport/0.1"

    def log_message(self, fmt, *args):
        # Keep terminal output concise while still showing requests.
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def send_bytes(self, body: bytes, status: int = 200, content_type: str = "application/octet-stream"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store" if content_type == "application/json" else "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, data: Dict[str, Any], status: int = 200):
        body = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self.send_bytes(body, status, "application/json; charset=utf-8")

    def do_HEAD(self):
        path = urlparse(self.path).path
        if path == "/":
            file_path = BASE_DIR / "templates" / "index.html"
        elif path.startswith("/static/"):
            rel = path[len("/static/"):]
            if ".." in Path(rel).parts:
                self.send_error(400)
                return
            file_path = BASE_DIR / "static" / rel
        elif path == "/api/health":
            body = json.dumps({"ok": True, "pvwatts_configured": bool(NREL_API_KEY)}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return
        else:
            self.send_error(404)
            return
        if not file_path.is_file():
            self.send_error(404)
            return
        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(file_path.stat().st_size))
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            return self.send_json({"ok": True, "pvwatts_configured": bool(NREL_API_KEY)})
        if path == "/":
            file_path = BASE_DIR / "templates" / "index.html"
        elif path.startswith("/static/"):
            rel = path[len("/static/"):]
            if ".." in Path(rel).parts:
                return self.send_json({"error": "Invalid path"}, 400)
            file_path = BASE_DIR / "static" / rel
        else:
            return self.send_json({"error": "Not found"}, 404)

        if not file_path.is_file():
            return self.send_json({"error": "Not found"}, 404)
        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {"application/javascript", "application/json"}:
            content_type += "; charset=utf-8"
        self.send_bytes(file_path.read_bytes(), 200, content_type)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 2_000_000:
                return self.send_json({"error": "Request too large"}, 413)
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            if not isinstance(payload, dict):
                raise ValueError("JSON body must be an object")
            if path == "/api/building/calculate":
                return self.send_json(api_building(payload))
            if path == "/api/project/calculate":
                return self.send_json(api_project(payload))
            return self.send_json({"error": "Not found"}, 404)
        except ValueError as exc:
            return self.send_json({"error": str(exc)}, 400)
        except Exception as exc:
            return self.send_json({"error": f"Calculation failed: {exc}"}, 500)


def run():
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    httpd = ThreadingHTTPServer((host, port), SolarPassportHandler)
    print(f"Solar Passport running at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run()
