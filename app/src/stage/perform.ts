// 紙偶表演：把 cue 的角色動畫（target＝角色 id）換算成姿勢、操偶線與嘴型。
// 角色動畫表：
//   strings.drop {anchors, stagger}     操偶線從上方落下、以紙環扣上（依序）
//   strings.tension {to, anchors}       調整張力（0 鬆垂～1 繃緊）
//   strings.loosen {anchors, fadeTo}    復原：線變鬆、變淡（不剪斷）
//   puppet.waveTry                      想揮手：手抬起 → 線繃緊 → 手被拉向一旁
//   puppet.kneeTug                      想往前走：膝蓋被線一扯、身體晃一下、扶住桌邊
//   puppet.reach / puppet.wave          另一隻手伸向前／揮手（孩子用）
//   puppet.lean {to} / puppet.move {dx} 身體前傾／移動
// 所有量都是「時間的純函式」；擺盪交給固定步長的 StringSim，每個 cue 開始時重設。
import { Group, Vector2, Vector3, type Material, type Object3D } from 'three';
import type { CharacterStart } from '../types/cue';
import type { CueTimeline, ResolvedAnim } from '../cues/timeline';
import { Rig, type AnchorName, type RigSpec } from './rig';
import { PaperString, StringSim } from './strings';
import { LAYER } from './layers';
import { clamp, ease, hashString, lerp, smoothstep } from '../util/math';

export const ANCHORS: AnchorName[] = ['wrist', 'elbow', 'knee'];
/**
 * 操偶線上端的水平偏移（本地座標，+＝面向的前方）：
 * 手腕、手肘的線往後上方（危險那一側）；膝蓋的線往前上方斜出，避開頭頸（兒童安全界線：線不經過脖子與臉）。
 */
const STRING_LEAN: Record<AnchorName, number> = { wrist: -0.25, elbow: -0.25, knee: 2.6 };
/** 操偶線上端的高度（遠高於任何鏡位的畫面上緣，線一定延伸出畫面） */
const STRING_TOP_Y = 14;
const STRING_WIDTH = 0.07;

export interface ActorConfig { id: string; spec: RigSpec; x: number; z: number; facing: 1 | -1 }

export interface LipsyncData { fps: number; frames: number[] }

type V2 = [number, number];

interface Intent {
  visible: boolean; x: number; y: number; z: number; facing: 1 | -1;
  dx: number; lift: number; lean: number;
  armRaise: number; reachB: number; waveB: number; grabTable: number; step: number;
  drop: Record<AnchorName, number>; tension: Record<AnchorName, number>; fade: Record<AnchorName, number>;
  pull: Record<AnchorName, V2>; bodyPush: V2;
}

const rec = <T>(v: () => T): Record<AnchorName, T> => ({ wrist: v(), elbow: v(), knee: v() });

export class PuppetActor {
  readonly rig: Rig;
  readonly strings = new Map<AnchorName, PaperString>();
  readonly stringMats = new Map<AnchorName, Material>();

  constructor(readonly cfg: ActorConfig, orderBase: number, ropeMat: Material, ringMat: Material) {
    this.rig = new Rig(cfg.spec, { renderOrderBase: orderBase, seed: hashString(cfg.id) % 10000 });
    for (const a of ANCHORS) {
      if (!cfg.spec.anchors[a]) continue;
      const mat = ropeMat.clone(); // 每條線各自一份材質，復原時才能個別變淡
      this.stringMats.set(a, mat);
      this.strings.set(a, new PaperString(mat, ringMat, LAYER.strings.order + orderBase % LAYER.actorStride));
    }
  }

  get root(): Group { return this.rig.root; }

  addTo(parent: Object3D): void {
    parent.add(this.rig.root);
    this.strings.forEach((s) => { parent.add(s.mesh); parent.add(s.ring); });
  }
}

/** 角色姿勢預設 */
function applyPosePreset(it: Intent, pose: string | undefined): void {
  if (pose === 'pulled') {
    it.armRaise = 0.55;
    it.pull.wrist = [-0.85, 0.25]; it.pull.elbow = [-0.3, 0.12]; it.pull.knee = [0.08, 0.1];
    it.tension.wrist = 1; it.tension.elbow = 1; it.tension.knee = 0.7;
  }
}

function prog(a: ResolvedAnim, t: number, from = 0, to = 1): number {
  const u = (t - a.start) / Math.max(1e-6, a.duration);
  return clamp((u - from) / (to - from));
}

