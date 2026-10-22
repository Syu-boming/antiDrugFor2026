// a2_shop：第二幕的燈籠店（a2 代理，G5 修正第 1 輪）。沿用 G4 燈籠店景（buildWorkshopG4，不改它），只在上面加第二幕需要的程式部分；
// 沒有寫到的 cue（例如 a2_c004）畫面和 workshop_g4 逐像素相同（額外的東西都 visible＝false、不投影）。
//   1. L1 短線（a2_c001）：阿樂叔叔右手腕背側的那條線只從紙環往上約 1.5 個手掌長（0.30 起漸淡、0.62 世界單位淡到 0），
//      不是一整條伸出畫面的繩（a2_c002 才有整條繩從上方落下）。做法：引擎畫的腕線網格每格加上沿線的頂點透明度（只在 a2_c001；
//      離開 a2_c001 或換景時還原），線寬、紙環、位置都是引擎原樣，量測照常。
//   2. 竹篾（a2_c001）：阿樂叔叔右手（A 側）握著一根竹篾、斜放在膝上（跟著手部件走；夾在手與前臂之間，看起來是握住的）。
//   3. 手部近景（a2_c008）：x＝INSERT_X 的獨立小台（鏡頭 camera.cut 過去）：阿樂叔叔的雙手（分件手臂圖＋白紙芯外框）想把燈籠紙對摺 →
//      右手腕背側的操偶線（引擎同款紙繩與紙環，只扣腕背）一頓一頓把手拉開（3 下，每下 0.3 秒、間隔 ≥ 0.4 秒）→ 紙皺成一團落到桌上。
//   4. 求助站（a2_c012）：assets/final/sets/a2_helpdesk/layout.json 建在 x＝HELP_X（同一個景裡），從求助站回店裡用鏡頭直接切
//      （不再第二次漸暗）；去求助站仍是漸暗換場（G6 修正第 1 輪試過直接切：兩個孩子往右走出店的那 1 秒會讓右側細格每秒明暗 4 次，維持漸暗）。
//   5. 回想小台（a2_c003，G6 修正第 1 輪）：assets/final/sets/a2_memory/layout.json（同一間店的背牆、地板＋兩張回想紙卡）建在 x＝MEM_X，
//      紙卡開合、翻面用 a2_memory.ts 的 memoryCardsUpdater（畫面同 a2_memory 景）；a2_c002→a2_c003→a2_c004 都在這個景裡，
//      鏡頭直接切（亮度差 ≤20%），不再每次按鍵都換景經過全黑。主光影子只涵蓋主舞台，回想小台和求助站一樣沒有主光投影（接觸陰影照常）。
// update 只依（cue、cue 內秒數）決定畫面＝時間的純函式；動作時間錨在台詞上（配音長度改了會跟著移）。
import {
  BufferAttribute, CanvasTexture, DoubleSide, Group, LinearMipmapLinearFilter, Matrix4, Mesh, MeshBasicMaterial, MeshStandardMaterial,
  PlaneGeometry, Vector3, type BufferGeometry, type Material, type Object3D,
} from 'three';
import { buildWorkshopG4 } from '../stage/workshop';
import { PaperString, RING_DIAMETER } from '../stage/strings';
import { finishTexture, makeCanvas } from '../stage/paper';
import { LAYER, type CameraPreset } from '../stage/layers';
import { buildImageSet, readLayout } from './imageSet';
import { A2_MEMORY_CAMERAS, memoryCardsUpdater } from './a2_memory';
import { clamp, ease, seeded, smoothstep } from '../util/math';
import type { CueTimeline } from '../cues/timeline';
import type { BuiltSet, SetEntry } from './types';

type V3 = [number, number, number];
/** 手部近景小台、求助站的世界 x（主舞台鏡頭看不到） */
export const INSERT_X = -40;
export const HELP_X = 40;
/** 回想小台（a2_c003）的世界 x */
export const MEM_X = -80;
const C = (pos: V3, target: V3, fov = 20): CameraPreset => ({ pos, target, fov });
export const A2_SHOP_CAMERAS: Record<string, CameraPreset> = {
  /** 手部近景（雙手＋燈籠紙） */
  a2s_hands: C([INSERT_X, 0.55, 4.6], [INSERT_X, 0.5, 0]),
  /** 求助站中景（同 a2_helpdesk 的 a2_help_mid，平移到 HELP_X） */
  a2s_help_mid: C([0.9 + HELP_X, 1.9, 17.5], [0.9 + HELP_X, 1.72, 0]),
  /** 回想小台：小晴近景（同 a2_memory 的 a2_memory_cu，平移到 MEM_X） */
  a2s_memory_cu: C([A2_MEMORY_CAMERAS.a2_memory_cu.pos[0] + MEM_X, A2_MEMORY_CAMERAS.a2_memory_cu.pos[1], A2_MEMORY_CAMERAS.a2_memory_cu.pos[2]],
    [A2_MEMORY_CAMERAS.a2_memory_cu.target[0] + MEM_X, A2_MEMORY_CAMERAS.a2_memory_cu.target[1], A2_MEMORY_CAMERAS.a2_memory_cu.target[2]], A2_MEMORY_CAMERAS.a2_memory_cu.fov),
};

