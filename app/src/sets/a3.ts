// 第三幕（a3）的景。G5 第三幕代理。
//   a3_arcade    紙燈節當天早上的騎樓上學路（a3_c001–a3_c002）：沿用 square 的 layout.json（拿掉長椅、早晨清亮的色彩分級），
//                再疊上第一幕同一套的紅磚柱、騎樓小燈籠串、邀請者的手（chr-inviter_hand-box，只有手與貼紙盒，從柱子後面＝畫面左緣伸出），
//                以及 a3_c002 的回想小圓窗（第二幕 a2_c002 被操偶線拉偏的手，褪色、手撕紙框；不含阿樂叔叔的臉）。
//   a3_gate      早上的校門口（a3_c003）：import gate.ts 的建構器（不改它），拿掉停在對面的小貨車（早上叔叔還沒來）。
//   a3_card      台口前緣的練習卡（a3_c004–a3_c007）：同一個校門口底景＋台口前緣立起的大紙卡（拒絕句＋口訣四格，字是程式排版的
//                Noto Sans TC 粗體，見 review/G5/a3/scripts/build_a3_art.py）。題卡出題時紙卡收平（不和 DOM 題卡疊字）。
//   a3_classroom 教室午後（a3_c008）：程式繪製的剪紙教室（後牆三扇窗、窗外對面騎樓屋頂與燈籠串輕擺、黑板只有粉筆畫沒有字、
//                講桌、課桌、後排同學的背影）；林老師走出教室時手上拿著手機（沿用 gate 的手機小道具圖）。
// 每格 update 只依（cue、cue 內秒數、鏡頭）決定畫面＝時間的純函式；動作時間錨在台詞上（配音長度改了會跟著移）。
import {
  CanvasTexture, Color, Group, Mesh, MeshBasicMaterial, MeshStandardMaterial, PlaneGeometry, Vector3, type Material, type Object3D,
} from 'three';
import { buildImageSet, readLayout, type SetLayout } from './imageSet';
import { buildGate } from './gate';
import { finishTexture, makeCanvas } from '../stage/paper';
import { LAYER, type CameraPreset } from '../stage/layers';
import { clamp, lerp } from '../util/math';
import { imagePiece, lineTime, placeOnCamera, screenLayer, sine01 } from './workshop_a0';
import type { BuiltSet, SetContext, SetEntry } from './types';

const C = (pos: [number, number, number], target: [number, number, number], fov = 20): CameraPreset => ({ pos, target, fov });

