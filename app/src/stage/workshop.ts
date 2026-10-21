// G4 燈籠店立體書景（workshop_g4）：全部由程式畫的厚卡紙景片，之後可由 g4_manifest.json 的正式景片圖替換。
// - 紙材：底色＋紙纖維＋手繪感線條；每張景片往右下烘進 3–5 px 深牛皮紙色的卡紙厚度（FX2），刀切邊 alphaTest 寫深度。
// - 立體書機關（FX6）：每張景片以底邊為鉸鏈，set.popup 時依序從平躺立起（略過頭再回正），set.fold 反向收攏。
// - 層間柔影（FX3）：景片投影到牆與地板（PCF 柔化）；角色腳下另有接觸陰影。
// - 兒童站位的背景（右側牆面）保持淺色：投影 v2 下亮度 ≥ 0.50（D-G2-06）。景片裡沒有任何文字。
import {
  CanvasTexture, DoubleSide, Group, LinearMipmapLinearFilter, Mesh, MeshStandardMaterial, PlaneGeometry, RepeatWrapping, type Material,
} from 'three';
import { finishTexture, fibers, makeCanvas } from './paper';
import { LAYER } from './layers';
import { seeded } from '../util/math';

export interface PopPiece {
  /** 鉸鏈群組（位置在景片底邊中央，旋轉 x 軸立起） */
  hinge: Group;
  /** 在 set 進度 0–1 中開始與結束的位置 */
  from: number;
  to: number;
  name: string;
}

export interface WorkshopG4 {
  group: Group;
  pieces: PopPiece[];
  /** 套用 FX8 降彩的材質 */
  materials: Material[];
  /** 桌邊（阿樂叔叔左手扶桌的世界座標） */
  tableEdge: [number, number];
  /** 角色站位參考 */
  marks: Record<string, { x: number; z: number }>;
  /** 量測用地標（世界座標）：工作台桌面上緣、圓凳座面上緣（驗收包量扶桌與臀部離凳用） */
  landmarks: Record<string, { x0: number; x1: number; y: number; z: number }>;
}

type Draw = (g: CanvasRenderingContext2D, W: number, H: number) => void;

const PPU = 150;
const KRAFT = '#7a5a3c';

/** 一張厚卡紙景片：draw 在像素空間畫外形（不透明處＝紙），程式往右下烘進卡紙厚度 */
function paperPiece(o: { w: number; h: number; draw: Draw; seed: number; thick?: number; ppu?: number; fiber?: number }): CanvasTexture {
  const ppu = o.ppu ?? PPU;
  const W = Math.min(2048, Math.round(o.w * ppu)), H = Math.min(2048, Math.round(o.h * ppu));
  const pad = 8;
  const [art, ag] = makeCanvas(W, H);
  ag.save(); ag.translate(pad, pad); ag.scale((W - pad * 2) / W, (H - pad * 2) / H);
  o.draw(ag, W, H);
  ag.restore();
  // 紙纖維只疊在紙上
  ag.save(); ag.globalCompositeOperation = 'source-atop'; fibers(ag, W, H, o.seed, o.fiber ?? 1.1); ag.restore();
  const [c, g] = makeCanvas(W, H);
  const thick = o.thick ?? 4;
  // 卡紙厚度：同外形的深牛皮紙色，往右下疊幾層
  const [sil, sg] = makeCanvas(W, H);
  sg.drawImage(art, 0, 0);
  sg.globalCompositeOperation = 'source-in';
  sg.fillStyle = KRAFT;
  sg.fillRect(0, 0, W, H);
  for (let k = thick; k >= 1; k--) g.drawImage(sil, k * 0.75, k);
  g.drawImage(art, 0, 0);
  const t = finishTexture(new CanvasTexture(c));
  t.minFilter = LinearMipmapLinearFilter;
  return t;
}