/** 母版像素 → 世界單位（阿樂叔叔分件紙偶：站姿高 3.55 ≈ 1610 px） */
const PX = 3.55 / 1610;
/** L1：紙環往上多遠開始變淡、多遠淡到 0（世界單位；手的長度約 0.38） */
const L1_FADE0 = 0.30, L1_FADE1 = 0.62;

// ───────────────────────────── 小工具 ─────────────────────────────
const sine01 = (u: number): number => 0.5 - 0.5 * Math.cos(Math.PI * clamp(u));
function lineStart(tl: CueTimeline, id: string, fb: number): number { const l = tl.lines.find((x) => x.line.id === id); return l ? l.start : fb; }
function lineEnd(tl: CueTimeline, id: string, fb: number): number { const l = tl.lines.find((x) => x.line.id === id); return l ? l.end : fb; }

function texOf(img: HTMLImageElement | HTMLCanvasElement): CanvasTexture {
  const t = finishTexture(new CanvasTexture(img as HTMLCanvasElement));
  t.minFilter = LinearMipmapLinearFilter;
  return t;
}
/** 圖片紙片：pivotPx＝圖上哪一點放在原點（像素，y 向下）；k＝每像素幾個世界單位 */
function imgPlane(img: HTMLImageElement | HTMLCanvasElement, w: number, h: number, pivotPx: [number, number], k: number, mats: Material[], basic = false): Mesh {
  const geo = new PlaneGeometry(w * k, h * k);
  geo.translate((w / 2 - pivotPx[0]) * k, -(h / 2 - pivotPx[1]) * k, 0);
  const map = texOf(img);
  const mat = basic ? new MeshBasicMaterial({ map, alphaTest: 0.5, side: DoubleSide })
    : new MeshStandardMaterial({ map, alphaTest: 0.5, side: DoubleSide, roughness: 0.94, metalness: 0 });
  mats.push(mat);
  const m = new Mesh(geo, mat);
  m.castShadow = false;
  m.receiveShadow = false;
  return m;
}

// ───────────────────────────── 竹篾（H5） ─────────────────────────────
function bambooCanvas(): HTMLCanvasElement {
  const W = 420, H = 30;
  const [c, g] = makeCanvas(W, H);
  g.fillStyle = '#fbf3e4'; g.beginPath(); g.roundRect(0, 0, W, H, 12); g.fill();           // 白紙芯外框
  g.fillStyle = '#5b4632'; g.beginPath(); g.roundRect(4, 5, W - 8, H - 10, 8); g.fill();    // 深色細邊
  g.fillStyle = '#e2c27f'; g.beginPath(); g.roundRect(6, 7, W - 12, H - 14, 6); g.fill();   // 竹色
  g.fillStyle = 'rgba(255,248,220,0.55)'; g.fillRect(10, 8, W - 20, 3);                     // 受光
  g.fillStyle = 'rgba(120,84,40,0.55)';
  for (const x of [96, 230, 352]) g.fillRect(x, 7, 3, H - 14);                               // 竹節
  return c;
}

