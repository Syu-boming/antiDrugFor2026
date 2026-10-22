// 第六幕 a6_c008 四季（時間轉場，FX11）：固定窗框構圖。G5 第六幕代理。
// 室內一面牆＋一扇大窗（assets/final/sets/a6_window/room，窗洞透明）；窗外是樹與天空，依季節換：秋黃葉 → 冬光禿 → 春新芽 → 夏濃綠。
// 窗內由 cue 的角色演出陪伴（葉護理師陪阿樂叔叔回診說話、阿琴阿姨陪他散步、孩子們帶折折來看他）。
// 換季（修正第 1 輪：不經過黑場）：完整版在 4.6／9.4／14.2 秒各交叉淡換 1.2 秒（後一季疊在前一季上面淡入，窗外亮度單向漸變）；
//       2 級短版（a6_c008_02 被略過）每 2 秒交叉淡換一次（1 秒）。
// 秋天窗外有幾片葉子慢慢飄落（亮度固定、只有位置移動）。全部是時間的純函式。
import { Group, Mesh, MeshStandardMaterial, type Material } from 'three';
import { buildImageSet, readLayout } from './imageSet';
import { imagePiece } from './workshop_a0';
import { LAYER, type CameraPreset } from '../stage/layers';
import { clamp, lerp } from '../util/math';
import { dropped, sine01 } from './a6_square_night';
import type { BuiltSet, SetContext, SetEntry } from './types';

const SEASONS = ['autumn', 'winter', 'spring', 'summer'] as const;
const TREE_IMG: Record<string, string> = { autumn: 'tree-autumn', winter: 'tree-winter', spring: 'tree-spring', summer: 'tree-summer' };
/** 窗洞（世界座標；review/G5/a6/scripts/build_a6_art2.py WIN） */
const WIN = { x0: -1.75, x1: 3.05, y0: 1.3, y1: 4.25 };
const ROOM = { x0: -6.2, w: 13.0, z: -1.2 };

export const A6_WINDOW_CAMERAS: Record<string, CameraPreset> = {
  /** 固定窗框構圖（修正第 1 輪推近：窗框當畫框，地板只留下緣一小條） */
  a6_win: { pos: [0.55, 1.72, 15.0], target: [0.55, 1.92, 0], fov: 20 },
};

