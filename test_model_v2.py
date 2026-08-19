import unittest

import model_v2 as m


class SolarPassportModelTests(unittest.TestCase):
    def setUp(self):
        def fake_generation(lat, lon, capacity_kwp, tilt, azimuth, losses, specific_yield):
            annual = capacity_kwp * 1500.0
            return {
                "monthly_kwh": [annual / 12.0] * 12,
                "annual_kwh": annual,
                "capacity_factor": annual / (capacity_kwp * 8760) * 100 if capacity_kwp else 0,
                "source": "NREL PVWatts v8",
                "source_confidence": "Medium-High",
                "cache_status": "test",
            }
        m.configure_generation(fake_generation)

    def test_residential_tariff_reference(self):
        self.assertAlmostEqual(m.tariff_a_cost(4520), 380.40, places=2)
        self.assertAlmostEqual(m.usage_from_tariff_a_bill(380.40), 4520, places=2)

    def test_commercial_tariff_des_example(self):
        self.assertAlmostEqual(m.tariff_b_cost(26880, 140), 1948.80, places=2)
        self.assertAlmostEqual(m.usage_from_tariff_b_bill(1948.80, 140), 26880, places=2)

    def test_commercial_requires_kva(self):
        with self.assertRaises(ValueError):
            m.tariff_b_cost(1000, 0)

    def test_high_tariff_all_equity_passes_economics_but_not_readiness(self):
        payload = {
            "mwp": 120, "mwac": 100, "p50_specific_yield": 1500, "p90_factor_pct": 95,
            "degradation_pct": 0.45, "curtailment_pct": 2, "other_losses_pct": 1,
            "ppa_years": 25, "capex_per_mw": 1500000, "opex_per_mw_year": 24000,
            "opex_escalation_pct": 2, "debt_pct": 0, "debt_rate_pct": "", "debt_tenor_years": "",
            "discount_rate_pct": 8, "tariff_escalation_pct": 0, "ppa_tariff": 1.0,
            "offtaker_ceiling": 1.0, "target_equity_irr_pct": 12, "min_dscr": 1.25,
            "grid_score": 55, "ppa_score": 55, "site_score": 70, "sponsor_score": 70,
            "approvals_score": 60, "execution_score": 65, "risk_allocation_score": 55,
            "financing_score": 65, "resource_score": 70,
        }
        result = m.api_project(payload)
        self.assertTrue(result["economics"]["pass"])
        self.assertFalse(result["economics"]["dscr_applicable"])
        self.assertIn("READINESS GAPS", result["overall_status"])

    def test_project_can_be_green_when_economics_and_readiness_pass(self):
        payload = {
            "mwp": 120, "mwac": 100, "p50_specific_yield": 1500, "p90_factor_pct": 95,
            "degradation_pct": 0.45, "curtailment_pct": 2, "other_losses_pct": 1,
            "ppa_years": 25, "capex_per_mw": 1500000, "opex_per_mw_year": 24000,
            "opex_escalation_pct": 2, "debt_pct": 65, "debt_rate_pct": 5.5, "debt_tenor_years": 15,
            "discount_rate_pct": 8, "tariff_escalation_pct": 0, "ppa_tariff": 0.12,
            "offtaker_ceiling": 0.13, "target_equity_irr_pct": 12, "min_dscr": 1.25,
            "grid_score": 100, "ppa_score": 100, "site_score": 100, "sponsor_score": 100,
            "approvals_score": 100, "execution_score": 100, "risk_allocation_score": 100,
            "financing_score": 100, "resource_score": 100,
        }
        result = m.api_project(payload)
        self.assertTrue(result["economics"]["pass"])
        self.assertEqual(result["readiness"]["score"], 100)
        self.assertTrue(result["overall_status"].startswith("GREEN"))


if __name__ == "__main__":
    unittest.main()