// ───────────────────────────── 鏡位 ─────────────────────────────
export const A3_ARCADE_CAMERAS: Record<string, CameraPreset> = {
  /** 騎樓跟拍起點（孩子往右走、紙飛機在前面帶路） */
  a3_follow0: C([-2.5, 1.4, 12.6], [-2.5, 1.15, 0]),
  /** 騎樓跟拍終點（孩子停下） */
  a3_follow1: C([-1.1, 1.4, 12.6], [-1.1, 1.15, 0]),
  /** 邀請者的手（左緣入畫、紅磚柱）＋兩個孩子 */
  a3_hand: C([-2.9, 1.4, 11.6], [-2.9, 1.15, 0]),
  /** 小宇近景（左邊看得到盒子；回想小窗在左上） */
  a3_xy_close: C([-2.15, 1.7, 9.4], [-2.15, 1.5, 0]),
  /** 兩人轉身往右走出畫面（紅磚柱在左，手慢慢縮回柱子後面） */
  a3_leave: C([-1.2, 1.5, 15.2], [-1.2, 1.25, 0]),
};
export const A3_GATE_CAMERAS: Record<string, CameraPreset> = {
  /** 校門口中景（校內在右）：林老師在校門內迎接，孩子從左邊走進來；品安從後面快步走過 */
  a3_gate_in: C([3.15, 1.5, 14.2], [3.15, 1.25, 0]),
  /** 台口全景（練習卡，不轉暗） */
  a3_apron: C([0, 1.9, 21.5], [0, 1.75, 0]),
  /** 台口全景（稍遠；Q4 點燈後從題卡鏡位回來，推近幅度小，練習卡的字不會快速掃過畫面） */
  a3_apron_far: C([0, 2.5, 27.5], [0, 2.15, 0]),
  /** 修正第 1 輪：練習卡近一級（a3_c004–a3_c005 開頭）：兩個示範的孩子在卡的左右兩邊、比 a3_apron 大約 1.3 倍；
   *  題卡模式折折的統一位置（x −4.7、z 4.15）剛好在左下角畫面內 */
  a3_apron2: C([-0.6, 1.85, 18.9], [-0.6, 1.7, 0]),
};
export const A3_CLASSROOM_CAMERAS: Record<string, CameraPreset> = {
  /** 教室中景：窗（燈籠串）在孩子身後、林老師在右邊的黑板前 */
  a3_cls_mid: C([-0.6, 1.75, 17.0], [-0.6, 1.45, 0]),
  /** 修正第 1 輪：兩個孩子＋地上的折折三人中景（頭到腳都在畫面裡；取代原來的兩人近景＋只拍到腿的折折插鏡） */
  a3_cls_trio: C([-2.1, 1.45, 9.4], [-2.1, 1.3, 0.3]),
  /** 林老師與小晴中景（林老師最後從這個鏡頭往右走出畫面） */
  a3_cls_lin: C([-1.0, 1.75, 12.6], [-1.0, 1.55, 0]),
  /** 結尾：兩個孩子轉頭看著窗外輕擺的燈籠串 */
  a3_cls_end: C([-2.4, 2.3, 9.0], [-2.85, 2.45, -3.6]),
};

// ───────────────────────────── 位置（世界座標） ─────────────────────────────
const PILLAR = { x: -5.75, z: 0.9, w: 1.15 };
/** 修正第 1 輪（美術 a3 第 3 項）：手和盒子往左下退（約 80 px）、稍微縮小；圖改用第三幕副本（拿掉盒角灰色短棒、彩度 −15%） */
const HAND = { y: 0.88, z: 0.74, w: 2.15, xHide: -7.0, xOut: -4.85 };
const COOL = new Color('#9aa8c4');
/** 回想小圓窗在 a3_xy_close 畫面上的位置（中心、佔畫面高） */
const MEM = { cx: -0.226, cy: 0.193, h: 0.32 };
const CARD = { z: 3.05, w: 6.0, lift: 0.6 };
/** 林老師站姿（stand）畫面右側那隻手（立牌身體座標；同 gate.ts 的 LIN_HAND） */
const LIN_HAND: [number, number] = [0.288, 1.462];

/** 手周圍略偏冷的柔光（徑向漸層，半透明；同第一幕） */
function coolGlow(): CanvasTexture {
  const S = 256;
  const [c, g] = makeCanvas(S, S);
  const grd = g.createRadialGradient(S / 2, S / 2, 4, S / 2, S / 2, S / 2);
  grd.addColorStop(0, 'rgba(255,255,255,1)');
  grd.addColorStop(0.55, 'rgba(255,255,255,0.55)');
  grd.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grd;
  g.fillRect(0, 0, S, S);
  return finishTexture(new CanvasTexture(c));
}

const deepCopy = <T>(o: T): T => JSON.parse(JSON.stringify(o)) as T;
const lineSpan = (tl: Parameters<typeof lineTime>[0], id: string, s0: number, s1: number): [number, number] => [lineTime(tl, [id], 'start', s0), lineTime(tl, [id], 'end', s1)];

