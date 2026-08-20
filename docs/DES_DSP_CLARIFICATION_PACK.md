# Solar Passport Core v3 — DES / DSP Net-Metering Clarification Pack

Purpose: obtain authoritative confirmation of the billing and eligibility rules that cannot be unambiguously derived from the published materials alone.

This document separates:
- **published facts**;
- **the current Core v3 interpretation**;
- **worked scenarios**;
- **questions requiring DES / DSP confirmation**.

## Published facts used

Current public sources state that:

1. Net-metering is available to existing DES customers without outstanding arrears, for Solar PV from 1 kW to 1 MW / 1000 kW, across residential, government, commercial and industrial categories.
2. For each billing period, import and export are recorded and the net of import/export forms the electricity bill.
3. If export exceeds import, the excess becomes electricity credit carried into a future billing period.
4. Net energy may roll over for a maximum of 12 months; unused credit is forfeited and there is no monetary payout.
5. Credits are netted at the prevailing gazetted tariff.
6. Current Tariff B is a monthly kWh charge whose block widths are multiplied by subscribed kVA.
7. The current Net-Metering Assessment Form records both installed **kWp** and **kWac**. For generation capacity above 12 kW it also requires load-profile information including daytime peak demand, daytime lowest demand and export in kWac.

Sources to attach to the formal request:
- Department of Energy — Net Metering Programme
- Net-Metering Guideline, current published edition
- Net-Metering Assessment Form v1.2
- DES Electricity Tariff — Tariff B

## Tariff B reference

For subscribed capacity `K` kVA, current published monthly Tariff B is modelled as:

- first `10 × K` kWh at BND 0.20/kWh;
- next `100 × K` kWh at BND 0.07/kWh;
- next `100 × K` kWh at BND 0.06/kWh;
- remaining kWh at BND 0.05/kWh.

For the scenarios below, `K = 140 kVA`.

Therefore the block boundaries are:

- 0–1,400 kWh @ 0.20;
- 1,401–15,400 kWh @ 0.07;
- 15,401–29,400 kWh @ 0.06;
- >29,400 kWh @ 0.05.

The DES published reference case of 26,880 kWh at 140 kVA produces:

`1,400×0.20 + 14,000×0.07 + 11,480×0.06 = BND 1,948.80`.

---

# Scenario B1 — same-month import and export

Subscribed capacity: **140 kVA**

- Grid import: 20,000 kWh
- Solar export: 5,000 kWh
- Opening carried credit: 0 kWh

### Current Core v3 interpretation

Net billed energy first:

`20,000 - 5,000 = 15,000 kWh`

Then apply Tariff B to 15,000 kWh:

- 1,400 × 0.20 = 280.00
- 13,600 × 0.07 = 952.00

**Bill = BND 1,232.00**

### Confirmation requested

Is this the operational billing sequence?

**Option A — energy-netting first**

`Tariff B(import kWh - export kWh)`

which gives **BND 1,232.00**.

Or does DSP:

**Option B — calculate gross import charges first and then apply export as a separate tariff-valued credit?**

If Option B is used, please provide the exact method for assigning the export kWh across Tariff B's kVA-linked blocks.

---

# Scenario B2 — prior-month credit plus current-month export

Subscribed capacity: **140 kVA**

### Month 1

- Import: 5,000 kWh
- Export: 10,000 kWh

Current Core v3 interpretation:

- billed energy = 0 kWh;
- closing energy credit = 5,000 kWh;
- bill = BND 0.00, excluding any charges outside the published energy calculation.

### Month 2

- Opening carried credit: 5,000 kWh
- Import: 20,000 kWh
- Export: 2,000 kWh

Current-month net import:

`20,000 - 2,000 = 18,000 kWh`

Apply prior credit:

`18,000 - 5,000 = 13,000 kWh billed`

Tariff B:

- 1,400 × 0.20 = 280.00
- 11,600 × 0.07 = 812.00

**Month 2 bill = BND 1,092.00**

Closing credit = 0 kWh.

### Confirmation requested

1. Is carried credit applied as **kWh before the current month's Tariff B block calculation**, as above?
2. If not, how is carried credit converted into value when Tariff B's marginal block changes month to month?
3. Are there fixed/minimum/demand/service charges that remain payable even when net billed energy is zero under net-metering?

---

# Scenario B3 — netting changes the marginal Tariff B block

