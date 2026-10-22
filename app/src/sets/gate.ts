// gate：校門口（放學接送區）。G5 第四幕代理負責（第三、四、五幕共用）。
// 底景照 assets/final/sets/gate/layout.json（資料驅動，站位、地標、鏡位都不變）；本檔只在上面加「需要程式的東西」，
// 而且只有 cue 寫了 setTrack 才動（沒寫的 cue＝和 layout.json 原樣相同，第三、五幕不受影響；騎樓小燈籠一直掛著、無風時幾乎不動）：
//   { "do": "truck",   "from": -9, "start": …, "duration": 4 }          小貨車從畫面左外開進來、慢慢停在 layout 的位置（輪子轉；車聲另排）
//   { "do": "lin",     "to": 1 }                                          警衛室窗內林老師的小背影（背對街道講電話；1 顯示、0 不顯示）
//   { "do": "walkers", "kind": "a", "x0": -4, "x1": 14, "z": -2.9, "z1": -3.2, "start": …, "duration": 8 }   遠景家長牽孩子離開（淺紙色背影小紙人；z1 省略＝不往後走）
//   { "do": "wind",    "to": 1, "start": …, "duration": 1.5 }            風（騎樓小燈籠擺動幅度，慢、小）
//   { "do": "key",     "hold": "ale.A|ale.B|chen.receive|chen.stand|none", "start": …, "duration": 0.4 }   車鑰匙跟著誰的手
//   { "do": "flag",    "to": 1 }                                          陳伯伯另一手拿導護旗
//   { "do": "map",     "to": 1, "start": …, "duration": 1.6 }            街道摺平後淡成牛皮紙地圖（俯視；a4_roadmap 同一張圖同一位置）
//   { "do": "farUp",   "to": 1 }                                          遠景（遠山、對街騎樓、校舍、校內圍牆）一直站著，set.popup 只立起近處景片
//                                                                         （同一區域不會在 1 秒內有太多景片接連立起：光敏）
//   { "do": "catEar",  "to": 1 }                                          小貨車換第四幕版貼圖：帆布下露出竹編貓頭骨架（1＝兩隻尖耳＋一小段頭框，同 a0 設計圖輪廓；
//                                                                         0.5＝帆布蓋住、只露左耳尖一小角；0＝layout 原圖）。G5 修正第 1 輪；第五幕要同一個骨架時在 a5 cue 的 setTrack 也寫 to 1
//   { "do": "brick",   "to": 0.3, "start": …, "duration": 0.8 }         對街紅磚騎樓降彩（0＝原色、1＝全灰；鏡頭移動時約 0.3，細格紅色光敏）
//   { "do": "lift",    "to": 1 }                                          孩子身後的中景景片（警衛室、校門柱、折疊門、校內圍牆）提亮：1＝貼圖顏色 ×(1＋LIFT_GAIN[景片])
//                                                                         （G5 修正第 2 輪：兒童站位背景投影亮度 ≥ 0.50，D-G2-06）
//   { "do": "haze",    "to": 1 }                                          校內那一側的景片（校舍、校內圍牆、警衛室、折疊門、門柱）蒙一層暖白（自發光加量 HAZE_ADD；
//                                                                         像隔一張薄描圖紙＝輕微景深：深色窗格、粉磚帶、樹籬加最多，淺色牆面幾乎到頂；不受舞台燈影響）
//                                                                         （G6 精修：兒童站位背景投影亮度 ≥ 0.50，D-G2-06；第四幕才寫，第三、五幕不受影響）
//   { "do": "hazeStreet", "to": 1 }                                       對街中景（小貨車、路口大樹）也蒙一點 HAZE_STREET（隔馬路看阿樂叔叔的鏡頭要和孩子鏡頭亮度相近才能硬切）
//   { "do": "gateOpen", "to": 1 }                                         折疊門收起來（放學時校門開著）：鐵柵往左邊門柱收攏成 GATE_OPEN_W 寬
//                                                                         （G5 修正第 2 輪：小晴常站在折疊門前，深色鐵柵讓兒童站位背景偏暗）
//   { "do": "zzpatch", "to": 1 }                                          原點的地板補片：引擎 stage.ts 給程式角色（折折）的接觸陰影放在 root 位置，
//                                                                         root 永遠在 (0,0,0)，地上多一個沒有主人的橢圓影子（折折自己另有影子）；有折折的 cue 打開，
//                                                                         用同一張地板貼圖、同樣的 UV 蓋住它（引擎修好後可以拿掉；見 review/G5/a4 handoff）
// setTrack 的時間參照同 animation.start；所有量都是時間的純函式。
import { CanvasTexture, Color, LinearMipmapLinearFilter, Matrix4, Mesh, MeshBasicMaterial, MeshStandardMaterial, PlaneGeometry, SRGBColorSpace, Vector3, type Material, type Object3D, type Texture } from 'three';
import { finishTexture, makeCanvas } from '../stage/paper';
import { buildImageSet, readLayout } from './imageSet';
import { A4_MAP_CAMERAS, imagePlane, mapOverlay, trackOf, trackValue } from './a4_roadmap';
import { clamp, ease, lerp } from '../util/math';
import type { CameraPreset } from '../stage/layers';
import type { BuiltSet, SetContext, SetEntry } from './types';

