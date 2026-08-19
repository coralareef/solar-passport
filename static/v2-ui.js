(() => {
  const $ = (sel, root=document) => root.querySelector(sel);
  const fmt = new Intl.NumberFormat('en-BN', { maximumFractionDigits: 1 });
  const money0 = new Intl.NumberFormat('en-BN', { style:'currency', currency:'BND', maximumFractionDigits:0 });

  function esc(value='') {
    return String(value).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  }
  function tariffText(x) { return x == null ? 'n/a' : `${(Number(x)*100).toFixed(2)}¢`; }
  function compactMoney(value) {
    const n = Number(value) || 0;
    const abs = Math.abs(n);
    if (abs >= 1e9) return `BND ${(n/1e9).toLocaleString('en-BN',{maximumFractionDigits:2})}b`;
    if (abs >= 1e6) return `BND ${(n/1e6).toLocaleString('en-BN',{maximumFractionDigits:2})}m`;
    if (abs >= 1e3) return `BND ${(n/1e3).toLocaleString('en-BN',{maximumFractionDigits:1})}k`;
    return money0.format(n);
  }

  function installSingleElectricityInput() {
    const form = $('#building-form');
    if (!form || $('#electricity-input-mode')) return;

    const billInput = form.elements.monthly_bill;
    const kwhInput = form.elements.monthly_kwh;
    const tariffSelect = form.elements.customer_tariff_choice;
    if (!billInput || !kwhInput || !tariffSelect) return;

    const billLabel = billInput.closest('label');
    const kwhLabel = kwhInput.closest('label');
    const grid = billLabel?.parentElement;
    const tariffLabel = tariffSelect.closest('label');
    if (!grid || !tariffLabel) return;

    const modeLabel = document.createElement('label');
    modeLabel.className = 'choice-label';
    modeLabel.innerHTML = `
      What number do you know?
      <select name="electricity_input_mode" id="electricity-input-mode">
        <option value="kwh" selected>I know my monthly electricity use (kWh)</option>
        <option value="bill">I know my monthly electricity bill (BND)</option>
      </select>
      <small>Enter one. Solar Passport calculates the other from the selected Brunei tariff.</small>
    `;
    grid.parentNode.insertBefore(modeLabel, grid);

    const kvaLabel = document.createElement('label');
    kvaLabel.id = 'commercial-kva-field';
    kvaLabel.innerHTML = `
      Subscribed capacity (kVA)
      <input type="number" name="subscribed_kva" min="0" step="any" placeholder="e.g. 140" />
      <small>Commercial Tariff B uses both monthly kWh and subscribed kVA. This value is normally shown on the electricity account/bill.</small>
    `;
    tariffLabel.insertAdjacentElement('afterend', kvaLabel);

    billLabel.id = 'monthly-bill-field';
    kwhLabel.id = 'monthly-kwh-field';
    grid.classList.add('single-energy-grid');

    const note = $('#effective-rate-note');
    const mode = $('#electricity-input-mode');

    function sync() {
      const isBill = mode.value === 'bill';
      const commercial = tariffSelect.value === 'business' || tariffSelect.value === 'commercial';
      billLabel.style.display = isBill ? 'grid' : 'none';
      kwhLabel.style.display = isBill ? 'none' : 'grid';
      grid.style.gridTemplateColumns = '1fr';
      kvaLabel.style.display = commercial ? 'grid' : 'none';

      if (note) {
        if (commercial) {
          note.innerHTML = `<strong>Commercial Tariff B:</strong> Solar Passport applies the DES kVA-based blocks. You only enter ${isBill ? 'your monthly bill' : 'your monthly kWh'} plus subscribed capacity (kVA).`;
        } else {
          note.innerHTML = `<strong>Residential Tariff A:</strong> Solar Passport applies the DES residential blocks automatically. You only enter ${isBill ? 'your monthly bill' : 'your monthly kWh'}.`;
        }
      }
    }

    mode.addEventListener('change', sync);
    tariffSelect.addEventListener('change', sync);
    form.addEventListener('input', e => {
      if (e.target === billInput || e.target === kwhInput) setTimeout(sync, 0);
    });
    sync();
  }

  function installProjectReadinessInputs() {
    const box = $('#project-form .compact-sliders');
    if (!box || $('#project-financing-readiness')) return;
    const financing = document.createElement('label');
    financing.id = 'project-financing-readiness';
    financing.innerHTML = `Financing readiness <span class="range-value">65</span><input type="range" name="financing_score" value="65" min="0" max="100" />`;
    const resource = document.createElement('label');
    resource.id = 'project-resource-readiness';
    resource.innerHTML = `Solar-resource evidence <span class="range-value">70</span><input type="range" name="resource_score" value="70" min="0" max="100" />`;
    box.insertBefore(financing, box.firstChild);
    box.insertBefore(resource, financing.nextSibling);
    [financing, resource].forEach(label => {
      const input = label.querySelector('input');
      const output = label.querySelector('.range-value');
      input.addEventListener('input', () => output.textContent = input.value);
    });
  }

  function installProjectRenderer() {
    if (typeof window.renderProject !== 'function') return;

    window.renderProject = function(data, payload, target) {
      const t = data.tested || {};
      const s = data.tariff_solver || {};
      const econ = data.economics || {};
      const ready = data.readiness || {};
      const overall = data.overall_status || ready.status || 'Assessment complete';
      const readinessOnly = ready.readiness_status || ready.status || 'n/a';
      const score = Number(ready.score) || 0;
      const statusEl = $('#project-status-top');
      if (statusEl) {
        statusEl.textContent = `${score}/100 readiness · ${overall}`;
        const upper = overall.toUpperCase();
        statusEl.className = `status-chip ${upper.includes('RED') ? 'bad' : upper.includes('GREEN') ? 'good' : 'warn'}`;
      }

      const gap = s.developer_floor == null ? null : Number(s.developer_floor) - Number(t.ppa_tariff);
      const corridor = s.corridor_exists == null ? 'Not tested' : (s.corridor_exists ? 'Exists' : 'No corridor');
      const dscrText = econ.dscr_applicable === false
        ? 'Not applicable'
        : (t.min_p90_dscr == null ? 'n/a' : `${Number(t.min_p90_dscr).toFixed(2)}×`);
      const dscrNote = econ.dscr_applicable === false
        ? 'All-equity case — no debt service to cover'
        : `Minimum ${Number(payload.min_dscr || 0).toFixed(2)}×`;

      target.innerHTML = `
        <div class="decision-card">
          <p class="eyebrow">BANKABILITY DECISION</p>
          <div class="decision-row">
            <div>
              <h3>${esc(overall)}</h3>
              <p>${esc(payload.project_name || 'Solar project')} ·
                <strong>Economics: ${econ.pass ? 'PASS' : 'FAIL'}</strong> ·
                Readiness: ${score}/100.
                Tested at ${tariffText(t.ppa_tariff)}/kWh.
                ${gap != null && gap > 0 ? `Developer floor is ${(gap*100).toFixed(2)}¢/kWh higher.` :
                  s.developer_floor != null ? 'Tested tariff clears the modelled developer floor.' : ''}
              </p>
            </div>
            <div class="score-ring">${score}</div>
          </div>
        </div>

        <div class="result-source">
          <span class="source-pill ${econ.pass ? 'good' : 'warn'}">Economics ${econ.pass ? 'PASS' : 'FAIL'}</span>
          <span class="source-pill ${score >= 80 ? 'good' : 'warn'}">Readiness ${score}/100</span>
          <span class="source-pill">${esc(readinessOnly)}</span>
        </div>

        <div class="metric-grid">
          <div class="metric"><span class="label">Equity IRR</span><strong>${t.equity_irr_pct==null?'n/a':Number(t.equity_irr_pct).toFixed(1)+'%'}</strong><small>Target ${payload.target_equity_irr_pct}% · ${econ.equity_irr_pass?'Pass':'Fail'}</small></div>
          <div class="metric"><span class="label">Minimum P90 DSCR</span><strong>${dscrText}</strong><small>${dscrNote}</small></div>
          <div class="metric"><span class="label">Project NPV</span><strong>${compactMoney(t.npv)}</strong><small>${econ.npv_pass?'Positive / pass':'Negative / fail'}</small></div>
          <div class="metric"><span class="label">LCOE</span><strong>${t.lcoe==null?'n/a':tariffText(t.lcoe)}</strong><small>Simplified lifecycle cost</small></div>
          <div class="metric"><span class="label">Total CAPEX</span><strong>${compactMoney(t.total_capex)}</strong><small>${compactMoney(payload.capex_per_mw)} / MWac</small></div>
          <div class="metric"><span class="label">Year-1 energy sold</span><strong>${fmt.format(t.year1_energy_mwh)} MWh</strong><small>After modelled losses</small></div>
          <div class="metric"><span class="label">Year-1 revenue</span><strong>${compactMoney(t.year1_revenue)}</strong><small>At tested PPA tariff</small></div>
          <div class="metric"><span class="label">Annual debt service</span><strong>${compactMoney(t.annual_debt_service)}</strong><small>${econ.dscr_applicable===false?'No project debt':'Level-debt MVP assumption'}</small></div>
        </div>

        <div class="panel-card">
          <h4>Economics gate</h4>
          <p class="muted">A very high tariff can make the economics pass. It does not automatically make land, grid, PPA documentation, approvals or execution ready.</p>
          <div class="scenario-grid">
            <div class="scenario ${econ.equity_irr_pass?'recommended':''}"><span>Target equity IRR</span><strong>${tariffText(s.for_target_equity_irr)}</strong><small>${econ.equity_irr_pass?'Pass':'Gap remains'}</small></div>
            <div class="scenario ${econ.p90_dscr_pass?'recommended':''}"><span>P90 lender DSCR</span><strong>${econ.dscr_applicable===false?'N/A':tariffText(s.for_min_p90_dscr)}</strong><small>${econ.dscr_applicable===false?'No debt in this case':(econ.p90_dscr_pass?'Pass':'Gap remains')}</small></div>
            <div class="scenario ${econ.npv_pass?'recommended':''}"><span>Zero project NPV</span><strong>${tariffText(s.for_zero_project_npv)}</strong><small>${econ.npv_pass?'Pass':'Gap remains'}</small></div>
            <div class="scenario recommended"><span>Developer floor</span><strong>${tariffText(s.developer_floor)}</strong><small>Binding: ${esc(s.binding_constraint||'n/a')}</small></div>
            <div class="scenario"><span>Offtaker ceiling</span><strong>${tariffText(s.offtaker_ceiling)}</strong></div>
            <div class="scenario"><span>Bankability corridor</span><strong>${corridor}</strong></div>
          </div>
        </div>

        <div class="panel-card">
          <h4>Readiness — separate from economics</h4>
          <p class="muted">This score answers whether the project is developed enough to transact/implement. Moving the tariff alone should not change these items.</p>
          <div class="scenario-grid">
            ${(ready.blocks || []).map(b => `<div class="scenario"><span>${esc(b.name)}</span><strong>${Number(b.score).toFixed(0)}/100</strong><small>Weight ${b.weight}%</small></div>`).join('')}
          </div>
        </div>

        <div class="panel-card"><h4>Recommended intervention</h4><ul class="driver-list">${(data.interventions||[]).map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div>

        <div class="panel-card">
          <h4>CAPEX × tariff sensitivity</h4>
          <div class="table-wrap"><table class="matrix-table"><thead><tr><th>CAPEX / MW</th>${(data.sensitivity?.tariffs||[]).map(x=>`<th>${tariffText(x)}</th>`).join('')}</tr></thead><tbody>
          ${(data.sensitivity?.matrix||[]).map(row=>`<tr><th>${compactMoney(row.capex_per_mw)}</th>${row.cells.map(cell=>{
            const passIrr = cell.equity_irr_pct != null && cell.equity_irr_pct >= Number(payload.target_equity_irr_pct);
            const passDscr = cell.dscr_applicable === false || (cell.p90_dscr != null && cell.p90_dscr >= Number(payload.min_dscr));
            const klass = passIrr && passDscr ? 'pass' : (passIrr || passDscr ? 'near' : 'fail');
            return `<td class="matrix-cell ${klass}"><strong>${cell.equity_irr_pct==null?'n/a':Number(cell.equity_irr_pct).toFixed(1)+'%'}</strong><small>${cell.dscr_applicable===false?'No debt':(cell.p90_dscr==null?'n/a':Number(cell.p90_dscr).toFixed(2)+'×')}</small></td>`;
          }).join('')}</tr>`).join('')}
          </tbody></table></div>
        </div>

        <div class="panel-card"><h4>Assumptions register</h4>
          <div class="table-wrap"><table><thead><tr><th>Variable</th><th>Value</th><th>Source</th><th>Confidence</th><th>Owner</th></tr></thead>
          <tbody>${(data.assumptions||[]).map(r=>`<tr><td><strong>${esc(r.variable)}</strong></td><td>${esc(r.value)}</td><td>${esc(r.source)}</td><td>${esc(r.confidence)}</td><td>${esc(r.owner)}</td></tr>`).join('')}</tbody></table></div>
        </div>
      `;
    };
  }

  window.addEventListener('load', () => {
    installSingleElectricityInput();
    installProjectReadinessInputs();
    installProjectRenderer();
  });
})();