/** 素材圖景片：原圖＋往右下烘進卡紙厚度（深牛皮紙色） */
function imagePiece(img: HTMLImageElement, thick = 5): CanvasTexture {
  const W = img.naturalWidth, H = img.naturalHeight;
  const pad = thick + 2;
  const [c, g] = makeCanvas(W + pad, H + pad);
  const [sil, sg] = makeCanvas(W, H);
  sg.drawImage(img, 0, 0);
  sg.globalCompositeOperation = 'source-in';
  sg.fillStyle = KRAFT;
  sg.fillRect(0, 0, W, H);
  for (let k = thick; k >= 1; k--) g.drawImage(sil, k * 0.75, k);
  g.drawImage(img, 0, 0);
  const t = finishTexture(new CanvasTexture(c));
  t.minFilter = LinearMipmapLinearFilter;
  return t;
}

function pieceMesh(tex: CanvasTexture, w: number, h: number, order: number, mats: Material[], a2c: boolean): Mesh {
  const mat = new MeshStandardMaterial({ map: tex, alphaTest: 0.5, side: DoubleSide, roughness: 0.92, metalness: 0, alphaToCoverage: a2c });
  mats.push(mat);
  const geo = new PlaneGeometry(w, h);
  geo.translate(0, h / 2, 0); // 底邊在原點（鉸鏈）
  const m = new Mesh(geo, mat);
  m.renderOrder = order;
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}

const line = (g: CanvasRenderingContext2D, pts: [number, number][], w: number, col: string): void => {
  g.strokeStyle = col; g.lineWidth = w; g.lineCap = 'round'; g.lineJoin = 'round';
  g.beginPath(); pts.forEach(([x, y], i) => (i ? g.lineTo(x, y) : g.moveTo(x, y))); g.stroke();
};

/** 紙燈籠（不發光）：橢圓燈身＋竹骨線＋上下木蓋 */
function lantern(g: CanvasRenderingContext2D, x: number, y: number, r: number, col: string): void {
  g.fillStyle = col;
  g.beginPath(); g.ellipse(x, y, r, r * 1.12, 0, 0, Math.PI * 2); g.fill();
  g.strokeStyle = 'rgba(120,70,30,0.42)'; g.lineWidth = Math.max(1.5, r * 0.06);
  for (let k = -2; k <= 2; k++) { g.beginPath(); g.ellipse(x, y, (r * Math.abs(k)) / 2.4, r * 1.12, 0, 0, Math.PI * 2); g.stroke(); }
  g.fillStyle = 'rgba(255,250,235,0.28)';
  g.beginPath(); g.ellipse(x - r * 0.35, y - r * 0.3, r * 0.22, r * 0.5, -0.3, 0, Math.PI * 2); g.fill();
  g.fillStyle = '#6a4630';
  g.fillRect(x - r * 0.42, y - r * 1.22, r * 0.84, r * 0.2);
  g.fillRect(x - r * 0.42, y + r * 1.04, r * 0.84, r * 0.2);
}

