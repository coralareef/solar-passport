from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional, Callable

_GENERATION_FN: Optional[Callable[..., Dict[str, Any]]] = None

def configure_generation(fn: Callable[..., Dict[str, Any]]) -> None:
    global _GENERATION_FN
    _GENERATION_FN = fn

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
    if not cashflows or not any(x < 0 for x in cashflows) or not any(x > 0 for x in cashflows):
        return None
    def value(rate: float) -> float:
        return npv(max(rate, -0.999999), cashflows)
    lo, hi = -0.95, 10.0
    vlo, vhi = value(lo), value(hi)
    for _ in range(8):
        if vlo == 0: return lo
        if vhi == 0: return hi
        if vlo * vhi < 0: break
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

# ---- Brunei electricity tariffs ----
# Tariff A – Residential
def tariff_a_cost(kwh: float) -> float:
    remaining = max(0.0, kwh)
    total = 0.0
    for qty, rate in ((600.0, 0.01), (1400.0, 0.08), (2000.0, 0.10)):
        used = min(remaining, qty)
        total += used * rate
        remaining -= used
        if remaining <= 0:
            return total
    return total + remaining * 0.12

def usage_from_tariff_a_bill(bill: float) -> float:
    remaining = max(0.0, bill)
    usage = 0.0
    for qty, rate in ((600.0, 0.01), (1400.0, 0.08), (2000.0, 0.10)):
        tier_cost = qty * rate
        if remaining <= tier_cost:
            return usage + remaining / rate
        usage += qty
        remaining -= tier_cost
    return usage + remaining / 0.12

# Tariff B – Commercial. "Units" are kWh thresholds multiplied by subscribed kVA.
def tariff_b_cost(kwh: float, subscribed_kva: float, minimum_charge: float = 2.0) -> float:
    kwh = max(0.0, f(kwh))
    kva = max(0.0, f(subscribed_kva))
    if kva <= 0:
        raise ValueError("Commercial Tariff B requires subscribed capacity (kVA).")
    remaining = kwh
    total = 0.0
    for units_per_kva, rate in ((10.0, 0.20), (100.0, 0.07), (100.0, 0.06)):
        qty = units_per_kva * kva
        used = min(remaining, qty)
        total += used * rate
        remaining -= used
        if remaining <= 0:
            return max(minimum_charge, total)
    total += remaining * 0.05
    return max(minimum_charge, total)

def usage_from_tariff_b_bill(bill: float, subscribed_kva: float, minimum_charge: float = 2.0) -> float:
    bill = max(0.0, f(bill))
    kva = max(0.0, f(subscribed_kva))
    if kva <= 0:
        raise ValueError("Commercial Tariff B requires subscribed capacity (kVA).")
    if bill <= minimum_charge:
        return min((bill / 0.20), 10.0 * kva)
    remaining = bill
    usage = 0.0
    for units_per_kva, rate in ((10.0, 0.20), (100.0, 0.07), (100.0, 0.06)):
        qty = units_per_kva * kva
        tier_cost = qty * rate
        if remaining <= tier_cost:
            return usage + remaining / rate
        usage += qty
        remaining -= tier_cost
    return usage + remaining / 0.05

def calculate_bill(kwh: float, tariff_type: str, flat_rate: float = 0.0, fixed_charge: float = 0.0, subscribed_kva: float = 0.0) -> float:
    if tariff_type == "tariff_a":
        return tariff_a_cost(kwh) + max(0.0, fixed_charge)
    if tariff_type == "tariff_b":
        return tariff_b_cost(kwh, subscribed_kva) + max(0.0, fixed_charge)
    return max(0.0, kwh) * max(0.0, flat_rate) + max(0.0, fixed_charge)