// ═══════════════════════════════════════════ a3_arcade ═══════════════════════════════════════════
function buildArcade(ctx: SetContext): BuiltSet {
  const src = readLayout(ctx, 'square');
  const layout: SetLayout = src ? deepCopy(src) : { format: 'antidrug-set/1' };
  layout.layers = (layout.layers ?? []).filter((l) => l.id !== 'prop-bench');      // 上學路：沒有長椅（品安不在）
  layout.grade = { tint: '#fdf6e8', saturation: 0.88 };                           // 早晨清亮（比第一幕放學後的暖色淡一點）
  layout.cameras = { ...(layout.cameras ?? {}), ...A3_ARCADE_CAMERAS };
  const base = buildImageSet({ ...ctx, name: 'square' }, layout);
  const group = base.group;
  group.name = 'set:a3_arcade';
  const mats: Material[] = [...(base.materials ?? [])];
  const report = [...(base.report ?? [])];
  const im = (id: string): HTMLImageElement | undefined => { const i = ctx.image(id); if (!i) report.push(`景 a3_arcade：缺圖 ${id}`); return i; };
  const add = (m: Mesh | null, x: number, y: number, z: number): Mesh | null => { if (m) { m.position.set(x, y, z); group.add(m); } return m; };

  add(imagePiece(im('sets/square_a1/garland'), { w: 9.0, pivot: [0.5, 1], order: LAYER.mid.order - 40, emissive: 0.15 }, mats), -1.7, 3.62, -1.5);
  add(imagePiece(im('sets/square_a1/pillar'), { w: PILLAR.w, order: LAYER.mid.order + 60, shadow: true }, mats), PILLAR.x, -0.03, PILLAR.z);
  // 邀請者的手＋貼紙盒（不降彩；固定反光，不閃）
  const handMats: Material[] = [];
  // 第三幕副本 sets/a3_arcade/handbox（review/G5/a3/scripts/build_a3_fix1_art.py：拿掉盒子右上角的灰色短棒與白色圓錐紙角——安全界線第 3 條、
  // 彩度 −15%——美術 a3 第 3 項）；缺圖才退回第一幕共用的 chr-inviter_hand-box
  const handImg = ctx.image('sets/a3_arcade/handbox') ?? im('chr-inviter_hand-box');
  if (!ctx.image('sets/a3_arcade/handbox')) report.push('景 a3_arcade：缺圖 sets/a3_arcade/handbox（退回 chr-inviter_hand-box）');
  const hand = add(imagePiece(handImg, { w: HAND.w, order: LAYER.mid.order + 55, shadow: true }, handMats), HAND.xHide, HAND.y, HAND.z);
  const glowMat = new MeshBasicMaterial({ map: coolGlow(), color: COOL, transparent: true, opacity: 0, depthWrite: false });
  const glow = new Mesh(new PlaneGeometry(4.6, 4.0), glowMat);
  glow.position.set(-5.3, 1.7, 0.5);
  glow.renderOrder = LAYER.mid.order + 50;
  glow.visible = false;
  group.add(glow);
  // 回想小圓窗（畫面疊層）
  const memImg = im('sets/a3_arcade/memory');
  const memTex = memImg ? finishTexture(new CanvasTexture(memImg)) : null;
  const mem = memTex ? screenLayer(memTex, 9002) : null;
  if (mem) group.add(mem);

  const baseUpdate = base.update;
  return {
    ...base, group, materials: mats, report,
    cameras: { ...(base.cameras ?? {}), ...A3_ARCADE_CAMERAS },
    update(o) {
      baseUpdate?.(o);
      const { tl, t, camera } = o;
      const id = tl.cue.id;
      // ---- 邀請者的手：a3_c001 _03 前從柱子後面伸出、「再給你看看」往前遞一點；a3_c002 孩子走遠後慢慢縮回柱子後面（不追）
      let out = 0, bob = 0, push = 0;
      if (id === 'a3_c001') {
        const s3 = lineTime(tl, ['a3_c001_03'], 'start', 11);
        out = sine01((t - (s3 - 1.4)) / 1.4);
        push = sine01((t - (s3 + 0.5)) / 1.0);
        for (const l of ['a3_c001_03', 'a3_c001_04']) {
          const [a, b] = lineSpan(tl, l, -9, -9);
          if (t > a && t < b + 0.4) bob = Math.max(bob, Math.sin(Math.PI * clamp((t - a) / (b - a + 0.4))));
        }
      } else if (id === 'a3_c002') {
        push = 1 - sine01((t - (lineTime(tl, ['a3_c002_02'], 'end', 7) + 0.2)) / 1.2);   // 拒絕之後手停在原地、不再往前
        out = 1 - sine01((t - (lineTime(tl, ['a3_c002_03'], 'end', 9) + 2.0)) / 1.6);
      }
      if (hand) {
        hand.visible = out > 0.002;
        hand.position.x = lerp(HAND.xHide, HAND.xOut, out) + 0.3 * push;
        hand.position.y = HAND.y + 0.035 * Math.sin(Math.PI * 2 * 0.9 * t) * bob;
        hand.rotation.z = 0.025 * bob * Math.sin(Math.PI * 2 * 0.45 * t);
      }
      glow.visible = out > 0.002;
      glowMat.opacity = 0.24 * out;
      // ---- 回想小圓窗（a3_c002）：開始後 0.8 秒打開、「我想一想」說完 0.4 秒後收起（各 0.45 秒，淡入淡出＋微微放大）
      if (mem) {
        let v = 0;
        if (id === 'a3_c002') {
          const e1 = lineTime(tl, ['a3_c002_01'], 'end', 3.5);
          v = sine01((t - 0.8) / 0.45) * (1 - sine01((t - (e1 + 0.4)) / 0.45));
        }
        mem.visible = v > 0.002;
        if (mem.visible) {
          // 修正第 1 輪（美術 a3 第 4 項）：往右下移、稍微縮小，不壓到畫面上緣的騎樓串燈（也不碰到下面的盒子）
          placeOnCamera(mem, camera, MEM.cx, MEM.cy, MEM.h * (0.92 + 0.08 * v), 1, 0.8);
          (mem.material as MeshBasicMaterial).opacity = v;
        }
      }
    },
  };
}

