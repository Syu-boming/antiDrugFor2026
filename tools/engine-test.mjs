// 播放狀態機測試：以 playwright-core＋系統 Google Chrome 操作 window.__engine 與實體按鍵，
// 驗證 v1.2 第 19.1 節的規則（連按、長按、上一步、暫停、重播、題目恢復未揭答、播放中不跳段），
// 以及 F5／Esc 攔截、頁面隱藏才暫停、GPU 中斷重建，與「有正式音檔」時的音訊排程與切換停止。
// 用即時時鐘（不是虛擬時鐘）跑，約 1.5 分鐘。
//
// 用法：node tools/engine-test.mjs [--headed]
import { createRequire } from 'node:module';
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(join(ROOT, 'app/package.json'));
const { chromium } = require('playwright-core');
const DIST = join(ROOT, 'app/dist');
if (!existsSync(join(DIST, 'index.html'))) { console.error('[engine-test] 請先在 app/ 執行 npm run build'); process.exit(1); }

const results = [];
const check = (name, ok, detail = '') => {
  results.push({ name, ok: !!ok, detail });
  console.log(`${ok ? '  通過' : '✗ 失敗'}  ${name}${detail ? `  （${detail}）` : ''}`);
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await chromium.launch({
  channel: 'chrome', headless: !process.argv.includes('--headed'),
  args: ['--autoplay-policy=no-user-gesture-required'],
});

async function open(indexPath) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto(`${pathToFileURL(indexPath).href}?nofs=1&cues=demo`);
  await page.waitForFunction(() => window.__engine && window.__engine.getState().mode === 'preparing', null, { timeout: 30000 });
  const st = () => page.evaluate(() => window.__engine.getState());
  const waitFor = (fn, arg, timeout = 15000) => page.waitForFunction(fn, arg, { timeout, polling: 50 });
  const waitPhase = (phase, timeout) => waitFor((p) => window.__engine.getState().phase === p, phase, timeout);
  return { page, st, waitFor, waitPhase, errors };
}

