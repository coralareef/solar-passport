# Core v3 external validation plan

Unit tests establish software consistency. They do not establish that every institutional convention or operational utility process has been interpreted correctly. Core v3 therefore requires staged validation before becoming the production calculation authority.

## Validation strategy

Use three distinct layers and never confuse their evidence strength.

### Layer A — deterministic synthetic validation

Purpose: prove software mechanics.

Use generated residential, commercial and large-C&I 8760-hour/15-minute fixtures to test:
- parser reliability;
- energy conservation;
- PV/load matching;
- tariff boundaries;
- net-metering carry/expiry;
- performance;
- regression behaviour.

These profiles are not empirical Brunei data.

### Layer B — public proxy-profile validation

Use calibrated public datasets such as NLR/NREL ResStock/ComStock only to expose Core v3 to more diverse time-series shapes.

Purpose: stress testing and robustness.

These profiles must not be used to claim Brunei customer behaviour, expected self-consumption or savings.

### Layer C — anonymized Brunei empirical validation

This is the release-relevant layer.

Minimum cases:
1. one residential rooftop;
2. one commercial Tariff B rooftop;
3. one larger C&I / utility-project finance case.

Prefer actual interval data and independent model/bill outputs where available.

See `docs/EMPIRICAL_DATA_ACQUISITION_PLAN.md`.

---

## V3-GATE-01 — DES / DSP net-metering settlement confirmation

Question to resolve:
How is the current gazetted tariff applied operationally to monthly import, export, carried-forward energy credit and Tariff B kVA-linked blocks?

Also confirm the formal capacity basis of the 1 kW–1 MW programme limit because the current assessment form records both kWp and kWac.

Validation package now exists at:
- `docs/DES_DSP_CLARIFICATION_PACK.md`
- `validation/des_tariff_b_scenarios.json`

It includes:
- same-month commercial import/export;
- carried credit crossing Tariff B blocks;
- marginal-block changes due to export;
- 12-month expiry timing;
- tariff change while credit remains outstanding;
- 1,080 kWp DC / 900 kWac capacity-limit example.

Acceptable outcome:
Written worked examples or confirmed billing/eligibility logic from the responsible utility/authority sufficient to reproduce the operational result.

Each confirmed scenario becomes a permanent regression test and a versioned policy rule.

---

## V3-GATE-02 — Independent project-finance reconciliation

A standardized synthetic utility-scale case now exists at:

`validation/finance_reconciliation_case.json`

Generate Core v3 reconciliation outputs with:

```bash
python validation/run_finance_reconciliation.py
```

This produces a JSON summary and annual CSV schedule under `validation/generated/finance/`.

Reconcile the same input assumptions independently in a bank/project-finance spreadsheet for:
- P50/P90 generation and CFADS;
- project IRR;
- equity IRR;
- NPV;
- LCOE;
- annual debt service;
- annual and minimum P90 DSCR;
- LLCR at financial close;
- DSRA requirement, funding and release;
- DSCR-constrained debt capacity;
- tariff solving for IRR, DSCR and NPV.

Differences must be explained as convention differences or fixed. Lender-specific conventions should become configurable rather than silently hard-coded.

---

## V3-GATE-03 — Real anonymized project reconciliation

Minimum three cases:
1. Residential rooftop with actual bills.
2. Commercial rooftop with actual monthly kWh, subscribed kVA and bills.
3. Utility/C&I project with independent CAPEX/OPEX/yield/financing assumptions.

For rooftop cases, where possible include interval data and compare:
- source consumption total;
- pre-solar bill;
- modelled PV generation;
- self-consumption;
- import/export;
- post-solar bill;
- annual saving.

Until those cases are available, development continues using deterministic fixtures and public proxy stress tests. Passing synthetic/proxy tests does not close Gate 03.

---

## V3-GATE-04 — PVWatts hourly live-data validation

Using the configured NLR API key:
- retrieve one Brunei hourly profile;
- confirm expected 8760/8784 point count;
- confirm annual total equals sum of hourly kWh within numerical tolerance;
- confirm monthly totals reconcile with hourly aggregation;
- confirm cache retrieval reproduces the live profile exactly;
- record weather-data source and station metadata;
- confirm concurrent requests do not corrupt persistent cache.

Core v3 already rejects an hourly PVWatts profile if its hourly/monthly/annual totals do not reconcile internally.

---

## V3-GATE-05 — UI/API integration

Do not redesign the accepted UI. Replace calculation calls behind the existing interface in controlled increments.

Schema mapping is documented in:

`docs/UI_V3_SCHEMA_MAP.md`

Migration order:
1. test adapters without UI changes;
2. switch DES Tariff A/B calculation to v3;
3. preserve one-value electricity input;
4. add interval upload inside the existing Building panel;
5. switch hourly energy/billing results to v3;
6. expose DSRA/model-boundary fields in the existing Project advanced section;
7. switch Project Bankability only after Gate 02 reconciliation;
8. retain v2 side-by-side until intended differences are understood.

Regression checks:
- existing Building Passport quick flow remains usable;
- one-value tariff input remains functional;
- current map/search workflow remains functional;
- current project inputs map to explicit v3 units;
- no hidden readiness defaults;
- all-equity DSCR displays as not applicable;
- v3 model boundary/audit metadata is visible in methodology/evidence detail;
- response times remain acceptable and hourly arrays are not unnecessarily returned to the browser.

---

## One-command local validation assets

Generate the current synthetic profiles and finance reconciliation pack with:

```bash
python validation/build_validation_pack.py
```

Generated files are intentionally excluded from Git.

---

## Release decision

Core v3 can move from draft to production candidate only when each gate is either:
- PASS; or
- explicitly accepted as a documented provisional limitation by the project owner and relevant stakeholder.

A software test PASS is not equivalent to a regulatory, empirical or lender validation PASS.