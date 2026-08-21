# Core v3 API examples

Core v3 uses explicit units. Percentage-style finance inputs are **decimal fractions** unless the field name explicitly says otherwise.

Examples:
- 65% debt = `0.65`
- 5.5% debt rate = `0.055`
- 12% target equity IRR = `0.12`
- P90/P50 factor of 90% = `0.90`
- DSCR = `1.25` (ratio, not percent)

## Status

`GET /api/v3/status`

## DES tariff

Residential:

```json
{
  "tariff": "residential",
  "consumption_kwh": 4520
}
```

Commercial:

```json
{
  "tariff": "commercial",
  "consumption_kwh": 26880,
  "subscribed_kva": 140
}
```

POST to `/api/v3/tariff/calculate`.

## Net-metering settlement

```json
{
  "tariff": "residential",
  "imports_kwh": [1000, 500, 700],
  "exports_kwh": [1200, 100, 200],
  "rollover_months": 12
}
```

POST to `/api/v3/net-metering/settle`.

For Tariff B, add `subscribed_kva`.

## Interval load parsing

```json
{
  "csv": "timestamp,load_kw\n2026-01-01 00:00,4\n2026-01-01 00:15,5\n...",
  "duplicate_policy": "error"
}
```

POST to `/api/v3/interval/parse`.

Default duplicate policy is `error`. Other policies (`first`, `last`, `average`, `sum`) require an explicit choice because they materially change energy totals.

## Hourly building analysis

```json
{
  "csv": "timestamp,load_kw\n...",
  "capacity_kwp": 50,
  "tariff": "commercial",
  "customer_category": "commercial",
  "subscribed_kva": 140,
  "lat": 4.9031,
  "lon": 114.9398,
  "tilt": 10,
  "azimuth": 180,
  "losses_pct": 14,
  "net_metering": true,
  "is_existing_des_customer": true,
  "has_outstanding_arrears": false,
  "duplicate_policy": "error",
  "minimum_completeness_pct": 95,
  "allow_incomplete": false,
  "allow_irregular_intervals": false
}
```

POST to `/api/v3/building/hourly`.

By default the endpoint refuses:
- unresolved duplicate timestamps;
- completeness below 95%;
- irregular timestamp gaps that are not whole multiples of the inferred meter interval.

Explicit overrides produce a provisional analysis and warnings. They should not be used to disguise poor source data.

## Project finance and bankability

```json
{
  "capex_bnd": 150000000,
  "year1_p50_mwh": 180000,
  "p90_factor": 0.90,
  "ppa_bnd_per_kwh": 0.10,
  "ppa_years": 25,
  "degradation": 0.005,
  "curtailment": 0.02,
  "other_losses": 0.01,
  "opex_year1_bnd": 2400000,
  "opex_escalation": 0.02,
  "tax_rate": 0,
  "discount_rate": 0.08,
  "debt_pct": 0.65,
  "debt_rate": 0.055,
  "debt_tenor_years": 15,
  "dsra_months": 6,
  "target_equity_irr": 0.12,
  "minimum_p90_dscr": 1.25,
  "offtaker_ceiling_bnd_per_kwh": 0.11,
  "readiness_scores": {
    "sponsor": 80,
    "financing": 70,
    "site_land": 75,
    "solar_resource": 85,
    "grid": 65,
    "ppa_offtake": 70,
    "approvals_environmental": 65,
    "execution": 75,
    "risk_allocation": 70
  }
}
```

POST to `/api/v3/finance/project`.

If `readiness_scores` is supplied, every listed readiness dimension is required. Core v3 does not silently fill missing readiness scores.

## Audit metadata

Calculation responses include an `audit` object containing:
- Core v3 model version;
- policy-registry version;
- UTC calculation timestamp;
- SHA-256 digest of the exact input payload;
- policy rule IDs used by the calculation.

The digest provides a reproducibility check. It does not replace retention of the authorized source documents/evidence in the future Project Passport datastore.
