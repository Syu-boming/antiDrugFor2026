// a2 段落檔產生器（a2 代理製作紀錄；G5 修正第 1 輪改寫，第一批版本留在 gen_a2_b1.mjs）：
// 讀 G5 第一階段底稿（a2_skeleton.json＝commit 3b5dd0e 的 app/cues/show/a2.json），覆寫各 cue 的表演，
// 輸出 a2.json（node review/G5/a2/scripts/gen_a2.mjs <輸出路徑>；預設寫到同資料夾）。
// G4 cue（a2_c002、a2_c004）的表演、台詞、題目、查核點原樣保留（a2_c004 只加 set: a2_shop，畫面與 workshop_g4 相同）。
//
// 修正第 1 輪（review/G5/qa/b1_director.md、b1_safety.md、b1_art.md 的第二幕條目）：
//   - a2_c001：L1 改成腕背短線（a2_shop 景畫漸淡）、右手握竹篾放膝上、推近終點以右腕為中心；折折坐在工作台上、說 _03 時在畫面裡；
//     推近與 _03 重疊（拿掉空轉）。a2_c001 用 a2_shop、a2_c002 用 workshop_g4 → 老師按下一步時自動漸暗換場，
//     停格（找找看 2）看得到線，a2_c002 從沒有線的畫面開始（接得上）。
//   - 題卡 Q2、Q3：SHOW_INTERFACE.md 第 12 節，折折上台（hush → 摺成題卡）；揭答、點燈留在原位 idle；
//     進出題卡的大幅縮放改成硬切（細格光敏）。
//   - a2_c008：開頭補手部近景（a2_shop 的獨立小台：雙手想摺燈籠紙、線一頓一頓、紙皺成一團）；
//     這段時間阿樂叔叔線放鬆、坐回凳子、手放回膝上；切回來時低頭看手（puppet.nod）。孩子換到工作台右邊（身後是牆，投影亮度 ≥ 0.50）。
//     必要旁白二字幕：手動分頁，「不能就說他吸毒，」不拆開，頁起點對上配音停頓。
//   - a2_c012：求助站建在 a2_shop 裡，去程漸暗換場、回程用動作接（葉護理師往畫面左走 → 店裡從右邊走進來），拿掉第二次漸暗；
//     葉護理師手機貼耳 2 秒（新姿勢 crouchphone）＋撥號沒人接音效；阿樂叔叔坐著低頭、雙手在膝上、1 次小拉扯。
//   - a2_c013：阿樂叔叔坐著低頭、雙手在膝上（不再平舉），慢慢說話時兩次慢點頭、葉護理師說完點頭兩下、1 次小拉扯；孩子站在開著的店門前。
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
const S = dirname(fileURLToPath(import.meta.url));
const orig = JSON.parse(readFileSync(`${S}/a2_skeleton.json`, 'utf8'));
const A = (name, start, duration, params, target) => {
  const a = { name, start };
  if (target) a.target = target;
  if (duration !== undefined && duration !== null) a.duration = duration;
  if (params) a.params = params;
  return a;
};
const P = (name, target, start, duration, params) => A(name, start, duration, params, target);
const r2 = (x) => Math.round(x * 100) / 100;

const out = JSON.parse(JSON.stringify(orig));
out.characters.ye.facing = 1; // 葉護理師的站姿、蹲姿原圖都朝畫面左（看向阿樂叔叔／從左邊來的孩子）
const set = (id, patch) => { const c = out.cues.find((x) => x.id === id); Object.assign(c, patch); return c; };
const cue = (id) => out.cues.find((x) => x.id === id);
const SHOP = 'a2_shop';
const HELP_X = 40;          // a2_shop.ts 的求助站位置
// 題卡模式折折站位（SHOW_INTERFACE.md 第 12 節建議 x≈−4.7、z≈3.4；quiz 鏡位下 z 3.4 會被 DOM 題卡蓋住大半，往前移到台口邊 z 4.2：
// 腳在畫面 89%、頭在題卡下緣之下，高度約畫面 9%）
const ZZ_QUIZ = { x: -4.7, y: 0, z: 4.2 };

