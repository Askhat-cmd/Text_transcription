async function fetchJSON(url) {
  const resp = await fetch(url);
  return resp.json();
}

async function loadRegistry() {
  const data = await fetchJSON('/api/registry/');
  const body = document.getElementById('registry-body');
  body.innerHTML = '';
  (data.sources || []).forEach((s) => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${s.source_type}</td>
      <td>${s.author}</td>
      <td>${s.title || s.source_id}</td>
      <td>${s.language || ''}</td>
      <td>${s.blocks_count ?? 0}</td>
      <td>${JSON.stringify(s.sd_distribution || {})}</td>
      <td>${s.status}</td>
      <td>${s.added_at}</td>
      <td><button class="btn secondary" data-id="${s.source_id}">Удалить</button></td>
    `;
    body.appendChild(row);
  });

  body.querySelectorAll('button[data-id]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const id = btn.getAttribute('data-id');
      await fetch(`/api/registry/${id}`, { method: 'DELETE' });
      await loadRegistry();
    });
  });

  const stats = await fetchJSON('/api/registry/stats');
  document.getElementById('registry-stats').textContent = `Всего источников: ${stats.total_sources}, блоков: ${stats.total_blocks}, ChromaDB: ${stats.chroma_total}`;
}


document.getElementById('export-merged').addEventListener('click', async () => {
  const resp = await fetchJSON('/api/registry/export/merged');
  alert(`Создан файл: ${resp.path}`);
});

loadRegistry();
