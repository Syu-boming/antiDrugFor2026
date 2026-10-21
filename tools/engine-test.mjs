// 播放狀態機測試：以 playwright-core＋系統 Google Chrome 操作 window.__engine 與實體按鍵，
// 驗證 v1.2 第 19.1 節的規則（連按、長按、上一步、暫停、重播、題目恢復未揭答、播放中不跳段），
// 以及 F5／Esc 攔截、頁面隱藏才暫停、GPU 中斷重建，與「有正式音檔」時的音訊排程與切換停止。
// 三、G4 代表鏡頭 cue 集（g4）的流程、WAIT_GUARD；四、虛擬時鐘下的確定性（重播一致）、布幕與署名卡時間、
// 開幕後角色不瞬間出現、操偶線落下與線寬、眨眼與嘴型；五、缺檔照常演出；六、字幕斷行與對白避讓的純函式測試；
// 七、G4 正式配音的操作測試（必要旁白播放中按上一步、R、暫停後繼續、系統停掉 AudioContext 後恢復、開頭靜音）：
// 對白聲音 ≤ 1、字幕與語音時間差 ≤ 50 ms（G4 修正第 29 項）。
// 前兩段與第七段用即時時鐘（不是虛擬時鐘）跑；全部約 5 分鐘。
//
// 用法：node tools/engine-test.mjs [--headed]
import { createRequire } from 'node:module';
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(join(ROOT, 'app/package.json'));
const { chromium } = require('playwright-core');
const DIST = join(ROOT, 'app/dist');
if (!existsSync(join(DIST, 'index.html'))) { console.error('[engine-test] 請先在 app/ 執行 npm run build'); process.exit(1); }

const dk = await import(pathToFileURL(join(ROOT, 'app/src/audio/ducking.ts')).href);
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