// ---------------------------------------------------------------- a2_c001 叔叔的手（找找看 2）
// 孩子站在工作台右端、靠近叔叔一點；叔叔說沒事後切到叔叔中景，鏡頭慢推到右腕（手上握竹篾、放膝上）。
// 折折坐在工作台左段（a0 也坐在工作台上），推近後在畫面右緣露出，說「大家仔細看……」。
const WRIST2 = { pos: [-2.7, 1.4, 7.1], target: [-2.7, 1.3, 0], fov: 20 };
const ALE_MED = { pos: [-2.5, 1.65, 9.95], target: [-2.5, 1.55, 0], fov: 20 };
const K1 = 'a2_c001_02.end';
set('a2_c001', {
  set: SHOP,
  initialState: {
    stage: { curtain: 'open', camera: 'g4_mid', light: 1 },
    characters: {
      ale: { visible: true, emotion: 'smile', sit: 0.35, strings: ['wrist'], stringTension: 0.55 },
      // 孩子在工作台右端外（身後是牆：投影亮度 ≥ 0.50）
      xiaoyu: { visible: true, emotion: 'smile', x: 2.25, z: -0.5, facing: -1 },
      xiaoqing: { visible: true, emotion: 'smile', pose: 'watch', x: 1.3, z: 0.45 },
      zhezhe: { visible: true, emotion: 'curious', x: -1.2, y: 1.4, z: -0.6 },
    },
  },
  animation: [
    // L1：引擎的腕線（a2_shop 只留腕背往上約 1.5 個手掌長、往上漸淡）；不透明度 0.98 讓材質一直是半透明模式
    P('strings.fade', 'ale', 0, 0.01, { anchors: ['wrist'], to: 0.98 }),
    P('puppet.sit', 'ale', 0.3, 1.3, { to: 1 }),
    P('puppet.face', 'xiaoyu', 1.2, null, { emotion: 'worried' }),
    P('zhezhe.look', 'zhezhe', 'a2_c001_01+0.3', 0.8, { yaw: -0.3 }),
    P('puppet.tilt', 'ale', 'a2_c001_02-0.1', 0.6, { to: 0.05 }),
    P('puppet.wave', 'ale', 'a2_c001_02+0.1', 1.5, {}),
    P('puppet.tilt', 'ale', K1 + '-0.3', 0.7, { to: 0 }),
    P('puppet.face', 'xiaoyu', K1 + '-0.6', null, { emotion: 'smile' }),
    // 孩子留在原地（a2_c002 前會換場漸暗，不必走回 G4 站位；少一段走路＝細格光敏）
    P('puppet.blink', 'xiaoqing', K1 + '+0.3'),
    // 切到阿樂叔叔中景，再慢推到右腕（4.5 秒、正弦緩動；縮放約 1.4 倍）——
    // 從 g4_mid 一路推進來是 2.4 倍縮放，細格光敏每秒 5 次（主線裁定：大幅縮放改硬切）。折折轉回來看觀眾，推近途中開口
    A('camera.cut', K1 + '+0.9', 0, { to: ALE_MED }),
    A('camera.move', K1 + '+1.1', 4.5, { to: WRIST2 }),
    P('zhezhe.look', 'zhezhe', K1 + '+0.5', 0.8, { yaw: 0 }),
  ],
  musicLevel: 0.65,
  voStart: 1.6,
  tail: 2.0,
});
{
  const c = cue('a2_c001');
  c.lines[1].start = 'a2_c001_01.end+0.45';
  c.lines[2].start = K1 + '+1.5';
  c.teacherNote = '找找看 2（約 30 秒，不計獎）：停格是阿樂叔叔的右手腕近景（手裡握著竹篾），腕背有一小段細細的灰色紙線。點一位。答案：手腕上多了一條細細的線。回應：「看得很仔細。這條線是什麼意思？我們繼續看。」按下一步時畫面會先暗下來再接下一段。';
}

// ---------------------------------------------------------------- a2_c003 那個小盒子（回想小窗，a2_memory）
set('a2_c003', {
  sceneId: 'a2_memory',
  set: 'a2_memory',
  initialState: {
    stage: { curtain: 'open', camera: 'a2_memory_cu', light: 0.94, desat: 0.5 },
    characters: {
      xiaoqing: { visible: true, pose: 'worried', emotion: 'worried', x: 2.15, z: 0.7, facing: 1 },
    },
  },
  animation: [
    P('puppet.face', 'xiaoqing', 'a2_c003_01+0.4', null, { emotion: 'neutral' }),
    P('puppet.blink', 'xiaoqing', 'a2_c003_01.end+0.2'),
    P('puppet.face', 'xiaoqing', 'a2_c003_02+3.1', null, { emotion: 'worried' }),
  ],
  audioId: null,
  music: [{ id: 'music_shiny', at: 0, loop: true, fade: 1.5, gain: 0.5 }],
  musicLevel: 0.7,
  voStart: 1.45,
  tail: 1.8,
});

