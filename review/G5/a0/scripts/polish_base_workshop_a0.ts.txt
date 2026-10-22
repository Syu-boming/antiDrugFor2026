// 開場（a0_c001–a0_c005）的燈籠店：沿用 G4 燈籠店景（buildWorkshopG4，不改它），再疊上開場需要的程式景片。G5 開場＋第一幕代理。
//   - 劇名紙條（a0_c001）：「紙燈節」程式排版（和署名卡同款字型），浮在畫面上方的紙條上，淡入、停約 3 秒、淡出收起（避開字幕區）
//   - 主燈設計圖（牆上，摺紙貓燈，沒有任何文字）、工作台中央空著的主燈底座（跟著工作台一起立起）、門口風鈴
//     （修正第 2 輪：上方吊燈籠不投影子；摺紙推近鏡位 a0_fold2）
//     （修正第 1 輪：工作台圖中央那個燈籠骨在本景擦掉，讓「空了一塊」看得出來；台口上方的八盞燈改由引擎的台口實景燈負責，本景不再畫）
//   - 回憶小窗（a0_c002）：暖杏色手撕邊紙框從畫面外緣收進來＋景片轉暖色（角色不變色）
//   - 小晴的筆記本特寫（a0_c004）：小窗裡的筆記本，竹骨架與問號一筆一筆畫上（程式畫線）
//   - 風鈴（a0_c004 開頭 S6）：輕輕擺幾下停住
// 每格 update 只依（cue、cue 內秒數、鏡頭）決定畫面＝時間的純函式。動作時間錨在台詞上（配音長度改了會跟著移）。
// 素材：assets/final/sets/workshop_a0/*（review/G5/a0/scripts/build_a01_art.py 程式繪製）。
import {
  CanvasTexture, Color, DoubleSide, Group, LinearMipmapLinearFilter, Mesh, MeshBasicMaterial, MeshStandardMaterial, PlaneGeometry, Vector3,
  type Material, type PerspectiveCamera,
} from 'three';
import { buildWorkshopG4 } from '../stage/workshop';
import { finishTexture, makeCanvas } from '../stage/paper';
import { LAYER } from '../stage/layers';
import type { CameraPreset } from '../stage/layers';
import type { CueTimeline } from '../cues/timeline';
import { clamp, lerp } from '../util/math';
import type { BuiltSet, SetContext, SetEntry } from './types';

