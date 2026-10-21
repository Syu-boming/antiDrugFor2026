// 演員名單：依 cue 檔的 characters（角色 id → { name, rig, x, z, facing }）建立紙偶，不再寫死在程式裡。
// rig 名稱 → 紙偶設定，依序查：
//   1. assets/final/g4_manifest.json 的 characters[角色 id]（G4 起；照舊有效，覆寫在找到的設定上）
//   2. assets/final/rig/show_characters.json 的 characters[角色 id]（同上，G5 新增）
//   3. assets/final/rig/show_characters.json 的 rigs[rig 名稱]（G5：新立牌角色只要放圖＋登記，不必改程式）
//   4. 內建設定 BUILTIN_RIGS[rig 名稱]
//   找不到 → 名冊的 fallback（adult／child）程式佔位紙偶，並記在 report。
// 程式角色（rig 設定 { rig: 'program', program: '<名稱>' }，例如折折 rig:'zhezhe'）：由 registerProgramRig 登記的建構器建立；
// 沒登記（例如 zhezhe.ts 還沒接上）就用「佔位小紙片」，不當機。
// 素材缺少時退回程式佔位紙偶並記在 report（準備畫面與 getState().castReport 都看得到），不當機。
import { CanvasTexture, DoubleSide, Group, Mesh, MeshStandardMaterial, PlaneGeometry, type Object3D } from 'three';
import type { CharacterRoster, CharacterStart } from '../types/cue';
import type { AssetStore } from '../data/assets';
import type { CueTimeline } from '../cues/timeline';
import { Rig } from './rig';
import { buildImageRig, partsFromRigJson, type AttachJson, type PartsJson, type RigJsonV04 } from './imagerig';
import { StandeeActor, type StandeePoseConfig } from './standee';
import { FaceRig, FALLBACK_FACES, parseFaceJson, type FallbackFace } from './face';
import { RIG_ALE, RIG_XIAOQING } from './rigspecs';
import { evalIntent, RigPerformer, StandeePerformer, type ActorPlacement, type LipsyncData, type Performer } from './perform';
import { LAYER, Z_STEP } from './layers';
import { finishTexture, fibers, makeCanvas } from './paper';

export interface PartsCharConfig {
  rig: 'parts';
  /** 分件資料的素材 JSON id：v04 格式（rig/ale_rig.json）或 parts.json 格式 */
  parts: string;
  /** 找不到 parts 時的退路（例如 rig/ale_v03/parts） */
  fallbackParts?: string;
  /** 部件圖像 id 前綴（部件圖 id＝前綴＋部件檔名去副檔名） */
  imagePrefix?: string;
  height: number;
  face?: string;
  attach?: string;
  fallbackFace?: string;
  seatHip?: number;
  stringArm?: 'r' | 'l';
  kneeLeg?: 'r' | 'l';
}

export interface StandeeCharConfig {
  rig: 'standee';
  height: number;
  poses: Record<string, string | StandeePoseConfig>;
  defaultPose?: string;
  face?: string;
  edge?: number;
}

export interface ProceduralCharConfig { rig: 'procedural'; spec: 'adult' | 'child' }

/** 程式角色（例如折折）：program＝registerProgramRig 登記的名稱；其他欄位原樣交給建構器 */
export interface ProgramCharConfig { rig: 'program'; program: string; height?: number; [k: string]: unknown }

export type CharConfig = PartsCharConfig | StandeeCharConfig | ProceduralCharConfig | ProgramCharConfig;