// ---------------------------------------------------------------- a2_c004（G4 代表鏡頭）：只換成 a2_shop（畫面相同），之後的題卡不必換景漸暗
cue('a2_c004').set = SHOP;

// ---------------------------------------------------------------- 題卡（Q2、Q3）：第 12 節折折上台；進出題卡硬切（細格光敏）
const ZZ_ON = { visible: true, emotion: 'happy', ...ZZ_QUIZ };
const quizAnims = () => [
  P('zhezhe.hush', 'zhezhe', -0.55, 1.4),
  P('zhezhe.fold', 'zhezhe', 0.1, 1.3, { form: 'card' }),
  A('camera.cut', 0, 0, { to: 'quiz' }),
  A('light.dim', 0, 1.2, { to: 0.55 }),
  A('quiz.show', 0.7, 0.6),
];
const revealAnims = () => [
  P('zhezhe.fold', 'zhezhe', 0.05, 1.0, { form: 'idle' }),
  A('quiz.reveal', 0.3, 0.45),
];
const lampAnims = (lid, idx) => [
  A('lamp.light', 0.3, 1.5, { index: idx }),
  // 點燈那句說完：折折小跳步退到題卡台口左外（題卡收起前已出畫），題卡收起、燈光恢復，再硬切回故事鏡位
  P('zhezhe.walkTo', 'zhezhe', `${lid}.end+0.05`, 1.5, { pos: [ZZ_QUIZ.x - 3.9, 0, ZZ_QUIZ.z] }),
  A('quiz.hide', `${lid}.end+0.3`, 0.6),
  A('light.restore', `${lid}.end+0.3`, 1.2),
  A('camera.cut', `${lid}.end+0.95`, 0, { to: 'g4_mid' }),
];

// Q2：起始狀態接 a2_c004 的停格
const C004_END_CHARS = {
  ale: { visible: true, pose: 'pulled_half', strings: ['wrist', 'elbow', 'knee'], stringTension: 1, emotion: 'confused', hand: 'grab' },
  xiaoqing: { visible: true, pose: 'worried', emotion: 'worried' },
  xiaoyu: { visible: true, pose: 'stepback', emotion: 'surprised' },
};
const C004_STAGE = { desat: 0.5, spot: 1, spotTarget: 'ale' };
set('a2_c005', { set: SHOP, initialState: { stage: { curtain: 'open', camera: 'g4_mid', light: 0.94, ...C004_STAGE }, characters: { ...C004_END_CHARS, zhezhe: ZZ_ON } }, animation: quizAnims() });
set('a2_c006', { set: SHOP, initialState: { stage: { curtain: 'open', camera: 'quiz', light: 0.55, quiz: true, ...C004_STAGE }, characters: { ...C004_END_CHARS, zhezhe: ZZ_ON } }, animation: revealAnims() });
set('a2_c007', { set: SHOP, initialState: { stage: { curtain: 'open', camera: 'quiz', light: 0.55, quiz: true, ...C004_STAGE }, characters: { ...C004_END_CHARS, zhezhe: ZZ_ON } }, animation: lampAnims('a2_c007_01', 2) });
cue('a2_c007').tail = 1.3;

