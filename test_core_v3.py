import unittest
from datetime import datetime, timedelta
from pathlib import Path

from core_v3 import (
    EvidenceStatus, EvidenceValue, PolicyRegistry, TariffEngine, NetMeteringLedger,
    parse_load_csv, resample_hourly, match_load_and_pv, IntervalPoint,
    ProjectFinanceInputs, model_project_finance, solve_tariff, debt_capacity_for_dscr,
    validate_net_metering_eligibility, PVWattsProfile, analyze_hourly_building,
    assess_bankability, make_audit,
)

ROOT = Path(__file__).resolve().parent
REG = PolicyRegistry.from_path(ROOT / "data" / "policy_registry.json")
TARIFF = TariffEngine(REG)

class EvidencePolicyTests(unittest.TestCase):
    def test_verified_requires_source(self):
        with self.assertRaises(ValueError):
            EvidenceValue(1, status=EvidenceStatus.VERIFIED).validate()
        self.assertEqual(EvidenceValue(1, status=EvidenceStatus.VERIFIED, source="DES").to_dict()["status"], "verified")

    def test_audit_digest_is_deterministic(self):
        a = make_audit(model_version="3", policy_registry_version="x", input_payload={"b": 2, "a": 1}, policy_rule_ids=["DES_TARIFF_A"])
        b = make_audit(model_version="3", policy_registry_version="x", input_payload={"a": 1, "b": 2}, policy_rule_ids=["DES_TARIFF_A"])
        self.assertEqual(a.input_sha256, b.input_sha256)
        self.assertEqual(a.policy_rule_ids, ("DES_TARIFF_A",))

    def test_net_metering_eligibility(self):
        ok = validate_net_metering_eligibility(REG, capacity_kw=1000, is_existing_des_customer=True, has_outstanding_arrears=False, technology="Solar PV", customer_category="commercial")
        self.assertTrue(ok["eligible"])
        too_big = validate_net_metering_eligibility(REG, capacity_kw=1000.1, is_existing_des_customer=True, has_outstanding_arrears=False, technology="Solar PV", customer_category="commercial")
        self.assertFalse(too_big["eligible"])

class TariffTests(unittest.TestCase):
    def test_residential_reference(self):
        self.assertAlmostEqual(TARIFF.residential_bill(4520).amount_bnd, 380.40, places=2)
        self.assertAlmostEqual(TARIFF.residential_consumption_from_bill(380.40), 4520, places=5)

    def test_residential_tier_boundaries(self):
        self.assertAlmostEqual(TARIFF.residential_bill(600).amount_bnd, 6.00, places=2)
        self.assertAlmostEqual(TARIFF.residential_bill(2000).amount_bnd, 118.00, places=2)
        self.assertAlmostEqual(TARIFF.residential_bill(4000).amount_bnd, 318.00, places=2)

    def test_commercial_des_reference(self):
        self.assertAlmostEqual(TARIFF.commercial_bill(26880, 140).amount_bnd, 1948.80, places=2)
        self.assertAlmostEqual(TARIFF.commercial_consumption_from_bill(1948.80, 140), 26880, places=5)

class NetMeteringTests(unittest.TestCase):
    def test_energy_credit_carry_and_bill(self):
        ledger = NetMeteringLedger(TARIFF, "residential")
        jan = ledger.settle(100, 300)
        self.assertEqual(jan.bill_bnd, 0)
        self.assertAlmostEqual(jan.credit_closing_kwh, 200)
        feb = ledger.settle(250, 0)
        self.assertAlmostEqual(feb.credit_used_kwh, 200)
        self.assertAlmostEqual(feb.net_billed_kwh, 50)
        self.assertAlmostEqual(feb.bill_bnd, 0.50)

    def test_credit_can_be_used_during_twelfth_future_period(self):
        ledger = NetMeteringLedger(TARIFF, "residential", rollover_months=12)
        ledger.settle(0, 100)
        for _ in range(11):
            ledger.settle(0, 0)
        self.assertAlmostEqual(ledger.credit_balance_kwh, 100)
        use = ledger.settle(100, 0)
        self.assertAlmostEqual(use.credit_used_kwh, 100)

    def test_unused_credit_is_forfeited_after_rollover_window(self):
        ledger = NetMeteringLedger(TARIFF, "residential", rollover_months=12)
        ledger.settle(0, 100)
        last = None
        for _ in range(12):
            last = ledger.settle(0, 0)
        self.assertAlmostEqual(ledger.credit_balance_kwh, 0)
        self.assertAlmostEqual(last.forfeited_kwh, 100)

