// 折折（摺紙貓）：程式幾何角色＋摺紙變形（FX13）。角色表 v03 第 1.4 節、v1.2 第 15.4 節、節拍表 v03 各段的折折動作。
//
// ═══════════════════════════════════════ 介面（給引擎代理與主線接線） ═══════════════════════════════════════
//
// 建立
//   const zz = new Zhezhe({ position: [x, y, z], height: 1.0, facing: 'front' });
//   scene.add(zz.group);
//   - position：腳底（地面）的世界座標；站在工作台上就給 y＝桌面高（G4 桌面 1.40）
//   - height：坐姿時到耳尖的高度（世界單位）。G4 中景（g4_mid）1.0 約 187 px；題卡台口（quiz 鏡位）建議 1.3–1.6
//   - facing：'front'（面向觀眾，預設）、'left'／'right'（四分之三側面 ±0.5 rad）或弧度（正值＝轉向畫面右）
//   - 其他：seed（眨眼／小動作的種子）、outline（暖褐細輪廓，預設開）、contactShadow（地面柔影，預設開）、
//     castShadow（投影到景片，預設開）、renderOrder（預設 LAYER.actors.order＋15）、presence（存在感，紙面常數自發光，預設 0.06）
//
// 每格
//   zz.update(cueTime, state?)   cueTime＝該 cue 內的秒數；state 可覆寫 { pos, yaw, mouth, visible, glow, presence }（立即生效、不經彈簧；
//                                presence 題卡模式建議跟著 light.dim 從 0.06 漸變到 0.2）
//   update 是時間的純函式：先把時間量化到 1/120 秒（固定步長），所有動作（含耳朵、尾巴的彈簧餘震）都用解析式從事件表算出，
//   沒有任何隱藏狀態，所以上一步、重播、跳轉到任一秒都得到同一格（tools/zhezhe_preview.mjs 逐像素驗證）。
//
// 事件（每個 cue 開始時 reset() 後重新排；at 省略＝最後一次 update 的時間，建議一律明寫）
//   zz.reset({ pos, yaw, form, emotion, glow, rise, seed })      清空事件、設定起始狀態
//   zz.fold(form, dur = 1.3, at?, { scale, fumble })             摺紙變形；form＝'idle'（貓）｜'card'｜'plane'｜'megaphone'｜
//                                                                 'magnifier'｜'lantern'｜'hat'｜'sheet'（方形燈籠紙）
//                                                                 時序見 FOLD_BEATS（摺紙聲 S2 對 FOLD_BEATS.crease、落點對 .land）；
//                                                                 換造型在紙包縮到最小時硬切（不交叉淡化、不翻到側面）
//   zz.say(lipsync, at?)                                          說話嘴型：audio/lipsync 的 { fps: 12, frames: [0–3] }（0 閉、1 半開、2 大開、3 圓唇）
//   zz.emote(emotion, at?)                                        情緒：'neutral'｜'happy'（開心）｜'curious'（好奇）｜'worried'（擔心，耳朵壓平、尾巴收起）｜
//                                                                 'proud'（得意）｜'sad'（失落，耳朵垂下）；耳朵、尾巴、頭用彈簧過渡，換情緒加眨一次
//   zz.blink(at?)、zz.twitch('l'|'r'|'both', at?)                 加眨一次；耳朵動一下（察覺到什麼，a3_c003）
//   zz.look(yaw, dur?, at?)                                       轉頭（±0.5 rad 內）
//   zz.walkTo(pos, dur, at?)                                      小跳步走路（每秒約 1.25 步，身體轉向行進方向、到了轉回正面）
//   zz.hopTo(pos, dur, height?, at?)                              大跳（跳上台口）：預備蹲 → 拋物線 → 落地壓扁回彈、耳朵晃一下
//   zz.flyTo(pos, dur, height?, at?)                              弧線飛行（紙飛機機頭朝飛行方向）
//   zz.glideTo(pos, dur, at?)、zz.turn(yaw, dur?, at?)            平移、轉身
//   zz.hush(at?)                                                  收摺收聲訊號（S3）：耳朵、尾巴收摺、閉眼點頭；S3 對 at＋HUSH_BEATS.snap
//   zz.glow(to, dur = 1.5, at?)                                   燈籠亮度（只做慢漸變；FX14）
//   zz.rise(dur, at?)                                             方形燈籠紙從平躺立起（a0_c002 開頭）
//   也可以一次給整個事件表：zz.setTrack({ start, events })（欄位同上，見 ZhezheEvent）
//   cue 接線：zz.setTrack(zhezheTrackFromTimeline(timeline, { pos, form, emotion, seed: zhezheSeed(cue.id) }, lipsync))
//   ——把 cue 裡 target＝'zhezhe' 的 zhezhe.* 動畫與折折的台詞轉成事件（名稱見該函式說明）
//
// 查詢
//   zz.poseAt(t)：該秒的完整姿勢（測試、量測用）；zz.probe()：世界外框、造型、嘴型、眼睛；zz.cardCorners()：題卡四角世界座標；
//   zz.triangles：三角面數（含外輪廓）；Zhezhe.mouthAt(lipsync, 秒)：對嘴值
//
// 安全與風格（CLAUDE.md 兒童安全界線第 9 條、v1.2 第 17.3 節）
//   - 材質啞光、不發光（燈籠的柔光只隨 glow 慢慢變）；變形時沒有閃光、沒有煙霧；換造型在紙包最小時硬切，同一區域一次變形約兩次明暗轉折。
//   - 眼睛只用簡單形（圓點、弧線、睜大、閉眼橫線），沒有高光點、不發光；笑點來自摺錯（fold 的 fumble），不來自症狀。
// ═══════════════════════════════════════════════════════════════════════════════════════════════════
import {
  BufferAttribute, BufferGeometry, CanvasTexture, Color, Group, Mesh, MeshBasicMaterial, PlaneGeometry, Quaternion, SRGBColorSpace,
  Vector3, type Material, type MeshStandardMaterial,
} from 'three';
import { clamp, hashString, lerp, seeded, smoothstep } from '../util/math';
import { LAYER } from './layers';
import { PAPER_T, PaperBuilder, ZZ_COLORS, inkMaterial, outlineMaterial, paperMaterial, v3, type V3 } from './zhezhe_paper';
import {
  CardForm, FOLD_FORMS, FrogForm, HatForm, LanternForm, MagnifierForm, MegaphoneForm, PlaneForm, SheetForm, partMesh,
  type FoldForm, type FormObject, type PartCtx,
} from './zhezhe_forms';

export type { FoldForm } from './zhezhe_forms';
export type ZhezheEmotion = 'neutral' | 'happy' | 'curious' | 'worried' | 'proud' | 'sad';
export const ZHEZHE_EMOTIONS: ZhezheEmotion[] = ['neutral', 'happy', 'curious', 'worried', 'proud', 'sad'];
export type ZhezheFacing = 'front' | 'left' | 'right' | number;
export interface LipsyncFrames { fps: number; frames: number[] }

export interface ZhezheOptions {
  position: V3;
  height: number;
  facing?: ZhezheFacing;
  seed?: number;
  outline?: boolean;
  contactShadow?: boolean;
  castShadow?: boolean;
  renderOrder?: number;
  /** 存在感（紙面常數自發光 0–0.3，預設 0.06）：題卡模式舞台燈調暗時建議 0.18–0.22，用 update 的 state.presence 隨燈光慢慢調 */
  presence?: number;
}

export interface ZhezheStart {
  pos?: V3;
  yaw?: number;
  form?: FoldForm;
  emotion?: ZhezheEmotion;
  glow?: number;
  /** 方形燈籠紙立起程度（form＝'sheet' 時）：0 平躺、1 立起 */
  rise?: number;
  seed?: number;
  visible?: boolean;
}

export type MoveStyle = 'walk' | 'hop' | 'fly' | 'glide';
export type ZhezheEvent =
  | { type: 'fold'; t: number; form: FoldForm; dur?: number; scale?: number; fumble?: boolean }
  | { type: 'emotion'; t: number; emotion: ZhezheEmotion }
  | { type: 'say'; t: number; lips: LipsyncFrames }
  | { type: 'blink'; t: number }
  | { type: 'twitch'; t: number; ear?: 'l' | 'r' | 'both' }
  | { type: 'look'; t: number; yaw: number; dur?: number }
  | { type: 'move'; t: number; dur: number; to: V3; style?: MoveStyle; height?: number }
  | { type: 'turn'; t: number; yaw: number; dur?: number }
  | { type: 'hush'; t: number; dur?: number }
  | { type: 'glow'; t: number; to: number; dur?: number }
  | { type: 'rise'; t: number; to?: number; dur?: number }
  | { type: 'visible'; t: number; on: boolean };

export interface ZhezheTrack { start: ZhezheStart; events: ZhezheEvent[] }

