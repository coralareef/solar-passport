from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


def npv(rate: float, cashflows: list[float]) -> float:
    if rate <= -1:
        raise ValueError("NPV discount rate must be greater than -100%")
    return sum(cf / ((1 + rate) ** i) for i, cf in enumerate(cashflows))


def irr(cashflows: list[float]) -> Optional[float]:
    if not cashflows or not any(x < 0 for x in cashflows) or not any(x > 0 for x in cashflows):
        return None

    def fn(r: float) -> float:
        return npv(r, cashflows)

    lo, hi = -0.95, 1.0
    flo, fhi = fn(lo), fn(hi)
    for _ in range(16):
        if flo * fhi <= 0:
            break
        hi *= 2
        fhi = fn(hi)
    else:
        return None
    for _ in range(150):
        mid = (lo + hi) / 2
        fm = fn(mid)
        if abs(fm) < 1e-8:
            return mid
        if flo * fm <= 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return (lo + hi) / 2


def annuity_payment(principal: float, annual_rate: float, years: int) -> float:
    if principal <= 0 or years <= 0:
        return 0.0
    if annual_rate <= -1:
        raise ValueError("Debt rate must be greater than -100%")
    if abs(annual_rate) < 1e-12:
        return principal / years
    return principal * annual_rate / (1 - (1 + annual_rate) ** (-years))


@dataclass(frozen=True)
class ProjectFinanceInputs:
    capex_bnd: float
    year1_p50_mwh: float
    p90_factor: float
    ppa_bnd_per_kwh: float
    ppa_years: int = 25
    degradation: float = 0.005
    curtailment: float = 0.0
    other_losses: float = 0.0
    opex_year1_bnd: float = 0.0
    opex_escalation: float = 0.02
    tariff_escalation: float = 0.0
    tax_rate: float = 0.0
    discount_rate: float = 0.08
    debt_pct: float = 0.65
    debt_rate: float = 0.055
    debt_tenor_years: int = 15
    dsra_months: float = 6.0
    dsra_funded_by_equity: bool = True
    target_equity_irr: float = 0.12
    minimum_p90_dscr: float = 1.25


@dataclass(frozen=True)
class ProjectFinanceResult:
    project_irr: Optional[float]
    equity_irr: Optional[float]
    project_npv_bnd: float
    lcoe_bnd_per_kwh: Optional[float]
    debt_bnd: float
    equity_bnd: float
    annual_debt_service_bnd: float
    dsra_requirement_bnd: float
    p50_dscr: tuple[Optional[float], ...]
    p90_dscr: tuple[Optional[float], ...]
    minimum_p90_dscr: Optional[float]
    llcr_p50: Optional[float]
    llcr_p90: Optional[float]
    p50_cfads: tuple[float, ...]
    p90_cfads: tuple[float, ...]
    project_cashflows: tuple[float, ...]
    equity_cashflows: tuple[float, ...]


def _whole_years(value, name: str) -> int:
    years = int(value)
    if float(value) != years:
        raise ValueError(f"{name} must be a whole number of years")
    return years


def _validate(i: ProjectFinanceInputs) -> tuple[int, int]:
    if i.capex_bnd <= 0:
        raise ValueError("capex_bnd must be > 0")
    if i.year1_p50_mwh <= 0:
        raise ValueError("year1_p50_mwh must be > 0")
    if not 0 < i.p90_factor <= 1:
        raise ValueError("p90_factor must be in (0, 1]")
    if i.ppa_bnd_per_kwh < 0:
        raise ValueError("ppa_bnd_per_kwh must be >= 0")
    if i.opex_year1_bnd < 0:
        raise ValueError("opex_year1_bnd must be >= 0")

    ppa_years = _whole_years(i.ppa_years, "ppa_years")
    debt_tenor = _whole_years(i.debt_tenor_years, "debt_tenor_years")
    if ppa_years < 1:
        raise ValueError("ppa_years must be >= 1")
    if debt_tenor < 1 or debt_tenor > ppa_years:
        raise ValueError("debt tenor must be within PPA term")

    if not 0 <= i.debt_pct <= 1:
        raise ValueError("debt_pct is a decimal fraction and must be between 0 and 1")
    if not 0 <= i.debt_rate <= 1:
        raise ValueError("debt_rate is a decimal fraction and must be between 0 and 1")
    if not 0 <= i.discount_rate <= 1:
        raise ValueError("discount_rate is a decimal fraction and must be between 0 and 1")
    if not 0 <= i.target_equity_irr <= 1:
        raise ValueError("target_equity_irr is a decimal fraction and must be between 0 and 1 (for example 0.12 for 12%)")
    if i.minimum_p90_dscr <= 0:
        raise ValueError("minimum_p90_dscr must be > 0")
    if not 0 <= i.dsra_months <= 24:
        raise ValueError("dsra_months must be between 0 and 24")

    for name in ("degradation", "curtailment", "other_losses", "tax_rate"):
        value = getattr(i, name)
        if not 0 <= value < 1:
            raise ValueError(f"{name} is a decimal fraction and must be in [0,1)")
    for name in ("opex_escalation", "tariff_escalation"):
        value = getattr(i, name)
        if not -0.99 < value <= 1:
            raise ValueError(f"{name} must be a decimal rate greater than -0.99 and no greater than 1")
    return ppa_years, debt_tenor