/** 角色在時間 t 的「意圖」（還沒加上擺盪模擬） */
export function evalIntent(cfg: ActorConfig, start: CharacterStart | undefined, anims: ResolvedAnim[], t: number): Intent {
  const it: Intent = {
    visible: start ? start.visible !== false : false,
    x: start?.x ?? cfg.x, y: start?.y ?? 0, z: start?.z ?? cfg.z, facing: start?.facing ?? cfg.facing,
    dx: 0, lift: 0, lean: 0, armRaise: 0, reachB: 0, waveB: 0, grabTable: 0, step: 0,
    drop: rec(() => 0), tension: rec(() => start?.stringTension ?? 0.3), fade: rec(() => 1),
    pull: rec<V2>(() => [0, 0]), bodyPush: [0, 0],
  };
  for (const a of start?.strings ?? []) if (a in it.drop) it.drop[a as AnchorName] = 1;
  applyPosePreset(it, start?.pose);

  for (const a of anims) {
    if (a.target !== cfg.id) continue;
    switch (a.name) {
      case 'strings.drop': {
        const list = (Array.isArray(a.params.anchors) ? a.params.anchors : ANCHORS) as AnchorName[];
        const stagger = Number(a.params.stagger ?? 0.4);
        const each = Math.max(0.3, a.duration - stagger * (list.length - 1));
        list.forEach((name, i) => {
          if (!(name in it.drop)) return;
          it.drop[name] = ease('out', (t - a.start - i * stagger) / each);
          it.tension[name] = 0.15; // 剛落下時是鬆的
        });
        break;
      }
      case 'strings.tension': {
        const list = (Array.isArray(a.params.anchors) ? a.params.anchors : ANCHORS) as AnchorName[];
        const p = ease(a.ease, prog(a, t));
        for (const n of list) if (n in it.tension) it.tension[n] = lerp(it.tension[n], Number(a.params.to ?? 1), p);
        break;
      }
      case 'strings.loosen': {
        const list = (Array.isArray(a.params.anchors) ? a.params.anchors : ANCHORS) as AnchorName[];
        const p = ease(a.ease, prog(a, t));
        for (const n of list) {
          if (!(n in it.tension)) continue;
          it.tension[n] = lerp(it.tension[n], 0, p);
          it.pull[n] = [lerp(it.pull[n][0], 0, p), lerp(it.pull[n][1], 0, p)];
          it.fade[n] = lerp(1, Number(a.params.fadeTo ?? 0.25), p);
        }
        break;
      }
      case 'puppet.waveTry': {
        // 0–30% 手抬起；30–42% 線繃緊（先繃緊）；42–67% 手被拉向一旁（再拉動）
        it.armRaise = Math.max(it.armRaise, ease('inOut', prog(a, t, 0, 0.3)));
        const tense = smoothstep(0.3, 0.42, (t - a.start) / a.duration);
        it.tension.wrist = Math.max(it.tension.wrist, lerp(0.25, 1, tense));
        it.tension.elbow = Math.max(it.tension.elbow, lerp(0.25, 1, smoothstep(0.32, 0.44, (t - a.start) / a.duration)));
        const pull = ease('inOut', prog(a, t, 0.42, 0.67));
        it.pull.wrist = [lerp(it.pull.wrist[0], -0.85, pull), lerp(it.pull.wrist[1], 0.25, pull)];
        it.pull.elbow = [lerp(it.pull.elbow[0], -0.3, pull), lerp(it.pull.elbow[1], 0.12, pull)];
        break;
      }
      case 'puppet.kneeTug': {
        // 想往前一步 → 膝蓋的線繃緊 → 被往後上方一扯 → 身體晃一下 → 另一隻手扶住桌邊
        it.step = Math.max(it.step, ease('inOut', prog(a, t, 0, 0.3)) * (1 - ease('inOut', prog(a, t, 0.38, 0.55))));
        it.tension.knee = Math.max(it.tension.knee, lerp(0.25, 1, smoothstep(0.24, 0.36, (t - a.start) / a.duration)));
        const tug = ease('inOut', prog(a, t, 0.38, 0.5)) - 0.6 * ease('inOut', prog(a, t, 0.6, 0.85));
        it.pull.knee = [lerp(it.pull.knee[0], 0.22, tug), lerp(it.pull.knee[1], 0.32, tug)];
        const push = ease('inOut', prog(a, t, 0.38, 0.46)) * (1 - ease('inOut', prog(a, t, 0.46, 0.6)));
        it.bodyPush = [it.bodyPush[0] - 0.35 * push, it.bodyPush[1]];
        it.grabTable = Math.max(it.grabTable, ease('inOut', prog(a, t, 0.5, 0.72)));
        break;
      }
      case 'puppet.reach': it.reachB = Math.max(it.reachB, ease(a.ease, prog(a, t))); break;
      case 'puppet.wave': it.waveB = Math.max(it.waveB, ease('inOut', prog(a, t, 0, 0.2)) * (1 - ease('inOut', prog(a, t, 0.85, 1)))); break;
      case 'puppet.lean': it.lean = lerp(it.lean, Number(a.params.to ?? 0.1), ease(a.ease, prog(a, t))); break;
      case 'puppet.move': it.dx += Number(a.params.dx ?? 0) * ease(a.ease, prog(a, t)); break;
      default: break;
    }
  }
  return it;
}