// ───────────────────────────── 共用小工具（square_a1.ts 也用） ─────────────────────────────
export const sine01 = (t: number): number => 0.5 - 0.5 * Math.cos(Math.PI * clamp(t));
/** 台詞時間（秒）：ids 依序找第一句在時間軸上的；which＝'start'｜'end'。都找不到回傳 fallback */
export function lineTime(tl: CueTimeline, ids: string[], which: 'start' | 'end' = 'start', fallback = 0): number {
  for (const id of ids) {
    const l = tl.lines.find((x) => x.line.id === id);
    if (l) return which === 'start' ? l.start : l.end;
  }
  return fallback;
}
/** 圖像景片：底邊中央（或 pivot）為原點；w 或 h 擇一（世界單位） */
export function imagePiece(img: HTMLImageElement | undefined, o: { w?: number; h?: number; pivot?: [number, number]; order: number; emissive?: number; basic?: boolean; transparent?: boolean; shadow?: boolean }, mats: Material[]): Mesh | null {
  if (!img) return null;
  const aspect = img.naturalWidth / img.naturalHeight;
  const w = o.w ?? (o.h ?? 1) * aspect, h = o.h ?? w / aspect;
  const tex = finishTexture(new CanvasTexture(img));
  tex.minFilter = LinearMipmapLinearFilter;
  const mat = o.basic
    ? new MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, side: DoubleSide })
    : new MeshStandardMaterial({ map: tex, side: DoubleSide, roughness: 0.92, metalness: 0, ...(o.transparent ? { transparent: true, depthWrite: false } : { alphaTest: 0.5 }) });
  if (o.emissive && mat instanceof MeshStandardMaterial) { mat.emissiveMap = tex; mat.emissive.setRGB(1, 1, 1); mat.emissiveIntensity = o.emissive; }
  mats.push(mat);
  const geo = new PlaneGeometry(w, h);
  const [px, py] = o.pivot ?? [0.5, 0];
  geo.translate((0.5 - px) * w, (0.5 - py) * h, 0);
  const m = new Mesh(geo, mat);
  m.renderOrder = o.order;
  m.castShadow = o.shadow ?? false;
  m.receiveShadow = !o.basic && (o.shadow ?? false);
  return m;
}
/** 畫面疊層（貼在鏡頭前，不受燈光、不寫深度；換景暗片 order 10000 仍蓋在上面） */
export function screenLayer(map: CanvasTexture<HTMLCanvasElement | HTMLImageElement>, order: number): Mesh {
  const mat = new MeshBasicMaterial({ map, transparent: true, depthTest: false, depthWrite: false, toneMapped: false });
  const m = new Mesh(new PlaneGeometry(1, 1), mat);
  m.renderOrder = order;
  m.frustumCulled = false;
  m.visible = false;
  return m;
}
const _f = new Vector3(), _r = new Vector3(), _u = new Vector3();
/** 把疊層放在鏡頭前 dist 處：cx、cy＝畫面中心起算（−0.5～0.5，cy 往上為正），hFrac＝佔畫面高的比例，aspect＝寬高比 */
export function placeOnCamera(m: Mesh, cam: PerspectiveCamera, cx: number, cy: number, hFrac: number, aspect: number, dist = 0.8): void {
  const H = 2 * dist * Math.tan((cam.fov * Math.PI) / 360);
  const W = H * cam.aspect;
  cam.getWorldDirection(_f);
  _r.set(1, 0, 0).applyQuaternion(cam.quaternion);
  _u.set(0, 1, 0).applyQuaternion(cam.quaternion);
  m.position.copy(cam.position).addScaledVector(_f, dist).addScaledVector(_r, cx * W).addScaledVector(_u, cy * H);
  m.quaternion.copy(cam.quaternion);
  m.scale.set(hFrac * H * aspect, hFrac * H, 1);
}

// ───────────────────────────── 鏡位 ─────────────────────────────
const C = (pos: [number, number, number], target: [number, number, number], fov = 20): CameraPreset => ({ pos, target, fov });
export const WORKSHOP_A0_CAMERAS: Record<string, CameraPreset> = {
  /** 工作台右段（燈籠紙在桌上摺成折折）：阿樂叔叔的位置在畫面外 */
  a0_table: C([1.55, 2.12, 9.4], [1.55, 1.95, -0.6]),
  /** 摺紙近景（a0_c002 開頭）：燈籠紙約佔畫面高 27%，摺成折折後約佔畫面高 39%、桌面約在畫面高 67%（字幕區之上） */
  a0_fold: C([0.75, 1.95, 6.6], [0.75, 1.83, -0.6]),
  /** 摺紙鏡位（修正第 2 輪）：和 a0_fold 同距離（折折大小不變），鏡頭略往下看，桌面在畫面高約 62%（上半部空牆少一點） */
  a0_fold2: C([0.75, 1.79, 6.6], [0.75, 1.67, -0.6]),
  /** 工作台中景（a0_c003 開頭）：桌面約在畫面高 66%、折折頭頂約 30%；左邊看得到空底座與設計圖一角 */
  a0_table2: C([0.45, 1.97, 7.4], [0.45, 1.85, -0.6]),
  /** 主燈設計圖近景（牆上的設計圖＋桌上的折折在右下回頭看） */
  a0_design: C([-1.05, 2.38, 9.3], [-1.2, 2.36, -3.5]),
  /** 空著的主燈底座與折折（「骨架不見了！」）：底座在畫面中央 */
  a0_base: C([0.15, 1.88, 6.3], [0.15, 1.72, -0.7]),
  /** 回憶小窗：阿樂叔叔坐在工作台前＋桌上的折折 */
  a0_memory: C([-0.95, 1.95, 12.4], [-0.95, 1.72, -0.5]),
  /** 阿樂叔叔（工作台後面）與折折的雙人中景 */
  a0_ale: C([0.05, 1.95, 11.4], [0.05, 1.72, -0.6]),
  /** 店內全景：孩子從右側進門 */
  a0_shop: C([1.8, 1.62, 14.6], [1.8, 1.42, 0]),
  /** 店內大全景（a0_c004 開頭）：孩子從右側門口走進來（人物小，走路時腿的明暗不觸發細格光敏），走到定點後切到 a0_kids */
  a0_shopwide: C([1.6, 2.65, 20], [1.6, 2.4, 0]),
  /** 孩子與筆記本特寫小窗（右側留白給小窗） */
  a0_kids: C([2.3, 1.66, 13.6], [2.3, 1.46, 0]),
  /** 摺放大鏡（摺成帽子）的笑點：推近約 1.3 倍，折折在台面前緣、小宇旁邊；阿樂叔叔仍在畫面左側 */
  a0_hat: C([1.35, 1.72, 10.4], [1.35, 1.54, 0]),
  /** 台口前緣：折折對全場說話，上方看得到八盞燈 */
  a0_apron: C([0.35, 2.15, 25.0], [0.35, 1.87, 0]),
};

