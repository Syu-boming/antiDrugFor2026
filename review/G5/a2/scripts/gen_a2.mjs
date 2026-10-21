// a2 段落檔產生器（a2 代理製作紀錄）：讀 G5 第一階段底稿（a2_skeleton.json＝commit 3b5dd0e 的 app/cues/show/a2.json），覆寫各 cue 的表演，
// 輸出 a2.json（node review/G5/a2/scripts/gen_a2.mjs <輸出路徑>；預設寫到同資料夾）。G4 cue（a2_c002、a2_c004）、台詞、題目、查核點原樣保留。
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
const S = dirname(fileURLToPath(import.meta.url));
const orig = JSON.parse(readFileSync(`${S}/a2_skeleton.json`, 'utf8'));
const byId = Object.fromEntries(orig.cues.map((c) => [c.id, c]));
const A = (name, start, duration, params, target) => {
  const a = { name, start };
  if (target) a.target = target;
  if (duration !== undefined && duration !== null) a.duration = duration;
  if (params) a.params = params;
  return a;
};
const P = (name, target, start, duration, params) => A(name, start, duration, params, target);

const out = JSON.parse(JSON.stringify(orig));
out.characters.ye.facing = 1; // 葉護理師的站姿、蹲姿原圖都朝畫面左（看向阿樂叔叔／從左邊來的孩子）
const set = (id, patch) => { const c = out.cues.find((x) => x.id === id); Object.assign(c, patch); return c; };

// ---------------------------------------------------------------- a2_c001 叔叔的手（找找看 2）
// 孩子先站在工作台前、靠近叔叔（群體）；叔叔說沒事後兩人走回 G4 站位（a2_c002 起始），鏡頭推近手腕。
const WRIST_CU = { pos: [-1.8, 1.95, 8.6], target: [-1.8, 1.85, 0], fov: 20 };
const K1 = 'a2_c001_02.end';
set('a2_c001', {
  initialState: {
    stage: { curtain: 'open', camera: 'g4_mid', light: 1 },
    characters: {
      ale: { visible: true, emotion: 'smile', sit: 0.35, strings: ['wrist'], stringTension: 0.25 },
      xiaoyu: { visible: true, emotion: 'smile', x: 1.0, z: -0.5, facing: -1 },
      xiaoqing: { visible: true, emotion: 'smile', pose: 'watch', x: 0.35, z: 0.45 },
    },
  },
  animation: [
    P('strings.fade', 'ale', 0, 0.01, { anchors: ['wrist'], to: 0.72 }),
    P('puppet.sit', 'ale', 0.3, 1.3, { to: 1 }),
    P('puppet.face', 'xiaoyu', 1.2, null, { emotion: 'worried' }),
    P('puppet.tilt', 'ale', 'a2_c001_02-0.1', 0.6, { to: 0.05 }),
    P('puppet.wave', 'ale', 'a2_c001_02+0.1', 1.5, {}),
    P('puppet.tilt', 'ale', K1 + '-0.3', 0.7, { to: 0 }),
    P('puppet.face', 'xiaoyu', K1 + '-0.6', null, { emotion: 'smile' }),
    // 孩子走回原位（往右；換姿勢在起步時翻面）
    // （光敏：兩人錯開走，同一區域每秒變化 ≤ 3 次）
    P('puppet.pose', 'xiaoqing', K1 + '-0.15', 0.24, { pose: 'walk' }),
    P('puppet.exit', 'xiaoqing', K1 + '-0.05', 1.5, { to: 1.5 }),
    P('puppet.pose', 'xiaoqing', K1 + '+1.35', 0.24, { pose: 'watch' }),
    P('puppet.pose', 'xiaoyu', K1 + '+1.2', 0.24, { pose: 'walk_r' }),
    P('puppet.exit', 'xiaoyu', K1 + '+1.3', 1.7, { to: 2.35 }),
    P('puppet.pose', 'xiaoyu', K1 + '+2.9', 0.24, { pose: 'stand' }),
    A('camera.move', K1 + '+3.4', 4.2, { to: WRIST_CU }),
  ],
  musicLevel: 0.65,
});
const c001 = out.cues.find((c) => c.id === 'a2_c001');
c001.voStart = 1.6;
c001.lines[1].start = 'a2_c001_01.end+0.45';
c001.lines[2].start = K1 + '+7.6';
c001.tail = 1.6;


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

