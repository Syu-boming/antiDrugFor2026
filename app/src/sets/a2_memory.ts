// a2_memory：第二幕 a2_c003「那個小盒子」——小晴近景＋褪色回想小窗（a2 代理）。
// 底景用 assets/final/sets/a2_memory/layout.json（燈籠店背牆、地板）；小窗兩張紙卡（盒子特寫／撕破的包裝紙與一團線）
// 由這裡依台詞時間開合、翻面：
//   - 開：a2_c003_01 開始前 0.45 秒，紙卡從平躺往上立起（0.7 秒，略過頭再回正，同 set.popup 的紙片）
//   - 翻面：a2_c003_02 開始後 3.0 秒（「裡面卻可能加了毒品」之前），水平壓扁到 55% 時硬切換圖再展開（0.3 秒，同立牌翻面，不交叉淡化）
// update 是時間的純函式（只依 cue 秒數與台詞時間），重播、跳轉都是同一格。
import type { Object3D } from 'three';
import { buildImageSet, readLayout } from './imageSet';
import type { SetEntry } from './types';
import { clamp, ease } from '../util/math';

const CAMERAS = { a2_memory_cu: { pos: [1.05, 2.02, 8.6] as [number, number, number], target: [1.05, 1.92, 0] as [number, number, number], fov: 20 } };

function lineStart(tl: { lines: { line: { id: string }; start: number }[] }, id: string, fallback: number): number {
  const l = tl.lines.find((x) => x.line.id === id);
  return l ? l.start : fallback;
}

export const A2_MEMORY: SetEntry = {
  title: '回想小窗（第二幕）',
  cameras: CAMERAS,
  build(ctx) {
    const layout = readLayout(ctx, 'a2_memory');
    if (!layout) throw new Error('缺 sets/a2_memory/layout');
    const base = buildImageSet(ctx, layout);
    base.cameras = { ...CAMERAS, ...(base.cameras ?? {}) };
    const cardA = base.group.getObjectByName('pop:memBox') as Object3D | undefined;
    const cardB = base.group.getObjectByName('pop:memWrapper') as Object3D | undefined;
    base.update = ({ tl, t }) => {
      const open0 = lineStart(tl, 'a2_c003_01', 1.5) - 0.45;
      const flip0 = lineStart(tl, 'a2_c003_02', 6) + 3.0;
      // 開：從往後平躺（-90°）立起，略過頭再回正
      const u = clamp((t - open0) / 0.7);
      const up = u <= 0 ? 0 : Math.min(1.04, ease('out', u) * 1.04) - Math.max(0, (u - 0.75) / 0.25) * 0.04;
      const rotX = -(1 - Math.min(1, up)) * Math.PI / 2 + Math.max(0, up - 1) * 0.5;
      // 翻面：0.3 秒，寬度壓到 55% 的那一刻換圖
      const f = clamp((t - flip0) / 0.3);
      const sx = f > 0 && f < 1 ? 1 - 0.45 * Math.sin(Math.PI * f) : 1;
      const showB = t >= flip0 + 0.15;
      for (const [card, on] of [[cardA, !showB], [cardB, showB]] as const) {
        if (!card) continue;
        card.visible = on && up > 0.02;
        card.rotation.x = rotX;
        card.scale.set(sx, 1, 1);
      }
    };
    return base;
  },
};
