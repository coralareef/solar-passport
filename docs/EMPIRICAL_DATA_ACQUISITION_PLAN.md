# Solar Passport Core v3 — Empirical Data Acquisition Plan

## Why synthetic data is not enough

Core v3 can be stress-tested with deterministic 8760-hour profiles and public proxy datasets, but those do not establish that Brunei customer load shapes, billing practice or project-finance conventions have been represented correctly.

The empirical validation objective is therefore modest and achievable: obtain a small number of anonymized Brunei cases with enough source evidence to reconcile the platform end-to-end.

## Three validation layers

### Layer A — deterministic synthetic fixtures

Use `validation/synthetic_profiles.py` to generate residential, commercial and large-C&I time series.

Purpose:
- parser reliability;
- 8760/15-minute performance;
- energy-balance conservation;
- PV/load matching;
- tariff edge cases;
- net-metering credit mechanics;
- regression testing.

Status: **software validation only**. Never label these as measured or representative Brunei load profiles.

### Layer B — public calibrated proxy profiles

Public sources such as NLR/NREL ResStock and ComStock provide 15-minute simulated load profiles calibrated against large empirical datasets. These can be used to expose Core v3 to more diverse realistic-looking load shapes.

Purpose:
- stress test profile diversity;
- test unusual daily/weekly patterns;
- verify scaling and parser robustness.

Status: **proxy validation only**. They are U.S.-stock models and must not be used to claim Brunei customer behaviour or expected savings.

### Layer C — anonymized Brunei empirical cases

This is the release-relevant layer.

Minimum target:
1. one residential customer;
2. one commercial Tariff B customer;
3. one larger C&I/project-finance case.

A stronger pilot would target 5–10 cases in each rooftop category before any population-level performance claims are made.

---

## Case R1 — residential rooftop

Minimum evidence:
- 12 monthly electricity bills if available; minimum 3 recent bills for initial reconciliation;
- monthly kWh and BND charge;
- tariff category;
- approximate district/location for PV resource matching;
- roof size or existing/proposed PV capacity if available.

Preferred evidence:
- smart-meter interval export at 15/30/60-minute resolution;
- actual installed PV generation if the home already has solar.

Anonymize/remove before sharing:
- customer name;
- NRIC/passport;
- electricity account number;
- exact house number if not required;
- phone/email.

Keep:
- timestamps;
- kWh;
- tariff category;
- district or approximate coordinates;
- system capacity if applicable.

## Case C1 — commercial Tariff B rooftop

Minimum evidence:
- 12 monthly kWh values;
- 12 corresponding DES charges;
- subscribed capacity (kVA) for each relevant period;
- tariff category;
- approximate location;
- operating type/hours.

Preferred evidence:
- 15/30/60-minute load file;
- peak demand data;
- an actual or proposed installer quotation;
- PV layout/system size;
- existing net-metering statement if available.

This is the most important tariff-validation case because the kVA-linked blocks must reconcile exactly to the DES bill before post-solar modelling is trusted.

## Case I1 — larger C&I / project-finance case

Minimum evidence:
- CAPEX basis and inclusions/exclusions;
- OPEX assumptions;
- P50 and P90 generation or sufficient resource/design data;
- PPA/offtake tariff or avoided-cost assumption;
- debt/equity assumptions;
- debt rate/profit rate;
- tenor;
- required DSCR/LLCR/DSRA convention if known;
- independent model outputs for reconciliation.

Preferred evidence:
- lender or adviser model with formulas visible;
- term sheet;
- annual project cash flow;
- debt schedule;
- construction drawdown/IDC assumptions.

Commercially sensitive values can be normalized/scaled for validation as long as the transformation is documented and preserves the mathematical relationships being tested.

---

## Where to obtain pilot data

### 1. Solar contractors

The Department of Energy publishes a registered Solar PV contractor list. Contractors are a natural pilot partner because they already collect customer bills and prepare net-metering submissions.

Request:
- one completed anonymized residential case;
- one completed anonymized commercial case;
- permission to compare Solar Passport outputs to the contractor's calculations.

Value to contractor:
- faster lead qualification;
- standardized quote comparison;
- reusable application data;
- fewer manual calculations.

### 2. Volunteer customers / own network

Recruit customers willing to provide bills and, where available, smart-meter data. Begin with people who already understand the objective and can consent to anonymized use.

Do not require exact address for calculation validation. District/approximate coordinates are generally sufficient for the PV-resource test.

### 3. DES / Department of Energy pilot support

For utility validation, ask for **worked anonymized examples**, not bulk customer data initially.

Request:
- a residential net-metering billing example;
- a commercial Tariff B net-metering billing example;
- clarification of interval data export availability/process where applicable;
- confirmation of the authoritative bill-calculation sequence.

This reduces privacy/governance barriers substantially.

### 4. Local banks / project developers

For project-finance validation, ask a participating institution to run the standardized test case in its own model or provide an anonymized existing model with agreed inputs.

The first objective is formula reconciliation, not customer credit data.

---

## Data-sharing principle

Core v3 should initially follow **minimum necessary data**:

- use anonymized data for model validation;
- keep personally identifiable fields outside the calculation dataset;
- assign a case ID such as `R1-2026-001`;
- retain source evidence separately from derived model outputs;
- record consent/purpose and access restrictions;
- never commit real customer datasets to the public/source-code repository.

Future production hosting will require a formal privacy, retention, authorization and cybersecurity design before storing customer meter/billing records centrally.

---

## Standard customer data package

A pilot folder should look like:

```text
R1-2026-001/
  case_metadata.json
  monthly_bills.csv
  interval_load.csv          # optional
  pv_actual.csv              # optional
  source_evidence/           # restricted, not Git
  reconciliation_notes.md
```

### `case_metadata.json` minimum fields

```json
{
  "case_id": "R1-2026-001",
  "category": "residential",
  "district": "Brunei-Muara",
  "tariff": "DES Tariff A",
  "subscribed_kva": null,
  "interval_minutes": 30,
  "data_period_start": "2025-01-01",
  "data_period_end": "2025-12-31",
  "evidence_status": "verified_source_data",
  "consent_for_model_validation": true
}
```

### `monthly_bills.csv`

```text
month,consumption_kwh,bill_bnd,subscribed_kva
2025-01,850,26.00,
...
```

### `interval_load.csv`

```text
timestamp,load_kwh
2025-01-01 00:00:00,0.22
2025-01-01 00:30:00,0.18
...
```

---

## Acceptance criteria for an empirical case

A case is useful only if Solar Passport can report:

1. source-data completeness;
2. pre-solar annual/monthly kWh;
3. pre-solar bills that reconcile to source bills;
4. PV resource source/version;
5. hourly self-consumption/import/export if interval data exists;
6. net-metering credit movement;
7. post-solar bill;
8. difference from independent/reference calculation;
9. explanation for every material difference;
10. audit metadata showing model and policy version.

## What to do while real data is being sourced

Do not block development.

Proceed with:
- deterministic synthetic profiles;
- public proxy-profile stress tests;
- DES/DSP worked clarification scenarios;
- finance reconciliation pack;
- frontend/schema mapping;
- automated validation reports.

Then replace the synthetic/proxy fixtures one-by-one with anonymized Brunei cases as they become available.