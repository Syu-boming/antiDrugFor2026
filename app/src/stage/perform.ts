// 紙偶表演：把 cue 的角色動畫（target＝角色 id）換算成姿勢、操偶線、臉部換片。
// 所有量都是「時間的純函式」；擺盪交給固定步長的 StringSim，每個 cue 開始（含重播、上一步、擷取跳轉）時重設。
//
// 角色動畫表（cue.animation 的 name；完整參數見 app/G4_INTERFACE.md）：
//   操偶線  strings.drop {anchors, stagger, each}   線一根根從上方落下、紙環扣上
//           strings.tension {anchors, to}           張力（0 鬆垂～1 繃緊）
//           strings.loosen {anchors, to}            變鬆：張力降到 to（預設 0）、拉力歸零
//           strings.fade {anchors, to}              變淡：不透明度降到 to（預設 0.35）
//           strings.detach {anchors, stagger}       脫落：紙環打開、線往上飄出畫面（不剪斷）
//   紙偶    puppet.popup                            隨立體書景片立起（以腳底為鉸鏈）
//           puppet.enter {from} / puppet.exit {to}  從畫面外走進來／走出去（dx，世界單位）
//           puppet.sit {to}                         坐姿程度（1 坐、0 站；0.5 半站）
//           puppet.waveTry                          想揮手：手抬起 → 線先繃緊 → 手被拉向旁邊
//           puppet.kneeTug {at}                     想站起：起身 → 膝前線繃緊 → 膝蓋被提起（腳離地）→ 晃一下 → 扶桌（at＝桌邊世界座標）
//           puppet.reach / puppet.wave / puppet.chest / puppet.grab {at}   B 側手：伸手、揮手、手放胸前、扶住某點
//           puppet.lean {to} / puppet.move {dx} / puppet.tilt {to}         傾身、移動、歪頭
//           puppet.pose {pose}                      立牌換姿勢（紙片翻面）
//           puppet.face {emotion}                   情緒換片（smile／neutral／confused／worried／surprised），轉折時加眨一次
//           puppet.blink                            加眨一次
import { Group, Vector2, Vector3, type Object3D } from 'three';
import type { CharacterStart } from '../types/cue';
import type { CueTimeline, ResolvedAnim } from '../cues/timeline';
import { Rig, type AnchorName } from './rig';
import { PaperString, StringSim } from './strings';
import type { StandeeActor } from './standee';
import type { EyeShape, FaceRig, MouthShape } from './face';
import { LAYER } from './layers';
import { clamp, ease, hashString, lerp, seeded, smoothstep } from '../util/math';

export const ANCHORS: AnchorName[] = ['wrist', 'elbow', 'knee'];
/** 操偶線上端的高度（遠高於任何鏡位的畫面上緣，線一定延伸出畫面） */
const STRING_TOP_Y = 15;
/** 線寬：中景約 9 px、近景 ≥ 8 px（1080p） */
export const STRING_WIDTH = 0.066;

export interface LipsyncData { fps: number; frames: number[] }

type V2 = [number, number];
type Rec<T> = Record<AnchorName, T>;
const rec = <T>(v: () => T): Rec<T> => ({ wrist: v(), elbow: v(), knee: v() });

export interface ActorPlacement { id: string; x: number; z: number; facing: 1 | -1 }

/** 分件紙偶（有操偶線錨點） */
export class RigPerformer {
  readonly kind = 'rig' as const;
  readonly strings = new Map<AnchorName, PaperString>();
  /** 頭部替換（head＝一般、head_worried＝困惑）各自的臉部換片；emotion 決定顯示哪一個 */
  heads = new Map<string, FaceRig>();
  activeFace: FaceRig | null = null;
  /** 正面視角的身體尺寸（世界單位） */
  readonly dims: { hipStand: number; seatHip: number; thigh: number; shin: number; ankleY: number };
  constructor(readonly place: ActorPlacement, readonly rig: Rig, readonly view: 'front' | 'side', public face: FaceRig | null, orderBase: number, opts: { seatHip?: number } = {}) {
    for (const a of ANCHORS) if (rig.spec.anchors[a]) this.strings.set(a, new PaperString(LAYER.strings.order + (orderBase % LAYER.actorStride)));
    const pel = rig.spec.parts.find((p) => p.id === (rig.spec.roles?.pelvis ?? 'pelvis'));
    const hipStand = pel ? pel.at[1] : 1.4;
    const L = rig.spec.limbs.legB ?? rig.spec.limbs.legA;
    const thigh = L ? Math.hypot(...rig.part(L.lower).spec.at) : 0.6;
    const shin = L ? Math.hypot(...rig.part(L.end).spec.at) : 0.5;
    const ankleY = hipStand - thigh - shin;
    this.dims = { hipStand, seatHip: opts.seatHip ?? ankleY + shin + 0.17, thigh, shin, ankleY };
  }
  get id(): string { return this.place.id; }
  get root(): Group { return this.rig.root; }
  addTo(parent: Object3D): void {
    parent.add(this.rig.root);
    this.strings.forEach((s) => { parent.add(s.mesh); parent.add(s.ring); });
  }
}

/** 整張圖立牌 */
export class StandeePerformer {
  readonly kind = 'standee' as const;
  constructor(readonly place: ActorPlacement, readonly actor: StandeeActor) {}
  get id(): string { return this.place.id; }
  get root(): Group { return this.actor.root; }
  get face(): FaceRig | null { return this.actor.face; }
  addTo(parent: Object3D): void { parent.add(this.actor.root); }
}

export type Performer = RigPerformer | StandeePerformer;