def _normalise_building_input(payload: Dict[str, Any]) -> Dict[str, float | str]:
    choice = str(payload.get("customer_tariff_choice") or "").lower()
    tariff_type = str(payload.get("tariff_type") or "").lower()
    if choice in {"residential", "home"}:
        tariff_type = "tariff_a"
    elif choice in {"business", "commercial"}:
        tariff_type = "tariff_b"
    elif tariff_type not in {"tariff_a", "tariff_b", "flat"}:
        tariff_type = "tariff_a"

    input_mode = str(payload.get("electricity_input_mode") or "kwh").lower()
    monthly_kwh = max(0.0, f(payload.get("monthly_kwh"), 0.0))
    monthly_bill = max(0.0, f(payload.get("monthly_bill"), 0.0))
    annual_kwh = max(0.0, f(payload.get("annual_kwh"), 0.0))
    flat_rate = max(0.0, f(payload.get("flat_rate"), 0.0678))
    fixed_charge = max(0.0, f(payload.get("fixed_charge"), 0.0))
    kva = max(0.0, f(payload.get("subscribed_kva"), 0.0))

    if annual_kwh > 0 and monthly_kwh <= 0 and input_mode != "bill":
        monthly_kwh = annual_kwh / 12.0

    if tariff_type == "tariff_b" and kva <= 0:
        raise ValueError("Commercial Tariff B needs the subscribed capacity (kVA) shown on the electricity account/bill.")

    if input_mode == "bill":
        if monthly_bill <= 0:
            raise ValueError("Enter a typical monthly electricity bill.")
        if tariff_type == "tariff_a":
            monthly_kwh = usage_from_tariff_a_bill(monthly_bill)
        elif tariff_type == "tariff_b":
            monthly_kwh = usage_from_tariff_b_bill(monthly_bill, kva)
        else:
            if flat_rate <= 0:
                raise ValueError("A custom tariff rate is required to estimate kWh from a bill.")
            monthly_kwh = max(0.0, monthly_bill - fixed_charge) / flat_rate
    else:
        if monthly_kwh <= 0:
            if annual_kwh > 0:
                monthly_kwh = annual_kwh / 12.0
            else:
                raise ValueError("Enter typical monthly electricity consumption in kWh.")
        monthly_bill = calculate_bill(monthly_kwh, tariff_type, flat_rate, fixed_charge, kva)

    return {
        "tariff_type": tariff_type,
        "input_mode": input_mode,
        "monthly_kwh": monthly_kwh,
        "monthly_bill": monthly_bill,
        "annual_kwh": monthly_kwh * 12.0,
        "flat_rate": flat_rate,
        "fixed_charge": fixed_charge,
        "subscribed_kva": kva,
    }

def building_cashflows(capex: float, year1_savings: float, o_and_m_pct: float, degradation: float,
                       opex_escalation: float, inverter_year: int, inverter_pct: float, years: int = 25) -> List[float]:
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
            return (year - 1) + (-prev) / flows[year]
    return None

