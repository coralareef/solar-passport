# Solar Passport Core v3

Core v3 is the trusted calculation and policy layer for Solar Passport. It is intentionally separated from the existing UI while the calculation interfaces are stabilized and tested.

## Version

`3.0.0-alpha.1`

## Modules

### Policy registry
- Loads versioned Brunei rules from `data/policy_registry.json`.
- Supports source/effective-date snapshots.
- Net-metering eligibility checks use the current 1 kW–1 MW range, DES-customer requirement, arrears requirement, customer category and Solar-PV-only requirement.
- A project should retain the exact registry version used in an assessment.

### Evidence model
Every important project variable can carry:
- Entered / Estimated / Benchmark / Verified status;
- source or source document;
- effective/review dates;
- owner and updater metadata.

A value marked Verified is rejected unless a source is provided.

### DES tariff engine
Implemented from the current published DES tariff structure:
- Tariff A residential progressive kWh tiers;
- Tariff B commercial kVA-linked blocks;
- forward bill calculation and reverse bill-to-consumption calculation.

Regression references:
- 4,520 kWh residential = BND 380.40;
- 26,880 kWh at 140 kVA commercial = BND 1,948.80.

### Net-metering settlement
The engine maintains an energy-credit ledger:
- monthly import and export are netted;
- excess export becomes kWh credit;
- prior credits are used FIFO against future net import;
- credits are retained for up to 12 future billing periods and then forfeited;
- cash payout is always zero;
- resulting net billed electricity is passed through the applicable DES tariff engine.

Source basis: Department of Energy Net-Metering Guideline, Chapter 6. The guideline states that credits use the prevailing gazetted tariff, energy credits roll over for a maximum of 12 months, excess credits are forfeited and no monetary transaction is involved.

**Validation requirement:** before institutional production use, confirm with DES/DSP how the gazetted Tariff B block calculation is applied to net-metering import/export settlement in operational billing. The current software applies the published Tariff B structure to net billed kWh after energy-credit netting; this is a transparent implementation interpretation, not a claimed DES billing-system specification.

### Interval load engine
- CSV parser for timestamp + kWh or timestamp + kW;
- common ISO and day/month/year timestamp formats;
- automatic interval inference;
- 15/30/60-minute and other regular intervals;
- kW-to-kWh conversion using inferred interval duration;
- duplicate/skipped/missing interval reporting;
- hourly resampling;
- hourly load/PV matching into self-consumption, grid import and grid export;
- monthly aggregation.

Incomplete files are not silently filled. The API reports completeness and warns below 95%.

### PVWatts hourly resource engine
- NLR PVWatts v8 endpoint;
- `timeframe=hourly` supported;
- requests one 1-kWp resource profile and scales locally for system size;
- persistent cache under `.cache/`;
- preserves weather-data-source and station-distance metadata;
- API key stays server-side.

### Building hourly engine
For interval-data assessments:
1. Normalize meter data to hourly energy.
2. Map actual meter timestamps to a canonical typical meteorological year by month/day/hour.
3. Scale the cached 1-kWp PVWatts hourly profile to the candidate system size.
4. Calculate hourly self-consumption/import/export.
5. Aggregate monthly.
6. Calculate baseline DES bill.
7. Apply net-metering energy-credit settlement if current eligibility checks pass.
8. Return annual and monthly bill/savings metrics.

Feb-29 is explicitly excluded when matching to a non-leap TMY. If multiple years of load data are supplied, equivalent month/day/hour observations are averaged.

### Project finance engine
Current scope:
- P50/P90 generation;
- annual degradation, curtailment and other losses;
- tariff and tariff escalation;
- OPEX and escalation;
- simplified cash tax on positive EBITDA;
- level annual debt service;
- debt/equity split;
- project IRR and equity IRR;
- project NPV;
- LCOE;
- annual P50 and P90 DSCR;
- minimum P90 DSCR;
- LLCR at financial close using debt-rate discounting over loan life;
- DSRA sizing in months of annual debt service;
- equity-funded DSRA reserve/release treatment;
- DSCR-constrained maximum debt capacity;
- tariff solvers for equity IRR, P90 DSCR and project NPV.

Not yet modeled:
- construction drawdowns;
- interest during construction;
- depreciation/tax shields;
- withholding tax;
- working capital;
- sculpted debt service;
- DSRA interest/LC structures;
- refinancing;
- termination payments;
- detailed deemed-energy/curtailment compensation;
- FX and inflation-indexation regimes.

These boundaries are returned by the v3 finance API and must remain visible until implemented.

## Core v3 API
Run:

```bat
python run_v3.py
```

Endpoints:
- `GET /api/v3/status`
- `GET /api/v3/policy/snapshot`
- `POST /api/v3/tariff/calculate`
- `POST /api/v3/net-metering/settle`
- `POST /api/v3/interval/parse`
- `POST /api/v3/building/hourly`
- `POST /api/v3/finance/project`

The existing UI continues to operate while these endpoints are stabilized.

## Verification sources

Primary public sources used for the current rules:
- Department of Electrical Services, Electricity Tariff: https://www.des.gov.bn/electricity-tariff/
- Department of Energy, Net Metering Programme: https://www.energy.gov.bn/net-metering-programme/
- Department of Energy, Net-Metering Guideline: https://www.energy.gov.bn/wp-content/uploads/2026/02/2025-Net-metering-Guideline-ENG-FINAL-vF-1.pdf
- SHENA / ESCOM, Guidelines and Best Practices for Solar Photovoltaic Design, Installations and Maintenance (Outdoor), May 2026 Rev 1.0.
- NLR Developer Network, PVWatts v8 API documentation: https://developer.nlr.gov/docs/solar/pvwatts/v8/

## Test strategy

`test_core_v3.py` contains deterministic regression tests. CI also reruns the existing `test_model_v2.py` so Core v3 development cannot silently break the current MVP model.

Run locally:

```bat
python -m unittest -v test_core_v3.py
python -m unittest -v test_model_v2.py
```

Core v3 should not be merged into `main` until both suites pass and the API branch receives a calculation review.
