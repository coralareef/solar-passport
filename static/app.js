const $ = (sel, root=document) => root.querySelector(sel);
const $$ = (sel, root=document) => [...root.querySelectorAll(sel)];
const fmt = new Intl.NumberFormat('en-BN', { maximumFractionDigits: 1 });
const money = new Intl.NumberFormat('en-BN', { style: 'currency', currency: 'BND', maximumFractionDigits: 0 });
const money2 = new Intl.NumberFormat('en-BN', { style: 'currency', currency: 'BND', maximumFractionDigits: 2 });

const BUILDING_DAYTIME_DEFAULTS = {
  workshop: 75, office: 80, retail: 75, supermarket: 85, warehouse: 60,
  restaurant: 70, school: 80, clinic: 75, factory: 80, residential: 40, other: 65
};

function formToObject(form) {
  const fd = new FormData(form);
  const out = {};
  for (const [k, v] of fd.entries()) {
    if (v === '') out[k] = '';
    else if (!Number.isNaN(Number(v)) && String(v).trim() !== '') out[k] = Number(v);
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
  if (!el) return;
  el.textContent = status;
  el.className = `status-chip ${statusClass(status)}`;
}
function switchView(view) {
  $$('.passport-view').forEach(v => v.classList.toggle('active', v.id === `view-${view}`));
  $$('.nav-link[data-view]').forEach(b => b.classList.toggle('active', b.dataset.view === view));
  $('#workspace').scrollIntoView({behavior:'smooth', block:'start'});
  if (view === 'building') setTimeout(() => window.roofMap?.invalidateSize(), 180);
}
$$('[data-view]').forEach(btn => btn.addEventListener('click', () => switchView(btn.dataset.view)));
$$('[data-switch]').forEach(btn => btn.addEventListener('click', () => switchView(btn.dataset.switch)));

$$('.form-section-title').forEach(btn => btn.addEventListener('click', () => {
  const section = btn.closest('.form-section');
  section.classList.toggle('open');
  const span = btn.querySelector('span');
  if (span) span.textContent = section.classList.contains('open') ? '−' : '+';
  setTimeout(() => window.roofMap?.invalidateSize(), 120);
}));
$$('input[type="range"]').forEach(input => {
  const output = input.closest('label')?.querySelector('.range-value');
  input.addEventListener('input', () => { if (output) output.textContent = input.value; });
});

const methodology = $('#methodology-modal');
$('[data-modal="methodology"]')?.addEventListener('click', () => methodology?.showModal());
$('.modal-close', methodology || document)?.addEventListener('click', () => methodology?.close());
methodology?.addEventListener('click', e => { if (e.target === methodology) methodology.close(); });
$('#print-passport')?.addEventListener('click', () => window.print());

function updateQuickDerivedInputs() {
  const form = $('#building-form');
  if (!form) return;
  const monthlyBill = Number(form.elements.monthly_bill.value) || 0;
  const monthlyKwh = Number(form.elements.monthly_kwh.value) || 0;
  const type = form.elements.building_type.value || 'other';
  const tariffChoice = form.elements.customer_tariff_choice.value;

  $('#annual-kwh').value = monthlyKwh > 0 ? monthlyKwh * 12 : 0;
  $('#daytime-share').value = BUILDING_DAYTIME_DEFAULTS[type] ?? 65;

  if (tariffChoice === 'residential') {
    $('#tariff-type').value = 'tariff_a';
    $('#effective-rate-note').textContent = 'Residential Tariff A will be applied to monthly imported electricity. The business-rate field below is ignored.';
  } else {
    $('#tariff-type').value = 'flat';
    if (monthlyBill > 0 && monthlyKwh > 0) {
      const effective = monthlyBill / monthlyKwh;
      $('#flat-rate').value = effective.toFixed(6);
      $('#effective-rate-note').textContent = `Effective electricity price inferred from your inputs: BND ${effective.toFixed(4)}/kWh (monthly bill ÷ monthly kWh).`;
    } else {
      $('#effective-rate-note').textContent = 'Enter both monthly bill and monthly kWh so Solar Passport can infer the effective electricity price.';
    }
  }
}
['input','change'].forEach(evt => $('#building-form')?.addEventListener(evt, e => {
  if (['monthly_bill','monthly_kwh','building_type','customer_tariff_choice'].includes(e.target.name)) updateQuickDerivedInputs();
}));
$('#payment-view')?.addEventListener('change', e => {
  $('#finance-quick').style.display = e.target.value === 'cash' ? 'none' : 'grid';
});
updateQuickDerivedInputs();

function initMap() {
  const fallback = $('#map-fallback');
  const mapDiv = $('#roof-map');
  if (!mapDiv) return;
  if (!window.L || !L.Control?.Draw) {
    mapDiv.style.display = 'none';
    fallback.style.display = 'grid';
    return;
  }
  const lat = Number($('#building-lat').value) || 4.9031;
  const lon = Number($('#building-lon').value) || 114.9398;
  const map = L.map('roof-map', { zoomControl:true, maxZoom:19 }).setView([lat, lon], 18);
  window.roofMap = map;
  const tiles = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxNativeZoom:19, maxZoom:19, attribution:'© OpenStreetMap contributors' }).addTo(map);
  tiles.on('tileerror', () => {
    fallback.textContent = 'Some map tiles could not load. You can still enter roof area manually.';
    fallback.classList.add('map-warning');
  });
  const drawn = new L.FeatureGroup();
  map.addLayer(drawn);
  map.addControl(new L.Control.Draw({ draw:{ polygon:true, rectangle:true, circle:false, circlemarker:false, marker:false, polyline:false }, edit:{ featureGroup:drawn, remove:true } }));
  map.on(L.Draw.Event.CREATED, e => {
    drawn.clearLayers(); drawn.addLayer(e.layer);
    let area = 0;
    const latlngs = e.layer.getLatLngs?.()[0] || [];
    if (latlngs.length >= 3) area = L.GeometryUtil.geodesicArea(latlngs);
    else if (e.layer.getBounds) {
      const b = e.layer.getBounds();
      area = L.GeometryUtil.geodesicArea([b.getNorthWest(), b.getNorthEast(), b.getSouthEast(), b.getSouthWest()]);
    }
    if (area > 0) $('#roof-area').value = Math.round(area);
  });
  map.on('moveend', () => {
    const c = map.getCenter();
    $('#building-lat').value = c.lat.toFixed(5);
    $('#building-lon').value = c.lng.toFixed(5);
  });
}
window.addEventListener('load', initMap);

