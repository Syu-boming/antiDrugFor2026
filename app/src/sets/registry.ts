// 景的登記表：景名 → 建構器。cue 的 set（或段落檔的 set）用這裡的景名。
// 找景的順序：本表 → 素材裡的 assets/final/sets/<景名>/layout.json（imageSet，資料驅動）→ kraft_stage（佔位景，並在準備畫面提醒）。
//
// 各幕代理新增需要程式的景：
//   1. 新增 app/src/sets/<景名>.ts，匯出 `export const <景名大寫>: SetEntry = { title, build(ctx) { ...; return { group, pieces, ... } } }`
//      （介面見 ./types.ts；可以在 build 裡呼叫 buildImageSet(ctx, layout) 再加自己的程式景片）
//   2. 在下面 import 一行、SET_REGISTRY 加一行（每幕只加自己的行，不要改別人的）
import { buildProscenium, buildWorkshop } from '../stage/sets';
import { buildWorkshopG4 } from '../stage/workshop';
import { KRAFT_STAGE } from './kraftStage';
import { A2_MEMORY } from './a2_memory';   // 第二幕（a2 代理）
import { A2_WINDOW } from './a2_window';   // 第二幕（a2 代理）
import { imageSetEntry, readLayout } from './imageSet';
import { GATE } from './gate';
import { A4_ROADMAP } from './a4_roadmap';
import { WORKSHOP_A0 } from './workshop_a0';
import { SQUARE_A1 } from './square_a1';
import type { BuiltSet, SetContext, SetEntry } from './types';
import type { CameraPreset } from '../stage/layers';

export { buildProscenium };

/** G4 燈籠店立體書景（畫面與 G4 驗收包相同；實作在 src/stage/workshop.ts） */
const WORKSHOP_G4: SetEntry = {
  title: '燈籠店（G4 立體書景）',
  build: (ctx) => {
    const ws = buildWorkshopG4({ alphaToCoverage: ctx.alphaToCoverage, image: (id) => ctx.image(id) });
    return { group: ws.group, pieces: ws.pieces, materials: ws.materials, marks: ws.marks, tableEdge: ws.tableEdge, landmarks: ws.landmarks };
  },
};

/** 技術骨架佔位景（demo.json） */
const WORKSHOP: SetEntry = {
  title: '燈籠工作室（技術骨架佔位景）',
  build: () => {
    const ws = buildWorkshop();
    return { group: ws.group, tableEdge: ws.tableEdge, marks: { ale: { x: -2.2, z: 0 }, xiaoqing: { x: 3.1, z: 0.3 } } };
  },
};

export const SET_REGISTRY: Record<string, SetEntry> = {
  workshop: WORKSHOP,
  workshop_g4: WORKSHOP_G4,
  kraft_stage: KRAFT_STAGE,
  // ---- 各幕代理在這裡加自己的景（一幕一段，註明是哪一幕）
  gate: GATE, // 第四幕代理：校門口（第三、四、五幕共用；layout.json 底景＋第四幕的程式道具，沒寫 setTrack 的 cue 和 layout 原樣相同）
  a4_roadmap: A4_ROADMAP, // 第四幕代理：紙上的路（牛皮紙地圖、小車、背光剪影幕）
  a2_memory: A2_MEMORY, // 第二幕 a2_c003 回想小窗
  a2_window: A2_WINDOW, // 第二幕 a2_c013 店外傍晚（窗內、剪影小窗、筆記本）
  workshop_a0: WORKSHOP_A0, // 開場（a0_c002–a0_c005）：G4 燈籠店＋設計圖、空底座、風鈴、八盞燈、回憶小窗、筆記本
  square_a1: SQUARE_A1, // 第一幕（a1）：廣場（square 的 layout.json）＋紅磚柱、邀請者的手、盒子特寫、包裝紙、燈籠店窗前
};

/** 全劇預設的佔位景 */
export const FALLBACK_SET = 'kraft_stage';

export type SetSource = 'registry' | 'layout' | 'fallback';

/** 找景：登記表 → layout.json → 佔位景 */
export function findSet(name: string, ctx: Pick<SetContext, 'json'>): { entry: SetEntry; source: SetSource } {
  const hit = SET_REGISTRY[name];
  if (hit) return { entry: hit, source: 'registry' };
  const layout = readLayout(ctx, name);
  if (layout) return { entry: imageSetEntry(layout), source: 'layout' };
  return { entry: SET_REGISTRY[FALLBACK_SET], source: 'fallback' };
}

/** 建景（建構失敗時退回佔位景，不讓演出當掉） */
export function buildSet(name: string, ctx: SetContext): { built: BuiltSet; source: SetSource; report: string[] } {
  const { entry, source } = findSet(name, ctx);
  const report: string[] = [];
  if (source === 'fallback') report.push(`景 ${name} 沒有登記也沒有 layout.json，用佔位景 ${FALLBACK_SET}`);
  try {
    const built = entry.build({ ...ctx, name });
    report.push(...(built.report ?? []));
    return { built, source, report };
  } catch (err) {
    report.push(`景 ${name} 建立失敗（${err instanceof Error ? err.message : String(err)}），用佔位景 ${FALLBACK_SET}`);
    return { built: SET_REGISTRY[FALLBACK_SET].build({ ...ctx, name: FALLBACK_SET }), source: 'fallback', report };
  }
}

/** 景的鏡位（不必建景；時間軸算鏡頭時用） */
export function setCameras(name: string, ctx: Pick<SetContext, 'json'>): Record<string, CameraPreset> | undefined {
  return findSet(name, ctx).entry.cameras;
}