/** 背牆（不立起，是立體書的底頁）：淺米色和紙牆、淺木樑、大窗、右上層架；兒童身後保持淺色 */
function wallTexture(W: number, H: number): CanvasTexture {
  const [c, g] = makeCanvas(W, H);
  const r = seeded(7);
  g.fillStyle = '#f4e9d3';
  g.fillRect(0, 0, W, H);
  // 和紙拼貼的接縫（很淡）
  for (let x = 0; x < W; x += W / 9) { g.fillStyle = 'rgba(160,130,95,0.07)'; g.fillRect(x + r() * 6, 0, 2, H); }
  for (let i = 0; i < 40; i++) { g.fillStyle = `rgba(255,255,255,${0.06 + r() * 0.06})`; g.fillRect(r() * W, r() * H, 40 + r() * 140, 20 + r() * 90); }
  fibers(g, W, H, 9, 1.5);
  // 踢腳板（很低、淺色）
  g.fillStyle = '#e8d5b3'; g.fillRect(0, H * 0.9, W, H * 0.1);
  g.fillStyle = 'rgba(120,90,60,0.25)'; g.fillRect(0, H * 0.9, W, 3);
  // 天花板木樑與柱子（淺中木色）
  g.fillStyle = '#b48a5e';
  g.fillRect(0, 0, W, H * 0.07);
  g.fillStyle = 'rgba(90,60,35,0.35)'; g.fillRect(0, H * 0.07 - 4, W, 4);
  g.fillStyle = '#b8905f';
  for (const x of [0.035, 0.965]) g.fillRect(W * x - 16, 0, 32, H * 0.9);
  // 大窗（左側中間）：淡天色、窗櫺；窗外一道遠山剪影（淡）
  const wx = W * 0.2, wy = H * 0.2, ww = W * 0.24, wh = H * 0.34;
  const sky = g.createLinearGradient(0, wy, 0, wy + wh);
  sky.addColorStop(0, '#cfe5ef'); sky.addColorStop(1, '#edf5ef');
  g.fillStyle = sky; g.fillRect(wx, wy, ww, wh);
  g.fillStyle = 'rgba(140,170,150,0.35)';
  g.beginPath(); g.moveTo(wx, wy + wh * 0.8); g.quadraticCurveTo(wx + ww * 0.3, wy + wh * 0.55, wx + ww * 0.55, wy + wh * 0.72);
  g.quadraticCurveTo(wx + ww * 0.8, wy + wh * 0.6, wx + ww, wy + wh * 0.7); g.lineTo(wx + ww, wy + wh); g.lineTo(wx, wy + wh); g.fill();
  g.fillStyle = '#8d6847';
  g.fillRect(wx - 12, wy - 12, ww + 24, 14); g.fillRect(wx - 12, wy + wh - 2, ww + 24, 16);
  g.fillRect(wx - 12, wy - 12, 12, wh + 26); g.fillRect(wx + ww, wy - 12, 12, wh + 26);
  g.fillRect(wx + ww / 2 - 5, wy, 10, wh);
  for (let k = 1; k < 3; k++) g.fillRect(wx, wy + (wh * k) / 3 - 4, ww, 8);
  // 釘在牆上的主燈設計圖（摺紙貓燈籠線稿，沒有字）
  const px = W * 0.5, py = H * 0.17, pw = W * 0.12, ph = H * 0.26;
  g.save(); g.translate(px + pw / 2, py + ph / 2); g.rotate(-0.025);
  g.fillStyle = 'rgba(80,60,40,0.18)'; g.fillRect(-pw / 2 + 6, -ph / 2 + 8, pw, ph);
  g.fillStyle = '#fbf6ea'; g.fillRect(-pw / 2, -ph / 2, pw, ph);
  g.strokeStyle = 'rgba(90,110,150,0.6)'; g.lineWidth = 3;
  g.beginPath(); g.ellipse(0, ph * 0.06, pw * 0.3, ph * 0.26, 0, 0, Math.PI * 2); g.stroke();
  g.beginPath(); g.moveTo(-pw * 0.24, -ph * 0.12); g.lineTo(-pw * 0.18, -ph * 0.3); g.lineTo(-pw * 0.06, -ph * 0.18); g.stroke();
  g.beginPath(); g.moveTo(pw * 0.24, -ph * 0.12); g.lineTo(pw * 0.18, -ph * 0.3); g.lineTo(pw * 0.06, -ph * 0.18); g.stroke();
  for (let k = -1; k <= 1; k++) { g.beginPath(); g.ellipse(0, ph * 0.06, pw * 0.3 * Math.abs(k) * 0.55 + 1, ph * 0.26, 0, 0, Math.PI * 2); g.stroke(); }
  g.fillStyle = '#c0533a'; g.beginPath(); g.arc(0, -ph / 2 + 10, 7, 0, Math.PI * 2); g.fill();
  g.restore();
  const t = finishTexture(new CanvasTexture(c));
  t.minFilter = LinearMipmapLinearFilter;
  return t;
}

