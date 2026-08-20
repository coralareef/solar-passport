from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Optional

ACTIVE_STATUSES = {"verified", "effective", "active"}

@dataclass(frozen=True)
class PolicyRule:
    id: str
    topic: str
    status: str
    value: Any
    source_title: Optional[str] = None
    source_url: Optional[str] = None
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    verified_on: Optional[str] = None
    notes: Optional[str] = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "PolicyRule":
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{k: raw.get(k) for k in allowed})

    def is_effective(self, on_date: date) -> bool:
        if self.status not in ACTIVE_STATUSES:
            return False
        if self.effective_from and date.fromisoformat(self.effective_from) > on_date:
            return False
        if self.effective_to and date.fromisoformat(self.effective_to) < on_date:
            return False
        return True

class PolicyRegistry:
    def __init__(self, rules: Iterable[PolicyRule], *, registry_version: str = "unknown", jurisdiction: str = "Brunei Darussalam"):
        self.registry_version = registry_version
        self.jurisdiction = jurisdiction
        self._rules = list(rules)
        self._by_id = {rule.id: rule for rule in self._rules}
        if len(self._by_id) != len(self._rules):
            raise ValueError("Policy registry contains duplicate rule IDs")

    @classmethod
    def from_path(cls, path: str | Path) -> "PolicyRegistry":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls((PolicyRule.from_dict(x) for x in data.get("rules", [])), registry_version=data.get("registry_version", "unknown"), jurisdiction=data.get("jurisdiction", "Brunei Darussalam"))

    def get(self, rule_id: str, *, require_effective: bool = False, on_date: Optional[date] = None) -> PolicyRule:
        try:
            rule = self._by_id[rule_id]
        except KeyError as exc:
            raise KeyError(f"Unknown policy rule: {rule_id}") from exc
        if require_effective and not rule.is_effective(on_date or date.today()):
            raise ValueError(f"Policy rule {rule_id} is not effective on {on_date or date.today()}")
        return rule

    def by_topic(self, topic: str, *, effective_only: bool = False, on_date: Optional[date] = None) -> list[PolicyRule]:
        rules = [r for r in self._rules if r.topic == topic]
        if effective_only:
            d = on_date or date.today()
            rules = [r for r in rules if r.is_effective(d)]
        return rules

    def snapshot(self, rule_ids: Iterable[str], *, on_date: Optional[date] = None) -> dict[str, Any]:
        d = on_date or date.today()
        selected = [self.get(rule_id) for rule_id in rule_ids]
        return {"registry_version": self.registry_version, "jurisdiction": self.jurisdiction, "as_of": d.isoformat(), "rules": [{"id": r.id, "topic": r.topic, "status": r.status, "value": r.value, "source_title": r.source_title, "source_url": r.source_url, "effective_from": r.effective_from, "verified_on": r.verified_on, "effective_on_date": r.is_effective(d)} for r in selected]}

def validate_net_metering_eligibility(registry: PolicyRegistry, *, capacity_kw: float, is_existing_des_customer: bool, has_outstanding_arrears: bool, technology: str, customer_category: str, electricity_act_offence: bool = False) -> dict[str, Any]:
    cap_rule = registry.get("NM_CAPACITY_RANGE")
    eligibility = registry.get("NM_CUSTOMER_ELIGIBILITY")
    cap = cap_rule.value
    el = eligibility.value
    checks = {
        "capacity": cap["minimum_kw"] <= capacity_kw <= cap["maximum_kw"],
        "existing_des_customer": bool(is_existing_des_customer) if el.get("existing_des_customer_required") else True,
        "no_outstanding_arrears": (not has_outstanding_arrears) if el.get("no_outstanding_arrears_required") else True,
        "solar_pv_only": technology.strip().lower() in {"solar", "solar pv", "pv"} if el.get("solar_pv_only") else True,
        "eligible_category": customer_category.strip().lower() in {x.lower() for x in el.get("eligible_categories", [])},
        "no_electricity_act_offence": not electricity_act_offence,
    }
    return {"eligible": all(checks.values()), "checks": checks, "policy_rules": [cap_rule.id, eligibility.id]}