// ---------------------------------------------------------------- 題卡 Q2（只調時間；起始狀態接 a2_c004 的停格）
const C004_END_CHARS = {
  ale: { visible: true, pose: 'pulled_half', strings: ['wrist', 'elbow', 'knee'], stringTension: 1, emotion: 'confused', hand: 'grab' },
  xiaoqing: { visible: true, pose: 'worried', emotion: 'worried' },
  xiaoyu: { visible: true, pose: 'stepback', emotion: 'surprised' },
};
const C004_STAGE = { desat: 0.5, spot: 1, spotTarget: 'ale' };
set('a2_c005', { initialState: { stage: { curtain: 'open', camera: 'g4_mid', light: 0.94, ...C004_STAGE }, characters: C004_END_CHARS } });
set('a2_c006', { initialState: { stage: { curtain: 'open', camera: 'quiz', light: 0.55, quiz: true, ...C004_STAGE }, characters: C004_END_CHARS } });
set('a2_c007', { initialState: { stage: { curtain: 'open', camera: 'quiz', light: 0.55, quiz: true, ...C004_STAGE }, characters: C004_END_CHARS } });

// ---------------------------------------------------------------- a2_c008 想不起來（必要旁白二）
// 手部中景（想用手→線先繃緊→手被拉開）→ 兩個孩子（小宇靠近小晴小聲問）→ 回到 g4_mid 群體構圖，必要旁白時畫面靜止。
// 孩子在這段換到前景（z 1.5／1.1、縮放約 1.1 倍），和阿樂叔叔組成前後景深的群體；後面的題卡、a2_c012 都接這個站位。
const HANDS = { pos: [-1.6, 2.12, 13.6], target: [-1.6, 2.0, 0], fov: 20 };
const KIDS2 = { pos: [0.95, 1.98, 7.4], target: [0.95, 1.88, 0], fov: 20 };
const ALE_PULLED = { visible: true, pose: 'pulled_half', strings: ['wrist', 'elbow', 'knee'], stringTension: 1, emotion: 'confused', hand: 'grab' };
const KQ = { x: 0.4, z: 1.5, facing: 1 };
const KY = { x: 1.45, z: 1.1, facing: -1 };
set('a2_c008', {
  initialState: {
    stage: { curtain: 'open', camera: 'g4_mid', light: 1, desat: 0.5, spot: 1, spotTarget: 'ale' },
    characters: {
      ale: ALE_PULLED,
      xiaoqing: { visible: true, pose: 'worried', emotion: 'worried', ...KQ },
      xiaoyu: { visible: true, pose: 'stand', emotion: 'worried', ...KY },
    },
  },
  animation: [
    A('camera.cut', 0, 0, { to: HANDS }),
    // 想用手：B 側手沿桌面去拿燈籠紙；A 側線放鬆一點、手慢慢收回來（意圖）
    P('strings.loosen', 'ale', 1.0, 1.2, { anchors: ['wrist', 'elbow'], to: 0.35 }),
    // 再抬手想摺紙 → 線繃直 → 手被拉回旁邊（WAVE_TRY 時序：繃直 +1.8、拉偏 +2.1～+2.85）
    P('puppet.waveTry', 'ale', 1.05, 3.8, { greet: 'worried', emotion: 'confused' }),
    P('puppet.tilt', 'ale', 'a2_c008_01+0.6', 0.8, { to: 0.13 }),
    P('puppet.face', 'ale', 'a2_c008_02', null, { emotion: 'worried' }),
    P('puppet.tilt', 'ale', 'a2_c008_02+0.3', 0.9, { to: 0.05 }),
    P('fx.spot', null, 'a2_c008_02.end+0.5', 1.6, { to: 0 }),
    // 兩個孩子（雙人近景）：小宇靠近小晴、身體傾向她，小聲問
    A('camera.cut', 'a2_c008_02.end+0.5', 0, { to: KIDS2 }),
    P('puppet.move', 'xiaoyu', 'a2_c008_02.end+0.65', 0.6, { dx: -0.2 }),
    P('puppet.lean', 'xiaoyu', 'a2_c008_02.end+0.7', 0.6, { to: -0.045 }),
    P('puppet.lean', 'xiaoqing', 'a2_c008_03+0.6', 0.6, { to: 0.03 }),
    P('puppet.lean', 'xiaoyu', 'a2_c008_04+0.2', 0.7, { to: 0 }),
    P('puppet.face', 'xiaoqing', 'a2_c008_04+1.4', null, { emotion: 'neutral' }),
    P('puppet.lean', 'xiaoqing', 'a2_c008_04+1.4', 0.7, { to: 0 }),
    // 必要旁白二：回到中景群體構圖，畫面靜止（只有呼吸、眨眼）
    A('camera.cut', 'a2_c008_04.end+0.25', 0, { to: 'g4_mid' }),
  ],
  sfx: [{ id: 'sfx_string_taut', at: 1.05 + 1.8, gain: 0.7 }],
  musicLevel: 0.72,
  voStart: 3.5,
  tail: 2.0,
});
{
  const c = out.cues.find((x) => x.id === 'a2_c008');
  c.lines[1].start = 'a2_c008_01.end+0.45';
  c.lines[2].start = 'a2_c008_02.end+0.95';
  c.lines[3].start = 'a2_c008_03.end+0.45';
  c.lines[4].start = 'a2_c008_04.end+0.7';
  c.teacherNote = '必要旁白二（一字不改）時畫面是穩定的中景：阿樂叔叔在左、兩個孩子在右前方，沒有人動作。播完停格，等老師按下一步。';
}