// ───────────────────────────── 位置（世界座標） ─────────────────────────────
const WALL_Z = -3.6;
const DESIGN = { x: -1.6, y: 2.45, w: 1.3 };
const STAND = { x: -0.2, y: 1.36, z: -0.78, w: 1.1 };
const CHIME = { x: 5.35, y: 4.75, z: -1.3, h: 1.12 };
/** 工作台圖（bg-workshop-table_v02，1479×791）上燈籠骨的範圍（像素；桌面在 y＝212）：本景擦掉 */
const TABLE_LANTERN = [[702, 0, 930, 212], [684, 0, 702, 176]] as const;

const WARM = new Color('#ffd9ae');

/** 劇名紙條（a0_c001）：米白紙條＋卡紙厚度＋兩端燕尾；字＝程式排版「紙燈節」（同署名卡 .sig-text：同字型、粗體、深褐、字距 0.14em） */
const TITLE_FONT = '"Microsoft JhengHei", "PingFang TC", "Noto Sans TC", "Heiti TC", sans-serif';
export const TITLE_STRIP = { w: 1100, h: 300 };
function titleStrip(): CanvasTexture {
  const { w: W, h: H } = TITLE_STRIP;
  const [c, g] = makeCanvas(W, H);
  const tail = 70, y0 = 46, y1 = H - 52;
  const shape = (dx: number, dy: number): void => {
    g.beginPath();
    g.moveTo(dx + 18, dy + y0); g.lineTo(dx + W - 18, dy + y0);
    g.lineTo(dx + W - 18 - tail * 0.55, dy + (y0 + y1) / 2); g.lineTo(dx + W - 18, dy + y1);
    g.lineTo(dx + 18, dy + y1); g.lineTo(dx + 18 + tail * 0.55, dy + (y0 + y1) / 2);
    g.closePath();
  };
  g.fillStyle = 'rgba(40,26,16,0.25)'; shape(4, 12); g.fill();          // 柔影
  g.fillStyle = '#6b4a32'; shape(5, 7); g.fill();                       // 卡紙厚度（同署名卡）
  g.fillStyle = '#f4e8d2'; shape(0, 0); g.fill();
  // 紙纖維（固定種子，確定性）
  let seed = 20261021;
  const rnd = (): number => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
  g.save(); shape(0, 0); g.clip();
  for (let i = 0; i < 420; i++) {
    const x = rnd() * W, y = y0 + rnd() * (y1 - y0), l = 6 + rnd() * 16, a = rnd() * Math.PI;
    g.strokeStyle = `rgba(150,110,70,${0.05 + rnd() * 0.07})`; g.lineWidth = 1;
    g.beginPath(); g.moveTo(x, y); g.lineTo(x + Math.cos(a) * l, y + Math.sin(a) * l); g.stroke();
  }
  g.restore();
  // 內框細線（同署名卡 ::before）
  g.strokeStyle = 'rgba(110,70,40,0.55)'; g.lineWidth = 3;
  g.beginPath();
  g.moveTo(96, y0 + 14); g.lineTo(W - 96, y0 + 14); g.moveTo(96, y1 - 14); g.lineTo(W - 96, y1 - 14);
  g.stroke();
  // 字：逐字排（字距 0.14em），置中
  const fs = 136;
  g.font = `700 ${fs}px ${TITLE_FONT}`;
  g.fillStyle = '#3a281c'; g.textBaseline = 'middle';
  const chars = ['紙', '燈', '節'];
  const gap = fs * 0.14;
  const widths = chars.map((ch) => g.measureText(ch).width);
  let x = (W - (widths.reduce((a, b) => a + b, 0) + gap * (chars.length - 1))) / 2;
  const cy = (y0 + y1) / 2 + 4;
  chars.forEach((ch, i) => { g.fillText(ch, x, cy); x += widths[i] + gap; });
  return finishTexture(new CanvasTexture(c));
}