export interface Intent {
  visible: boolean; x: number; y: number; z: number; facing: 1 | -1;
  dx: number; lift: number; lean: number; popup: number; walk: number;
  sit: number; armRaise: number; reachB: number; waveB: number; chestB: number; grabB: number; grabAt: V2 | null; step: number;
  headTilt: number;
  drop: Rec<number>; landAt: Rec<number>; tension: Rec<number>; fade: Rec<number>; detach: Rec<number>;
  pull: Rec<V2>; swing: Rec<number>; bodyPush: V2;
  pose: string; flip: number; emotion: string; events: number[];
}

/** 正面紙偶（圖片分件）的拉力量：手腕被拉到 A 側（畫面左）、略往上；膝蓋往上提 */
const FRONT = {
  raised: [-0.3, 0.72] as V2,
  pullWrist: [-0.58, -0.46] as V2,
  pullElbow: [-0.16, 0.06] as V2,
  pullKnee: [0.05, 0.3] as V2,
  chest: [-0.3, -0.24] as V2,
};
const SIDE = { pullWrist: [-0.85, 0.25] as V2, pullElbow: [-0.3, 0.12] as V2, pullKnee: [0.22, 0.32] as V2 };

function applyPosePreset(it: Intent, pose: string | undefined, view: 'front' | 'side'): void {
  if (!pose) return;
  const P = view === 'front' ? FRONT : SIDE;
  if (pose === 'sit') { it.sit = 1; }
  if (pose === 'pulled' || pose === 'pulled_sit' || pose === 'pulled_half') {
    it.armRaise = view === 'front' ? 1 : 0.55;
    it.pull.wrist = [...P.pullWrist]; it.pull.elbow = [...P.pullElbow];
    it.tension.wrist = 1; it.tension.elbow = 1; it.tension.knee = 0.8;
    if (pose === 'pulled_sit') it.sit = 1;
    if (pose === 'pulled_half') {
      it.sit = 0.55; it.pull.knee = [P.pullKnee[0] * 0.75, P.pullKnee[1] * 0.75]; it.tension.knee = 1;
      it.grabB = 1; it.emotion = 'confused'; it.headTilt = 0.07;
    } else if (view === 'side') {
      it.pull.knee = [0.08, 0.1];
    }
  }
}

function prog(a: ResolvedAnim, t: number, from = 0, to = 1): number {
  const u = (t - a.start) / Math.max(1e-6, a.duration);
  return clamp((u - from) / (to - from));
}

const anchorList = (a: ResolvedAnim): AnchorName[] => ((Array.isArray(a.params.anchors) ? a.params.anchors : ANCHORS) as AnchorName[]).filter((n) => ANCHORS.includes(n));

/** 落下：前 85% 加速落下，最後彈一下（紙繩的重量） */
function dropEase(u: number): number {
  if (u <= 0) return 0;
  if (u >= 1) return 1;
  if (u < 0.82) { const k = u / 0.82; return k * k * (3 - 2 * k) * 1.02; }
  const k = (u - 0.82) / 0.18;
  return 1.02 - 0.02 * k;
}