// ---------------------------------------------------------------- a2_c008 想不起來（必要旁白二）
// 手部近景（a2_shop 小台，表演時間見 a2_shop.ts INSERT_BEATS：想對摺 → 第 1 下 1.3 秒 → 再摺 → 第 2 下 2.75 秒 → 再摺 → 第 3 下 4.15 秒 → 紙團落下）
// 同時主舞台的阿樂叔叔：線放鬆、坐回凳子、手放回膝上（畫面在近景，看不到過程）→ 切回來低頭看手 → 兩個孩子小聲問 → 必要旁白二（畫面靜止）。
const ALE_LOOK = { pos: [-2.3, 1.72, 10.8], target: [-2.3, 1.62, 0], fov: 20 };
const KIDS2 = { pos: [2.0, 1.98, 8.4], target: [2.0, 1.88, 0], fov: 20 };
const ALE_PULLED = { visible: true, pose: 'pulled_half', strings: ['wrist', 'elbow', 'knee'], stringTension: 1, emotion: 'confused', hand: 'grab' };
/** 坐著、線微鬆（仍看得見、微繃）、雙手垂在膝旁 */
const ALE_SEATED = { visible: true, sit: 1, strings: ['wrist', 'elbow', 'knee'], stringTension: 0.45, emotion: 'worried' };
// 孩子在工作台右端之外（身後是牆；中景 g4_mid 與雙人近景都量過，投影亮度 ≥ 0.50），前景 z 1.5／1.1
const KQ = { x: 1.6, z: 1.5, facing: 1 };
const KY = { x: 2.6, z: 1.1, facing: -1 };
const INS_END = 5.3;
set('a2_c008', {
  set: SHOP,
  initialState: {
    stage: { curtain: 'open', camera: 'g4_mid', light: 1, desat: 0.5, spot: 1, spotTarget: 'ale' },
    characters: {
      ale: ALE_PULLED,
      xiaoqing: { visible: true, pose: 'worried', emotion: 'worried', ...KQ },
      xiaoyu: { visible: true, pose: 'stand', emotion: 'worried', ...KY },
    },
  },
  animation: [
    A('camera.cut', 0, 0, { to: 'a2s_hands' }),
    // 主舞台（看不到）：線放鬆到微繃、坐回去、放開桌邊、身體回正
    P('strings.loosen', 'ale', 0.8, 2.0, { anchors: ['wrist', 'elbow', 'knee'], to: 0.45 }),
    P('puppet.sit', 'ale', 0.8, 1.6, { to: 1 }),
    P('puppet.grab', 'ale', 0.8, 1.2, { to: 0 }),
    P('puppet.lean', 'ale', 0.8, 1.2, { to: 0 }),
    P('puppet.tilt', 'ale', 0.8, 1.0, { to: 0 }),
    P('puppet.face', 'ale', 1.0, null, { emotion: 'worried' }),
    A('fx.spot', 0.8, 0.01, { to: 0 }),
    // 切回阿樂叔叔：低頭看自己的手（慢慢低下、說完才抬起）
    A('camera.cut', INS_END, 0, { to: ALE_LOOK }),
    P('puppet.nod', 'ale', INS_END - 0.3, 4.8, { count: 1, depth: 0.9 }),
    P('puppet.tilt', 'ale', 'a2_c008_02+0.3', 0.9, { to: 0.07 }),
    P('puppet.face', 'ale', 'a2_c008_02', null, { emotion: 'confused' }),
    // 兩個孩子（雙人近景）：小宇靠近小晴、身體傾向她，小聲問
    A('camera.cut', 'a2_c008_02.end+0.35', 0, { to: KIDS2 }),
    P('puppet.tilt', 'ale', 'a2_c008_02.end+0.4', 0.8, { to: 0 }),
    P('puppet.face', 'ale', 'a2_c008_02.end+0.4', null, { emotion: 'worried' }),
    P('puppet.move', 'xiaoyu', 'a2_c008_02.end+0.5', 0.6, { dx: -0.2 }),
    P('puppet.lean', 'xiaoyu', 'a2_c008_02.end+0.55', 0.6, { to: -0.045 }),
    P('puppet.lean', 'xiaoqing', 'a2_c008_03+0.6', 0.6, { to: 0.03 }),
    P('puppet.lean', 'xiaoyu', 'a2_c008_04+0.2', 0.7, { to: 0 }),
    P('puppet.face', 'xiaoqing', 'a2_c008_04+1.4', null, { emotion: 'neutral' }),
    P('puppet.lean', 'xiaoqing', 'a2_c008_04+1.4', 0.7, { to: 0 }),
    // 必要旁白二：回到中景群體構圖，畫面靜止（只有呼吸、眨眼）
    A('camera.cut', 'a2_c008_04.end+0.25', 0, { to: 'g4_mid' }),
  ],
  sfx: [
    { id: 'sfx_paper_rustle', at: 0.4, gain: 0.4 },
    { id: 'sfx_string_taut', at: 1.3, gain: 0.55 },
    { id: 'sfx_paper_rustle', at: 1.95, gain: 0.35 },
    { id: 'sfx_string_taut', at: 2.75, gain: 0.55 },
    { id: 'sfx_string_taut', at: 4.15, gain: 0.55 },
    { id: 'sfx_paper_rustle', at: 4.25, gain: 0.5 },
  ],
  musicLevel: 0.72,
  voStart: INS_END + 0.2,
  tail: 1.8,
});
{
  const c = cue('a2_c008');
  c.lines[1].start = 'a2_c008_01.end+0.45';
  c.lines[2].start = 'a2_c008_02.end+0.75';
  c.lines[3].start = 'a2_c008_03.end+0.4';
  c.lines[4].start = 'a2_c008_04.end+0.6';
  // 必要旁白二（一字不改）：手動分頁。第 1 頁「不過，看見一個人站不穩，」→ 第 2 頁「不能就說他吸毒，／也可能有其他身體狀況。」→ 第 3 頁「我們要先找大人幫忙。」
  // 頁的時間依字數比例分配：第 2、3 頁起點落在配音停頓（3.6、9.6 秒）附近，「不能就說他吸毒」整句在同一行
  c.lines[4].text = '不過，看見一個人站不穩，\n\n不能就說他吸毒，\n也可能有其他身體狀況。\n\n我們要先找大人幫忙。';
  c.teacherNote = '開頭是阿樂叔叔的手部近景：想摺燈籠紙，手被線拉得一頓一頓，紙皺成一團（無台詞約 5 秒）。必要旁白二（一字不改）時畫面是穩定的中景：阿樂叔叔坐在左邊、兩個孩子在右前方，沒有人動作。播完停格，等老師按下一步。';
}