// ======================================================================= 一、狀態機（暫代音訊）
console.log('\n一、播放狀態機（示範 cue，暫代音訊）');
{
  const { page, st, waitFor, waitPhase, errors } = await open(join(DIST, 'index.html'));
  let s = await st();
  check('素材未就緒前停在準備畫面；就緒後可按「準備播放」', s.phase === 'preparing' && await page.isEnabled('.ready-btn'));
  await page.click('.ready-btn');
  await waitPhase('title_idle');
  s = await st();
  check('按「準備播放」後停在片頭待機（署名卡）', s.cueId === 'a0_c000' && !(await page.isHidden('#title-card')), `時鐘 ${s.clock}、音訊 ${s.audioState}`);

  await page.evaluate(() => { window.__marker = 123; });
  await page.keyboard.press('F5');
  await page.keyboard.press('Escape');
  await sleep(300);
  s = await st();
  const marker = await page.evaluate(() => window.__marker);
  check('F5／Esc 一律攔截、不做任何動作（沒有重新整理）', marker === 123 && s.blockedKeys >= 2 && s.phase === 'title_idle', `攔截 ${s.blockedKeys} 次`);

  await page.keyboard.press('r');
  await sleep(100);
  check('片頭待機按 R 不動作', (await st()).phase === 'title_idle');

  // 連按：第一下開幕，其餘忽略
  const ign0 = (await st()).ignoredInputs;
  for (let i = 0; i < 5; i++) { await page.keyboard.press('PageDown'); await sleep(40); }
  s = await st();
  check('連按 5 下只推進一個節點（開幕播放中）', s.cueId === 'a0_c001' && s.phase === 'playing' && s.ignoredInputs - ign0 >= 4, `忽略 ${s.ignoredInputs - ign0} 次`);

  // 長按：key repeat 全部忽略
  const rep0 = s.ignoredRepeats;
  await page.keyboard.down('PageDown');
  for (let i = 0; i < 8; i++) { await page.keyboard.down('PageDown'); await sleep(20); }
  await page.keyboard.up('PageDown');
  s = await st();
  check('長按（key repeat）全部忽略', s.ignoredRepeats - rep0 >= 8 && s.cueId === 'a0_c001', `repeat ${s.ignoredRepeats - rep0} 次`);

  await waitPhase('story_waiting', 8000);
  s = await st();
  check('播放中不跳段：開幕播完停在同一個 cue 等老師', s.cueId === 'a0_c001' && s.cueTime >= s.cueDuration - 0.01);

  await sleep(400);
  await page.keyboard.press('PageDown');
  await waitFor(() => window.__engine.getState().cueId === 'a2_c002');
  check('劇情等待按下一步：播放下一段', (await st()).phase === 'playing');
  check('找不到音檔時顯示「暫代音訊」標示', !(await page.isHidden('#badge-placeholder')) && (await st()).placeholderAudio);

  await sleep(1500);
  await page.keyboard.press('Period');
  await sleep(50);
  const p1 = await st();
  await sleep(700);
  const p2 = await st();
  check('句點鍵暫停：時間停在原地', p1.paused && Math.abs(p2.cueTime - p1.cueTime) < 0.03 && p2.cueId === 'a2_c002', `${p1.cueTime} → ${p2.cueTime}`);
  await page.keyboard.press('Period');
  await sleep(500);
  const p3 = await st();
  check('再按句點鍵繼續', !p3.paused && p3.cueTime > p2.cueTime + 0.3, `${p2.cueTime} → ${p3.cueTime}`);

  await page.keyboard.press('Space');
  await sleep(300);
  const sp = await st();
  await page.keyboard.press('Space');
  check('空白鍵也能暫停／繼續（筆電備援）', sp.paused && !(await st()).paused);

  await sleep(600);
  const r0 = await st();
  await page.keyboard.press('r');
  await sleep(60);
  const r1 = await st();
  check('R 重播目前段落：同一個 cue 從頭播', r1.cueId === r0.cueId && r1.cueTime < r0.cueTime - 0.5 && r1.playId > r0.playId && r1.phase === 'playing', `${r0.cueTime} → ${r1.cueTime}`);

  // 頁面隱藏才暫停；恢復後等老師按鍵；失焦不暫停
  await page.evaluate(() => { window.dispatchEvent(new Event('blur')); });
  await sleep(100);
  check('視窗失焦不暫停', !(await st()).paused);
  await page.evaluate(() => {
    Object.defineProperty(document, 'visibilityState', { value: 'hidden', configurable: true });
    document.dispatchEvent(new Event('visibilitychange'));
  });
  await sleep(100);
  const h1 = await st();
  await page.evaluate(() => {
    Object.defineProperty(document, 'visibilityState', { value: 'visible', configurable: true });
    document.dispatchEvent(new Event('visibilitychange'));
  });
  await sleep(600);
  const h2 = await st();
  check('頁面隱藏時自動暫停', h1.paused && h1.pauseReason === 'hidden');
  check('頁面恢復後仍停住，不自行播放', h2.paused && Math.abs(h2.cueTime - h1.cueTime) < 0.05);
  await page.keyboard.press('PageDown');
  await sleep(300);
  const h3 = await st();
  check('暫停中按下一步：只繼續、不跳到下一段', !h3.paused && h3.cueId === 'a2_c002' && h3.phase === 'playing');

  // 上一步
  await page.keyboard.press('PageUp');
  await sleep(100);
  s = await st();
  check('播放中按上一步：回到上一個穩定節點並停止聲音', s.cueId === 'a0_c001' && s.phase === 'story_waiting' && s.activeVoices === 0);
  await page.keyboard.press('PageUp');
  await sleep(100);
  check('再按上一步：回到片頭待機（布幕重新合攏）', (await st()).phase === 'title_idle');
  await page.keyboard.press('PageUp');
  await sleep(100);
  check('片頭待機按上一步：不動作', (await st()).phase === 'title_idle');

  // 題目：不自動揭答；揭答回饋播完停住；上一步恢復未揭答
  await page.evaluate(() => window.__engine.gotoCue('a2_c005', { mode: 'after' }));
  await sleep(1500);
  s = await st();
  const correct0 = await page.locator('.quiz-opt.correct').count();
  check('題目出現後不自動揭答（等 1.5 秒仍未揭答）', s.phase === 'quiz_shown' && !s.revealed && correct0 === 0 && !(await page.isHidden('#quiz-card')));
  await page.keyboard.press('PageDown');
  await sleep(150);
  for (let i = 0; i < 3; i++) { await page.keyboard.press('PageDown'); await sleep(60); }
  s = await st();
  check('揭答回饋播放中忽略重複輸入', s.phase === 'reveal_playing' && s.cueId === 'a2_c006');
  await waitPhase('reveal_waiting', 12000);
  await sleep(1500);
  s = await st();
  check('揭答回饋播完停住（留出發獎時間）', s.phase === 'reveal_waiting' && s.revealed);
  check('正解蓋印章＋外框，點亮第 2 盞燈', (await page.locator('.quiz-opt.opt-3.correct').count()) === 1 && s.lampsLit.includes(2));
  await page.keyboard.press('PageUp');
  await sleep(150);
  s = await st();
  check('上一步回到題目：恢復成未揭答', s.phase === 'quiz_shown' && !s.revealed && (await page.locator('.quiz-opt.correct').count()) === 0 && s.lampsLit.length === 0);

  // 揭答 → 閉幕 → 片尾署名卡（一次按鍵）
  await sleep(400);
  await page.keyboard.press('PageDown');
  await waitPhase('reveal_waiting', 12000);
  await sleep(400);
  await page.keyboard.press('PageDown');
  await sleep(100);
  s = await st();
  check('正解等待按下一步：收起題卡開始閉幕（不會同時再觸發揭答）', s.cueId === 'a8_c002' && s.phase === 'playing');
  await waitPhase('ended', 8000);
  s = await st();
  check('閉幕後自動停在片尾署名卡', s.cueId === 'a8_c003' && !(await page.isHidden('#title-card')));
  await sleep(500);
  const e0 = s.ignoredInputs;
  await page.keyboard.press('PageDown');
  await sleep(100);
  s = await st();
  check('結束後按下一步保持畫面', s.phase === 'ended' && s.ignoredInputs === e0 + 1);
  await page.keyboard.press('PageUp');
  await sleep(100);
  s = await st();
  check('片尾按上一步：回到正解等待（跳過自動接續的閉幕）', s.phase === 'reveal_waiting' && s.revealed);

  // GPU 中斷：停止聲音、停在中斷畫面；按一次後重建並回到穩定節點
  await page.evaluate(() => window.__engine.gotoCue('a2_c004', { mode: 'play' }));
  await sleep(800);
  const lost = await page.evaluate(() => window.__engine.debug.loseContext());
  await waitFor(() => window.__engine.getState().mode === 'context_lost', null, 5000).catch(() => undefined);
  s = await st();
  check('GPU 中斷：停止聲音並停在中斷畫面', lost && s.mode === 'context_lost' && s.activeVoices === 0 && !(await page.isHidden('#lost-screen')));
  await page.keyboard.press('PageDown');
  await waitFor(() => window.__engine.getState().mode === 'waiting', null, 10000).catch(() => undefined);
  s = await st();
  check('按一次後重建，回到目前 cue 的穩定節點', s.mode === 'waiting' && s.cueId === 'a2_c002' && !s.contextLost && (await page.isHidden('#lost-screen')), `${s.cueId} ${s.phase}`);
  await sleep(400);
  await page.keyboard.press('PageDown');
  await sleep(1200);
  const shot = await page.screenshot({ type: 'jpeg', quality: 80 });
  s = await st();
  check('重建後可以繼續播放且畫面不是黑的', s.cueId === 'a2_c004' && s.phase === 'playing' && shot.length > 25000, `截圖 ${(shot.length / 1024).toFixed(0)} KB`);

  // 教師選單與聲畫偏移
  await page.keyboard.press('m');
  const menuOn = !(await page.isHidden('#teacher-menu'));
  await page.keyboard.press('m');
  check('M 鍵開關教師選單（預設隱藏）', menuOn && (await page.isHidden('#teacher-menu')));
  await page.evaluate(() => window.__engine.debug.setAvOffset(80));
  check('聲畫偏移可設定（毫秒）', (await st()).avOffsetMs === 80);
  await page.evaluate(() => window.__engine.debug.setAvOffset(0));

  check('過程中沒有頁面錯誤', errors.length === 0, errors.slice(0, 3).join(' | '));
  await page.close();
}