async function open(indexPath, query = 'nofs=1&cues=demo') {
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto(`${pathToFileURL(indexPath).href}?${query}`);
  await page.waitForFunction(() => window.__engine && ['preparing', 'waiting'].includes(window.__engine.getState().mode), null, { timeout: 60000 });
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
  {
    // 暫代音訊標示：找一個沒有配音檔的 cue（正式配音陸續進來，所以不寫死 cue）
    const ph = (await page.evaluate(() => window.__engine.getCues())).find((c) => c.placeholder && c.kind !== 'title');
    const cur = await st();
    if (!ph) check('找不到音檔時顯示「暫代音訊」標示', true, '所有句子都有音檔，略過');
    else if (cur.placeholderAudio) check('找不到音檔時顯示「暫代音訊」標示', !(await page.isHidden('#badge-placeholder')));
    else {
      check('有正式配音的段落不顯示「暫代音訊」標示', await page.isHidden('#badge-placeholder'));
    }
  }

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
    // 配樂（測試對白避讓）：示範 cue 的 a2_c002 改用這首循環配樂
    mkdirSync(join(tmp, 'audio/music'), { recursive: true });
    writeFileSync(join(tmp, 'audio/music/music_test_v01.wav'), wav(4.0, 220));
    mkdirSync(join(tmp, 'cues'), { recursive: true });
    const demo = JSON.parse(readFileSync(join(ROOT, 'app/cues/demo.json'), 'utf8'));
    for (const c of demo.cues) if (c.id === 'a2_c002') c.audioId = 'music_test';
    writeFileSync(join(tmp, 'cues/demo.json'), JSON.stringify(demo));
    const { runPack } = await import(pathToFileURL(join(ROOT, 'tools/pack.mjs')).href);
    const man = await runPack({ audioDir: join(tmp, 'audio'), assetsDir: join(tmp, 'none'), outDir: join(tmp, 'data'), cuesDir: join(tmp, 'cues'), sourcesFile: join(tmp, 'none.json') });
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
      const voN = (x) => x.voiceIds.filter((v) => v.startsWith('vo_')).length;
      check('播放時兩句台詞都排進對白匯流排', voN(s) === 2 && s.voiceIds.includes('vo_a2_c002_01'), `對白 ${voN(s)} 個（全部 ${s.activeVoices}）`);
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
      check('切換節點時停止舊台詞（不重疊）', s.voiceIds.filter((v) => v.startsWith('vo_')).length === 0 && s.cueId === 'a0_c001');
      await page.evaluate(() => window.__engine.gotoCue('a2_c002', { mode: 'play' }));
      await waitFor(() => window.__engine.getState().cueTime > 1.5, null, 12000);
      const lv0 = await page.evaluate(() => window.__engine.debug.audioLevels());
      await waitFor(() => window.__engine.getState().cueTime > 7.6, null, 12000);
      s = await st();
      check('台詞時間到時字幕同步出現', s.subtitle.includes('我想揮手'), s.subtitle);
      const lv1 = await page.evaluate(() => window.__engine.debug.audioLevels());
      await waitFor(() => window.__engine.getState().cueTime > 9.2, null, 12000);
      const lv2 = await page.evaluate(() => window.__engine.debug.audioLevels());
      await waitFor(() => window.__engine.getState().phase === 'story_waiting', null, 15000);
      await sleep(1300);
      const lv3 = await page.evaluate(() => window.__engine.debug.audioLevels());
      check('配樂在播（段落配樂 music_test，基準音量約 0.8）', lv0.musicId === 'music_test' && Math.abs(lv0.musicBus - 0.8) < 0.1, `bus ${lv0.musicBus.toFixed(2)}`);
      check('對白壓低配樂：說話前配樂未避讓', lv0.duck > 0.9, `duck ${lv0.duck.toFixed(2)}`);
      check(`對白壓低配樂：說話時避讓到 DUCK_LEVEL（${dk.DUCK_LEVEL}，約 ${(20 * Math.log10(dk.DUCK_LEVEL)).toFixed(0)} dB）`, Math.abs(lv1.duck - dk.DUCK_LEVEL) < 0.06, `duck ${lv1.duck.toFixed(2)}`);
      check('對白壓低配樂：相鄰兩句之間（間隔 < 0.9 秒）不回升', lv2.duck < dk.DUCK_LEVEL + 0.1, `duck ${lv2.duck.toFixed(2)}`);
      check('對白壓低配樂：說完後回升', lv3.duck > 0.85, `duck ${lv3.duck.toFixed(2)}`);
      check(`教師停格：劇情段落播完後配樂降到基準音量的 ${dk.HOLD_MUSIC_RATIO}（時間常數 ${dk.HOLD_TC} 秒）`, lv3.musicBus < 0.8 * dk.HOLD_MUSIC_RATIO * 2.2, `bus ${lv3.musicBus.toFixed(3)}（停住 1.3 秒時）`);
      await page.evaluate(() => window.__engine.gotoCue('a2_c002', { mode: 'play' }));
      await waitFor(() => window.__engine.getState().cueTime > 7.3, null, 12000);
      await page.keyboard.press('r');
      await sleep(100);
      s = await st();
      check('重播時舊台詞停止、重新排程', voN(s) === 2 && s.cueTime < 1, `對白 ${voN(s)} 個`);
    }
    check('過程中沒有頁面錯誤', errors.length === 0, errors.slice(0, 3).join(' | '));
    await page.close();
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
}

// ======================================================================= 三、G4 代表鏡頭（即時）
console.log('\n三、G4 代表鏡頭 cue 集（g4，即時時鐘）');
{
  const { page, st, waitFor, waitPhase, errors } = await open(join(DIST, 'index.html'), 'nofs=1&cues=g4');
  let s = await st();
  check('g4 載入：名冊建立三個紙偶（阿樂叔叔、小晴、小宇）', s.actors.join(',') === 'ale,xiaoqing,xiaoyu' && s.set === 'workshop_g4', `${s.actors.join('、')}；${s.castReport.join('；')}`);
  await page.click('.ready-btn');
  await waitPhase('title_idle');
  check('g4 片頭待機：署名卡、布幕合攏', !(await page.isHidden('#title-card')) && (await st()).world.curtain < 0.01);
  await sleep(450);
  await page.keyboard.press('PageDown');
  await waitFor(() => window.__engine.getState().cueId === 'a0_c001');
  // WAIT_GUARD：一進入等待就按（< 350 ms）要被忽略
  await page.waitForFunction(() => window.__engine.getState().phase === 'story_waiting', null, { timeout: 20000, polling: 'raf' });
  const ig0 = (await st()).ignoredInputs;
  await page.keyboard.press('PageDown');
  s = await st();
  check('WAIT_GUARD 350 ms：剛停住時的誤觸下一步被忽略', s.cueId === 'a0_c001' && s.ignoredInputs === ig0 + 1 && s.phase === 'story_waiting');
  await sleep(420);
  await page.keyboard.press('PageDown');
  await waitFor(() => window.__engine.getState().cueId === 'a2_c002');
  check('等待超過 350 ms 後按下一步：播放「線落下來」', (await st()).phase === 'playing');
  await page.evaluate(() => window.__engine.gotoCue('a2_c004', { mode: 'after' }));
  await sleep(450);
  s = await st();
  check('必要旁白一播完停格＝最後謝幕等待（G4 的下一步是閉幕）', s.phase === 'final_waiting');
  await page.keyboard.press('PageDown');
  await waitPhase('ended', 12000);
  s = await st();
  check('閉幕：布幕合攏後自動停在同款署名卡', s.cueId === 'a8_c003' && !(await page.isHidden('#title-card')) && s.world.curtain < 0.01);
  await page.keyboard.press('PageUp');
  await sleep(150);
  check('片尾按上一步：回到必要旁白一的停格', (await st()).cueId === 'a2_c004');
  check('g4 過程中沒有頁面錯誤', errors.length === 0, errors.slice(0, 3).join(' | '));
  await page.close();
}