/** update 的即時覆寫（不經彈簧） */
export interface ZhezheState { pos?: V3; yaw?: number; mouth?: number | null; visible?: boolean; glow?: number; presence?: number }

/** 摺紙造型（大片薄紙）的直射光反應倍率與補上的存在感 */
const FORM_DIRECT = 0.5, FORM_PRESENCE_ADD = 0.42;

/** 固定步長（秒） */
export const ZZ_STEP = 1 / 120;

/**
 * 摺紙變形的節拍（dur 的比例）。一般造型：0–0.12 預備（壓扁）→ 0.08–0.42 原造型收摺成紙包 → 0.24–0.45 紙包縮到最小（輕轉 ±16°）→
 * 0.45 硬切換造型（紙包最小、只有約 1/3 大）→ 0.45–0.94 新造型由紙包攤開、長回原大小 → 0.94 落點。
 * 從 sheet（方形燈籠紙）開始：三下摺在 crease（各自的落點），之後縮成紙包、攤開成新造型。
 * 摺紙聲 S2 建議對 crease；落點（land）可以加一聲輕的紙張「啪」。
 */
export const FOLD_BEATS = {
  defaultDur: 1.3,
  normal: { crease: [0.1], swap: 0.45, land: 0.94 },
  fromSheet: { crease: [0.6 * 0.28, 0.6 * 0.62, 0.6 * 0.96], swap: 0.68, land: 0.97 },
} as const;
/** 收摺收聲訊號：snap＝耳朵、尾巴收好的瞬間（S3 對這裡），秒 */
export const HUSH_BEATS = { dur: 1.4, snap: 0.55 } as const;

interface Phases { c0: number; c1: number; f0: number; swap: number; f1: number; o0: number; o1: number; antic: number; hop: number }
const PH_NORMAL: Phases = { c0: 0.08, c1: 0.42, f0: 0.24, swap: 0.45, f1: 0.66, o0: 0.5, o1: 0.94, antic: 1, hop: 0.14 };
const PH_SHEET: Phases = { c0: 0, c1: 0.6, f0: 0.6, swap: 0.68, f1: 0.82, o0: 0.72, o1: 0.97, antic: 0, hop: 0.08 };

// ─────────────────────────────────────────── 純函式小工具 ───────────────────────────────────────────
const easeIO = (t: number): number => { t = clamp(t); return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; };
const easeOut = (t: number): number => { t = clamp(t); return 1 - (1 - t) * (1 - t); };
const sine = (t: number): number => 0.5 - 0.5 * Math.cos(Math.PI * clamp(t));
const bump = (t: number, a: number, b: number): number => (t <= a || t >= b ? 0 : Math.sin((Math.PI * (t - a)) / (b - a)));
/** 二階彈簧的單位步階響應（τ＜0 為 0）：f 頻率 Hz、z 阻尼比 */
function stepResp(tau: number, f: number, z: number): number {
  if (tau <= 0) return 0;
  const w = 2 * Math.PI * f, wd = w * Math.sqrt(1 - z * z);
  return 1 - Math.exp(-z * w * tau) * (Math.cos(wd * tau) + (z / Math.sqrt(1 - z * z)) * Math.sin(wd * tau));
}
/** 衰減正弦（耳朵動一下、落地晃一下） */
function impulse(tau: number, f: number, z: number): number {
  if (tau <= 0) return 0;
  const w = 2 * Math.PI * f;
  return Math.exp(-z * w * tau) * Math.sin(w * Math.sqrt(1 - z * z) * tau);
}
const quant = (t: number): number => Math.round(t / ZZ_STEP) * ZZ_STEP;

// ─────────────────────────────────────────── 情緒目標 ───────────────────────────────────────────
interface EmoTarget {
  /** 耳朵前後（正＝往後壓平）與外翻（正＝往外垂），左右各一 */
  epL: number; epR: number; erL: number; erR: number;
  headP: number; headR: number;
  tailLift: number; tailCurl: number; tailLen: number; wag: number;
  chest: number; brows: number;
  eyes: EyeShape;
}
type EyeShape = 'open' | 'wide' | 'happy' | 'closed';
const EMO: Record<ZhezheEmotion, EmoTarget> = {
  neutral: { epL: 0.05, epR: 0.05, erL: 0.12, erR: 0.12, headP: 0, headR: 0, tailLift: 0.3, tailCurl: 1, tailLen: 1, wag: 0.25, chest: 0, brows: 0, eyes: 'open' },
  happy: { epL: -0.08, epR: -0.08, erL: 0.05, erR: 0.05, headP: -0.05, headR: 0.07, tailLift: 0.6, tailCurl: 1.15, tailLen: 1, wag: 0.8, chest: 0.4, brows: 0, eyes: 'happy' },
  curious: { epL: -0.28, epR: 0.22, erL: 0.02, erR: 0.2, headP: 0.02, headR: 0.2, tailLift: 0.85, tailCurl: 1.75, tailLen: 1, wag: 0, chest: 0, brows: 0, eyes: 'wide' },
  worried: { epL: 1.15, epR: 1.15, erL: 0.5, erR: 0.5, headP: 0.12, headR: 0, tailLift: -0.55, tailCurl: 2.3, tailLen: 0.72, wag: 0, chest: -0.3, brows: 1, eyes: 'open' },
  proud: { epL: -0.1, epR: -0.1, erL: 0.03, erR: 0.03, headP: -0.17, headR: -0.05, tailLift: 1.0, tailCurl: 0.7, tailLen: 1.05, wag: 0.3, chest: 1, brows: 0, eyes: 'happy' },
  sad: { epL: 0.45, epR: 0.45, erL: 1.05, erR: 1.05, headP: 0.2, headR: 0.04, tailLift: -0.25, tailCurl: 0.55, tailLen: 0.9, wag: 0, chest: -0.2, brows: 0.6, eyes: 'open' },
};
type EmoKey = Exclude<keyof EmoTarget, 'eyes'>;
const SPRING: Record<EmoKey, [number, number]> = {
  epL: [2.4, 0.42], epR: [2.4, 0.42], erL: [2.2, 0.45], erR: [2.2, 0.45], headP: [1.4, 0.7], headR: [1.4, 0.7],
  tailLift: [0.9, 0.6], tailCurl: [0.9, 0.65], tailLen: [0.9, 0.8], wag: [0.8, 0.9], chest: [1.2, 0.8], brows: [3, 0.9],
};

// ─────────────────────────────────────────── 姿勢 ───────────────────────────────────────────
export interface ZhezhePose {
  t: number;
  visible: boolean;
  /** 地面點（世界） */
  pos: V3;
  /** 離地高度（折折身高單位） */
  air: number;
  /** 整體朝向（弧度） */
  yaw: number;
  form: FoldForm;
  /** 目前造型攤開程度 0–1 */
  open: number;
  /** 翻面角（弧度，換造型時） */
  spin: number;
  /** 本地 z 壓扁 0–1 */
  press: number;
  scale: number;
  formScale: number;
  sx: number;
  sy: number;
  /** 整體搖晃（摺錯時的 oops、落地） */
  wobble: number;
  /** 紙飛機飛行時機頭方向與傾斜 */
  heading: number | null;
  bank: number;
  pitch: number;
  earL: [number, number];
  earR: [number, number];
  head: [number, number, number];
  tail: { lift: number; curl: number; len: number; wag: number };
  legs: [number, number];
  eyes: EyeShape;
  brows: number;
  /** −1＝不說話（閉嘴「人」字），0–3＝對嘴值 */
  mouth: number;
  breath: number;
  chest: number;
  glow: number;
  rise: number;
  /** 正在走／跳 */
  moving: boolean;
}

// ─────────────────────────────────────────── 臉 ───────────────────────────────────────────
/** 臉的兩半是平面，以中央直摺線為稜（往前凸），兩側各往後斜 FACE_K */
const FACE_Z0 = 0.112, FACE_K = 0.42;
const faceZ = (x: number): number => FACE_Z0 - FACE_K * Math.abs(x);
type Tri2 = [number, number, number, number, number, number];