/** 內建紙偶設定（G4 時的素材位置；正式素材由 g4_manifest.json／show_characters.json 覆寫） */
export const BUILTIN_RIGS: Record<string, CharConfig> = {
  adult: { rig: 'procedural', spec: 'adult' },
  child: { rig: 'procedural', spec: 'child' },
  ale_v03: {
    rig: 'parts', parts: 'rig/ale_rig', fallbackParts: 'rig/ale_v03/parts', imagePrefix: 'rig/ale_v03/', height: 3.55,
    face: 'face/ale/face', attach: 'rig/ale_attach', fallbackFace: 'ale:head', stringArm: 'r', kneeLeg: 'l',
  },
  'standee:xiaoqing': {
    rig: 'standee', height: 2.5, defaultPose: 'stand', face: 'face/xiaoqing/face',
    poses: { stand: { image: 'chr-xiaoqing_master' }, reach: { image: 'chr-xiaoqing_pose-reach-worried' } },
  },
  'standee:xiaoyu': {
    rig: 'standee', height: 2.42, defaultPose: 'stand', face: 'face/xiaoyu/face',
    poses: { stand: { image: 'chr-xiaoyu_master' }, stepback: { image: 'chr-xiaoyu_pose-stepback-surprised' } },
  },
  /** 折折（程式角色；app/src/stage/zhezhe.ts 接上前用佔位小紙片） */
  zhezhe: { rig: 'program', program: 'zhezhe', height: 0.95 },
};

/** assets/final/rig/show_characters.json（共用美術代理維護；格式見 app/SHOW_INTERFACE.md） */
export interface ShowCharactersJson {
  format?: string;
  /** rig 名稱 → 紙偶設定（BUILTIN_RIGS 條目同格式，例如 "standee:pinan": { rig: 'standee', height, poses, face }） */
  rigs?: Record<string, CharConfig>;
  /** 角色 id → 完整設定（有 rig 欄位；共用美術代理的寫法）或部分覆寫（同 g4_manifest.json 的 characters）；standee 的 poses 會合併 */
  characters?: Record<string, Partial<CharConfig>>;
  /** 退路臉部範圍（FALLBACK_FACES 同格式；key＝<角色 id>:<姿勢>） */
  fallbackFaces?: Record<string, FallbackFace>;
}
export const SHOW_CHARACTERS_JSON = 'rig/show_characters';

// ------------------------------------------------------------------ 程式角色

/** 程式角色的介面（舞台每格呼叫 apply；不經過 PuppetDirector） */
export interface ProgramPerformer {
  readonly kind: 'program';
  readonly place: ActorPlacement;
  readonly root: Group;
  readonly id: string;
  addTo(parent: Object3D): void;
  /**
   * 每格呼叫：start＝這個 cue 的 initialState.characters[id]（沒列＝不在台上）；tl.anims 裡 target＝id 的動畫自己解讀
   * （puppet.enter／exit／move／popup／face 與 <程式名>.<動作>）。必須是時間的純函式（重播、上一步、擷取一致）。
   */
  apply(tl: CueTimeline, t: number, start: CharacterStart | undefined, ctx: ProgramContext): void;
  /** 量測用：目前眼睛與嘴型（debug.faces） */
  faceState?(): { eyes: string; mouth: string } | null;
  dispose?(): void;
}

export interface ProgramContext {
  /** 舞台燈總量 0.55–1 */
  light: number;
  /** 播放識別（換 cue、重播時改變；有模擬狀態的角色用它重設） */
  playKey: string;
  lipsync: (id: string) => LipsyncData | undefined;
}

export interface ProgramRigOptions {
  id: string;
  place: ActorPlacement;
  assets: AssetStore | null;
  orderBase: number;
  alphaToCoverage: boolean;
  config: ProgramCharConfig;
}

export type ProgramRigFactory = (o: ProgramRigOptions) => ProgramPerformer | null;

const PROGRAM_RIGS = new Map<string, ProgramRigFactory>();

/** 登記程式角色（例如 registerProgramRig('zhezhe', createZhezhePerformer)）；要在 cue 檔載入、建立紙偶之前呼叫 */
export function registerProgramRig(name: string, factory: ProgramRigFactory): void { PROGRAM_RIGS.set(name, factory); }
export function programRigNames(): string[] { return [...PROGRAM_RIGS.keys()]; }

