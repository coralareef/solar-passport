# Solar Passport — Existing UI to Core v3 Schema Map

Objective: preserve the accepted user interface while replacing the calculation path underneath it in controlled stages.

## Design rule

The frontend should not know financial formulas or tariff formulas. It should collect user-facing values, label their evidence quality, and send normalized data to an adapter/service layer.

Core v3 uses decimal ratios internally (`0.12` = 12%). The current UI generally uses human percentages (`12` = 12%). Every percentage conversion must therefore be explicit and tested.

---

# 1. Building Passport

## Two analysis grades

The existing Building Passport should support two grades without redesigning the main experience.

### Quick Screening

Inputs available to normal customer:
- building type;
- one electricity value: monthly kWh **or** monthly bill;
- customer tariff category;
- subscribed kVA if commercial;
- roof area / polygon;
- location;
- payment preference.

Output label:
**Screening / Estimated load profile**

The quick path may use monthly consumption and a transparent building-type load-shape assumption. The assumption must be recorded as `Estimated`, never hidden as measured data.

### Verified Interval Analysis

Additional input:
- 15/30/60-minute or hourly CSV.

Output label:
**Interval-data analysis**

This uses the Core v3 hourly Building Engine and should be the preferred basis for investment-grade customer savings analysis.

## Current UI → normalized building fields

| Current UI | Normalized v3 meaning | Transformation / rule |
|---|---|---|
| `site_name` | project/site display name | pass through; not part of financial mathematics |
| `building_type` | load-profile archetype / metadata | pass through; only used for quick estimated profile |
| electricity input mode | known energy or bill | if bill is supplied, reverse-calculate kWh through the selected DES tariff |
| `monthly_kwh` | monthly/annual source load | convert to 12-month series only for quick screening; mark Estimated if extrapolated |
| `monthly_bill` | bill evidence | reverse through Tariff A/B, never `bill ÷ kWh` for current DES tariffs |
| `customer_tariff_choice=residential` | `tariff=residential` | DES Tariff A |
| `customer_tariff_choice=business` | `tariff=commercial` | require `subscribed_kva` for DES Tariff B |
| subscribed kVA field | `subscribed_kva` | required for commercial Tariff B |
| `roof_area_m2` | physical screening constraint | use for capacity screening; does not alter PVWatts resource |
| map polygon | roof geometry + area | retain polygon as evidence, send calculated area to sizing service |
| `lat`, `lon` | PVWatts location | pass through |
| `tilt` | PVWatts tilt degrees | pass through |
| `azimuth` | PVWatts azimuth degrees | pass through |
| `losses` | PVWatts losses percent | rename API field to `losses_pct`; numeric value remains human percent for PVWatts client |
| `usable_roof_pct` | sizing constraint | UI percent → decimal where sizing engine expects ratio |
| `area_per_kwp` | sizing constraint | pass through |
| interval CSV | `csv` in `/api/v3/building/hourly` | parser validates timestamp/value columns and completeness |
| net-metering toggle | `net_metering` | eligibility engine decides whether it may be applied |

## Cost/finance fields

The current Building Passport cost/financing model is not yet the same as the Core v3 project-finance engine. Do not silently map it into utility-scale project finance.

For rooftop v3, create a dedicated lifecycle-finance adapter that preserves:
- CAPEX/kWp;
- O&M;
- degradation;
- inverter replacement;
- cash purchase;
- financing term/rate/down-payment;
- project IRR/NPV/payback;
- first-year monthly cash impact.

Until that adapter is implemented, the v2 rooftop financing output should remain clearly versioned separately from the v3 hourly energy/billing result.

---

# 2. Project Bankability Passport

The Project UI maps cleanly to Core v3, but unit conversion is mandatory.