// ───────────────────────────── 手部近景：燈籠紙（平、對摺、皺、一團） ─────────────────────────────
function paperCanvas(state: number, seed: number): HTMLCanvasElement {
  const W = 520, H = 340;
  const [c, g] = makeCanvas(W, H);
  const r = seeded(seed);
  const outline = (pts: [number, number][]): void => {
    g.beginPath(); g.moveTo(pts[0][0], pts[0][1]); for (const p of pts.slice(1)) g.lineTo(p[0], p[1]); g.closePath();
  };
  // 外形：平整長方形 → 邊緣越來越不規則
  const jag = [0, 3, 10, 18][state] ?? 0;
  const pts: [number, number][] = [];
  const N = 36;
  for (let i = 0; i < N; i++) {
    const u = i / N;
    let x: number, y: number;
    if (u < 0.25) { x = 14 + (W - 28) * (u / 0.25); y = 14; }
    else if (u < 0.5) { x = W - 14; y = 14 + (H - 28) * ((u - 0.25) / 0.25); }
    else if (u < 0.75) { x = W - 14 - (W - 28) * ((u - 0.5) / 0.25); y = H - 14; }
    else { x = 14; y = H - 14 - (H - 28) * ((u - 0.75) / 0.25); }
    pts.push([x + (r() - 0.5) * jag * 2, y + (r() - 0.5) * jag * 2]);
  }
  g.fillStyle = '#fbf3e4'; g.lineJoin = 'round'; g.lineWidth = 16; g.strokeStyle = '#fbf3e4';
  outline(pts); g.fill(); g.stroke();
  g.lineWidth = 3; g.strokeStyle = '#6a5240'; outline(pts); g.stroke();
  g.save(); outline(pts); g.clip();
  g.fillStyle = '#f3e6cc'; g.fillRect(0, 0, W, H);                       // 和紙（米白，非飽和紅）
  for (let i = 0; i < 140; i++) {                                         // 纖維
    g.strokeStyle = r() < 0.5 ? 'rgba(160,130,90,0.18)' : 'rgba(255,255,255,0.35)';
    g.lineWidth = 1 + r();
    const x = r() * W, y = r() * H, a = r() * Math.PI;
    g.beginPath(); g.moveTo(x, y); g.lineTo(x + Math.cos(a) * 14, y + Math.sin(a) * 14); g.stroke();
  }
  if (state >= 1) {                                                       // 摺痕
    g.strokeStyle = 'rgba(120,96,70,0.45)'; g.lineWidth = 3;
    g.beginPath(); g.moveTo(W * 0.5, 0); g.lineTo(W * 0.5 + (r() - 0.5) * 20, H); g.stroke();
  }
  if (state >= 2) {                                                       // 皺褶：深淺折線
    const n = state === 2 ? 7 : 14;
    for (let i = 0; i < n; i++) {
      const x0 = r() * W, y0 = r() * H, x1 = x0 + (r() - 0.5) * 220, y1 = y0 + (r() - 0.5) * 160;
      g.strokeStyle = 'rgba(110,86,60,0.42)'; g.lineWidth = 2.5;
      g.beginPath(); g.moveTo(x0, y0); g.lineTo((x0 + x1) / 2 + (r() - 0.5) * 30, (y0 + y1) / 2 + (r() - 0.5) * 30); g.lineTo(x1, y1); g.stroke();
      g.strokeStyle = 'rgba(255,252,240,0.6)'; g.lineWidth = 2;
      g.beginPath(); g.moveTo(x0 + 3, y0 + 3); g.lineTo(x1 + 3, y1 + 3); g.stroke();
    }
  }
  g.restore();
  return c;
}
/** 皺成一團的紙球（不規則多邊形＋皺褶） */
function ballCanvas(): HTMLCanvasElement {
  const S = 220;
  const [c, g] = makeCanvas(S, S);
  const r = seeded(77);
  const pts: [number, number][] = [];
  for (let i = 0; i < 15; i++) { const a = (i / 15) * Math.PI * 2, rr = S * (0.36 + r() * 0.09); pts.push([S / 2 + Math.cos(a) * rr, S / 2 + Math.sin(a) * rr * 0.86]); }
  const path = (): void => { g.beginPath(); g.moveTo(pts[0][0], pts[0][1]); for (const p of pts.slice(1)) g.lineTo(p[0], p[1]); g.closePath(); };
  g.lineJoin = 'round';
  g.fillStyle = '#fbf3e4'; g.strokeStyle = '#fbf3e4'; g.lineWidth = 14; path(); g.fill(); g.stroke();
  g.strokeStyle = '#6a5240'; g.lineWidth = 3; path(); g.stroke();
  g.save(); path(); g.clip();
  g.fillStyle = '#efdfc2'; g.fillRect(0, 0, S, S);
  for (let i = 0; i < 16; i++) {
    const x0 = S / 2 + (r() - 0.5) * S * 0.7, y0 = S / 2 + (r() - 0.5) * S * 0.6;
    g.strokeStyle = 'rgba(110,86,60,0.5)'; g.lineWidth = 2.5;
    g.beginPath(); g.moveTo(x0, y0); g.lineTo(x0 + (r() - 0.5) * 90, y0 + (r() - 0.5) * 70); g.lineTo(x0 + (r() - 0.5) * 90, y0 + (r() - 0.5) * 70); g.stroke();
    g.strokeStyle = 'rgba(255,252,240,0.65)'; g.lineWidth = 2;
    g.beginPath(); g.moveTo(x0 + 4, y0 - 3); g.lineTo(x0 + (r() - 0.5) * 70, y0 + (r() - 0.5) * 60); g.stroke();
  }
  g.restore();
  return c;
}
/** 手部近景的桌面背景（工作台桌面＋上方柔和的店內牆面；淡、低對比，像景深模糊） */
function insertBackdrop(): HTMLCanvasElement {
  const W = 1400, H = 820;
  const [c, g] = makeCanvas(W, H);
  const r = seeded(91);
  // 上方：店內的牆（淡、低對比，像景深模糊）
  const wall = g.createLinearGradient(0, 0, 0, H * 0.24);
  wall.addColorStop(0, '#f8f0e0'); wall.addColorStop(1, '#f2e6cf');
  g.fillStyle = wall; g.fillRect(0, 0, W, H * 0.24);
  g.fillStyle = 'rgba(206,176,128,0.22)';                                 // 遠處的柱子（模糊）
  g.fillRect(W * 0.18, 0, 46, H * 0.24); g.fillRect(W * 0.71, 0, 46, H * 0.24);
  // 桌面：牛皮紙色木板，木紋很淡、斷斷續續
  g.fillStyle = '#b48a5c'; g.fillRect(0, H * 0.24, W, H * 0.025);       // 桌緣
  const top = g.createLinearGradient(0, H * 0.265, 0, H);
  top.addColorStop(0, '#e9cfa6'); top.addColorStop(1, '#e2c296');
  g.fillStyle = top; g.fillRect(0, H * 0.265, W, H * 0.735);
  for (let i = 0; i < 70; i++) {
    const y = H * 0.29 + r() * H * 0.7, x = r() * W, len = 80 + r() * 260;
    g.strokeStyle = `rgba(150,108,66,${0.08 + r() * 0.1})`; g.lineWidth = 1.5 + r() * 2;
    g.beginPath(); g.moveTo(x, y); g.quadraticCurveTo(x + len / 2, y + (r() - 0.5) * 8, x + len, y + (r() - 0.5) * 6); g.stroke();
  }
  // 桌上的東西（畫面上緣、淡）：左上一束竹篾、右上一小疊燈籠紙
  for (let k = 0; k < 7; k++) {
    g.strokeStyle = k % 2 ? '#e4c783' : '#d8b672'; g.lineWidth = 9;
    g.beginPath(); g.moveTo(70 + k * 6, H * 0.36 + k * 4); g.lineTo(430 + k * 4, H * 0.31 + k * 4); g.stroke();
  }
  g.fillStyle = '#a2794c'; g.fillRect(250, H * 0.325, 16, 34);
  for (let k = 0; k < 3; k++) { g.fillStyle = ['#f6ecd8', '#f1e3c8', '#f7eedc'][k]; g.fillRect(1010 + k * 6, H * 0.30 + k * 7, 300, 54); g.strokeStyle = 'rgba(120,96,70,0.4)'; g.lineWidth = 2; g.strokeRect(1010 + k * 6, H * 0.30 + k * 7, 300, 54); }
  return c;
}

