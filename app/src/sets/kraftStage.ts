// kraft_stage：全劇的中性牛皮紙舞台佔位景（還沒做景的 cue 用）。
// 淺牛皮紙背牆（幾張紙拼貼的接縫、纖維）、牛皮紙地板、左右兩片摺紙屏風（隨 set.popup 立起）、前景兩側低矮的摺紙邊。
// 畫面上沒有任何文字或除錯標示；兒童站位的背景保持淺色（背牆自發光 0.3，舞台燈調暗時仍夠亮，同 workshop_g4 的做法）。
import { CanvasTexture, DoubleSide, Group, LinearMipmapLinearFilter, Mesh, MeshStandardMaterial, PlaneGeometry, RepeatWrapping, type Material } from 'three';
import { fibers, finishTexture, makeCanvas } from '../stage/paper';
import { LAYER } from '../stage/layers';
import { seeded } from '../util/math';
import type { BuiltSet, PopPiece, SetEntry } from './types';

const KRAFT_WALL = '#dcc39b';
const KRAFT_FLOOR = '#c4a274';
const KRAFT_DARK = '#8a6a48';

function wallTexture(): CanvasTexture {
  const W = 1800, H = 780;
  const [c, g] = makeCanvas(W, H);
  const r = seeded(101);
  g.fillStyle = KRAFT_WALL;
  g.fillRect(0, 0, W, H);
  // 幾張紙拼貼：每張略有明暗差、接縫處一條淡淡的壓痕
  const cols = 6;
  for (let k = 0; k < cols; k++) {
    const x0 = (W / cols) * k;
    g.fillStyle = `rgba(${k % 2 ? '255,248,232' : '150,110,70'},${0.04 + r() * 0.04})`;
    g.fillRect(x0, 0, W / cols, H);
    g.fillStyle = 'rgba(120,85,50,0.12)';
    g.fillRect(x0 + r() * 4, 0, 3, H);
  }
  for (let i = 0; i < 50; i++) { g.fillStyle = `rgba(255,250,236,${0.04 + r() * 0.05})`; g.fillRect(r() * W, r() * H, 60 + r() * 160, 20 + r() * 80); }
  fibers(g, W, H, 103, 1.6);
  // 上緣一道深一點的紙邊（像舞台背景紙的捲邊），下緣踢腳
  g.fillStyle = 'rgba(110,78,48,0.22)'; g.fillRect(0, 0, W, H * 0.05);
  g.fillStyle = '#cdb088'; g.fillRect(0, H * 0.9, W, H * 0.1);
  g.fillStyle = 'rgba(110,78,48,0.25)'; g.fillRect(0, H * 0.9, W, 3);
  const t = finishTexture(new CanvasTexture(c));
  t.minFilter = LinearMipmapLinearFilter;
  return t;
}

function floorTexture(): CanvasTexture {
  const [c, g] = makeCanvas(1024, 512);
  const r = seeded(107);
  g.fillStyle = KRAFT_FLOOR;
  g.fillRect(0, 0, 1024, 512);
  for (let y = 0; y < 512; y += 128) {
    g.fillStyle = 'rgba(90,62,36,0.18)'; g.fillRect(0, y, 1024, 2);
    g.fillStyle = `rgba(255,240,215,${0.03 + r() * 0.05})`; g.fillRect(0, y + 8, 1024, 110);
  }
  fibers(g, 1024, 512, 109, 1.4);
  const t = finishTexture(new CanvasTexture(c));
  t.wrapS = t.wrapT = RepeatWrapping;
  t.repeat.set(4, 2);
  return t;
}

/** 摺紙屏風（三折，刀切邊、往右下烘進卡紙厚度） */
function screenTexture(seed: number, w: number, h: number): CanvasTexture {
  const ppu = 120;
  const W = Math.round(w * ppu), H = Math.round(h * ppu);
  const [c, g] = makeCanvas(W + 8, H + 8);
  const [art, ag] = makeCanvas(W, H);
  const panels = 3;
  for (let k = 0; k < panels; k++) {
    const x0 = (W / panels) * k, x1 = (W / panels) * (k + 1);
    ag.fillStyle = k % 2 ? '#cfb185' : '#d8bd93';
    ag.beginPath();
    ag.moveTo(x0, H); ag.lineTo(x0 + 6, H * 0.04 + (k % 2) * 10); ag.lineTo(x1 - 6, H * 0.04 + (k % 2) * 10); ag.lineTo(x1, H); ag.closePath();
    ag.fill();
    ag.fillStyle = 'rgba(110,78,48,0.25)'; ag.fillRect(x1 - 3, H * 0.05, 3, H * 0.95);
  }
  ag.save(); ag.globalCompositeOperation = 'source-atop'; fibers(ag, W, H, seed, 1.2); ag.restore();
  const [sil, sg] = makeCanvas(W, H);
  sg.drawImage(art, 0, 0);
  sg.globalCompositeOperation = 'source-in';
  sg.fillStyle = KRAFT_DARK;
  sg.fillRect(0, 0, W, H);
  for (let k = 5; k >= 1; k--) g.drawImage(sil, k * 0.75, k);
  g.drawImage(art, 0, 0);
  const t = finishTexture(new CanvasTexture(c));
  t.minFilter = LinearMipmapLinearFilter;
  return t;
}