Subscribed capacity: **140 kVA**

- Import: 35,000 kWh
- Export: 7,000 kWh
- Opening credit: 0 kWh

Current Core v3 interpretation:

`35,000 - 7,000 = 28,000 kWh`

Tariff B on 28,000 kWh:

- 1,400 × 0.20 = 280.00
- 14,000 × 0.07 = 980.00
- 12,600 × 0.06 = 756.00

**Bill = BND 2,016.00**

For comparison, gross import of 35,000 kWh before any export treatment would be BND 2,380.00.

### Confirmation requested

Please confirm whether solar export reduces the amount of energy entering the later Tariff B blocks, as in the BND 2,016.00 result.

---

# Scenario B4 — carried credit crosses the 12-month settlement boundary

Assume 100 kWh excess credit is created in Billing Period 1 and remains unused.

Core v3 currently interprets "roll over for a maximum of 12 months" as allowing that credit to remain available through the following 12 billing periods, after which any remaining balance is forfeited.

### Confirmation requested

Please provide a date/billing-period example defining precisely when a credit created in Billing Period 1 expires. In particular, confirm whether it can be used during Billing Period 13 before expiry, or whether it expires at the start of that period.

---

# Scenario B5 — gazetted tariff changes while kWh credit is outstanding

Assume:

- 5,000 kWh credit was created under Tariff Version X;
- it remains valid when Tariff Version Y becomes effective;
- the customer later imports 8,000 kWh.

### Confirmation requested

Because the guideline describes electricity credit in kWh and also states credits are netted at the prevailing gazetted tariff, should the 5,000 kWh be:

A. deducted from current energy first, with the remaining 3,000 kWh billed entirely under Tariff Version Y; or
B. assigned a monetary value at the tariff prevailing when the credit was created; or
C. treated using another method?

Core v3 should follow the confirmed operational method and retain the applicable tariff-policy version in the audit record.

---

# Scenario C1 — formal basis of the 1 MW programme limit

The programme states eligibility from 1 kW up to 1 MW / 1000 kW. The current Assessment Form separately records:

- installed capacity in **kWp**; and
- installed capacity in **kWac**.

Example project:

- PV array: 1,080 kWp DC
- inverter aggregate rating: 900 kWac
- DC/AC ratio: 1.20

### Confirmation requested

Is this system eligible under the 1 MW programme limit?

Please confirm whether the programme's capacity boundary is assessed using:

1. PV module nameplate capacity in kWp DC;
2. inverter aggregate AC rating in kWac;
3. maximum export capacity at the PCC;
4. another defined installed-generation measure.

The answer is required so Solar Passport can enforce the eligibility gate correctly rather than assuming kWp or kWac.

---

# Draft formal query

**Subject: Request for clarification on Net-Metering billing treatment and 1 MW capacity basis — Solar Passport validation**

Dear Sir/Madam,

I am developing a Brunei-focused Solar Passport decision platform intended to standardise solar assessment, tariff calculation and Net-Metering application preparation. Before the calculation engine is relied upon, I would appreciate DES/DSP's confirmation of several operational billing cases where the current published guideline and Tariff B need to be combined.

Attached are five worked billing scenarios using a 140 kVA commercial account. The main clarification requested is whether monthly import, export and carried-forward electricity credits are first netted in kWh and the resulting net kWh is then passed through the current Tariff B blocks, or whether DSP applies another settlement sequence. The scenarios also ask how outstanding kWh credits are handled when a gazetted tariff changes and exactly when the 12-month credit period expires.

I would also appreciate confirmation of the formal capacity basis for the Net-Metering Programme's 1 kW–1 MW eligibility limit. The current Assessment Form records both kWp and kWac. For example, would a 1,080 kWp DC array limited by 900 kWac of inverter capacity be inside or outside the programme limit?

The objective is to reproduce the Department's actual rules faithfully in software. Any worked billing example, written clarification or reference to the applicable provision would be sufficient and will be retained as the source for the corresponding software rule.

Thank you for your guidance.

Kind regards,
Solar Passport Project

---

## Software action after response

For each answer received:

1. create/update the corresponding policy-registry rule;
2. record source, effective date and verified date;
3. encode the confirmed worked scenario as a permanent regression test;
4. retain older policy versions so historical assessments remain reproducible;
5. close V3-GATE-01 only when the scenarios can be reproduced exactly.