// ───────────────────────────── 手部近景：一隻手臂（前臂＋手，白紙芯外框，肘在原點） ─────────────────────────────
interface ArmParts { group: Group; wristBack: Vector3; mats: Material[] }
function buildArm(ctx: { image(id: string): HTMLImageElement | undefined }, side: 'r' | 'l', k: number, order: number): ArmParts | null {
  // G5 修正第 2 輪：優先用母版分件的近景處理版（2 倍解析度、紙纖維、2 px 深色紙邊；review/G5/a2/scripts/build_fix2_a2_art.py），
  // 沒有才用紙偶本體的分件（座標都以母版 px 計，近景版 ×2）
  const ins = ctx.image(`sets/a2_shop/insert-ale-forearm-${side}`) && ctx.image(`sets/a2_shop/insert-ale-hand-${side}`);
  const S = ins ? 2 : 1;
  const src = (part: string): HTMLImageElement | undefined => ctx.image(ins ? `sets/a2_shop/insert-ale-${part}` : `rig/chr-ale_${part}`);
  const fa = src(`forearm-${side}`), hd = src(`hand-${side}`);
  const faO = src(`forearm-${side}-outline`), hdO = src(`hand-${side}-outline`);
  if (!fa || !hd) return null;
  // ale_rig.json：forearm_r pivot [83,53]、hand_r pivot [49,32] 接在前臂 [84,238]；forearm_l [71,53]、hand_l [54,32] 接在 [95,251]
  // 紙環（修正第 2 輪）：從 ale_attach.json wrist_back〔forearm_r 69,210〕往手的方向移到腕背橫紋上（離關節約 10 px）
  const P = side === 'r' ? { fa: [83, 53], hd: [49, 32], joint: [84, 238], wb: [77, 229] } : { fa: [71, 53], hd: [54, 32], joint: [95, 251], wb: [89, 243] };
  const mats: Material[] = [];
  const group = new Group();
  const add = (img: HTMLImageElement | undefined, pivot: number[], off: [number, number], z: number, ord: number): void => {
    if (!img) return;
    const m = imgPlane(img, img.naturalWidth, img.naturalHeight, [pivot[0] * S, pivot[1] * S], k / S, mats);
    m.position.set(off[0], off[1], z);
    m.renderOrder = ord;
    group.add(m);
  };
  const jx = (P.joint[0] - P.fa[0]) * k, jy = -(P.joint[1] - P.fa[1]) * k;
  // 外框（白紙芯＋深色細邊，比部件大一圈）在最後面
  add(faO, P.fa, [0, 0], -0.004, order);
  add(hdO, P.hd, [jx, jy], -0.003, order + 1);
  add(fa, P.fa, [0, 0], 0, order + 2);
  add(hd, P.hd, [jx, jy], 0.002, order + 3);
  return { group, wristBack: new Vector3((P.wb[0] - P.fa[0]) * k, -(P.wb[1] - P.fa[1]) * k, 0.01), mats };
}