function faceGeo(tris: Tri2[], off: number): BufferGeometry {
  const pos = new Float32Array(tris.length * 9);
  tris.forEach((tr, i) => {
    for (let k = 0; k < 3; k++) {
      const x = tr[k * 2], y = tr[k * 2 + 1];
      pos[i * 9 + k * 3] = x; pos[i * 9 + k * 3 + 1] = y; pos[i * 9 + k * 3 + 2] = faceZ(x) + off;
    }
  });
  const g = new BufferGeometry();
  g.setAttribute('position', new BufferAttribute(pos, 3));
  g.computeVertexNormals();
  return g;
}
function ellipse(cx: number, cy: number, rx: number, ry: number, seg = 14): Tri2[] {
  const out: Tri2[] = [];
  for (let i = 0; i < seg; i++) {
    const a0 = (i / seg) * Math.PI * 2, a1 = ((i + 1) / seg) * Math.PI * 2;
    out.push([cx, cy, cx + Math.cos(a0) * rx, cy + Math.sin(a0) * ry, cx + Math.cos(a1) * rx, cy + Math.sin(a1) * ry]);
  }
  return out;
}
function strip(pts: [number, number][], w: number): Tri2[] {
  const out: Tri2[] = [];
  for (let i = 0; i < pts.length - 1; i++) {
    const [x0, y0] = pts[i], [x1, y1] = pts[i + 1];
    const dx = x1 - x0, dy = y1 - y0, l = Math.hypot(dx, dy) || 1;
    const nx = (-dy / l) * (w / 2), ny = (dx / l) * (w / 2);
    out.push([x0 - nx, y0 - ny, x1 - nx, y1 - ny, x1 + nx, y1 + ny], [x0 - nx, y0 - ny, x1 + nx, y1 + ny, x0 + nx, y0 + ny]);
  }
  return out;
}
const arcPts = (cx: number, cy: number, r: number, a0: number, a1: number, n = 8): [number, number][] =>
  Array.from({ length: n + 1 }, (_, i) => { const a = a0 + ((a1 - a0) * i) / n; return [cx + Math.cos(a) * r, cy + Math.sin(a) * r] as [number, number]; });

class FaceDecals {
  readonly group = new Group();
  private eyes: Record<EyeShape, Mesh>;
  private brows: Mesh;
  private mouths: Mesh[];
  readonly tris: number;
  constructor(ink: Material, renderOrder: number) {
    const EX = 0.118, EY = 0.168;
    const both = (f: (cx: number) => Tri2[]): Tri2[] => [...f(-EX), ...f(EX)];
    const mk = (tris: Tri2[], off: number, mat: Material = ink): Mesh => {
      const m = new Mesh(faceGeo(tris, off), mat);
      m.renderOrder = renderOrder;
      this.group.add(m);
      return m;
    };
    let n = 0;
    const count = (t: Tri2[]): Tri2[] => { n += t.length; return t; };
    this.eyes = {
      open: mk(count(both((cx) => ellipse(cx, EY, 0.029, 0.036))), 0.004),
      wide: mk(count(both((cx) => ellipse(cx, EY + 0.002, 0.036, 0.044))), 0.004),
      happy: mk(count(both((cx) => strip(arcPts(cx, EY - 0.018, 0.031, 0.35, Math.PI - 0.35), 0.014))), 0.004),
      closed: mk(count(both((cx) => strip([[cx - 0.033, EY - 0.004], [cx - 0.012, EY - 0.008], [cx + 0.012, EY - 0.008], [cx + 0.033, EY - 0.004]], 0.012))), 0.004),
    };
    // 擔心的小眉毛（內側上提）
    this.brows = mk(count([...strip([[-0.165, 0.226], [-0.082, 0.246]], 0.012), ...strip([[0.082, 0.246], [0.165, 0.226]], 0.012)]), 0.004);
    // 鼻子（倒三角，跨中央稜線所以在 x＝0 補頂點）
    mk(count([[-0.027, 0.106, 0, 0.08, 0, 0.106], [0, 0.106, 0, 0.08, 0.027, 0.106]]), 0.016, inkMaterial(ZZ_COLORS.nose));
    // 嘴：−1 閉嘴「人」字；1 半開、2 大開（小三角）；3 圓唇
    const closed = count([...strip([[0, 0.081], [-0.016, 0.064], [-0.04, 0.059]], 0.0105), ...strip([[0, 0.081], [0.016, 0.064], [0.04, 0.059]], 0.0105)]);
    const tri = (w: number, top: number, bot: number): Tri2[] => count([[-w, top, 0, bot, 0, top], [0, top, 0, bot, w, top]]);
    const round: Tri2[] = [];
    for (let i = 0; i < 8; i++) {
      const a0 = (i / 8) * Math.PI * 2, a1 = ((i + 1) / 8) * Math.PI * 2;
      round.push([0, 0.048, Math.cos(a0) * 0.024, 0.048 + Math.sin(a0) * 0.03, Math.cos(a1) * 0.024, 0.048 + Math.sin(a1) * 0.03]);
    }
    count(round);
    this.mouths = [mk(closed, 0.016), mk(tri(0.03, 0.078, 0.04), 0.016), mk(tri(0.042, 0.08, 0.014), 0.016), mk(round, 0.016)];
    // 鬍鬚（短、細、暖褐，不超出臉）
    const wh = inkMaterial('#8a5d47');
    mk(count([...strip([[-0.135, 0.07], [-0.215, 0.083]], 0.0065), ...strip([[-0.135, 0.052], [-0.21, 0.04]], 0.0065),
      ...strip([[0.135, 0.07], [0.215, 0.083]], 0.0065), ...strip([[0.135, 0.052], [0.21, 0.04]], 0.0065)]), 0.004, wh);
    // 腮紅
    mk(count([...ellipse(-0.19, 0.11, 0.032, 0.018, 10), ...ellipse(0.19, 0.11, 0.032, 0.018, 10)]), 0.003, inkMaterial(ZZ_COLORS.blush));
    this.tris = n;
  }
  set(eyes: EyeShape, brows: number, mouth: number, open: number): void {
    const e: EyeShape = open < 0.7 ? 'closed' : eyes;
    for (const k of Object.keys(this.eyes) as EyeShape[]) this.eyes[k].visible = k === e;
    this.brows.visible = brows > 0.5 && e !== 'happy';
    const mi = mouth <= 0 ? 0 : Math.min(3, Math.round(mouth));
    this.mouths.forEach((m, i) => { m.visible = i === mi; });
  }
}

// ─────────────────────────────────────────── 尾巴（摺紙長條） ───────────────────────────────────────────
/**
 * 一條斜摺的紙條：每道摺痕讓紙條轉個方向、翻到另一面，所以尾巴一節淺橙一節白。
 * 摺痕位置與方向每格依 lift（起始角）、curl（捲曲）、wag（輕搖）、len（長度）算出，網格拓撲固定。
 */