/** layout.json 的鏡位（同步複製一份：時間軸算鏡頭時不必先建景）＋第四幕的鏡位 */
const LAYOUT_CAMERAS: Record<string, CameraPreset> = {
  gate_wide: { pos: [0, 3.6, 27], target: [0, 3.2, 0], fov: 20 },
  gate_mid: { pos: [-0.2, 1.7, 17.5], target: [-0.2, 1.5, 0], fov: 20 },
  gate_inside: { pos: [3.3, 1.5, 13.5], target: [3.3, 1.35, 0], fov: 20 },
  gate_bench: { pos: [-2.4, 1.45, 13.5], target: [-2.4, 1.25, 0], fov: 20 },
  gate_truck_window: { pos: [-6.457, 2.438, 8.1], target: [-6.707, 2.188, -2.4], fov: 20 },
};
export const GATE_A4_CAMERAS: Record<string, CameraPreset> = {
  /** 放學大全景（第四幕開場；比 gate_wide 低一點、往左一點，看得到小貨車停的位置與警衛室） */
  a4_gate_wide: { pos: [0, 2.6, 24.5], target: [0, 2.3, 0], fov: 20 },
  /** 隔著馬路看阿樂叔叔（孩子那一側的視角）。G5 修正第 2 輪：斜角從約 21° 收到約 14°——引擎把紙環畫在紙偶前 0.24，
   *  斜看時紙環對前臂的視差約 0.24·sin(斜角)·每單位像素，斜 20° 的近景會偏 15–20 px（停格時腕環、肘環浮在前臂外） */
  a4_across: { pos: [-2.4, 1.95, 12.6], target: [-6.0, 1.72, -1.9], fov: 20 },
  /** 隔著馬路看阿樂叔叔：慢慢推近（斜角約 10°，停格時紙環落在前臂上） */
  a4_across_push: { pos: [-3.5, 1.9, 10.9], target: [-6.05, 1.72, -1.9], fov: 20 },
  /** 孩子在接送線後、背後是警衛室的窗（窗裡林老師的小背影） */
  a4_window: { pos: [3.7, 1.9, 13.2], target: [3.85, 1.7, -0.6], fov: 20 },
  /** 孩子在前景（右）、阿樂叔叔在對街（左）：前後景深。G5 修正第 2 輪：鏡頭往左 1.25、注視點往右，
   *  看阿樂叔叔的斜角從約 20° 收到約 15.5°（紙環視差見 a4_across 的說明；a4_c007 結尾＝a4_c008 開頭的停格） */
  a4_deep: { pos: [-2.0, 1.85, 13.4], target: [-1.0, 1.55, 0], fov: 29 },
  /** 兩個孩子近景（接送線後） */
  a4_kids: { pos: [2.85, 1.2, 13.0], target: [2.85, 1.08, 1.85], fov: 20 },
  /** 小晴說話（往她推近一點） */
  a4_kids_qg: { pos: [2.55, 1.25, 11.4], target: [2.5, 1.12, 1.95], fov: 20 },
  /** 小宇說話 */
  a4_kids_xy: { pos: [3.25, 1.25, 11.4], target: [3.2, 1.12, 1.8], fov: 20 },
  /** 折折從筆記本探出頭（放寬、放低，看得到地上的折折） */
  a4_kids_z2: { pos: [2.85, 1.15, 13.4], target: [2.85, 1.02, 2.0], fov: 20 },
  /** 林老師蹲下跟孩子說話（林老師＋孩子） */
  a4_guard_lin: { pos: [4.55, 1.5, 12.4], target: [4.45, 1.32, 0.8], fov: 20 },
  /** 兩個孩子＋折折（折折把問題交給觀眾） */
  a4_kids_z: { pos: [3.05, 1.2, 13.1], target: [3.05, 1.08, 1.9], fov: 20 },
  /** 校門內外同框（林老師在門內喊、陳伯伯在對面長椅旁） */
  a4_gate_wide2: { pos: [0.8, 2.2, 22], target: [0.8, 1.9, 0], fov: 20 },
  /** 往上看紙飛機（街道開始摺平） */
  a4_up: { pos: [2.4, 2.4, 11.5], target: [0.4, 4.9, 0], fov: 20 },
  /** 高處斜看馬路（街道摺平中） */
  a4_fold_high: { pos: [-4.6, 9.0, 3.75], target: [-4.8, 0, -1.3], fov: 20 },
  /** 警衛室門口四人中景 */
  a4_guard: { pos: [3.6, 1.75, 15.6], target: [3.6, 1.6, 0.6], fov: 20 },
  /** 長椅中景（陳伯伯、阿樂叔叔；G5 修正第 1 輪陳伯伯往右 0.65，鏡位跟著往右、退後一點） */
  a4_bench: { pos: [-1.55, 1.6, 12.9], target: [-1.55, 1.45, 0], fov: 20 },
  /** 收鑰匙近景 */
  a4_keyclose: { pos: [-1.45, 1.95, 10.9], target: [-1.5, 1.82, 0.3], fov: 20 },
  /** 長椅與小貨車（帶到後車窗的中途：先橫移、再慢慢推近） */
  a4_truck_mid: { pos: [-1.5, 2.2, 13.0], target: [-4.4, 2.0, -1.0], fov: 20 },
  /** 慢慢帶到小貨車後車窗（貓耳形的竹骨架；從右邊看過去，畫面不碰到台口摺幕） */
  a4_truck_window: { pos: [-4.3, 2.55, 8.3], target: [-6.6, 2.25, -2.4], fov: 17 },
  /** 小貨車車斗近景（只有車、沒有人、看不到阿樂叔叔的線；a4_c013 直接切過來，再慢慢推近到貓耳）
   *  畫面左緣在台口摺幕內（z 4 處 x ≥ −6.7），貓耳在畫面中央偏上、約佔畫面高 18% */
  a4_truck_close: { pos: [-4.6, 2.8, 7.3], target: [-7.5, 1.95, -2.4], fov: 18 },
  /** 貓耳骨架停格（a4_c013 最後；兩耳＋頭框約佔畫面高 20%，在畫面中央偏右上、字幕區外） */
  a4_ears: { pos: [-5.0, 2.75, 6.6], target: [-7.7, 2.0, -2.4], fov: 17 },
  /** 俯視（和 a4_roadmap 同一個鏡位） */
  a4_map_top: A4_MAP_CAMERAS.a4_map_top,
  /** 俯視整張地圖（a4_c002 街道在這個鏡位摺平；a4_c003 起點同一個鏡位） */
  a4_map: A4_MAP_CAMERAS.a4_map,
};
const GATE_CAMERAS: Record<string, CameraPreset> = { ...LAYOUT_CAMERAS, ...GATE_A4_CAMERAS };