/** 角色在時間 t 的「意圖」（還沒加上擺盪模擬） */
export function evalIntent(place: ActorPlacement, view: 'front' | 'side', start: CharacterStart | undefined, anims: ResolvedAnim[], t: number, defaultPose = ''): Intent {
  const it: Intent = {
    visible: start ? start.visible !== false : false,
    x: start?.x ?? place.x, y: start?.y ?? 0, z: start?.z ?? place.z, facing: start?.facing ?? place.facing,
    dx: 0, lift: 0, lean: 0, popup: start?.popup ?? 1, walk: 0,
    sit: start?.sit ?? 0, armRaise: 0, reachB: 0, waveB: 0, chestB: 0, grabB: 0, grabAt: null, step: 0, headTilt: 0,
    drop: rec(() => 0), landAt: rec(() => -99), tension: rec(() => start?.stringTension ?? 0.3), fade: rec(() => 1), detach: rec(() => 0),
    pull: rec<V2>(() => [0, 0]), swing: rec(() => 0), bodyPush: [0, 0],
    pose: defaultPose, flip: 0, emotion: start?.emotion ?? 'smile', events: [],
  };
  for (const a of start?.strings ?? []) if (a in it.drop) it.drop[a as AnchorName] = 1;
  applyPosePreset(it, start?.pose, view);
  if (start?.pose && !['sit', 'pulled', 'pulled_sit', 'pulled_half', 'stand'].includes(start.pose)) it.pose = start.pose;
  if (start?.sit !== undefined) it.sit = start.sit;
  if (start?.emotion) it.emotion = start.emotion;
  if (start?.hand === 'chest') it.chestB = 1;
  if (start?.hand === 'grab') it.grabB = 1;
  const P = view === 'front' ? FRONT : SIDE;
  const mine = anims.filter((a) => a.target === place.id);
  if (mine.some((a) => a.name === 'puppet.popup') && start?.popup === undefined) it.popup = 0;

  for (const a of mine) {
    switch (a.name) {
      case 'strings.drop': {
        const list = anchorList(a);
        const stagger = Number(a.params.stagger ?? 0.9);
        const each = Number(a.params.each ?? Math.max(0.5, a.duration - stagger * (list.length - 1)));
        list.forEach((name, i) => {
          const s0 = a.start + i * stagger;
          const u = (t - s0) / each;
          it.landAt[name] = s0 + each * 0.82;
          if (u <= 0 && it.drop[name] < 1) { it.drop[name] = 0; return; }
          it.drop[name] = Math.max(it.drop[name] >= 1 ? 1 : 0, dropEase(u));
          it.tension[name] = u < 1 ? 0.08 : 0.2; // 剛落下時是鬆的
          // 落下時紙繩左右晃，扣上後由模擬擺盪幾下停住
          it.swing[name] = u > 0.3 && u < 0.85 ? 0.14 * (i % 2 ? -1 : 1) : 0;
        });
        break;
      }
      case 'strings.tension': {
        const p = ease(a.ease, prog(a, t));
        for (const n of anchorList(a)) it.tension[n] = lerp(it.tension[n], Number(a.params.to ?? 1), p);
        break;
      }
      case 'strings.loosen': {
        const p = ease(a.ease ?? 'inOut', prog(a, t));
        const list = anchorList(a);
        for (const n of list) {
          it.tension[n] = lerp(it.tension[n], Number(a.params.to ?? 0), p);
          it.pull[n] = [lerp(it.pull[n][0], 0, p), lerp(it.pull[n][1], 0, p)];
        }
        // 線鬆了，被拉起的手臂也慢慢放下（不再被拉著）
        if (list.includes('wrist')) it.armRaise = lerp(it.armRaise, 0, p);
        break;
      }
      case 'strings.fade': {
        const p = ease(a.ease ?? 'inOut', prog(a, t));
        for (const n of anchorList(a)) it.fade[n] = lerp(it.fade[n], Number(a.params.to ?? 0.35), p);
        break;
      }
      case 'strings.detach': {
        const list = anchorList(a);
        const stagger = Number(a.params.stagger ?? 0.6);
        const each = Math.max(0.6, a.duration - stagger * (list.length - 1));
        list.forEach((n, i) => {
          const u = clamp((t - a.start - i * stagger) / each);
          it.detach[n] = Math.max(it.detach[n], ease('inOut', u));
          if (u > 0) { it.tension[n] = Math.min(it.tension[n], 0.1); it.pull[n] = [it.pull[n][0] * (1 - u), it.pull[n][1] * (1 - u)]; }
        });
        break;
      }
      case 'puppet.popup': {
        const u = prog(a, t);
        // 紙片立起：略過頭再回正（像有彈性的厚卡紙）
        it.popup = u <= 0 ? 0 : u >= 1 ? 1 : Math.min(1.04, ease('out', u) * 1.04) - Math.max(0, (u - 0.75) / 0.25) * 0.04;
        break;
      }
      case 'puppet.enter': case 'puppet.exit': {
        const p = ease(a.ease ?? 'inOut', prog(a, t));
        const off = Number(a.params.from ?? a.params.to ?? (a.name === 'puppet.enter' ? -6 : 6));
        it.dx += a.name === 'puppet.enter' ? off * (1 - p) : off * p;
        if (p > 0 && p < 1) it.walk = 1;
        break;
      }
      case 'puppet.sit': it.sit = lerp(it.sit, Number(a.params.to ?? 1), ease(a.ease ?? 'inOut', prog(a, t))); break;
      case 'puppet.waveTry': {
        // 0–30% 手抬起（意圖）；30–42% 線繃緊（先繃緊）；42–67% 手被拉向一旁（再拉動）
        const u = (t - a.start) / a.duration;
        it.armRaise = Math.max(it.armRaise, ease('inOut', prog(a, t, 0, 0.3)));
        it.tension.wrist = Math.max(it.tension.wrist, lerp(0.2, 1, smoothstep(0.3, 0.42, u)));
        it.tension.elbow = Math.max(it.tension.elbow, lerp(0.2, 1, smoothstep(0.33, 0.45, u)));
        const pull = ease('inOut', prog(a, t, 0.42, 0.67));
        it.pull.wrist = [lerp(it.pull.wrist[0], P.pullWrist[0], pull), lerp(it.pull.wrist[1], P.pullWrist[1], pull)];
        it.pull.elbow = [lerp(it.pull.elbow[0], P.pullElbow[0], pull), lerp(it.pull.elbow[1], P.pullElbow[1], pull)];
        if (view === 'front') it.chestB = Math.max(it.chestB, ease('inOut', prog(a, t, 0.55, 0.85)));
        if (u >= 0.5) { it.emotion = String(a.params.emotion ?? 'confused'); it.events.push(a.start + a.duration * 0.5); }
        if (view === 'front') it.headTilt = Math.max(it.headTilt, 0.07 * ease('inOut', prog(a, t, 0.5, 0.8)));
        break;
      }
      case 'puppet.kneeTug': {
        // 想站起（意圖）→ 膝前線繃緊 → 膝蓋被往上提、腳離地 → 身體晃一下 → B 側手扶住桌邊
        const u = (t - a.start) / a.duration;
        if (view === 'front') {
          it.sit = lerp(it.sit, Math.max(0, it.sit - 0.45), ease('inOut', prog(a, t, 0, 0.32)));
          it.tension.knee = Math.max(it.tension.knee, lerp(0.2, 1, smoothstep(0.22, 0.34, u)));
          const tug = ease('inOut', prog(a, t, 0.36, 0.5)) - 0.25 * ease('inOut', prog(a, t, 0.62, 0.9));
          it.pull.knee = [lerp(it.pull.knee[0], P.pullKnee[0], tug), lerp(it.pull.knee[1], P.pullKnee[1], tug)];
          const push = ease('inOut', prog(a, t, 0.36, 0.46)) * (1 - ease('inOut', prog(a, t, 0.48, 0.66)));
          it.bodyPush = [it.bodyPush[0] + 0.14 * push, it.bodyPush[1] + 0.05 * push];
          const g = ease('inOut', prog(a, t, 0.44, 0.66));
          if (g > 0) { it.grabB = Math.max(it.grabB, g); it.chestB *= 1 - g; }
          if (Array.isArray(a.params.at)) it.grabAt = [Number(a.params.at[0]), Number(a.params.at[1])];
        } else {
          it.step = Math.max(it.step, ease('inOut', prog(a, t, 0, 0.3)) * (1 - ease('inOut', prog(a, t, 0.38, 0.55))));
          it.tension.knee = Math.max(it.tension.knee, lerp(0.25, 1, smoothstep(0.24, 0.36, u)));
          const tug = ease('inOut', prog(a, t, 0.38, 0.5)) - 0.6 * ease('inOut', prog(a, t, 0.6, 0.85));
          it.pull.knee = [lerp(it.pull.knee[0], P.pullKnee[0], tug), lerp(it.pull.knee[1], P.pullKnee[1], tug)];
          const push = ease('inOut', prog(a, t, 0.38, 0.46)) * (1 - ease('inOut', prog(a, t, 0.46, 0.6)));
          it.bodyPush = [it.bodyPush[0] - 0.35 * push, it.bodyPush[1]];
          it.grabB = Math.max(it.grabB, ease('inOut', prog(a, t, 0.5, 0.72)));
        }
        break;
      }
      case 'puppet.reach': it.reachB = Math.max(it.reachB, ease(a.ease, prog(a, t))); break;
      case 'puppet.wave': it.waveB = Math.max(it.waveB, ease('inOut', prog(a, t, 0, 0.2)) * (1 - ease('inOut', prog(a, t, 0.85, 1)))); break;
      case 'puppet.chest': it.chestB = lerp(it.chestB, Number(a.params.to ?? 1), ease(a.ease ?? 'inOut', prog(a, t))); break;
      case 'puppet.grab': {
        it.grabB = lerp(it.grabB, Number(a.params.to ?? 1), ease(a.ease ?? 'inOut', prog(a, t)));
        if (Array.isArray(a.params.at)) it.grabAt = [Number(a.params.at[0]), Number(a.params.at[1])];
        break;
      }
      case 'puppet.lean': it.lean = lerp(it.lean, Number(a.params.to ?? 0.1), ease(a.ease, prog(a, t))); break;
      case 'puppet.move': it.dx += Number(a.params.dx ?? 0) * ease(a.ease, prog(a, t)); break;
      case 'puppet.tilt': {
        if (t >= a.start) it.events.push(a.start);
        it.headTilt = lerp(it.headTilt, Number(a.params.to ?? 0.08), ease(a.ease ?? 'inOut', prog(a, t)));
        break;
      }
      case 'puppet.pose': {
        const half = a.start + a.duration / 2;
        if (t >= half) it.pose = String(a.params.pose ?? it.pose);
        const u = prog(a, t);
        if (u > 0 && u < 1) it.flip = u;
        it.events.push(half);
        break;
      }
      case 'puppet.face': if (t >= a.start) { it.emotion = String(a.params.emotion ?? it.emotion); } it.events.push(a.start); break;
      case 'puppet.blink': it.events.push(a.start); break;
      default: break;
    }
  }
  if (it.popup < 0.02) it.visible = false;
  return it;
}

