const $ = (sel, root=document) => root.querySelector(sel);
const $$ = (sel, root=document) => [...root.querySelectorAll(sel)];
const fmt = new Intl.NumberFormat('en-BN', { maximumFractionDigits: 1 });
const money = new Intl.NumberFormat('en-BN', { style: 'currency', currency: 'BND', maximumFractionDigits: 0 });
const money2 = new Intl.NumberFormat('en-BN', { style: 'currency', currency: 'BND', maximumFractionDigits: 2 });

function formToObject(form) {
  const fd = new FormData(form);
  const out = {};
  for (const [k, v] of fd.entries()) {
    if (v === '') out[k] = '';
    else if (!Number.isNaN(Number(v)) && v.trim?.() !== '') out[k] = Number(v);
    else out[k] = v;
  }
  return out;
}

function statusClass(text='') {
  const s = text.toUpperCase();
  if (s.includes('RED') || s.includes('HOLD') || s.includes('STOP')) return 'bad';
  if (s.includes('AMBER') || s.includes('CONDITION') || s.includes('OPTIMISE')) return 'warn';
  if (s.includes('GREEN') || s === 'PROCEED') return 'good';
  return 'neutral';
}

function setTopStatus(id, status) {
  const el = document.getElementById(id);
  el.textContent = status;
  el.className = `status-chip ${statusClass(status)}`;
}

function switchView(view) {
  $$('.passport-view').forEach(v => v.classList.toggle('active', v.id === `view-${view}`));
  $$('.nav-link[data-view]').forEach(b => b.classList.toggle('active', b.dataset.view === view));
  document.getElementById('workspace').scrollIntoView({behavior: 'smooth', block: 'start'});
  if (view === 'building') setTimeout(() => window.roofMap?.invalidateSize(), 200);
}

$$('[data-view]').forEach(btn => btn.addEventListener('click', () => switchView(btn.dataset.view)));
$$('[data-switch]').forEach(btn => btn.addEventListener('click', () => switchView(btn.dataset.switch)));

$$('.form-section-title').forEach(btn => {
  btn.addEventListener('click', () => {
    const section = btn.closest('.form-section');
    section.classList.toggle('open');
    btn.querySelector('span').textContent = section.classList.contains('open') ? '−' : '+';
    setTimeout(() => window.roofMap?.invalidateSize(), 120);
  });
});

$$('input[type="range"]').forEach(input => {
  const output = input.closest('label').querySelector('.range-value');
  input.addEventListener('input', () => output.textContent = input.value);
});

// Modal
const methodology = $('#methodology-modal');
$('[data-modal="methodology"]').addEventListener('click', () => methodology.showModal());
$('.modal-close', methodology).addEventListener('click', () => methodology.close());
methodology.addEventListener('click', e => { if (e.target === methodology) methodology.close(); });
$('#print-passport').addEventListener('click', () => window.print());

// Optional roof map; website remains functional if external map scripts fail.
function initMap() {
  const fallback = $('#map-fallback');
  if (!window.L || !L.Control?.Draw) {
    $('#roof-map').style.display = 'none';
    fallback.style.display = 'grid';
    return;
  }
  const lat = Number($('#building-lat').value) || 4.9031;
  const lon = Number($('#building-lon').value) || 114.9398;
  const map = L.map('roof-map', { zoomControl: true, maxZoom: 19 }).setView([lat, lon], 18);
  window.roofMap = map;
  const baseTiles = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxNativeZoom: 19,
    maxZoom: 19,
    attribution: '© OpenStreetMap contributors'
  }).addTo(map);
  baseTiles.on('tileerror', () => {
    fallback.textContent = 'Some map tiles could not load. You can still enter roof area manually.';
    fallback.classList.add('map-warning');
  });
  const drawn = new L.FeatureGroup();
  map.addLayer(drawn);
  const drawControl = new L.Control.Draw({
    draw: { polygon: true, rectangle: true, circle: false, circlemarker: false, marker: false, polyline: false },
    edit: { featureGroup: drawn, remove: true }
  });
  map.addControl(drawControl);
  map.on(L.Draw.Event.CREATED, e => {
    drawn.clearLayers();
    drawn.addLayer(e.layer);
    const latlngs = e.layer.getLatLngs()[0] || [];
    if (latlngs.length >= 3) {
      const area = L.GeometryUtil.geodesicArea(latlngs);
      $('#roof-area').value = Math.round(area);
    } else if (e.layer.getBounds) {
      const bounds = e.layer.getBounds();
      const corners = [bounds.getNorthWest(), bounds.getNorthEast(), bounds.getSouthEast(), bounds.getSouthWest()];
      $('#roof-area').value = Math.round(L.GeometryUtil.geodesicArea(corners));
    }
  });
  map.on('moveend', () => {
    const c = map.getCenter();
    $('#building-lat').value = c.lat.toFixed(5);
    $('#building-lon').value = c.lng.toFixed(5);
  });
}
window.addEventListener('load', initMap);

