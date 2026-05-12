async function fetchJSON(url) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error('request failed');
  return resp.json();
}

function renderGovernanceReadiness(readiness) {
  const container = document.getElementById('governance-readiness');
  if (!container) return;
  container.innerHTML = '';
  const entries = Object.entries(readiness || {});
  if (!entries.length) {
    container.innerHTML = '<div class="muted">Нет данных</div>';
    return;
  }
  entries.forEach(([label, count]) => {
    const row = document.createElement('div');
    row.className = 'sd-bar';
    const bar = document.createElement('span');
    bar.style.width = `${Math.min(100, Number(count || 0) * 10)}px`;
    row.innerHTML = `<strong>${label}</strong>`;
    row.appendChild(bar);
    row.appendChild(document.createTextNode(`${count}`));
    container.appendChild(row);
  });
}

async function loadDashboard() {
  try {
    const stats = await fetchJSON('/api/registry/stats');
    document.getElementById('stat-sources').textContent = stats.total_sources ?? 0;
    document.getElementById('stat-blocks').textContent = stats.total_blocks ?? 0;
    document.getElementById('stat-chroma').textContent = stats.chroma_total ?? 0;
    renderGovernanceReadiness(stats.governance_readiness);

    const reg = await fetchJSON('/api/registry/');
    const list = document.getElementById('recent-list');
    list.innerHTML = '';
    (reg.sources || []).slice(-5).reverse().forEach((s) => {
      const li = document.createElement('li');
      li.innerHTML = `<strong>${s.title || s.source_id}</strong> · ${s.author || ''} · <span class="muted">${s.status}</span>`;
      list.appendChild(li);
    });
  } catch (err) {
    console.error(err);
  }
}

loadDashboard();
