// 示範場景（燈籠工作室佔位）與台口：全部用程式產生的紙片，之後換成 assets/final 的正式景片。
// 畫面上的字一律由程式排版，景片圖裡不放任何文字。
import {
  CanvasTexture, Color, DoubleSide, Group, Mesh, MeshStandardMaterial, PlaneGeometry, RepeatWrapping, Shape, ShapeGeometry,
} from 'three';
import { cutPaperMaterial, cutPaperTexture, finishTexture, paperSheetTexture, makeCanvas, fibers } from './paper';
import { LAYER, STAGE_OPENING, Z_STEP } from './layers';

/** 背景牆：暖色和紙牆、木樑、一扇窗與擺著燈籠的層架（全是平塗，沒有文字） */
function backdropTexture(): CanvasTexture {
  return paperSheetTexture(1600, 760, '#efe0c4', 3, (g, W, H) => {
    // 地腳板
    g.fillStyle = '#c9a77c'; g.fillRect(0, H * 0.86, W, H * 0.14);
    // 木樑
    g.fillStyle = '#8a6142';
    for (const x of [0.06, 0.38, 0.7, 0.96]) g.fillRect(W * x - 14, 0, 28, H * 0.86);
    g.fillRect(0, H * 0.12, W, 22);
    // 窗：淡藍天色＋窗櫺
    const wx = W * 0.44, wy = H * 0.24, ww = W * 0.2, wh = H * 0.3;
    g.fillStyle = '#bcd7e6'; g.fillRect(wx, wy, ww, wh);
    g.fillStyle = 'rgba(255,255,255,0.35)'; g.fillRect(wx, wy + wh * 0.62, ww, wh * 0.38);
    g.fillStyle = '#7a5538';
    g.fillRect(wx - 8, wy - 8, ww + 16, 10); g.fillRect(wx - 8, wy + wh - 2, ww + 16, 10);
    g.fillRect(wx + ww / 2 - 4, wy, 8, wh); g.fillRect(wx, wy + wh / 2 - 4, ww, 8);
    // 層架與燈籠（不發光，不閃爍）
    g.fillStyle = '#7d5a3e';
    g.fillRect(W * 0.74, H * 0.42, W * 0.2, 14);
    const lantern = (x: number, y: number, r: number, col: string): void => {
      g.fillStyle = col; g.beginPath(); g.ellipse(x, y, r, r * 1.15, 0, 0, Math.PI * 2); g.fill();
      g.strokeStyle = 'rgba(90,50,20,0.35)'; g.lineWidth = 3;
      for (let k = -2; k <= 2; k++) { g.beginPath(); g.ellipse(x, y, r * Math.abs(k) / 2.6, r * 1.15, 0, 0, Math.PI * 2); g.stroke(); }
      g.fillStyle = '#5a3d2a'; g.fillRect(x - r * 0.45, y - r * 1.25, r * 0.9, r * 0.2); g.fillRect(x - r * 0.45, y + r * 1.05, r * 0.9, r * 0.2);
    };
    lantern(W * 0.78, H * 0.35, 30, '#e8a24a');
    lantern(W * 0.84, H * 0.35, 26, '#f0c66a');
    lantern(W * 0.9, H * 0.35, 30, '#df8c4a');
    lantern(W * 0.16, H * 0.5, 34, '#f0c66a');
    lantern(W * 0.24, H * 0.52, 28, '#e8a24a');
    g.fillStyle = '#7d5a3e'; g.fillRect(W * 0.1, H * 0.6, W * 0.2, 14);
  });
}

function floorTexture(): CanvasTexture {
  const t = paperSheetTexture(1024, 512, '#b98d62', 5, (g, W, H) => {
    g.strokeStyle = 'rgba(80,50,30,0.25)'; g.lineWidth = 3;
    for (let x = 0; x < W; x += 128) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, H); g.stroke(); }
  });
  t.wrapS = t.wrapT = RepeatWrapping;
  t.repeat.set(3, 1);
  return t;
}

