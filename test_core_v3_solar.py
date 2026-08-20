import calendar
import time
import unittest

from core_v3 import PVWattsClient


class PVWattsConsistencyTests(unittest.TestCase):
    def test_hourly_profile_reconciles_to_monthly_and_annual(self):
        hourly = tuple([1.0] * 8760)
        monthly = tuple(calendar.monthrange(2025, month)[1] * 24 for month in range(1, 13))
        annual_error, monthly_error = PVWattsClient._reconcile_hourly(hourly, monthly, 8760.0)
        self.assertAlmostEqual(annual_error, 0.0, places=12)
        self.assertAlmostEqual(monthly_error, 0.0, places=12)

    def test_reconciliation_detects_unit_mismatch(self):
        hourly = tuple([1.0] * 8760)
        monthly = tuple(calendar.monthrange(2025, month)[1] * 24 for month in range(1, 13))
        annual_error, _ = PVWattsClient._reconcile_hourly(hourly, monthly, 8_760_000.0)
        self.assertGreater(annual_error, 99.0)

    def test_expired_cache_entry_is_not_valid(self):
        client = PVWattsClient(api_key="test", cache_max_age_days=1)
        self.assertTrue(client._cache_entry_valid({"cached_at_epoch": time.time()}))
        self.assertFalse(client._cache_entry_valid({"cached_at_epoch": time.time() - 2 * 86400}))


if __name__ == "__main__":
    unittest.main()