const v2 = new Vector2();
const w3 = new Vector3();
const top3 = new Vector3();
const bot3 = new Vector3();

/** 眨眼時間表：3–6 秒隨機（以角色與 cue 為種子，重播一致）＋轉頭／情緒轉折時加眨 */
function blinkTimes(actorId: string, cueId: string, duration: number, events: number[]): number[] {
  const r = seeded(hashString(`${actorId}|${cueId}|blink`));
  const out: number[] = [];
  let t = 0.6 + r() * 2.2;
  while (t < duration + 2) { out.push(t); t += 3 + r() * 3; }
  for (const e of events) out.push(e + 0.06);
  return out.sort((a, b) => a - b);
}

function eyeAt(times: number[], t: number): EyeShape {
  for (const b of times) {
    if (t < b) break;
    const d = t - b;
    if (d < 0.05) return 'half';
    if (d < 0.12) return 'closed';
    if (d < 0.17) return 'half';
  }
  return 'open';
}

const LIP_SHAPES: MouthShape[] = ['closed', 'half', 'open', 'round'];

export class PuppetDirector {
  readonly sim = new StringSim();
  private key = '';
  private blinkCache = new Map<string, number[]>();
  /** 舞台燈總量（紙繩亮度跟著走） */
  light = 1;

  constructor(public actors: Map<string, Performer>, private lipsync: (id: string) => LipsyncData | undefined = () => undefined) {}

  /** 新 cue／重播／上一步時重設模擬 */
  reset(): void { this.key = ''; }

  setActors(actors: Map<string, Performer>): void { this.actors = actors; this.key = ''; this.blinkCache.clear(); }

  private intents(tl: CueTimeline, time: number): Map<string, Intent> {
    const chars = tl.cue.initialState.characters ?? {};
    const m = new Map<string, Intent>();
    this.actors.forEach((a, id) => {
      const view = a.kind === 'rig' ? a.view : 'front';
      const def = a.kind === 'standee' ? a.actor.cfg.defaultPose : '';
      m.set(id, evalIntent(a.place, view, chars[id], tl.anims, time, def));
    });
    return m;
  }