/** 手部近景的表演（insert 內秒數 → 姿勢）。
 *  想摺 → 線先繃直（0.1 秒）→ 手被往左上拉開（0.3 秒）→ 停在被拉開的位置 → 慢慢再試 → 第 2 下 → 再試 → 第 3 下 → 紙皺成一團落下 → 手慢慢放下。
 *  細格光敏：同一個區域每秒最多 2 次變化（拉開後不彈回、再試走得慢；三下間隔 1.4 秒）。 */
export const INSERT_BEATS = {
  fold1: [0.35, 1.15] as const, tug1: 1.3,
  fold2: [1.95, 2.6] as const, tug2: 2.75,
  fold3: [3.4, 3.95] as const, tug3: 4.15,
  ballDrop: [4.3, 4.75] as const, settle: [4.8, 5.5] as const,
};
/** 右手腕被拉的方向（單位向量，insert 座標）：從手腕靜止位置指向線的上端 */
let PULL_DIR: [number, number] = [-0.35, 0.94];
function insertPose(t: number): { aDx: number; aDy: number; aRot: number; bDx: number; bDy: number; tension: number; fold: number; paper: number; ball: number; ballY: number } {
  const B = INSERT_BEATS;
  const sm = (a: number, b: number): number => sine01((t - a) / (b - a));
  // 拉扯：0.1 秒線繃直，0.1–0.4 秒手被拉開（ease-out），之後停在那裡（下一次再試才慢慢回來）
  const jerk = (t0: number): number => (t < t0 + 0.1 ? 0 : t < t0 + 0.4 ? ease('out', (t - t0 - 0.1) / 0.3) : 1);
  const f1 = sm(B.fold1[0], B.fold1[1]), f2 = sm(B.fold2[0], B.fold2[1]), f3 = sm(B.fold3[0], B.fold3[1]);
  // 位置＝往右摺的進度（0–1）與被拉開的量（0–1）交替：每次再試從被拉開的位置慢慢往右回
  let fold = 0, pulled = 0;
  if (t < B.tug1) { fold = f1; }
  else if (t < B.fold2[0]) { fold = f1 * (1 - jerk(B.tug1)); pulled = jerk(B.tug1); }
  else if (t < B.tug2) { pulled = 1 - f2; fold = f2 * 0.75; }
  else if (t < B.fold3[0]) { fold = 0.75 * (1 - jerk(B.tug2)); pulled = jerk(B.tug2); }
  else if (t < B.tug3) { pulled = 1 - f3 * 0.8; fold = f3 * 0.5; }
  else { fold = 0.5 * (1 - jerk(B.tug3)); pulled = jerk(B.tug3); }
  const settle = sm(B.settle[0], B.settle[1]);
  // 拉開的方向＝沿著線往上（線拉手腕是順著線的方向，線本身幾乎不橫掃過畫面：細格光敏）；再試只往右挪一點
  const aDx = fold * 0.08 + pulled * PULL_DIR[0] * 0.13 - settle * 0.03;
  const aDy = fold * 0.01 + pulled * PULL_DIR[1] * 0.13 - settle * 0.1;
  const aRot = -fold * 0.05 + pulled * 0.06 + settle * 0.04;
  const bDx = -fold * 0.02 + settle * 0.02;
  const bDy = -settle * 0.06;
  // 張力：平常 0.75（只微鬆）；每次拉扯 0.1 秒內繃直，0.5 秒後慢慢回到 0.8
  const taut = (t0: number): number => clamp((t - t0) / 0.1) * (1 - 0.8 * sm(t0 + 0.5, t0 + 1.0));
  const tension = clamp(Math.max(0.75 + 0.05 * pulled, 0.75 + 0.25 * Math.max(t >= B.tug1 ? taut(B.tug1) : 0, t >= B.tug2 ? taut(B.tug2) : 0, t >= B.tug3 ? taut(B.tug3) : 0)));
  // 紙：0 平、1 摺痕、2 皺、3 更皺；第 3 下之後變成一團落下
  const paper = t < B.tug1 + 0.2 ? (fold > 0.3 ? 1 : 0) : t < B.tug2 + 0.2 ? 2 : 3;
  const ball = t >= B.tug3 + 0.15 ? 1 : 0;
  const d = clamp((t - B.ballDrop[0]) / (B.ballDrop[1] - B.ballDrop[0]));
  const ballY = d < 0.8 ? -0.3 * (d / 0.8) ** 2 : -0.3 + 0.03 * Math.sin(Math.PI * (d - 0.8) / 0.2);
  return { aDx, aDy, aRot, bDx, bDy, tension, fold, paper, ball, ballY };
}