/** 平面紙片（刀切邊）：位置以中心點、底邊對齊 */
function cutPiece(o: { w: number; h: number; color: string; shape: Parameters<typeof cutPaperTexture>[0]['shape']; seed: number;
  x: number; y: number; z: number; order: number; decorate?: (g: CanvasRenderingContext2D, W: number, H: number) => void }): Mesh {
  const m = new Mesh(new PlaneGeometry(o.w, o.h), cutPaperMaterial(cutPaperTexture(o)));
  m.position.set(o.x, o.y + o.h / 2, o.z);
  m.renderOrder = o.order;
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}

export interface WorkshopSet { group: Group; tableEdge: [number, number] }

/** 燈籠工作室佔位景 */
export function buildWorkshop(): WorkshopSet {
  const g = new Group();
  g.name = 'set:workshop';
  const back = new Mesh(new PlaneGeometry(34, 16), new MeshStandardMaterial({ map: backdropTexture(), roughness: 0.95 }));
  back.position.set(0, 7, LAYER.backdrop.z);
  back.receiveShadow = true;
  back.renderOrder = LAYER.backdrop.order;
  g.add(back);

  const floor = new Mesh(new PlaneGeometry(34, 10), new MeshStandardMaterial({ map: floorTexture(), roughness: 0.95 }));
  floor.rotation.x = -Math.PI / 2;
  floor.position.set(0, 0, -0.2);
  floor.receiveShadow = true;
  floor.renderOrder = LAYER.backdrop.order + 1;
  g.add(floor);

  // 中景：工作台（桌面＋兩支腳）與桌上的紙燈籠骨架
  const tz = LAYER.mid.z, to = LAYER.mid.order;
  g.add(cutPiece({ w: 2.6, h: 0.22, color: '#8f6545', shape: 'rect', seed: 21, x: 0.2, y: 1.72, z: tz + Z_STEP * 2, order: to + 2 }));
  g.add(cutPiece({ w: 0.18, h: 1.72, color: '#7a5539', shape: 'rect', seed: 22, x: -0.9, y: 0, z: tz, order: to }));
  g.add(cutPiece({ w: 0.18, h: 1.72, color: '#7a5539', shape: 'rect', seed: 23, x: 1.3, y: 0, z: tz, order: to }));
  g.add(cutPiece({ w: 0.62, h: 0.7, color: '#f2d39a', shape: 'ellipse', seed: 24, x: 0.75, y: 1.92, z: tz + Z_STEP * 3, order: to + 3,
    decorate: (c, W, H) => { c.strokeStyle = 'rgba(120,80,40,0.45)'; c.lineWidth = 3; for (let k = 1; k < 4; k++) { c.beginPath(); c.ellipse(W / 2, H / 2, W * k / 8, H / 2.1, 0, 0, Math.PI * 2); c.stroke(); } } }));
  // 後景：小凳與紙卷
  g.add(cutPiece({ w: 0.9, h: 0.75, color: '#9b7350', shape: 'round', seed: 25, x: 4.8, y: 0, z: LAYER.far.z, order: LAYER.far.order }));
  g.add(cutPiece({ w: 1.6, h: 0.5, color: '#e9d7b4', shape: 'capsule', seed: 26, x: -5.2, y: 0, z: LAYER.far.z + Z_STEP, order: LAYER.far.order + 1 }));

  // 前景：兩側的桂花葉剪紙（畫面邊緣，不擋說話者的臉）
  const leaf = (x: number, flip: number, seed: number): Mesh => {
    const m = cutPiece({ w: 2.2, h: 1.6, color: '#5f7d4a', shape: 'ellipse', seed, x, y: -0.4, z: LAYER.fore.z, order: LAYER.fore.order,
      decorate: (c, W, H) => { c.strokeStyle = 'rgba(30,50,20,0.5)'; c.lineWidth = 5; c.beginPath(); c.moveTo(W * 0.1, H * 0.9); c.quadraticCurveTo(W * 0.5, H * 0.5, W * 0.95, H * 0.15); c.stroke(); } });
    m.rotation.z = 0.5 * flip;
    return m;
  };
  g.add(leaf(-8.4, 1, 31), leaf(8.6, -1, 32));
  return { group: g, tableEdge: [-0.9, 1.94] };
}

