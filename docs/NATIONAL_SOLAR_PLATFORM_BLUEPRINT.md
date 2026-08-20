# Solar Passport — National Solar Transaction Platform Blueprint

## Mission

Solar Passport should become the shared digital transaction layer that reduces the cost, uncertainty and time required to move a Brunei solar opportunity from first screening to commissioning and operation.

It should make the lives of four core groups easier:

1. Customers / off-takers — understand whether solar makes sense, procure transparently, compare offers and complete applications.
2. Solar developers / EPCs / suppliers — qualify leads, submit standardized designs and quotes, satisfy compliance requirements and progress projects faster.
3. Government / regulator / utility — apply current policy consistently, receive structured applications, evaluate projects against common rules and monitor national deployment.
4. Financial institutions / investors — receive a standardized bankability package with traceable assumptions, downside cases and financing metrics.

The platform should not claim to replace engineering judgment, grid studies, regulatory approval, legal advice, physical surveys or construction. It should digitize and coordinate the information, qualification, commercial, approval and evidence workflow around those activities.

---

## Core product decision

Do not build four disconnected calculators. Build one shared `Project Passport` record with role-based views.

Every project should have one project ID and one controlled dataset covering:

- site and ownership;
- customer account and load;
- tariff and net-metering policy;
- roof / land geometry;
- solar-resource assumptions;
- technical design;
- equipment and certifications;
- quotations and procurement;
- financial model and financing;
- grid connection;
- regulatory applications;
- compliance evidence;
- contracts and approvals;
- construction / commissioning status;
- operating generation and performance.

The same data should feed the customer quote, developer design, government application, lender model and final operating record. Re-keying the same information into separate forms should be eliminated wherever possible.

---

## Trust architecture

Every important variable should carry metadata:

- `value`
- `unit`
- `status`: Entered / Estimated / Benchmark / Verified
- `source`
- `source_url_or_document`
- `effective_date`
- `expiry_or_review_date`
- `owner`
- `last_updated_by`
- `last_updated_at`

A number without provenance must never silently become a 'verified' number.

Policy rules should be versioned. A project assessed under one tariff or guideline must retain the rule version used even after national policy changes.

---

## Stakeholder workspaces

### 1. Customer / Off-taker Workspace

Primary question: `Should I install solar, what size, what will it cost, and who should I buy it from?`

Capabilities:

- locate building / trace roof;
- enter one known electricity value or upload bills;
- upload interval meter data;
- automatically apply the correct DES tariff logic;
- estimate hourly self-consumption and export;
- show cash / financing / lease / PPA cases;
- show payback, IRR, NPV and bill impact in plain language;
- request quotations from registered contractors;
- compare normalized quotes;
- appoint a selected contractor;
- track net-metering application progress;
- store approvals, warranties and commissioning records;
- view actual generation and savings after commissioning.

### 2. Developer / EPC Workspace

Primary question: `Which opportunities are qualified, what do I need to submit, and what is blocking execution?`

Capabilities:

- qualified lead pipeline;
- site and load data provided once by customer;
- system design submission;
- equipment schedule and certification upload;
- automatic compliance matrix;
- standardized CAPEX/OPEX quote submission;
- yield model upload / comparison against platform reference;
- RFQ / tender response;
- net-metering application package generation;
- project milestones and evidence tracker;
- commissioning package / as-built upload;
- warranty and O&M record.

### 3. Government / Utility / Regulator Workspace

Primary question: `Is this application complete, compliant, technically acceptable and consistent with current policy?`

Capabilities:

- policy and rule registry;
- contractor registry synchronization / verification;
- standardized application intake;
- automated completeness checking;
- compliance exceptions queue;
- grid-assessment handoff and result recording;
- digital review comments and resubmissions;
- approval / conditional approval / rejection workflow;
- RFP / tender publication and bid comparison;
- national pipeline dashboard: MW proposed, approved, installed, connected, generated;
- policy analytics: rejection reasons, average processing time, bottlenecks, tariff sensitivity;
- national renewable-energy reporting.

### 4. Bank / Investor Workspace

Primary question: `Is this cash flow financeable and what are the downside risks?`

Capabilities:

- standardized financial model input;
- P50 / P90 generation;
- project and equity IRR;
- DSCR by year and minimum P90 DSCR;
- LLCR;
- debt sizing / sculpting;
- DSRA requirement;
- debt tenor and pricing;
- NPV / LCOE;
- tariff solver / developer floor;
- downside sensitivity and break-even analysis;
- evidence register linked to assumptions;
- conditions precedent checklist;
- credit memo export.

---

## National project lifecycle

### Gate 0 — Discovery / Prospecting

Inputs:
- map location;
- building footprint / roof area;
- broad building type;
- cached solar resource.

Outputs:
- technical solar potential;
- lead score;
- estimated potential generation;
- invitation to complete a Quick Passport.

