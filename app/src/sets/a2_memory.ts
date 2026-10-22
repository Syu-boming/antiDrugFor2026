// a2_memory：第二幕 a2_c003「那個小盒子」——小晴近景＋褪色回想小窗（a2 代理）。盒子特寫 v02＝a1_c003 盒子特寫貼圖（含灰線頭）＋輕微褪色（build_a2_art.py mem_box_v2）。
// 底景用 assets/final/sets/a2_memory/layout.json（燈籠店背牆、地板）；小窗兩張紙卡（盒子特寫／撕破的包裝紙與一團線）
// 由這裡依台詞時間開合、翻面：
//   - 開：a2_c003_01 開始時，紙卡從平躺往上立起（0.9 秒，略過頭再回正，同 set.popup 的紙片；G5 修正第 1 輪：避開換場漸亮的同一秒，細格光敏）
//   - 翻面：a2_c003_02 開始後 3.0 秒（「裡面卻可能加了毒品」之前），水平壓扁到 55% 時硬切換圖再展開（0.3 秒，同立牌翻面，不交叉淡化）
// update 是時間的純函式（只依 cue 秒數與台詞時間），重播、跳轉都是同一格。
// G6 修正第 1 輪：全劇的 a2_c003 改用 a2_shop 裡的同一個回想小台（MEM_X，見 a2_shop.ts 第 5 項；同一間店，鏡頭直接切、不經過全黑），
// 這個景保留給單獨預覽；紙卡開合、翻面由 memoryCardsUpdater 共用。
import type { Object3D } from 'three';
import { buildImageSet, readLayout } from './imageSet';
import type { SetEntry } from './types';
import { clamp, ease } from '../util/math';

export const A2_MEMORY_CAMERAS = { a2_memory_cu: { pos: [1.05, 2.02, 8.6] as [number, number, number], target: [1.05, 1.92, 0] as [number, number, number], fov: 20 } };

function lineStart(tl: { lines: { line: { id: string }; start: number }[] }, id: string, fallback: number): number {
  const l = tl.lines.find((x) => x.line.id === id);
  return l ? l.start : fallback;
}

/**
 * 回想小窗兩張紙卡的開合與翻面（G6 修正第 1 輪抽出來：a2_shop 把同一個回想小台建在 MEM_X，a2_c003 改用鏡頭直接切，
 * 不再換景經過全黑；兩邊共用這一段，畫面相同）。group＝裡面有 pop:memBox、pop:memWrapper 的群組。
 */
export function memoryCardsUpdater(group: Object3D): (o: { tl: { lines: { line: { id: string }; start: number }[] }; t: number }) => void {
  const cardA = group.getObjectByName('pop:memBox') as Object3D | undefined;
  const cardB = group.getObjectByName('pop:memWrapper') as Object3D | undefined;
  return ({ tl, t }) => {
    const open0 = lineStart(tl, 'a2_c003_01', 1.5);
    const flip0 = lineStart(tl, 'a2_c003_02', 6) + 3.0;
    // 開：從往後平躺（-90°）立起，略過頭再回正
    const u = clamp((t - open0) / 0.9);
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
}

export const A2_MEMORY: SetEntry = {
  title: '回想小窗（第二幕）',
  cameras: A2_MEMORY_CAMERAS,
  build(ctx) {
    const layout = readLayout(ctx, 'a2_memory');
    if (!layout) throw new Error('缺 sets/a2_memory/layout');
    const base = buildImageSet(ctx, layout);
    base.cameras = { ...A2_MEMORY_CAMERAS, ...(base.cameras ?? {}) };
    base.update = memoryCardsUpdater(base.group);
    return base;
  },
};