/** 佔位小紙片：白底淺橙的小摺紙（像一隻還沒摺好的紙貓），只做進出場、移動、立起與說話時的輕微彈動 */
class PaperScrapPerformer implements ProgramPerformer {
  readonly kind = 'program' as const;
  readonly root = new Group();
  private body = new Group();
  constructor(readonly place: ActorPlacement, height: number, orderBase: number, a2c: boolean) {
    const W = 220, H = 240;
    const [c, g] = makeCanvas(W, H);
    g.fillStyle = '#fbf3e6';
    g.beginPath(); g.moveTo(W * 0.12, H * 0.98); g.lineTo(W * 0.2, H * 0.3); g.lineTo(W * 0.3, H * 0.04); g.lineTo(W * 0.44, H * 0.26);
    g.lineTo(W * 0.56, H * 0.26); g.lineTo(W * 0.7, H * 0.04); g.lineTo(W * 0.8, H * 0.3); g.lineTo(W * 0.88, H * 0.98); g.closePath(); g.fill();
    g.fillStyle = '#f2c79a';
    g.beginPath(); g.moveTo(W * 0.5, H * 0.3); g.lineTo(W * 0.86, H * 0.96); g.lineTo(W * 0.5, H * 0.96); g.closePath(); g.fill();
    g.strokeStyle = 'rgba(150,110,70,0.5)'; g.lineWidth = 3;
    g.beginPath(); g.moveTo(W * 0.5, H * 0.28); g.lineTo(W * 0.5, H * 0.96); g.stroke();
    g.save(); g.globalCompositeOperation = 'source-atop'; fibers(g, W, H, 77, 0.9); g.restore();
    const tex = finishTexture(new CanvasTexture(c));
    const mat = new MeshStandardMaterial({ map: tex, alphaTest: 0.5, side: DoubleSide, roughness: 0.9, metalness: 0, alphaToCoverage: a2c });
    const w = height * W / H;
    const geo = new PlaneGeometry(w, height);
    geo.translate(0, height / 2, 0);
    const m = new Mesh(geo, mat);
    m.renderOrder = orderBase + 1;
    m.castShadow = true;
    this.body.add(m);
    this.root.add(this.body);
    this.root.name = `program:${place.id}`;
  }
  get id(): string { return this.place.id; }
  addTo(parent: Object3D): void { parent.add(this.root); }
  apply(tl: CueTimeline, t: number, start: CharacterStart | undefined): void {
    const it = evalIntent(this.place, 'front', start, tl.anims, t);
    this.root.visible = it.visible;
    if (!it.visible) return;
    const speaking = tl.lines.some((l) => l.actorId === this.place.id && t >= l.start && t < l.end);
    const bob = speaking ? Math.abs(Math.sin(t * Math.PI * 4)) * 0.05 : 0;
    this.root.position.set(it.x + it.dx, it.y + it.lift + (it.walk ? Math.abs(Math.sin(t * Math.PI * 3.2)) * 0.04 : 0), it.z);
    this.root.rotation.set(-(1 - Math.min(1, it.popup)) * Math.PI / 2, 0, 0);
    this.body.scale.set(it.facing, 1 + bob, 1);
  }
  faceState(): null { return null; }
}

// ------------------------------------------------------------------ 建立

export type AnyPerformer = Performer | ProgramPerformer;

export interface CastResult { actors: Map<string, Performer>; programs: Map<string, ProgramPerformer>; report: string[]; timings: Record<string, number> }

/** 全劇演員池的一個條目：key＝池內唯一鍵（同一角色換 rig 時不同），id＝角色 id */
export interface CastEntry { key: string; id: string; entry: CharacterRoster[string] }

export interface PoolResult { pool: Map<string, AnyPerformer>; report: string[]; timings: Record<string, number> }