// Q3：起始狀態接 a2_c008 的停格
const C008_END_CHARS = {
  ale: ALE_SEATED,
  xiaoqing: { visible: true, pose: 'worried', emotion: 'neutral', ...KQ },
  xiaoyu: { visible: true, pose: 'stand', emotion: 'worried', ...KY, x: KY.x - 0.2 },
};
set('a2_c009', { set: SHOP, initialState: { stage: { curtain: 'open', camera: 'g4_mid', light: 1, desat: 0.5 }, characters: { ...C008_END_CHARS, zhezhe: ZZ_ON } }, animation: quizAnims() });
set('a2_c010', { set: SHOP, initialState: { stage: { curtain: 'open', camera: 'quiz', light: 0.55, quiz: true, desat: 0.5 }, characters: { ...C008_END_CHARS, zhezhe: ZZ_ON } }, animation: revealAnims() });
set('a2_c011', { set: SHOP, initialState: { stage: { curtain: 'open', camera: 'quiz', light: 0.55, quiz: true, desat: 0.5 }, characters: { ...C008_END_CHARS, zhezhe: ZZ_ON } }, animation: lampAnims('a2_c011_01', 3) });
cue('a2_c011').tail = 1.3;

// ---------------------------------------------------------------- a2_c012 去找葉護理師
// 店內：兩人往店門（右）走出去，起步就漸暗換場 → 求助站（a2_shop 的 x＝HELP_X）：孩子已在葉護理師身邊，小晴伸手求助，葉護理師擔心、點頭
// → 直接切回店裡（不再漸暗）：葉護理師已走到阿樂叔叔身邊，再往前一小步、蹲下平視 → 兩人近景：打電話沒人接 → 中景（孩子在右前方）。
// 細格光敏：孩子起步就漸暗、求助站不再走進來、店裡葉護理師不從畫面外走進來、同一區域的換姿勢與字幕出現間隔 ≥ 1 秒；
// 移動用 puppet.move（紙偶平移，沒有 puppet.exit 每秒 3.2 下的走路起伏——起伏讓頭頂、鞋子的邊緣在細格裡每秒變化 5 次以上）。
const TWO2 = { pos: [-2.2, 1.95, 13.0], target: [-2.2, 1.85, 0], fov: 20 };    // 店裡中景：葉護理師站在阿樂叔叔旁邊（全身入鏡），往前一步蹲下
const TWO = { pos: [-2.1, 1.5, 11.6], target: [-2.1, 1.4, 0], fov: 20 };       // 蹲下後的兩人近景（平視、打電話）
const SHOP_C = { pos: [-0.3, 1.5, 14.6], target: [-0.3, 1.42, 0], fov: 20 };
const RUN = 2.6;             // 往右出畫的距離（大部分在漸暗中完成）
const D1 = 1.0;              // 漸暗開始（孩子剛起步就慢慢暗下來）
const H0 = D1 + 0.62;        // 全暗：換到求助站
const YE_H = HELP_X + 1.9;   // 葉護理師在求助站的位置
const QH = { x: HELP_X + 0.55 };   // 求助站：小晴在葉護理師左前方伸手（z 照店裡的站位）
const YH = { x: HELP_X - 0.45 };   // 小宇在小晴左後方
const CUT = H0 + 1.85;       // 接回店裡（葉護理師點頭之後）
const YE_SHOP = -0.05;       // 店裡：切過來時葉護理師已經走到阿樂叔叔旁邊，再往前一小步（→ −0.45）蹲下；伸出的手離膝前紙環與膝線 ≥ 0.4，不會像握著線
const YE_IN = -0.4;
const PARK = 3.9;            // 兩人鏡頭時孩子先停在畫面右外（x＋PARK），切中景前回到站位
const QX0 = KQ.x + RUN, YX0 = KY.x - 0.2 + RUN;   // 走出去之後的位置
set('a2_c012', {
  set: SHOP,
  initialState: {
    stage: { curtain: 'open', camera: 'g4_mid', light: 1, desat: 0.5 },
    characters: {
      ale: ALE_SEATED,
      xiaoqing: { visible: true, pose: 'worried', emotion: 'neutral', ...KQ },
      xiaoyu: { visible: true, pose: 'stand', emotion: 'worried', ...KY, x: KY.x - 0.2 },
      ye: { visible: true, pose: 'stand', emotion: 'neutral', x: YE_H, z: 0.1, facing: 1 },
    },
  },
  animation: [
    // 店內：往右跑出店門（阿樂叔叔低頭）
    P('puppet.nod', 'ale', 0.2, 2.2, { count: 1, depth: 0.6 }),
    // 兩人轉身往店門（右）一起出去：起步後畫面就漸暗（細格光敏：不在亮的畫面裡換姿勢＋長距離移動）
    { ...P('puppet.move', 'xiaoyu', 0.35, 1.3, { dx: RUN }), ease: 'in' },
    { ...P('puppet.move', 'xiaoqing', 0.45, 1.3, { dx: RUN }), ease: 'in' },
    P('puppet.lean', 'xiaoqing', 0.2, 0.5, { to: 0.03 }),
    A('fade.out', D1, 0.6, {}),
    // 全暗：換到求助站（孩子已在葉護理師身邊）
    A('camera.cut', H0, 0, { to: 'a2s_help_mid' }),
    A('fx.desat', H0, 0.03, { to: 0.3 }),
    P('puppet.move', 'xiaoqing', H0, 0.01, { dx: r2(QH.x - QX0) }),
    P('puppet.move', 'xiaoyu', H0, 0.01, { dx: r2(YH.x - YX0) }),
    P('puppet.pose', 'xiaoqing', H0 + 0.01, 0.01, { pose: 'reach' }),
    P('puppet.pose', 'xiaoyu', H0 + 0.01, 0.01, { pose: 'stand' }),
    A('fade.in', H0 + 0.08, 0.6, {}),
    // 求助站：小晴伸手 → 葉護理師擔心、身體前傾、點頭 → 起步往畫面左走（孩子帶路，下一個鏡頭在店裡）
    P('puppet.face', 'ye', H0 + 0.5, null, { emotion: 'worried' }),
    P('puppet.lean', 'ye', H0 + 0.7, 0.45, { to: -0.035 }),
    P('puppet.nod', 'ye', H0 + 1.0, 0.8, { count: 1 }),
    P('puppet.lean', 'ye', H0 + 1.4, 0.3, { to: 0 }),
    // 接回店裡：葉護理師從右邊走進來、蹲下；孩子先停在畫面右外
    A('camera.cut', CUT, 0, { to: TWO2 }),
    A('fx.desat', CUT, 0.03, { to: 0.32 }),
    P('puppet.move', 'ye', CUT, 0.01, { dx: r2(YE_SHOP - YE_H) }),
    P('puppet.move', 'ye', CUT + 0.35, 0.8, { dx: YE_IN }),
    P('puppet.pose', 'ye', CUT + 1.2, 0.24, { pose: 'crouch' }),
    P('puppet.move', 'xiaoqing', CUT, 0.01, { dx: r2(KQ.x + PARK - QH.x) }),
    P('puppet.move', 'xiaoyu', CUT, 0.01, { dx: r2(KY.x - 0.2 + PARK - YH.x) }),
    P('puppet.pose', 'xiaoqing', CUT + 0.02, 0.01, { pose: 'worried' }),
    P('puppet.lean', 'xiaoqing', CUT + 0.02, 0.01, { to: 0 }),
    // 蹲下後切到兩人近景；孩子從停的位置回到站位（兩個位置都在這個鏡頭外）
    A('camera.cut', CUT + 1.9, 0, { to: TWO }),
    P('puppet.move', 'xiaoqing', CUT + 2.0, 0.01, { dx: -PARK }),
    P('puppet.move', 'xiaoyu', CUT + 2.0, 0.01, { dx: -PARK }),
    A('fx.desat', CUT + 0.8, 3.0, { to: 0.2 }),
    P('puppet.nod', 'ale', CUT + 0.3, 2.6, { count: 1, depth: 0.5 }),
    P('puppet.tilt', 'ale', 'a2_c012_02-0.2', 0.8, { to: 0.08 }),
    P('puppet.tilt', 'ale', 'a2_c012_02.end+0.5', 0.9, { to: 0.03 }),
    // 打電話：手機貼耳約 2 秒（撥號、等、沒人接）→ 放下、表情轉擔心 → 「你家人的電話沒人接……」
    P('puppet.pose', 'ye', 'a2_c012_02.end+0.3', 0.24, { pose: 'crouchphone' }),
    P('puppet.pose', 'ye', 'a2_c012_02.end+2.35', 0.24, { pose: 'crouch' }),
    P('puppet.face', 'ye', 'a2_c012_02.end+2.6', null, { emotion: 'worried' }),
    // 等電話時，阿樂叔叔的腕線被拉了一下（線先繃直，身體被帶一點，0.4 秒後落回）
    P('strings.tension', 'ale', 'a2_c012_02.end+1.35', 0.12, { anchors: ['wrist', 'elbow'], to: 1 }),
    P('puppet.lean', 'ale', 'a2_c012_02.end+1.4', 0.3, { to: 0.035 }),
    P('puppet.lean', 'ale', 'a2_c012_02.end+1.8', 0.5, { to: 0 }),
    P('strings.tension', 'ale', 'a2_c012_02.end+1.75', 0.5, { anchors: ['wrist', 'elbow'], to: 0.45 }),
    // 中景：小晴說盒子的事（身體微微傾向葉護理師，不比手勢、不指人）
    A('camera.cut', 'a2_c012_03.end+0.2', 0, { to: SHOP_C }),
    P('puppet.lean', 'xiaoqing', 'a2_c012_04-0.1', 0.6, { to: -0.035 }),
    P('puppet.lean', 'xiaoqing', 'a2_c012_04.end+0.3', 0.7, { to: 0 }),
    P('puppet.nod', 'ye', 'a2_c012_05+0.2', 1.0, { count: 1 }),
  ],
  audioId: null,
  music: [
    { id: 'music_courage', at: 0.15, loop: false, fade: 1.0, gain: 1 },
    { id: 'music_town', at: CUT - 0.1, loop: true, fade: 1.6, gain: 0.5 },
  ],
  musicLevel: 0.75,
  sfx: [
    { id: 'sfx_footsteps', at: 0.35, gain: 0.5 },
    { id: 'sfx_crowd_short', at: H0 + 0.1, gain: 0.45 },
    { id: 'sfx_phone_noanswer', at: 'a2_c012_02.end+0.6', gain: 0.6 },
    { id: 'sfx_string_taut', at: 'a2_c012_02.end+1.35', gain: 0.35 },
  ],
  voStart: CUT + 2.25,
  tail: 1.8,
});
{
  const c = cue('a2_c012');
  c.lines[1].start = 'a2_c012_01.end+0.45';
  c.lines[2].start = 'a2_c012_02.end+3.45';
  c.lines[3].start = 'a2_c012_03.end+0.45';
  c.lines[4].start = 'a2_c012_04.end+0.45';
  c.teacherNote = '兩個孩子往右跑出店門、到廣場另一頭的求助站（帳篷上是手捧愛心圖示，沒有紅十字）找葉護理師；葉護理師跟著回到店裡、蹲下和阿樂叔叔平視、拿手機打給他的家人沒人接、答應請警察去看盒子。播完停格，等老師按下一步。';
}