/** 筆記本特寫上逐筆畫的筆畫（右頁：竹骨架燈籠；左頁：大問號）。座標＝notebook 圖的像素（900×600） */
function notebookStrokes(): [number, number][][] {
  const S: [number, number][][] = [];
  const cx = 676, cy = 300, rx = 120, ry = 150;
  const ell = (k: number, n = 40): [number, number][] => Array.from({ length: n + 1 }, (_, i) => { const a = -Math.PI / 2 + (2 * Math.PI * i) / n; return [cx + rx * k * Math.cos(a), cy + ry * Math.sin(a)]; });
  S.push(ell(1));
  S.push(ell(0.5));
  S.push(Array.from({ length: 21 }, (_, i) => { const a = Math.PI * (i / 20); return [cx - rx * Math.cos(a), cy + 0.32 * ry * Math.sin(a)] as [number, number]; }));
  S.push([[cx - 34, cy - ry - 4], [cx + 34, cy - ry - 4]]);
  S.push([[cx - 34, cy + ry + 4], [cx + 34, cy + ry + 4]]);
  // 問號（左頁）
  const q: [number, number][] = [];
  for (let i = 0; i <= 24; i++) { const a = Math.PI * 1.15 - (Math.PI * 1.45 * i) / 24; q.push([225 + 78 * Math.cos(a), 200 - 78 * Math.sin(a)]); }
  q.push([258, 300], [226, 340], [226, 382]);
  S.push(q);
  S.push([[222, 446], [230, 446]]);
  return S;
}

