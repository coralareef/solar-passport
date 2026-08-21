# Solar Passport Core v3 — Real-Case Validation Pilot Playbook

## Objective

Obtain a small number of consented, anonymized Brunei cases that can independently validate the parts of Core v3 that synthetic tests cannot prove: actual DES billing, actual customer load shape, installer assumptions, and project-finance conventions.

This is a **model-validation pilot**, not a commercial customer-data collection programme and not a regulatory submission platform.

## Recommended pilot cohort

Start small and deliberately diverse.

### Cohort A — rooftop installer partners

Target **3 registered Solar PV installers/contractors**:

1. one company focused on small-scale rooftop residential/commercial work;
2. one company with larger commercial/industrial or ground-mounted experience;
3. one additional contractor to provide an independent comparison of assumptions and workflow pain points.

Ask each contractor for:
- one anonymized residential case if available;
- one anonymized commercial Tariff B case if available;
- the contractor's original calculation/quotation assumptions;
- the net-metering application/assessment data fields used, with identifiers removed;
- feedback on what they currently calculate manually and where errors/delay most often occur.

Do not require a customer's identity or exact address.

### Cohort B — direct customer cases

Target:
- **2 residential customers**;
- **2 commercial customers**.

These can be existing solar customers, customers currently considering solar, or non-solar customers willing to let Solar Passport model a hypothetical system.

Residential minimum:
- 3–12 months of DES bills;
- monthly kWh and bill amount;
- approximate district/location;
- PV capacity / quotation if available.

Commercial minimum:
- 3–12 months of DES bills;
- monthly kWh;
- subscribed capacity in kVA for the same period;
- bill amount;
- approximate district/location;
- operating type/hours;
- PV quotation/system size if available.

Interval data is preferred but is not required to begin tariff reconciliation.

### Cohort C — authority clarification

Engage the Department of Energy / relevant DES-DSP billing representatives with the prepared scenario pack.

Do **not** initially ask for bulk customer meter data.

Ask for:
- confirmation of the commercial Tariff B net-metering calculation sequence;
- one worked residential net-metering billing example;
- one worked commercial Tariff B net-metering billing example;
- confirmation of the 1 kW–1 MW capacity basis (DC kWp, AC kW, or another defined measure);
- clarification on treatment of carried credits if the gazetted tariff changes.

Use `docs/DES_DSP_CLARIFICATION_PACK.md` as the meeting/email attachment basis.

### Cohort D — finance reviewer

Target **one project-finance reviewer first**, then ideally a second independent reviewer.

Possible reviewer types:
- local bank project/corporate finance team;
- infrastructure finance adviser;
- solar project developer with a detailed financial model;
- accountant/financial modeller familiar with project finance.

Give them the standardized synthetic case in `validation/finance_reconciliation_case.json` rather than asking for customer-credit data.

Ask them to reproduce or review:
- P50/P90 CFADS;
- project IRR;
- equity IRR;
- NPV;
- LCOE;
- level debt service;
- P90 DSCR;
- LLCR;
- DSRA sizing/funding/release;
- tariff required for target equity IRR and minimum DSCR.

The first objective is convention reconciliation, not a lending decision.

---

## Suggested contractor selection method

Use the Department of Energy's latest registered Solar PV contractor list as the source population. Prioritize contractors whose current official listing shows active small-scale rooftop capability and, for one pilot partner, large-scale capability.

Selection criteria:
- registered/currently verified status where available;
- installation type relevant to the pilot;
- willingness to provide anonymized historic cases;
- ability to explain their calculation assumptions;
- diversity of project type rather than choosing three nearly identical installers.

Do not describe participation as Government endorsement of Solar Passport.

---

## What exactly to ask a contractor for

A useful request is small enough that they can respond without a data project.

### Residential case package

1. anonymized monthly bill table:
   - month;
   - kWh;
   - BND bill.
2. proposed/installed PV capacity in kWp and kWac if known;
3. panel/inverter specification or quotation summary;
4. approximate district or coordinates rounded sufficiently to avoid identifying the house;
5. contractor's expected annual generation and annual savings;
6. actual generation/savings if the system has already operated for at least several months;
7. interval load CSV if available.

### Commercial case package

1. anonymized monthly bill table:
   - month;
   - kWh;
   - BND bill;
   - subscribed kVA.
2. business/building type and operating hours;
3. proposed/installed kWp and kWac;
4. contractor's annual generation and savings calculation;
5. quotation assumptions, including CAPEX and O&M if available;
6. approximate site location;
7. interval load CSV if available;
8. net-metering application/assessment outputs with names/account numbers removed if available.