This is a lead-generation screen only. It must not infer willingness to buy, income, creditworthiness or actual consumption from roof geometry.

### Gate 1 — Quick Solar Passport

Inputs:
- customer type;
- one known electricity value or bill upload;
- subscribed capacity where commercial tariff requires it;
- roof geometry;
- basic financing preference.

Outputs:
- recommended preliminary kWp;
- expected bill impact;
- estimated CAPEX;
- payback / IRR / NPV;
- confidence rating;
- next action.

### Gate 2 — Verified Load & Site

Required evidence:
- 12 months bills or interval load data;
- customer account / tariff category;
- subscribed kVA where applicable;
- site ownership / authorization;
- roof / land survey information.

Outputs:
- verified load model;
- tariff baseline;
- hourly self-consumption / export model;
- site data pack.

### Gate 3 — Technical Pre-Design & Compliance

Required developer inputs:
- module / inverter / BOS specification;
- DC/AC ratio;
- layout;
- SLD;
- protection philosophy;
- equipment certifications;
- compliance declarations.

Automated checks should reference current Department of Energy / AENBD / ESCOM / SHENA requirements but must clearly distinguish automated checks from formal regulatory approval.

### Gate 4 — Procurement / RFQ

Platform functions:
- issue standard RFQ;
- invite eligible registered contractors;
- normalize bid assumptions;
- compare CAPEX, yield, warranties, equipment, O&M and exclusions;
- expose deviations instead of comparing headline price alone.

### Gate 5 — Bankability & Financing

Platform functions:
- validate project economics;
- model net-metering / tariff mechanics;
- financing scenarios;
- P50/P90;
- DSCR / LLCR / DSRA;
- IRR / NPV / LCOE;
- break-even tariff / CAPEX;
- sensitivity matrix;
- lender conditions.

### Gate 6 — Regulatory / Grid Approval

Platform functions:
- auto-populate current approved forms;
- package required evidence;
- route to responsible authority / utility if integrations are formally authorized;
- maintain comments, resubmissions and decision history;
- record grid study result.

The software must not simulate formal approval by itself.

### Gate 7 — Contract / Financial Close

Platform functions:
- generate project data schedules;
- populate government- or counsel-approved PPA / EPC / lease templates;
- manage versioning and approvals;
- capture financing term sheet and conditions precedent.

Do not claim a generic auto-generated contract is Brunei-law compliant. Only approved templates controlled by the relevant authority / legal counsel should be treated as authoritative.

### Gate 8 — Construction & Commissioning

Track:
- construction milestones;
- inspections;
- test certificates;
- as-builts;
- net meter installation;
- commissioning;
- warranties;
- defects / punch list.

### Gate 9 — Operations

Track:
- actual solar generation;
- grid import / export;
- bill savings;
- performance ratio;
- degradation;
- outages / maintenance;
- warranty claims;
- environmental attributes / certificates;
- national reporting.

---

## Policy logic that should be treated as first-class software

### Current Net-Metering Programme

The policy engine should encode, with version/date/source:

- existing DES customer eligibility;
- no outstanding arrears requirement;
- Solar PV only;
- minimum 1 kW and maximum 1 MW / 1000 kW under the programme;
- residential, government, commercial and industrial categories;
- contractor / installer processes the application on the customer's behalf;
- export credits are accounted at the prevailing gazetted tariff for the relevant supply voltage / PCC;
- excess energy credit can roll over for up to 12 months;
- remaining credit after the settlement period is forfeited;
- no monetary cash transaction for net-metering credit;
- no electricity licence is required for qualifying <=1 MW net-metering installations;
- environmental attributes remain with the net-metering consumer or investor / asset owner.

These rules must be kept in a versioned policy registry instead of hard-coded invisibly in calculations.

### DES electricity tariff

The current engine should support at minimum:

- Tariff A residential 4-tier structure;
- Tariff B commercial kVA-linked tier structure;
- explicit flag that Tariff B does not apply to heavy industry;
- future-effective tariff versions, including the proposed progressive commercial tariff targeted for 2028 once formally published.

Do not describe the current commercial tariff as a single BND/kWh rate. It depends on consumption and subscribed capacity.

---

## Compliance engine

The compliance engine should have rules grouped by source and scope. For example, the May 2026 ESCOM outdoor solar guideline includes requirements such as:

- bypass diodes on solar modules, with at least three per module for series-connected arrays;
- grid-connected inverters being grid-following;
- transformerless grid-following configuration with automatic shutdown for grid loss / instability;
- minimum IP65 inverter enclosures for outdoor installations;
- bottom-entry cable entries outdoors; top entry prohibited.

The platform should record:

- rule ID;
- source document and revision;
- scope applicability;
- developer response;
- evidence document;
- pass / fail / not applicable / review required;
- reviewer decision.