  apply(tl: CueTimeline, t: number, playKey: string): void {
    const drive = (time: number): Map<string, { px: number; py: number; k?: number; c?: number }> => {
      const out = new Map<string, { px: number; py: number; k?: number; c?: number }>();
      this.intents(tl, time).forEach((it, id) => {
        for (const n of ANCHORS) {
          out.set(`${id}:${n}`, { px: it.pull[n][0], py: it.pull[n][1], k: 40 + 50 * it.tension[n] });
          out.set(`${id}:sw:${n}`, { px: it.swing[n], py: 0, k: 30, c: 2.6 });
        }
        out.set(`${id}:body`, { px: it.bodyPush[0], py: it.bodyPush[1] });
      });
      return out;
    };
    const key = `${tl.cue.id}#${playKey}`;
    if (key !== this.key) { this.key = key; this.sim.reset(drive(0)); }
    this.sim.advanceTo(t, drive, drive(0));
    const intents = this.intents(tl, t);
    // 說話者位置（聆聽反應用）
    this.actors.forEach((actor, id) => {
      const it = intents.get(id)!;
      if (actor.kind === 'rig') {
        if (actor.view === 'front') this.poseFront(actor, it, tl, t); else this.poseSide(actor, it, tl, t);
      } else this.poseStandee(actor, it, tl, t, intents);
    });
  }

  // ------------------------------------------------------------------ 臉

  private faceAt(actorId: string, it: Intent, tl: CueTimeline, t: number, painted: MouthShape): { eyes: EyeShape; mouth: MouthShape; speaking: boolean } {
    const ck = `${tl.cue.id}|${actorId}|${it.events.join(',')}`;
    let times = this.blinkCache.get(ck);
    if (!times) { times = blinkTimes(actorId, tl.cue.id, tl.duration, it.events); this.blinkCache.set(ck, times); }
    const eyes = eyeAt(times, t);
    const sp = this.mouthOpen(actorId, tl, t);
    if (sp) return { eyes, mouth: sp, speaking: true };
    const emo = it.emotion;
    const mouth: MouthShape = emo === 'smile' ? (painted === 'smile' ? 'smile' : painted) : emo === 'confused' || emo === 'worried' ? (painted === 'open' ? 'open' : 'worried')
      : emo === 'surprised' ? (painted === 'round' || painted === 'open' ? painted : 'round') : 'closed';
    return { eyes, mouth, speaking: false };
  }

  /** 嘴型：有對嘴資料就照資料（每秒 12 格，0 閉、1 半開、2 大開、3 圓唇），沒有就依字幕時間產生佔位開合 */
  mouthOpen(actorId: string, tl: CueTimeline, t: number): MouthShape | null {
    for (const l of tl.lines) {
      if (l.actorId !== actorId || t < l.start || t >= l.end) continue;
      const lip = this.lipsync(l.line.lipsyncId ?? l.line.id);
      const local = t - l.start;
      if (lip) {
        const v = lip.frames[Math.min(lip.frames.length - 1, Math.floor(local * lip.fps))] ?? 0;
        return LIP_SHAPES[v] ?? 'closed';
      }
      const q = Math.floor(local * 12) / 12;
      const h = hashString(`${l.line.id}:${Math.floor(q * 5)}`);
      const syl = Math.abs(Math.sin(q * Math.PI * 5));
      if (syl < 0.3) return 'closed';
      if (syl < 0.7) return 'half';
      return h % 7 === 0 ? 'round' : h % 3 === 0 ? 'half' : 'open';
    }
    return null;
  }

  // ------------------------------------------------------------------ 立牌

  private poseStandee(p: StandeePerformer, it: Intent, tl: CueTimeline, t: number, all: Map<string, Intent>): void {
    const a = p.actor;
    a.root.visible = it.visible;
    if (!it.visible) return;
    a.setPose(it.pose || a.cfg.defaultPose);
    const phase = (hashString(p.id) % 1000) / 1000;
    a.root.position.set(it.x + it.dx, it.y + it.lift + (it.walk ? Math.abs(Math.sin(t * Math.PI * 3.2)) * 0.035 : 0), it.z);
    a.root.rotation.set(-(1 - Math.min(1, it.popup)) * Math.PI / 2 + Math.max(0, it.popup - 1) * 0.5, 0, 0);
    // 聆聽：別人說話時微微傾向說話者
    let listen = 0;
    for (const l of tl.lines) {
      if (!l.actorId || l.actorId === p.id) continue;
      const w = smoothstep(l.start - 0.1, l.start + 0.35, t) * (1 - smoothstep(l.end + 0.2, l.end + 0.8, t));
      if (w <= 0) continue;
      const other = all.get(l.actorId);
      const dir = other ? Math.sign((other.x + other.dx) - (it.x + it.dx)) : 0;
      listen = Math.max(-1, Math.min(1, listen + dir * w));
    }
    const breath = Math.sin((t / 3.6 + phase) * Math.PI * 2);
    const flip = it.flip > 0 ? Math.max(0.06, Math.abs(Math.cos(Math.PI * it.flip))) : 1;
    a.body.scale.set(flip * it.facing * (1 - 0.003 * breath), 1 + 0.007 * breath, 1);
    const head = a.head;
    if (head) {
      // 有頭層：聆聽時頭微微轉向說話者（±2.5° 內）、句首輕輕點一下頭；身體只做很小的擺動
      let nod = 0;
      for (const l of tl.lines) {
        if (!l.actorId || l.actorId === p.id) continue;
        const u = (t - l.start - 0.15) / 0.5;
        if (u > 0 && u < 1) nod = Math.max(nod, Math.sin(Math.PI * u));
      }
      head.rotation.z = clamp(-listen * 0.03 + it.headTilt + 0.006 * Math.sin((t / 4.2 + phase) * Math.PI * 2) - nod * 0.012, -0.044, 0.044);
      head.position.y = (head.userData.y0 ??= head.position.y) - nod * 0.01;
      a.body.rotation.z = 0.004 * Math.sin((t / 5.3 + phase) * Math.PI * 2) - listen * 0.01 - it.lean;
    } else {
      a.body.rotation.z = 0.005 * Math.sin((t / 5.3 + phase) * Math.PI * 2) - listen * 0.025 - it.lean;
    }
    const face = a.face;
    if (face) {
      const f = this.faceAt(p.id, it, tl, t, face.painted);
      face.set(f.eyes, f.mouth);
    }
  }