class IntervalTests(unittest.TestCase):
    def test_parse_15_min_kw_and_resample(self):
        text = "timestamp,load_kw\n2026-01-01 00:00,4\n2026-01-01 00:15,4\n2026-01-01 00:30,4\n2026-01-01 00:45,4\n2026-01-01 01:00,8\n"
        report = parse_load_csv(text)
        self.assertAlmostEqual(report.inferred_interval_minutes, 15)
        self.assertAlmostEqual(sum(p.kwh for p in report.points), 6.0)
        self.assertAlmostEqual(resample_hourly(report.points)[0].kwh, 4.0)

    def test_duplicate_timestamps_fail_by_default(self):
        text = "timestamp,kwh\n2026-01-01 00:00,1\n2026-01-01 00:00,1\n2026-01-01 01:00,1\n"
        with self.assertRaises(ValueError):
            parse_load_csv(text)
        report = parse_load_csv(text, duplicate_policy="first")
        self.assertEqual(report.duplicate_rows, 1)
        self.assertAlmostEqual(sum(p.kwh for p in report.points), 2.0)

    def test_match_energy_balance(self):
        t = datetime(2026, 1, 1, 12)
        x = match_load_and_pv([IntervalPoint(t, 10)], [IntervalPoint(t, 6)])[0]
        self.assertEqual((x.self_consumed_kwh, x.grid_import_kwh, x.grid_export_kwh), (6, 4, 0))

class FinanceTests(unittest.TestCase):
    def base(self, **kw):
        d = dict(capex_bnd=1_500_000, year1_p50_mwh=1800, p90_factor=.9, ppa_bnd_per_kwh=.10, ppa_years=25, opex_year1_bnd=24000, debt_pct=.65, debt_rate=.055, debt_tenor_years=15, dsra_months=6, target_equity_irr=.12, minimum_p90_dscr=1.25)
        d.update(kw)
        return ProjectFinanceInputs(**d)

    def test_debt_metrics(self):
        r = model_project_finance(self.base())
        self.assertGreater(r.annual_debt_service_bnd, 0)
        self.assertIsNotNone(r.minimum_p90_dscr)
        self.assertIsNotNone(r.llcr_p90)
        self.assertAlmostEqual(r.dsra_requirement_bnd, r.annual_debt_service_bnd / 2, places=6)

    def test_all_equity_dscr_not_applicable(self):
        r = model_project_finance(self.base(debt_pct=0))
        self.assertEqual(r.debt_bnd, 0)
        self.assertIsNone(r.minimum_p90_dscr)
        self.assertIsNone(r.llcr_p90)

    def test_percentage_unit_mistake_is_rejected(self):
        with self.assertRaises(ValueError):
            model_project_finance(self.base(target_equity_irr=12))
        with self.assertRaises(ValueError):
            model_project_finance(self.base(debt_pct=65))

    def test_tariff_solver(self):
        i = self.base(ppa_bnd_per_kwh=.05)
        floor = solve_tariff(i, "p90_dscr")
        self.assertIsNotNone(floor)
        r = model_project_finance(ProjectFinanceInputs(**{**i.__dict__, "ppa_bnd_per_kwh": floor}))
        self.assertGreaterEqual(r.minimum_p90_dscr + 1e-8, i.minimum_p90_dscr)

    def test_dscr_debt_capacity(self):
        i = self.base(debt_pct=.90, minimum_p90_dscr=1.4)
        debt = debt_capacity_for_dscr(i)
        self.assertGreaterEqual(debt, 0)
        self.assertLessEqual(debt, i.capex_bnd * .90)

    def test_economics_and_readiness_are_separate(self):
        i = self.base(ppa_bnd_per_kwh=1.0, debt_pct=0.0)
        weak = {"sponsor":70,"financing":65,"site_land":70,"solar_resource":70,"grid":55,"ppa_offtake":55,"approvals_environmental":60,"execution":65,"risk_allocation":55}
        a = assess_bankability(i, readiness_scores=weak, offtaker_ceiling_bnd_per_kwh=1.0)
        self.assertEqual(a.financial_status, "PASS")
        self.assertIn("READINESS GAPS", a.combined_status)
        strong = {k:100 for k in weak}
        b = assess_bankability(i, readiness_scores=strong, offtaker_ceiling_bnd_per_kwh=1.0)
        self.assertIn("GREEN", b.combined_status)

    def test_partial_readiness_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_bankability(self.base(), readiness_scores={"grid": 80})

class BuildingEngineTests(unittest.TestCase):
    def test_hourly_self_use(self):
        start = datetime(2025, 1, 1)
        hourly, loads = [], []
        for h in range(8760):
            ts = start + timedelta(hours=h)
            pv = 1.0 if ts.hour == 12 else 0.0
            hourly.append(pv)
            loads.append(IntervalPoint(ts, 2.0 if ts.hour == 12 else 0.1))
        profile = PVWattsProfile(4.9, 114.9, 10, 180, 14, sum(hourly), tuple([sum(hourly)/12]*12), tuple(hourly), 10, None, None)
        r = analyze_hourly_building(load_points=loads, pv_profile=profile, capacity_kwp=1, tariff_engine=TARIFF, tariff="residential")
        self.assertGreater(r.self_consumed_kwh, 300)
        self.assertEqual(r.grid_export_kwh, 0)
        self.assertGreater(r.annual_saving_bnd, 0)
        self.assertEqual(len(r.months), 12)

if __name__ == "__main__":
    unittest.main()
