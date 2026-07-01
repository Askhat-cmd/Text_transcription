import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

import { chromium } from '../web_ui/node_modules/playwright/index.mjs';

const CONFIG_PATH = process.argv[2];

if (!CONFIG_PATH) {
  console.error('Usage: node prd_047_36_hf4_browser_check.mjs <config.json>');
  process.exit(2);
}

const config = JSON.parse(await readTextFile(CONFIG_PATH));

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function readTextFile(filePath) {
  const { readFile } = await import('node:fs/promises');
  return readFile(filePath, 'utf-8');
}

async function waitForCondition(fn, { timeoutMs = 90000, intervalMs = 500, label = 'condition' } = {}) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    const value = await fn();
    if (value) {
      return value;
    }
    await sleep(intervalMs);
  }
  throw new Error(`Timed out waiting for ${label}`);
}

async function countText(page, text) {
  return page.getByText(text, { exact: false }).count();
}

async function getStoredActiveChatId(page) {
  return page.evaluate(() => localStorage.getItem('bot_active_chat_id') || '');
}

async function captureState(page, label) {
  const screenshotPath = path.join(config.output_dir, `${label}.png`);
  await page.screenshot({ path: screenshotPath, fullPage: true });
  const pageText = await page.locator('body').innerText();
  return {
    label,
    screenshot_path: screenshotPath,
    pipeline_count: await countText(page, 'Pipeline NEO'),
    trace_unavailable_count: await countText(page, 'Trace unavailable'),
    has_requested_turn_missing: pageText.includes('requested_turn_missing'),
    has_trace_expired_reason: pageText.includes('debug_trace_expired_after_backend_restart'),
    active_chat_id: await getStoredActiveChatId(page),
    page_text_preview: pageText.slice(0, 4000),
  };
}

async function fetchSessions(userId, webSessionId) {
  const response = await fetch(
    `${config.backend_base_url.replace(/\/$/, '')}/api/v1/users/${encodeURIComponent(userId)}/sessions?limit=200`,
    {
      headers: {
        'X-API-Key': config.api_key,
        'X-Session-Id': webSessionId,
      },
    }
  );
  const payload = await response.json();
  return Array.isArray(payload.sessions) ? payload.sessions : [];
}