const baseName = (f: string): string => f.replace(/^.*\//, '').replace(/\.[a-z0-9]+$/i, '').replace(/_v\d+$/i, '');

/** 演員池鍵：角色 id＋rig（同一角色在不同段落用不同紙偶時分開建立） */
export const castKey = (id: string, rig: string | undefined): string => `${id}|${rig ?? ''}`;

/** 舊介面（單一名冊）：建立名冊上的紙偶 */
export function buildCast(roster: CharacterRoster | undefined, assets: AssetStore | null, opts: { alphaToCoverage: boolean; marks?: Record<string, { x: number; z: number }> }): CastResult {
  const entries = Object.entries(roster ?? {}).map(([id, entry]) => ({ key: castKey(id, entry.rig), id, entry }));
  const r = buildCastPool(entries, assets, opts);
  const actors = new Map<string, Performer>();
  const programs = new Map<string, ProgramPerformer>();
  for (const e of entries) {
    const p = r.pool.get(e.key);
    if (!p) continue;
    if (p.kind === 'program') programs.set(e.id, p); else actors.set(e.id, p);
  }
  return { actors, programs, report: r.report, timings: r.timings };
}

/** 建立演員池（全劇所有段落的名冊聯集；依序給 renderOrder 基準） */
export function buildCastPool(entries: CastEntry[], assets: AssetStore | null, opts: { alphaToCoverage: boolean; marks?: Record<string, { x: number; z: number }> }): PoolResult {
  const pool = new Map<string, AnyPerformer>();
  const report: string[] = [];
  const timings: Record<string, number> = {};
  const man = assets?.getJson<{ characters?: Record<string, Partial<CharConfig>> }>('g4_manifest');
  const show = assets?.getJson<ShowCharactersJson>(SHOW_CHARACTERS_JSON);
  const faces: Record<string, FallbackFace> = { ...FALLBACK_FACES, ...(show?.fallbackFaces ?? {}) };
  let i = 0;
  for (const { key, id, entry } of entries) {
    if (pool.has(key)) continue;
    const orderBase = LAYER.actors.order + i * LAYER.actorStride;
    i++;
    const mark = opts.marks?.[id];
    const place: ActorPlacement = { id, x: entry.x ?? mark?.x ?? 0, z: entry.z ?? mark?.z ?? 0, facing: (entry.facing ?? 1) as 1 | -1 };
    const rigName = entry.rig ?? '';
    const fallbackName = entry.fallback ?? (id === 'ale' ? 'adult' : 'child');
    // show_characters.json 的 characters[角色 id] 可以是完整設定（有 rig 欄位，共用美術代理的寫法），也可以只是部分覆寫
    const showChar = show?.characters?.[id];
    const found = show?.rigs?.[rigName] ?? BUILTIN_RIGS[rigName] ?? (showChar && 'rig' in showChar ? showChar as CharConfig : undefined);
    if (!found && rigName) report.push(`${entry.name}（${id}）：紙偶 ${rigName} 還沒登記（show_characters.json），用程式佔位紙偶`);
    const builtin = found ?? BUILTIN_RIGS[fallbackName];
    const layers = [man?.characters?.[id], showChar].filter(Boolean) as Partial<CharConfig>[];
    let cfg = builtin as CharConfig;
    for (const o of layers) {
      const prev = cfg as Partial<StandeeCharConfig>;
      const next = { ...cfg, ...o } as CharConfig;
      // 姿勢表合併（G4 的姿勢不會被只列新姿勢的覆寫蓋掉）
      if (next.rig === 'standee' && prev.poses && (o as Partial<StandeeCharConfig>).poses) next.poses = { ...prev.poses, ...(o as Partial<StandeeCharConfig>).poses };
      cfg = next;
    }
    const t0 = performance.now();
    let perf: AnyPerformer | null = null;
    try {
      if (cfg.rig === 'parts' && assets) perf = buildParts(id, place, cfg, assets, orderBase, opts.alphaToCoverage, report, faces);
      else if (cfg.rig === 'standee' && assets) perf = buildStandee(id, place, cfg, assets, orderBase, opts.alphaToCoverage, report, faces);
      else if (cfg.rig === 'program') {
        const f = PROGRAM_RIGS.get(cfg.program);
        perf = f ? f({ id, place, assets, orderBase, alphaToCoverage: opts.alphaToCoverage, config: cfg }) : null;
        if (!perf) {
          report.push(`${entry.name}（${id}）：程式角色 ${cfg.program} 還沒接上，用佔位小紙片`);
          perf = new PaperScrapPerformer(place, cfg.height ?? 0.95, orderBase, opts.alphaToCoverage);
        }
      }
    } catch (err) {
      report.push(`${entry.name}（${id}）：素材建立失敗（${err instanceof Error ? err.message : String(err)}），改用佔位紙偶`);
      perf = null;
    }
    if (!perf) {
      const spec = cfg.rig === 'procedural' ? (cfg.spec === 'adult' ? RIG_ALE : RIG_XIAOQING) : (fallbackName === 'adult' ? RIG_ALE : RIG_XIAOQING);
      const rig = new Rig({ ...spec, id }, { renderOrderBase: orderBase, seed: i * 1000 });
      perf = new RigPerformer(place, rig, 'side', null, orderBase);
      if (cfg.rig !== 'procedural') report.push(`${entry.name}（${id}）：找不到正式素材，用程式佔位紙偶`);
    }
    timings[id] = performance.now() - t0;
    pool.set(key, perf);
  }
  return { pool, report, timings };
}

function buildParts(id: string, place: ActorPlacement, cfg: PartsCharConfig, assets: AssetStore, orderBase: number, a2c: boolean, report: string[], fallbackFaces: Record<string, FallbackFace>): Performer | null {
  // 分件資料：先找 v04 格式（部件圖已裁切，含替換部件 head_worried），再找 parts.json 格式（整張畫布）
  let parts: PartsJson | undefined;
  let origins: Record<string, [number, number]> = {};
  let imageIds: Record<string, string> = {};
  let variants: Record<string, string> = {};
  let fixed = false;
  const raw = assets.getJson<RigJsonV04 & PartsJson>(cfg.parts) ?? (cfg.fallbackParts ? assets.getJson<RigJsonV04 & PartsJson>(cfg.fallbackParts) : undefined);
  const usedId = assets.getJson(cfg.parts) ? cfg.parts : cfg.fallbackParts ?? cfg.parts;
  if (raw && (raw as RigJsonV04).layers_back_to_front) {
    const conv = partsFromRigJson(raw as RigJsonV04);
    parts = conv.parts; origins = conv.origins; imageIds = conv.imageIds; variants = conv.variants;
    fixed = !!(raw as RigJsonV04).fix_log;
  } else if (raw) parts = raw as PartsJson;
  if (!parts) { report.push(`${id}：缺少分件資料 ${cfg.parts}`); return null; }
  const prefix = usedId === cfg.parts && imageIds && Object.keys(imageIds).length ? '' : (cfg.imagePrefix ?? `${usedId.replace(/\/[^/]*$/, '')}/`);
  const missing: string[] = [];
  const lookup = (pid: string, file: string): { img: CanvasImageSource; origin: [number, number] } | undefined => {
    const iid = imageIds[pid];
    const img = (iid ? assets.image(iid) : undefined) ?? assets.image(`${prefix}${baseName(file)}`) ?? assets.image(`${prefix}${pid}`);
    if (!img) { missing.push(pid); return undefined; }
    return { img, origin: origins[pid] ?? [0, 0] };
  };
  const varSpec: Record<string, { of: string; bbox: [number, number, number, number] }> = {};
  for (const [vid, of] of Object.entries(variants)) {
    const o = origins[vid];
    const img = imageIds[vid] ? assets.image(imageIds[vid]) : undefined;
    if (!o || !img) continue;
    varSpec[vid] = { of, bbox: [o[0], o[1], o[0] + img.naturalWidth, o[1] + img.naturalHeight] };
  }
  const attachRaw = cfg.attach ? assets.getJson<Record<string, unknown>>(cfg.attach) : undefined;
  const attach: AttachJson | undefined = attachRaw ? (attachRaw.points ? Object.fromEntries(Object.entries(attachRaw.points as Record<string, { part: string; master_px?: [number, number] }>)
    .map(([k, v]) => [k, { part: v.part, px: v.master_px }])) as AttachJson : attachRaw as AttachJson) : undefined;
  const res = buildImageRig({
    id, parts, height: cfg.height, stringArm: cfg.stringArm, kneeLeg: cfg.kneeLeg, attach, image: lookup, variants: varSpec,
    seamJoints: fixed ? [] : undefined,
  });
  if (missing.length > 3) { report.push(`${id}：分件圖缺 ${missing.join('、')}`); return null; }
  if (missing.length) report.push(`${id}：分件圖缺 ${missing.join('、')}（其餘照常）`);
  const rig = new Rig(res.spec, { renderOrderBase: orderBase, seed: 1, alphaToCoverage: a2c });
  // 臉部換片：一般頭（笑）用退路換片（眨眼）；困惑頭（head_worried）用正式換片（face.json 的基準圖）
  const faces = new Map<string, FaceRig>();
  const faceCfg = cfg.face ? parseFaceJson(assets.getJson(cfg.face)) : undefined;
  const fb = cfg.fallbackFace ? fallbackFaces[cfg.fallbackFace] : undefined;
  for (const pid of ['head', ...Object.keys(varSpec).filter((v) => varSpec[v].of === 'head')]) {
    if (!rig.has(pid)) continue;
    const part = rig.part(pid);
    const hp = res.headPivotPx, s = res.scale;
    const px2local = (x: number, y: number): [number, number] => [(x - hp[0]) * s, (hp[1] - y) * s];
    const o = origins[pid] ?? [0, 0];
    const local2 = (x: number, y: number): [number, number] => px2local(x + o[0], y + o[1]); // 換片座標是該頭部圖的像素
    const useImages = !!faceCfg && faceCfg.baseImage === imageIds[pid];
    const f = new FaceRig(id, part.pivot, useImages ? local2 : px2local, s, {
      config: useImages ? faceCfg : undefined, fallback: useImages ? undefined : fb, baseImage: useImages ? undefined : lookup(pid, pid)?.img,
      baseId: imageIds[pid], source: { image: (fid) => assets.image(fid) },
      renderOrder: orderBase + 1 + part.spec.z + 1, zBase: part.spec.z * Z_STEP + 0.003,
    });
    faces.set(pid, f);
  }
  const modes = [...faces.entries()].map(([k, f]) => `${k}=${f.mode === 'images' ? '正式換片' : f.mode === 'fallback' ? '退路換片' : '無'}`);
  if (modes.length) report.push(`${id}：臉部 ${modes.join('、')}`);
  if (assets.isFallback(`${prefix}torso`)) report.push(`${id}：分件圖來自退路來源 ${assets.source(`${prefix}torso`).replace(/\/[^/]*$/, '/')}`);
  const perf = new RigPerformer(place, rig, 'front', faces.get('head') ?? null, orderBase, { seatHip: cfg.seatHip });
  perf.heads = faces;
  return perf;
}

function buildStandee(id: string, place: ActorPlacement, cfg: StandeeCharConfig, assets: AssetStore, orderBase: number, a2c: boolean, report: string[], fallbackFaces: Record<string, FallbackFace>): Performer | null {
  const poses: Record<string, StandeePoseConfig> = {};
  for (const [k, v] of Object.entries(cfg.poses)) poses[k] = typeof v === 'string' ? { image: v } : v;
  const actor = new StandeeActor({ id, height: cfg.height, poses, defaultPose: cfg.defaultPose ?? Object.keys(poses)[0], edge: cfg.edge }, (iid) => assets.image(iid), {
    renderOrderBase: orderBase, alphaToCoverage: a2c, faceConfig: cfg.face ? parseFaceJson(assets.getJson(cfg.face)) : undefined,
    fallbackFaces, faceImage: (fid) => assets.image(fid),
  });
  if (!actor.ready) { report.push(`${id}：立牌圖全部找不到（${actor.missing.join('、')}）`); return null; }
  if (actor.missing.length) report.push(`${id}：缺姿勢圖 ${actor.missing.join('、')}`);
  const modes = [...actor.poses.values()].map((p) => `${p.name}=${p.face?.mode === 'images' ? '正式換片' : p.face?.mode === 'fallback' ? '退路換片' : '無'}`);
  report.push(`${id}：臉部 ${modes.join('、')}`);
  return new StandeePerformer(place, actor);
}

/** 換段落時把紙偶的 renderOrder 移到段落內的位置（段落名冊第 j 個角色＝actors.order＋j×actorStride；G4 名冊順序不變） */
const ORDER_BASE = new WeakMap<object, number>();
export function retargetOrder(p: AnyPerformer, poolBase: number, base: number): void {
  const cur = ORDER_BASE.get(p) ?? poolBase;
  const d = base - cur;
  if (!d) return;
  p.root.traverse((o) => { o.renderOrder += d; });
  ORDER_BASE.set(p, base);
}