// ---------------------------------------------------------------- 題卡 Q3（只調時間；起始狀態接 a2_c008 的停格）
const C008_END_CHARS = {
  ale: { ...ALE_PULLED, emotion: 'worried' },
  xiaoqing: { visible: true, pose: 'worried', emotion: 'neutral', ...KQ },
  xiaoyu: { visible: true, pose: 'stand', emotion: 'worried', ...KY, x: 1.25 },
};
set('a2_c009', { initialState: { stage: { curtain: 'open', camera: 'g4_mid', light: 1, desat: 0.5 }, characters: C008_END_CHARS } });
set('a2_c010', { initialState: { stage: { curtain: 'open', camera: 'quiz', light: 0.55, quiz: true, desat: 0.5 }, characters: C008_END_CHARS } });
set('a2_c011', { initialState: { stage: { curtain: 'open', camera: 'quiz', light: 0.55, quiz: true, desat: 0.5 }, characters: C008_END_CHARS } });

// ---------------------------------------------------------------- a2_c012 去找葉護理師
// 店內：兩人往右跑出店門（跟拍往右）→ 漸暗換景 → 廣場另一頭的求助站：孩子從左邊走進來，小晴指回燈籠店，葉護理師看著他們、往前一步
// → 漸暗換景 → 店內：葉護理師蹲在阿樂叔叔身邊平視（鏡頭放低），孩子在右前方。
const PAN_R = { pos: [2.7, 1.6, 16.4], target: [2.7, 1.37, 0], fov: 20 };
const SHOP_C = { pos: [-0.6, 1.5, 14.2], target: [-0.6, 1.42, 0], fov: 20 };
const D1 = 2.3, D2 = 6.9; // 兩次漸暗開始
set('a2_c012', {
  initialState: {
    stage: { curtain: 'open', camera: 'g4_mid', light: 1, desat: 0.5 },
    characters: {
      ale: { ...ALE_PULLED, emotion: 'worried' },
      xiaoqing: { visible: true, pose: 'worried', emotion: 'neutral', ...KQ },
      xiaoyu: { visible: true, pose: 'stand', emotion: 'worried', ...KY, x: 1.25 },
      ye: { visible: true, pose: 'stand', emotion: 'neutral', x: 40, z: 0.1, facing: 1 },
    },
  },
  animation: [
    // 店內：往右跑出店門
    P('puppet.pose', 'xiaoqing', 0.2, 0.24, { pose: 'walk' }),
    P('puppet.pose', 'xiaoyu', 0.3, 0.24, { pose: 'walk_r' }),
    P('puppet.exit', 'xiaoqing', 0.3, 1.9, { to: 8.5 }),
    P('puppet.exit', 'xiaoyu', 0.3, 1.9, { to: 8.5 }),
    A('fade.out', D1, 0.6, {}),
    // 全暗：換到求助站
    A('set.swap', D1 + 0.62, 0, { set: 'a2_helpdesk' }),
    A('camera.cut', D1 + 0.62, 0, { to: 'a2_help_mid' }),
    P('puppet.move', 'ale', D1 + 0.62, 0.03, { dx: -30 }),
    P('puppet.move', 'xiaoqing', D1 + 0.62, 0.03, { dx: -11.8 }),
    P('puppet.move', 'xiaoyu', D1 + 0.62, 0.03, { dx: -13.25 }),
    P('puppet.move', 'ye', D1 + 0.62, 0.03, { dx: -38.1 }),
    A('fade.in', D1 + 0.7, 0.6, {}),
    P('puppet.exit', 'xiaoqing', D1 + 2.0, 1.6, { to: 3.5 }),
    P('puppet.exit', 'xiaoyu', D1 + 2.0, 1.6, { to: 3.5 }),
    P('puppet.pose', 'xiaoqing', D1 + 3.5, 0.24, { pose: 'reach' }),
    P('puppet.pose', 'xiaoyu', D1 + 3.65, 0.24, { pose: 'stand' }),
    P('puppet.face', 'ye', D1 + 3.2, null, { emotion: 'worried' }),
    P('puppet.lean', 'ye', D1 + 3.3, 0.5, { to: -0.035 }),
    P('puppet.exit', 'ye', D1 + 3.85, 0.7, { to: -1.4 }),
    A('fade.out', D2, 0.6, {}),
    // 全暗：回到店內，葉護理師蹲在阿樂叔叔身邊
    A('set.swap', D2 + 0.62, 0, { set: 'workshop_g4' }),
    A('camera.cut', D2 + 0.62, 0, { to: SHOP_C }),
    P('puppet.move', 'ale', D2 + 0.62, 0.03, { dx: 30 }),
    P('puppet.sit', 'ale', D2 + 0.62, 0.03, { to: 1 }),
    P('puppet.move', 'ye', D2 + 0.62, 0.03, { dx: -1.15 }),
    P('puppet.lean', 'ye', D2 + 0.62, 0.03, { to: 0 }),
    P('puppet.pose', 'ye', D2 + 0.64, 0.24, { pose: 'crouch' }),
    P('puppet.move', 'xiaoqing', D2 + 0.62, 0.03, { dx: 0.45 }),
    P('puppet.move', 'xiaoyu', D2 + 0.62, 0.03, { dx: 1.9 }),
    P('puppet.pose', 'xiaoqing', D2 + 0.64, 0.24, { pose: 'worried' }),
    A('fx.desat', D2 + 0.62, 0.03, { to: 0.32 }),
    A('fade.in', D2 + 0.95, 0.6, {}),
    A('fx.desat', D2 + 1.6, 3.0, { to: 0.2 }),
    P('puppet.tilt', 'ale', 'a2_c012_02-0.2', 0.8, { to: 0.1 }),
    P('puppet.tilt', 'ale', 'a2_c012_02.end+0.5', 0.9, { to: 0.05 }),
    // 小晴說盒子的事：身體微微傾向葉護理師（不比手勢、不指向任何人）
    P('puppet.lean', 'xiaoqing', 'a2_c012_04-0.1', 0.6, { to: -0.035 }),
    P('puppet.lean', 'xiaoqing', 'a2_c012_04.end+0.3', 0.7, { to: 0 }),
  ],
  audioId: null,
  music: [
    { id: 'music_courage', at: 0.15, loop: false, fade: 1.0, gain: 1 },
    { id: 'music_town', at: D2 + 0.6, loop: true, fade: 1.6, gain: 0.5 },
  ],
  musicLevel: 0.75,
  sfx: [
    { id: 'sfx_footsteps', at: 0.35, gain: 0.55 },
  ],
  voStart: D2 + 1.75,
  tail: 1.8,
});
{
  const c = out.cues.find((x) => x.id === 'a2_c012');
  c.lines[1].start = 'a2_c012_01.end+0.45';
  c.lines[2].start = 'a2_c012_02.end+2.3';
  c.lines[3].start = 'a2_c012_03.end+0.45';
  c.lines[4].start = 'a2_c012_04.end+0.45';
  c.teacherNote = '兩個孩子往右跑出店門、到廣場另一頭的求助站（帳篷上是手捧愛心圖示，沒有紅十字）找葉護理師；葉護理師進店蹲下和阿樂叔叔平視、打電話給他的家人沒人接、答應請警察去看盒子。播完停格，等老師按下一步。';
}

