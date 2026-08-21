from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .tariffs import TariffEngine

@dataclass
class CreditBatch:
    kwh: float
    age_months: int = 0

@dataclass(frozen=True)
class SettlementMonth:
    month_index: int
    import_kwh: float
    export_kwh: float
    credit_opening_kwh: float
    credit_used_kwh: float
    new_credit_kwh: float
    forfeited_kwh: float
    credit_closing_kwh: float
    net_billed_kwh: float
    bill_bnd: float

class NetMeteringLedger:
    """Energy-credit ledger for the current Brunei Net-Metering Programme.

    Credits are retained as kWh, not cash. Prior credits are applied to net
    imported energy on a FIFO basis. A credit can be used for up to 12 future
    billing periods and is then forfeited. The resulting net billed kWh is
    passed to the prevailing DES tariff engine.
    """
    def __init__(self, tariff_engine: TariffEngine, tariff: str, *, subscribed_kva: Optional[float] = None, rollover_months: int = 12):
        if rollover_months < 1:
            raise ValueError("rollover_months must be at least 1")
        self.tariff_engine = tariff_engine
        self.tariff = tariff
        self.subscribed_kva = subscribed_kva
        self.rollover_months = rollover_months
        self._credits: list[CreditBatch] = []
        self._month = 0

    @property
    def credit_balance_kwh(self) -> float:
        return sum(x.kwh for x in self._credits)

    def _consume_credits(self, needed_kwh: float) -> float:
        needed = max(0.0, needed_kwh)
        used = 0.0
        while needed > 1e-12 and self._credits:
            batch = self._credits[0]
            take = min(needed, batch.kwh)
            batch.kwh -= take
            needed -= take
            used += take
            if batch.kwh <= 1e-12:
                self._credits.pop(0)
        return used

    def settle(self, import_kwh: float, export_kwh: float) -> SettlementMonth:
        self._month += 1
        import_kwh = max(0.0, float(import_kwh))
        export_kwh = max(0.0, float(export_kwh))
        opening = self.credit_balance_kwh
        forfeited = 0.0
        period_net = import_kwh - export_kwh
        used = 0.0
        new_credit = 0.0
        if period_net >= 0:
            used = self._consume_credits(period_net)
            net_billed = max(0.0, period_net - used)
        else:
            net_billed = 0.0
            new_credit = -period_net
            self._credits.append(CreditBatch(new_credit, age_months=0))

        new_batch = self._credits[-1] if new_credit > 0 and self._credits else None
        kept = []
        for batch in self._credits:
            if batch is new_batch:
                kept.append(batch)
                continue
            batch.age_months += 1
            if batch.age_months >= self.rollover_months:
                forfeited += batch.kwh
            else:
                kept.append(batch)
        self._credits = kept
        bill = self.tariff_engine.bill(self.tariff, net_billed, self.subscribed_kva).amount_bnd
        return SettlementMonth(self._month, import_kwh, export_kwh, opening, used, new_credit, forfeited, self.credit_balance_kwh, net_billed, bill)

def settle_series(tariff_engine: TariffEngine, tariff: str, imports_kwh: list[float], exports_kwh: list[float], *, subscribed_kva: Optional[float] = None, rollover_months: int = 12) -> list[SettlementMonth]:
    if len(imports_kwh) != len(exports_kwh):
        raise ValueError("imports_kwh and exports_kwh must have equal length")
    ledger = NetMeteringLedger(tariff_engine, tariff, subscribed_kva=subscribed_kva, rollover_months=rollover_months)
    return [ledger.settle(i, e) for i, e in zip(imports_kwh, exports_kwh)]