/** 前景低矮的摺紙邊（波浪形，像紙剪的草丘；只在畫面兩側） */
function ridgeTexture(seed: number): CanvasTexture {
  const W = 360, H = 120;
  const [c, g] = makeCanvas(W, H);
  const r = seeded(seed);
  g.fillStyle = '#b48d62';
  g.beginPath();
  g.moveTo(0, H);
  for (let x = 0; x <= W; x += 30) g.lineTo(x, H * (0.25 + 0.35 * r()));
  g.lineTo(W, H); g.closePath(); g.fill();
  g.save(); g.globalCompositeOperation = 'source-atop'; fibers(g, W, H, seed + 1, 1.0); g.fillStyle = 'rgba(80,55,30,0.18)'; g.fillRect(0, H * 0.85, W, H * 0.15); g.restore();
  const t = finishTexture(new CanvasTexture(c));
  t.minFilter = LinearMipmapLinearFilter;
  return t;
}

export function buildKraftStage(opts: { alphaToCoverage: boolean }): BuiltSet {
  const group = new Group();
  group.name = 'set:kraft_stage';
  const mats: Material[] = [];
  const pieces: PopPiece[] = [];
  const WALL_Z = -3.6;

  const wallMat = new MeshStandardMaterial({ map: wallTexture(), roughness: 0.96, metalness: 0 });
  wallMat.emissiveMap = wallMat.map;
  wallMat.emissive.setRGB(1, 1, 1);
  wallMat.emissiveIntensity = 0.3;
  wallMat.color.setScalar(0.86);
  mats.push(wallMat);
  const wall = new Mesh(new PlaneGeometry(30, 13), wallMat);
  wall.position.set(0, 13 / 2 - 0.6, WALL_Z);
  wall.receiveShadow = true;
  wall.renderOrder = LAYER.backdrop.order;
  group.add(wall);

  const floorMat = new MeshStandardMaterial({ map: floorTexture(), roughness: 0.95, metalness: 0 });
  mats.push(floorMat);
  const floor = new Mesh(new PlaneGeometry(32, 12), floorMat);
  floor.rotation.x = -Math.PI / 2;
  floor.position.set(0, 0, WALL_Z + 6);
  floor.receiveShadow = true;
  floor.renderOrder = LAYER.backdrop.order + 1;
  group.add(floor);

  const add = (name: string, tex: CanvasTexture, w: number, h: number, x: number, z: number, order: number, from: number, to: number, rotY = 0): void => {
    const hinge = new Group();
    hinge.name = `pop:${name}`;
    hinge.position.set(x, 0, z);
    hinge.rotation.y = rotY;
    const mat = new MeshStandardMaterial({ map: tex, alphaTest: 0.5, side: DoubleSide, roughness: 0.92, metalness: 0, alphaToCoverage: opts.alphaToCoverage });
    mats.push(mat);
    const geo = new PlaneGeometry(w, h);
    geo.translate(0, h / 2, 0);
    const m = new Mesh(geo, mat);
    m.renderOrder = order;
    m.castShadow = true;
    m.receiveShadow = true;
    hinge.add(m);
    group.add(hinge);
    pieces.push({ hinge, from, to, name });
  };
  // 左右摺紙屏風（中後景，畫面邊緣，不擋站位）
  add('screen_left', screenTexture(111, 3.0, 3.4), 3.0, 3.4, -6.2, -2.4, LAYER.far.order, 0.05, 0.4, 0.12);
  add('screen_right', screenTexture(113, 3.0, 3.4), 3.0, 3.4, 6.2, -2.4, LAYER.far.order + 1, 0.15, 0.5, -0.12);
  // 前景兩側低矮紙邊
  add('ridge_left', ridgeTexture(115), 3.0, 1.0, -6.4, 2.3, LAYER.fore.order, 0.55, 0.85);
  add('ridge_right', ridgeTexture(117), 3.0, 1.0, 6.4, 2.3, LAYER.fore.order + 1, 0.6, 0.9);

  return {
    group, pieces, materials: mats,
    marks: {
      ale: { x: -2.8, z: 0 }, chen: { x: -1.2, z: -0.3 }, zhezhe: { x: 0.3, z: 1.1 }, xiaoqing: { x: 1.9, z: 0.45 }, xiaoyu: { x: 3.3, z: -0.5 },
      pinan: { x: 4.6, z: 0 }, lin: { x: 5.5, z: -0.6 }, ye: { x: 6.4, z: -0.2 },
    },
  };
}

export const KRAFT_STAGE: SetEntry = { title: '牛皮紙舞台（佔位景）', build: (ctx) => buildKraftStage({ alphaToCoverage: ctx.alphaToCoverage }) };
