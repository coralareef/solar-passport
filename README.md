# Solar Passport MVP

Solar Passport is a Brunei-focused decision platform with two products:

1. **Building Solar Passport** — for building/business owners deciding whether rooftop solar makes sense, what size to install, likely savings/payback, and whether financing improves or worsens monthly cash flow.
2. **Project Bankability Passport** — for developers, investors, lenders and offtakers testing PPA tariffs, equity IRR, P90 DSCR, NPV, LCOE and the bankability corridor.

## Recommended Windows start

The project remains dependency-free (Python 3.10+ standard library only).

### First-time NREL setup

1. Copy `.env.example` to a new file named `.env`.
2. Open `.env` and enter your own NREL key:

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

`run.py` loads `.env` before importing the application. The older `py app.py` command does **not** load `.env`; use `run.py` for local development.

The website performs a small connection check on page load and shows either:

- **NREL PVWatts v8 connected**, or
- **Estimate mode — NREL key not active**.

PVWatts remains server-side; the API key is never sent to browser JavaScript.

## Building Passport — revised customer flow

The normal Building Passport asks for:

- building type;
- typical monthly bill;
- typical monthly kWh from the bill;
- roof area / map polygon;
- cash vs financing preference.

Technical inputs such as daytime-use share, export credit, specific yield fallback, tilt, azimuth, CAPEX/kWp, O&M, discount rate, degradation and inverter replacement are under **Advanced assumptions**.

For business accounts, the quick screen derives an effective electricity price from `monthly bill / monthly kWh` instead of asking the customer for a "flat import rate".

Solar Passport automatically compares:

- maximum roof capacity;
- annual bill/load offset sizing;
- self-consumption sizing;
- maximum IRR;
- maximum NPV;
- best first-year financed cash flow.

The user does not need to choose a sizing objective.

## Building modelling boundaries

- PV generation uses NREL PVWatts v8 when configured; otherwise the visible specific-yield fallback is used.
- Monthly building load is still flat across the year in this MVP.
- Self-consumption still uses a daytime-share proxy. The UI estimates it by building type and lets an analyst override it.
- The next accuracy improvement should be 15/30/60-minute or hourly load upload matched against hourly PVWatts generation.
- Residential Tariff A and a custom/effective flat tariff are implemented.
- Brunei commercial tariff rules, demand/subscribed-capacity charges and net-metering/export-credit treatment must be replaced with verified current rules before investment-grade reliance.
- Cost inputs are assumptions until replaced by actual installer quotations.
- Structural, electrical and utility approvals remain outside the software assessment.

## Project modelling boundaries

- Annual cash flows and level debt service.
- P90 is represented by a user-entered P90/P50 factor.
- Developer floor is the highest tariff required by equity IRR, P90 DSCR and zero project NPV constraints.
- Construction drawdowns, IDC, DSRA, LLCR, sculpted debt, depreciation, withholding tax, FX, termination compensation and detailed deemed-energy mechanics remain future modules.

## Security

- No API keys are stored in source code.
- `.env` is ignored by Git.
- NREL is called from Python on the server.
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

1. Interval-load CSV/XLSX upload and hourly PV/load matching.
2. Verified Brunei commercial tariff and net-metering engine.
3. Bill upload/extraction and evidence tagging.
4. Installer quotation upload and RFQ/quote normalisation.
5. Branded Solar Passport PDF.
6. Saved scenarios, accounts and database.
7. Detailed project debt model and gas-displacement/offtaker value engine.