// ---------------------------------------------------------------- a2_c013 說出實情（懸念）：店外傍晚（a2_window）
set('a2_c013', {
  sceneId: 'a2_window',
  set: 'a2_window',
  initialState: {
    stage: { curtain: 'open', camera: 'a2_win_wide', light: 1, desat: 0.12 },
    characters: {
      ale: { visible: true, pose: 'pulled_sit', strings: ['wrist', 'elbow', 'knee'], stringTension: 1, emotion: 'worried', hand: 'lap', x: -2.95, z: -1.5 },
      ye: { visible: true, pose: 'crouch', emotion: 'worried', x: -1.1, z: -1.15, facing: 1 },
      xiaoqing: { visible: true, pose: 'watch', emotion: 'worried', x: 0.4, z: 0.55, facing: 1 },
      xiaoyu: { visible: true, pose: 'stand', emotion: 'worried', x: 1.4, z: 0.95, facing: -1 },
      zhezhe: { visible: true, emotion: 'worried', x: -0.62, y: 0.88, z: -0.45 },
    },
  },
  animation: [
    A('light.dim', 0.5, 6.0, { to: 0.88 }),
    P('puppet.tilt', 'ale', 0, 0.01, { to: 0.12 }),
    P('puppet.lean', 'ye', 'a2_c013_01', 1.2, { to: -0.03 }),
    P('puppet.tilt', 'ale', 'a2_c013_01+2.4', 1.0, { to: 0.08 }),
    P('puppet.tilt', 'ale', 'a2_c013_02+0.8', 1.0, { to: 0.13 }),
    // 葉護理師說話，阿樂叔叔慢慢點一下頭
    P('puppet.tilt', 'ale', 'a2_c013_03.end-1.0', 0.6, { to: 0.02 }),
    P('puppet.tilt', 'ale', 'a2_c013_03.end-0.35', 0.7, { to: 0.07 }),
    // 筆記本特寫：小晴在問號旁邊又畫一個問號（程式畫線，見 a2_window.ts）
    A('camera.cut', 'a2_c013_03.end+0.5', 0, { to: 'a2_win_note' }),
    A('camera.cut', 'a2_c013_03.end+3.1', 0, { to: 'a2_win_kids' }),
    // 折折回頭看空空的工作台，耳朵垂下
    P('zhezhe.look', 'zhezhe', 'a2_c013_03.end+3.4', 0.9, { yaw: -0.45 }),
    P('zhezhe.emote', 'zhezhe', 'a2_c013_03.end+3.9', null, { emotion: 'sad' }),
  ],
  audioId: null,
  music: [
    { id: 'music_shiny', at: 0, loop: true, fade: 1.5, gain: 0.45 },
    { id: 'music_town_night', at: 'a2_c013_02.end+0.4', loop: true, fade: 2.0, gain: 0.85 },
  ],
  musicLevel: 0.72,
  sfx: [{ id: 'sfx_wind', at: 0.6, gain: 0.3 }],
  voStart: 1.6,
  tail: 2.2,
});
{
  const c = out.cues.find((x) => x.id === 'a2_c013');
  c.lines[2].start = 'a2_c013_02.end+0.8';
  c.lines[3].start = 'a2_c013_03.end+4.7';
  c.lines[4].start = 'a2_c013_04.end+0.45';
  c.teacherNote = '傍晚的店外：窗裡葉護理師蹲在阿樂叔叔身邊；右上角剪影回憶小窗在阿樂叔叔伸手接過盒子之前就收起（不出現打開或使用）。筆記本特寫：小晴又畫一個問號；折折回頭看工作台、耳朵垂下。播完停格，等老師按下一步。';
}

// ---------------------------------------------------------------- 流程欄位（G4 cue 只動 next／prevStable）

writeFileSync(process.argv[2] ?? join(S, 'a2.json'), JSON.stringify(out, null, 1) + '\n');
console.log('wrote a2.json');