export const A6_WINDOW: SetEntry = {
  title: '四季窗景（第六幕 a6_c008：室內窗框＋窗外的樹與天空換季）',
  cameras: A6_WINDOW_CAMERAS,
  build(ctx: SetContext): BuiltSet {
    const layout = readLayout(ctx, 'a6_window') ?? { format: 'antidrug-set/1' };
    const base = buildImageSet({ ...ctx, name: 'a6_window' }, layout);
    const group = base.group;
    group.name = 'set:a6_window';
    const mats: Material[] = [...(base.materials ?? [])];
    const report = [...(base.report ?? [])];
    const im = (n: string): HTMLImageElement | undefined => { const i = ctx.image(`sets/a6_window/${n}`); if (!i) report.push(`景 a6_window：缺圖 ${n}`); return i; };
    const cx = (WIN.x0 + WIN.x1) / 2;
    // 窗外：天空（四張）與樹（四張），每季一組，用透明度切換
    const outside: Record<string, Mesh[]> = {};
    SEASONS.forEach((s, k) => {
      const list: Mesh[] = [];
      const sky = imagePiece(im(`sky-${s}`), { w: 8.6, order: LAYER.backdrop.order + 2 + k, emissive: 0.55, transparent: true }, mats);
      if (sky) { sky.position.set(cx, WIN.y0 - 1.6, -4.4); group.add(sky); list.push(sky); }
      const tree = imagePiece(im(TREE_IMG[s]), { w: 5.2, order: LAYER.far.order + 2 + k, emissive: 0.3, transparent: true }, mats);
      if (tree) { tree.position.set(cx + 1.3, -0.9, -2.9); group.add(tree); list.push(tree); }
      outside[s] = list;
    });
    // 秋天飄落的葉子（窗外）
    const leaves: Mesh[] = [];
    for (let i = 0; i < 6; i++) {
      const leaf = imagePiece(im('leaf'), { w: 0.22, pivot: [0.5, 0.5], order: LAYER.far.order + 12, emissive: 0.3 }, mats);
      if (leaf) { group.add(leaf); leaves.push(leaf); }
    }
    // 室內牆（窗洞透明）
    const roomImg = im('room');
    const room = imagePiece(roomImg, { w: ROOM.w, order: LAYER.mid.order - 40, emissive: 0.28, shadow: true }, mats);
    if (room) { room.position.set(ROOM.x0 + ROOM.w / 2, 0, ROOM.z); room.receiveShadow = true; group.add(room); }
    const shelf = imagePiece(im('shelf'), { w: 1.7, order: LAYER.mid.order - 10, emissive: 0.12, shadow: true }, mats);
    if (shelf) { shelf.position.set(-4.25, 0, -0.95); group.add(shelf); }
    const plant = imagePiece(im('plant'), { w: 1.15, order: LAYER.mid.order - 8, emissive: 0.12, shadow: true }, mats);
    if (plant) { plant.position.set(4.75, 0, -0.75); group.add(plant); }

    const setVis = (s: string, a: number): void => {
      for (const m of outside[s] ?? []) {
        m.visible = a > 0.002;
        const mat = m.material as MeshStandardMaterial;
        mat.opacity = a;
      }
    };
    const leafGroup = new Group();
    group.add(leafGroup);
    const baseUpdate = base.update;
    return {
      ...base, group, materials: mats, report,
      cameras: { ...(base.cameras ?? {}), ...A6_WINDOW_CAMERAS },
      landmarks: { ...(base.landmarks ?? {}), window: { x0: WIN.x0, x1: WIN.x1, y: WIN.y0, z: ROOM.z } },
      update(o) {
        baseUpdate?.(o);
        const { tl, t } = o;
        const short = tl.cue.id === 'a6_c008' && dropped(tl, 'a6_c008_02');
        // 季節：交叉淡換（後一季疊在前一季上面淡入，窗外亮度單向變化）；完整版 4.6／9.4／14.2 秒各 1.2 秒，短版 1.5／3.5／5.5 秒各 1 秒
        let cur = 3, u = 0;
        if (tl.cue.id === 'a6_c008') {
          const at = short ? [1.5, 3.5, 5.5] : [4.6, 9.4, 14.2];
          const dur = short ? 1.0 : 1.2;
          cur = 0;
          for (let k = 1; k < 4; k++) { const p = sine01((t - at[k - 1]) / dur); if (p >= 1) cur = k; else { u = p; break; } }
        }
        SEASONS.forEach((s, k) => setVis(s, k === cur ? 1 : k === cur + 1 ? u : 0));
        // 葉子：秋天（完整版 0–5.4 秒、短版 0–2.3 秒）慢慢飄落，進出畫面時淡入淡出
        const autumnEnd = short ? 2.3 : 5.4;
        leaves.forEach((leaf, i) => {
          const period = 4.2 + (i % 3) * 0.7;
          const ph = ((t + i * 1.37) % period) / period;
          const vis = tl.cue.id === 'a6_c008' && t < autumnEnd;
          leaf.visible = vis;
          if (!vis) return;
          leaf.position.set(lerp(WIN.x0 + 0.5 + i * 0.75, WIN.x0 + 0.1 + i * 0.75, ph) + 0.18 * Math.sin(ph * Math.PI * 3 + i), lerp(WIN.y1 + 0.3, WIN.y0 - 0.2, ph), -2.4);
          leaf.rotation.z = 0.6 * Math.sin(ph * Math.PI * 2 + i);
          (leaf.material as MeshStandardMaterial).opacity = clamp(Math.min(ph / 0.12, (1 - ph) / 0.12, (autumnEnd - t) / 0.6));
          (leaf.material as MeshStandardMaterial).transparent = true;
        });
      },
    };
  },
};