function floorTexture(): CanvasTexture {
  const [c, g] = makeCanvas(1024, 512);
  g.fillStyle = '#dcc39c';
  g.fillRect(0, 0, 1024, 512);
  const r = seeded(17);
  for (let y = 0; y < 512; y += 64) {
    g.fillStyle = 'rgba(110,75,45,0.22)'; g.fillRect(0, y, 1024, 3);
    const off = r() * 256;
    for (let x = off; x < 1024; x += 256 + r() * 120) { g.fillStyle = 'rgba(110,75,45,0.16)'; g.fillRect(x, y, 3, 64); }
    g.fillStyle = `rgba(255,245,225,${0.04 + r() * 0.06})`; g.fillRect(0, y + 6, 1024, 54);
  }
  fibers(g, 1024, 512, 19, 1.3);
  const t = finishTexture(new CanvasTexture(c));
  t.wrapS = t.wrapT = RepeatWrapping;
  t.repeat.set(4, 2);
  return t;
}

/** G4 景用到的素材圖 id（assets/final；素材代理產出）。缺哪張就用程式畫的同位置景片 */
export const G4_SET_IMAGES = { back: 'bg-workshop-back', floor: 'bg-workshop-floor', table: 'bg-workshop-table', lanterns: 'bg-workshop-lanterns', wing: 'bg-workshop-wing' };