function loading(target) {
  target.innerHTML = `<div class="loading"><span class="spinner"></span><strong>Running decision model…</strong><small>Generation · economics · readiness</small></div>`;
}

async function postJSON(url, payload) {
  const res = await fetch(url, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `Request failed: ${res.status}`);
  return data;
}

const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
function barChart(rows, key='solar_kwh') {
  const max = Math.max(1, ...rows.map(r => r[key] || 0));
  return `<div class="chart-shell"><div class="bar-chart">${rows.map((r,i) => {
    const h = Math.max(3, (r[key] / max) * 100);
    return `<div class="bar" style="height:${h}%" data-month="${months[i]}" title="${months[i]}: ${fmt.format(r[key])} kWh"></div>`;
  }).join('')}</div></div>`;
}

function assumptionsTable(rows) {
  return `<div class="table-wrap"><table><thead><tr><th>Variable</th><th>Value</th><th>Source</th><th>Confidence</th><th>Owner</th></tr></thead><tbody>${rows.map(r => `
    <tr><td><strong>${r.variable}</strong></td><td>${r.value}</td><td>${r.source}</td><td><span class="assumption-confidence">${r.confidence}</span></td><td>${r.owner}</td></tr>
  `).join('')}</tbody></table></div>`;
}

$('#building-form').addEventListener('submit', async e => {
  e.preventDefault();
  const target = $('#building-results');
  loading(target);
  try {
    const payload = formToObject(e.currentTarget);
    const data = await postJSON('/api/building/calculate', payload);
    renderBuilding(data, payload, target);
  } catch (err) {
    target.innerHTML = `<div class="error-card"><strong>Could not run the Building Passport.</strong><br>${err.message}</div>`;
  }
});