async function postJSON(url, payload) {
  const res = await fetch(url, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload) });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `Request failed: ${res.status}`);
  return data;
}
function loading(target) { target.innerHTML = `<div class="loading"><span class="spinner"></span><strong>Running Solar Passport…</strong><small>Solar production · bill impact · sizing · economics</small></div>`; }

async function checkSolarDataConnection() {
  const badge = $('#nrel-status');
  if (!badge) return;
  const probe = {
    site_name:'Connection test', tariff_type:'flat', flat_rate:0.10, monthly_bill:100,
    annual_kwh:12000, daytime_share_pct:70, export_credit:0, roof_area_m2:10,
    usable_roof_pct:50, area_per_kwp:6.5, specific_yield:1420, lat:4.9031, lon:114.9398,
    tilt:10, azimuth:180, losses:14, capex_per_kwp:1500, om_pct:1, discount_rate_pct:8,
    degradation_pct:0.5, inverter_replacement_pct:8, down_payment_pct:20, loan_rate_pct:5.5,
    loan_years:10, sizing_mode:'custom', capacity_kwp:0.5
  };
  try {
    const data = await postJSON('/api/building/calculate', probe);
    const source = data?.recommendation?.selected?.generation_source || '';
    if (source.includes('NREL PVWatts')) {
      badge.className = 'resource-status connected';
      badge.innerHTML = `<span class="status-dot"></span><div><strong>NREL PVWatts v8 connected</strong><small>Solar generation is being calculated from the NREL resource model for the entered coordinates.</small></div>`;
    } else {
      badge.className = 'resource-status fallback';
      badge.innerHTML = `<span class="status-dot"></span><div><strong>Estimate mode — NREL key not active</strong><small>Start the app with <code>py run.py</code> after placing your key in <code>.env</code>. The fallback yield remains visible under Advanced assumptions.</small></div>`;
    }
  } catch (err) {
    badge.className = 'resource-status fallback';
    badge.innerHTML = `<span class="status-dot"></span><div><strong>Could not verify PVWatts connection</strong><small>${escapeHtml(err.message)}. Building assessment can still use estimate mode.</small></div>`;
  }
}
window.addEventListener('load', checkSolarDataConnection);

