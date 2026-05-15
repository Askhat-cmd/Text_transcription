async function fetchJSON(url) {
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status}: ${url}`);
  }
  return resp.json();
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = value;
}

function renderGovernanceReadiness(governance) {
  const container = document.getElementById('governance-readiness');
  if (!container) return;
  container.innerHTML = '';

  const readiness = String(governance?.readiness || 'unknown');
  const rates = [
    ['governance', Number(governance?.governance_present_rate || 0)],
    ['allowed_use', Number(governance?.allowed_use_present_rate || 0)],
    ['safety_flags', Number(governance?.safety_flags_present_rate || 0)],
  ];

  const statusRow = document.createElement('div');
  statusRow.className = 'sd-bar';
  statusRow.innerHTML = `<strong>status</strong>`;
  const statusLabel = document.createElement('span');
  statusLabel.style.width = `${readiness === 'ready' ? 100 : 35}px`;
  statusRow.appendChild(statusLabel);
  statusRow.appendChild(document.createTextNode(readiness));
  container.appendChild(statusRow);

  rates.forEach(([label, rate]) => {
    const row = document.createElement('div');
    row.className = 'sd-bar';
    row.innerHTML = `<strong>${label}</strong>`;
    const bar = document.createElement('span');
    bar.style.width = `${Math.min(100, Math.round(rate * 100))}px`;
    row.appendChild(bar);
    row.appendChild(document.createTextNode(`${Math.round(rate * 100)}%`));
    container.appendChild(row);
  });

  if (governance?.legacy_sd_active) {
    const row = document.createElement('div');
    row.className = 'sd-bar';
    row.innerHTML = '<strong>legacy_sd</strong>';
    const bar = document.createElement('span');
    bar.style.width = '100px';
    row.appendChild(bar);
    row.appendChild(document.createTextNode('active'));
    container.appendChild(row);
  }
}

function renderRecentSources(items) {
  const list = document.getElementById('recent-list');
  if (!list) return;
  list.innerHTML = '';

  if (!Array.isArray(items) || items.length === 0) {
    const li = document.createElement('li');
    li.className = 'muted';
    li.textContent = 'Нет данных по источникам';
    list.appendChild(li);
    return;
  }

  items.forEach((s) => {
    const title = s.title || s.source_id || 'unknown';
    const status = s.status || 'unknown';
    const blocks = Number(s.blocks || 0);
    const protection = s.protected ? 'protected' : (s.hygiene_action || 'manual_review');
    const li = document.createElement('li');
    li.innerHTML = `<strong>${title}</strong> · <span class="muted">${status}</span> · blocks: ${blocks} · ${protection}`;
    list.appendChild(li);
  });
}

function renderWarnings(warnings) {
  const section = document.getElementById('dashboard-errors');
  const list = document.getElementById('dashboard-errors-list');
  if (!section || !list) return;

  list.innerHTML = '';
  const normalized = Array.isArray(warnings) ? warnings.filter(Boolean) : [];
  if (!normalized.length) {
    section.style.display = 'none';
    return;
  }

  normalized.forEach((w) => {
    const li = document.createElement('li');
    li.textContent = String(w);
    list.appendChild(li);
  });
  section.style.display = 'block';
}

function renderUnavailable(reason) {
  setText('stat-sources', '—');
  setText('stat-blocks', '—');
  setText('stat-chroma', '—');
  setText('stat-enrichment', '—');
  setText('stat-sources-meta', reason);
  setText('stat-blocks-meta', reason);
  setText('stat-chroma-meta', reason);
  setText('stat-enrichment-meta', reason);
  renderGovernanceReadiness({ readiness: 'unknown' });
  renderWarnings([reason]);
  renderRecentSources([]);
}

async function loadDashboard() {
  try {
    const summary = await fetchJSON('/api/dashboard/');

    const sources = summary.sources || {};
    const blocks = summary.blocks || {};
    const chroma = summary.chroma || {};
    const enrichment = summary.enrichment || {};

    setText('stat-sources', String(sources.total ?? 0));
    setText('stat-sources-meta', `active: ${sources.active ?? 0}, protected: ${sources.protected ?? 0}`);

    setText('stat-blocks', String(blocks.production_total ?? 0));
    setText('stat-blocks-meta', `active source blocks: ${blocks.active_source_blocks ?? 0}`);

    setText('stat-chroma', String(chroma.count ?? 0));
    setText('stat-chroma-meta', `status: ${chroma.status || 'unknown'}`);

    const reviewItems = Number(enrichment.review_queue_items_count || 0);
    const provider = enrichment.provider_status || 'unknown';
    setText('stat-enrichment', `${reviewItems}`);
    setText(
      'stat-enrichment-meta',
      `provider: ${provider}, completed: ${enrichment.items_completed ?? 0}, P0/P1/P2: ${enrichment.p0 ?? 0}/${enrichment.p1 ?? 0}/${enrichment.p2 ?? 0}`
    );

    renderGovernanceReadiness(summary.governance || {});
    renderRecentSources(summary.recent_sources || []);

    const warnings = Array.isArray(summary.warnings) ? [...summary.warnings] : [];
    if ((summary.chroma || {}).status !== 'ok') {
      warnings.push('Chroma unavailable');
    }
    renderWarnings(warnings);
  } catch (err) {
    console.error(err);
    renderUnavailable('API unavailable');
  }
}

loadDashboard();