// ═══════════════════════════════════════════ a3_gate／a3_card ═══════════════════════════════════════════
function buildMorningGate(ctx: SetContext, withCard: boolean): BuiltSet {
  const base = buildGate({ ...ctx, name: 'gate' });
  const group = base.group;
  group.name = withCard ? 'set:a3_card' : 'set:a3_gate';
  const report = [...(base.report ?? [])];
  // 早上小貨車還沒來：拿掉 layout 裡停在對面的小貨車（連輪子）
  const truck = base.pieces?.find((p) => p.name === 'prop-truck');
  const detached: Object3D[] = [];
  if (truck) { truck.hinge.parent?.remove(truck.hinge); detached.push(truck.hinge); }
  const pieces = (base.pieces ?? []).filter((p) => p.name !== 'prop-truck');
  // 練習卡（台口前緣，以底邊為鉸鏈立起；字是程式排版，見 build_a3_art.py）
  let hinge: Group | null = null;
  let cardMat: MeshStandardMaterial | null = null;
  const ownMats: Material[] = [];
  if (withCard) {
    const img = ctx.image('sets/a3_gate/card');
    if (!img) report.push('景 a3_card：缺圖 sets/a3_gate/card');
    const own: Material[] = ownMats;
    const card = imagePiece(img, { w: CARD.w, order: LAYER.fore.order + 20, emissive: 0.22, shadow: true }, own);
    if (card) {
      hinge = new Group();
      hinge.name = 'pop:a3-card';
      hinge.position.set(0, 0.01, CARD.z);
      card.position.y = CARD.lift;
      hinge.add(card);
      // 牛皮紙底座（紙卡架高：字離字幕區遠一點；題卡模式時整張紙卡在 DOM 題卡後面）
      const baseMat = new MeshStandardMaterial({ color: '#b48c62', roughness: 1, metalness: 0 });
      own.push(baseMat);
      const base = new Mesh(new PlaneGeometry(CARD.w - 0.5, CARD.lift + 0.06), baseMat);
      base.position.set(0, (CARD.lift + 0.06) / 2, -0.012);
      base.renderOrder = LAYER.fore.order + 19;
      base.castShadow = true;
      hinge.add(base);
      hinge.visible = false;
      group.add(hinge);
      cardMat = card.material as MeshStandardMaterial;
    }
  }

  const baseUpdate = base.update;
  return {
    ...base, group, pieces, report,
    cameras: { ...(base.cameras ?? {}), ...A3_GATE_CAMERAS },
    dispose() {
      base.dispose?.();
      for (const o of detached) o.traverse((m) => { const mm = m as Mesh; if (mm.isMesh) { mm.geometry.dispose(); const mt = mm.material as MeshStandardMaterial; mt.map?.dispose(); mt.dispose(); } });
      if (cardMat) { cardMat.map?.dispose(); cardMat.dispose(); }
      for (const m of ownMats) m.dispose();
    },
    update(o) {
      baseUpdate?.(o);
      if (!hinge) return;
      const { tl, t } = o;
      const id = tl.cue.id;
      // 立起：a3_c004 折折攤開小紙卡之後（1.6 秒起 0.9 秒，略過頭再回正）。a3_c005 出題：開頭 fade.out 全暗（0.6 秒）時收平
      //（修正第 1 輪：畫面黑著時收，看不到變化；不和 DOM 題卡疊字）；a3_c006、a3_c007 收著
      let up = 0;
      if (id === 'a3_c004') {
        const u = clamp((t - 1.6) / 0.9);
        up = u <= 0 ? 0 : Math.min(1.03, (1 - Math.pow(1 - u, 3)) * 1.03) - Math.max(0, (u - 0.75) / 0.25) * 0.03;
      } else if (id === 'a3_c005') up = t < 0.6 ? 1 : 0;
      hinge.visible = up > 0.004;
      hinge.rotation.x = -(1 - Math.min(1, up)) * Math.PI / 2 + Math.max(0, up - 1) * 0.6;
    },
  };
}