def evaluate_building_capacity(payload: Dict[str, Any], capacity_kwp: float) -> Dict[str, Any]:
    if _GENERATION_FN is None:
        raise RuntimeError("Solar generation model is not configured.")

    electricity = _normalise_building_input(payload)
    monthly_load = [electricity["monthly_kwh"]] * 12
    annual_load = float(electricity["annual_kwh"])
    daytime_share = pct(payload.get("daytime_share_pct"), 65.0)
    export_credit = max(0.0, f(payload.get("export_credit"), 0.0))
    specific_yield = max(1.0, f(payload.get("specific_yield"), 1420.0))

    lat = f(payload.get("lat"), 4.9031)
    lon = f(payload.get("lon"), 114.9398)
    tilt = f(payload.get("tilt"), 10.0)
    azimuth = f(payload.get("azimuth"), 180.0)
    losses = f(payload.get("losses"), 14.0)
    generation = _GENERATION_FN(lat, lon, capacity_kwp, tilt, azimuth, losses, specific_yield)
    monthly_pv = generation["monthly_kwh"]

    rows = []
    bill_before_total = bill_after_total = self_consumed_total = export_total = credit_total = 0.0
    for i, (load, solar) in enumerate(zip(monthly_load, monthly_pv)):
        daytime_load = load * daytime_share
        self_consumed = min(solar, daytime_load)
        export = max(0.0, solar - self_consumed)
        import_kwh = max(0.0, load - self_consumed)
        bill_before = calculate_bill(load, electricity["tariff_type"], electricity["flat_rate"],
                                     electricity["fixed_charge"], electricity["subscribed_kva"])
        gross_after = calculate_bill(import_kwh, electricity["tariff_type"], electricity["flat_rate"],
                                     electricity["fixed_charge"], electricity["subscribed_kva"])
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
    annual_generation = float(generation["annual_kwh"])
    self_consumption_pct = self_consumed_total / annual_generation * 100 if annual_generation > 0 else 0.0
    load_coverage_pct = self_consumed_total / annual_load * 100 if annual_load > 0 else 0.0

    capex_per_kwp = max(0.0, f(payload.get("capex_per_kwp"), 1500.0))
    capex = capacity_kwp * capex_per_kwp + max(0.0, f(payload.get("development_cost"), 0.0))
    om_pct = pct(payload.get("om_pct"), 1.0)
    degradation = pct(payload.get("degradation_pct"), 0.5)
    escalation = pct(payload.get("opex_escalation_pct"), 2.0)
    inverter_year = int(clamp(f(payload.get("inverter_year"), 12), 1, 25))
    inverter_pct = pct(payload.get("inverter_replacement_pct"), 8.0)
    discount_rate = pct(payload.get("discount_rate_pct"), 8.0)

    flows = building_cashflows(capex, annual_saving, om_pct, degradation, escalation, inverter_year, inverter_pct)
    project_irr = irr(flows)
    project_npv = npv(discount_rate, flows)
    payback = simple_payback(flows)

    down_payment = pct(payload.get("down_payment_pct"), 20.0)
    loan_rate = pct(payload.get("loan_rate_pct"), 5.5)
    loan_years = int(clamp(f(payload.get("loan_years"), 10), 1, 25))
    financed = max(0.0, capex * (1 - down_payment))
    monthly_debt = annuity_payment(financed, loan_rate, loan_years, 12)
    first_year_om = capex * om_pct
    monthly_net_cash = annual_saving / 12 - first_year_om / 12 - monthly_debt

    return {
        "capacity_kwp": round(capacity_kwp, 2),
        "annual_load_kwh": round(annual_load, 1),
        "inferred_monthly_bill": round(float(electricity["monthly_bill"]), 2),
        "inferred_monthly_kwh": round(float(electricity["monthly_kwh"]), 1),
        "tariff_type": electricity["tariff_type"],
        "subscribed_kva": round(float(electricity["subscribed_kva"]), 2) if electricity["tariff_type"] == "tariff_b" else None,
        "annual_generation_kwh": round(annual_generation, 1),
        "capacity_factor_pct": round(float(generation.get("capacity_factor", 0.0)), 2),
        "generation_source": generation.get("source", "Unknown"),
        "generation_confidence": generation.get("source_confidence", "Unknown"),
        "generation_cache": generation.get("cache_status"),
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
    irr_val = result["project_irr_pct"]
    finance = 100.0 if irr_val is not None and irr_val >= 8 else max(20.0, 60 + (irr_val or -10) * 2)
    self_use = min(100.0, result["self_consumption_pct"])
    energy_profile = 90.0 if result["annual_load_kwh"] > 0 else 55.0
    resource = 85.0 if "NREL PVWatts" in str(result["generation_source"]) else 55.0
    implementation = pct(payload.get("implementation_readiness_pct"), 60.0) * 100
    net_meter = pct(payload.get("net_metering_readiness_pct"), 50.0) * 100
    blocks = [
        ("Energy profile", 15, energy_profile), ("Solar resource", 10, resource),
        ("Roof / site", 15, roof), ("Self-consumption", 10, self_use),
        ("Financial attractiveness", 20, finance), ("Financing", 10, 80.0 if result["monthly_debt_payment"] > 0 else 60.0),
        ("Net-metering readiness", 5, net_meter), ("Electrical readiness", 5, electrical),
        ("Documentation", 5, documentation), ("Implementation risk", 5, implementation),
    ]
    score = sum(weight * val / 100 for _, weight, val in blocks)
    model_irr, model_npv = result["project_irr_pct"], result["npv"]
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
    return {"score": round(score), "status": status,
            "blocks": [{"name": n, "weight": w, "score": round(v)} for n, w, v in blocks]}

def recommend_building(payload: Dict[str, Any]) -> Dict[str, Any]:
    roof_area = max(0.0, f(payload.get("roof_area_m2"), 250.0))
    usable_factor = pct(payload.get("usable_roof_pct"), 75.0)
    area_per_kwp = max(3.0, f(payload.get("area_per_kwp"), 6.5))
    max_roof = roof_area * usable_factor / area_per_kwp
    if max_roof <= 0:
        raise ValueError("Roof area and usable-roof assumptions produce no usable solar capacity.")

    probe_cap = max(0.1, min(max_roof, 1.0))
    base = evaluate_building_capacity(payload, probe_cap)
    annual_load = base["annual_load_kwh"]
    yield_per_kwp = base["annual_generation_kwh"] / base["capacity_kwp"] if base["capacity_kwp"] > 0 else max(1.0, f(payload.get("specific_yield"), 1420))
    yield_per_kwp = max(1.0, yield_per_kwp)
    max_bill_offset = annual_load / yield_per_kwp
    daytime_share = pct(payload.get("daytime_share_pct"), 65.0)
    self_consumption_size = annual_load * daytime_share / yield_per_kwp

    upper = max(0.1, max_roof)
    candidates = []
    for i in range(1, 33):
        candidates.append(evaluate_building_capacity(payload, upper * i / 32.0))

    def irr_key(r: Dict[str, Any]) -> float:
        return r["project_irr_pct"] if r["project_irr_pct"] is not None else -999.0

    best_irr_raw = max(candidates, key=irr_key)
    best_irr_value = irr_key(best_irr_raw)
    near_best = [r for r in candidates if irr_key(r) >= best_irr_value - 0.05]
    best_irr = max(near_best, key=lambda r: r["capacity_kwp"]) if near_best else best_irr_raw
    best_npv = max(candidates, key=lambda r: r["npv"])
    best_cash = max(candidates, key=lambda r: r["first_year_net_monthly_cash"])

    cases = {
        "maximum_roof": evaluate_building_capacity(payload, max_roof),
        "bill_offset": evaluate_building_capacity(payload, max(0.1, min(max_roof, max_bill_offset))),
        "self_consumption": evaluate_building_capacity(payload, max(0.1, min(max_roof, self_consumption_size))),
        "financial_return": best_irr,
        "maximum_npv": best_npv,
        "cash_flow": best_cash,
    }
    selected_mode = str(payload.get("sizing_mode") or "financial_return")
    selected = cases.get(selected_mode, best_irr)
    return {
        "max_roof_kwp": round(max_roof, 1),
        "max_bill_offset_kwp": round(min(max_roof, max_bill_offset), 1),
        "self_consumption_kwp": round(min(max_roof, self_consumption_size), 1),
        "financial_return_kwp": best_irr["capacity_kwp"],
        "maximum_npv_kwp": best_npv["capacity_kwp"],
        "cash_flow_kwp": best_cash["capacity_kwp"],
        "pv_yield_per_kwp": round(yield_per_kwp, 1),
        "selected": selected,
    }

def api_building(payload: Dict[str, Any]) -> Dict[str, Any]:
    recommendation = recommend_building(payload)
    selected = recommendation["selected"]
    readiness = building_readiness(payload, selected)
    reasons = []
    if selected["self_consumption_pct"] < 65:
        reasons.append("Estimated excess export is relatively high; a smaller system or more daytime electricity use may improve value.")
    if selected["project_irr_pct"] is not None and selected["project_irr_pct"] < 8:
        reasons.append("Financial return is below the 8% screening reference under the current cost and tariff assumptions.")
    if selected["first_year_net_monthly_cash"] < 0:
        reasons.append("The financing assumptions produce negative first-year monthly cash flow.")
    if "NREL PVWatts" not in str(selected["generation_source"]):
        reasons.append("Generation is using the fallback yield rather than PVWatts.")
    if not reasons:
        reasons.append("The selected sizing case is financially and operationally coherent under the stated assumptions.")
    tariff_label = {"tariff_a": "DES Tariff A – Residential", "tariff_b": "DES Tariff B – Commercial", "flat": "Custom flat tariff"}.get(selected["tariff_type"], selected["tariff_type"])
    assumptions = [
        {"variable": "Electricity tariff", "value": tariff_label, "source": "Account type / DES tariff model", "confidence": "High" if selected["tariff_type"] in {"tariff_a","tariff_b"} else "Medium", "owner": "Platform"},
        {"variable": "Monthly electricity use", "value": selected["inferred_monthly_kwh"], "source": "Entered or tariff-derived", "confidence": "Medium-High", "owner": "Customer"},
        {"variable": "PV generation", "value": recommendation["pv_yield_per_kwp"], "source": selected["generation_source"], "confidence": selected["generation_confidence"], "owner": "Platform"},
        {"variable": "PV CAPEX (BND/kWp)", "value": f(payload.get("capex_per_kwp"), 1500.0), "source": "Market assumption until quote", "confidence": "Medium", "owner": "Customer"},
        {"variable": "Daytime load share (%)", "value": f(payload.get("daytime_share_pct"), 65.0), "source": "Building-type estimate", "confidence": "Low-Medium", "owner": "Platform"},
        {"variable": "Export credit (BND/kWh)", "value": f(payload.get("export_credit"), 0.0), "source": "User / policy assumption", "confidence": "Low-Medium", "owner": "Customer"},
    ]
    if selected["tariff_type"] == "tariff_b":
        assumptions.insert(1, {"variable": "Subscribed capacity (kVA)", "value": selected["subscribed_kva"], "source": "Customer electricity account", "confidence": "High", "owner": "Customer"})
    return {"recommendation": recommendation, "readiness": readiness, "decision_reasons": reasons[:5], "assumptions": assumptions}

# ---- Project bankability model ----
def project_model(payload: Dict[str, Any], tariff: float, use_p90: bool = False, capex_per_mw_override: Optional[float] = None) -> Dict[str, Any]:
    mwp = max(0.001, f(payload.get("mwp"), 120.0))
    mwac = max(0.001, f(payload.get("mwac"), 100.0))
    p50_specific = max(1.0, f(payload.get("p50_specific_yield"), 1500.0))
    p90_factor = clamp(f(payload.get("p90_factor_pct"), 95.0), 50, 100) / 100
    degradation = pct(payload.get("degradation_pct"), 0.45)
    curtailment = pct(payload.get("curtailment_pct"), 2.0)
    other_losses = pct(payload.get("other_losses_pct"), 1.0)
    ppa_years = int(clamp(f(payload.get("ppa_years"), 25), 5, 40))

    capex_per_mw = capex_per_mw_override if capex_per_mw_override is not None else max(0.0, f(payload.get("capex_per_mw"), 1_500_000.0))
    total_capex = mwac * capex_per_mw
    opex_per_mw = max(0.0, f(payload.get("opex_per_mw_year"), 24_000.0))
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

    base_generation_mwh = mwp * p50_specific * (p90_factor if use_p90 else 1.0)
    project_flows = [-total_capex]
    equity_flows = [-equity]
    dscrs, energy_series, revenue_series, cfads_series = [], [], [], []

    for year in range(1, ppa_years + 1):
        gross = base_generation_mwh * ((1 - degradation) ** (year - 1))
        sold_mwh = gross * (1 - curtailment) * (1 - other_losses)
        year_tariff = tariff * ((1 + tariff_escalation) ** (year - 1))
        revenue = sold_mwh * 1000 * year_tariff
        opex = mwac * opex_per_mw * ((1 + opex_escalation) ** (year - 1))
        ebitda = revenue - opex
        tax = max(0.0, ebitda) * tax_rate
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

    if not use_p90 and debt > 0:
        p90 = project_model(payload, tariff, use_p90=True, capex_per_mw_override=capex_per_mw)
        min_p90_dscr = p90["min_dscr"]
    elif use_p90:
        min_p90_dscr = min(dscrs) if dscrs else None
    else:
        min_p90_dscr = None

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
        "tariff": tariff, "total_capex": total_capex, "debt": debt, "equity": equity,
        "debt_pct": debt_pct * 100, "dscr_applicable": debt > 0,
        "year1_energy_mwh": energy_series[0] if energy_series else 0.0,
        "year1_revenue": revenue_series[0] if revenue_series else 0.0,
        "year1_cfads": cfads_series[0] if cfads_series else 0.0,
        "annual_debt_service": annual_debt_service,
        "min_dscr": min(dscrs) if dscrs else None, "min_p90_dscr": min_p90_dscr,
        "project_irr_pct": project_irr * 100 if project_irr is not None else None,
        "equity_irr_pct": equity_irr * 100 if equity_irr is not None else None,
        "npv": project_npv, "lcoe": lcoe,
    }