/** 陳伯伯手的位置（立牌身體座標，世界單位；review/G5/a4/art_meta.json 由圖量得） */
const CHEN_HAND: Record<string, [number, number]> = {
  'chen.stand': [-0.551, 1.399],      // stand：畫面左側（他的右手）垂下
  'chen.receive': [-0.971, 1.568],    // receive：伸出去的手掌
  flag: [0.587, 1.329],               // 另一手（stand、receive 同位置）
};
/** 林老師手的位置（stand；畫面右側那隻手） */
const LIN_HAND: [number, number] = [0.288, 1.462];

/** farUp 時一直站著的遠景景片（layout.json 的 id） */
const FAR_PIECES = ['sq-mountains', 'sq-backrow', 'school-building', 'school-wall', 'sq-tree-a'];
/** setTrack lift 提亮的景片（layout.json 的 id）與增益（線性顏色倍數；×1.45 ≈ sRGB 明度 +18%；折疊門的深色鐵柵另外多提一點） */
const LIFT_GAIN: Record<string, number> = { 'guard-house': 0.45, pillar: 0.45, 'pillar-2': 0.45, 'school-wall': 0.45, 'folding-gate': 0.8 };
/** setTrack haze 的景片（layout.json 的 id）與自發光加量（線性；HAZE_COLOR × 量 × 軌值）。加法：暗的地方提得多、亮的地方幾乎不變 */
const HAZE_ADD: Record<string, number> = {
  'sq-mountains': 0.15, 'sq-backrow': 0.26, 'school-building': 0.36,                       // 遠景：最朦（空氣透視）
  'school-wall': 0.3, 'folding-gate': 0.3, 'guard-house': 0.12, pillar: 0.14, 'pillar-2': 0.14,   // 孩子身後的中景
};
/** setTrack hazeStreet：對街的中景（小貨車、路口大樹）也蒙一點（隔馬路看阿樂叔叔的鏡頭和孩子鏡頭亮度拉近，才能硬切） */
const HAZE_STREET: Record<string, number> = { 'prop-truck': 0.1, 'sq-tree-a': 0.15 };
const HAZE_COLOR = new Color('#fff0dc');
/** setTrack gateOpen：折疊門收攏後的寬度比例（layout 寬 0.9；左緣貼著右邊那根門柱不動） */
const GATE_OPEN_W = 0.3;
/** setTrack zzpatch：補片範圍（世界 x、z；接觸陰影 0.6×0.5 置中在 (0, 0.05)） */
const ZZ_PATCH = { x0: -0.38, x1: 0.38, z0: -0.26, z1: 0.36, y: 0.02 };
/** 第四幕版小貨車的竹編貓頭骨架露出部分中心（車圖底邊中央為原點的世界座標；review/G5/a4/art_meta.json fix1.truck_catear） */
const CAT_EAR_LOCAL: [number, number] = [0.178, 2.277];