// ======================================================================= 四、G4 虛擬時鐘（確定性與表演）
console.log('\n四、G4 虛擬時鐘：重播一致、布幕時間、角色進場、操偶線、臉部換片');
{
  const { page, st, errors } = await open(join(DIST, 'index.html'), 'capture=1&cues=g4&step=30');
  await page.waitForFunction(() => window.__engine.getState().mode === 'waiting', null, { timeout: 60000 });
  const play = (id) => page.evaluate((i) => window.__engine.capture.playCue(i), id);
  const seek = (t) => page.evaluate((x) => window.__engine.capture.seek(x), t);
  const shot = async () => (await page.screenshot({ type: 'png' })).toString('base64');
  await play('a2_c002');
  await seek(12.0); const A = await shot();
  await seek(5.0); await seek(12.0); const B = await shot();
  await play('a2_c002'); await seek(12.0); const C = await shot();
  check('重播一致：同一 cue 同一時間的畫面逐像素相同（倒回、重播都一樣）', A === B && B === C, `${A === B}/${B === C}`);

  // 署名卡約 1 秒淡出、布幕約 2 秒打開（在署名卡淡出之後）
  await play('a0_c001');
  const samples = [];
  for (let t = 0; t <= 4.0001; t += 0.05) { await seek(t); const w = (await st()).world; samples.push([t, w.titleCard, w.curtain]); }
  const firstBelow = (k, v) => samples.find((x) => x[k] <= v)?.[0];
  const firstAbove = (k, v) => samples.find((x) => x[k] >= v)?.[0];
  const titleGone = firstBelow(1, 0.02), curtain5 = firstAbove(2, 0.05), curtain95 = firstAbove(2, 0.95);
  check('署名卡約 1 秒淡出', titleGone !== undefined && titleGone >= 0.85 && titleGone <= 1.15, `${titleGone?.toFixed(2)} 秒`);
  check('布幕在署名卡淡出後才開始動', curtain5 !== undefined && curtain5 >= 0.95, `5% 開於 ${curtain5?.toFixed(2)} 秒`);
  check('布幕移動約 2 秒（全程 2.0 秒，5%→95% 約 1.4 秒）', curtain95 !== undefined && curtain95 - curtain5 >= 1.2 && curtain95 - curtain5 <= 2.2, `${(curtain95 - curtain5).toFixed(2)} 秒`);
  await seek(3.4);
  const pr0 = await page.evaluate(() => window.__engine.debug.probe());
  await seek(10.6);
  const pr1 = await page.evaluate(() => window.__engine.debug.probe());
  const hOf = (pr, id) => { const a = pr.actors.find((x) => x.id === id); return a && a.visible ? a.box[3] - a.box[1] : 0; };
  check('開幕後角色不瞬間出現：布幕全開時角色還平躺（隨景片立起）', ['ale', 'xiaoqing', 'xiaoyu'].every((id) => hOf(pr0, id) < 0.4 * hOf(pr1, id)),
    ['ale', 'xiaoqing', 'xiaoyu'].map((id) => `${id} ${hOf(pr0, id).toFixed(0)}→${hOf(pr1, id).toFixed(0)}px`).join('、'));

  // 操偶線：一根根落下、扣上紙環；近景線寬 ≥ 8 px
  await play('a2_c002');
  const vis = async (t) => { await seek(t); const p = await page.evaluate(() => window.__engine.debug.probe()); return Object.fromEntries(p.strings.map((x) => [x.anchor, x])); };
  const s5 = await vis(3.0), s8 = await vis(4.8), s11 = await vis(7.0);
  check('操偶線落下前看不到線（3.0 秒）', !s5.wrist.visible && !s5.elbow.visible && !s5.knee.visible);
  check('操偶線一根根落下（4.8 秒：腕背已扣上、膝前還沒落下；第一根在 5 秒前落下）', s8.wrist.visible && s8.wrist.ringPx && !s8.knee.visible);
  check('三條線都扣上（腕背、肘外、膝前），紙環是正方形圓環（直徑約 2.4 倍線寬）', s11.wrist.visible && s11.elbow.visible && s11.knee.visible
    && ['wrist', 'elbow', 'knee'].every((n) => s11[n].ringRadiusPx * 2 > s11[n].widthPx * 1.8 && s11[n].ringRadiusPx * 2 < s11[n].widthPx * 3.2),
  ['wrist', 'elbow', 'knee'].map((n) => `${n} 線 ${s11[n].widthPx.toFixed(1)}／環 ${(s11[n].ringRadiusPx * 2).toFixed(1)} px`).join('、'));
  const wides = [];
  for (const [id, t] of [['a2_c002', 7.0], ['a2_c002', 22.0], ['a2_c004', 4.6], ['a2_c004', 9.0], ['a2_c004', 13.0]]) {
    await play(id); await seek(t);
    const pc = await page.evaluate(() => window.__engine.debug.probe());
    wides.push(...pc.strings.filter((x) => x.visible && x.ringPx).map((x) => x.widthPx * (1080 / 720)));
  }
  check('線寬 6–10 px（1080p 換算；中景與 a2_c004 各鏡位）', Math.min(...wides) >= 6 && Math.max(...wides) <= 10, `${Math.min(...wides).toFixed(1)}–${Math.max(...wides).toFixed(1)} px@1080`);

  // 臉部換片：說話時嘴型變化、3–6 秒眨一次
  await play('a2_c002');
  const cues = await page.evaluate(() => window.__engine.getCues());
  const tl = cues.find((c) => c.id === 'a2_c002');
  const mouths = new Set(), eyes = { ale: 0, xiaoqing: 0, xiaoyu: 0 }, prev = {};
  for (let t = 0; t < tl.duration; t += 1 / 24) {
    await seek(t);
    const f = await page.evaluate(() => window.__engine.debug.faces());
    if (t > 13.2 && t < 15.5 && f.ale) mouths.add(f.ale.mouth);
    for (const id of Object.keys(eyes)) {
      const e = f[id]?.eyes;
      if (e === 'closed' && prev[id] !== 'closed') eyes[id]++;
      prev[id] = e;
    }
  }
  check('對嘴：阿樂叔叔說話時嘴型換片（至少 3 種）', mouths.size >= 3, [...mouths].join('、'));
  const minBlinks = Math.floor(tl.duration / 6.5);
  check(`眨眼：每個角色在 ${tl.duration.toFixed(0)} 秒內至少眨 ${minBlinks} 次（3–6 秒一次＋情緒轉折）`, Object.values(eyes).every((n) => n >= minBlinks), JSON.stringify(eyes));

  // G4 修正第 2 輪第 10 項：換姿勢翻面前 0.2 秒到結束後 0.3 秒不眨眼（每秒 30 格逐格檢查）
  const rtl = await page.evaluate(() => window.__engine.debug.timeline('a2_c002'));
  const flipBad = [];
  let flipFrames = 0;
  for (const a of rtl.anims.filter((x) => x.name === 'puppet.pose')) {
    for (let t = a.start - 0.2; t <= a.end + 0.3 + 1e-6; t += 1 / 30) {
      await seek(t);
      const e = (await page.evaluate(() => window.__engine.debug.faces()))[a.target]?.eyes;
      flipFrames++;
      if (e !== 'open') flipBad.push(`${a.target} ${t.toFixed(3)}s ${e}`);
    }
  }
  check('眨眼不和換姿勢翻面重疊：翻面前 0.2 秒到結束後 0.3 秒眼睛都是睜開', flipBad.length === 0 && flipFrames > 0, flipBad.length ? flipBad.slice(0, 4).join('、') : `${flipFrames} 格`);

  // G4 修正第 2 輪第 6 項：線還鬆時畫面裡那段線是下垂弧（中點偏移 ≥ 15 px），繃直節拍後是直線（≤ 3 px）
  const sagOf = (path) => {
    const pts = [];
    for (let i = 0; i < path.length; i++) {
      const p = path[i];
      if (p[1] < 0) continue;
      if (i > 0 && path[i - 1][1] < 0 && !pts.length) { const a = path[i - 1]; const u = -a[1] / (p[1] - a[1]); pts.push([a[0] + (p[0] - a[0]) * u, 0]); }
      pts.push(p);
    }
    if (pts.length < 3) return null;
    const L = [0];
    for (let i = 1; i < pts.length; i++) L.push(L[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
    const half = L[L.length - 1] / 2;
    let m = pts[pts.length - 1];
    for (let i = 1; i < L.length; i++) if (L[i] >= half) { const u = (half - L[i - 1]) / Math.max(1e-9, L[i] - L[i - 1]); m = [pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * u, pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * u]; break; }
    const a = pts[0], b = pts[pts.length - 1], cl = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1;
    return Math.abs((b[0] - a[0]) * (a[1] - m[1]) - (a[0] - m[0]) * (b[1] - a[1])) / cl * (1080 / 720);
  };
  await play('a2_c002');
  const sagAt = async (t) => { await seek(t); const p = await page.evaluate(() => window.__engine.debug.probe()); return Object.fromEntries(p.strings.filter((x) => x.visible && x.path).map((x) => [x.anchor, sagOf(x.path)])); };
  const sl = await sagAt(11.0), stt = await sagAt(12.6);
  check('操偶線還鬆（11.0 秒）是下垂弧：三條線中點偏移 ≥ 15 px（1080p 換算）', ['wrist', 'elbow', 'knee'].every((n) => sl[n] >= 15), Object.entries(sl).map(([k, v]) => `${k} ${v?.toFixed(1)}`).join('、'));
  check('繃直節拍後（12.6 秒）腕背、肘外是直線：中點偏移 ≤ 3 px', ['wrist', 'elbow'].every((n) => stt[n] !== null && stt[n] <= 3), Object.entries(stt).map(([k, v]) => `${k} ${v?.toFixed(1)}`).join('、'));

  // G4 修正第 2 輪第 7 項：站起時臀部離凳上移 ≥ 25 px；扶桌時近側手（不透明範圍）跨過桌面上緣 ≥ 10 px
  const hipAbove = async (t) => { await seek(t); const p = await page.evaluate(() => window.__engine.debug.probe()); const a = p.actors.find((x) => x.id === 'ale'); const st = p.landmarks.stoolTop; return { above: (st[0][1] + st[1][1]) / 2 - a.joints.hip[1], p, a }; };
  // 站起拍跟著 a2_c002_01 結束時間走（kneeTug＝台詞結束＋0.15 s），取樣點也以台詞結束時間為準（2026-10-21 主線：配音換 ElevenLabs 後句長改變）
  const vt = JSON.parse(readFileSync(join(ROOT, 'audio/vo/timings.json'), 'utf8'));
  const L1 = 13.45 + vt.a2_c002_01.seconds;
  const h0 = await hipAbove(L1 - 0.04), h1 = await hipAbove(L1 + 0.66);
  const rise = (h1.above - h0.above) * (1080 / 720);
  const h2 = await hipAbove(L1 + 4.16);
  const hand = h2.a.opaque?.hand_l, tt = h2.p.landmarks.tableTop;
  const ty = (tt[0][1] + tt[1][1]) / 2;
  const straddle = hand ? Math.min(ty - hand[1], hand[3] - ty) * (1080 / 720) : -1;
  check(`站起拍：臀部相對凳面上移 ≥ 25 px（台詞結束＋0.66 秒對 −0.04 秒，${(L1 + 0.66).toFixed(2)} 對 ${(L1 - 0.04).toFixed(2)} 秒，1080p 換算）`, rise >= 25, `${rise.toFixed(1)} px`);
  check(`扶桌：近側手不透明範圍跨過桌面上緣 ≥ 10 px（台詞結束＋4.16 秒＝${(L1 + 4.16).toFixed(2)} 秒）`, straddle >= 10, `${straddle.toFixed(1)} px`);
  const ws = await page.evaluate(() => [getComputedStyle(document.querySelector('.quiz-q')).whiteSpace, getComputedStyle(document.querySelector('.sig-card')).backgroundImage.slice(0, 22)]);
  check('題卡題目支援手動換行（white-space: pre-line）', ws[0] === 'pre-line', ws[0]);
  check('署名卡由程式排字（素材紙卡只當底）', (await page.textContent('.sig-text')) === '許博明老師製作', ws[1]);
  check('虛擬時鐘測試沒有頁面錯誤', errors.length === 0, errors.slice(0, 3).join(' | '));
  await page.close();
}

// ======================================================================= 五、缺檔照常演出
console.log('\n五、配樂與音效缺檔時照常演出（暫存資料夾）');
{
  const tmp = mkdtempSync(join(tmpdir(), 'antidrug-engine-missing-'));
  try {
    copyFileSync(join(DIST, 'index.html'), join(tmp, 'index.html'));
    copyFileSync(join(DIST, 'app.js'), join(tmp, 'app.js'));
    mkdirSync(join(tmp, 'audio'), { recursive: true });
    const { runPack } = await import(pathToFileURL(join(ROOT, 'tools/pack.mjs')).href);
    await runPack({ audioDir: join(tmp, 'audio'), outDir: join(tmp, 'data') });
    const { page, st, waitFor, waitPhase, errors } = await open(join(tmp, 'index.html'), 'nofs=1&cues=g4');
    let s = await st();
    check('缺配樂、音效、配音時仍可按「準備播放」', s.mode === 'preparing' && await page.isEnabled('.ready-btn'));
    check('準備畫面與狀態列出缺檔', s.missingAudio.includes('music_m4_strings') && s.missingAudio.includes('sfx_string_drop'), `缺 ${s.missingAudio.length} 個`);
    await page.click('.ready-btn');
    await waitPhase('title_idle');
    await sleep(450);
    await page.keyboard.press('PageDown');
    await waitFor(() => window.__engine.getState().cueTime > 3.0, null, 10000);
    s = await st();
    check('缺檔下開幕照常播放（不當機）', s.cueId === 'a0_c001' && s.phase === 'playing' && errors.length === 0, errors.slice(0, 2).join(' | '));
    await page.close();
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
}

// ======================================================================= 六、純函式（Node 直接執行 TypeScript）
console.log('\n六、字幕斷行、對白避讓排程（純函式）');
{
  const tlmod = await import(pathToFileURL(join(ROOT, 'app/src/ui/textlayout.ts')).href);
  const script = readFileSync(join(ROOT, 'script/劇本_v03.md'), 'utf8').split('\n').filter((l) => /^\[a\d_c\d{3}_\d{2}\]/.test(l)).map((l) => l.replace(/^\[[^\]]+\] [^：]+：/, ''));
  const broken = script.flatMap((t) => tlmod.brokenWords(t).map((b) => `${t.slice(0, 8)}…（${b}）`));
  const over = script.filter((t) => tlmod.layoutSubtitle(t).some((pg) => pg.length > 2 || pg.some((r) => tlmod.charLen(r) > 16)));
  check(`劇本 ${script.length} 句字幕：每行 ≤ 16 字、每頁 ≤ 2 行`, over.length === 0, over.slice(0, 2).join(' | '));
  check('劇本字幕斷行不拆開詞表裡的詞', broken.length === 0, broken.slice(0, 3).join(' | '));
  // 斷行產生的行首（不含台詞本身的第一個字，例如「……你是青蛙燈嗎？」本來就以刪節號開頭）
  const rowStart = script.flatMap((t) => tlmod.layoutSubtitle(t).flat().slice(1)).filter((r) => /^[，、。！？；：…」』）]/.test(r));
  check('斷行後標點不出現在行首', rowStart.length === 0, rowStart.slice(0, 3).join(' | '));
  const nar = tlmod.layoutSubtitle('這些線是故事的比喻。毒品可能讓人的頭腦和身體受到影響，不聽使喚。人不會真的變成喪屍。');
  check('必要旁白一：句子不跨頁（3 頁、第二頁兩行）', nar.length === 3 && nar[0][0] === '這些線是故事的比喻。' && nar[2][0] === '人不會真的變成喪屍。', JSON.stringify(nar));
  const man = tlmod.layoutSubtitle('第一行\n第二行\n\n第三行');
  check('cue 文字支援手動換行（\\n 換行、\\n\\n 換頁）', JSON.stringify(man) === JSON.stringify([['第一行', '第二行'], ['第三行']]), JSON.stringify(man));
  check('手動換行不影響朗讀字數與配音比對', tlmod.spokenChars('第一行\n第二行') === 6 && tlmod.plainText('第一行\n第二行') === '第一行第二行');
  const plan = dk.duckingPlan([[2, 4], [4.5, 6], [9, 10]]);
  const at = (t) => dk.duckGainAt(plan, t);
  check(`避讓排程：說話前 0.15 秒開始壓低、說話中約 ${dk.DUCK_LEVEL}`, at(1.5) > 0.95 && Math.abs(at(3) - dk.DUCK_LEVEL) < 0.02, `${at(1.5).toFixed(2)} / ${at(3).toFixed(2)}`);
  check('避讓排程：間隔 0.5 秒的兩句之間不回升；間隔 3 秒的會回升', at(4.3) < dk.DUCK_LEVEL + 0.08 && at(8.5) > 0.85, `${at(4.3).toFixed(2)} / ${at(8.5).toFixed(2)}`);
  check('避讓排程：最後一句說完 0.3 秒後回升', at(10.2) < dk.DUCK_LEVEL + 0.08 && at(11.5) > 0.9, `${at(10.2).toFixed(2)} / ${at(11.5).toFixed(2)}`);
  const val = await import(pathToFileURL(join(ROOT, 'app/src/cues/validate.ts')).href);
  for (const f of readdirSync(join(ROOT, 'app/cues')).filter((x) => x.endsWith('.json') && !x.includes('schema'))) {
    const v = val.validateCueFile(JSON.parse(readFileSync(join(ROOT, 'app/cues', f), 'utf8')));
    check(`cue 檔 ${f} 驗證通過、沒有未知動畫名稱`, v.ok && v.warnings.length === 0, [...v.errors, ...v.warnings].slice(0, 3).join(' | '));
  }
}

// ======================================================================= 七、G4 正式配音的操作測試（即時、AudioContext 時鐘）
console.log('\n七、G4 正式配音：必要旁白播放中按上一步、R、暫停後繼續、系統停掉 AudioContext 後恢復、開頭靜音');
{
  const { page, st, waitFor, waitPhase, errors } = await open(join(DIST, 'index.html'), 'nofs=1&cues=g4');
  await page.click('.ready-btn');
  await waitPhase('title_idle');
  let s = await st();
  if (s.clock !== 'audio') {
    check('G4 操作測試需要 AudioContext 時鐘', false, `時鐘 ${s.clock}、音訊 ${s.audioState}`);
  } else {
    const voN = (x) => x.voSounding; // 正在發聲的對白（排程時間已到、還沒結束）
    const sync = () => page.evaluate(() => window.__engine.debug.voiceSync());
    const maxDiff = (xs) => (xs.length ? Math.max(...xs.map((x) => Math.abs(x.diffMs))) : NaN);
    const narr = async () => { await page.evaluate(() => window.__engine.gotoCue('a2_c004', { mode: 'play' })); await waitFor(() => window.__engine.getState().cueTime > 7.0, null, 15000); };
    await narr();
    s = await st();
    let sy = await sync();
    check('必要旁白播放中：發聲中的對白 1 個、字幕與語音時間差 ≤ 50 ms', voN(s) === 1 && sy.length === 1 && maxDiff(sy) <= 50, `對白 ${voN(s)}、差 ${maxDiff(sy)} ms（${sy.map((x) => x.id).join('、')}）`);
    // 上一步：回到 a2_c002 的停格，聲音全部停
    await page.keyboard.press('PageUp');
    await sleep(150);
    s = await st();
    check('旁白播放中按上一步：回到上一個穩定節點、發聲中的對白 0 個', s.cueId === 'a2_c002' && s.mode === 'waiting' && voN(s) === 0, `${s.cueId} ${s.phase}、對白 ${voN(s)}`);
    // R：從頭重播，舊台詞停掉
    await narr();
    await page.keyboard.press('r');
    await sleep(150);
    s = await st();
    check('旁白播放中按 R：同一段從頭播、發聲中的對白 ≤ 1（舊旁白已停）', s.cueId === 'a2_c004' && s.cueTime < 1 && voN(s) <= 1, `t=${s.cueTime}、對白 ${voN(s)}`);
    await waitFor(() => window.__engine.getState().cueTime > 6.6, null, 12000);
    sy = await sync();
    s = await st();
    check('重播後旁白：字幕與語音時間差 ≤ 50 ms、發聲中的對白 ≤ 1', voN(s) <= 1 && sy.length === 1 && maxDiff(sy) <= 50, `差 ${maxDiff(sy)} ms`);
    // 暫停後繼續
    await page.keyboard.press('Period');
    await sleep(600);
    const p1 = await st();
    await page.keyboard.press('Period');
    await sleep(400);
    sy = await sync();
    s = await st();
    check('旁白暫停 0.6 秒後繼續：時間停住、恢復後字幕與語音時間差 ≤ 50 ms、發聲中的對白 ≤ 1', p1.paused && p1.audioState === 'suspended' && !s.paused && voN(s) <= 1 && maxDiff(sy) <= 50, `暫停時 ${p1.audioState}；差 ${maxDiff(sy)} ms`);
    // 系統把 AudioContext 停掉（例如投影機切換、Windows 音訊裝置變動），之後系統自己恢復、老師再按繼續
    const t0 = (await st()).cueTime;
    const stA = await page.evaluate(() => window.__engine.debug.systemSuspendAudio());
    await sleep(500);
    const a1 = await st();
    check('系統停掉 AudioContext（suspended）：引擎自動暫停、時間停住', stA === 'suspended' && a1.paused && a1.pauseReason === 'audio' && Math.abs(a1.cueTime - t0) < 0.15, `暫停原因 ${a1.pauseReason}、${t0}→${a1.cueTime}`);
    await page.evaluate(() => window.__engine.debug.systemResumeAudio());
    await sleep(400);
    const a2 = await st();
    check('系統自己恢復音訊時：引擎仍停住等老師（再停一次，聲音不會自己播）', a2.paused && a2.audioState !== 'running' && Math.abs(a2.cueTime - a1.cueTime) < 0.1, `音訊 ${a2.audioState}、${a1.cueTime}→${a2.cueTime}`);
    await page.keyboard.press('Period');
    await sleep(500);
    sy = await sync();
    s = await st();
    check('老師按繼續後：音訊恢復、字幕與語音時間差 ≤ 50 ms、發聲中的對白 ≤ 1', !s.paused && s.audioState === 'running' && voN(s) <= 1 && (sy.length === 0 || maxDiff(sy) <= 50), `差 ${maxDiff(sy)} ms、對白 ${voN(s)}`);
    // 開頭靜音（HDMI 吞音）：400 ms 時畫面停在第一格、聲音一起延後
    await page.evaluate(() => window.__engine.debug.setLeadIn(400));
    await page.evaluate(() => window.__engine.gotoCue('a2_c004', { mode: 'play' }));
    await sleep(200);
    const l1 = await st();
    await waitFor(() => window.__engine.getState().cueTime > 1.5, null, 8000);
    sy = await sync();
    check('開頭靜音 400 ms：按下後先停在第一格，之後照常播、字幕與語音時間差 ≤ 50 ms', l1.leadInMs === 400 && l1.cueTime === 0 && sy.length === 1 && maxDiff(sy) <= 50, `0.2 秒時 t=${l1.cueTime}；差 ${maxDiff(sy)} ms`);
    await page.evaluate(() => window.__engine.debug.setLeadIn(0));
  }
  check('G4 操作測試沒有頁面錯誤', errors.length === 0, errors.slice(0, 3).join(' | '));
  await page.close();
}

await browser.close();
const failed = results.filter((r) => !r.ok);
console.log(`\n[engine-test] ${results.length - failed.length}／${results.length} 項通過${failed.length ? `；失敗：${failed.map((f) => f.name).join('、')}` : ''}`);
process.exit(failed.length ? 1 : 0);
