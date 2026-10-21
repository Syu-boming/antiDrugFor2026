// 第一幕（a1）的小鎮廣場：沿用 square 的 layout.json（buildImageSet），再疊上第一幕的程式景片。G5 開場＋第一幕代理。
//   - 騎樓下的小燈籠串、遠景布置的鎮民剪影（中性、沒有五官）
//   - 畫面左側的紅磚柱子；邀請者的手（chr-inviter_hand-box，只有手與貼紙盒，從柱子後面＝畫面左側伸出）＋手周圍略偏冷的柔光（FX8）
//   - 盒子特寫小窗（a1_c003「找找看 1」：老師指得到貼紙一層蓋一層、邊角翹起、一小截灰色線頭、沒有任何說明）
//   - 被風吹來的撕破包裝紙（a1_c008，FX12）；燈籠店門面與窗內阿樂叔叔的剪影（FX10：舉竹篾 → 手往旁一歪 → 竹篾落下；看不到線）
// 每格 update 只依（cue、cue 內秒數、鏡頭）決定畫面＝時間的純函式；動作時間錨在台詞上。
// 素材：assets/final/sets/square_a1/*（review/G5/a0/scripts/build_a01_art.py 程式繪製）、chr-inviter_hand-box、props/prop-sticker-box。
import {
  CanvasTexture, Color, DoubleSide, Group, Mesh, MeshBasicMaterial, MeshStandardMaterial, PlaneGeometry, type Material,
} from 'three';
import { buildImageSet, readLayout } from './imageSet';
import { finishTexture, makeCanvas } from '../stage/paper';
import { LAYER, type CameraPreset } from '../stage/layers';
import { clamp, lerp } from '../util/math';
import { imagePiece, lineTime, placeOnCamera, screenLayer, sine01 } from './workshop_a0';
import type { BuiltSet, SetContext, SetEntry } from './types';

const C = (pos: [number, number, number], target: [number, number, number], fov = 20): CameraPreset => ({ pos, target, fov });
export const SQUARE_A1_CAMERAS: Record<string, CameraPreset> = {
  /** 廣場大全景（換景後交代地點：騎樓、燈籠串、遠景布置的鎮民） */
  a1_wide: C([0.4, 2.75, 24.5], [0.4, 2.5, 0]),
  /** 長椅中景：品安坐長椅綁燈籠，孩子從右邊走過來 */
  a1_bench: C([-1.1, 1.72, 13.2], [-1.1, 1.5, 0]),
  /** 紙青蛙跳進燈籠的近景 */
  a1_lantern: C([-1.75, 1.75, 8.6], [-1.75, 1.55, 0]),
  /** 邀請者的手（左緣入畫）＋長椅上的品安＋孩子 */
  a1_hand: C([-2.05, 1.72, 13.0], [-2.05, 1.5, 0]),
  /** 雙人近景（小宇、小晴看盒子） */
  a1_two: C([-1.5, 1.8, 11.2], [-1.5, 1.58, 0]),
  /** 跟拍孩子往右（品安留在畫面左後方） */
  a1_follow: C([-0.6, 1.72, 13.8], [-0.6, 1.5, 0]),
  /** 拒絕後兩人繼續往右：品安留在畫面左後方 */
  a1_follow2: C([0.45, 1.72, 13.8], [0.45, 1.5, 0]),
  /** 往燈籠店的街上 */
  a1_street: C([3.42, 1.72, 13.6], [3.42, 1.5, 0]),
  /** 包裝紙特寫（推近） */
  a1_wrapper: C([2.3, 0.7, 5.6], [2.3, 0.5, 0.9]),
  /** 包裝紙特寫的起點（硬切進來後再慢慢推近到 a1_wrapper） */
  a1_wrapper0: C([2.35, 0.78, 6.5], [2.35, 0.56, 0.9]),
  /** 燈籠店窗前中景 */
  a1_window: C([4.3, 1.95, 12.0], [4.3, 1.78, 0]),
};

// ───────────────────────────── 位置（世界座標） ─────────────────────────────
const PILLAR = { x: -5.75, z: 0.9, w: 1.15 };
const HAND = { y: 1.08, z: 0.74, w: 2.3, xHide: -6.95, xOut: -4.8 };
/** 騎樓最右邊那一間的燈籠店窗（掛在騎樓景片前面） */
const SHOP = { x: 5.0, y: 1.0, z: -1.54, w: 2.5 };
/** 窗框圖的窗洞（世界單位，相對窗框圖左上角；build_a01_art.py 的 window_units_from_topleft） */
const WIN = { x0: 0.147, y0: 0.56, x1: 2.353, y1: 2.24, imgH: 2.547 };
const SIL = { w: 0.9, ppu: 453 * 1.06 / 0.9 };
const WRAP = { w: 0.8, z: 0.95, xStop: 2.65, xFrom: -3.2 };
const COOL = new Color('#9aa8c4');

