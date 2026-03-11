async function postJSON(url, data) {
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return resp.json();
}

async function fetchJSON(url) {
  const resp = await fetch(url);
  return resp.json();
}

function renderJob(job) {
  const container = document.createElement('div');
  container.className = 'job-card';
  container.innerHTML = `
    <div><strong>Job:</strong> ${job.job_id}</div>
    <div class="muted">${job.current_stage || 'queued'}</div>
    <div class="progress"><span style="width:${job.progress || 0}%"></span></div>
  `;
  return container;
}

async function pollJob(jobId, slot) {
  const interval = setInterval(async () => {
    const data = await fetchJSON(`/api/status/${jobId}`);
    slot.innerHTML = '';
    slot.appendChild(renderJob(data));
    if (data.status === 'done' || data.status === 'failed' || data.status === 'skipped') {
      clearInterval(interval);
    }
  }, 2000);
}

document.getElementById('yt-submit').addEventListener('click', async () => {
  const urls = document.getElementById('yt-urls').value.split('\n').map(u => u.trim()).filter(Boolean);
  const author = document.getElementById('yt-author').value;
  const authorId = document.getElementById('yt-author-id').value;
  const jobs = document.getElementById('yt-jobs');
  jobs.innerHTML = '';

  for (const url of urls) {
    const job = await postJSON('/api/ingest/youtube', { url, author, author_id: authorId });
    const slot = document.createElement('div');
    jobs.appendChild(slot);
    slot.appendChild(renderJob(job));
    pollJob(job.job_id, slot);
  }
});