function renderBuilding(data, payload, target) {
  const r = data.recommendation.selected;
  const ready = data.readiness;
  setTopStatus('building-status-top', `${ready.score}/100 · ${ready.status}`);
  const payback = r.simple_payback_years == null ? 'Beyond model' : `${r.simple_payback_years.toFixed(1)} yr`;
  const irr = r.project_irr_pct == null ? 'n/a' : `${r.project_irr_pct.toFixed(1)}%`;

  target.innerHTML = `
    <div class="decision-card">
      <p class="eyebrow">EXECUTIVE DECISION</p>
      <div class="decision-row">
        <div><h3>${ready.status}</h3><p>${payload.site_name || 'Building'} · Recommended ${fmt.format(r.capacity_kwp)} kWp under the selected sizing objective.</p></div>
        <div class="score-ring">${ready.score}</div>
      </div>
    </div>

    <div class="metric-grid">
      <div class="metric"><span class="label">Recommended size</span><strong>${fmt.format(r.capacity_kwp)} kWp</strong><small>Roof max ${fmt.format(data.recommendation.max_roof_kwp)} kWp</small></div>
      <div class="metric"><span class="label">Year-1 saving</span><strong>${money.format(r.year1_saving)}</strong><small>Bill ${money.format(r.bill_before)} → ${money.format(r.bill_after)}</small></div>
      <div class="metric"><span class="label">Project IRR</span><strong>${irr}</strong><small>25-year simplified project cash flow</small></div>
      <div class="metric"><span class="label">Cash payback</span><strong>${payback}</strong><small>Includes O&amp;M and inverter replacement</small></div>
      <div class="metric"><span class="label">Self-consumption</span><strong>${r.self_consumption_pct.toFixed(1)}%</strong><small>${fmt.format(r.export_kwh)} kWh exported / yr</small></div>
      <div class="metric"><span class="label">Load coverage</span><strong>${r.load_coverage_pct.toFixed(1)}%</strong><small>${fmt.format(r.annual_load_kwh)} kWh annual load</small></div>
      <div class="metric"><span class="label">CAPEX</span><strong>${money.format(r.capex)}</strong><small>${money.format(payload.capex_per_kwp)} / kWp</small></div>
      <div class="metric"><span class="label">Financed monthly cash</span><strong>${money2.format(r.first_year_net_monthly_cash)}</strong><small>Debt payment ${money2.format(r.monthly_debt_payment)} / month</small></div>
    </div>

    <div class="panel-card">
      <h4>Why this size?</h4>
      <div class="scenario-grid">
        <div class="scenario"><span>Maximum roof</span><strong>${fmt.format(data.recommendation.max_roof_kwp)} kWp</strong></div>
        <div class="scenario"><span>Max bill offset</span><strong>${fmt.format(data.recommendation.max_bill_offset_kwp)} kWp</strong></div>
        <div class="scenario"><span>Self-consumption</span><strong>${fmt.format(data.recommendation.self_consumption_kwp)} kWp</strong></div>
        <div class="scenario"><span>Best IRR</span><strong>${fmt.format(data.recommendation.financial_return_kwp)} kWp</strong></div>
        <div class="scenario"><span>Best NPV</span><strong>${fmt.format(data.recommendation.maximum_npv_kwp)} kWp</strong></div>
        <div class="scenario"><span>Best cash flow</span><strong>${fmt.format(data.recommendation.cash_flow_kwp)} kWp</strong></div>
      </div>
    </div>

    <div class="panel-card"><h4>Decision drivers</h4><ul class="driver-list">${data.decision_reasons.map(x => `<li>${x}</li>`).join('')}</ul></div>

    <div class="panel-card">
      <h4>Monthly solar production</h4>
      <p class="muted">${r.generation_source} · ${r.generation_confidence} confidence</p>
      ${barChart(r.monthly)}
      <div class="table-wrap"><table><thead><tr><th>Month</th><th>Load</th><th>Solar</th><th>Self-use</th><th>Export</th><th>Import</th><th>Bill before</th><th>Bill after</th></tr></thead><tbody>
        ${r.monthly.map((m,i) => `<tr><td>${months[i]}</td><td>${fmt.format(m.load_kwh)}</td><td>${fmt.format(m.solar_kwh)}</td><td>${fmt.format(m.self_consumed_kwh)}</td><td>${fmt.format(m.export_kwh)}</td><td>${fmt.format(m.grid_import_kwh)}</td><td>${money2.format(m.bill_before)}</td><td>${money2.format(m.bill_after)}</td></tr>`).join('')}
      </tbody></table></div>
    </div>

    <div class="panel-card"><h4>Assumptions register</h4>${assumptionsTable(data.assumptions)}</div>
  `;
}

$('#project-form').addEventListener('submit', async e => {
  e.preventDefault();
  const target = $('#project-results');
  loading(target);
  try {
    const payload = formToObject(e.currentTarget);
    const data = await postJSON('/api/project/calculate', payload);
    renderProject(data, payload, target);
  } catch (err) {
    target.innerHTML = `<div class="error-card"><strong>Could not run the Project Passport.</strong><br>${err.message}</div>`;
  }
});

function tariffText(x) { return x == null ? 'n/a' : `${(x * 100).toFixed(2)}¢`; }

