# Solar Passport MVP

A working, dependency-free Python web MVP for two products:

1. **Building Solar Passport** — preliminary building solar sizing, bill impact, self-consumption, financing, IRR/NPV/payback and readiness.
2. **Project Bankability Passport** — PPA tariff solver, P50/P90 debt sizing tests, equity/project IRR, DSCR, NPV, LCOE, bankability corridor and CAPEX × tariff sensitivity.

## Run locally

```bash
cd solar_passport
python app.py
```

Then open `http://127.0.0.1:5000`.

## Optional PVWatts integration

The website works without Python packages and without external API keys. In fallback mode the Building Passport uses the user-visible `specific yield` field.

To enable NREL PVWatts v8:

```bash
export NREL_API_KEY="your-key"
python app.py
```

Do **not** commit API keys to source code.

## MVP modelling boundaries

### Building
- Monthly load is currently flat across 12 months unless a future interval-load upload module is added.
- Self-consumption is approximated from monthly PV and an estimated daytime load share.
- Tariff A and a custom flat tariff are implemented. Detailed commercial demand/subscribed-capacity tariffs and net-metering credit carry-forward rules should be added from verified official sources.
- Project cash flow includes degradation, O&M and a configurable inverter replacement.

### Project
- Uses annual cash flows and level debt service.
- P90 is represented as a user-defined P90/P50 factor.
- The tariff solver independently tests target equity IRR, P90 DSCR and zero project NPV; the highest is the developer floor.
- Tax is supported in the backend but set to zero in the current UI.
- Construction drawdowns, IDC, DSRA, LLCR, sculpted debt, depreciation, withholding tax, FX, termination payments and detailed deemed-energy mechanics remain future modules.

## Security changes from the previous calculator

- API keys are no longer embedded in Python or JavaScript.
- NREL key is read from `NREL_API_KEY` only on the server.
- The roof map uses OpenStreetMap/Leaflet and does not require a Google Maps key.

## Suggested next build increments

1. CSV/XLSX interval-load upload and hourly PV/load matching.
2. Verified Brunei commercial tariff and net-metering engine.
3. Building quote/RFQ normaliser.
4. Detailed project debt model with construction phase, DSRA and LLCR.
5. Offtaker/gas-displacement value engine.
6. Login, database, scenario persistence and evidence/source attachments.
7. Branded PDF report generated server-side from a saved scenario.