export function buildWorkshopG4(opts: { alphaToCoverage: boolean; image?: (id: string) => HTMLImageElement | undefined }): WorkshopG4 {
  const group = new Group();
  group.name = 'set:workshop_g4';
  const mats: Material[] = [];
  const pieces: PopPiece[] = [];
  const a2c = opts.alphaToCoverage;
  const img = (k: keyof typeof G4_SET_IMAGES): HTMLImageElement | undefined => opts.image?.(G4_SET_IMAGES[k]);
  const backImg = img('back'), floorImg = img('floor'), tableImg = img('table'), lanternImg = img('lanterns'), wingImg = img('wing');

  // ---- 底頁：牆與地板（不立起）
  const WALL_Z = -3.6;
  let wallMat: MeshStandardMaterial;
  let wallW = 30, wallH = 13, wallY = wallH / 2 - 0.6;
  if (backImg) {
    // 素材背牆：寬 21（涵蓋台口內所有鏡位），底邊踢腳板對齊地面
    wallW = 21; wallH = wallW * backImg.naturalHeight / backImg.naturalWidth; wallY = wallH / 2 - 0.02;
    const t = finishTexture(new CanvasTexture(backImg));
    t.minFilter = LinearMipmapLinearFilter;
    wallMat = new MeshStandardMaterial({ map: t, roughness: 0.96, metalness: 0 });
  } else wallMat = new MeshStandardMaterial({ map: wallTexture(1800, 780), roughness: 0.96, metalness: 0 });
  // 牆面底亮度：用同一張圖當自發光（0.32），舞台燈調暗或降彩時，兒童身後的牆在投影 v2 下仍 ≥ 0.50（D-G2-06）；
  // 影子只壓暗漫射的部分，仍看得到角色與景片的柔影
  wallMat.emissiveMap = wallMat.map;
  wallMat.emissive.setRGB(1, 1, 1);
  wallMat.emissiveIntensity = 0.32;
  wallMat.color.setScalar(0.86);
  mats.push(wallMat);
  const wall = new Mesh(new PlaneGeometry(wallW, wallH), wallMat);
  wall.position.set(0, wallY, WALL_Z);
  wall.receiveShadow = true;
  wall.renderOrder = LAYER.backdrop.order;
  group.add(wall);
  let floorTex: CanvasTexture<HTMLCanvasElement | HTMLImageElement> = floorTexture();
  if (floorImg) {
    floorTex = finishTexture(new CanvasTexture(floorImg));
    floorTex.wrapS = floorTex.wrapT = RepeatWrapping;
    floorTex.repeat.set(10, 4);
  }
  const floorMat = new MeshStandardMaterial({ map: floorTex, roughness: 0.95, metalness: 0 });
  mats.push(floorMat);
  const floor = new Mesh(new PlaneGeometry(32, 12), floorMat);
  floor.rotation.x = -Math.PI / 2;
  floor.position.set(0, 0, WALL_Z + 6);
  floor.receiveShadow = true;
  floor.renderOrder = LAYER.backdrop.order + 1;
  group.add(floor);

  const add = (name: string, tex: CanvasTexture, w: number, h: number, x: number, y: number, z: number, order: number, from: number, to: number): Mesh => {
    const hinge = new Group();
    hinge.name = `pop:${name}`;
    hinge.position.set(x, y, z);
    const m = pieceMesh(tex, w, h, order, mats, a2c);
    hinge.add(m);
    group.add(hinge);
    pieces.push({ hinge, from, to, name });
    return m;
  };

  // ---- 牆前景片（貼著牆立起）：右上層架與燈籠、左側抽屜櫃（素材背牆已畫了層架，就不再加）
  if (!backImg) add('shelf', paperPiece({ w: 4.4, h: 1.5, seed: 31, draw: (g, W, H) => {
    g.fillStyle = '#a77c52';
    g.fillRect(0, H * 0.78, W, H * 0.12);
    g.fillStyle = 'rgba(70,45,25,0.35)'; g.fillRect(0, H * 0.88, W, H * 0.02);
    g.fillStyle = '#8f6845'; g.fillRect(W * 0.06, H * 0.9, W * 0.03, H * 0.1); g.fillRect(W * 0.91, H * 0.9, W * 0.03, H * 0.1);
    lantern(g, W * 0.15, H * 0.5, H * 0.25, '#f2b765');
    lantern(g, W * 0.37, H * 0.46, H * 0.3, '#f6d58e');
    lantern(g, W * 0.6, H * 0.5, H * 0.25, '#ec9d6c');
    lantern(g, W * 0.82, H * 0.47, H * 0.28, '#f4cfa0');
  } }), 4.4, 1.5, 2.3, 3.05, WALL_Z + 0.08, LAYER.far.order - 40, 0.06, 0.27);

  add('cabinet', paperPiece({ w: 2.3, h: 2.6, seed: 33, draw: (g, W, H) => {
    g.fillStyle = '#b48a5f'; g.fillRect(0, H * 0.04, W, H * 0.96);
    g.fillStyle = '#9c7450'; g.fillRect(0, 0, W, H * 0.06);
    g.strokeStyle = 'rgba(70,45,25,0.55)'; g.lineWidth = 4;
    for (let r = 0; r < 4; r++) for (let k = 0; k < 3; k++) {
      const x = W * (0.06 + k * 0.31), y = H * (0.1 + r * 0.22);
      g.strokeRect(x, y, W * 0.27, H * 0.18);
      g.fillStyle = '#6a4630'; g.beginPath(); g.arc(x + W * 0.135, y + H * 0.09, 6, 0, Math.PI * 2); g.fill();
    }
    // 櫃頂一疊燈籠紙卷
    g.fillStyle = '#f3ead8';
    for (let k = 0; k < 3; k++) { g.beginPath(); g.ellipse(W * (0.25 + k * 0.25), H * 0.03, W * 0.1, H * 0.03, 0, 0, Math.PI * 2); g.fill(); }
  } }), 2.3, 2.6, -5.6, 0, -2.6, LAYER.far.order, 0.06, 0.27);

  // ---- 遠景：竹篾桶與紙卷架（右後）
  add('rack', paperPiece({ w: 1.5, h: 1.7, seed: 35, draw: (g, W, H) => {
    g.fillStyle = '#c99b62';
    g.beginPath(); g.moveTo(W * 0.2, H); g.lineTo(W * 0.27, H * 0.45); g.lineTo(W * 0.73, H * 0.45); g.lineTo(W * 0.8, H); g.fill();
    g.strokeStyle = 'rgba(110,70,30,0.5)'; g.lineWidth = 3;
    for (let k = 1; k < 4; k++) line(g, [[W * 0.22, H * (0.45 + k * 0.13)], [W * 0.78, H * (0.45 + k * 0.13)]], 3, 'rgba(110,70,30,0.45)');
    for (let k = 0; k < 9; k++) line(g, [[W * (0.32 + k * 0.045), H * 0.5], [W * (0.28 + k * 0.055), H * 0.02 + (k % 3) * 8]], 6, '#e2c27f');
  } }), 1.5, 1.7, 4.9, 0, -2.4, LAYER.far.order + 2, 0.08, 0.29);

  // 素材吊燈籠（掛在右上方、兒童頭頂上方很高的地方，遠離操偶線）
  if (lanternImg) {
    const w = 5.6, h = w * lanternImg.naturalHeight / lanternImg.naturalWidth;
    add('lanterns', imagePiece(lanternImg, 4), w + 0.05, h + 0.05, 3.9, 8.2 - h, -2.2, LAYER.far.order + 6, 0.5, 0.71);
  }
  // 素材側翼：竹篾束（左右台口邊）
  if (wingImg) {
    const h = 3.7, w = h * wingImg.naturalWidth / wingImg.naturalHeight;
    add('wing_left', imagePiece(wingImg, 6), w, h, -7.0, -0.05, 2.0, LAYER.fore.order + 2, 0.72, 0.93);
  }

  // ---- 中景：工作台（阿樂叔叔左手扶的桌邊在左端）
  const TABLE = { x0: -2.32, x1: 0.22, top: 1.4, z: -0.75 };
  if (tableImg) {
    // 素材工作台：桌面板在圖高 72.6% 處（量自 bg-workshop-table_v02），桌面高 1.40
    const iw = tableImg.naturalWidth, ih = tableImg.naturalHeight;
    const topFrac = (ih - 216) / ih;
    const h = TABLE.top / topFrac, w = h * iw / ih;
    TABLE.x1 = TABLE.x0 + w * (1 - 16 / iw);
    TABLE.z = -0.85;
    add('bench', imagePiece(tableImg, 6), w * (iw + 8) / iw, h * (ih + 8) / ih, TABLE.x0 + w / 2 - w * 8 / iw, 0, TABLE.z, LAYER.mid.order, 0.27, 0.49);
  } else {
  const tw = TABLE.x1 - TABLE.x0;
  add('bench', paperPiece({ w: tw, h: 1.62, seed: 41, thick: 5, draw: (g, W, H) => {
    const top = H * (1 - 1.4 / 1.62);
    // 桌面（看得到上緣一條桌面）＋前緣
    g.fillStyle = '#c69a6a'; g.fillRect(0, top - H * 0.035, W, H * 0.05);
    g.fillStyle = '#9e7149'; g.fillRect(0, top + H * 0.012, W, H * 0.085);
    g.fillStyle = 'rgba(60,35,20,0.35)'; g.fillRect(0, top + H * 0.092, W, 3);
    // 桌腳與橫撐
    g.fillStyle = '#8b6141';
    g.fillRect(W * 0.03, top + H * 0.09, W * 0.05, H); g.fillRect(W * 0.92, top + H * 0.09, W * 0.05, H);
    g.fillRect(W * 0.03, H * 0.82, W * 0.94, H * 0.035);
    // 桌上：燈籠骨架（竹篾線）、一卷燈籠紙、一束竹篾、筆筒
    const cx = W * 0.62, cy = top - H * 0.16, rx = W * 0.09, ry = H * 0.13;
    g.strokeStyle = '#d8b673'; g.lineWidth = 5;
    for (let k = -2; k <= 2; k++) { g.beginPath(); g.ellipse(cx, cy, rx * Math.abs(k) / 2 + 2, ry, 0, 0, Math.PI * 2); g.stroke(); }
    g.beginPath(); g.ellipse(cx, cy, rx, ry * 0.35, 0, 0, Math.PI * 2); g.stroke();
    g.fillStyle = '#f3ead8'; g.fillRect(W * 0.28, top - H * 0.075, W * 0.2, H * 0.075);
    g.fillStyle = '#e4d6bb'; g.beginPath(); g.ellipse(W * 0.48, top - H * 0.0375, W * 0.012, H * 0.0375, 0, 0, Math.PI * 2); g.fill();
    for (let k = 0; k < 6; k++) line(g, [[W * (0.8 + k * 0.012), top - 2], [W * (0.77 + k * 0.02), top - H * 0.22]], 5, '#e0bd78');
    g.fillStyle = '#8a9cb0'; g.fillRect(W * 0.12, top - H * 0.11, W * 0.06, H * 0.11);
    for (let k = 0; k < 3; k++) line(g, [[W * (0.135 + k * 0.012), top - H * 0.1], [W * (0.125 + k * 0.02), top - H * 0.2]], 4, '#5a4636');
  } }), tw, 1.62, (TABLE.x0 + TABLE.x1) / 2, 0, TABLE.z, LAYER.mid.order, 0.27, 0.49);
  }

  // 圓凳（阿樂叔叔坐的，大多被他擋住）
  add('stool', paperPiece({ w: 0.9, h: 0.98, seed: 43, draw: (g, W, H) => {
    g.fillStyle = '#a07450'; g.beginPath(); g.ellipse(W / 2, H * 0.06, W * 0.46, H * 0.06, 0, 0, Math.PI * 2); g.fill();
    g.fillStyle = '#8a6140';
    g.fillRect(W * 0.12, H * 0.08, W * 0.09, H * 0.92); g.fillRect(W * 0.79, H * 0.08, W * 0.09, H * 0.92);
    g.fillRect(W * 0.45, H * 0.1, W * 0.1, H * 0.9);
    g.fillRect(W * 0.12, H * 0.62, W * 0.76, H * 0.05);
  } }), 0.9, 0.98, -2.6, 0, -0.32, LAYER.mid.order + 4, 0.28, 0.5);

  // ---- 前景：左下一疊燈籠、右下紙卷（畫面邊緣，不擋臉）
  add('fore_left', paperPiece({ w: 2.2, h: 1.1, seed: 51, thick: 6, draw: (g, W, H) => {
    lantern(g, W * 0.28, H * 0.55, H * 0.36, '#e7a25e');
    lantern(g, W * 0.62, H * 0.62, H * 0.32, '#f0c27a');
    g.fillStyle = '#8f6a48'; g.fillRect(0, H * 0.92, W, H * 0.08);
  } }), 2.2, 1.1, -6.6, -0.05, 2.3, LAYER.fore.order, 0.72, 0.93);
  add('fore_right', paperPiece({ w: 2.0, h: 0.8, seed: 53, thick: 6, draw: (g, W, H) => {
    for (let k = 0; k < 3; k++) {
      g.fillStyle = ['#f3ead8', '#efd9b5', '#f6e7c9'][k];
      g.fillRect(W * 0.1, H * (0.25 + k * 0.24), W * 0.78, H * 0.2);
      g.fillStyle = 'rgba(150,120,80,0.6)'; g.beginPath(); g.ellipse(W * 0.88, H * (0.35 + k * 0.24), W * 0.03, H * 0.1, 0, 0, Math.PI * 2); g.fill();
    }
  } }), 2.0, 0.8, 6.4, -0.05, 2.2, LAYER.fore.order + 1, 0.74, 0.95);

  return {
    group, pieces, materials: mats, tableEdge: [TABLE.x0 + 0.1, TABLE.top],
    marks: { ale: { x: -2.6, z: 0 }, xiaoqing: { x: 1.85, z: 0.45 }, xiaoyu: { x: 3.35, z: -0.5 } },
    landmarks: {
      tableTop: { x0: TABLE.x0, x1: TABLE.x1, y: TABLE.top, z: TABLE.z },
      // 圓凳：寬 0.9、高 0.98，座面橢圓橫跨 4%–96%
      stoolTop: { x0: -2.6 - 0.414, x1: -2.6 + 0.414, y: 0.98, z: -0.32 },
    },
  };
}

/** 依 set 進度（0–1）擺好每張景片的鉸鏈角度：平躺（往後倒）→ 立起（略過頭再回正） */
export function applyPopup(pieces: PopPiece[], set: number): void {
  for (const p of pieces) {
    const u = Math.min(1, Math.max(0, (set - p.from) / Math.max(1e-6, p.to - p.from)));
    // 立起曲線：ease-out 到 1.06 再回到 1（厚卡紙的彈性）
    const e = u <= 0 ? 0 : u >= 1 ? 1 : u < 0.78 ? 1.06 * (1 - Math.pow(1 - u / 0.78, 3)) : 1.06 - 0.06 * ((u - 0.78) / 0.22);
    p.hinge.rotation.x = -(1 - e) * Math.PI / 2;
    p.hinge.visible = e > 0.02;
  }
}
