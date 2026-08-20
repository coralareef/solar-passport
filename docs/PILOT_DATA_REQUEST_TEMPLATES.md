# Solar Passport — Pilot Data Request Templates

These templates are for model-validation outreach. Keep the request narrow: enough data to reconcile the calculation engine, without asking partners to disclose unnecessary personal or commercially sensitive information.

## 1. Solar contractor / installer

**Subject: Request for anonymized solar project data for Solar Passport validation**

Dear [Company/Name],

I am developing Solar Passport, a Brunei-focused platform intended to standardise rooftop solar assessment, billing calculations, procurement and Net-Metering application preparation.

I am currently validating the calculation engine against real Brunei cases and would appreciate your support with one or two anonymized completed/project cases. I am primarily looking for:

- monthly electricity consumption and bill values;
- subscribed kVA for commercial accounts;
- interval load data if available;
- installed/proposed PV capacity and basic system assumptions;
- your calculated annual generation/savings for comparison.

Customer name, account number, NRIC, phone number and exact address are not required and should be removed. An approximate district/location is sufficient for solar-resource reconciliation.

The data would be used only to compare Solar Passport's calculations against an existing real case and identify any differences before the platform is relied upon. I would be happy to share the reconciliation results back with you.

Thank you.

## 2. Residential volunteer

Hi [Name], I am testing a Brunei solar-calculation platform and need a few anonymized real electricity cases to make sure the numbers match actual DES bills.

If you are comfortable helping, I would only need your monthly kWh and bill values (ideally 12 months, but 3 recent months is already useful). If your meter/app can export hourly or half-hourly usage, that would be even more useful.

I do not need your name, account number, NRIC or exact address in the validation dataset. The data will be used to test the calculation model, not for marketing or profiling.

## 3. Commercial customer

**Subject: Solar Passport model-validation pilot — anonymized electricity data**

Dear [Name],

I am validating Solar Passport, a Brunei solar assessment platform designed to calculate the financial impact of rooftop solar using the actual DES commercial tariff structure.

Would your company be willing to provide an anonymized electricity-data case for model validation?

Minimum information requested:
- monthly kWh consumption;
- monthly electricity charge;
- subscribed capacity (kVA);
- business/building type;
- approximate district.

If available, a 15/30/60-minute meter export would allow us to test self-consumption and export much more accurately.

We do not require the customer's account number, company registration number, personal information or exact address. The objective is to reconcile Solar Passport's pre-solar and post-solar calculations against a real Brunei load profile and return the findings to the participant.

## 4. Bank / project-finance reviewer

**Subject: Request to reconcile standardized solar project-finance case**

Dear [Name],

Solar Passport Core v3 now includes a project-finance engine calculating P50/P90 cash flows, equity IRR, project IRR, NPV, LCOE, DSCR, LLCR, DSRA and tariff floors.

Before using these outputs institutionally, I would like to reconcile a fixed synthetic 100 MWac solar case against an independently prepared project-finance model.

I can provide a single standardized input sheet and annual Core v3 output schedule. No customer or commercially confidential project data is required.

The purpose is to identify convention differences in areas such as LLCR definition, DSRA funding/release, debt-service timing and lender thresholds, and to make those conventions configurable rather than assumed.

Would you or a colleague be willing to review/re-run this test case?

## Data handling note to include where appropriate

- Dataset receives a random validation case ID.
- Personally identifiable information is removed before calculation.
- Source evidence is not committed to the public/source-code repository.
- Data is used only for the agreed validation purpose unless further permission is obtained.
- Published results, if any, should be aggregated/anonymized unless the participant explicitly approves attribution.