  // ------------------------------------------------------------------ 正面分件紙偶（圖片分件）

  private poseFront(actor: RigPerformer, it: Intent, tl: CueTimeline, t: number): void {
    const rig = actor.rig;
    const id = actor.id;
    const D = actor.dims;
    rig.root.visible = it.visible;
    if (!it.visible) { actor.strings.forEach((s) => s.hide()); return; }
    rig.resetPose();
    const body = this.sim.get(`${id}:body`);
    const phase = (hashString(id) % 1000) / 1000;
    const breath = Math.sin((t / 3.8 + phase) * Math.PI * 2);
    rig.root.scale.x = it.facing;
    rig.root.position.set(it.x + it.dx, it.y + it.lift, it.z);
    rig.root.rotation.set(-(1 - Math.min(1, it.popup)) * Math.PI / 2 + Math.max(0, it.popup - 1) * 0.5, 0, 0);

    // 骨盆高度：站 hipStand、坐 seatHip；身體被拉時晃一下
    const pel = rig.role('pelvis');
    const hipY = lerp(D.hipStand, D.seatHip, clamp(it.sit)) + body.oy * 0.6;
    if (pel) {
      const pp = rig.part(pel);
      pp.pivot.position.set(pp.spec.at[0] + body.ox * 0.5, hipY, 0);
      rig.setRot(pel, -body.ox * 0.12);
    }
    const torso = rig.role('torso');
    if (torso) rig.setRot(torso, 0.006 * breath - it.lean - body.ox * 0.1);
    const head = rig.role('head');
    if (head) rig.setRot(head, 0.012 * Math.sin((t / 4.6 + phase) * Math.PI * 2) + it.headTilt + body.ox * 0.15);
    rig.root.updateMatrixWorld(true);

    // A 側手臂（操偶線那隻）：意圖位置＋線的拉力位移（模擬）
    const LA = rig.spec.limbs.armA;
    if (LA) {
      const sA = rig.localPoint(LA.upper);
      const [l1, l2] = rig.limbLengths('armA');
      const restOff = rig.localPoint(LA.end).sub(sA); // 靜止姿勢的手腕相對肩膀
      const rest: V2 = [restOff.x, restOff.y];
      const wr = this.sim.get(`${id}:wrist`), el = this.sim.get(`${id}:elbow`);
      const aw = it.drop.wrist >= 0.999 ? 1 : 0, ae = it.drop.elbow >= 0.999 ? 1 : 0;
      // 抬手（意圖）：手腕沿身體外側的弧線抬起（角度與距離內插），不從肩膀前面、臉前穿過；
      // 抬起後手肘改朝外下方（solveLimbBlend），手肘與兩條線都離開頭頸（G4 整合：原本手肘會停在耳朵旁）。
      const R = FRONT.raised;
      const ra = Math.atan2(rest[1], rest[0]), rd = Math.hypot(rest[0], rest[1]);
      let qa = Math.atan2(R[1], R[0]);
      const qd = Math.hypot(R[0], R[1]);
      if (R[0] < 0) { while (qa > ra) qa -= Math.PI * 2; } else { while (qa < ra) qa += Math.PI * 2; }
      const ang = lerp(ra, qa, it.armRaise), dist = lerp(rd, qd, it.armRaise);
      const tx = Math.cos(ang) * dist + wr.ox * aw + el.ox * 0.4 * ae;
      const ty = Math.sin(ang) * dist + wr.oy * aw + el.oy * 0.4 * ae;
      const d = Math.hypot(tx, ty), maxR = (l1 + l2) * 0.995;
      const k = d > maxR ? maxR / d : 1;
      v2.set(sA.x + tx * k, sA.y + ty * k);
      rig.solveLimbBlend('armA', v2, smoothstep(0.3, 0.85, it.armRaise));
    }

    // B 側手臂：放膝上（靜止）、手放胸前（擔心）、扶桌邊
    const LB = rig.spec.limbs.armB;
    if (LB) {
      const sB = rig.localPoint(LB.upper);
      const restOff = rig.localPoint(LB.end).sub(sB);
      let tx = restOff.x, ty = restOff.y;
      tx = lerp(tx, FRONT.chest[0], it.chestB); ty = lerp(ty, FRONT.chest[1], it.chestB);
      if (it.grabB > 0) {
        // 扶桌：目標是世界座標的桌邊（預設在骨盆旁邊）
        let gx = 0.78, gy = 1.4;
        if (it.grabAt) { gx = (it.grabAt[0] - rig.root.position.x) * it.facing; gy = it.grabAt[1] - rig.root.position.y; }
        tx = lerp(tx, gx - sB.x, it.grabB); ty = lerp(ty, gy - sB.y + 0.12, it.grabB);
      }
      tx = lerp(tx, 0.62, it.reachB); ty = lerp(ty, 0.1, it.reachB);
      const [l1, l2] = rig.limbLengths('armB');
      const d = Math.hypot(tx, ty), maxR = (l1 + l2) * 0.995;
      const k = d > maxR ? maxR / d : 1;
      v2.set(sB.x + tx * k, sB.y + ty * k);
      rig.solveLimb('armB', v2);
      const hB = rig.role('handB');
      if (hB) {
        // 扶桌時手指朝下壓在桌面；放胸前時手掌斜貼胸口
        const world = rig.chainRot(hB);
        const target = 0.9 * it.chestB * (1 - it.grabB);
        rig.setRot(hB, lerp(0, target - world, Math.max(it.grabB, it.chestB)));
      }
    }

    // 腿（正面視角）：小腿保持近乎垂直，大腿以透視縮短連接骨盆與膝蓋（坐姿＝大腿朝向鏡頭）
    for (const limb of ['legA', 'legB'] as const) {
      const L = rig.spec.limbs[limb];
      if (!L) continue;
      const shin = rig.part(L.lower), end = rig.part(L.end);
      const hip = rig.localPoint(L.upper);
      const pelvisX = pel ? rig.part(pel).pivot.position.x : 0;
      const side = Math.sign(hip.x - pelvisX) || (limb === 'legA' ? 1 : -1);
      // 坐著時兩膝分開；扣膝前線的那條腿張得更開，讓膝前線走身體外側（DECISIONS D-G2-04）
      const splay = side * (limb === 'legA' ? 0.06 + 0.25 * clamp(it.sit) : 0.02 + 0.13 * clamp(it.sit));
      const ankle: V2 = [hip.x + splay + end.spec.at[0], D.ankleY];
      let knee: V2 = [ankle[0] + side * 0.02 * it.sit, ankle[1] + D.shin];
      if (limb === 'legA') {
        const kn = this.sim.get(`${id}:knee`);
        const att = it.drop.knee >= 0.999 ? 1 : 0;
        knee = [knee[0] + kn.ox * att, knee[1] + Math.max(0, kn.oy) * att];
        ankle[0] = knee[0] - kn.ox * 0.4 * att; ankle[1] = knee[1] - D.shin;
      }
      // 大腿向量（骨盆 → 膝蓋）
      let vx = knee[0] - hip.x, vy = knee[1] - hip.y;
      let len = Math.hypot(vx, vy);
      if (len > D.thigh) { vx *= D.thigh / len; vy *= D.thigh / len; len = D.thigh; knee = [hip.x + vx, hip.y + vy]; }
      const restT = Math.atan2(shin.spec.at[1], shin.spec.at[0]);
      rig.setLength(L.upper, clamp(len / D.thigh, 0.12, 1));
      rig.setRot(L.upper, Math.atan2(vy, vx) - restT - rig.chainRot(L.upper));
      // 小腿：從膝蓋指向腳踝
      const restS = Math.atan2(end.spec.at[1], end.spec.at[0]);
      const sx = ankle[0] - knee[0], sy = ankle[1] - knee[1];
      rig.setRot(L.lower, Math.atan2(sy, sx) - restS - rig.chainRot(L.lower));
    }

    // 頭部替換：笑＝一般頭；其他情緒＝困惑頭（若有）。硬切，轉折時加眨一次（events）
    let face = actor.face;
    if (actor.heads.size > 1) {
      const worried = it.emotion !== 'smile' && actor.heads.has('head_worried');
      const show = worried ? 'head_worried' : 'head';
      for (const [pid, f] of actor.heads) {
        const part = rig.part(pid);
        const on = pid === show;
        if (part.mesh) part.mesh.visible = on;
        f.setVisible(on);
      }
      face = actor.heads.get(show) ?? face;
    }
    actor.activeFace = face;
    if (face) {
      const f = this.faceAt(id, it, tl, t, face.painted);
      face.set(f.eyes, f.mouth);
    }
    rig.root.updateMatrixWorld(true);
    this.poseStrings(actor, it, t, 'front');
  }

