(() => {
  const $ = (sel, root=document) => root.querySelector(sel);

  // The first revision used a full Building Passport calculation as a connection
  // probe. Remove that load handler so page load makes only one small PVWatts test.
  if (typeof window.checkSolarDataConnection === 'function') {
    window.removeEventListener('load', window.checkSolarDataConnection);
  }

  function escapeHtml(value='') {
    return String(value).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  }

  async function fetchJSON(url) {
    const res = await fetch(url, { headers: { 'Accept': 'application/json' }, cache: 'no-store' });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || data.diagnostic || `Request failed: ${res.status}`);
    return data;
  }

  async function refreshPvwattsStatus() {
    const badge = $('#nrel-status');
    if (!badge) return;
    try {
      const data = await fetchJSON('/api/pvwatts/status');
      if (data.connected) {
        const weather = data.station?.weather_data_source ? ` Weather source: ${escapeHtml(data.station.weather_data_source)}.` : '';
        badge.className = 'resource-status connected';
        badge.innerHTML = `<span class="status-dot"></span><div><strong>NREL PVWatts v8 connected</strong><small>Live 4 kW API probe succeeded.${weather}</small></div>`;
      } else {
        badge.className = 'resource-status fallback';
        badge.innerHTML = `<span class="status-dot"></span><div><strong>Estimate mode — PVWatts probe failed</strong><small>${escapeHtml(data.error || 'Unknown PVWatts error')}. The same diagnostic is printed in Command Prompt.</small></div>`;
      }
    } catch (err) {
      badge.className = 'resource-status fallback';
      badge.innerHTML = `<span class="status-dot"></span><div><strong>Could not test PVWatts</strong><small>${escapeHtml(err.message)}</small></div>`;
    }
  }

  function installLocationSearch() {
    const mapShell = $('.map-shell');
    const mapDiv = $('#roof-map');
    if (!mapShell || !mapDiv || $('#roof-location-search')) return;

    const wrap = document.createElement('div');
    wrap.className = 'location-search';
    wrap.innerHTML = `
      <div class="location-search-row">
        <input id="roof-location-search" type="search" autocomplete="off" placeholder="Search Brunei road, kampong, landmark or building…" aria-label="Search roof location" />
        <button type="button" class="btn btn-ink" id="roof-location-search-btn">Search</button>
      </div>
      <div class="location-search-note">You can also paste coordinates, e.g. <strong>4.9031, 114.9398</strong>.</div>
      <div class="location-search-results" id="roof-location-results" aria-live="polite"></div>
    `;
    mapShell.parentNode.insertBefore(wrap, mapShell);

    const input = $('#roof-location-search');
    const button = $('#roof-location-search-btn');
    const results = $('#roof-location-results');

    async function search() {
      const q = input.value.trim();
      if (q.length < 2) {
        results.innerHTML = '<div class="location-search-note">Enter at least 2 characters.</div>';
        return;
      }
      button.disabled = true;
      button.textContent = 'Searching…';
      results.innerHTML = '';
      try {
        const data = await fetchJSON(`/api/geocode?q=${encodeURIComponent(q)}`);
        const items = data.results || [];
        if (!items.length) {
          const diag = data.diagnostic ? `<br><small>${escapeHtml(data.diagnostic)}</small>` : '';
          results.innerHTML = `<div class="location-search-note">No Brunei locations found. Try a road, kampong, landmark, district, or paste coordinates.${diag}</div>`;
          return;
        }
        const provider = data.provider ? `<div class="location-search-note">Search source: ${escapeHtml(data.provider)}</div>` : '';
        results.innerHTML = provider + items.map((item, i) => `
          <button type="button" class="location-result" data-i="${i}">
            <strong>${escapeHtml(item.display_name)}</strong>
            <small>${Number(item.lat).toFixed(5)}, ${Number(item.lon).toFixed(5)}</small>
          </button>
        `).join('');
        results.querySelectorAll('.location-result').forEach(el => el.addEventListener('click', () => {
          const item = items[Number(el.dataset.i)];
          const map = window.roofMap;
          if (map) {
            if (Array.isArray(item.boundingbox) && item.boundingbox.length === 4) {
              const [south, north, west, east] = item.boundingbox;
              map.fitBounds([[south, west], [north, east]], { maxZoom: 18 });
            } else {
              map.setView([item.lat, item.lon], 18);
            }
          }
          const lat = $('#building-lat');
          const lon = $('#building-lon');
          if (lat) lat.value = Number(item.lat).toFixed(5);
          if (lon) lon.value = Number(item.lon).toFixed(5);
          input.value = item.display_name;
          results.innerHTML = '<div class="location-search-note">Map moved to the selected location. Zoom in and trace the roof.</div>';
        }));
      } catch (err) {
        results.innerHTML = `<div class="location-search-note error">${escapeHtml(err.message)}. You can still paste latitude, longitude into the search box.</div>`;
      } finally {
        button.disabled = false;
        button.textContent = 'Search';
      }
    }

    button.addEventListener('click', search);
    input.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        e.preventDefault();
        search();
      }
    });
  }

  window.addEventListener('load', () => {
    refreshPvwattsStatus();
    installLocationSearch();
  });
})();