// ======================================================================= 二、正式音檔路徑
console.log('\n二、有正式音檔時（測試用合成音檔，暫存資料夾，不動到 app/dist）');
{
  const tmp = mkdtempSync(join(tmpdir(), 'antidrug-engine-test-'));
  try {
    copyFileSync(join(DIST, 'index.html'), join(tmp, 'index.html'));
    copyFileSync(join(DIST, 'app.js'), join(tmp, 'app.js'));
    mkdirSync(join(tmp, 'audio/vo'), { recursive: true });
    // 合成 16-bit 單聲道 WAV（安靜的正弦音）
    const wav = (sec, hz) => {
      const rate = 24000, n = Math.round(sec * rate), b = Buffer.alloc(44 + n * 2);
      b.write('RIFF', 0); b.writeUInt32LE(36 + n * 2, 4); b.write('WAVE', 8); b.write('fmt ', 12);
      b.writeUInt32LE(16, 16); b.writeUInt16LE(1, 20); b.writeUInt16LE(1, 22); b.writeUInt32LE(rate, 24);
      b.writeUInt32LE(rate * 2, 28); b.writeUInt16LE(2, 32); b.writeUInt16LE(16, 34); b.write('data', 36); b.writeUInt32LE(n * 2, 40);
      for (let i = 0; i < n; i++) b.writeInt16LE(Math.round(Math.sin((2 * Math.PI * hz * i) / rate) * 2000), 44 + i * 2);
      return b;
    };
    writeFileSync(join(tmp, 'audio/vo/vo_a2_c002_01_v01.wav'), wav(2.0, 440));
    writeFileSync(join(tmp, 'audio/vo/vo_a2_c002_02_v01.wav'), wav(1.0, 660));
    writeFileSync(join(tmp, 'audio/vo/vo_a2_c002_02_v02.wav'), wav(1.5, 550)); // 較新版本應被採用
    const { runPack } = await import(pathToFileURL(join(ROOT, 'tools/pack.mjs')).href);
    const man = await runPack({ audioDir: join(tmp, 'audio'), assetsDir: join(tmp, 'none'), outDir: join(tmp, 'data') });
    check('打包時取最新版本的音檔', man.audio.vo_a2_c002_02?.source.endsWith('_v02.wav') && Math.abs((man.audio.vo_a2_c002_02.duration ?? 0) - 1.5) < 0.01);

    const { page, st, waitFor, waitPhase, errors } = await open(join(tmp, 'index.html'));
    await page.click('.ready-btn');
    await waitPhase('title_idle');
    const cues = await page.evaluate(() => window.__engine.getCues());
    const c2 = cues.find((c) => c.id === 'a2_c002');
    check('該段兩句都有音檔 → 不是暫代模式', c2 && !c2.placeholder);
    let s = await st();
    if (s.clock !== 'audio') {
      check('音訊時鐘可用（AudioContext 有前進）', false, `時鐘 ${s.clock}、音訊 ${s.audioState}；無頭模式可能沒有音訊裝置`);
    } else {
      check('現場以 AudioContext 時鐘驅動', true);
      await page.evaluate(() => window.__engine.gotoCue('a2_c002', { mode: 'play' }));
      await sleep(200);
      s = await st();
      check('播放時兩句台詞都排進對白匯流排', s.activeVoices === 2 && s.voiceIds.includes('vo_a2_c002_01'), `排程 ${s.activeVoices} 個`);
      await page.keyboard.press('Period');
      await sleep(300);
      s = await st();
      check('暫停時 AudioContext 一起停（聲音與畫面同一個時鐘）', s.paused && s.audioState === 'suspended');
      await page.keyboard.press('Period');
      await sleep(300);
      check('繼續時 AudioContext 恢復', (await st()).audioState === 'running');
      await page.keyboard.press('PageUp');
      await sleep(100);
      s = await st();
      check('切換節點時停止舊台詞（不重疊）', s.activeVoices === 0 && s.cueId === 'a0_c001');
      await page.evaluate(() => window.__engine.gotoCue('a2_c002', { mode: 'play' }));
      await waitFor(() => window.__engine.getState().cueTime > 7.3, null, 12000);
      s = await st();
      check('台詞時間到時字幕同步出現', s.subtitle.includes('我想揮手'), s.subtitle);
      await page.keyboard.press('r');
      await sleep(100);
      s = await st();
      check('重播時舊台詞停止、重新排程', s.activeVoices === 2 && s.cueTime < 1);
    }
    check('過程中沒有頁面錯誤', errors.length === 0, errors.slice(0, 3).join(' | '));
    await page.close();
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
}

await browser.close();
const failed = results.filter((r) => !r.ok);
console.log(`\n[engine-test] ${results.length - failed.length}／${results.length} 項通過${failed.length ? `；失敗：${failed.map((f) => f.name).join('、')}` : ''}`);
process.exit(failed.length ? 1 : 0);