Automated compliance checking should never be presented as final statutory approval.

---

## Carbon / environmental attributes

Treat environmental value as an optional revenue module, not guaranteed base-case revenue.

The current net-metering guideline explicitly states that environmental attributes belong to the consumer or investor / asset owner. I-TRACK lists Brunei among countries supported by an authorized issuer structure for I-REC(E). The platform can therefore include:

- renewable generation eligible for attribute tracking;
- Scope 2 avoided-emissions reporting;
- I-REC(E) facility / issuance workflow status;
- certificate quantity;
- certificate market-price assumption;
- scenario revenue.

Base-case bankability should default this revenue to zero unless registration, issuance route, ownership, buyer / offtake and pricing are evidenced.

---

## Power-system engineering boundary

Do not try to recreate DIgSILENT inside Solar Passport initially.

The platform should instead become the workflow and evidence layer around grid studies:

- connection point;
- voltage level;
- substation / feeder;
- available hosting / injection capacity if published or supplied by utility;
- required studies;
- study provider;
- study files;
- fault level;
- protection requirements;
- voltage / reactive requirements;
- curtailment conditions;
- grid study decision and conditions.

Future integration can exchange data with power-system analysis tools, but the first product should manage the process and results, not implement a full transient-stability solver.

---

## Data model — minimum entities

1. Organization
2. User
3. Role / permission
4. Customer account
5. Site
6. Building / land polygon
7. Meter
8. Load profile
9. Tariff version
10. Policy rule version
11. Solar resource profile
12. System design
13. Equipment item
14. Equipment certification
15. Contractor registration
16. RFQ
17. Bid / quotation
18. Financial scenario
19. Financing offer
20. Grid connection case
21. Regulatory application
22. Compliance requirement
23. Evidence document
24. Approval / decision
25. Contract / term sheet
26. Construction milestone
27. Commissioning record
28. Operating meter data
29. Environmental attribute record
30. Audit log

---

## What Solar Passport should not become

Avoid these traps:

1. A giant form — each stakeholder should only see information relevant to their role and current gate.
2. A black-box score — every decision must expose the drivers and evidence.
3. A regulator impersonator — automated checks support formal decisions; they do not replace statutory authority.
4. A legal-document generator without controlled templates — use approved templates and variable schedules.
5. A marketplace that rewards cheapest CAPEX — normalize technical quality, yield assumptions, warranties and exclusions.
6. A carbon-revenue model that assumes certificates will automatically sell — environmental revenue must be evidence-based.
7. A calculator that re-queries external APIs for identical data — cache resource / policy data with version and expiry.
8. A static rules engine — every tariff, guideline and application form must be versioned and updateable without rewriting the financial model.

---

## Build order

### Phase 1 — Trusted national calculation core

Build now:
- versioned DES tariff engine;
- versioned net-metering settlement engine;
- PVWatts cache;
- interval load parser;
- hourly PV / load matching;
- customer Building Passport;
- project finance engine with P50/P90, DSCR, LLCR, DSRA, debt sizing;
- source / assumption registry;
- automated regression tests.

### Phase 2 — Qualification & procurement

- contractor registry;
- equipment / compliance matrix;
- RFQ creation;
- standardized bid submission;
- quote comparison;
- selected-contractor appointment;
- project lifecycle gates.

### Phase 3 — Regulatory workflow

Only after engagement / approval from responsible agencies:
- net-metering form auto-population;
- assessment checklist;
- submission package;
- review workflow;
- digital comments / resubmissions;
- approval records;
- national dashboard.

### Phase 4 — Finance & contracts

With participating banks / legal owners:
- bank-specific debt products and hurdle rules;
- lender credit pack;
- conditions precedent;
- approved PPA / EPC / lease templates;
- e-sign / execution integration where authorized.

### Phase 5 — Operations / national intelligence

- operating-data ingestion;
- generation / savings verification;
- O&M / warranty;
- environmental attributes;
- national solar deployment dashboard;
- performance benchmarking;
- prospecting map using building footprints and cached solar resource.

---

## National success metrics

Measure transaction outcomes, not website traffic:

- days from lead to qualified project;
- days from complete net-metering package to decision;
- % applications complete at first submission;
- % projects receiving >=2 comparable bids;
- project conversion rate from screening to commissioning;
- financing approval time;
- installed MW / year facilitated;
- average solar CAPEX / kWp;
- average self-consumption rate;
- verified annual renewable generation;
- avoided grid energy / emissions;
- common rejection / delay reasons;
- customer realized savings versus modeled savings.

The strongest national value of Solar Passport is the dataset created by standardized transactions. Over time it can reveal exactly where Brunei solar projects fail, what interventions lower cost, what financing structures work, which policies create bottlenecks and which segments convert fastest.