/** 景片貼圖（同 imageSet.ts：往右下烘進卡紙厚度 thick px；gray＝先轉成灰階） */
function cardTexture(image: HTMLImageElement, thick = 5, gray = false): Texture {
  const W = image.naturalWidth, H = image.naturalHeight;
  const pad = thick + 2;
  const [c, g] = makeCanvas(W + pad, H + pad);
  const [art, ag] = makeCanvas(W, H);
  if (gray) ag.filter = 'saturate(0)';
  ag.drawImage(image, 0, 0);
  const [sil, sg] = makeCanvas(W, H);
  sg.drawImage(art, 0, 0);
  sg.globalCompositeOperation = 'source-in';
  sg.fillStyle = '#7a5a3c';
  sg.fillRect(0, 0, W, H);
  for (let k = thick; k >= 1; k--) g.drawImage(sil, k * 0.75, k);
  g.drawImage(art, 0, 0);
  const t = finishTexture(new CanvasTexture(c));
  t.minFilter = LinearMipmapLinearFilter;
  return t;
}

const tmpV = new Vector3();
const tmpM = new Matrix4();

function findByPrefix(root: Object3D | null | undefined, prefix: string): Object3D | null {
  if (!root) return null;
  let hit: Object3D | null = null;
  root.traverse((o) => { if (!hit && o.name.startsWith(prefix) && o.visible) hit = o; });
  return hit;
}