async function waitForReady(page) {
  const chatUrl = `${config.frontend_base_url.replace(/\/$/, '')}/chat`;
  await page.goto(chatUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.locator('textarea').first().waitFor({ timeout: 30000 });
  await waitForCondition(
    async () => (await fetchSessions(config.user_id, config.web_session_id)).length >= 1,
    { timeoutMs: 30000, intervalMs: 500, label: 'initial chat session created' }
  );
  await waitForCondition(async () => !(await page.getByText('РџРµСЂРµРґ РЅР°С‡Р°Р»РѕРј СЂР°Р±РѕС‚С‹ РЅСѓР¶РЅРѕ СѓРєР°Р·Р°С‚СЊ API key.', { exact: false }).isVisible().catch(() => false)), {
    timeoutMs: 15000,
    intervalMs: 300,
    label: 'chat ready without settings blocker',
  });
  await sleep(8000);
}

async function sendPrompt(page, prompt, expectedPipelineCount) {
  const textarea = page.locator('textarea').first();
  await waitForCondition(
    async () => await textarea.isEnabled(),
    { timeoutMs: 60000, intervalMs: 250, label: 'textarea enabled before send' }
  );
  await textarea.fill(prompt);
  await textarea.press('Enter');

  await waitForCondition(
    async () => (await countText(page, 'Pipeline NEO')) >= expectedPipelineCount,
    { timeoutMs: 180000, intervalMs: 500, label: `pipeline count ${expectedPipelineCount}` }
  );
  await waitForCondition(
    async () => (await page.locator('textarea').first().inputValue()) === '',
    { timeoutMs: 15000, intervalMs: 250, label: 'textarea clear after send' }
  );
  await waitForCondition(
    async () => await page.locator('textarea').first().isEnabled(),
    { timeoutMs: 120000, intervalMs: 500, label: 'textarea re-enabled after response' }
  );
}

async function runPreRestart(page) {
  const prompts = [
    'Р§С‚Рѕ С‚Р°РєРѕРµ РґСѓС€Р°? РЎСѓС‰РµСЃС‚РІСѓРµС‚ Р»Рё РѕРЅР° РёР»Рё СЌС‚Рѕ РєСѓР»СЊС‚СѓСЂРЅРѕ-С„РёР»РѕСЃРѕС„СЃРєР°СЏ РєРѕРЅСЃС‚СЂСѓРєС†РёСЏ?',
    'Р° С‡РµРј РѕС‚Р»РёС‡Р°РµС‚СЃСЏ РґСѓС€Р° РѕС‚ СЃРѕР·РЅР°РЅРёСЏ?',
    'РІ С‡РµРј СЃРјС‹СЃР» Р¶РёР·РЅРё! РєР°Рє С‚С‹ СЃС‡РёС‚Р°РµС€СЊ РµСЃС‚СЊ Р»Рё РѕРЅ РІРѕРѕР±С‰Рµ РіР»РѕР±Р°Р»СЊРЅРѕ?',
    'РЅР°РїСЂРёРјРµСЂ РјРѕСЏ СЃРµРјСЊСЏ, СЌС‚Рѕ СЃРјС‹СЃР» РґР»СЏ РјРµРЅСЏ РїСЂРµРѕРґРѕР»РµРІР°С‚СЊ С‚СЂСѓРґРЅРѕСЃС‚Рё',
    'СЃРєР°Р¶Рё Р° С‡С‚Рѕ РѕР± СЌС‚РѕРј РіРѕРІРѕСЂРёС‚СЃСЏ РІ РќРµР№СЂРѕСЃС‚Р°Р»РєРёРЅРіРµ?',
  ];

  for (let index = 0; index < prompts.length; index += 1) {
    await sendPrompt(page, prompts[index], 1);
  }

  const beforeReload = await captureState(page, 'fresh_chat_before_reload');
  const sessions = await fetchSessions(config.user_id, config.web_session_id);
  const primarySession = sessions[0] ?? null;

  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.locator('textarea').first().waitFor({ timeout: 30000 });
  await waitForCondition(
    async () => (await countText(page, 'Pipeline NEO')) >= 1,
    { timeoutMs: 90000, intervalMs: 500, label: 'pipeline visible after reload' }
  );

  const afterReload = await captureState(page, 'fresh_chat_after_reload');

  return {
    mode: 'pre_restart',
    user_id: config.user_id,
    web_session_id: config.web_session_id,
    old_session_id: primarySession?.session_id ?? null,
    session_titles: sessions.map((session) => session.title),
    before_reload: beforeReload,
    after_reload: afterReload,
  };
}

async function runPostRestart(page) {
  const existingSessions = await fetchSessions(config.user_id, config.web_session_id);
  const existingSessionIds = new Set(existingSessions.map((session) => session.session_id).filter(Boolean));

  await waitForCondition(
    async () => (await countText(page, 'Trace unavailable')) >= 1,
    { timeoutMs: 90000, intervalMs: 500, label: 'old session unavailable traces after restart' }
  );
  const oldSessionAfterRestart = await captureState(page, 'old_session_after_restart');

  await page.locator('aside button').first().click();
  const createdSession = await waitForCondition(
    async () => {
      const sessions = await fetchSessions(config.user_id, config.web_session_id);
      return sessions.find((session) => session.session_id && !existingSessionIds.has(session.session_id)) || null;
    },
    { timeoutMs: 30000, intervalMs: 500, label: 'new distinct session created' }
  );
  await waitForCondition(
    async () => (await getStoredActiveChatId(page)) === createdSession.session_id,
    { timeoutMs: 30000, intervalMs: 300, label: 'new session becomes active chat id' }
  );
  await waitForCondition(
    async () => (await countText(page, 'Trace unavailable')) === 0,
    { timeoutMs: 30000, intervalMs: 300, label: 'old unavailable cards cleared from fresh chat view' }
  );

  const prompts = [
    'Р§С‚Рѕ С‚Р°РєРѕРµ РґСѓС€Р°? РЎСѓС‰РµСЃС‚РІСѓРµС‚ Р»Рё РѕРЅР° РёР»Рё СЌС‚Рѕ РєСѓР»СЊС‚СѓСЂРЅРѕ-С„РёР»РѕСЃРѕС„СЃРєР°СЏ РєРѕРЅСЃС‚СЂСѓРєС†РёСЏ?',
    'Р° С‡РµРј РѕС‚Р»РёС‡Р°РµС‚СЃСЏ РґСѓС€Р° РѕС‚ СЃРѕР·РЅР°РЅРёСЏ?',
  ];
  for (let index = 0; index < prompts.length; index += 1) {
    await sendPrompt(page, prompts[index], 1);
  }

  const newChatBeforeReload = await captureState(page, 'new_chat_after_restart_before_reload');

  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.locator('textarea').first().waitFor({ timeout: 30000 });
  await waitForCondition(
    async () => (await getStoredActiveChatId(page)) === createdSession.session_id,
    { timeoutMs: 30000, intervalMs: 300, label: 'reloaded page restores new active chat id' }
  );
  await waitForCondition(
    async () => (await countText(page, 'Pipeline NEO')) >= 1,
    { timeoutMs: 90000, intervalMs: 500, label: 'post-restart new chat pipeline visible after reload' }
  );
  const newChatAfterReload = await captureState(page, 'new_chat_after_restart_after_reload');

  return {
    mode: 'post_restart',
    user_id: config.user_id,
    web_session_id: config.web_session_id,
    old_session_id: config.old_session_id ?? null,
    new_session_id: createdSession?.session_id ?? null,
    old_session_after_restart: oldSessionAfterRestart,
    new_chat_before_reload: newChatBeforeReload,
    new_chat_after_reload: newChatAfterReload,
  };
}

async function main() {
  await mkdir(config.output_dir, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1600, height: 1200 } });
  await context.addInitScript(
    ({ apiKey, userId, webSessionId }) => {
      localStorage.setItem('bot_api_key', apiKey);
      localStorage.setItem('bot_user_id', userId);
      if (!localStorage.getItem('bot_web_session_id')) {
        localStorage.setItem('bot_web_session_id', webSessionId);
      }
      if (!localStorage.getItem('bot_settings')) {
        localStorage.setItem(
          'bot_settings',
          JSON.stringify({
            apiKey,
            userId,
            theme: 'system',
            showSources: true,
            showPath: true,
            includeFeedbackPrompt: true,
            autoScroll: true,
            compactMode: false,
            soundEnabled: false,
          })
        );
      }
    },
    {
      apiKey: config.api_key,
      userId: config.user_id,
      webSessionId: config.web_session_id,
    }
  );

  const page = await context.newPage();
  try {
    await waitForReady(page);
    const result = config.mode === 'post_restart'
      ? await runPostRestart(page)
      : await runPreRestart(page);

    await writeFile(
      config.result_path,
      JSON.stringify(result, null, 2),
      'utf-8'
    );
  } finally {
    await browser.close();
  }
}

await main();