class TailStrip {
  readonly group = new Group();
  private geo: BufferGeometry;
  private olGeo: BufferGeometry;
  readonly n = 9;
  readonly tris: number;
  private root = new Vector3(0.14, 0.075, -0.085);
  private U: Vector3; private V = new Vector3(0, 1, 0); private N: Vector3;
  constructor(ctx: PartCtx, olMat: Material | null, private olW: number) {
    const yaw = 0.55;
    this.U = new Vector3(Math.cos(yaw), 0, -Math.sin(yaw));
    this.N = new Vector3().crossVectors(this.U, this.V).normalize();
    const n = this.n, triPer = 12, T = n * triPer;
    const pos = new Float32Array(T * 9), col = new Float32Array(T * 9), bak = new Float32Array(T * 9), edg = new Float32Array(T * 9), uv = new Float32Array(T * 6);
    const cf = new Color(ZZ_COLORS.front), cb = new Color(ZZ_COLORS.back), ce = new Color(ZZ_COLORS.edge);
    for (let i = 0; i < n; i++) for (let k = 0; k < triPer; k++) {
      const t = i * triPer + k;
      // 0–1 正面、2–3 背面、4–11 側邊
      const c = k < 2 ? (i % 2 === 0 ? cf : cb) : k < 4 ? (i % 2 === 0 ? cb : cf) : ce;
      const hide = k < 4 ? (k % 2 === 0 ? [false, true, false] : [false, false, true]) : [true, true, true];
      for (let v = 0; v < 3; v++) {
        const o = t * 9 + v * 3;
        col[o] = c.r; col[o + 1] = c.g; col[o + 2] = c.b;
        bak[o] = c.r; bak[o + 1] = c.g; bak[o + 2] = c.b;
        for (let q = 0; q < 3; q++) edg[o + q] = q === v ? 1 : hide[q] ? 1 : 0;
        uv[t * 6 + v * 2] = i * 0.17 + v * 0.05; uv[t * 6 + v * 2 + 1] = v * 0.07;
      }
    }
    this.geo = new BufferGeometry();
    this.geo.setAttribute('position', new BufferAttribute(pos, 3));
    this.geo.setAttribute('normal', new BufferAttribute(new Float32Array(T * 9), 3));
    this.geo.setAttribute('color', new BufferAttribute(col, 3));
    this.geo.setAttribute('aBack', new BufferAttribute(bak, 3));
    this.geo.setAttribute('aEdge', new BufferAttribute(edg, 3));
    this.geo.setAttribute('uv', new BufferAttribute(uv, 2));
    const m = new Mesh(this.geo, ctx.mat);
    m.castShadow = ctx.castShadow;
    m.renderOrder = ctx.renderOrder;
    m.frustumCulled = false;
    this.group.add(m);
    this.olGeo = new BufferGeometry();
    this.olGeo.setAttribute('position', new BufferAttribute(new Float32Array(n * 6 * 3), 3));
    if (olMat) {
      const ol = new Mesh(this.olGeo, olMat);
      ol.renderOrder = ctx.renderOrder;
      ol.frustumCulled = false;
      this.group.add(ol);
    }
    this.tris = T + (olMat ? n * 2 : 0);
    ctx.tris.n += this.tris;
  }
  update(lift: number, curl: number, len: number, wag: number, t: number): void {
    const n = this.n;
    const w = 2 * Math.PI * 0.7;
    const th: number[] = [];
    let a = lift + wag * 0.2 * Math.sin(w * t);
    for (let i = 0; i < n; i++) {
      th.push(a);
      const turn = curl * (0.11 + 0.05 * (i + 1)) + wag * 0.09 * Math.sin(w * t - 0.75 * (i + 1));
      a += clamp(turn, -1.05, 1.05);
    }
    const L = (i: number): number => 0.064 * len * (1 - 0.035 * i);
    const W = (i: number): number => (i >= n ? 0 : 0.09 - 0.005 * i);
    const cs: [number, number][] = [[0, 0]];
    for (let i = 0; i < n; i++) cs.push([cs[i][0] + L(i) * Math.cos(th[i]), cs[i][1] + L(i) * Math.sin(th[i])]);
    // 摺痕：在第 i 個節點，方向垂直於前後兩段的角平分線
    const crease = (i: number): [[number, number], [number, number]] => {
      if (i >= n) { const p = cs[n]; return [p, p]; }
      let dir: number, half: number;
      if (i === 0) { dir = th[0] + Math.PI / 2; half = W(0) / 2; }
      else { const d = th[i] - th[i - 1]; dir = (th[i] + th[i - 1]) / 2 + Math.PI / 2; half = W(i) / 2 / Math.max(0.4, Math.cos(d / 2)); }
      const c = cs[i], ux = Math.cos(dir) * half, uy = Math.sin(dir) * half;
      return [[c[0] - ux, c[1] - uy], [c[0] + ux, c[1] + uy]];
    };
    const P = (p: [number, number], z: number): Vector3 => this.root.clone().addScaledVector(this.U, p[0]).addScaledVector(this.V, p[1]).addScaledVector(this.N, z);
    const pos = this.geo.getAttribute('position') as BufferAttribute;
    const nor = this.geo.getAttribute('normal') as BufferAttribute;
    const olp = this.olGeo.getAttribute('position') as BufferAttribute;
    const tt = PAPER_T;
    let vi = 0;
    const put = (a: Vector3, b: Vector3, c: Vector3): void => {
      const nn = new Vector3().subVectors(b, a).cross(new Vector3().subVectors(c, a));
      if (nn.lengthSq() > 1e-14) nn.normalize();
      for (const p of [a, b, c]) { pos.setXYZ(vi, p.x, p.y, p.z); nor.setXYZ(vi, nn.x, nn.y, nn.z); vi++; }
    };
    let oi = 0;
    for (let i = 0; i < n; i++) {
      const [r0, l0] = crease(i), [r1, l1] = crease(i + 1);
      const z = i * tt * 1.08;
      const q = [r0, r1, l1, l0];
      const F = q.map((p) => P(p, z + tt / 2)), B = q.map((p) => P(p, z - tt / 2));
      put(F[0], F[1], F[2]); put(F[0], F[2], F[3]);
      put(B[0], B[2], B[1]); put(B[0], B[3], B[2]);
      for (let k = 0; k < 4; k++) { const j = (k + 1) % 4; put(F[k], B[k], B[j]); put(F[k], B[j], F[j]); }
      // 外輪廓：同一節往外擴 olW、放在這一節後面
      const cx = (q[0][0] + q[1][0] + q[2][0] + q[3][0]) / 4, cy = (q[0][1] + q[1][1] + q[2][1] + q[3][1]) / 4;
      const ex = q.map((p) => { const dx = p[0] - cx, dy = p[1] - cy, d = Math.hypot(dx, dy) || 1; return [p[0] + (dx / d) * this.olW * 1.3, p[1] + (dy / d) * this.olW * 1.3] as [number, number]; });
      const E = ex.map((p) => P(p, z - tt * 0.9));
      for (const p of [E[0], E[1], E[2], E[0], E[2], E[3]]) { olp.setXYZ(oi++, p.x, p.y, p.z); }
    }
    pos.needsUpdate = true; nor.needsUpdate = true; olp.needsUpdate = true;
  }
}

// ─────────────────────────────────────────── 貓本體 ───────────────────────────────────────────
class CatRig implements FormObject {
  readonly group = new Group();
  private body = new Group();
  private bodyMesh: Group;
  private head = new Group();
  private earL = new Group();
  private earR = new Group();
  private earBaseL = new Quaternion();
  private earBaseR = new Quaternion();
  private legL = new Group();
  private legR = new Group();
  readonly face: FaceDecals;
  readonly tail: TailStrip;
  static readonly NECK = new Vector3(0, 0.415, 0.03);
  constructor(ctx: PartCtx, ink: Material) {
    // 身體：坐姿的多面體（前中線有一道山摺稜），淺橙；前腳是摺過來的白色背面
    const B = (x: number, y: number, z: number): Vector3[] => (x === 0 ? [v3(0, y, z)] : [v3(-x, y, z), v3(x, y, z)]);
    const bodyPts = [
      ...B(0, 0, 0.17), ...B(0.15, 0, 0.11), ...B(0.19, 0, -0.08), ...B(0.12, 0, -0.17), ...B(0, 0, -0.19),
      ...B(0.205, 0.14, -0.06), ...B(0.15, 0.17, -0.17), ...B(0, 0.19, -0.21),
      ...B(0, 0.27, 0.165), ...B(0.12, 0.28, 0.08),
      ...B(0.1, 0.43, 0.0), ...B(0, 0.45, 0.075), ...B(0, 0.43, -0.09), ...B(0.07, 0.44, -0.06),
    ];
    const bb = new PaperBuilder().hull(bodyPts, () => ZZ_COLORS.front);
    this.bodyMesh = partMesh(bb, ctx);
    this.body.add(this.bodyMesh);

    // 頭：前面是兩個斜平面（中央直摺線往前凸）＋後腦多面體
    const F = (x: number, y: number): Vector3 => v3(x, y, faceZ(x));
    const headPts = [
      F(0, 0.29), F(-0.25, 0.29), F(0.25, 0.29), F(-0.275, 0.14), F(0.275, 0.14), F(-0.13, -0.005), F(0.13, -0.005), F(0, -0.045),
      v3(0, 0.27, -0.15), v3(-0.19, 0.27, -0.07), v3(0.19, 0.27, -0.07), v3(-0.2, 0.12, -0.11), v3(0.2, 0.12, -0.11),
      v3(-0.1, 0.0, -0.1), v3(0.1, 0.0, -0.1), v3(0, 0.04, -0.15),
    ];
    const hb = new PaperBuilder().hull(headPts, () => ZZ_COLORS.front);
    // 嘴邊：往上摺的白色紙片（左右兩片各貼在臉的一半）
    const muz = (pts: [number, number][]): void => { hb.slab(pts.map(([x, y]) => F(x, y)), ZZ_COLORS.back, ZZ_COLORS.front, PAPER_T, PAPER_T / 2 + 0.0012); };
    muz([[0, 0.112], [-0.125, 0.1], [-0.06, -0.004], [0, -0.03]]);
    muz([[0, 0.112], [0, -0.03], [0.06, -0.004], [0.125, 0.1]]);
    this.head.add(partMesh(hb, ctx));
    this.face = new FaceDecals(ink, ctx.renderOrder + 1);
    this.head.add(this.face.group);
    ctx.tris.n += this.face.tris;

    // 耳朵：三角紙片（外淺橙、內側另一片白紙），中間一道谷摺；鉸鏈在頭頂邊
    const ear = (side: -1 | 1): Group => {
      const eb = new PaperBuilder();
      const b0 = v3(-0.095, 0, 0), b1 = v3(0.095, 0, 0), tip = v3(0.035 * side, 0.225, -0.012), mid = v3(0, 0, -0.022);
      eb.slab([b0, mid, tip], ZZ_COLORS.front, ZZ_COLORS.back);
      eb.slab([mid, b1, tip], ZZ_COLORS.front, ZZ_COLORS.back);
      const i0 = v3(-0.058, 0.022, 0.0), i1 = v3(0.058, 0.022, 0.0), it = v3(0.028 * side, 0.165, -0.01), im = v3(0, 0.022, -0.014);
      eb.slab([i0, im, it], ZZ_COLORS.back, ZZ_COLORS.front, PAPER_T, PAPER_T * 1.05);
      eb.slab([im, i1, it], ZZ_COLORS.back, ZZ_COLORS.front, PAPER_T, PAPER_T * 1.05);
      return partMesh(eb, ctx);
    };
    this.earL.add(ear(-1));
    this.earR.add(ear(1));
    const ex = 0.155;
    this.earL.position.set(-ex, 0.285, faceZ(ex) - 0.03);
    this.earR.position.set(ex, 0.285, faceZ(ex) - 0.03);
    this.earBaseL.setFromAxisAngle(new Vector3(0, 1, 0), Math.atan(FACE_K));
    this.earBaseR.setFromAxisAngle(new Vector3(0, 1, 0), -Math.atan(FACE_K));
    this.head.add(this.earL, this.earR);
    this.head.position.copy(CatRig.NECK);

    // 前腳：細長的多面體（白色＝摺過來的背面），鉸鏈在胸前
    const leg = (cx: number): Group => {
      // 正面是一整片朝前微向下的平面（受光、白色清楚），背面收成稜
      const pts = [v3(cx - 0.042, 0.31, 0.125), v3(cx + 0.042, 0.31, 0.125), v3(cx, 0.31, 0.06),
        v3(cx - 0.05, 0, 0.205), v3(cx + 0.05, 0, 0.205), v3(cx - 0.05, 0.03, 0.212), v3(cx + 0.05, 0.03, 0.212), v3(cx, 0, 0.1)].map((p) => p.sub(v3(cx, 0.31, 0.1)));
      return partMesh(new PaperBuilder().hull(pts, () => ZZ_COLORS.back), ctx);
    };
    this.legL.add(leg(-0.075)); this.legL.position.set(-0.075, 0.31, 0.1);
    this.legR.add(leg(0.075)); this.legR.position.set(0.075, 0.31, 0.1);

    this.tail = new TailStrip(ctx, ctx.outlineMat, ctx.outlineW);
    this.body.add(this.tail.group, this.head, this.legL, this.legR);
    this.group.add(this.body);
  }
  setOpen(): void { /* 由 apply 處理 */ }
  apply(p: ZhezhePose): void {
    const o = p.form === 'idle' ? p.open : 1;
    const c = 1 - o;
    // 身體呼吸、挺胸、收摺時壓扁
    const sy = (1 + p.breath * 0.012) * lerp(0.62, 1, easeIO(o));
    this.bodyMesh.scale.set(1 + c * 0.06, sy, 1 + p.chest * 0.045);
    // 頭
    this.head.position.set(CatRig.NECK.x, CatRig.NECK.y * sy - c * 0.08, CatRig.NECK.z + p.chest * 0.008);
    this.head.rotation.set(p.head[0] + c * 1.0, p.head[2], p.head[1], 'YXZ');
    // 耳朵：base × 外翻（z）× 前後（x）；收摺時往前摺平蓋在臉上
    const earQ = (base: Quaternion, side: -1 | 1, pitch: number, roll: number): Quaternion => base.clone()
      .multiply(new Quaternion().setFromAxisAngle(new Vector3(0, 0, 1), -side * roll))
      .multiply(new Quaternion().setFromAxisAngle(new Vector3(1, 0, 0), -(pitch - c * 2.3)));
    this.earL.quaternion.copy(earQ(this.earBaseL, -1, p.earL[0], p.earL[1]));
    this.earR.quaternion.copy(earQ(this.earBaseR, 1, p.earR[0], p.earR[1]));
    // 腳
    this.legL.rotation.x = p.legs[0] + c * 1.1;
    this.legR.rotation.x = p.legs[1] + c * 1.1;
    this.legL.position.y = 0.31 * sy; this.legR.position.y = 0.31 * sy;
    // 尾巴
    this.tail.update(p.tail.lift - c * 0.6, p.tail.curl + c * 3, p.tail.len * lerp(0.35, 1, o), p.tail.wag * o, p.t);
    this.face.set(p.eyes, p.brows, p.mouth, o);
  }
}