const v2 = new Vector2();
const w3 = new Vector3();
const top3 = new Vector3();
const bot3 = new Vector3();

export class PuppetDirector {
  readonly sim = new StringSim();
  private key = '';

  constructor(readonly actors: Map<string, PuppetActor>, private lipsync: (id: string) => LipsyncData | undefined = () => undefined) {}

  /** 新 cue／重播／上一步時重設模擬 */
  reset(): void { this.key = ''; }

  apply(tl: CueTimeline, t: number, playKey: string): void {
    const chars = tl.cue.initialState.characters ?? {};
    const intentsAt = (time: number): Map<string, Intent> => {
      const m = new Map<string, Intent>();
      this.actors.forEach((a, id) => m.set(id, evalIntent(a.cfg, chars[id], tl.anims, time)));
      return m;
    };
    // 模擬通道：每個錨點的拉力位移＋身體擺盪
    const drive = (time: number): Map<string, { px: number; py: number }> => {
      const out = new Map<string, { px: number; py: number }>();
      intentsAt(time).forEach((it, id) => {
        for (const n of ANCHORS) out.set(`${id}:${n}`, { px: it.pull[n][0], py: it.pull[n][1] });
        out.set(`${id}:body`, { px: it.bodyPush[0], py: it.bodyPush[1] });
      });
      return out;
    };
    const key = `${tl.cue.id}#${playKey}`;
    if (key !== this.key) { this.key = key; this.sim.reset(drive(0)); }
    this.sim.advanceTo(t, drive, drive(0));

    const intents = intentsAt(t);
    this.actors.forEach((actor, id) => this.pose(actor, intents.get(id)!, tl, t));
  }

