// 演員名單：依 cue 檔的 characters（角色 id → { name, rig, x, z, facing }）建立紙偶，不再寫死在程式裡。
// rig 名稱 → 紙偶設定：先查 assets/final/g4_manifest.json 的 characters[角色 id]，再查內建設定（BUILTIN_RIGS）。
// 素材缺少時退回程式佔位紙偶並記在 report（準備畫面與 getState().castReport 都看得到），不當機。
import type { CharacterRoster } from '../types/cue';
import type { AssetStore } from '../data/assets';
import { Rig } from './rig';
import { buildImageRig, partsFromRigJson, type AttachJson, type PartsJson, type RigJsonV04 } from './imagerig';
import { StandeeActor, type StandeePoseConfig } from './standee';
import { FaceRig, FALLBACK_FACES, parseFaceJson } from './face';
import { RIG_ALE, RIG_XIAOQING } from './rigspecs';
import { RigPerformer, StandeePerformer, type Performer } from './perform';
import { LAYER, Z_STEP } from './layers';

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

export type CharConfig = PartsCharConfig | StandeeCharConfig | ProceduralCharConfig;

/** 內建紙偶設定（G4 時的素材位置；正式素材由 g4_manifest.json 覆寫） */
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
};

export interface CastResult { actors: Map<string, Performer>; report: string[]; timings: Record<string, number> }

const baseName = (f: string): string => f.replace(/^.*\//, '').replace(/\.[a-z0-9]+$/i, '').replace(/_v\d+$/i, '');

export function buildCast(roster: CharacterRoster | undefined, assets: AssetStore | null, opts: { alphaToCoverage: boolean; marks?: Record<string, { x: number; z: number }> }): CastResult {
  const actors = new Map<string, Performer>();
  const report: string[] = [];
  const timings: Record<string, number> = {};
  const man = assets?.getJson<{ characters?: Record<string, Partial<CharConfig>> }>('g4_manifest');
  let i = 0;
  for (const [id, entry] of Object.entries(roster ?? {})) {
    const orderBase = LAYER.actors.order + i * LAYER.actorStride;
    i++;
    const mark = opts.marks?.[id];
    const place = { id, x: entry.x ?? mark?.x ?? 0, z: entry.z ?? mark?.z ?? 0, facing: (entry.facing ?? 1) as 1 | -1 };
    const builtin = BUILTIN_RIGS[entry.rig ?? ''] ?? BUILTIN_RIGS[id === 'ale' ? 'adult' : 'child'];
    const over = man?.characters?.[id];
    const cfg = (over ? { ...builtin, ...over } : builtin) as CharConfig;
    const t0 = performance.now();
    let perf: Performer | null = null;
    try {
      if (cfg.rig === 'parts' && assets) perf = buildParts(id, place, cfg, assets, orderBase, opts.alphaToCoverage, report);
      else if (cfg.rig === 'standee' && assets) perf = buildStandee(id, place, cfg, assets, orderBase, opts.alphaToCoverage, report);
    } catch (err) {
      report.push(`${entry.name}（${id}）：素材建立失敗（${err instanceof Error ? err.message : String(err)}），改用佔位紙偶`);
      perf = null;
    }
    if (!perf) {
      const spec = cfg.rig === 'procedural' ? (cfg.spec === 'adult' ? RIG_ALE : RIG_XIAOQING) : (id === 'ale' ? RIG_ALE : RIG_XIAOQING);
      const rig = new Rig({ ...spec, id }, { renderOrderBase: orderBase, seed: i * 1000 });
      perf = new RigPerformer(place, rig, 'side', null, orderBase);
      if (cfg.rig !== 'procedural') report.push(`${entry.name}（${id}）：找不到正式素材，用程式佔位紙偶`);
    }
    timings[id] = performance.now() - t0;
    actors.set(id, perf);
  }
  return { actors, report, timings };
}

function buildParts(id: string, place: { id: string; x: number; z: number; facing: 1 | -1 }, cfg: PartsCharConfig, assets: AssetStore, orderBase: number, a2c: boolean, report: string[]): Performer | null {
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
  const fb = cfg.fallbackFace ? FALLBACK_FACES[cfg.fallbackFace] : undefined;
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

function buildStandee(id: string, place: { id: string; x: number; z: number; facing: 1 | -1 }, cfg: StandeeCharConfig, assets: AssetStore, orderBase: number, a2c: boolean, report: string[]): Performer | null {
  const poses: Record<string, StandeePoseConfig> = {};
  for (const [k, v] of Object.entries(cfg.poses)) poses[k] = typeof v === 'string' ? { image: v } : v;
  const actor = new StandeeActor({ id, height: cfg.height, poses, defaultPose: cfg.defaultPose ?? Object.keys(poses)[0], edge: cfg.edge }, (iid) => assets.image(iid), {
    renderOrderBase: orderBase, alphaToCoverage: a2c, faceConfig: cfg.face ? parseFaceJson(assets.getJson(cfg.face)) : undefined,
    fallbackFaces: FALLBACK_FACES, faceImage: (fid) => assets.image(fid),
  });
  if (!actor.ready) { report.push(`${id}：立牌圖全部找不到（${actor.missing.join('、')}）`); return null; }
  if (actor.missing.length) report.push(`${id}：缺姿勢圖 ${actor.missing.join('、')}`);
  const modes = [...actor.poses.values()].map((p) => `${p.name}=${p.face?.mode === 'images' ? '正式換片' : p.face?.mode === 'fallback' ? '退路換片' : '無'}`);
  report.push(`${id}：臉部 ${modes.join('、')}`);
  return new StandeePerformer(place, actor);
}