def solve_tariff(payload: Dict[str, Any], objective: str) -> Optional[float]:
    target_equity_irr = f(payload.get("target_equity_irr_pct"), 12.0)
    min_dscr = f(payload.get("min_dscr"), 1.25)
    if objective == "dscr" and pct(payload.get("debt_pct"), 65.0) <= 0:
        return None
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
        if passes(mid): hi = mid
        else: lo = mid
    return hi

def project_readiness(payload: Dict[str, Any]) -> Dict[str, Any]:
    scores = {
        "Sponsor capability": pct(payload.get("sponsor_score"), 70.0) * 100,
        "Financing readiness": pct(payload.get("financing_score"), 65.0) * 100,
        "Site / land": pct(payload.get("site_score"), 70.0) * 100,
        "Solar resource": pct(payload.get("resource_score"), 70.0) * 100,
        "Grid": pct(payload.get("grid_score"), 55.0) * 100,
        "PPA / offtake readiness": pct(payload.get("ppa_score"), 55.0) * 100,
        "Approvals / environmental": pct(payload.get("approvals_score"), 60.0) * 100,
        "Execution": pct(payload.get("execution_score"), 65.0) * 100,
        "Risk allocation": pct(payload.get("risk_allocation_score"), 55.0) * 100,
    }
    weights = {
        "Sponsor capability": 10, "Financing readiness": 15, "Site / land": 10,
        "Solar resource": 10, "Grid": 15, "PPA / offtake readiness": 15,
        "Approvals / environmental": 10, "Execution": 10, "Risk allocation": 5,
    }
    total = sum(scores[k] * weights[k] / 100 for k in scores)
    status = "GREEN — READY" if total >= 80 else "AMBER — READINESS GAPS" if total >= 55 else "RED — NOT READY"
    return {"score": round(total), "status": status,
            "blocks": [{"name": k, "weight": weights[k], "score": round(scores[k])} for k in scores]}