// ─────────────────────────────────────────── 地面柔影 ───────────────────────────────────────────
let shadowTex: CanvasTexture | null = null;
function zzShadowTexture(): CanvasTexture {
  if (shadowTex) return shadowTex;
  const c = document.createElement('canvas');
  c.width = 128; c.height = 128;
  const g = c.getContext('2d')!;
  const grd = g.createRadialGradient(64, 64, 4, 64, 64, 62);
  grd.addColorStop(0, 'rgba(45,28,16,0.5)');
  grd.addColorStop(0.55, 'rgba(45,28,16,0.2)');
  grd.addColorStop(1, 'rgba(45,28,16,0)');
  g.fillStyle = grd;
  g.fillRect(0, 0, 128, 128);
  shadowTex = new CanvasTexture(c);
  shadowTex.colorSpace = SRGBColorSpace;
  return shadowTex;
}

/** 各造型的柔影強度、腳印大小 */
const FORM_SHADOW: Record<FoldForm, [number, number, number]> = {
  idle: [1, 0.62, 0.42], card: [0.3, 1.1, 0.3], plane: [0.3, 0.9, 0.35], megaphone: [0.55, 0.7, 0.4], magnifier: [0.45, 0.6, 0.25],
  lantern: [0.7, 0.55, 0.45], hat: [0.75, 0.7, 0.35], sheet: [0.5, 0.75, 0.3], frog: [0.9, 0.8, 0.4],
};

// ─────────────────────────────────────────── 主類別 ───────────────────────────────────────────
export class Zhezhe {
  readonly group = new Group();
  readonly height: number;
  readonly triangles: number;
  private scaler = new Group();
  private mover = new Group();
  private holders = new Map<FoldForm, Group>();
  private objs = new Map<FoldForm, FormObject>();
  private cat: CatRig;
  private card: CardForm;
  private lantern: LanternForm;
  private sheet: SheetForm;
  private shadow: Mesh | null = null;
  private track: ZhezheTrack;
  private sorted: ZhezheEvent[] = [];
  private lastT = 0;
  private baseYaw: number;
  private seed: number;
  private mats: Material[] = [];
  /** 地面柔影開關（量測背景明度差時暫時關掉） */
  shadowEnabled = true;
  private presenceU = { value: 0.06 };
  private formPresenceU = { value: 0.06 + FORM_PRESENCE_ADD };

  constructor(readonly opts: ZhezheOptions) {
    this.height = opts.height;
    this.seed = opts.seed ?? 7;
    const f = opts.facing ?? 'front';
    this.baseYaw = typeof f === 'number' ? f : f === 'left' ? -0.5 : f === 'right' ? 0.5 : 0;
    const ro = opts.renderOrder ?? LAYER.actors.order + 15;
    this.presenceU.value = opts.presence ?? 0.06;
    this.formPresenceU.value = this.presenceU.value + FORM_PRESENCE_ADD;
    const mat = paperMaterial({ presence: this.presenceU });
    const ol = opts.outline === false ? null : outlineMaterial();
    const ink = inkMaterial();
    this.mats.push(mat, ink);
    if (ol) this.mats.push(ol);
    const ctx: PartCtx = { mat, outlineMat: ol, outlineW: 0.0135, castShadow: opts.castShadow !== false, renderOrder: ro, tris: { n: 0 }, presence: this.presenceU, direct: 1 };
    this.cat = new CatRig(ctx, ink);
    // 摺紙造型的大片薄紙：外輪廓只用一半寬。紙片轉到側對鏡頭時，外輪廓殼會變成一條深色帶掃過畫面，
    // 寬度減半後同一區域的明暗起伏小於光敏門檻（review/G5/zhezhe/flash.json）。
    // 而且大片紙轉向時（例如題卡往前攤開那一瞬間，紙面朝下背光）會整片變暗再變亮：直射光反應減半、改由存在感補亮度。
    const formMat = paperMaterial({ presence: this.formPresenceU, direct: FORM_DIRECT });
    this.mats.push(formMat);
    const fctx: PartCtx = { ...ctx, mat: formMat, outlineW: 0.0055, presence: this.formPresenceU, direct: FORM_DIRECT };
    this.card = new CardForm(fctx);
    this.lantern = new LanternForm(fctx);
    this.sheet = new SheetForm(fctx);
    const forms: Record<FoldForm, FormObject> = {
      idle: this.cat, card: this.card, plane: new PlaneForm(fctx, ink), megaphone: new MegaphoneForm(fctx), magnifier: new MagnifierForm(fctx),
      lantern: this.lantern, hat: new HatForm(fctx), sheet: this.sheet, frog: new FrogForm(fctx, ink),
    };
    for (const k of FOLD_FORMS) {
      const h = new Group();
      h.add(forms[k].group);
      h.visible = false;
      this.holders.set(k, h);
      this.objs.set(k, forms[k]);
      this.mover.add(h);
    }
    if (opts.contactShadow !== false) {
      const sm = new MeshBasicMaterial({ map: zzShadowTexture(), transparent: true, depthWrite: false, opacity: 1 });
      this.mats.push(sm);
      this.shadow = new Mesh(new PlaneGeometry(1, 1), sm);
      this.shadow.rotation.x = -Math.PI / 2;
      this.shadow.renderOrder = LAYER.backdrop.order + 6;
      this.scaler.add(this.shadow);
      ctx.tris.n += 2;
    }
    this.triangles = ctx.tris.n;
    this.scaler.add(this.mover);
    this.scaler.scale.setScalar(this.height);
    this.group.add(this.scaler);
    this.group.name = 'zhezhe';
    this.track = { start: { pos: opts.position, yaw: this.baseYaw, form: 'idle', emotion: 'neutral' }, events: [] };
    this.reset();
    this.update(0);
  }