export const WORKSHOP_A0: SetEntry = {
  title: '燈籠店（開場：G4 燈籠店＋劇名紙條、主燈設計圖、空底座、風鈴、回憶小窗、筆記本）',
  cameras: WORKSHOP_A0_CAMERAS,
  build(ctx: SetContext): BuiltSet {
    const ws = buildWorkshopG4({ alphaToCoverage: ctx.alphaToCoverage, image: (id) => ctx.image(id) });
    const group = ws.group;
    group.name = 'set:workshop_a0';
    const mats: Material[] = [...ws.materials];
    const report: string[] = [];
    const im = (n: string): HTMLImageElement | undefined => { const i = ctx.image(`sets/workshop_a0/${n}`); if (!i) report.push(`景 workshop_a0：缺圖 ${n}`); return i; };
    const baseColors = ws.materials.map((m) => (m as MeshStandardMaterial).color?.clone());
    // 圓凳：回憶（a0_c002）阿樂叔叔坐在上面；回到現在（a0_c003 起）他站在工作台後面，凳子收到工作台後方（鏡頭橫移時不會掃過細凳腳）
    const stool = ws.pieces.find((p) => p.name === 'stool')?.hinge;
    const stool0 = stool ? stool.position.clone() : null;

    // 修正第 2 輪：上方吊燈籠不投影子（牆上那排灰色圓影；G4 燈籠店景本身不動，只改本景這一份）
    const lanterns = ws.pieces.find((p) => p.name === 'lanterns')?.hinge;
    lanterns?.traverse((o) => { if ((o as Mesh).isMesh) (o as Mesh).castShadow = false; });
    // 主燈設計圖（貼在牆上，和牆一樣有自發光，兒童身後仍夠亮）
    const design = imagePiece(im('design'), { w: DESIGN.w, order: LAYER.far.order - 30, emissive: 0.3 }, mats);
    if (design) { design.position.set(DESIGN.x, DESIGN.y, WALL_Z + 0.06); design.receiveShadow = true; group.add(design); }
    // 工作台：擦掉圖上中央那個燈籠骨（本景的貼圖是這次建景新做的畫布，不影響 workshop_g4）
    const bench = ws.pieces.find((p) => p.name === 'bench');
    const benchMesh = bench?.hinge.children.find((o): o is Mesh => o instanceof Mesh);
    const benchTex = (benchMesh?.material as MeshStandardMaterial | undefined)?.map as CanvasTexture | undefined;
    const benchCanvas = benchTex?.image as HTMLCanvasElement | undefined;
    if (benchTex && benchCanvas && typeof benchCanvas.getContext === 'function' && benchCanvas.width > 1400) {
      const g = benchCanvas.getContext('2d');
      if (g) { for (const [x0, y0, x1, y1] of TABLE_LANTERN) g.clearRect(x0, y0, x1 - x0, y1 - y0); benchTex.needsUpdate = true; }
    } else report.push('景 workshop_a0：工作台貼圖不是預期的畫布，燈籠骨沒有擦掉');
    // 空著的主燈底座（在工作台面中央；掛在工作台的鉸鏈上，開幕時跟著工作台一起立起）
    const stand = imagePiece(im('stand'), { w: STAND.w, order: LAYER.mid.order + 8, shadow: true }, mats);
    if (stand) {
      if (bench) { const h = bench.hinge.position; stand.position.set(STAND.x - h.x, STAND.y - h.y, STAND.z - h.z); bench.hinge.add(stand); }
      else { stand.position.set(STAND.x, STAND.y, STAND.z); group.add(stand); }
    }
    // 門口風鈴（懸掛點在上緣中央）
    const chimeHinge = new Group();
    chimeHinge.position.set(CHIME.x, CHIME.y, CHIME.z);
    const chime = imagePiece(im('chime'), { h: CHIME.h, pivot: [0.5, 1], order: LAYER.mid.order + 20, shadow: true }, mats);
    if (chime) chimeHinge.add(chime);
    group.add(chimeHinge);
    // 劇名紙條（畫面疊層）
    const title = screenLayer(titleStrip(), 9003);
    group.add(title);

    // 回憶小窗（畫面疊層）
    const memImg = im('memoryframe');
    const memTex = memImg ? finishTexture(new CanvasTexture(memImg)) : null;
    const memory = memTex ? screenLayer(memTex, 9000) : null;
    if (memory) group.add(memory);

    // 筆記本特寫（畫面疊層；筆畫由程式逐筆畫）
    const nbImg = im('notebook');
    const [nbCanvas, nbG] = makeCanvas(900, 600);
    const nbTex = finishTexture(new CanvasTexture(nbCanvas));
    const notebook = nbImg ? screenLayer(nbTex, 9001) : null;
    if (notebook) group.add(notebook);
    const strokes = notebookStrokes();
    const strokeLen = strokes.map((s) => s.slice(1).reduce((a, p, i) => a + Math.hypot(p[0] - s[i][0], p[1] - s[i][1]), 0));
    const total = strokeLen.reduce((a, b) => a + b, 0);
    let nbDrawn = -1;
    const drawNotebook = (p: number): void => {
      const q = Math.round(clamp(p) * 240) / 240;     // 量化（每 1/240 才重畫一次貼圖）
      if (q === nbDrawn || !nbImg) return;
      nbDrawn = q;
      nbG.clearRect(0, 0, 900, 600);
      nbG.drawImage(nbImg, 0, 0, 900, 600);
      nbG.strokeStyle = '#4a3c34'; nbG.lineWidth = 7; nbG.lineCap = 'round'; nbG.lineJoin = 'round';
      let left = q * total;
      strokes.forEach((s, k) => {
        if (left <= 0) return;
        nbG.beginPath();
        nbG.moveTo(s[0][0], s[0][1]);
        let acc = 0;
        for (let i = 1; i < s.length; i++) {
          const seg = Math.hypot(s[i][0] - s[i - 1][0], s[i][1] - s[i - 1][1]);
          if (acc + seg <= left) { nbG.lineTo(s[i][0], s[i][1]); acc += seg; continue; }
          const u = (left - acc) / seg;
          nbG.lineTo(lerp(s[i - 1][0], s[i][0], u), lerp(s[i - 1][1], s[i][1], u));
          acc = left;
          break;
        }
        nbG.stroke();
        left -= strokeLen[k];
      });
      nbTex.needsUpdate = true;
    };

    return {
      group, pieces: ws.pieces, materials: mats, marks: ws.marks, tableEdge: ws.tableEdge,
      landmarks: { ...ws.landmarks, emptyStand: { x0: STAND.x - STAND.w / 2, x1: STAND.x + STAND.w / 2, y: STAND.y + 0.3, z: STAND.z } },
      cameras: WORKSHOP_A0_CAMERAS, report,
      // 修正第 1 輪：主光比 G4 預設（[-7, 13, 16]）更正面、略低——阿樂叔叔站在工作台後（離牆 2 單位），影子只偏約 0.15 單位、
      // 貼在身後，不再在牆上變成一個「脫離身體的人影」；上方吊燈籠的影子也不會掉進畫面上緣
      light: { key: [-1.5, 10, 19], keyIntensity: 0.95 },
      update({ tl, t, camera }) {
        const id = tl.cue.id;
        if (stool && stool0) {
          if (id === 'a0_c003' || id === 'a0_c004' || id === 'a0_c005') stool.position.set(-1.85, stool0.y, -1.4);
          else stool.position.copy(stool0);
        }
        // ---- 劇名紙條（a0_c001）：5.2 秒起 0.6 秒淡入（略放大到原尺寸），停到 8.5 秒，0.6 秒淡出收起；不移動（光敏）
        let ti = 0;
        if (id === 'a0_c001') ti = sine01((t - 5.2) / 0.6) * (1 - sine01((t - 8.5) / 0.6));
        title.visible = ti > 0.001;
        if (title.visible) {
          placeOnCamera(title, camera, 0, 0.29, 0.22 * (0.97 + 0.03 * ti), TITLE_STRIP.w / TITLE_STRIP.h, 0.7);
          (title.material as MeshBasicMaterial).opacity = ti;
        }
        // ---- 回憶小窗（a0_c002）：「是阿樂叔叔把我摺出來的喔」說完前 0.5 秒，紙框只用不透明度淡入（1.4 秒，緩入緩出；
        //      修正第 1 輪：不再從外緣縮放收進來，細格光敏），景片轉暖；淡入完成後 cue 裡才切到回憶鏡位
        let mem = 0;
        if (id === 'a0_c002') mem = sine01((t - (lineTime(tl, ['a0_c002_02'], 'end', 9) - 0.5)) / 1.4);
        if (memory) {
          memory.visible = mem > 0.001;
          if (memory.visible) {
            placeOnCamera(memory, camera, 0, 0, 1.0, 16 / 9, 0.75);
            (memory.material as MeshBasicMaterial).opacity = mem;
          }
        }
        ws.materials.forEach((m, i) => { const c = (m as MeshStandardMaterial).color; const b = baseColors[i]; if (c && b) c.copy(b).lerp(b.clone().multiply(WARM), 0.75 * mem); });
        // ---- 風鈴（a0_c004 開頭 S6）：輕擺，阻尼漸停（擺幅小、慢，不閃）
        let ang = 0;
        if (id === 'a0_c004') { const s = t - 0.15; if (s > 0) ang = 0.13 * Math.exp(-s / 1.6) * Math.sin(2 * Math.PI * 0.85 * s); }
        chimeHinge.rotation.z = ang;
        // ---- 筆記本特寫（a0_c004）：小晴「我記下來」→ 小窗打開、竹骨架與問號逐筆畫上 → 折折開口前收起
        let nb = 0, draw = 0;
        if (id === 'a0_c004') {
          const t0 = lineTime(tl, ['a0_c004_02'], 'start', 3) + 0.55;
          const t1 = lineTime(tl, ['a0_c004_03', 'a0_c004_05'], 'start', t0 + 4) - 0.1;
          nb = sine01((t - t0) / 0.45) * (1 - sine01((t - t1) / 0.45));
          draw = clamp((t - t0 - 0.35) / Math.max(1.2, Math.min(2.8, t1 - t0 - 0.8)));
        }
        if (notebook) {
          notebook.visible = nb > 0.001;
          if (notebook.visible) {
            drawNotebook(draw);
            placeOnCamera(notebook, camera, 0.285, 0.16, 0.4 * (0.94 + 0.06 * nb), 1.5, 0.78);
            (notebook.material as MeshBasicMaterial).opacity = nb;
          }
        }
      },
    };
  },
};