/** 台口外框（深色厚卡紙，中間挖出舞台開口）＋上方摺幕＋台口前緣（題卡模式亮起） */
export function buildProscenium(): { group: Group; lip: Mesh } {
  const g = new Group();
  g.name = 'proscenium';
  const { width: ow, height: oh, centerY } = STAGE_OPENING;
  const outer = new Shape();
  outer.moveTo(-22, -6); outer.lineTo(22, -6); outer.lineTo(22, 18); outer.lineTo(-22, 18); outer.closePath();
  const hole = new Shape();
  const r = 0.35, x0 = -ow / 2, x1 = ow / 2, y0 = centerY - oh / 2, y1 = centerY + oh / 2;
  hole.moveTo(x0, y0); hole.lineTo(x1, y0); hole.lineTo(x1, y1 - r); hole.quadraticCurveTo(x1, y1, x1 - r, y1);
  hole.lineTo(x0 + r, y1); hole.quadraticCurveTo(x0, y1, x0, y1 - r); hole.closePath();
  outer.holes.push(hole);
  const tex = paperSheetTexture(512, 512, '#3d2b22', 41);
  tex.wrapS = tex.wrapT = RepeatWrapping;
  tex.repeat.set(0.25, 0.25);
  const frameMat = new MeshStandardMaterial({ map: tex, roughness: 0.9, side: DoubleSide });
  const frame = new Mesh(new ShapeGeometry(outer), frameMat);
  frame.position.z = LAYER.proscenium.z;
  frame.renderOrder = LAYER.proscenium.order;
  frame.receiveShadow = true;
  g.add(frame);

  // 開口內緣的淺色紙邊（厚卡紙側邊的暗示）
  const edgeMat = new MeshStandardMaterial({ color: '#b08a5e', roughness: 0.9, side: DoubleSide });
  const edgeH = new PlaneGeometry(ow, 0.12), edgeV = new PlaneGeometry(0.12, oh);
  for (const [geo, x, y] of [[edgeH, 0, y1], [edgeV, x0, centerY], [edgeV, x1, centerY]] as const) {
    const e = new Mesh(geo, edgeMat);
    e.position.set(x, y, LAYER.proscenium.z + 0.01);
    e.renderOrder = LAYER.proscenium.order + 1;
    g.add(e);
  }

  // 上方摺幕（固定，不動）
  const [vc, vg] = makeCanvas(512, 128);
  vg.fillStyle = '#6e2626'; vg.fillRect(0, 0, 512, 128);
  fibers(vg, 512, 128, 43, 1.5);
  vg.fillStyle = '#c9a25a'; vg.fillRect(0, 108, 512, 8);
  const vtex = finishTexture(new CanvasTexture(vc));
  vtex.wrapS = RepeatWrapping; vtex.repeat.set(4, 1);
  const val = new PlaneGeometry(ow + 0.6, 1.0, 120, 2);
  const pos = val.attributes.position;
  for (let i = 0; i < pos.count; i++) pos.setZ(i, 0.12 * (0.5 + 0.5 * Math.cos((pos.getX(i) / (ow + 0.6) + 0.5) * 26 * Math.PI * 2)));
  val.computeVertexNormals();
  const valance = new Mesh(val, new MeshStandardMaterial({ map: vtex, roughness: 0.85, side: DoubleSide }));
  valance.position.set(0, y1 - 0.45, LAYER.curtain.z + 0.2);
  valance.renderOrder = LAYER.curtain.order + 5;
  valance.castShadow = false;
  g.add(valance);

  // 台口前緣：題卡模式時慢慢亮起（自發光漸變，不閃爍）
  const lipMat = new MeshStandardMaterial({ color: '#d9b77a', emissive: new Color('#ffcf7a'), emissiveIntensity: 0, roughness: 0.8 });
  const lip = new Mesh(new PlaneGeometry(ow + 1, 0.22), lipMat);
  lip.position.set(0, y0 + 0.02, LAYER.proscenium.z + 0.02);
  lip.renderOrder = LAYER.proscenium.order + 2;
  g.add(lip);
  return { group: g, lip };
}