function escapeHtml(value='') { return String(value).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }
const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
function barChart(rows, key='solar_kwh') {
  const max = Math.max(1, ...rows.map(r => Number(r[key]) || 0));
  return `<div class="chart-shell"><div class="bar-chart">${rows.map((r,i) => `<div class="bar" style="height:${Math.max(3,(Number(r[key])||0)/max*100)}%" data-month="${months[i]}" title="${months[i]}: ${fmt.format(r[key])} kWh"></div>`).join('')}</div></div>`;
}
function assumptionsTable(rows=[]) {
  return `<div class="table-wrap"><table><thead><tr><th>Variable</th><th>Value</th><th>Source</th><th>Confidence</th><th>Owner</th></tr></thead><tbody>${rows.map(r => `<tr><td><strong>${escapeHtml(r.variable)}</strong></td><td>${escapeHtml(r.value)}</td><td>${escapeHtml(r.source)}</td><td>${escapeHtml(r.confidence)}</td><td>${escapeHtml(r.owner)}</td></tr>`).join('')}</tbody></table></div>`;
}

$('#building-form')?.addEventListener('submit', async e => {
  e.preventDefault(); updateQuickDerivedInputs();
  const target = $('#building-results'); loading(target);
  try {
    const payload = formToObject(e.currentTarget);
    const data = await postJSON('/api/building/calculate', payload);
    renderBuilding(data, payload, target);
  } catch (err) {
    target.innerHTML = `<div class="error-card"><strong>Could not run the Building Passport.</strong><br>${escapeHtml(err.message)}</div>`;
  }
});

