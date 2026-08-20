# Core v3 verification record

Date: 2026-08-20

## Evidence hierarchy

Validation evidence is deliberately separated:

1. **Deterministic unit/regression tests** — prove internal software behaviour.
2. **Synthetic 8760/15-minute fixtures** — prove end-to-end time-series plumbing and edge handling.
3. **Public calibrated proxy profiles** — broaden time-series stress testing, but do not represent Brunei customers.
4. **Anonymized Brunei empirical cases** — required to validate real billing/load behaviour.
5. **Authority/lender confirmation** — required for ambiguous utility rules and institutional finance conventions.

No lower layer automatically proves a higher layer.

## Verified public-source inputs

1. DES Tariff A and Tariff B calculation structure.
2. Net-metering eligibility range of 1 kW to 1 MW / 1000 kW.
3. Existing DES-customer and no-arrears requirements.
4. Solar-PV-only eligibility and residential/government/commercial/industrial categories.
5. Net-metering settlement principles: import/export metering, prevailing gazetted tariff, energy-credit carry-forward, maximum 12-month rollover, forfeiture after settlement period, no cash transaction.
6. No Electricity Licence required for qualifying <=1 MW installations under the programme.
7. Environmental attributes retained by the Net-Metering Consumer or Investor / Asset Owner.
8. May 2026 ESCOM outdoor-solar baseline requirements including bypass diodes, grid-following inverter configuration and minimum IP65 outdoor inverter enclosure.
9. PVWatts v8 supports monthly/hourly outputs and returns hourly AC output when `timeframe=hourly`.
10. The current Net-Metering Assessment Form records both installed kWp and kWac and requests load-profile information for systems above 12 kW.

## Deterministic regression references

- Residential Tariff A: 4,520 kWh => BND 380.40.
- Commercial Tariff B: 26,880 kWh at 140 kVA => BND 1,948.80.
- Reverse tariff calculations reproduce those same consumption values.
- Net-metering ledger carries energy credits and produces zero cash payout.
- Interval parser converts 15-minute kW readings to interval kWh and aggregates to hourly energy.
- Duplicate timestamps fail by default unless a resolution policy is explicitly selected.
- Incomplete or irregular interval data requires explicit provisional override before hourly analysis.
- All-equity finance cases return DSCR/LLCR as not applicable rather than failed.
- Debt cases return P50/P90 DSCR, LLCR and DSRA requirement.
- Closed-form one-period finance cases independently verify IRR/NPV/LCOE/DSCR/LLCR arithmetic.
- Bankability results separate economics from readiness.
- PVWatts hourly profiles are checked against monthly and annual totals before acceptance.

## Validation assets

- `docs/DES_DSP_CLARIFICATION_PACK.md`
- `validation/des_tariff_b_scenarios.json`
- `validation/synthetic_profiles.py`
- `validation/finance_reconciliation_case.json`
- `validation/run_finance_reconciliation.py`
- `validation/build_validation_pack.py`
- `docs/EMPIRICAL_DATA_ACQUISITION_PLAN.md`
- `docs/UI_V3_SCHEMA_MAP.md`
- `validation/case_metadata.schema.json`

## Open validation items before institutional reliance

### Net-metering + Tariff B operational billing
The guideline gives the net energy/credit process but does not provide a worked commercial Tariff B net-metering example. Core v3 currently applies Tariff B to net billed kWh after energy-credit netting. Confirm this with DES/DSP before presenting it as the operational billing-system method.

The programme also states a 1 kW–1 MW limit while the assessment form records both kWp and kWac. Confirm the formal capacity basis before automatically rejecting borderline DC/AC designs.

### Tax model
Current tax logic is deliberately simplified and does not model depreciation, capital allowances, loss carry-forward, withholding tax or project-specific incentives. Tax assumptions must remain user/evidence inputs until a validated Brunei project-finance tax module is developed.

### P90
Core v3 accepts a P90/P50 factor. It does not independently derive probability-of-exceedance distributions from multi-year resource uncertainty. Investment-grade P90 should come from a validated resource/energy-yield study or a later uncertainty engine.

### LLCR / DSRA
The formulas are project-finance screening constructs, but lender-specific definitions, reserve funding mechanics and covenants must be independently reconciled and configurable when banks participate.

### Debt service
Core v3 alpha uses level annual debt service. Sculpted debt, construction drawdowns and IDC remain explicitly out of scope.

### Interval data
The parser does not silently synthesize missing meter data. A future repair workflow must require an explicit fill/interpolation method, reason and evidence owner before repaired data is treated as reliable.

### Empirical Brunei load data
Synthetic and public proxy load profiles validate software robustness only. Real anonymized Brunei residential/commercial cases are still required to validate actual customer load shapes, billing and post-solar outcomes.

## Release rule

Do not merge Core v3 into the default production calculation path solely because the unit tests pass. Merge after:
1. CI passes v2, v3 and validation-fixture suites;
2. finance formulas receive independent calculation review;
3. DES/DSP settlement/capacity interpretation is confirmed or explicitly maintained as provisional;
4. existing UI regression checks pass;
5. at least one real anonymized residential, commercial and project-finance case is reconciled against external calculations.

See `docs/CORE_V3_VALIDATION_PLAN.md` for the gate-by-gate process.