---

## Data minimization / anonymization rules

Before a case enters the validation dataset, remove or replace:

- customer/company name when not needed;
- NRIC/passport numbers;
- DES account number;
- meter serial number where identifying;
- personal email/phone;
- exact residential address;
- bank-account or payment information;
- signatures.

Retain only what is necessary for calculation validation:

- timestamps;
- kWh/kW;
- bill amounts;
- subscribed kVA;
- tariff category;
- approximate location/district;
- PV design assumptions;
- finance assumptions relevant to the model.

Assign an internal case ID such as:

- `R-BN-001` residential;
- `C-BN-001` commercial;
- `F-BN-001` project-finance.

Do not commit real customer data to GitHub. Store it outside the source-code repository in an access-controlled pilot folder.

---

## Consent / purpose statement

Before accepting a case, record a simple written confirmation that:

- the data provider is authorized to share the anonymized data for model-validation purposes;
- Solar Passport will use the data to test and improve calculation accuracy;
- the case will not be publicly disclosed in identifiable form;
- results are experimental and do not constitute regulatory approval, engineering certification, or financing approval.

For formal institutional pilots, replace this with an approved data-sharing / confidentiality arrangement.

---

## Reconciliation procedure per case

### Step 1 — source-data check

Record:
- source documents received;
- period covered;
- completeness;
- duplicates/missing intervals;
- tariff category;
- subscribed kVA where relevant;
- whether data is measured, entered, estimated, benchmark, or independently verified.

### Step 2 — pre-solar bill reconciliation

Before modelling solar, Core v3 must reproduce the original electricity bill using the source kWh/kVA values.

If the baseline bill cannot be reproduced, stop. Do not proceed to solar savings until the discrepancy is explained.

### Step 3 — load-profile reconciliation

If interval data exists:
- parse the source file;
- reconcile annual/monthly kWh to bills;
- document missing/duplicate intervals;
- require explicit treatment for any repaired data.

### Step 4 — PV resource/design reconciliation

Compare:
- live/cached PVWatts output;
- contractor yield assumption;
- actual generation if available.

Do not automatically treat PVWatts or contractor yield as the truth. Record the difference and evidence basis.

### Step 5 — post-solar calculation

Compare:
- self-consumption;
- grid import;
- grid export;
- net-metering credits;
- post-solar bill;
- annual saving.

### Step 6 — independent output comparison

Compare Solar Passport against:
- contractor's original calculation;
- actual DES/net-metering statement if available;
- actual generation data if available.

Classify differences as:
- Core v3 defect;
- source-data issue;
- policy/utility convention ambiguity;
- different modelling assumption;
- timing/weather difference;
- unresolved.

### Step 7 — close the case

A validation case passes only when all material differences are either within the agreed tolerance or have an explicit documented explanation.

---

## Recommended first outreach sequence

1. Approach **two registered rooftop installers** for one residential and one commercial anonymized historic case each.
2. Approach **one registered installer with larger commercial/LSS experience** for commercial/C&I workflow and financial assumptions.
3. In parallel, recruit **one residential and one commercial volunteer customer** as an independent source not selected by the installer.
4. Send the DES/DSP clarification pack after the internal scenario numbers have been checked once more.
5. Give the standardized 100 MWac finance case to one local bank/adviser/developer for an independent model run.
6. Do not expand the sample until the Validation Console can ingest and report these first cases consistently.

---

## Minimum dataset to unlock the Validation Console

Development of the console does **not** require waiting for empirical data.

Build against synthetic fixtures now. A first useful real-data milestone is reached when we have:

- one anonymized residential monthly-bill case;
- one anonymized commercial bill+kVA case;
- one interval CSV of any Brunei building type;
- one external finance-model comparison of the standardized case.

That is enough to exercise every major validation workflow.

---

## Pilot success criteria

The first pilot is successful if Solar Passport can demonstrate, with evidence:

1. exact/accepted reproduction of source DES bills;
2. robust ingestion of real interval files;
3. transparent explanation of PV/yield differences;
4. consistent self-consumption/import/export calculations;
5. documented handling of net-metering policy ambiguities;
6. reconciled project-finance conventions;
7. a repeatable validation report for each case;
8. a clear list of model changes required before production use.

The objective is not to prove Solar Passport is already correct. The objective is to discover precisely where it is correct, where it differs, and what evidence is required to close each gap.