// ───────────────────────────── 景 ─────────────────────────────
export const A2_SHOP: SetEntry = {
  title: '燈籠店（第二幕：L1 短線、竹篾、手部近景、求助站）',
  cameras: A2_SHOP_CAMERAS,
  build(ctx) {
    const ws = buildWorkshopG4({ alphaToCoverage: ctx.alphaToCoverage, image: (id) => ctx.image(id) });
    const group = new Group();
    group.name = 'set:a2_shop';
    group.add(ws.group);
    const report: string[] = [];
    const setMats: Material[] = [...ws.materials];   // 套 FX8 降彩（景片、道具）
    const extraMats: Material[] = [];                // 不降彩（阿樂叔叔的手）
    const disposables: { dispose(): void }[] = [];

    // ---- 2. 竹篾
    const bamboo = imgPlane(bambooCanvas(), 420, 30, [120, 15], 0.66 / 420, setMats);
    bamboo.visible = false;
    bamboo.matrixAutoUpdate = false;
    group.add(bamboo);
    const bambooLocal = new Matrix4().makeRotationZ(-0.7).setPosition(0.03, -0.16, 0.115);

    // ---- 3. 手部近景小台
    const insert = new Group();
    insert.name = 'a2:handsInsert';
    insert.position.set(INSERT_X, 0, 0);
    insert.visible = false;
    group.add(insert);
    const back = imgPlane(insertBackdrop(), 1400, 820, [700, 410], 3.9 / 1400, setMats);
    back.position.set(0, 0.42, -0.35);
    back.renderOrder = LAYER.mid.order;
    insert.add(back);
    const PW = 1.0 / 520;    // 紙：寬 1.0
    const paperTex = [0, 1, 2, 3].map((s) => texOf(paperCanvas(s, 31 + s * 7)));
    const paperMat = new MeshStandardMaterial({ map: paperTex[0], alphaTest: 0.5, side: DoubleSide, roughness: 0.95, metalness: 0 });
    setMats.push(paperMat);
    paperTex.forEach((t) => disposables.push(t));
    const paperGeo = new PlaneGeometry(520 * PW, 340 * PW);
    paperGeo.translate(-260 * PW, 0, 0);   // 右緣是原點（左手那邊固定，右手把左緣往右帶＝對摺）
    const paper = new Mesh(paperGeo, paperMat);
    paper.renderOrder = LAYER.actors.order - 2;
    const PAPER_RIGHT: V3 = [0.5, 0.22, -0.05];
    paper.position.set(...PAPER_RIGHT);
    insert.add(paper);
    const ball = imgPlane(ballCanvas(), 220, 220, [110, 150], 0.36 / 220, setMats);
    ball.renderOrder = LAYER.actors.order - 1;
    ball.visible = false;
    insert.add(ball);
    const K_ARM = PX * 1.12;   // 近景的手臂比例（比紙偶本身略大一點）
    const armA = buildArm(ctx, 'r', K_ARM, LAYER.actors.order + 4);
    const armB = buildArm(ctx, 'l', K_ARM, LAYER.actors.order + 10);
    if (!armA || !armB) report.push('景 a2_shop：缺阿樂叔叔手臂分件圖（rig/chr-ale_forearm-*、hand-*），手部近景用不到');
    const A0 = { x: -0.95, y: -0.36, rot: Math.PI - 0.66 };   // A 側（畫面左，右手）：肘在畫面左下外，手壓在紙的左下角
    const B0 = { x: 0.95, y: -0.36, rot: Math.PI + 0.64 };     // B 側（畫面右，左手）
    if (armA) { insert.add(armA.group); extraMats.push(...armA.mats); }
    if (armB) { insert.add(armB.group); extraMats.push(...armB.mats); }
    const rope = new PaperString(LAYER.strings.order + 2);
    // 紙繩與紙環貼圖用複本：換景釋放時（stage disposeTree）不會釋放到阿樂叔叔身上那幾條線共用的貼圖
    if (rope.ropeMat.map) { rope.ropeMat.map = rope.ropeMat.map.clone(); rope.ropeMat.map.needsUpdate = true; }
    if (rope.ringMat.map) { rope.ringMat.map = rope.ringMat.map.clone(); rope.ringMat.map.needsUpdate = true; }
    insert.add(rope.mesh, rope.ring);
    rope.mesh.castShadow = false; rope.ring.castShadow = false;
    const ROPE_W = 0.028;     // 近景約 19 px（和 a2_c001 手腕近景、a2_c002 落下的線同一種紙繩與紙環）
    const wb = new Vector3(), top = new Vector3(), bot = new Vector3();
    // 線的上端：右手腕靜止位置往左上、剛好在畫面上緣外（a2s_hands 鏡頭上緣約 y 1.27）
    let ROPE_TOP: [number, number] = [-1.0, 1.42];
    if (armA) {
      armA.group.position.set(A0.x, A0.y, 0); armA.group.rotation.z = A0.rot; armA.group.updateMatrix();
      const w0 = armA.wristBack.clone().applyMatrix4(armA.group.matrix);
      ROPE_TOP = [w0.x - 0.42, 1.42];
      const dx = ROPE_TOP[0] - w0.x, dy = ROPE_TOP[1] - w0.y, n = Math.hypot(dx, dy) || 1;
      PULL_DIR = [dx / n, dy / n];
    }

    // ---- 4. 求助站
    const hl = readLayout(ctx, 'a2_helpdesk');
    let help: BuiltSet | null = null;
    if (hl) {
      help = buildImageSet({ ...ctx, name: 'a2_helpdesk' }, hl);
      help.group.position.x = HELP_X;
      help.group.visible = false;
      help.group.traverse((o) => { (o as Mesh).castShadow = false; });
      group.add(help.group);
      setMats.push(...(help.materials ?? []));
      report.push(...(help.report ?? []));
    } else report.push('景 a2_shop：缺 sets/a2_helpdesk/layout，求助站不顯示');

    // ---- 5. 回想小台（a2_c003）
    const ml = readLayout(ctx, 'a2_memory');
    let mem: BuiltSet | null = null;
    let memUpdate: ReturnType<typeof memoryCardsUpdater> | null = null;
    if (ml) {
      mem = buildImageSet({ ...ctx, name: 'a2_memory' }, ml);
      mem.group.position.x = MEM_X;
      mem.group.visible = false;
      mem.group.traverse((o) => { (o as Mesh).castShadow = false; });
      group.add(mem.group);
      setMats.push(...(mem.materials ?? []));
      report.push(...(mem.report ?? []));
      memUpdate = memoryCardsUpdater(mem.group);
    } else report.push('景 a2_shop：缺 sets/a2_memory/layout，回想小台不顯示');

    // ---- 1. L1 短線：引擎畫的腕線（cast 群組裡 37×2 頂點的紙繩網格）
    let patched: { mesh: Mesh; mat: MeshBasicMaterial } | null = null;
    const unpatch = (): void => {
      if (!patched) return;
      const g = patched.mesh.geometry as BufferGeometry;
      if (g.getAttribute('color')) g.deleteAttribute('color');
      patched.mat.vertexColors = false;
      patched.mat.needsUpdate = true;
      patched = null;
    };
    const castRoot = (): Object3D | null => {
      const scene = group.parent?.parent;
      if (!scene) return null;
      return scene.children.find((o) => o !== group.parent && o.children.some((ch) => ch.name.startsWith('rig:'))) ?? null;
    };
    const ropeMeshes = (root: Object3D): Mesh[] => root.children.filter((o): o is Mesh => (o as Mesh).isMesh === true
      && o.renderOrder >= LAYER.strings.order && o.renderOrder < LAYER.fore.order
      && ((o as Mesh).geometry as BufferGeometry).getAttribute('position')?.count === 74);
    const applyL1 = (root: Object3D, fadeOut: number): void => {
      const vis = ropeMeshes(root).filter((m) => m.visible);
      const mesh = vis.length === 1 ? vis[0] : null;
      if (!mesh) { unpatch(); return; }
      const mat = mesh.material as MeshBasicMaterial;
      if (patched && patched.mesh !== mesh) unpatch();
      const geo = mesh.geometry as BufferGeometry;
      const pos = geo.getAttribute('position') as BufferAttribute;
      let col = geo.getAttribute('color') as BufferAttribute | undefined;
      if (!col) { col = new BufferAttribute(new Float32Array(74 * 4).fill(1), 4); geo.setAttribute('color', col); }
      if (!mat.vertexColors) { mat.vertexColors = true; mat.needsUpdate = true; }
      patched = { mesh, mat };
      // 由下端（i＝36）往上累積中心線距離
      let acc = 0, px = 0, py = 0;
      for (let i = 36; i >= 0; i--) {
        const cx = (pos.getX(i * 2) + pos.getX(i * 2 + 1)) / 2, cy = (pos.getY(i * 2) + pos.getY(i * 2 + 1)) / 2;
        if (i < 36) acc += Math.hypot(cx - px, cy - py);
        px = cx; py = cy;
        const a = (1 - smoothstep(L1_FADE0, L1_FADE1, acc)) * fadeOut;
        col.setW(i * 2, a); col.setW(i * 2 + 1, a);
      }
      col.needsUpdate = true;
    };

    const findPart = (root: Object3D, rigPrefix: string, part: string): Object3D | null => {
      const rig = root.children.find((o) => o.name.startsWith(rigPrefix) && o.visible);
      return rig?.getObjectByName(part) ?? null;
    };
    const m4 = new Matrix4();

    const update: BuiltSet['update'] = ({ tl, t }) => {
      const id = tl.cue.id;
      const root = castRoot();
      // 1–2：a2_c001
      if (id === 'a2_c001' && root) {
        applyL1(root, 1);
        const hand = findPart(root, 'rig:', 'hand_r');
        if (hand) {
          hand.updateWorldMatrix(true, false);
          bamboo.matrix.copy(m4.multiplyMatrices(hand.matrixWorld, bambooLocal));
          bamboo.matrixWorldNeedsUpdate = true;
          bamboo.visible = true;
        } else bamboo.visible = false;
      } else { unpatch(); bamboo.visible = false; }

      // 3：手部近景（a2_c008）
      insert.visible = id === 'a2_c008';
      if (insert.visible && armA && armB) {
        const p = insertPose(t);
        armA.group.position.set(A0.x + p.aDx, A0.y + p.aDy, 0);
        armA.group.rotation.z = A0.rot + p.aRot;
        armB.group.position.set(B0.x + p.bDx, B0.y + p.bDy, 0.02);
        armB.group.rotation.z = B0.rot;
        insert.updateMatrixWorld(true);
        // 紙：左緣跟著右手（A 側）往右帶＝對摺（寬度縮成 1 − 0.45×fold）
        paperMat.map = paperTex[p.paper];
        paper.visible = !p.ball;
        paper.scale.set(1 - 0.14 * p.fold, 1 - 0.02 * p.fold, 1);
        paper.rotation.z = p.paper >= 2 ? 0.05 * (p.paper - 1) : 0;
        ball.visible = !!p.ball;
        ball.position.set(0.02, 0.3 + p.ballY, -0.04);
        // 操偶線：腕背紙環往上、往畫面左上伸出畫面
        armA.group.localToWorld(wb.copy(armA.wristBack));
        insert.worldToLocal(wb);
        bot.set(wb.x, wb.y, 0.25);
        top.set(ROPE_TOP[0], ROPE_TOP[1], 0.25);   // 上端固定在畫面上緣外一點（畫面上方的線幾乎不動：細格光敏）
        rope.update({ top, bottom: bot, bow: -(1 - p.tension) * 0.2, width: ROPE_W, opacity: 1, ring: 1, ringDiameter: RING_DIAMETER * ROPE_W / 0.043, light: 1 });
      } else rope.hide();

      // 4：求助站（a2_c012）
      if (help) help.group.visible = id === 'a2_c012';

      // 5：回想小台（a2_c003）
      if (mem) {
        mem.group.visible = id === 'a2_c003';
        if (mem.group.visible) memUpdate?.({ tl, t });
      }
    };

    return {
      group, pieces: ws.pieces, materials: setMats, marks: ws.marks, tableEdge: ws.tableEdge, landmarks: ws.landmarks,
      cameras: { ...A2_SHOP_CAMERAS }, report, update,
      // 舞台換景時已先釋放 group 裡的幾何、材質與目前用到的貼圖；這裡還原引擎的腕線、釋放沒掛在材質上的紙張貼圖
      dispose: () => { unpatch(); disposables.forEach((d) => d.dispose()); },
    };
  },
};

// 給 a2_window.ts 用的同款工具
export { lineStart as a2LineStart, lineEnd as a2LineEnd };
