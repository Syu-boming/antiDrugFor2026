// 第一幕（a1）的小鎮廣場：沿用 square 的 layout.json（buildImageSet），再疊上第一幕的程式景片。G5 開場＋第一幕代理。
//   - 騎樓下的小燈籠串（修正第 1 輪：拿掉半透明灰色的鎮民剪影，裁定 6）
//   - 畫面左側的紅磚柱子；邀請者的手（chr-inviter_hand-box，只有手與貼紙盒，從柱子後面＝畫面左側伸出）
//     ＋手周圍的背景略偏冷、略降彩（FX8：手後面一層冷灰藍半透明紙，右緣漸淡；盒子與手在它前面，不降彩）
//   - 盒子特寫小窗（a1_c003「找找看 1」：老師指得到貼紙一層蓋一層、邊角翹起、一小截灰色線頭、沒有任何說明；放在畫面左上，不蓋住品安）
//   - 被風吹來的撕破包裝紙（a1_c008，FX12：停在孩子身後左下方，離孩子一個身寬以上）；
//     燈籠店門面（修正第 2 輪：窗嵌進店面牆，有屋簷、木柱、店門）與窗內阿樂叔叔的剪影（FX10：兩階深色剪影看得出圍裙與髮型；手垂著 → 舉起竹條 → 手被往旁邊一帶、往左歪 →
//     竹條慢慢落下（在窗內看得到）、窗光漸亮一點；看不到線）。右側行道樹移到窗戶右邊，窗戶整個露出來
// 每格 update 只依（cue、cue 內秒數、鏡頭）決定畫面＝時間的純函式；動作時間錨在台詞上。
// 素材：assets/final/sets/square_a1/*（review/G5/a0/scripts/build_a01_art.py 程式繪製）、chr-inviter_hand-box、props/prop-sticker-box。
import {
  CanvasTexture, Color, Group, Mesh, MeshBasicMaterial, MeshStandardMaterial, PlaneGeometry, type Material,
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
  /** 往燈籠店的街上（修正第 1 輪）：包裝紙停在左下（孩子身後一個身寬以外），右邊已經看得到燈籠店的窗 */
  a1_street2: C([2.2, 1.72, 13.6], [2.2, 1.5, 0]),
  /** 品安回頭看柱子（a1_c004 結尾，a6 秘密的伏筆）：左緣是紅磚柱子，品安在右半 */
  a1_pinan: C([-3.55, 1.6, 9.8], [-3.55, 1.42, 0]),
  /** 包裝紙特寫（推近）：中心是紙邊裡那團灰色紙線，折折在左側三分之一 */
  a1_wrapper: C([-0.46, 0.62, 6.4], [-0.46, 0.32, 1.4]),
  /** 包裝紙特寫的起點（硬切進來後再慢慢推近到 a1_wrapper） */
  a1_wrapper0: C([-0.44, 0.72, 7.3], [-0.44, 0.36, 1.4]),
  /** 燈籠店窗前中景 */
  a1_window: C([4.3, 1.95, 12.0], [4.3, 1.78, 0]),
};

// ───────────────────────────── 位置（世界座標） ─────────────────────────────
const PILLAR = { x: -5.75, z: 0.9, w: 1.15 };
/** 手後面的冷色層（世界座標；右緣 x0→x1 漸淡；在品安〔x −2.75～−2.05〕左邊就淡完） */
const COOLBAND = { xl: -10.5, x0: -3.9, x1: -2.95, y0: -0.3, y1: 6.5, z: 0.4 };
const HAND = { y: 1.08, z: 0.74, w: 2.3, xHide: -6.95, xOut: -4.8 };
/** 騎樓最右邊那一間的燈籠店窗（掛在騎樓景片前面） */
const SHOP = { x: 5.0, y: 1.3, z: -1.54, w: 2.5 };
/** 燈籠店門面牆（修正第 2 輪：窗嵌進店面，不再像獨立立在廣場上的窗框）：在窗紙後面、騎樓柱子前面；
 *  左下角 x 3.35、y −0.07，3.75 × 3.85 單位（review/G5/a0/scripts/build_fix2_art.py） */
const SHOPWALL = { x0: 3.35, y0: -0.07, w: 3.75, z: -1.59 };
/** 窗框圖的窗洞（世界單位，相對窗框圖左上角；build_a01_art.py 的 window_units_from_topleft） */
const WIN = { x0: 0.147, y0: 0.56, x1: 2.353, y1: 2.24, imgH: 2.547 };
const SIL = { w: 0.9, ppu: 453 * 1.06 / 0.9 };
/** 剪影時間（小晴「不要碰…」說完後幾秒）：lit＝走到窗下時窗光 1.2 秒漸亮（鏡頭跟拍平移時窗紙不亮，窗格明暗小）；
 *  raise＝舉起竹條（a1.json 的 sfx_bamboo_drop 對 raise＋2.35） */