  // ─── 事件 ───
  reset(start: ZhezheStart = {}): this {
    this.track = { start: { pos: this.opts.position, yaw: this.baseYaw, form: 'idle', emotion: 'neutral', glow: 0, rise: 1, visible: true, ...start }, events: [] };
    this.sorted = [];
    return this;
  }
  setTrack(track: ZhezheTrack): this {
    this.reset(track.start);
    for (const e of track.events) this.track.events.push({ ...e } as ZhezheEvent);
    this.resort();
    return this;
  }
  getTrack(): ZhezheTrack { return { start: { ...this.track.start }, events: this.track.events.map((e) => ({ ...e }) as ZhezheEvent) }; }
  private push(e: ZhezheEvent): this { this.track.events.push(e); this.resort(); return this; }
  private resort(): void { this.sorted = this.track.events.map((e, i) => ({ e, i })).sort((a, b) => a.e.t - b.e.t || a.i - b.i).map((x) => x.e); }
  private at(t?: number): number { return t ?? this.lastT; }
  fold(form: FoldForm, dur = FOLD_BEATS.defaultDur, at?: number, o: { scale?: number; fumble?: boolean } = {}): this { return this.push({ type: 'fold', t: this.at(at), form, dur, ...o }); }
  say(lips: LipsyncFrames, at?: number): this { return this.push({ type: 'say', t: this.at(at), lips }); }
  emote(emotion: ZhezheEmotion, at?: number): this { return this.push({ type: 'emotion', t: this.at(at), emotion }); }
  blink(at?: number): this { return this.push({ type: 'blink', t: this.at(at) }); }
  twitch(ear: 'l' | 'r' | 'both' = 'both', at?: number): this { return this.push({ type: 'twitch', t: this.at(at), ear }); }
  look(yaw: number, dur = 0.5, at?: number): this { return this.push({ type: 'look', t: this.at(at), yaw, dur }); }
  walkTo(to: V3, dur: number, at?: number): this { return this.push({ type: 'move', t: this.at(at), dur, to, style: 'walk' }); }
  hopTo(to: V3, dur = 0.9, height = 0.9, at?: number): this { return this.push({ type: 'move', t: this.at(at), dur, to, style: 'hop', height }); }
  flyTo(to: V3, dur: number, height = 0.6, at?: number): this { return this.push({ type: 'move', t: this.at(at), dur, to, style: 'fly', height }); }
  glideTo(to: V3, dur: number, at?: number): this { return this.push({ type: 'move', t: this.at(at), dur, to, style: 'glide' }); }
  turn(yaw: number, dur = 0.5, at?: number): this { return this.push({ type: 'turn', t: this.at(at), yaw, dur }); }
  hush(at?: number): this { return this.push({ type: 'hush', t: this.at(at), dur: HUSH_BEATS.dur }); }
  glow(to: number, dur = 1.5, at?: number): this { return this.push({ type: 'glow', t: this.at(at), to, dur }); }
  rise(dur = 1.0, at?: number, to = 1): this { return this.push({ type: 'rise', t: this.at(at), dur, to }); }
  show(on: boolean, at?: number): this { return this.push({ type: 'visible', t: this.at(at), on }); }

  /** 對嘴值（12 fps 整數 0–3；超出範圍＝−1 不說話） */
  static mouthAt(lips: LipsyncFrames | undefined, tIn: number): number {
    if (!lips || tIn < 0) return -1;
    const i = Math.floor(tIn * lips.fps + 1e-6);
    return i >= 0 && i < lips.frames.length ? lips.frames[i] : -1;
  }