// ═══════════════════════════════════════════ a3_classroom ═══════════════════════════════════════════
const CLASSROOM_LAYOUT: SetLayout = {
  format: 'antidrug-set/1',
  title: '教室（午後）',
  // 窗外：午後天空＋對面騎樓屋頂（背牆三扇窗挖空，從窗洞看出去）
  wall: { image: 'outside', width: 24, y: -1.6, z: -5.0, emissive: 0.5 },
  floor: { image: 'floor', repeat: [1, 1], width: 32, depth: 15, z: 10 },
  layers: [
    { id: 'backwall', image: 'backwall', x: 0, y: 0, z: -3.6, width: 24, layer: 'far', emissive: 0.3, thick: 0 },
    { id: 'board', image: 'board', x: 2.35, y: 1.0, z: -3.55, width: 4.2, layer: 'far', order: 20, emissive: 0.15 },
    { id: 'students', image: 'students', x: 6.4, y: 0, z: -2.6, width: 6.2, layer: 'far', order: 30, emissive: 0.15 },
    { id: 'desk-a', image: 'desk', x: -5.0, y: 0, z: -1.6, width: 1.7, layer: 'mid', order: 1 },
    { id: 'desk-b', image: 'desk', x: -3.1, y: 0, z: -1.6, width: 1.7, layer: 'mid', order: 2 },
    { id: 'desk-c', image: 'desk', x: -1.2, y: 0, z: -1.6, width: 1.7, layer: 'mid', order: 3 },
    { id: 'desk-d', image: 'desk', x: 4.6, y: 0, z: -1.7, width: 1.7, layer: 'mid', order: 4 },
    { id: 'desk-e', image: 'desk', x: 6.6, y: 0, z: -1.7, width: 1.7, layer: 'mid', order: 5 },
    { id: 'teacherdesk', image: 'teacherdesk', x: 2.9, y: 0, z: -1.0, width: 1.6, layer: 'mid', order: 8 },
  ],
  grade: { preset: 'classroom_afternoon' },
  light: { key: [-9, 11, 14], keyColor: '#ffe9cc' },
};