export function buildGate(ctx: SetContext): BuiltSet {
  const layout = readLayout(ctx, 'gate');
  if (!layout) throw new Error('缺少 sets/gate/layout.json');
  const base = buildImageSet(ctx, layout);
  const group = base.group;
  const mats: Material[] = [...(base.materials ?? [])];
  const report = [...(base.report ?? [])];
  const tint = new Color('#fff6e6');
  const img = (n: string): HTMLImageElement | undefined => {
    const im = ctx.image(n);
    if (!im) report.push(`景 gate：缺圖 ${n}`);
    return im;
  };
  const prop = (n: string, w: number): Mesh | null => {
    const m = imagePlane(img(n), w);
    if (m) { ((m.material as MeshStandardMaterial).color).copy(tint); mats.push(m.material as Material); m.castShadow = true; }
    return m;
  };

  // ---- 小貨車：輪子疊在車圖上（跟著車一起摺、一起移動）
  const truck = base.pieces?.find((p) => p.name === 'prop-truck');
  const truckX0 = truck?.hinge.position.x ?? -7.6;
  const truckLayer = (layout.layers ?? []).find((l) => l.id === 'prop-truck') as unknown as { _wheels?: { id: string; centers_world_from_bottom_center: [number, number][]; diameter_world: number } } | undefined;
  const wheels: Mesh[] = [];
  const wr = (truckLayer?._wheels?.diameter_world ?? 0.83) / 2;
  if (truck && truckLayer?._wheels) {
    const truckMesh = truck.hinge.children[0] as Mesh | undefined;
    for (const [cx, cy] of truckLayer._wheels.centers_world_from_bottom_center) {
      const w = prop(truckLayer._wheels.id, wr * 2);
      if (!w) continue;
      w.geometry.translate(0, -wr, 0);
      w.position.set(cx, cy, 0.02);
      w.renderOrder = (truckMesh?.renderOrder ?? 200) + 0.5;
      truck.hinge.add(w);
      wheels.push(w);
    }
  }

  // ---- 第四幕版小貨車貼圖（setTrack catEar：帆布下的竹編貓頭骨架；同尺寸，只換貼圖）
  const truckMat = (truck?.hinge.children[0] as Mesh | undefined)?.material as MeshStandardMaterial | undefined;
  const truckTex0 = truckMat?.map ?? null;
  const catImg = ctx.image('sets/gate/set-gate_a4-truck'), tipImg = ctx.image('sets/gate/set-gate_a4-truck-tip');
  const truckTexA4 = catImg ? cardTexture(catImg) : null;
  const truckTexTip = tipImg ? cardTexture(tipImg) : truckTexA4;
  let catOn = 0;

  // ---- 對街紅磚騎樓的灰階疊層（setTrack brick：不透明度＝降彩量；跟著同一個鉸鏈立起、摺下）
  const backrow = base.pieces?.find((p) => p.name === 'sq-backrow');
  let brickOv: Mesh | null = null;
  {
    const src = backrow?.hinge.children[0] as Mesh | undefined;
    const brickImg = ctx.image('sets/square/set-square_backrow');
    if (backrow && src && brickImg) {
      const sm = src.material as MeshStandardMaterial;
      const bm = new MeshStandardMaterial({ map: cardTexture(brickImg, 5, true), side: sm.side, roughness: sm.roughness, metalness: 0, color: sm.color.clone(), transparent: true, opacity: 0, depthWrite: false });
      mats.push(bm);
      brickOv = new Mesh(src.geometry, bm);
      brickOv.name = 'gate:brickGray';
      brickOv.renderOrder = src.renderOrder + 0.5;
      brickOv.receiveShadow = src.receiveShadow;
      brickOv.visible = false;
      backrow.hinge.add(brickOv);
    }
  }

  // ---- 孩子身後的中景景片提亮（setTrack lift）
  const liftMats: { mat: MeshStandardMaterial; c0: Color; gain: number }[] = [];
  group.traverse((o) => {
    const gain = o.name.startsWith('pop:') ? LIFT_GAIN[o.name.slice(4)] : undefined;
    if (gain === undefined) return;
    const m = (o.children[0] as Mesh | undefined)?.material as MeshStandardMaterial | undefined;
    if (m && m.color) liftMats.push({ mat: m, c0: m.color.clone(), gain });
  });
  let liftOn = 0;
  // 校內那一側蒙一層暖白（setTrack haze；layout 的這些景片沒有自發光貼圖，emissive 是整片均勻加量）
  const hazeMats: { mat: MeshStandardMaterial; amt: number; street: number }[] = [];
  group.traverse((o) => {
    const id = o.name.startsWith('pop:') ? o.name.slice(4) : '';
    const amt = HAZE_ADD[id] ?? 0, street = HAZE_STREET[id] ?? 0;
    if (!amt && !street) return;
    const m = (o.children[0] as Mesh | undefined)?.material as MeshStandardMaterial | undefined;
    if (m && m.emissive && !m.emissiveMap) hazeMats.push({ mat: m, amt, street });
  });
  if (brickOv) hazeMats.push({ mat: brickOv.material as MeshStandardMaterial, amt: HAZE_ADD['sq-backrow'], street: 0 });   // 紅磚降彩疊層也蒙同樣的白
  let hazeOn = '';
  // 折疊門（setTrack gateOpen）
  let foldGate: Mesh | null = null, foldGateW = 0.9;
  group.traverse((o) => { if (o.name === 'pop:folding-gate' && o.children[0]) foldGate = o.children[0] as Mesh; });
  {
    const fgLayer = (layout.layers ?? []).find((l) => l.id === 'folding-gate') as { width?: number } | undefined;
    foldGateW = fgLayer?.width ?? 0.9;
  }

  // ---- 原點的地板補片（setTrack zzpatch；同一張地板貼圖、同樣的 UV、同樣接收影子，只是畫在接觸陰影之後）
  let zzPatch: Mesh | null = null;
  {
    let floor: Mesh | null = null;
    group.traverse((o) => {
      const m = o as Mesh;
      const g = m.geometry as PlaneGeometry | undefined;
      if (!floor && m.isMesh && Math.abs(m.rotation.x + Math.PI / 2) < 1e-3 && g?.type === 'PlaneGeometry' && g.parameters.width >= 10) floor = m;
    });
    const fl = floor as Mesh | null;
    if (fl) {
      const g = fl.geometry as PlaneGeometry;
      const W = g.parameters.width, D = g.parameters.height;
      const fz = fl.position.z, fx = fl.position.x;
      const pg = new PlaneGeometry(ZZ_PATCH.x1 - ZZ_PATCH.x0, ZZ_PATCH.z1 - ZZ_PATCH.z0);
      const pos = pg.attributes.position, uv = pg.attributes.uv;
      const cx = (ZZ_PATCH.x0 + ZZ_PATCH.x1) / 2, cz = (ZZ_PATCH.z0 + ZZ_PATCH.z1) / 2;
      for (let k = 0; k < pos.count; k++) {
        const wx = cx + pos.getX(k), wz = cz - pos.getY(k);          // 平面轉 −90°：本地 y → 世界 −z
        uv.setXY(k, (wx - fx + W / 2) / W, (fz - wz + D / 2) / D);    // 和地板 PlaneGeometry 的 UV 一樣
      }
      uv.needsUpdate = true;
      // 不透明、寫深度：接觸陰影是半透明（三維引擎在不透明物件之後才畫），比補片低（y 0.012），深度測試就被擋掉
      const fm = (fl.material as MeshStandardMaterial).clone();
      mats.push(fm);
      zzPatch = new Mesh(pg, fm);
      zzPatch.name = 'gate:zzPatch';
      zzPatch.rotation.x = -Math.PI / 2;
      zzPatch.position.set(cx, ZZ_PATCH.y, cz);
      zzPatch.receiveShadow = true;
      zzPatch.renderOrder = fl.renderOrder + 1;
      zzPatch.visible = false;
      group.add(zzPatch);
    }
  }

  // ---- 警衛室窗內的小背影（林老師）
  const lin = prop('sets/gate/set-gate_a4-lin-back', 0.8);
  if (lin) { lin.position.set(4.3, 1.08, -1.12); lin.renderOrder = 205; lin.visible = false; group.add(lin); }

  // ---- 遠景家長剪影
  const walkers: Record<string, Mesh> = {};
  for (const k of ['a', 'b']) {
    const m = prop(`sets/gate/set-gate_a4-walkers-${k}`, 1.5);
    if (m) { m.visible = false; m.renderOrder = 150; group.add(m); walkers[k] = m; }
  }

  // ---- 騎樓下的小燈籠（吊點在繩子上端）
  const lanterns: { m: Mesh; phase: number }[] = [];
  for (const [x, y, ph] of [[-2.95, 2.42, 0.0], [-2.3, 2.34, 1.7]] as [number, number, number][]) {
    const m = prop('sets/gate/set-gate_a4-lantern', 0.42);
    if (!m) continue;
    m.geometry.translate(0, -(m.userData.h as number), 0);
    m.position.set(x, y, -3.3);
    m.renderOrder = 110;
    group.add(m);
    lanterns.push({ m, phase: ph });
  }

  // ---- 車鑰匙、導護旗（跟著角色的手；角色在 stage 先擺好姿勢，景的 update 之後才呼叫）
  const key = prop('sets/gate/set-gate_a4-key', 0.3);
  if (key) {
    key.geometry.translate(0, -(key.userData.h as number) / 2, 0);
    key.renderOrder = 396;
    key.visible = false;
    group.add(key);
  }
  const flag = prop('sets/gate/set-gate_a4-flag', 0.78);
  if (flag) {
    flag.geometry.translate(0.78 * 0.5 - 0.78 * 0.14, -0.42, 0);   // 握點（竹柄下段）在原點
    flag.renderOrder = 394;
    flag.visible = false;
    group.add(flag);
  }

  const phone = prop('sets/gate/set-gate_a4-phone', 0.13);
  if (phone) {
    phone.geometry.translate(0, -0.12, 0);
    phone.renderOrder = 394;
    phone.visible = false;
    group.add(phone);
  }
  // ---- 對焦到後車窗（FX7 的替代：車窗以外慢慢暗一點；只在 setTrack 的 focus 打開時）
  let focus: Mesh | null = null;
  {
    const c = document.createElement('canvas');
    c.width = 512; c.height = 256;
    const g2 = c.getContext('2d')!;
    // 平面 16×8（x −14～2、y 0～8）＝512×256 px；洞的中心＝第四幕版貼圖的竹編貓頭骨架（在車前 0.25，往右偏一點抵掉斜看的視差）
    const ear = { x0: truckX0 + CAT_EAR_LOCAL[0] + 0.05, y: ((layout.layers ?? []).find((l) => l.id === 'prop-truck')?.y ?? 0) + CAT_EAR_LOCAL[1] };
    const cx = ((ear.x0 + 14) / 16) * 512, cy = (1 - ear.y / 8) * 256;
    const gr = g2.createRadialGradient(cx, cy, 0, cx, cy, 80);   // 車窗與貓耳（約 0.9 單位內）全亮，2.5 單位外最暗
    gr.addColorStop(0, 'rgba(40,28,20,0)');
    gr.addColorStop(0.36, 'rgba(40,28,20,0)');
    gr.addColorStop(1, 'rgba(40,28,20,1)');
    g2.fillStyle = gr;
    g2.fillRect(0, 0, 512, 256);
    const tex = new CanvasTexture(c);
    tex.colorSpace = SRGBColorSpace;
    focus = new Mesh(new PlaneGeometry(16, 8), new MeshBasicMaterial({ map: tex, transparent: true, opacity: 0, depthWrite: false }));
    focus.position.set(-6, 4, -2.15);
    focus.renderOrder = 250;
    focus.visible = false;
    group.add(focus);
  }

  // ---- 地圖淡入（街道摺平後）
  const ov = mapOverlay(ctx);
  if (ov) { ov.mesh.visible = false; group.add(ov.mesh); }

  /** 角色手的世界座標：ale.A＝畫面左側（扣操偶線那隻）、ale.B＝畫面右側；chen.*＝立牌身體座標 */
  const handAt = (scene: Object3D | null, who: string, out: Vector3): { ok: boolean; rot: number; flip: number } => {
    if (who.startsWith('ale.')) {
      const rig = findByPrefix(scene, 'rig:');
      if (!rig) return { ok: false, rot: 0, flip: 1 };
      const hr = rig.getObjectByName('hand_r'), hl = rig.getObjectByName('hand_l');
      if (!hr || !hl) return { ok: false, rot: 0, flip: 1 };
      hr.updateWorldMatrix(true, false); hl.updateWorldMatrix(true, false);
      const pr = new Vector3().setFromMatrixPosition(hr.matrixWorld), pl = new Vector3().setFromMatrixPosition(hl.matrixWorld);
      const h = who === 'ale.A' ? (pr.x < pl.x ? hr : hl) : (pr.x < pl.x ? hl : hr);
      // 手心：手腕樞紐往手掌方向 0.13
      out.set(0.02, -0.17, 0.24).applyMatrix4(h.matrixWorld);
      const e = h.matrixWorld.elements;
      return { ok: true, rot: Math.atan2(e[1], e[0]), flip: Math.sign(e[0] * e[5] - e[1] * e[4]) || 1 };
    }
    const chen = scene?.getObjectByName('standee:chen');
    if (!chen || !chen.visible) return { ok: false, rot: 0, flip: 1 };
    const body = chen.children[0];
    body.updateWorldMatrix(true, false);
    const p = CHEN_HAND[who] ?? CHEN_HAND['chen.stand'];
    out.set(p[0], p[1], 0.06).applyMatrix4(body.matrixWorld);
    tmpM.copy(body.matrixWorld);
    return { ok: true, rot: 0, flip: Math.sign(tmpM.elements[0]) || 1 };
  };

  return {
    ...base, group, materials: mats, report,
    cameras: { ...(base.cameras ?? {}), ...GATE_A4_CAMERAS },
    update(o) {
      base.update?.(o);
      const { tl, t } = o;
      const scene = group.parent?.parent ?? null;
      const ev = trackOf(tl);
      if (trackValue(tl, 'farUp', t, 0, 'linear') > 0.5) {
        for (const p of base.pieces ?? []) if (FAR_PIECES.includes(p.name)) { p.hinge.rotation.x = 0; p.hinge.visible = true; }
      }
      // 小貨車開進來（減速停住）
      if (truck) {
        let dx = 0;
        for (const e of ev) {
          if (e.do !== 'truck') continue;
          const u = e.duration > 0 ? clamp((t - e.start) / e.duration) : 1;
          const from = Number(e.p.from ?? -9);
          dx = from * (1 - (1 - Math.pow(1 - u, 2.4)));
          if (t < e.start) dx = from;
        }
        truck.hinge.position.x = truckX0 + dx;
        truck.hinge.position.y = (layout.layers ?? []).find((l) => l.id === 'prop-truck')?.y ?? 0;
        for (const w of wheels) w.rotation.z = dx / wr;
      }
      if (truckMat && truckTexA4) {
        const v = trackValue(tl, 'catEar', t, 0, 'linear');
        const on = v > 0.75 ? 2 : v > 0.25 ? 1 : 0;
        if (on !== catOn) { truckMat.map = on === 2 ? truckTexA4 : on === 1 ? truckTexTip : truckTex0; truckMat.needsUpdate = true; catOn = on; }
      }
      if (brickOv) {
        const k = clamp(trackValue(tl, 'brick', t, 0));
        (brickOv.material as MeshStandardMaterial).opacity = k;
        brickOv.visible = k > 0.002;
      }
      const lf = clamp(trackValue(tl, 'lift', t, 0));
      if (lf !== liftOn) { for (const L of liftMats) L.mat.color.copy(L.c0).multiplyScalar(1 + L.gain * lf); liftOn = lf; }
      const hz = clamp(trackValue(tl, 'haze', t, 0)), hs = clamp(trackValue(tl, 'hazeStreet', t, 0));
      if (`${hz},${hs}` !== hazeOn) { for (const H of hazeMats) H.mat.emissive.copy(HAZE_COLOR).multiplyScalar(H.amt * hz + H.street * hs); hazeOn = `${hz},${hs}`; }
      if (zzPatch) zzPatch.visible = trackValue(tl, 'zzpatch', t, 0, 'linear') > 0.5;
      const fg = foldGate as Mesh | null;
      if (fg) {
        const k = lerp(1, GATE_OPEN_W, clamp(trackValue(tl, 'gateOpen', t, 0)));
        fg.scale.x = k;
        fg.position.x = -(1 - k) * foldGateW / 2;
      }
      if (lin) lin.visible = trackValue(tl, 'lin', t, 0, 'linear') > 0.5;
      for (const [k, m] of Object.entries(walkers)) {
        m.visible = false;
        for (const e of ev) {
          if (e.do !== 'walkers' || e.p.kind !== k || t < e.start || t > e.start + e.duration) continue;
          const u = (t - e.start) / Math.max(1e-6, e.duration);
          m.visible = true;
          const z0 = Number(e.p.z ?? -2.9);
          m.position.set(lerp(Number(e.p.x0 ?? -4), Number(e.p.x1 ?? 14), u), Math.abs(Math.sin((t - e.start) * Math.PI * 2.1)) * 0.03, lerp(z0, Number(e.p.z1 ?? z0), u));
        }
      }
      const wind = trackValue(tl, 'wind', t, 0);
      for (const l of lanterns) l.m.rotation.z = (0.02 + 0.11 * wind) * Math.sin((t / 2.6) * Math.PI * 2 + l.phase) + 0.03 * wind * Math.sin((t / 1.7) * Math.PI * 2 + l.phase * 2);
      // 車鑰匙：在誰的手上（換手時在兩個位置之間移動）
      if (key) {
        let cur = 'none', prev = 'none', u = 1;
        for (const e of ev) {
          if (e.do !== 'key' || t < e.start) continue;
          prev = cur; cur = String(e.p.hold ?? 'none');
          u = e.duration > 0 ? clamp((t - e.start) / e.duration) : 1;
        }
        const a = new Vector3(), b = new Vector3();
        const ha = cur === 'none' ? { ok: false, rot: 0, flip: 1 } : handAt(scene, cur, a);
        const hb = prev === 'none' || u >= 1 ? { ok: false, rot: 0, flip: 1 } : handAt(scene, prev, b);
        key.visible = ha.ok;
        if (ha.ok) {
          const k = ease('sine', u);
          if (hb.ok) a.lerp(b, 1 - k);
          key.position.copy(a);
          const r0 = cur.startsWith('ale.') ? ha.rot - 1.35 : -1.25;
          key.rotation.set(0, 0, r0);
          key.scale.set(ha.flip, 1, 1);
        }
      }
      if (flag) {
        const on = trackValue(tl, 'flag', t, 0, 'linear') > 0.5;
        const h = on ? handAt(scene, 'flag', tmpV) : { ok: false, rot: 0, flip: 1 };
        flag.visible = on && h.ok;
        if (flag.visible) { flag.position.copy(tmpV); flag.scale.set(h.flip, 1, 1); }
      }
      if (phone) {
        const on = trackValue(tl, 'phone', t, 0, 'linear') > 0.5;
        const linS = on ? scene?.getObjectByName('standee:lin') : null;
        phone.visible = !!linS && linS.visible;
        if (phone.visible && linS) {
          const body = linS.children[0];
          body.updateWorldMatrix(true, false);
          phone.position.set(LIN_HAND[0], LIN_HAND[1], 0.06).applyMatrix4(body.matrixWorld);
          phone.rotation.z = 0.15;
        }
      }
      if (focus) {
        const f = trackValue(tl, 'focus', t, 0);
        (focus.material as MeshBasicMaterial).opacity = 0.5 * f;
        focus.visible = f > 0.002;
      }
      if (ov) {
        const m = trackValue(tl, 'map', t, 0);
        ov.mat.opacity = m;
        ov.mesh.visible = m > 0.001;
      }
    },
  };
}

export const GATE: SetEntry = { title: '校門口（放學接送區）', cameras: GATE_CAMERAS, build: (ctx) => buildGate(ctx) };