  // ─── 姿勢（純函式） ───
  poseAt(tRaw: number): ZhezhePose {
    const t = quant(tRaw);
    const st = this.track.start;
    const ev = this.sorted;
    const seed = (st.seed ?? this.seed) >>> 0;
    const p: ZhezhePose = {
      t, visible: st.visible !== false, pos: [...(st.pos ?? this.opts.position)] as V3, air: 0, yaw: st.yaw ?? this.baseYaw,
      form: st.form ?? 'idle', open: 1, spin: 0, press: 0, scale: 1, formScale: 1, sx: 1, sy: 1, wobble: 0, heading: null, bank: 0, pitch: 0,
      earL: [0, 0], earR: [0, 0], head: [0, 0, 0], tail: { lift: 0, curl: 1, len: 1, wag: 0 }, legs: [0, 0], eyes: 'open', brows: 0, mouth: -1,
      breath: Math.sin((2 * Math.PI * t) / 3.1 + (seed % 7)), chest: 0, glow: st.glow ?? 0, rise: st.rise ?? 1, moving: false,
    };
    // 顯示
    for (const e of ev) if (e.type === 'visible' && e.t <= t) p.visible = e.on;

    // 摺紙變形
    let form: FoldForm = p.form, formScale = 1, settledAt = -1e9, fumbleAt = -1e9;
    let trans: { from: FoldForm; to: FoldForm; s: number; ph: Phases; fromScale: number; toScale: number } | null = null;
    for (const e of ev) {
      if (e.type !== 'fold' || e.t > t) continue;
      const dur = Math.max(0.3, e.dur ?? FOLD_BEATS.defaultDur);
      const sc = e.scale ?? 1;
      if (t < e.t + dur) {
        trans = { from: form, to: e.form, s: (t - e.t) / dur, ph: form === 'sheet' ? PH_SHEET : PH_NORMAL, fromScale: formScale, toScale: sc };
      } else { trans = null; settledAt = e.t + dur; if (e.fumble) fumbleAt = e.t + dur; }
      form = e.form; formScale = sc;
    }
    if (trans) {
      const { s, ph } = trans;
      const antic = ph.antic * bump(s, 0, 0.12);
      p.sy = 1 - 0.08 * antic; p.sx = 1 + 0.05 * antic;
      // 換造型＝在收到最小的瞬間硬切（v1.2 第 15.4 節換片規則：動作中段硬切）。不翻到側面：
      // 翻到側面時紙包會「消失再出現」，同一區域多兩次明暗轉折（光敏量測見 review/G5/zhezhe/flash.json）。
      const MIN = 0.34;
      if (s < ph.swap) {
        p.form = trans.from; p.formScale = trans.fromScale;
        p.open = 1 - (ph === PH_SHEET ? clamp((s - ph.c0) / (ph.c1 - ph.c0)) : easeIO((s - ph.c0) / (ph.c1 - ph.c0)));
        const k = easeIO((s - ph.f0) / (ph.swap - ph.f0));
        p.scale = lerp(1, ph === PH_SHEET ? 0.8 : 0.82, easeIO((s - ph.c0) / (ph.f0 - ph.c0))) * lerp(1, MIN / 0.82, k);
        p.spin = 0.28 * Math.sin(Math.PI * k);
      } else {
        p.form = trans.to; p.formScale = trans.toScale;
        p.open = easeIO((s - ph.o0) / (ph.o1 - ph.o0));
        const k = easeOut((s - ph.swap) / (ph.f1 - ph.swap));
        p.scale = lerp(MIN, 1, easeIO((s - ph.swap) / (ph.o1 - ph.swap))) * (1 + 0.04 * bump(s, ph.o1 - 0.12, 1));
        p.spin = -0.2 * Math.sin(Math.PI * k);
      }
      p.air += ph.hop * Math.sin(Math.PI * clamp((s - 0.18) / 0.64));
    } else {
      p.form = form; p.formScale = formScale;
      const ts = t - settledAt;
      if (ts >= 0 && ts < 0.6) p.sy *= 1 - 0.03 * impulse(ts, 2.2, 0.5);
    }
    // 摺錯（oops）：落定後左右晃 1.5 下
    if (t >= fumbleAt && t < fumbleAt + 1.0) p.wobble = 0.14 * impulse(t - fumbleAt, 1.5, 0.25);

    // 情緒（彈簧疊加）
    const emoEvents = ev.filter((e): e is Extract<ZhezheEvent, { type: 'emotion' }> => e.type === 'emotion');
    const base = EMO[st.emotion ?? 'neutral'];
    const val = (k: EmoKey): number => {
      let v = base[k], prev = base[k];
      const [fq, z] = SPRING[k];
      for (const e of emoEvents) { if (e.t > t) break; const tg = EMO[e.emotion][k]; v += (tg - prev) * stepResp(t - e.t, fq, z); prev = tg; }
      return v;
    };
    let emo = base, prevEyes: EyeShape = base.eyes, emoT = -1e9;
    for (const e of emoEvents) if (e.t <= t) { prevEyes = emo.eyes; emo = EMO[e.emotion]; emoT = e.t; }
    p.earL = [val('epL'), val('erL')];
    p.earR = [val('epR'), val('erR')];
    p.head = [val('headP'), val('headR'), 0];
    p.tail = { lift: val('tailLift'), curl: val('tailCurl'), len: val('tailLen'), wag: val('wag') };
    p.chest = val('chest');
    p.brows = val('brows');
    // 眼睛形狀在換情緒後 0.07 秒換（和加眨的那一次重疊，看不到硬切）
    p.eyes = t - emoT >= 0.07 ? emo.eyes : prevEyes;

    // 轉頭
    let headYaw = 0;
    for (const e of ev) if (e.type === 'look' && e.t <= t) headYaw = lerp(headYaw, e.yaw, sine((t - e.t) / (e.dur ?? 0.5)));
    p.head[2] = clamp(headYaw, -0.6, 0.6);

    // 耳朵動一下（事件＋種子決定的偶發小抖，3.5–8 秒一次）
    const tw = (ear: 'l' | 'r'): number => {
      let a = 0;
      for (const e of ev) if (e.type === 'twitch' && e.t <= t && (e.ear === undefined || e.ear === 'both' || e.ear === ear)) a += 1.0 * impulse(t - e.t, 2.6, 0.3);
      return a;
    };
    const rnd = seeded(seed * 31 + 5);
    let idleTw = 0, tt = 2 + rnd() * 3;
    let twSide = 0;
    while (tt <= t + 0.01) { const tauI = t - tt; if (tauI >= 0 && tauI < 1.2) { idleTw = 0.16 * impulse(tauI, 3, 0.4); twSide = rnd() < 0.5 ? 0 : 1; } else rnd(); tt += 3.5 + rnd() * 4.5; }
    p.earL[0] -= tw('l') + (twSide === 0 ? idleTw : 0);
    p.earR[0] -= tw('r') + (twSide === 1 ? idleTw : 0);

    // 收摺收聲訊號
    for (const e of ev) {
      if (e.type !== 'hush' || e.t > t) continue;
      const d = e.dur ?? HUSH_BEATS.dur, s = t - e.t;
      if (s > d + 0.6) continue;
      const pre = bump(s, 0, 0.3) * 0.6;
      const k = smoothstep(0.25, HUSH_BEATS.snap, s) * (1 - smoothstep(d - 0.35, d + 0.5, s));
      p.earL[0] += -0.35 * pre + (1.35 - p.earL[0]) * k; p.earR[0] += -0.35 * pre + (1.35 - p.earR[0]) * k;
      p.tail.curl += 1.6 * k; p.tail.lift -= 0.5 * k; p.tail.wag *= 1 - k;
      p.head[0] += 0.2 * k * (s < d - 0.2 ? 1 : 0.6);
      p.sy *= 1 - 0.035 * k;
      if (k > 0.55) p.eyes = 'happy';
    }

    // 移動
    let pos = new Vector3(...p.pos);
    let yaw = p.yaw;
    for (const e of ev) {
      if (e.type === 'turn' && e.t <= t) yaw = lerp(yaw, e.yaw, sine((t - e.t) / (e.dur ?? 0.5)));
      if (e.type !== 'move' || e.t > t) continue;
      const from = pos.clone(), to = new Vector3(...e.to);
      const u = clamp((t - e.t) / e.dur);
      const style = e.style ?? 'walk';
      const dir = to.x - from.x;
      const travelYaw = Math.abs(dir) > 1e-3 ? Math.sign(dir) * 0.75 : 0;
      const tIn = t - e.t;
      if (u >= 1) { pos = to; if (style === 'hop' && tIn - e.dur < 0.7) { p.sy *= 1 - 0.1 * impulse(tIn - e.dur, 2.4, 0.45); p.earL[0] += 0.5 * impulse(tIn - e.dur, 2.6, 0.35); p.earR[0] += 0.5 * impulse(tIn - e.dur, 2.6, 0.35); } continue; }
      p.moving = true;
      if (style === 'glide') { pos = from.lerp(to, sine(u)); continue; }
      if (style === 'walk') {
        const k = easeIO(u);
        pos = from.clone().lerp(to, k);
        const dist = from.distanceTo(to) / this.height;
        const steps = Math.max(1, Math.round((e.dur * 1.25)));
        const ph = k * steps;
        p.air += 0.034 * Math.abs(Math.sin(Math.PI * ph)) * Math.min(1, dist * 3);
        const sw = Math.sin(2 * Math.PI * ph) * 0.35;
        p.legs = [sw, -sw];
        p.tail.wag = Math.max(p.tail.wag, 0.5);
        const turnIn = smoothstep(0, Math.min(0.3, e.dur / 3), tIn) * (1 - smoothstep(e.dur - Math.min(0.3, e.dur / 3), e.dur, tIn));
        yaw += travelYaw * turnIn;
        continue;
      }
      if (style === 'hop') {
        const a0 = 0.18, a1 = 0.86;
        const k = clamp((u - a0) / (a1 - a0));
        pos = from.clone().lerp(to, sine(k));
        const H = (e.height ?? 0.9);
        p.air += H * 4 * k * (1 - k);
        const crouch = bump(u, 0, a0 + 0.04);
        p.sy *= 1 - 0.14 * crouch; p.sx *= 1 + 0.06 * crouch;
        const flight = k > 0 && k < 1 ? Math.sin(Math.PI * k) : 0;
        p.sy *= 1 + 0.06 * flight;
        p.earL[0] += 0.35 * flight; p.earR[0] += 0.35 * flight;
        p.legs = [0.5 * flight, 0.5 * flight];
        const land = u > a1 ? bump(u, a1, 1) : 0;
        p.sy *= 1 - 0.12 * land;
        yaw += travelYaw * 0.6 * bump(u, 0, 1);
        continue;
      }
      // fly：二次貝茲弧線，紙飛機機頭沿切線
      const ctrl = from.clone().lerp(to, 0.5);
      ctrl.y += (e.height ?? 0.6) * this.height;
      const k = sine(u);
      const q = (a: Vector3, b: Vector3, c: Vector3, s: number): Vector3 => a.clone().multiplyScalar((1 - s) * (1 - s)).add(b.clone().multiplyScalar(2 * (1 - s) * s)).add(c.clone().multiplyScalar(s * s));
      pos = q(from, ctrl, to, k);
      const tan = from.clone().multiplyScalar(-2 * (1 - k)).add(ctrl.clone().multiplyScalar(2 - 4 * k)).add(to.clone().multiplyScalar(2 * k));
      p.heading = Math.atan2(-tan.z, tan.x);
      p.pitch = Math.atan2(tan.y, Math.hypot(tan.x, tan.z));
      p.bank = 0.35 * Math.sin(Math.PI * u);
    }
    p.pos = [pos.x, pos.y, pos.z];
    p.yaw = yaw;

    // 眨眼：種子決定 3–6 秒一次＋事件＋換情緒（變形中不眨）
    const blinks: number[] = [];
    const br = seeded(seed * 97 + 13);
    for (let b = 1 + br() * 2.5; b < t + 1; b += 3 + br() * 3) blinks.push(b);
    for (const e of ev) { if (e.type === 'blink') blinks.push(e.t); if (e.type === 'emotion') blinks.push(e.t + 0.02); }
    if (!trans && p.eyes !== 'happy' && blinks.some((b) => t >= b && t < b + 0.11)) p.eyes = 'closed';

    // 說話
    for (const e of ev) {
      if (e.type !== 'say' || e.t > t) continue;
      const m = Zhezhe.mouthAt(e.lips, t - e.t);
      if (m >= 0) p.mouth = m;
    }
    if (p.mouth > 0) { p.head[0] -= 0.012 * p.mouth; p.earL[0] -= 0.03; p.earR[0] -= 0.03; }

    // 燈籠亮度、紙立起
    for (const e of ev) {
      if (e.type === 'glow' && e.t <= t) p.glow = lerp(p.glow, e.to, sine((t - e.t) / (e.dur ?? 1.5)));
      if (e.type === 'rise' && e.t <= t) p.rise = lerp(p.rise, e.to ?? 1, easeIO((t - e.t) / (e.dur ?? 1)));
    }
    return p;
  }

  // ─── 套用 ───
  update(tRaw: number, state: ZhezheState = {}): ZhezhePose {
    this.lastT = tRaw;
    const p = this.poseAt(tRaw);
    if (state.pos) p.pos = [...state.pos] as V3;
    if (state.yaw !== undefined) p.yaw = state.yaw;
    if (state.mouth !== undefined && state.mouth !== null) p.mouth = state.mouth;
    if (state.visible !== undefined) p.visible = state.visible;
    if (state.glow !== undefined) p.glow = state.glow;
    this.presenceU.value = clamp(state.presence ?? this.opts.presence ?? 0.06, 0, 0.4);
    this.formPresenceU.value = this.presenceU.value + FORM_PRESENCE_ADD;
    this.apply(p);
    return p;
  }

