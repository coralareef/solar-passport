# Solar Passport MVP

Solar Passport is a Brunei-focused decision platform with two products:

1. **Building Solar Passport** — for building/business owners deciding whether rooftop solar makes sense, what size to install, likely savings/payback, and whether financing improves or worsens monthly cash flow.
2. **Project Bankability Passport** — for developers, investors, lenders and offtakers testing PPA tariffs, equity IRR, P90 DSCR, NPV, LCOE and the bankability corridor.

## Recommended Windows start

The project remains dependency-free (Python 3.10+ standard library only).

### First-time NREL setup

1. Copy `.env.example` to a new file named `.env`.
2. Open `.env` and enter your own NLR/NREL API key:

```text
NREL_API_KEY=YOUR_KEY_HERE
HOST=127.0.0.1
PORT=5000
```

3. `.env` is ignored by Git and must never be committed.
4. Start with:

```bat
cd /d D:\solar_passport
py run.py
```

or double-click `start.bat`.

`run.py` loads `.env` before importing the application. Use `run.py` for local development.

## PVWatts performance cache

The Building Passport evaluates many possible solar sizes. It no longer calls PVWatts separately for every size.

For each unique site / tilt / azimuth / loss configuration, Solar Passport now:

1. requests one **1-kWp** PVWatts resource profile;
2. stores the monthly kWh-per-kWp result in `.cache/pvwatts_profiles.json`;
3. scales that profile locally for all candidate system sizes;
4. reuses the stored profile on later runs and after restarts.

The cache is ignored by Git. Default cache life is 365 days and can be changed with `PV_CACHE_MAX_AGE_DAYS`.

The Command Prompt prints the model run time, for example:

```text
[MODEL] Building Passport completed in 0.042s (solar profile: cache).
```

## Building Passport electricity input

The customer now enters **one** electricity value:

- monthly kWh; or
- monthly electricity bill.

Then select the account type.

### Residential

Uses DES **Tariff A** block pricing. Solar Passport can convert both directions between monthly kWh and bill value.

### Commercial

Uses DES **Tariff B** kVA-based block pricing. Commercial calculations require **subscribed capacity (kVA)** because the tariff thresholds depend on kVA. Solar Passport can convert between bill and kWh once kVA is supplied.

The earlier `monthly bill ÷ monthly kWh = effective flat rate` shortcut is no longer used for DES commercial accounts.

## Building modelling boundaries

- PV generation uses PVWatts v8 when configured; otherwise the visible specific-yield fallback is used.
- Monthly building load is still flat across the year in this MVP.
- Self-consumption still uses a daytime-share proxy. The next accuracy improvement is 15/30/60-minute or hourly load upload matched against hourly solar generation.
- Tariff A and Tariff B are implemented in `model_v2.py` with regression tests.
- Net-metering/export-credit treatment remains an explicit assumption until a verified current rule is incorporated.
- Cost inputs remain assumptions until replaced by actual installer quotations.
- Structural, electrical and utility approvals remain outside the software assessment.

## Project Passport decision logic

Economics and readiness are now separate.

**Economics gate** tests:

- target equity IRR;
- minimum P90 DSCR when debt is used;
- project NPV;
- developer floor versus offtaker ceiling.

**Readiness score** separately covers sponsor, financing, site/land, solar-resource evidence, grid, PPA/offtake readiness, approvals, execution and risk allocation.

A very high tariff can therefore produce:

```text
AMBER — ECONOMICS PASS, READINESS GAPS
```

This means the financial case clears its hurdles but the development/readiness inputs are still incomplete. If debt is 0%, DSCR is correctly shown as not applicable rather than treated as a failure.

## Project modelling boundaries

- Annual cash flows and level debt service.
- P90 is represented by a user-entered P90/P50 factor.
- Developer floor is the highest applicable tariff required by equity IRR, P90 DSCR and zero project NPV constraints.
- Construction drawdowns, IDC, DSRA, LLCR, sculpted debt, depreciation, withholding tax, FX, termination compensation and detailed deemed-energy mechanics remain future modules.

## Run model regression tests

```bat
cd /d D:\solar_passport
python -m unittest -v test_model_v2.py
```

The regression suite checks the residential tariff, the published DES commercial example, bill-to-kWh inversions, debt-free DSCR handling, and green/amber project decision behaviour.

## Security

- No API keys are stored in source code.
- `.env` and `.cache/` are ignored by Git.
- PVWatts is called from Python on the server.
- The roof map uses OpenStreetMap/Leaflet and requires no Google Maps key.

## Normal update workflow

After changes are made to GitHub:

```bat
cd /d D:\solar_passport
git pull
py run.py
```

If you change files locally:

```bat
git status
git add .
git commit -m "Describe the change"
git push
```

## Next recommended increments

1. Satellite/map layer suitable for rooftop tracing.
2. Interval-load CSV/XLSX upload and hourly PV/load matching.
3. Prospecting mode: cached area-level solar resource + building footprints for technical lead screening (not buyer-likelihood claims without energy/customer data).
4. Verified net-metering/export-credit engine.
5. Bill upload/extraction and evidence tagging.
6. Installer quotation upload and RFQ/quote normalisation.
7. Branded Solar Passport PDF, saved scenarios and database.
8. Detailed project debt model and gas-displacement/offtaker value engine.