def _cfads_series(i: ProjectFinanceInputs, p90: bool, ppa_years: Optional[int] = None) -> list[float]:
    years = ppa_years if ppa_years is not None else _whole_years(i.ppa_years, "ppa_years")
    factor = i.p90_factor if p90 else 1.0
    out = []
    for year in range(1, years + 1):
        gross_mwh = i.year1_p50_mwh * factor * ((1 - i.degradation) ** (year - 1))
        sold_mwh = gross_mwh * (1 - i.curtailment) * (1 - i.other_losses)
        tariff = i.ppa_bnd_per_kwh * ((1 + i.tariff_escalation) ** (year - 1))
        revenue = sold_mwh * 1000 * tariff
        opex = i.opex_year1_bnd * ((1 + i.opex_escalation) ** (year - 1))
        ebitda = revenue - opex
        tax = max(0.0, ebitda) * i.tax_rate
        out.append(ebitda - tax)
    return out


def _llcr(cfads: list[float], debt: float, debt_rate: float, tenor: int) -> Optional[float]:
    if debt <= 0:
        return None
    return sum(cfads[y - 1] / ((1 + debt_rate) ** y) for y in range(1, tenor + 1)) / debt


def model_project_finance(i: ProjectFinanceInputs) -> ProjectFinanceResult:
    ppa_years, debt_tenor = _validate(i)
    debt = i.capex_bnd * i.debt_pct
    annual_ds = annuity_payment(debt, i.debt_rate, debt_tenor)
    dsra = annual_ds * i.dsra_months / 12 if debt > 0 else 0.0
    equity = i.capex_bnd - debt + (dsra if i.dsra_funded_by_equity else 0.0)
    p50 = _cfads_series(i, False, ppa_years)
    p90 = _cfads_series(i, True, ppa_years)
    p50_dscr, p90_dscr = [], []
    equity_flows = [-equity]
    project_flows = [-i.capex_bnd]

    for year in range(1, ppa_years + 1):
        service = annual_ds if year <= debt_tenor else 0.0
        p50_dscr.append(p50[year - 1] / service if service > 0 else None)
        p90_dscr.append(p90[year - 1] / service if service > 0 else None)
        equity_flows.append(p50[year - 1] - service)
        project_flows.append(p50[year - 1])

    # An equity-funded DSRA is reserved at financial close and released after the
    # final scheduled debt-service year in this screening model.
    if i.dsra_funded_by_equity and dsra > 0:
        equity_flows[debt_tenor] += dsra

    discounted_cost = i.capex_bnd
    discounted_energy_kwh = 0.0
    for year in range(1, ppa_years + 1):
        discounted_cost += i.opex_year1_bnd * ((1 + i.opex_escalation) ** (year - 1)) / ((1 + i.discount_rate) ** year)
        energy_kwh = i.year1_p50_mwh * 1000 * ((1 - i.degradation) ** (year - 1)) * (1 - i.curtailment) * (1 - i.other_losses)
        discounted_energy_kwh += energy_kwh / ((1 + i.discount_rate) ** year)

    min_p90 = min((x for x in p90_dscr if x is not None), default=None)
    return ProjectFinanceResult(
        irr(project_flows), irr(equity_flows), npv(i.discount_rate, project_flows),
        discounted_cost / discounted_energy_kwh if discounted_energy_kwh > 0 else None,
        debt, equity, annual_ds, dsra, tuple(p50_dscr), tuple(p90_dscr), min_p90,
        _llcr(p50, debt, i.debt_rate, debt_tenor),
        _llcr(p90, debt, i.debt_rate, debt_tenor),
        tuple(p50), tuple(p90), tuple(project_flows), tuple(equity_flows),
    )


def solve_tariff(i: ProjectFinanceInputs, objective: str, *, lower: float = 0.0, upper: float = 1.0) -> Optional[float]:
    _validate(i)

    def passes(t: float) -> bool:
        result = model_project_finance(ProjectFinanceInputs(**{**i.__dict__, "ppa_bnd_per_kwh": t}))
        if objective == "equity_irr":
            return result.equity_irr is not None and result.equity_irr >= i.target_equity_irr
        if objective == "p90_dscr":
            return result.minimum_p90_dscr is None or result.minimum_p90_dscr >= i.minimum_p90_dscr
        if objective == "npv":
            return result.project_npv_bnd >= 0
        raise ValueError("objective must be equity_irr, p90_dscr or npv")

    hi = upper
    for _ in range(8):
        if passes(hi):
            break
        hi *= 2
    else:
        return None
    lo = lower
    for _ in range(90):
        mid = (lo + hi) / 2
        if passes(mid):
            hi = mid
        else:
            lo = mid
    return hi


def debt_capacity_for_dscr(i: ProjectFinanceInputs, *, max_debt_pct: Optional[float] = None) -> float:
    _, debt_tenor = _validate(i)
    leverage_cap = i.debt_pct if max_debt_pct is None else min(i.debt_pct, max_debt_pct)
    if not 0 <= leverage_cap <= 1:
        raise ValueError("max_debt_pct must be a decimal fraction between 0 and 1")
    max_debt = i.capex_bnd * leverage_cap
    if max_debt <= 0:
        return 0.0
    p90 = _cfads_series(i, True)
    min_cfads = min(p90[:debt_tenor])
    max_service = min_cfads / i.minimum_p90_dscr
    if i.debt_rate == 0:
        dscr_debt = max_service * debt_tenor
    else:
        dscr_debt = max_service * (1 - (1 + i.debt_rate) ** (-debt_tenor)) / i.debt_rate
    return max(0.0, min(max_debt, dscr_debt))
