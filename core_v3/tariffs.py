from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .policy import PolicyRegistry

@dataclass(frozen=True)
class BillResult:
    tariff_id: str
    consumption_kwh: float
    amount_bnd: float
    subscribed_kva: Optional[float]
    breakdown: tuple[dict, ...]

class TariffEngine:
    def __init__(self, registry: PolicyRegistry):
        self.registry = registry

    def residential_bill(self, consumption_kwh: float) -> BillResult:
        kwh = max(0.0, float(consumption_kwh))
        rule = self.registry.get("DES_TARIFF_A")
        remaining = kwh
        previous_upper = 0.0
        total = 0.0
        rows = []
        for tier in rule.value["tiers"]:
            upper = tier["to_kwh"]
            quantity = remaining if upper is None else min(remaining, max(0.0, float(upper) - previous_upper))
            rate = float(tier["rate_bnd_per_kwh"])
            cost = quantity * rate
            rows.append({"kwh": quantity, "rate_bnd_per_kwh": rate, "cost_bnd": cost})
            total += cost
            remaining -= quantity
            if upper is not None:
                previous_upper = float(upper)
            if remaining <= 1e-12:
                break
        return BillResult(rule.id, kwh, round(total, 10), None, tuple(rows))

    def residential_consumption_from_bill(self, bill_bnd: float) -> float:
        remaining_bill = max(0.0, float(bill_bnd))
        rule = self.registry.get("DES_TARIFF_A")
        previous_upper = 0.0
        usage = 0.0
        for tier in rule.value["tiers"]:
            upper = tier["to_kwh"]
            rate = float(tier["rate_bnd_per_kwh"])
            if upper is None:
                return usage + remaining_bill / rate
            width = float(upper) - previous_upper
            tier_cost = width * rate
            if remaining_bill <= tier_cost + 1e-12:
                return usage + remaining_bill / rate
            usage += width
            remaining_bill -= tier_cost
            previous_upper = float(upper)
        return usage

    def commercial_bill(self, consumption_kwh: float, subscribed_kva: float) -> BillResult:
        kwh = max(0.0, float(consumption_kwh))
        kva = float(subscribed_kva)
        if kva <= 0:
            raise ValueError("Subscribed capacity (kVA) must be greater than zero for DES Tariff B")
        rule = self.registry.get("DES_TARIFF_B")
        remaining = kwh
        total = 0.0
        rows = []
        for block in rule.value["blocks"]:
            rate = float(block["rate_bnd_per_unit"])
            quantity = remaining if block.get("remaining") else min(remaining, float(block["units_times_kva"]) * kva)
            cost = quantity * rate
            rows.append({"kwh": quantity, "rate_bnd_per_kwh": rate, "cost_bnd": cost})
            total += cost
            remaining -= quantity
            if remaining <= 1e-12:
                break
        return BillResult(rule.id, kwh, round(total, 10), kva, tuple(rows))

    def commercial_consumption_from_bill(self, bill_bnd: float, subscribed_kva: float) -> float:
        remaining_bill = max(0.0, float(bill_bnd))
        kva = float(subscribed_kva)
        if kva <= 0:
            raise ValueError("Subscribed capacity (kVA) must be greater than zero for DES Tariff B")
        rule = self.registry.get("DES_TARIFF_B")
        usage = 0.0
        for block in rule.value["blocks"]:
            rate = float(block["rate_bnd_per_unit"])
            if block.get("remaining"):
                return usage + remaining_bill / rate
            width = float(block["units_times_kva"]) * kva
            block_cost = width * rate
            if remaining_bill <= block_cost + 1e-12:
                return usage + remaining_bill / rate
            usage += width
            remaining_bill -= block_cost
        return usage

    def bill(self, tariff: str, consumption_kwh: float, subscribed_kva: Optional[float] = None) -> BillResult:
        key = tariff.strip().lower()
        if key in {"a", "tariff_a", "residential"}:
            return self.residential_bill(consumption_kwh)
        if key in {"b", "tariff_b", "commercial"}:
            if subscribed_kva is None:
                raise ValueError("subscribed_kva is required for commercial Tariff B")
            return self.commercial_bill(consumption_kwh, subscribed_kva)
        raise ValueError(f"Unsupported tariff: {tariff}")
