# Core v3 external validation plan

Unit tests establish software consistency. They do not establish that every institutional convention or operational utility process has been interpreted correctly. Core v3 therefore requires external reconciliation before becoming the production calculation authority.

## V3-GATE-01 — DES / DSP net-metering settlement confirmation

Question to resolve:
How is the current gazetted tariff applied operationally to monthly import, export, carried-forward energy credit and Tariff B kVA-linked blocks?

Validation package should include:
- one residential worked example across at least three months including carried credit;
- one commercial Tariff B worked example including subscribed kVA;
- treatment of export in the same month as import;
- treatment of prior-month credit;
- 12-month settlement/forfeiture interpretation;
- treatment if tariff changes while credits are outstanding.

Acceptable outcome:
Written worked example or confirmed billing logic from the responsible utility/authority sufficient to reproduce the operational result.

## V3-GATE-02 — Independent project-finance reconciliation

Reconcile Core v3 against an independently prepared spreadsheet/model for at least:
- all-equity project;
- debt-financed project;
- P50/P90 cash flows;
- project IRR;
- equity IRR;
- NPV;
- LCOE;
- annual DSCR;
- minimum P90 DSCR;
- LLCR at financial close;
- DSRA requirement and reserve release;
- DSCR-constrained debt capacity;
- tariff solving for IRR, DSCR and NPV.

Differences must be explained as convention differences or fixed.

## V3-GATE-03 — Real anonymized project reconciliation

Minimum three cases:
1. Residential rooftop with actual bills.
2. Commercial rooftop with actual monthly kWh, subscribed kVA and bills.
3. Utility/C&I project with independent CAPEX/OPEX/yield/financing assumptions.

For rooftop cases, where possible include interval data and compare:
- source consumption total;
- pre-solar bill;
- modeled PV generation;
- self-consumption;
- import/export;
- post-solar bill;
- annual saving.

## V3-GATE-04 — PVWatts hourly live-data validation

Using the configured NLR API key:
- retrieve one Brunei hourly profile;
- confirm expected 8760/8784 point count;
- confirm annual total equals sum of hourly kWh within numerical tolerance;
- confirm monthly totals reconcile with hourly aggregation;
- confirm cache retrieval reproduces the live profile exactly;
- record weather-data source and station metadata.

## V3-GATE-05 — UI/API integration

Do not redesign the accepted UI. Replace calculation calls behind the existing interface in controlled increments.

Regression checks:
- existing Building Passport quick flow remains usable;
- one-value tariff input remains functional;
- current map/search workflow remains functional;
- current project inputs map to explicit v3 units;
- no hidden readiness defaults;
- all-equity DSCR displays as not applicable;
- v3 model boundary/audit metadata is visible in methodology/evidence detail;
- response times remain acceptable and hourly arrays are not unnecessarily returned to the browser.

## Release decision

Core v3 can move from draft to production candidate only when each gate is either:
- PASS; or
- explicitly accepted as a documented provisional limitation by the project owner and relevant stakeholder.