  private apply(p: ZhezhePose): void {
    this.group.visible = p.visible;
    this.group.position.set(p.pos[0], p.pos[1], p.pos[2]);
    this.group.rotation.set(0, p.yaw, 0);
    // 漂浮造型的輕微起伏（題卡靜止）
    const hover = p.form === 'plane' || p.form === 'lantern' ? 0.015 * Math.sin(2 * Math.PI * 0.45 * p.t) : 0;
    this.mover.position.set(0, p.air + hover, 0);
    this.mover.rotation.set(0, p.spin, p.wobble, 'YXZ');
    const s = p.scale;
    this.mover.scale.set(s * p.sx, s * p.sy, s * lerp(1, 0.1, p.press));
    for (const [k, h] of this.holders) {
      const on = k === p.form;
      h.visible = on;
      if (!on) continue;
      h.scale.setScalar(p.formScale);
      if (k === 'plane') {
        if (p.heading !== null) h.rotation.set(p.bank + 0.45, p.heading - p.yaw, p.pitch, 'YZX');
        else h.rotation.set(0.45 + 0.04 * Math.sin(2 * Math.PI * 0.4 * p.t), -0.35, 0, 'YZX');
      } else h.rotation.set(0, 0, 0);
      if (k === 'idle') this.cat.apply(p);
      else this.objs.get(k)!.setOpen(p.open, p.t);
    }
    this.lantern.setGlow(p.form === 'lantern' ? p.glow : 0);
    this.sheet.setRise(p.rise);
    if (this.shadow) {
      const [a, w, d] = FORM_SHADOW[p.form];
      const lift = clamp(p.air / 0.9);
      const k = (1 - lift) * a;
      (this.shadow.material as MeshBasicMaterial).opacity = k;
      this.shadow.visible = this.shadowEnabled && k > 0.01;
      this.shadow.scale.set(w * (1 - 0.35 * lift) * p.scale, d * (1 - 0.35 * lift) * p.scale, 1);
      this.shadow.position.set(0, 0.004, 0.02);
    }
  }

  // ─── 查詢 ───
  /** 最後一次 update 的時間（秒） */
  get lastPoseT(): number { return this.lastT; }
  /** 世界外框與目前狀態（量測用；需先 update） */
  probe(): { form: FoldForm; open: number; mouth: number; eyes: EyeShape; box: { min: V3; max: V3 } } {
    this.group.updateMatrixWorld(true);
    const min = new Vector3(Infinity, Infinity, Infinity), max = new Vector3(-Infinity, -Infinity, -Infinity);
    const v = new Vector3();
    this.mover.traverse((o) => {
      const m = o as Mesh;
      if (!m.isMesh || !m.visible || !isShown(m)) return;
      const pos = m.geometry.getAttribute('position') as BufferAttribute;
      for (let i = 0; i < pos.count; i += 1) { v.fromBufferAttribute(pos, i).applyMatrix4(m.matrixWorld); min.min(v); max.max(v); }
    });
    const p = this.poseAt(this.lastT);
    return { form: p.form, open: p.open, mouth: p.mouth, eyes: p.eyes, box: { min: [min.x, min.y, min.z], max: [max.x, max.y, max.z] } };
  }
  /** 題卡四角世界座標（左下、右下、右上、左上；form＝'card' 完全攤開時才準確） */
  cardCorners(): V3[] {
    this.group.updateMatrixWorld(true);
    return this.card.corners().map((c) => { const w = c.applyMatrix4(this.card.group.matrixWorld); return [w.x, w.y, w.z] as V3; });
  }
  /** 紙材的摺痕明度（測試用） */
  get paperMaterial(): MeshStandardMaterial { return this.mats[0] as MeshStandardMaterial; }
  dispose(): void {
    this.group.traverse((o) => { const m = o as Mesh; if (m.isMesh) m.geometry.dispose(); });
    for (const m of this.mats) m.dispose();
  }
}

function isShown(o: { visible: boolean; parent: unknown }): boolean {
  let c: { visible: boolean; parent: unknown } | null = o;
  while (c) { if (!c.visible) return false; c = c.parent as typeof c; }
  return true;
}

// ─────────────────────────────────────────── cue 時間軸 → 事件表（主線接線用） ───────────────────────────────────────────
/** 只用到的欄位（和 cues/timeline.ts 的 CueTimeline 相容，不直接匯入，避免和引擎改版綁死） */
export interface ZhezheTimelineLike {
  anims: { name: string; target?: string; start: number; duration: number; params: Record<string, unknown> }[];
  lines: { line: { id: string; lipsyncId?: string }; actorId: string | null; start: number }[];
}

/**
 * 把解析後的 cue 時間軸轉成折折的事件表。建議的動畫名稱（target＝折折的角色 id，預設 'zhezhe'）：
 *   zhezhe.fold {form, scale?, fumble?}（長度＝dur，預設 1.3）、zhezhe.emote {emotion}、zhezhe.blink、zhezhe.twitch {ear}、
 *   zhezhe.look {yaw}、zhezhe.walk|hop|fly|glide {to:[x,y,z] 或 dx/dy/dz, height?}、zhezhe.turn {yaw}、zhezhe.hush、
 *   zhezhe.glow {to}、zhezhe.rise {to?}、zhezhe.show {on}
 * 台詞：actorId＝折折的句子自動 say（對嘴資料用 lipsyncId ?? 台詞編號）。
 */
export function zhezheTrackFromTimeline(tl: ZhezheTimelineLike, start: ZhezheStart & { pos: V3 }, lipsync: (id: string) => LipsyncFrames | undefined = () => undefined, actorId = 'zhezhe'): ZhezheTrack {
  const events: ZhezheEvent[] = [];
  let cur: V3 = [...start.pos] as V3;
  const num = (v: unknown, d: number): number => (typeof v === 'number' && Number.isFinite(v) ? v : d);
  const anims = tl.anims.filter((a) => a.name.startsWith('zhezhe.') && (a.target === undefined || a.target === actorId)).sort((a, b) => a.start - b.start);
  for (const a of anims) {
    const p = a.params ?? {}, t = a.start, kind = a.name.slice('zhezhe.'.length);
    switch (kind) {
      case 'fold': if (typeof p.form === 'string' && (FOLD_FORMS as string[]).includes(p.form)) events.push({ type: 'fold', t, form: p.form as FoldForm, dur: a.duration > 0 ? a.duration : FOLD_BEATS.defaultDur, scale: typeof p.scale === 'number' ? p.scale : undefined, fumble: p.fumble === true }); break;
      case 'emote': if (typeof p.emotion === 'string' && (ZHEZHE_EMOTIONS as string[]).includes(p.emotion)) events.push({ type: 'emotion', t, emotion: p.emotion as ZhezheEmotion }); break;
      case 'blink': events.push({ type: 'blink', t }); break;
      case 'twitch': events.push({ type: 'twitch', t, ear: p.ear === 'l' || p.ear === 'r' ? p.ear : 'both' }); break;
      case 'look': events.push({ type: 'look', t, yaw: num(p.yaw, 0), dur: a.duration > 0 ? a.duration : 0.5 }); break;
      case 'turn': events.push({ type: 'turn', t, yaw: num(p.yaw, 0), dur: a.duration > 0 ? a.duration : 0.5 }); break;
      case 'walk': case 'hop': case 'fly': case 'glide': {
        const to: V3 = Array.isArray(p.to) && p.to.length === 3 ? (p.to as number[]).map(Number) as V3 : [cur[0] + num(p.dx, 0), cur[1] + num(p.dy, 0), cur[2] + num(p.dz, 0)];
        events.push({ type: 'move', t, dur: a.duration > 0 ? a.duration : kind === 'hop' ? 0.9 : 1.5, to, style: kind, height: typeof p.height === 'number' ? p.height : undefined });
        cur = to;
        break;
      }
      case 'hush': events.push({ type: 'hush', t, dur: a.duration > 0 ? a.duration : HUSH_BEATS.dur }); break;
      case 'glow': events.push({ type: 'glow', t, to: num(p.to, 1), dur: a.duration > 0 ? a.duration : 1.5 }); break;
      case 'rise': events.push({ type: 'rise', t, to: num(p.to, 1), dur: a.duration > 0 ? a.duration : 1 }); break;
      case 'show': events.push({ type: 'visible', t, on: p.on !== false }); break;
      default: break;
    }
  }
  for (const l of tl.lines) {
    if (l.actorId !== actorId) continue;
    const lips = lipsync(l.line.lipsyncId ?? l.line.id);
    if (lips) events.push({ type: 'say', t: l.start, lips });
  }
  return { start, events };
}

/** 依 cue id 產生穩定的種子（同一 cue 重播眨眼一致） */
export const zhezheSeed = (cueId: string): number => hashString(`zhezhe:${cueId}`);