export const SIL_T = { lit: 4.4, raise: 5.6 };
const WRAP = { w: 0.8, z: 1.4, xStop: -0.5, xFrom: -4.6, t0: 2.0, dur: 2.0 };
const COOL = new Color('#7c889f');

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

/** 冷色層的透明度：左邊全滿，右緣（COOLBAND.x0→x1）漸淡到 0 */
function coolBand(): CanvasTexture {
  const W = 512;
  const [c, g] = makeCanvas(W, 4);
  const span = COOLBAND.x1 - COOLBAND.xl, f0 = (COOLBAND.x0 - COOLBAND.xl) / span;
  const grd = g.createLinearGradient(0, 0, W, 0);
  grd.addColorStop(0, 'rgba(255,255,255,1)');
  grd.addColorStop(f0, 'rgba(255,255,255,1)');
  grd.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grd;
  g.fillRect(0, 0, W, 4);
  return finishTexture(new CanvasTexture(c));
}

export const SQUARE_A1: SetEntry = {
  title: '小鎮廣場（第一幕：square＋紅磚柱、邀請者的手、盒子特寫、包裝紙、燈籠店窗前）',
  cameras: SQUARE_A1_CAMERAS,
  build(ctx: SetContext): BuiltSet {
    const layout0 = readLayout(ctx, 'square') ?? { format: 'antidrug-set/1' };
    // 本景的副本：右側行道樹移到燈籠店窗戶右邊（a1_c008 窗戶整個露出來；共用的 square layout.json 不動）
    const layout = { ...layout0, layers: (layout0.layers ?? []).map((l) => (l.id === 'tree-b' ? { ...l, x: 8.9 } : l)) };
    const base = buildImageSet({ ...ctx, name: 'square' }, layout);
    const group = base.group;
    group.name = 'set:square_a1';
    const mats: Material[] = [...(base.materials ?? [])];
    const report = [...(base.report ?? [])];
    const im = (id: string): HTMLImageElement | undefined => { const i = ctx.image(id); if (!i) report.push(`景 square_a1：缺圖 ${id}`); return i; };
    const add = (m: Mesh | null, x: number, y: number, z: number): Mesh | null => { if (m) { m.position.set(x, y, z); group.add(m); } return m; };

    // 騎樓下的小燈籠串
    add(imagePiece(im('sets/square_a1/garland'), { w: 9.0, pivot: [0.5, 1], order: LAYER.mid.order - 40, emissive: 0.15 }, mats), -1.7, 3.62, -1.5);
    // 紅磚柱子（畫面左側）
    add(imagePiece(im('sets/square_a1/pillar'), { w: PILLAR.w, order: LAYER.mid.order + 60, shadow: true }, mats), PILLAR.x, -0.03, PILLAR.z);
    // 邀請者的手＋貼紙盒（不降彩：俗豔的貼紙層就是要看起來很亮；固定反光，不閃）
    const handMats: Material[] = [];
    const hand = add(imagePiece(im('chr-inviter_hand-box'), { w: HAND.w, order: LAYER.mid.order + 55, shadow: true }, handMats), HAND.xHide, HAND.y, HAND.z);
    // 手後面的背景略偏冷、略降彩：一層冷灰藍半透明（在柱子、手、品安後面，在騎樓、行道樹、長椅左端前面）
    const glowMat = new MeshBasicMaterial({ map: coolBand(), color: COOL, transparent: true, opacity: 0, depthWrite: false });
    const glow = new Mesh(new PlaneGeometry(COOLBAND.x1 - COOLBAND.xl, COOLBAND.y1 - COOLBAND.y0), glowMat);
    glow.position.set((COOLBAND.xl + COOLBAND.x1) / 2, (COOLBAND.y0 + COOLBAND.y1) / 2, COOLBAND.z);
    glow.renderOrder = LAYER.mid.order + 50;
    glow.visible = false;
    group.add(glow);

    // 燈籠店門面牆（窗、窗紙、剪影都在它前面；只接受影子、不投影子到後排騎樓）
    const wall = add(imagePiece(im('sets/square_a1/shopwall'), { w: SHOPWALL.w, order: LAYER.mid.order - 36, emissive: 0.3, shadow: true }, mats),
      SHOPWALL.x0 + SHOPWALL.w / 2, SHOPWALL.y0, SHOPWALL.z);
    if (wall) wall.castShadow = false;
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
    const bamboo = imagePiece(im('sets/square_a1/silbamboo'), { w: 60 / P, pivot: [0.5, 0.3], order: LAYER.mid.order - 26, transparent: true }, silMat);
    const hand0 = { x: (110 - 240) / P, y: (250 - 60) / P };
    if (bamboo) sil.add(bamboo);
    // （修正第 1 輪：拿掉窗紙前那層半透明紙——剪影要夠深，和窗光的明度差 ΔL* ≥ 40）

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
        // 冷色層：a1_c002 手伸出時 1.5 秒漸入；a1_c003 全開；a1_c004 跟著手縮回漸淡
        const cool = id === 'a1_c002' ? sine01((t - 0.6) / 1.5) : id === 'a1_c003' ? 1 : id === 'a1_c004' ? out : 0;
        glow.visible = cool > 0.002;
        glowMat.opacity = 0.26 * cool;
        // ---- 盒子特寫小窗：a1_c003 小晴「這盒子上面什麼都沒寫」→ 打開，停到 cue 結束（老師指線索）；a1_c004 一開始收起
        let cv = 0;
        if (id === 'a1_c003') cv = sine01((t - (lineTime(tl, ['a1_c003_02'], 'start', 3) + 0.35)) / 0.5);
        else if (id === 'a1_c004') cv = 1 - sine01((t - 0.25) / 0.5);
        if (card) {
          card.visible = cv > 0.002;
          if (card.visible) {
            // 畫面左上（真的盒子在它下方左緣），高 38%：品安的頭和燈籠、兩個孩子都留在畫面裡（修正第 1 輪）
            placeOnCamera(card, camera, -0.31, 0.27, 0.38 * (0.95 + 0.05 * cv), cardAspect, 0.82);
            (card.material as MeshBasicMaterial).opacity = cv;
          }
        }
        // ---- 包裝紙（a1_c008）：風從左邊吹來，翻滾著停在孩子身後左下方（離小晴一個身寬以上，畫面左下）
        if (wrap) {
          let vis = false, x = WRAP.xStop, y = 0, rz = 0;
          if (id === 'a1_c008') {
            const t0 = WRAP.t0, dur = WRAP.dur;
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
        // ---- 窗內剪影（a1_c008）：手垂著拿竹條 → 舉起（0.8 秒）→ 手被往旁邊一帶、往左歪（0.5 秒）→ 竹條慢慢落下（1 秒，
        //      在窗內看得到，落到窗台下被窗框擋住）→ 窗光漸亮約 12%（1.2 秒）。時間錨在小晴「不要碰…」說完（cue 的音效同一個錨）
        let raise = 0, tilt = 0, fall = 0, lit = 0, on = 0;
        // 剪影只在窗前這一段出現（前面幾段窗裡只有窗紙）；G6 精修：a1_c007 題卡淡出全暗後就切到 a1_c008 開頭的街景，
        // 剪影在全暗那一刻先出現（不在 a1_c008 第一格突然冒出來）
        sil.visible = id === 'a1_c008' || (id === 'a1_c007' && t >= lineTime(tl, ['a1_c007_01'], 'end', 4) + 1.16);
        if (id === 'a1_c008') {
          const t02 = lineTime(tl, ['a1_c008_02'], 'end', 9);
          on = sine01((t - t02 - SIL_T.lit) / 1.2);
          const T0 = t02 + SIL_T.raise;
          raise = sine01((t - T0) / 0.8);
          tilt = sine01((t - T0 - 0.85) / 0.5);
          fall = clamp((t - T0 - 1.4) / 1.0);
          lit = sine01((t - T0 - 1.4) / 1.2);
        }
        // 白天的窗紙不發亮（窗格明暗對比小，鏡頭移動時不會一格一格閃過）；窗前這一段屋裡點著燈，竹條落下時再亮一點（焦點）
        if (paperMat) paperMat.emissiveIntensity = id === 'a1_c008' ? 0.2 + 0.55 * on + 0.12 * lit : 0.2;
        const th = lerp(1.7, -0.15, raise) + 0.9 * tilt + (id === 'a1_c008' ? 0.02 * Math.sin(Math.PI * 2 * 0.22 * t) : 0);   // a1_c007 結尾不擺（a1_c008 第 0 秒擺幅＝0，接得上）
        shoulder.rotation.z = th;
        if (bamboo) {
          // 手的位置（剪影座標）＝肩膀＋旋轉後的手；竹條從手上鬆開後往下掉（落到窗台下方被窗框擋住）
          const hx = shoulder.position.x + hand0.x * Math.cos(th) - hand0.y * Math.sin(th);
          const hy = shoulder.position.y + hand0.x * Math.sin(th) + hand0.y * Math.cos(th);
          const g = fall * fall;
          const drop = hy + 0.35;            // 從手的高度落到窗台（剪影原點＝窗洞下緣）下方 0.35
          bamboo.position.set(hx - 0.12 * fall, hy - drop * g, 0.004);
          bamboo.rotation.z = lerp(0.35 * th, 0.25, raise) + 1.1 * g;
          bamboo.visible = fall < 0.999;
        }
      },
    };
  },
};