function renderBuilding(data, payload, target) {
  const r = data.recommendation.selected;
  const ready = data.readiness;
  setTopStatus('building-status-top', `${ready.score}/100 · ${ready.status}`);
  const payback = r.simple_payback_years == null ? 'Beyond model' : `${r.simple_payback_years.toFixed(1)} yr`;
  const irr = r.project_irr_pct == null ? 'n/a' : `${r.project_irr_pct.toFixed(1)}%`;
  const sourceGood = String(r.generation_source).includes('NREL PVWatts');
  const paymentView = payload.payment_view || 'compare';
  const financedCard = paymentView === 'cash' ? '' : `<div class="metric"><span class="label">Financed monthly position</span><strong>${money2.format(r.first_year_net_monthly_cash)}</strong><small>After estimated loan payment and first-year maintenance</small></div>`;

  target.innerHTML = `
    <div class="decision-card">
      <p class="eyebrow">YOUR BUILDING DECISION</p>
      <div class="decision-row"><div><h3>${escapeHtml(ready.status)}</h3><p>${escapeHtml(payload.site_name || 'Building')} · Solar Passport recommends approximately <strong>${fmt.format(r.capacity_kwp)} kWp</strong> under the financial-return screen, then shows the alternative sizing cases below.</p></div><div class="score-ring">${ready.score}</div></div>
    </div>
    <div class="result-source"><span class="source-pill ${sourceGood?'good':'warn'}">${sourceGood?'● NREL PVWatts v8':'● Estimate mode'}</span><span class="source-pill">${escapeHtml(r.generation_confidence)} confidence</span></div>
    ${sourceGood ? '' : `<div class="explainer"><strong>Solar-generation limitation:</strong> this run used the fallback specific-yield assumption because PVWatts was not active. Configure the API or replace the fallback with a validated resource study before relying on the generation estimate for investment approval.</div>`}
    <div class="metric-grid simple-metric-grid">
      <div class="metric"><span class="label">Recommended solar size</span><strong>${fmt.format(r.capacity_kwp)} kWp</strong><small>Physical roof maximum: ${fmt.format(data.recommendation.max_roof_kwp)} kWp</small></div>
      <div class="metric"><span class="label">Estimated installed cost</span><strong>${money.format(r.capex)}</strong><small>Uses the cost assumption under Advanced assumptions</small></div>
      <div class="metric"><span class="label">Year-1 bill saving</span><strong>${money.format(r.year1_saving)}</strong><small>Bill ${money.format(r.bill_before)} → ${money.format(r.bill_after)}</small></div>
      <div class="metric"><span class="label">Payback</span><strong>${payback}</strong><small>Includes modelled maintenance and inverter replacement</small></div>
      <div class="metric"><span class="label">Investment return (IRR)</span><strong>${irr}</strong><small>25-year simplified project cash-flow measure</small></div>
      <div class="metric"><span class="label">Solar used in the building</span><strong>${r.self_consumption_pct.toFixed(1)}%</strong><small>${fmt.format(r.export_kwh)} kWh/yr estimated excess sent to grid</small></div>
      ${financedCard}
    </div>
    <div class="panel-card"><h4>Why this size?</h4><p class="muted">Solar Passport automatically tests several questions. The largest roof system is often different from the financially preferred system.</p>
      <div class="scenario-grid">
        <div class="scenario"><span>What physically fits?</span><strong>${fmt.format(data.recommendation.max_roof_kwp)} kWp</strong><small>Maximum roof capacity.</small></div>
        <div class="scenario"><span>Offset annual electricity?</span><strong>${fmt.format(data.recommendation.max_bill_offset_kwp)} kWp</strong><small>Approximate annual bill/load offset size.</small></div>
        <div class="scenario"><span>Keep solar mostly on-site?</span><strong>${fmt.format(data.recommendation.self_consumption_kwp)} kWp</strong><small>Reduces low-value excess export.</small></div>
        <div class="scenario recommended"><span>Best percentage return</span><strong>${fmt.format(data.recommendation.financial_return_kwp)} kWp</strong><small>Current default recommendation.</small></div>
        <div class="scenario"><span>Highest total value</span><strong>${fmt.format(data.recommendation.maximum_npv_kwp)} kWp</strong><small>Maximises modelled NPV.</small></div>
        <div class="scenario"><span>Best financed cash flow</span><strong>${fmt.format(data.recommendation.cash_flow_kwp)} kWp</strong><small>Maximises first-year monthly cash position.</small></div>
      </div>
    </div>
    <div class="panel-card"><h4>What is driving the decision?</h4><ul class="driver-list">${(data.decision_reasons||[]).map(x=>`<li>${escapeHtml(x)}</li>`).join('')}</ul></div>
    <div class="panel-card"><h4>Monthly solar production</h4>${barChart(r.monthly)}<div class="table-wrap"><table><thead><tr><th>Month</th><th>Building use</th><th>Solar</th><th>Used on-site</th><th>Export</th><th>Grid import</th><th>Bill before</th><th>Bill after</th></tr></thead><tbody>${r.monthly.map((m,i)=>`<tr><td>${months[i]}</td><td>${fmt.format(m.load_kwh)}</td><td>${fmt.format(m.solar_kwh)}</td><td>${fmt.format(m.self_consumed_kwh)}</td><td>${fmt.format(m.export_kwh)}</td><td>${fmt.format(m.grid_import_kwh)}</td><td>${money2.format(m.bill_before)}</td><td>${money2.format(m.bill_after)}</td></tr>`).join('')}</tbody></table></div></div>
    <div class="panel-card"><h4>Assumptions &amp; evidence</h4><p class="muted">Treat this section as the audit trail. Replace estimates and benchmarks as actual bills, quotations, engineering studies and official rules become available.</p>${assumptionsTable(data.assumptions)}</div>
  `;
}

