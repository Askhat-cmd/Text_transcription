async function postForm(url, formData) {
  const resp = await fetch(url, {
    method: 'POST',
    body: formData,
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

const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('book-file');
const dropLabel = document.getElementById('drop-label');

function setFileLabel(file) {
  dropLabel.textContent = file ? file.name : 'Перетащите файл сюда или кликните для выбора';
}

dropZone.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', (e) => {
  const file = e.target.files[0];
  setFileLabel(file);
});

dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('active');
});

dropZone.addEventListener('dragleave', () => dropZone.classList.remove('active'));

dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('active');
  const file = e.dataTransfer.files[0];
  if (file) {
    fileInput.files = e.dataTransfer.files;
    setFileLabel(file);
  }
});

document.getElementById('book-submit').addEventListener('click', async () => {
  const file = fileInput.files[0];
  if (!file) return;

  const form = new FormData();
  form.append('file', file);
  form.append('author', document.getElementById('book-author').value);
  form.append('author_id', document.getElementById('book-author-id').value);
  form.append('book_title', document.getElementById('book-title').value);
  form.append('language', document.getElementById('book-lang').value);

  const slot = document.getElementById('book-job');
  const job = await postForm('/api/ingest/book', form);
  slot.innerHTML = '';
  slot.appendChild(renderJob(job));
  pollJob(job.job_id, slot);
});