/** 盒子特寫的紙卡（白色紙卡＋深色細邊＋盒子圖） */
function boxCard(img: HTMLImageElement | undefined): CanvasTexture | null {
  if (!img) return null;
  const pad = 46, W = img.naturalWidth + pad * 2, H = img.naturalHeight + pad * 2;
  const [c, g] = makeCanvas(W + 16, H + 16);
  g.fillStyle = 'rgba(40,28,20,0.28)';
  g.beginPath(); g.roundRect(14, 16, W, H, 22); g.fill();
  g.fillStyle = '#fbf6ec';
  g.beginPath(); g.roundRect(4, 4, W, H, 22); g.fill();
  g.strokeStyle = '#5a4636'; g.lineWidth = 4;
  g.beginPath(); g.roundRect(4, 4, W, H, 22); g.stroke();
  g.strokeStyle = 'rgba(90,70,54,0.35)'; g.lineWidth = 2;
  g.beginPath(); g.roundRect(18, 18, W - 28, H - 28, 14); g.stroke();
  g.drawImage(img, 4 + pad, 4 + pad);
  return finishTexture(new CanvasTexture(c));
}

/** 手周圍略偏冷的柔光（徑向漸層，半透明） */
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

export const SQUARE_A1: SetEntry = {
  title: '小鎮廣場（第一幕：square＋紅磚柱、邀請者的手、盒子特寫、包裝紙、燈籠店窗前）',
  cameras: SQUARE_A1_CAMERAS,
  build(ctx: SetContext): BuiltSet {
    const layout = readLayout(ctx, 'square') ?? { format: 'antidrug-set/1' };
    const base = buildImageSet({ ...ctx, name: 'square' }, layout);
    const group = base.group;
    group.name = 'set:square_a1';
    const mats: Material[] = [...(base.materials ?? [])];
    const report = [...(base.report ?? [])];
    const im = (id: string): HTMLImageElement | undefined => { const i = ctx.image(id); if (!i) report.push(`景 square_a1：缺圖 ${id}`); return i; };
    const add = (m: Mesh | null, x: number, y: number, z: number): Mesh | null => { if (m) { m.position.set(x, y, z); group.add(m); } return m; };

    // 騎樓下的小燈籠串、遠景布置的鎮民
    add(imagePiece(im('sets/square_a1/garland'), { w: 9.0, pivot: [0.5, 1], order: LAYER.mid.order - 40, emissive: 0.15 }, mats), -1.7, 3.62, -1.5);
    add(imagePiece(im('sets/square_a1/townsfolk'), { w: 5.2, order: LAYER.far.order + 30, emissive: 0.5 }, mats), 8.4, -0.06, -2.95);
    // 紅磚柱子（畫面左側）
    add(imagePiece(im('sets/square_a1/pillar'), { w: PILLAR.w, order: LAYER.mid.order + 60, shadow: true }, mats), PILLAR.x, -0.03, PILLAR.z);
    // 邀請者的手＋貼紙盒（不降彩：俗豔的貼紙層就是要看起來很亮；固定反光，不閃）
    const handMats: Material[] = [];
    const hand = add(imagePiece(im('chr-inviter_hand-box'), { w: HAND.w, order: LAYER.mid.order + 55, shadow: true }, handMats), HAND.xHide, HAND.y, HAND.z);
    // 手周圍略偏冷的柔光
    const glowMat = new MeshBasicMaterial({ map: coolGlow(), color: COOL, transparent: true, opacity: 0, depthWrite: false });
    const glow = new Mesh(new PlaneGeometry(4.6, 4.0), glowMat);
    glow.position.set(-5.4, 1.7, 0.5);
    glow.renderOrder = LAYER.mid.order + 50;
    glow.visible = false;
    group.add(glow);

    // 騎樓下燈籠店的窗（窗格挖空）＋窗紙＋窗內剪影
    const shopImg = im('sets/square_a1/shopwindow');
    const shop = add(imagePiece(shopImg, { w: SHOP.w, order: LAYER.mid.order - 20, shadow: false }, mats), SHOP.x, SHOP.y, SHOP.z);
    const shopH = shop && shopImg ? SHOP.w * shopImg.naturalHeight / shopImg.naturalWidth : WIN.imgH;
    const wx = SHOP.x - SHOP.w / 2 + (WIN.x0 + WIN.x1) / 2, ww = WIN.x1 - WIN.x0;
    const wy0 = SHOP.y + shopH - WIN.y1, wy1 = SHOP.y + shopH - WIN.y0;
    const paper = imagePiece(im('sets/square_a1/windowpaper'), { w: ww + 0.16, h: wy1 - wy0 + 0.16, order: LAYER.mid.order - 30, emissive: 0.75 }, mats);
    add(paper, wx, wy0 - 0.08, SHOP.z - 0.035);
    const paperMat = paper?.material as MeshStandardMaterial | undefined;
    const silMat: Material[] = [];
    const sil = new Group();
    sil.position.set(wx + 0.3, wy0 - 0.02, SHOP.z - 0.025);
    group.add(sil);
    const P = SIL.ppu;
    const body = imagePiece(im('sets/square_a1/silbody'), { w: SIL.w, order: LAYER.mid.order - 28, transparent: true }, silMat);
    if (body) sil.add(body);
    const shoulder = new Group();
    shoulder.position.set(-SIL.w / 2 + 83 / P, SIL.w * 857 / 481 - 333 / P, 0.002);
    sil.add(shoulder);
    const arm = imagePiece(im('sets/square_a1/silarm'), { w: 300 / P, pivot: [240 / 300, 1 - 250 / 300], order: LAYER.mid.order - 27, transparent: true }, silMat);
    if (arm) shoulder.add(arm);
    const bamboo = imagePiece(im('sets/square_a1/silbamboo'), { w: 60 / P, pivot: [0.5, 0.5], order: LAYER.mid.order - 26, transparent: true }, silMat);
    const hand0 = { x: (110 - 240) / P, y: (250 - 60) / P };
    if (bamboo) sil.add(bamboo);
    // 窗紙前再一層半透明紙（剪影是投在紙上的影子，邊緣柔一點）
    const veilMat = new MeshStandardMaterial({ color: '#fff0d6', transparent: true, opacity: 0.32, depthWrite: false, side: DoubleSide, roughness: 1, metalness: 0 });
    veilMat.emissive.set('#ffe6bf'); veilMat.emissiveIntensity = 0.35;
    const veil = new Mesh(new PlaneGeometry(ww + 0.1, wy1 - wy0 + 0.1), veilMat);
    veil.position.set(wx, (wy0 + wy1) / 2, SHOP.z - 0.012);
    veil.renderOrder = LAYER.mid.order - 24;
    group.add(veil);
    mats.push(veilMat);

    // 被風吹來的撕破包裝紙（直立的小紙片，像其他景片一樣是一張卡紙）
    const wrapGroup = new Group();
    const wrap = imagePiece(im('sets/square_a1/wrapper'), { w: WRAP.w, pivot: [0.5, 0.08], order: LAYER.actors.order + 150, shadow: true }, handMats);
    if (wrap) wrapGroup.add(wrap);
    wrapGroup.visible = false;
    group.add(wrapGroup);

    // 盒子特寫小窗（畫面疊層）
    const cardTex = boxCard(im('sets/square_a1/boxclose'));
    const card = cardTex ? screenLayer(cardTex, 9002) : null;
    const cardAspect = cardTex ? (cardTex.image as HTMLCanvasElement).width / (cardTex.image as HTMLCanvasElement).height : 1;
    if (card) group.add(card);

    const baseUpdate = base.update;
    return {
      ...base, group, materials: mats, report,
      landmarks: { ...(base.landmarks ?? {}), shopWindow: { x0: wx - ww / 2, x1: wx + ww / 2, y: wy0, z: SHOP.z } },
      cameras: { ...(base.cameras ?? {}), ...SQUARE_A1_CAMERAS },
      update(o) {
        baseUpdate?.(o);
        const { tl, t, camera } = o;
        const id = tl.cue.id;
        // ---- 邀請者的手：a1_c002 從柱子後面伸出；說話時輕輕動；a1_c004「試試看嘛」往前遞；孩子說「不用，我們不要」之後縮回柱子後面
        let out = 0, bob = 0, push = 0;
        if (id === 'a1_c002') {
          out = sine01((t - 0.6) / 1.8);
          for (const l of ['a1_c002_01', 'a1_c002_02']) { const s0 = lineTime(tl, [l], 'start', -9), s1 = lineTime(tl, [l], 'end', -9); if (t > s0 && t < s1 + 0.4) bob = Math.max(bob, Math.sin(Math.PI * clamp((t - s0) / (s1 - s0 + 0.4)))); }
        } else if (id === 'a1_c003') out = 1;
        else if (id === 'a1_c004') {
          const s0 = lineTime(tl, ['a1_c004_01'], 'start', 0), s1 = lineTime(tl, ['a1_c004_01'], 'end', 2);
          if (t > s0 && t < s1 + 0.4) bob = Math.sin(Math.PI * clamp((t - s0) / (s1 - s0 + 0.4)));
          push = sine01((t - s1 + 1.3) / 0.9) * (1 - sine01((t - lineTime(tl, ['a1_c004_02'], 'start', s1 + 1)) / 1.0));
          out = 1 - sine01((t - lineTime(tl, ['a1_c004_04'], 'end', 12) - 0.3) / 1.6);
        }
        if (hand) {
          hand.visible = out > 0.002;
          hand.position.x = lerp(HAND.xHide, HAND.xOut, out) + 0.22 * push;
          hand.position.y = HAND.y + 0.035 * Math.sin(Math.PI * 2 * 0.9 * t) * bob;
          hand.rotation.z = 0.025 * bob * Math.sin(Math.PI * 2 * 0.45 * t);
        }
        glow.visible = out > 0.002;
        glowMat.opacity = 0.26 * out;
        // ---- 盒子特寫小窗：a1_c003 小晴「這盒子上面什麼都沒寫」→ 打開，停到 cue 結束（老師指線索）；a1_c004 一開始收起
        let cv = 0;
        if (id === 'a1_c003') cv = sine01((t - (lineTime(tl, ['a1_c003_02'], 'start', 3) + 0.35)) / 0.5);
        else if (id === 'a1_c004') cv = 1 - sine01((t - 0.25) / 0.5);
        if (card) {
          card.visible = cv > 0.002;
          if (card.visible) {
            placeOnCamera(card, camera, -0.2, 0.09, 0.6 * (0.95 + 0.05 * cv), cardAspect, 0.82);
            (card.material as MeshBasicMaterial).opacity = cv;
          }
        }
        // ---- 包裝紙（a1_c008）：風從左邊吹來，翻滾著停在孩子腳邊
        if (wrap) {
          let vis = false, x = WRAP.xStop, y = 0, rz = 0;
          if (id === 'a1_c008') {
            const t0 = 0.9, dur = 2.6;
            const u = clamp((t - t0) / dur);
            vis = t >= t0;
            const e = 1 - Math.pow(1 - u, 2.2);
            x = lerp(WRAP.xFrom, WRAP.xStop, e);
            y = 0.42 * Math.sin(Math.PI * Math.min(1, u * 1.15)) * (1 - u) + 0.05 * Math.abs(Math.sin(u * Math.PI * 3)) * (1 - u);
            rz = 0.5 * (1 - u) * Math.sin(u * Math.PI * 2.2);
          }
          wrapGroup.visible = vis;
          wrapGroup.position.set(x, y, WRAP.z);
          wrapGroup.rotation.z = rz;
        }
        // ---- 窗內剪影（a1_c008）：舉著竹篾 → 手往旁一歪 → 竹篾輕輕掉下去
        let tilt = 0, fall = 0;
        sil.visible = id === 'a1_c008';      // 剪影只在窗前這一段出現（前面幾段窗裡只有窗紙）
        // 白天的窗紙不發亮（窗格明暗對比小，鏡頭移動時不會一格一格閃過）；窗前這一段屋裡點著燈
        if (paperMat) paperMat.emissiveIntensity = id === 'a1_c008' ? 0.75 : 0.2;
        if (id === 'a1_c008') {
          const td = lineTime(tl, ['a1_c008_02'], 'end', 9) + 5.8;
          tilt = sine01((t - td) / 0.45);
          fall = clamp((t - td - 0.25) / 0.7);
        }
        const th = 0.02 * Math.sin(Math.PI * 2 * 0.22 * t) + 0.62 * tilt;
        shoulder.rotation.z = th;
        if (bamboo) {
          // 手的位置（剪影座標）＝肩膀＋旋轉後的手；竹篾從手上鬆開後往下掉（窗台下方被門面擋住）
          const hx = shoulder.position.x + hand0.x * Math.cos(th) - hand0.y * Math.sin(th);
          const hy = shoulder.position.y + hand0.x * Math.sin(th) + hand0.y * Math.cos(th);
          const g = fall * fall;
          bamboo.position.set(hx - 0.1 * fall, hy - 1.5 * g, 0.004);
          bamboo.rotation.z = 0.25 * tilt + 1.2 * g;
          bamboo.visible = fall < 0.999;
        }
      },
    };
  },
};