def api_project(payload: Dict[str, Any]) -> Dict[str, Any]:
    mwp, mwac = f(payload.get("mwp"), 0), f(payload.get("mwac"), 0)
    capex_per_mw = f(payload.get("capex_per_mw"), 0)
    ppa_years = f(payload.get("ppa_years"), 0)
    tariff = f(payload.get("ppa_tariff"), 0.07)
    debt_pct = pct(payload.get("debt_pct"), 65.0)

    if mwp <= 0 or mwac <= 0:
        raise ValueError("DC and AC project capacities must be greater than zero.")
    if capex_per_mw <= 0:
        raise ValueError("All-in CAPEX per MWac must be greater than zero.")
    if ppa_years < 5:
        raise ValueError("PPA term must be at least 5 years for this model.")
    if tariff < 0:
        raise ValueError("PPA tariff cannot be negative.")
    if debt_pct > 0:
        if str(payload.get("debt_rate_pct", "")).strip() == "":
            raise ValueError("Debt rate is required when debt is greater than 0%.")
        if str(payload.get("debt_tenor_years", "")).strip() == "":
            raise ValueError("Debt tenor is required when debt is greater than 0%.")

    result = project_model(payload, tariff)
    irr_tariff = solve_tariff(payload, "irr")
    dscr_tariff = solve_tariff(payload, "dscr")
    npv_tariff = solve_tariff(payload, "npv")
    floors = [x for x in (irr_tariff, dscr_tariff, npv_tariff) if x is not None]
    developer_floor = max(floors) if floors else None
    ceiling = max(0.0, f(payload.get("offtaker_ceiling"), 0.0))
    corridor_known = ceiling > 0 and developer_floor is not None
    corridor_exists = corridor_known and developer_floor <= ceiling

    target_irr = f(payload.get("target_equity_irr_pct"), 12.0)
    min_dscr = f(payload.get("min_dscr"), 1.25)
    irr_pass = result["equity_irr_pct"] is not None and result["equity_irr_pct"] >= target_irr
    dscr_pass = True if not result["dscr_applicable"] else (result["min_p90_dscr"] is not None and result["min_p90_dscr"] >= min_dscr)
    npv_pass = result["npv"] >= 0
    economics_pass = irr_pass and dscr_pass and npv_pass
    readiness = project_readiness(payload)

    if not economics_pass:
        overall = "RED — ECONOMICS FAIL"
    elif corridor_known and not corridor_exists:
        overall = "AMBER — OFFTAKER / TARIFF GAP"
    elif readiness["score"] >= 80:
        overall = "GREEN — ECONOMICS PASS & READY"
    else:
        overall = "AMBER — ECONOMICS PASS, READINESS GAPS"

    binding = None
    if developer_floor is not None:
        candidates = {"Equity IRR": irr_tariff, "P90 DSCR": dscr_tariff, "Project NPV": npv_tariff}
        valid = {k:v for k,v in candidates.items() if v is not None}
        binding = max(valid, key=valid.get) if valid else None

    capex_cases = payload.get("sensitivity_capex_cases") or [1_100_000, 1_300_000, 1_500_000, 1_800_000, 2_000_000]
    tariff_cases = payload.get("sensitivity_tariff_cases") or [0.06, 0.07, 0.08, 0.09, 0.10, 0.12]
    matrix = []
    for capex in capex_cases:
        cells = []
        for t in tariff_cases:
            m = project_model(payload, f(t), capex_per_mw_override=f(capex))
            cells.append({
                "tariff": f(t),
                "equity_irr_pct": round(m["equity_irr_pct"], 1) if m["equity_irr_pct"] is not None else None,
                "p90_dscr": round(m["min_p90_dscr"], 2) if m["min_p90_dscr"] is not None else None,
                "npv_m": round(m["npv"] / 1_000_000, 1),
                "dscr_applicable": m["dscr_applicable"],
            })
        matrix.append({"capex_per_mw": f(capex), "cells": cells})

    interventions = []
    if not irr_pass:
        interventions.append("Test lower CAPEX, higher tariff, or a different capital structure to meet the target equity IRR.")
    if result["dscr_applicable"] and not dscr_pass:
        interventions.append("Improve debt sizing/rate/tenor or project cash flow to meet the P90 DSCR requirement.")
    if not npv_pass:
        interventions.append("The project has negative NPV at the selected discount rate; improve revenue or reduce lifecycle cost.")
    if corridor_known and not corridor_exists:
        interventions.append("The developer floor is above the offtaker ceiling; there is no bankability corridor under current assumptions.")
    if readiness["score"] < 80:
        weak = sorted(readiness["blocks"], key=lambda x: x["score"])[:3]
        interventions.append("Close the lowest readiness gaps: " + ", ".join(x["name"] for x in weak) + ".")
    if not interventions:
        interventions.append("Economics and readiness clear the current screening thresholds; proceed to detailed diligence and transaction structuring.")

    return {
        "overall_status": overall,
        "economics": {
            "pass": economics_pass, "equity_irr_pass": irr_pass, "p90_dscr_pass": dscr_pass,
            "npv_pass": npv_pass, "dscr_applicable": result["dscr_applicable"],
        },
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
            "corridor_exists": corridor_exists if corridor_known else None,
        },
        "readiness": readiness,
        "sensitivity": {"tariffs": tariff_cases, "matrix": matrix},
        "interventions": interventions[:6],
        "assumptions": [
            {"variable": "CAPEX / MWac", "value": capex_per_mw, "source": "User / project assumption", "confidence": "Medium", "owner": "Developer"},
            {"variable": "P50 specific yield", "value": f(payload.get("p50_specific_yield"), 1500), "source": "User / resource assumption", "confidence": "Medium", "owner": "Developer"},
            {"variable": "P90 factor", "value": f(payload.get("p90_factor_pct"), 95), "source": "User assumption until resource study", "confidence": "Low-Medium", "owner": "Developer"},
            {"variable": "Debt share", "value": f(payload.get("debt_pct"), 65), "source": "Financing assumption", "confidence": "Medium", "owner": "Developer"},
            {"variable": "Target equity IRR", "value": target_irr, "source": "Investor hurdle rate", "confidence": "Medium", "owner": "Investor"},
        ],
    }
