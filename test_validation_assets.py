import json
import unittest
from pathlib import Path

from core_v3 import PolicyRegistry, TariffEngine
from validation.synthetic_profiles import generate_hourly, generate_15min
from validation.run_finance_reconciliation import build_report, load_case

ROOT = Path(__file__).resolve().parent
REG = PolicyRegistry.from_path(ROOT / "data" / "policy_registry.json")
TARIFF = TariffEngine(REG)


class SyntheticProfileTests(unittest.TestCase):
    def test_hourly_profiles_are_8760_and_scaled(self):
        expected = {"residential": 9600, "commercial": 120000, "large_ci": 1200000}
        for name, annual in expected.items():
            points = generate_hourly(name, year=2025)
            self.assertEqual(len(points), 8760)
            self.assertAlmostEqual(sum(kwh for _, kwh in points), annual, places=5)
            self.assertTrue(all(kwh >= 0 for _, kwh in points))

    def test_15min_profile_preserves_energy(self):
        hourly = generate_hourly("commercial", year=2025)
        qh = generate_15min("commercial", year=2025)
        self.assertEqual(len(qh), 35040)
        self.assertAlmostEqual(sum(x[1] for x in hourly), sum(x[1] for x in qh), places=5)


class DESClarificationFixtureTests(unittest.TestCase):
    def test_machine_readable_scenarios_match_current_tariff_math(self):
        payload = json.loads((ROOT / "validation" / "des_tariff_b_scenarios.json").read_text(encoding="utf-8"))
        kva = payload["subscribed_kva"]
        scenarios = {x["id"]: x for x in payload["scenarios"]}
        self.assertAlmostEqual(TARIFF.commercial_bill(15000, kva).amount_bnd, scenarios["B1_same_month_netting"]["core_v3_assumption"]["bill_bnd"], places=2)
        self.assertAlmostEqual(TARIFF.commercial_bill(13000, kva).amount_bnd, scenarios["B2_carried_credit"]["core_v3_assumption"]["month_2_bill_bnd"], places=2)
        self.assertAlmostEqual(TARIFF.commercial_bill(28000, kva).amount_bnd, scenarios["B3_block_crossing"]["core_v3_assumption"]["bill_bnd"], places=2)
        self.assertAlmostEqual(TARIFF.commercial_bill(35000, kva).amount_bnd, scenarios["B3_block_crossing"]["gross_import_bill_before_export_bnd"], places=2)


class FinanceReconciliationFixtureTests(unittest.TestCase):
    def test_standard_case_remains_reproducible(self):
        case = load_case()
        report = build_report(case)
        expected = case["baseline_core_v3_outputs_for_comparison"]
        s = report["summary"]
        self.assertAlmostEqual(s["annual_debt_service_bnd"], expected["annual_debt_service_bnd_approx"], places=1)
        self.assertAlmostEqual(s["dsra_requirement_bnd"], expected["dsra_requirement_bnd_approx"], places=1)
        self.assertAlmostEqual(s["equity_bnd"], expected["equity_funding_at_close_bnd_approx"], places=1)
        self.assertAlmostEqual(s["project_irr_pct"], expected["project_irr_pct_approx"], places=3)
        self.assertAlmostEqual(s["equity_irr_pct"], expected["equity_irr_pct_approx"], places=3)
        self.assertAlmostEqual(s["project_npv_bnd"], expected["project_npv_bnd_approx"], places=1)
        self.assertAlmostEqual(s["lcoe_bnd_per_kwh"], expected["lcoe_bnd_per_kwh_approx"], places=5)
        self.assertAlmostEqual(s["minimum_p90_dscr"], expected["minimum_p90_dscr_approx"], places=4)
        self.assertAlmostEqual(s["llcr_p50"], expected["llcr_p50_approx"], places=4)
        self.assertAlmostEqual(s["llcr_p90"], expected["llcr_p90_approx"], places=4)
        self.assertEqual(len(report["annual_schedule"]), 25)


if __name__ == "__main__":
    unittest.main()