$('#project-form')?.addEventListener('submit', async e => {
  e.preventDefault();
  const target = $('#project-results'); loading(target);
  try {
    const payload = formToObject(e.currentTarget);
    const data = await postJSON('/api/project/calculate', payload);
    renderProject(data, payload, target);
  } catch (err) {
    target.innerHTML = `<div class="error-card"><strong>Could not run the Project Passport.</strong><br>${escapeHtml(err.message)}</div>`;
  }
});
function tariffText(x) { return x == null ? 'n/a' : `${(Number(x)*100).toFixed(2)}¢`; }
function renderProject(data, payload, target) {
  const t=data.tested, s=data.tariff_solver, ready=data.readiness;
  setTopStatus('project-status-top', `${ready.score}/100 · ${ready.status}`);
  const atFloor = s.developer_floor != null && t.ppa_tariff >= s.developer_floor;
  const decision = atFloor ? ready.status : 'AMBER — TARIFF / COST GAP';
  const gap = s.developer_floor == null ? null : s.developer_floor - t.ppa_tariff;
  target.innerHTML = `
    <div class="decision-card"><p class="eyebrow">BANKABILITY DECISION</p><div class="decision-row"><div><h3>${escapeHtml(decision)}</h3><p>${escapeHtml(payload.project_name||'Solar project')} · Tested at ${tariffText(t.ppa_tariff)}/kWh. ${gap>0?`Modelled developer floor is ${(gap*100).toFixed(2)}¢/kWh higher.`:'Tested tariff clears the modelled developer floor.'}</p></div><div class="score-ring">${ready.score}</div></div></div>
    <div class="metric-grid">
      <div class="metric"><span class="label">Equity IRR</span><strong>${t.equity_irr_pct==null?'n/a':t.equity_irr_pct.toFixed(1)+'%'}</strong><small>Target ${payload.target_equity_irr_pct}%</small></div>
      <div class="metric"><span class="label">Minimum P90 DSCR</span><strong>${t.min_p90_dscr==null?'n/a':t.min_p90_dscr.toFixed(2)+'×'}</strong><small>Minimum ${Number(payload.min_dscr).toFixed(2)}×</small></div>
      <div class="metric"><span class="label">Project NPV</span><strong>${money.format(t.npv)}</strong><small>Discounted project cash flow</small></div>
      <div class="metric"><span class="label">LCOE</span><strong>${t.lcoe==null?'n/a':tariffText(t.lcoe)}</strong><small>Simplified lifecycle cost</small></div>
      <div class="metric"><span class="label">Total CAPEX</span><strong>${money.format(t.total_capex)}</strong><small>${money.format(payload.capex_per_mw)} / MWac</small></div>
      <div class="metric"><span class="label">Year-1 energy sold</span><strong>${fmt.format(t.year1_energy_mwh)} MWh</strong><small>After modelled losses</small></div>
      <div class="metric"><span class="label">Year-1 revenue</span><strong>${money.format(t.year1_revenue)}</strong><small>At tested PPA</small></div>
      <div class="metric"><span class="label">Annual debt service</span><strong>${money.format(t.annual_debt_service)}</strong><small>Level-debt MVP assumption</small></div>
    </div>
    <div class="panel-card"><h4>Tariff required by each constraint</h4><div class="scenario-grid"><div class="scenario"><span>Target equity IRR</span><strong>${tariffText(s.for_target_equity_irr)}</strong></div><div class="scenario"><span>P90 lender DSCR</span><strong>${tariffText(s.for_min_p90_dscr)}</strong></div><div class="scenario"><span>Zero project NPV</span><strong>${tariffText(s.for_zero_project_npv)}</strong></div><div class="scenario recommended"><span>Developer floor</span><strong>${tariffText(s.developer_floor)}</strong><small>Binding: ${escapeHtml(s.binding_constraint||'n/a')}</small></div><div class="scenario"><span>Offtaker ceiling</span><strong>${tariffText(s.offtaker_ceiling)}</strong></div><div class="scenario"><span>Bankability corridor</span><strong>${s.corridor_exists?'Exists':'No corridor'}</strong></div></div></div>
    <div class="panel-card"><h4>Recommended intervention</h4><ul class="driver-list">${(data.interventions||[]).map(x=>`<li>${escapeHtml(x)}</li>`).join('')}</ul></div>
    <div class="panel-card"><h4>CAPEX × tariff sensitivity</h4><div class="table-wrap"><table class="matrix-table"><thead><tr><th>CAPEX / MW</th>${data.sensitivity.tariffs.map(x=>`<th>${tariffText(x)}</th>`).join('')}</tr></thead><tbody>${data.sensitivity.matrix.map(row=>`<tr><th>${money.format(row.capex_per_mw)}</th>${row.cells.map(cell=>{const passIrr=cell.equity_irr_pct!=null&&cell.equity_irr_pct>=payload.target_equity_irr_pct; const passDscr=cell.p90_dscr!=null&&cell.p90_dscr>=payload.min_dscr; const klass=passIrr&&passDscr?'pass':(passIrr||passDscr?'near':'fail'); return `<td class="matrix-cell ${klass}"><strong>${cell.equity_irr_pct==null?'n/a':cell.equity_irr_pct.toFixed(1)+'%'}</strong><small>${cell.p90_dscr==null?'n/a':cell.p90_dscr.toFixed(2)+'×'}</small></td>`;}).join('')}</tr>`).join('')}</tbody></table></div></div>
    <div class="panel-card"><h4>Assumptions register</h4>${assumptionsTable(data.assumptions)}</div>`;
}