| Current UI field | Core v3 field | Transformation |
|---|---|---|
| `mwp` | context + `year1_p50_mwh` | `mwp × p50_specific_yield` |
| `mwac` | context | also used to convert per-MW CAPEX/OPEX to totals |
| `p50_specific_yield` | `year1_p50_mwh` | multiply by MWp |
| `p90_factor_pct` | `p90_factor` | divide by 100 |
| `degradation_pct` | `degradation` | divide by 100 |
| `curtailment_pct` | `curtailment` | divide by 100 |
| `other_losses_pct` | `other_losses` | divide by 100 |
| `capex_per_mw` | `capex_bnd` | multiply by MWac |
| `opex_per_mw_year` | `opex_year1_bnd` | multiply by MWac |
| `opex_escalation_pct` | `opex_escalation` | divide by 100 |
| `debt_pct` | `debt_pct` | divide by 100 |
| `debt_rate_pct` | `debt_rate` | divide by 100 |
| `debt_tenor_years` | same | integer pass-through |
| `target_equity_irr_pct` | `target_equity_irr` | divide by 100 |
| `min_dscr` | `minimum_p90_dscr` | pass through ratio, e.g. 1.25 |
| `ppa_tariff` | `ppa_bnd_per_kwh` | pass through |
| `ppa_years` | `ppa_years` | integer pass-through |
| `tariff_escalation_pct` | `tariff_escalation` | divide by 100 |
| `offtaker_ceiling` | bankability assessment argument | pass through BND/kWh |
| `discount_rate_pct` | `discount_rate` | divide by 100 |
| `tax_rate_pct` | `tax_rate` | divide by 100 |

## New v3 finance fields the UI must expose before production switch

Core v3 currently includes assumptions that the old UI does not fully expose. To avoid hidden lender assumptions, add them inside the existing **Financing / Advanced** section rather than redesigning the page:

- `dsra_months` — e.g. 6 months;
- `dsra_funded_by_equity` — yes/no;
- clear note that current debt service is level annual debt service;
- model-boundary note for IDC/construction drawdown/sculpted debt/depreciation until those modules exist.

Values may be pre-filled as **Benchmark**, but cannot be represented as Verified unless sourced from a lender/term sheet.

---

# 3. Readiness mapping

Core v3 readiness keys are:

```text
sponsor
financing
site_land
solar_resource
grid
ppa_offtake
approvals_environmental
execution
risk_allocation
```

The frontend must either submit all nine or omit readiness entirely.

No backend defaults should create an apparently precise readiness score.

Suggested current-UI mapping:

| UI concept | v3 key |
|---|---|
| Sponsor capability | `sponsor` |
| Financing readiness | `financing` |
| Site / land | `site_land` |
| Solar resource evidence | `solar_resource` |
| Grid readiness | `grid` |
| PPA / offtake | `ppa_offtake` |
| Approvals / environmental | `approvals_environmental` |
| Execution | `execution` |
| Risk allocation | `risk_allocation` |

Display economics and readiness separately.

Examples:
- `PASS + GREEN` → `GREEN — ECONOMICS PASS & READY`
- `PASS + AMBER` → `AMBER — ECONOMICS PASS, READINESS GAPS`
- economics fail → `RED — ECONOMICS FAIL`
- developer floor above offtaker ceiling → `AMBER — OFFTAKER / TARIFF GAP`
- no readiness data → `ECONOMICS PASS — READINESS NOT ASSESSED`

---

# 4. Proposed adapter endpoints

Do not make the browser assemble institutional calculations.

Recommended service endpoints:

```text
POST /api/v3/building/quick
POST /api/v3/building/hourly
POST /api/v3/project/assess
POST /api/v3/tariff/calculate
GET  /api/v3/policy/snapshot
```

### `/api/v3/building/quick`

Purpose: preserve the simple current UI when interval data is unavailable.

Responsibilities:
- derive kWh from one bill input if necessary;
- apply correct tariff logic;
- generate a clearly Estimated load shape from building type/operating information;
- use cached PVWatts resource;
- size candidate systems;
- return confidence/evidence status.

### `/api/v3/building/hourly`

Already exists in alpha form.

Purpose:
- parse measured interval data;
- reject poor/duplicate data unless explicitly overridden;
- match hourly PV and load;
- settle DES/net-metering bills;
- return audit metadata.

### `/api/v3/project/assess`

Replace the old `/api/project/calculate` after Gate 02 validation.

Responsibilities:
- normalize plant and finance inputs;
- model finance;
- compute tariff floors;
- assess economics separately from readiness;
- return audit/model-boundary metadata.

---

# 5. Migration order

1. Add adapter tests without changing UI.
2. Switch DES Tariff A/B quick calculations to v3.
3. Add interval-upload control in the existing Building panel.
4. Switch hourly energy/billing results to v3.
5. Add DSRA fields and switch Project calculations to v3 after finance reconciliation.
6. Remove v2 calculations only after side-by-side regression shows intended differences.

For an interim period, responses should include:

```json
{
  "calculation_engine": "core-v3",
  "model_version": "...",
  "policy_registry_version": "...",
  "analysis_grade": "screening|interval",
  "input_sha256": "..."
}
```

This allows frontend and exported reports to identify exactly which engine produced each answer.