// ---------------------------------------------------------------- a2_c013 說出實情（懸念）：店外傍晚（a2_window）
// 阿樂叔叔坐著低頭、雙手垂在膝旁（線微鬆）；慢慢說（兩次慢點頭）→ 小拉扯 1 次 → 葉護理師說完，他點頭兩下。
// 孩子站在開著的店門前（a2_window 的暖光門口：身後投影亮度 ≥ 0.50）；折折坐在窗台上，回頭看窗裡空空的工作台。
set('a2_c013', {
  sceneId: 'a2_window',
  set: 'a2_window',
  initialState: {
    stage: { curtain: 'open', camera: 'a2_win_wide', light: 1, desat: 0.12 },
    characters: {
      ale: { ...ALE_SEATED, x: -2.95, z: -1.5 },
      ye: { visible: true, pose: 'crouch', emotion: 'worried', x: -1.1, z: -1.15, facing: 1 },
      xiaoqing: { visible: true, pose: 'watch', emotion: 'worried', x: 2.05, z: 0.55, facing: 1 },
      xiaoyu: { visible: true, pose: 'stand', emotion: 'worried', x: 3.05, z: 0.95, facing: -1 },
      zhezhe: { visible: true, emotion: 'worried', x: -0.62, y: 0.88, z: -0.45 },
    },
  },
  animation: [
    A('light.dim', 0.5, 6.0, { to: 0.88 }),
    P('puppet.lean', 'ye', 'a2_c013_01', 1.2, { to: -0.03 }),
    // 「低頭慢慢說話」：兩次慢點頭（各約 2.2 秒）
    P('puppet.nod', 'ale', 'a2_c013_01+0.2', 4.6, { count: 2, depth: 0.8 }),
    P('puppet.nod', 'ale', 'a2_c013_02+0.3', 2.6, { count: 1, depth: 0.9 }),
    // 「他就試了。」之後：腕線被拉了一下（線先繃直，身體被帶一點，0.4 秒後落回）
    P('strings.tension', 'ale', 'a2_c013_02.end+0.15', 0.12, { anchors: ['wrist', 'elbow'], to: 1 }),
    P('puppet.lean', 'ale', 'a2_c013_02.end+0.2', 0.3, { to: 0.035 }),
    P('puppet.lean', 'ale', 'a2_c013_02.end+0.6', 0.5, { to: 0 }),
    P('strings.tension', 'ale', 'a2_c013_02.end+0.55', 0.5, { anchors: ['wrist', 'elbow'], to: 0.45 }),
    // 葉護理師說完，阿樂叔叔點頭兩下
    P('puppet.nod', 'ale', 'a2_c013_03.end-0.6', 2.0, { count: 2, depth: 1 }),
    // 筆記本特寫：小晴在問號旁邊又畫一個問號（程式畫線，見 a2_window.ts）
    A('camera.cut', 'a2_c013_03.end+0.5', 0, { to: 'a2_win_note' }),
    A('camera.cut', 'a2_c013_03.end+3.1', 0, { to: 'a2_win_kids' }),
    // 折折回頭看空空的工作台（畫面左邊的窗），耳朵垂下
    P('zhezhe.look', 'zhezhe', 'a2_c013_03.end+3.4', 0.9, { yaw: -0.45 }),
    P('zhezhe.emote', 'zhezhe', 'a2_c013_03.end+3.9', null, { emotion: 'sad' }),
  ],
  audioId: null,
  music: [
    { id: 'music_shiny', at: 0, loop: true, fade: 1.5, gain: 0.45 },
    { id: 'music_town_night', at: 'a2_c013_02.end+0.4', loop: true, fade: 2.0, gain: 0.85 },
  ],
  musicLevel: 0.72,
  sfx: [
    { id: 'sfx_wind', at: 0.6, gain: 0.3 },
    { id: 'sfx_string_taut', at: 'a2_c013_02.end+0.15', gain: 0.3 },
  ],
  voStart: 1.6,
  tail: 2.2,
});
{
  const c = cue('a2_c013');
  c.lines[2].start = 'a2_c013_02.end+0.8';
  c.lines[3].start = 'a2_c013_03.end+4.7';
  c.lines[4].start = 'a2_c013_04.end+0.45';
  c.teacherNote = '傍晚的店外：窗裡葉護理師蹲在阿樂叔叔身邊，阿樂叔叔低著頭慢慢說；右上角剪影回憶小窗在阿樂叔叔伸手接過盒子之前就收起（不出現打開或使用）。孩子在開著的店門口等。筆記本特寫：小晴又畫一個問號；折折回頭看工作台、耳朵垂下。播完停格，等老師按下一步。';
}

writeFileSync(process.argv[2] ?? join(S, 'a2.json'), JSON.stringify(out, null, 1) + '\n');
console.log('wrote a2.json');
