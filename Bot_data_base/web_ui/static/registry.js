async function fetchJSON(url, options = undefined) {
  const resp = await fetch(url, options);
  let payload = {};
  try {
    payload = await resp.json();
  } catch (_err) {
    payload = {};
  }
  if (!resp.ok) {
    const message = payload?.detail || payload?.message || `HTTP ${resp.status}`;
    throw new Error(String(message));
  }
  return payload;
}

function resolveDeleteState(source) {
  const policy = source.delete_policy || {};
  const state = String(policy.state || '').trim();
  const reason = String(policy.reason || '').trim();
  if (state === 'protected') {
    return { label: 'Защищено', disabled: true, reason: reason || 'Основной источник базы', className: 'btn secondary' };
  }
  if (state === 'delete') {
    return { label: 'Удалить', disabled: false, reason: reason || 'Можно удалить безопасно', className: 'btn secondary' };
  }
  if (state === 'cleanup_test') {
    return { label: 'Очистить тестовый', disabled: false, reason: reason || 'Тестовый источник', className: 'btn secondary' };
  }
  if (state === 'archive') {
    return { label: 'Архив', disabled: true, reason: reason || 'Архивный источник', className: 'btn secondary' };
  }
  return { label: 'Недоступно', disabled: true, reason: reason || 'Удаление недоступно по политике', className: 'btn secondary' };
}

async function loadRegistry() {
  const data = await fetchJSON('/api/registry/');
  const body = document.getElementById('registry-body');
  body.innerHTML = '';

  (data.sources || []).forEach((s) => {
    const hygieneReason = Array.isArray(s.hygiene_reason) ? s.hygiene_reason.join(', ') : '';
    const deleteState = resolveDeleteState(s);
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${s.source_type || ''}</td>
      <td>${s.author || ''}</td>
      <td>${s.title || s.source_id}</td>
      <td>${s.language || ''}</td>
      <td>${s.blocks_count ?? 0}</td>
      <td><strong>${s.recommended_hygiene_action || 'manual_review'}</strong><br><span class="muted">${hygieneReason}</span></td>
      <td>${s.status || ''}</td>
      <td>${s.added_at || ''}</td>
      <td>
        <button class="${deleteState.className}" data-id="${s.source_id}" ${deleteState.disabled ? 'disabled' : ''}>${deleteState.label}</button>
        <br><span class="muted">${deleteState.reason}</span>
      </td>
    `;
    body.appendChild(row);
  });

  body.querySelectorAll('button[data-id]:not([disabled])').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const id = btn.getAttribute('data-id');
      if (!id) return;
      try {
        const payload = await fetchJSON(`/api/registry/${encodeURIComponent(id)}`, { method: 'DELETE' });
        alert(payload.message || 'Источник удален');
      } catch (err) {
        alert(String(err?.message || 'Удаление отклонено политикой гигиены'));
      }
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