  // ------------------------------------------------------------------ 操偶線

  private poseStrings(actor: RigPerformer, it: Intent, t: number, view: 'front' | 'side'): void {
    const rig = actor.rig;
    const id = actor.id;
    const f = it.facing;
    for (const n of ANCHORS) {
      const s = actor.strings.get(n);
      if (!s) continue;
      const drop = Math.min(1, it.drop[n]);
      if (drop <= 0.001 || it.fade[n] <= 0.002) { s.hide(); continue; }
      const anchor = rig.anchorWorld(n, w3);
      if (!anchor) { s.hide(); continue; }
      // 線的上端：手腕、手肘往 A 側（畫面左、危險方位）上方；膝前線往外側上方，走身體外側、避開頭頸
      const lean = view === 'front' ? (n === 'knee' ? 2.8 : n === 'wrist' ? -0.7 : -0.55) : (n === 'knee' ? 2.6 : -0.25);
      const pullX = it.pull[n][0] * f * (view === 'front' ? 1.1 : 2.2);
      // 深度：手腕、手肘線在所有部件前面；膝前線在軀幹、大腿前面，但在 B 側前臂與手後面
      //（B 側手扶桌時，手臂從線前面經過，不會看起來像多扣了一處）
      const zFront = it.z + (view === 'front' && n === 'knee' ? 0.085 : 0.24);
      top3.set(anchor.x + (pullX + lean) * f, STRING_TOP_Y, zFront);
      const det = it.detach[n];
      // 脫落：下端沿線往上飄出畫面（紙環先打開）
      const by = lerp(STRING_TOP_Y, anchor.y, drop);
      bot3.set(lerp(anchor.x, top3.x, det * 0.25) + det * 0.6 * f, lerp(by, STRING_TOP_Y + 1, ease('in', det)), zFront);
      const sw = this.sim.get(`${id}:sw:${n}`).ox;
      const bow = ((1 - it.tension[n]) * 0.26 * drop + sw + det * 0.5) * (n === 'knee' ? 1 : -1) * f;
      const landed = drop >= 0.999 && det < 0.15 ? clamp((t - it.landAt[n]) / 0.12) : 0;
      const ringA = rig.anchorAngle(n);
      const aw = rig.spec.anchors[n]?.width ?? 0.18;
      s.update({ top: top3, bottom: bot3, bow, width: STRING_WIDTH, opacity: it.fade[n], ring: det > 0 ? Math.max(0, 1 - det * 6) : landed, ringAngle: ringA, ringWidth: aw, light: this.light });
    }
  }