function buildClassroom(ctx: SetContext): BuiltSet {
  const layout = deepCopy(CLASSROOM_LAYOUT);
  layout.cameras = { ...A3_CLASSROOM_CAMERAS };
  const base = buildImageSet({ ...ctx, name: 'a3_classroom' }, layout);
  const group = base.group;
  const mats: Material[] = [...(base.materials ?? [])];
  const report = [...(base.report ?? [])];
  const im = (id: string): HTMLImageElement | undefined => { const i = ctx.image(id); if (!i) report.push(`景 a3_classroom：缺圖 ${id}`); return i; };
  // 窗外的燈籠串（吊點在左上；輕輕擺動，週期 3.4 秒、幅度很小）
  const garlands: { m: Mesh; ph: number }[] = [];
  for (const [x, y, ph] of [[-3.6, 3.32, 0], [-3.4, 2.92, 1.9]] as [number, number, number][]) {
    const m = imagePiece(im('sets/a3_classroom/garland'), { w: 6.4, pivot: [0.5, 1], order: LAYER.backdrop.order + 5, emissive: 0.35 }, mats);
    if (!m) continue;
    m.position.set(x, y, -4.3 + ph * 0.05);
    group.add(m);
    garlands.push({ m, ph });
  }
  // 林老師的手機（gate 的小道具圖；a3_c008 走出教室時拿在手上）
  const phone = imagePiece(im('sets/gate/set-gate_a4-phone'), { w: 0.13, pivot: [0.5, 0.55], order: LAYER.actors.order + 200 }, mats);
  if (phone) { phone.visible = false; group.add(phone); }
  const tmp = new Vector3();

  const baseUpdate = base.update;
  return {
    ...base, group, materials: mats, report,
    cameras: { ...(base.cameras ?? {}), ...A3_CLASSROOM_CAMERAS },
    update(o) {
      baseUpdate?.(o);
      const { tl, t } = o;
      for (const g of garlands) g.m.rotation.z = 0.018 * Math.sin((t / 3.4) * Math.PI * 2 + g.ph) + 0.006 * Math.sin((t / 2.1) * Math.PI * 2 + g.ph * 2);
      if (phone) {
        const on = tl.cue.id === 'a3_c008' && t >= lineTime(tl, ['a3_c008_04'], 'end', 30) + 0.5;
        const scene = group.parent?.parent ?? null;
        const lin = on ? scene?.getObjectByName('standee:lin') : null;
        phone.visible = !!lin && lin.visible;
        if (phone.visible && lin) {
          const body = lin.children[0];
          body.updateWorldMatrix(true, false);
          tmp.set(LIN_HAND[0], LIN_HAND[1], 0.06).applyMatrix4(body.matrixWorld);
          phone.position.copy(tmp);
          phone.rotation.z = 0.15;
        }
      }
    },
  };
}

export const A3_ARCADE: SetEntry = { title: '騎樓上學路（第三幕，早上）', cameras: A3_ARCADE_CAMERAS, build: buildArcade };
export const A3_GATE: SetEntry = { title: '校門口（第三幕，早上）', cameras: A3_GATE_CAMERAS, build: (ctx) => buildMorningGate(ctx, false) };
export const A3_CARD: SetEntry = { title: '台口前緣的練習卡（第三幕）', cameras: A3_GATE_CAMERAS, build: (ctx) => buildMorningGate(ctx, true) };
export const A3_CLASSROOM: SetEntry = { title: '教室午後（第三幕）', cameras: A3_CLASSROOM_CAMERAS, build: buildClassroom };
