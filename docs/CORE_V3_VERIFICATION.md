# Core v3 verification record

Date: 2026-08-20

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

## Deterministic regression references

- Residential Tariff A: 4,520 kWh => BND 380.40.
- Commercial Tariff B: 26,880 kWh at 140 kVA => BND 1,948.80.
- Reverse tariff calculations reproduce those same consumption values.
- Net-metering ledger carries energy credits and produces zero cash payout.
- Interval parser converts 15-minute kW readings to interval kWh and aggregates to hourly energy.
- All-equity finance cases return DSCR/LLCR as not applicable rather than failed.
- Debt cases return P50/P90 DSCR, LLCR and DSRA requirement.

## Open validation items before institutional reliance

### Net-metering + Tariff B operational billing
The guideline gives the net-charge formula and energy-credit process but does not provide a worked commercial Tariff B net-metering example. Core v3 currently applies Tariff B to net billed kWh after energy-credit netting. Confirm this implementation with DES/DSP before presenting it as the operational billing-system method.

### Tax model
Current tax logic is deliberately simplified and does not model depreciation, capital allowances, loss carry-forward, withholding tax or project-specific incentives. Tax assumptions must remain user/evidence inputs until a validated Brunei project-finance tax module is developed.

### P90
Core v3 accepts a P90/P50 factor. It does not independently derive probability-of-exceedance distributions from multi-year resource uncertainty. Investment-grade P90 should come from a validated resource/energy-yield study or a later uncertainty engine.

### LLCR / DSRA
The formulas are standard project-finance screening constructs but lender-specific definitions, reserve funding mechanics and covenants must be configurable when banks formally participate.

### Debt service
Core v3 alpha uses level annual debt service. Sculpted debt, construction drawdowns and IDC remain explicitly out of scope.

### Interval data
The parser reports missing/duplicate/skipped rows and does not silently synthesize missing meter data. A future data-quality workflow should require an explicit fill/repair method and evidence owner before investment-grade use.

## Release rule

Do not merge Core v3 into the default production calculation path solely because the unit tests pass. Merge after:
1. CI passes both v2 and v3 suites;
2. finance formulas receive independent calculation review;
3. DES/DSP settlement interpretation is confirmed or clearly maintained as provisional;
4. existing UI regression checks pass;
5. at least one real anonymized residential, commercial and project-finance case is reconciled against external calculations.
