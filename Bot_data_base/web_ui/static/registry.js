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

function setText(id, value) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = value;
}

function showRegistryError(message) {
  const el = document.getElementById('registry-errors');
  if (!el) return;
  const text = String(message || '').trim();
  if (!text) {
    el.style.display = 'none';
    el.textContent = '';
    return;
  }
  el.textContent = `Ошибка загрузки реестра: ${text}`;
  el.style.display = 'block';
}

function setRegistryStatus(message) {
  setText('registry-status', message || '');
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

function renderRows(sources) {
  const body = document.getElementById('registry-body');
  body.innerHTML = '';

  (sources || []).forEach((source) => {
    const hygieneReason = Array.isArray(source.hygiene_reason) ? source.hygiene_reason.join(', ') : '';
    const deleteState = resolveDeleteState(source);
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${source.source_type || ''}</td>
      <td>${source.author || ''}</td>
      <td>${source.title || source.source_id}</td>
      <td>${source.language || ''}</td>
      <td>${source.blocks_count ?? 0}</td>
      <td><strong>${source.recommended_hygiene_action || 'manual_review'}</strong><br><span class="muted">${hygieneReason}</span></td>
      <td>${source.status || ''}</td>
      <td>${source.added_at || ''}</td>
      <td>
        <button class="${deleteState.className}" data-id="${source.source_id}" ${deleteState.disabled ? 'disabled' : ''}>${deleteState.label}</button>
        <br><span class="muted">${deleteState.reason}</span>
      </td>
    `;
    body.appendChild(row);
  });
}

function bindDeleteHandlers() {
  const body = document.getElementById('registry-body');
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
}

async function loadRegistry() {
  const body = document.getElementById('registry-body');
  body.innerHTML = '';
  setRegistryStatus('Загрузка реестра...');
  showRegistryError('');

  try {
    const data = await fetchJSON('/api/registry/');
    const sources = Array.isArray(data.sources) ? data.sources : [];
    const policyWarnings = Array.isArray(data.warnings)
      ? data.warnings.filter((item) => String(item || '').includes('row_policy_error:'))
      : [];

    if (sources.length === 0) {
      setRegistryStatus('Источники не найдены');
    } else {
      setRegistryStatus(`Загружено источников: ${sources.length}`);
    }

    renderRows(sources);
    bindDeleteHandlers();

    if (policyWarnings.length > 0) {
      showRegistryError(`Ошибки политики на строках: ${policyWarnings.length}`);
    }

    const stats = await fetchJSON('/api/registry/stats');
    setText(
      'registry-stats',
      `Всего источников: ${stats.total_sources}, блоков: ${stats.total_blocks}, ChromaDB: ${stats.chroma_total}`,
    );
  } catch (err) {
    setRegistryStatus('Реестр не загружен');
    setText('registry-stats', '');
    showRegistryError(String(err?.message || err || 'unknown_error'));
  }
}

document.getElementById('export-merged').addEventListener('click', async () => {
  try {
    const resp = await fetchJSON('/api/registry/export/merged');
    alert(`Создан файл: ${resp.path}`);
  } catch (err) {
    showRegistryError(String(err?.message || err || 'unknown_error'));
  }
});

loadRegistry();