  // ------------------------------------------------------------------ 側面佔位紙偶（技術骨架示範用）

  private poseSide(actor: RigPerformer, it: Intent, tl: CueTimeline, t: number): void {
    const rig = actor.rig;
    const id = actor.id;
    rig.root.visible = it.visible;
    if (!it.visible) { actor.strings.forEach((s) => s.hide()); return; }
    rig.resetPose();
    const body = this.sim.get(`${id}:body`);
    const f = it.facing;
    rig.root.scale.x = f;
    rig.root.position.set(it.x + (it.dx + body.ox * 0.35) * f, it.y + it.lift + it.step * 0.04, it.z);
    rig.root.rotation.set(-(1 - Math.min(1, it.popup)) * Math.PI / 2, 0, -(it.lean + body.ox * 0.18 + it.step * 0.04) * f);
    const phase = (hashString(id) % 1000) / 1000;
    if (rig.has('torso')) rig.setRot('torso', 0.012 * Math.sin((t / 3.6 + phase) * Math.PI * 2));
    if (rig.has('head')) rig.setRot('head', 0.02 * Math.sin((t / 4.4 + phase) * Math.PI * 2) - it.pull.wrist[0] * 0.04);
    rig.root.updateMatrixWorld(true);
    const L = rig.spec.limbs;
    const len = (limb: string): number => { const l = L[limb]; return Math.hypot(...rig.part(l.lower).spec.at) + Math.hypot(...rig.part(l.end).spec.at); };

    const sA = rig.localPoint('upperArmA');
    const reachA = len('armA');
    const rest: V2 = [sA.x - reachA * 0.2, sA.y - reachA * 0.96];
    const raised: V2 = [sA.x - reachA * 0.3, sA.y + reachA * 0.55];
    const wr = this.sim.get(`${id}:wrist`), el = this.sim.get(`${id}:elbow`);
    const attachedW = it.drop.wrist >= 0.999 ? 1 : 0, attachedE = it.drop.elbow >= 0.999 ? 1 : 0;
    v2.set(lerp(rest[0], raised[0], it.armRaise) + wr.ox * attachedW + el.ox * 0.5 * attachedE,
      lerp(rest[1], raised[1], it.armRaise) + wr.oy * attachedW + el.oy * 0.5 * attachedE);
    rig.solveLimb('armA', v2);
    if (rig.has('handA')) rig.setRot('handA', 0.15 * it.armRaise - wr.ox * 0.2);

    const sB = rig.localPoint('upperArmB');
    const reachB = len('armB');
    let tx = sB.x + reachB * 0.2, ty = sB.y - reachB * 0.96;
    const wave = it.waveB * Math.sin(t * Math.PI * 2 * 1.4) * 0.12;
    tx = lerp(tx, sB.x + reachB * 0.72, it.reachB); ty = lerp(ty, sB.y + reachB * 0.15, it.reachB);
    tx = lerp(tx, sB.x + reachB * 0.35 + wave, it.waveB); ty = lerp(ty, sB.y + reachB * 0.6, it.waveB);
    tx = lerp(tx, sB.x + reachB * 0.6, it.grabB); ty = lerp(ty, sB.y - reachB * 0.74, it.grabB);
    v2.set(tx, ty);
    rig.solveLimb('armB', v2);

    const ankleY = rig.part('pelvis').spec.at[1] - 0.1 - Math.hypot(...rig.part('shinA').spec.at) - Math.hypot(...rig.part('footA').spec.at);
    const hipA = rig.localPoint('thighA'), hipB = rig.localPoint('thighB');
    const kn = this.sim.get(`${id}:knee`);
    const attachedK = it.drop.knee >= 0.999 ? 1 : 0;
    const planted = (hip: Vector2): V2 => [hip.x + 0.02 - (body.ox * 0.35), ankleY - it.lift - it.step * 0.04];
    const pa = planted(hipA);
    v2.set(pa[0] + it.step * 0.3 + kn.ox * 0.7 * attachedK, pa[1] + it.step * 0.08 + Math.max(0, kn.oy) * 0.8 * attachedK);
    rig.solveLimb('legA', v2);
    const pb = planted(hipB);
    v2.set(pb[0], pb[1]);
    rig.solveLimb('legB', v2);
    if (rig.has('footA')) rig.setRot('footA', -rig.chainRot('footA'));
    if (rig.has('footB')) rig.setRot('footB', -rig.chainRot('footB'));

    // 佔位臉：眼、嘴是部件
    if (rig.has('eyeL') && rig.has('eyeR') && rig.has('mouth')) {
      const fx = this.faceAt(id, it, tl, t, 'closed');
      const blink = fx.eyes === 'closed' ? 0.15 : fx.eyes === 'half' ? 0.5 : 1;
      rig.part('eyeL').mesh!.scale.y = blink;
      rig.part('eyeR').mesh!.scale.y = blink;
      const open = fx.mouth === 'open' ? 1 : fx.mouth === 'round' ? 0.75 : fx.mouth === 'half' ? 0.45 : 0;
      const m = rig.part('mouth').mesh!;
      m.scale.y = 0.22 + 0.78 * open;
      m.scale.x = fx.mouth === 'round' ? 0.7 : 1;
    }
    rig.root.updateMatrixWorld(true);
    this.poseStrings(actor, it, t, 'side');
  }
}