function renderProject(data, payload, target) {
  const t = data.tested;
  const s = data.tariff_solver;
  const ready = data.readiness;
  setTopStatus('project-status-top', `${ready.score}/100 · ${ready.status}`);
  const atOrAboveFloor = s.developer_floor != null && t.ppa_tariff >= s.developer_floor;
  const projectDecision = atOrAboveFloor ? ready.status : 'AMBER — TARIFF / COST GAP';
  const gap = s.developer_floor == null ? null : (s.developer_floor - t.ppa_tariff);

  target.innerHTML = `
    <div class="decision-card">
      <p class="eyebrow">BANKABILITY DECISION</p>
      <div class="decision-row">
        <div><h3>${projectDecision}</h3><p>${payload.project_name || 'Solar project'} · Tested at ${tariffText(t.ppa_tariff)}/kWh. ${gap > 0 ? `Current tariff is ${(gap*100).toFixed(2)}¢ below the modelled developer floor.` : 'Current tariff clears the modelled developer floor.'}</p></div>
        <div class="score-ring">${ready.score}</div>
      </div>
    </div>

    <div class="metric-grid">
      <div class="metric"><span class="label">Equity IRR @ tested tariff</span><strong>${t.equity_irr_pct == null ? 'n/a' : t.equity_irr_pct.toFixed(1)+'%'}</strong><small>Target ${payload.target_equity_irr_pct}%</small></div>
      <div class="metric"><span class="label">Minimum P90 DSCR</span><strong>${t.min_p90_dscr == null ? 'n/a' : t.min_p90_dscr.toFixed(2)+'×'}</strong><small>Minimum ${Number(payload.min_dscr).toFixed(2)}×</small></div>
      <div class="metric"><span class="label">Project NPV</span><strong>${money.format(t.npv)}</strong><small>Discounted project cash flow</small></div>
      <div class="metric"><span class="label">LCOE</span><strong>${t.lcoe == null ? 'n/a' : tariffText(t.lcoe)}</strong><small>Simplified lifecycle cost</small></div>
      <div class="metric"><span class="label">Total CAPEX</span><strong>${money.format(t.total_capex)}</strong><small>${money.format(payload.capex_per_mw)} / MWac</small></div>
      <div class="metric"><span class="label">Year-1 energy sold</span><strong>${fmt.format(t.year1_energy_mwh)} MWh</strong><small>After curtailment &amp; other losses</small></div>
      <div class="metric"><span class="label">Year-1 revenue</span><strong>${money.format(t.year1_revenue)}</strong><small>At tested PPA tariff</small></div>
      <div class="metric"><span class="label">Annual debt service</span><strong>${money.format(t.annual_debt_service)}</strong><small>${payload.debt_tenor_years}-year debt tenor</small></div>
    </div>

    <div class="panel-card">
      <h4>Bankability corridor</h4>
      <div class="corridor ${s.corridor_exists ? 'exists' : 'missing'}">
        <div class="corridor-side"><span>Developer floor</span><strong>${tariffText(s.developer_floor)}</strong><small>Binding: ${s.binding_constraint || 'n/a'}</small></div>
        <div class="corridor-arrow">→</div>
        <div class="corridor-side"><span>Offtaker ceiling</span><strong>${tariffText(s.offtaker_ceiling)}</strong><small>${s.corridor_exists ? 'Economic corridor exists' : 'No confirmed corridor under current inputs'}</small></div>
      </div>
      <div class="scenario-grid">
        <div class="scenario"><span>For target equity IRR</span><strong>${tariffText(s.for_target_equity_irr)}</strong></div>
        <div class="scenario"><span>For P90 DSCR</span><strong>${tariffText(s.for_min_p90_dscr)}</strong></div>
        <div class="scenario"><span>For zero project NPV</span><strong>${tariffText(s.for_zero_project_npv)}</strong></div>
      </div>
    </div>

    <div class="panel-card"><h4>Recommended intervention</h4><ul class="driver-list">${data.interventions.map(x => `<li>${x}</li>`).join('')}</ul></div>

    <div class="panel-card">
      <h4>CAPEX × tariff sensitivity</h4>
      <div class="table-wrap"><table class="matrix-table"><thead><tr><th>CAPEX / MW</th>${data.sensitivity.tariffs.map(x => `<th>${tariffText(x)}</th>`).join('')}</tr></thead><tbody>
      ${data.sensitivity.matrix.map(row => `<tr><th>${money.format(row.capex_per_mw)}</th>${row.cells.map(cell => {
        const passIrr = cell.equity_irr_pct != null && cell.equity_irr_pct >= payload.target_equity_irr_pct;
        const passDscr = cell.p90_dscr != null && cell.p90_dscr >= payload.min_dscr;
        const klass = passIrr && passDscr ? 'pass' : (passIrr || passDscr ? 'near' : 'fail');
        return `<td class="matrix-cell ${klass}"><strong>${cell.equity_irr_pct == null ? 'n/a' : cell.equity_irr_pct.toFixed(1)+'%'}</strong><small>${cell.p90_dscr == null ? 'n/a' : cell.p90_dscr.toFixed(2)+'×'}</small></td>`;
      }).join('')}</tr>`).join('')}
      </tbody></table></div>
    </div>

    <div class="panel-card"><h4>Assumptions register</h4>${assumptionsTable(data.assumptions)}</div>
  `;
}