  private pose(actor: PuppetActor, it: Intent, tl: CueTimeline, t: number): void {
    const rig = actor.rig;
    const id = actor.cfg.id;
    rig.root.visible = it.visible;
    actor.strings.forEach((s) => s.update(top3, bot3, 0, STRING_WIDTH, false, false));
    if (!it.visible) return;
    rig.resetPose();
    const body = this.sim.get(`${id}:body`);
    const f = it.facing;
    rig.root.scale.x = f;
    rig.root.position.set(it.x + (it.dx + body.ox * 0.35) * f, it.y + it.lift + it.step * 0.04, it.z);
    rig.root.rotation.z = -(it.lean + body.ox * 0.18 + it.step * 0.04) * f;
    // 呼吸：軀幹極輕微擺動（時間的純函式）
    const phase = (hashString(id) % 1000) / 1000;
    rig.setRot('torso', 0.012 * Math.sin((t / 3.6 + phase) * Math.PI * 2));
    rig.setRot('head', 0.02 * Math.sin((t / 4.4 + phase) * Math.PI * 2) - it.pull.wrist[0] * 0.04);
    rig.root.updateMatrixWorld(true);

    const L = rig.spec.limbs;
    const len = (limb: string): number => {
      const l = L[limb];
      return Math.hypot(...rig.part(l.lower).spec.at) + Math.hypot(...rig.part(l.end).spec.at);
    };

    // A 側手臂（操偶線那隻）：意圖位置＋線的拉力位移
    const sA = rig.localPoint('upperArmA');
    const reachA = len('armA');
    const rest: V2 = [sA.x - reachA * 0.2, sA.y - reachA * 0.96];
    const raised: V2 = [sA.x - reachA * 0.3, sA.y + reachA * 0.55];
    const wr = this.sim.get(`${id}:wrist`), el = this.sim.get(`${id}:elbow`);
    const attachedW = it.drop.wrist >= 0.999 ? 1 : 0, attachedE = it.drop.elbow >= 0.999 ? 1 : 0;
    v2.set(lerp(rest[0], raised[0], it.armRaise) + wr.ox * attachedW + el.ox * 0.5 * attachedE,
      lerp(rest[1], raised[1], it.armRaise) + wr.oy * attachedW + el.oy * 0.5 * attachedE);
    rig.solveLimb('armA', v2);
    rig.setRot('handA', 0.15 * it.armRaise - wr.ox * 0.2);

    // B 側手臂：伸手、揮手、扶桌
    const sB = rig.localPoint('upperArmB');
    const reachB = len('armB');
    const restB: V2 = [sB.x + reachB * 0.2, sB.y - reachB * 0.96];
    let tx = restB[0], ty = restB[1];
    const wave = it.waveB * Math.sin(t * Math.PI * 2 * 1.4) * 0.12;
    tx = lerp(tx, sB.x + reachB * 0.72, it.reachB); ty = lerp(ty, sB.y + reachB * 0.15, it.reachB);
    tx = lerp(tx, sB.x + reachB * 0.35 + wave, it.waveB); ty = lerp(ty, sB.y + reachB * 0.6, it.waveB);
    tx = lerp(tx, sB.x + reachB * 0.6, it.grabTable); ty = lerp(ty, sB.y - reachB * 0.74, it.grabTable);
    v2.set(tx, ty);
    rig.solveLimb('armB', v2);

    // 腿：B 腳踩穩不動（身體晃時腳不滑）；A 腳被膝蓋的線牽動
    // 腳踝靜止高度＝髖關節高度 − 大腿 − 小腿（紙偶根在地面 y=0）
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
    rig.setRot('footA', -rig.chainRot('footA'));
    rig.setRot('footB', -rig.chainRot('footB'));

    // 臉：眨眼（3–6 秒一次）與嘴型（每秒 12 格量化）
    const period = 3.6 + (hashString(id + 'blink') % 200) / 100;
    const blink = ((t + phase * period) % period) < 0.13 ? 0.15 : 1;
    rig.part('eyeL').mesh.scale.y = blink;
    rig.part('eyeR').mesh.scale.y = blink;
    const mouth = this.mouthOpen(id, tl, t);
    const m = rig.part('mouth').mesh;
    m.scale.y = 0.22 + 0.78 * mouth.open;
    m.scale.x = mouth.round ? 0.7 : 1;

    // 操偶線：上端在畫面外，下端扣在錨點；張力低時有弧度，繃緊時拉直
    rig.root.updateMatrixWorld(true);
    for (const n of ANCHORS) {
      const s = actor.strings.get(n);
      if (!s) continue;
      const drop = it.drop[n];
      if (drop <= 0.001 || it.fade[n] <= 0.001) continue;
      const anchor = rig.anchorWorld(n, w3);
      if (!anchor) continue;
      const pullX = it.pull[n][0] * f;
      const zFront = it.z + 0.2;
      top3.set(anchor.x + pullX * 2.2 + STRING_LEAN[n] * f, STRING_TOP_Y, zFront);
      bot3.set(anchor.x, lerp(STRING_TOP_Y, anchor.y, drop), zFront);
      const bow = (1 - it.tension[n]) * 0.32 * drop * f;
      const mat = actor.stringMats.get(n);
      if (mat) { mat.transparent = it.fade[n] < 0.999; mat.opacity = it.fade[n]; mat.depthWrite = !mat.transparent; }
      s.update(top3, bot3, bow, STRING_WIDTH, drop >= 0.999, true);
    }
  }

  /** 嘴型：有對嘴資料就照資料，沒有就依字幕時間產生佔位開合 */
  private mouthOpen(actorId: string, tl: CueTimeline, t: number): { open: number; round: boolean } {
    for (const l of tl.lines) {
      if (l.actorId !== actorId || t < l.start || t >= l.end) continue;
      const lip = this.lipsync(l.line.lipsyncId ?? l.line.id);
      const local = t - l.start;
      if (lip) {
        const shape = lip.frames[Math.min(lip.frames.length - 1, Math.floor(local * lip.fps))] ?? 0;
        return { open: [0, 0.45, 1, 0.75][shape] ?? 0, round: shape === 3 };
      }
      // 佔位：每秒 12 格量化、約每秒 5 個音節
      const q = Math.floor(local * 12) / 12;
      const h = hashString(`${l.line.id}:${Math.floor(q * 5)}`);
      const syl = Math.abs(Math.sin(q * Math.PI * 5));
      const levels = [0, 0.45, 1];
      const lv = syl < 0.3 ? 0 : syl < 0.7 ? 1 : (h % 3 === 0 ? 1 : 2);
      return { open: levels[lv], round: h % 7 === 0 && lv > 0 };
    }
    return { open: 0, round: false };
  }
}
