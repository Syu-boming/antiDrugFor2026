// 折折（摺紙貓）用的「摺紙」幾何與材質（FX13）。
// - 和剪紙人物的對比：剪紙＝平面刀切輪廓＋白紙芯描邊；摺紙＝平整的小面（每個面明暗不同）＋清楚的摺痕線＋看得到的紙厚與正反兩色。
// - 紙：正面淺橙、背面白（燈籠紙兩面色）；摺過去的部分露出白色背面。
// - 摺痕：網格裡兩個相鄰三角形的夾角 > CREASE_DEG，或是紙的邊緣，就在那條邊畫一道細的暗線（以重心座標＋fwidth 算，約 1 px，
//   不隨距離變粗變細、不閃）；同一平面上的三角化對角線不畫。
// - 紙厚：薄片（slab）＝正面、背面、側邊三部分，側邊用紙芯色。
// - 材質：MeshStandardMaterial 啞光（roughness 0.93、metalness 0）、平面著色、雙面；背面顏色由 aBack 屬性指定（單層紙用）。
//   不用自發光（燈籠例外，見 zhezhe_forms.ts）、不用高光貼圖，所以變形時不會有閃光。
import {
  BackSide, BufferAttribute, BufferGeometry, CanvasTexture, Color, DoubleSide, MeshBasicMaterial, MeshStandardMaterial,
  RepeatWrapping, SRGBColorSpace, Vector3, type Texture,
} from 'three';
import { ConvexHull } from 'three/examples/jsm/math/ConvexHull.js';
import { seeded } from '../util/math';

/** 折折色票（sRGB）。和全劇色票協調：暖米色背景上用淺杏橙＋暖白，深色只用暖褐。 */
export const ZZ_COLORS = {
  /** 燈籠紙正面：淺橙（杏色）。比舞台中間調（牛皮紙桌、地板 L*≈60）亮，暗背景靠紙色、亮背景靠暖褐外輪廓 */
  front: '#f6c79c',
  /** 燈籠紙背面：暖白 */
  back: '#fdf6ea',
  /** 紙厚側邊（紙芯） */
  edge: '#e8d2b2',
  /** 眼睛、嘴（暖深褐，不用純黑） */
  ink: '#3f281d',
  /** 鼻子 */
  nose: '#a7604c',
  /** 腮紅 */
  blush: '#f09a80',
  /** 外輪廓細線（暖褐） */
  outline: '#5a3826',
  /** 燈籠骨架（竹） */
  bamboo: '#9c6f45',
} as const;

/** 紙厚（以折折身高 1 為單位） */
export const PAPER_T = 0.0095;
/** 夾角超過這個角度才畫摺痕線 */
export const CREASE_DEG = 9;

export type V3 = [number, number, number];
export const v3 = (x: number, y: number, z: number): Vector3 => new Vector3(x, y, z);

const linear = (hex: string): Color => new Color(hex); // three 的 Color.set 會把 sRGB 轉成線性工作色彩空間

interface Tri {
  p: [Vector3, Vector3, Vector3];
  front: Color;
  back: Color;
  /** 不畫摺痕（紙厚側邊） */
  noCrease?: boolean;
  /** 指定隱藏哪幾條邊（對應頂點 0、1、2 的對邊）；未指定時自動判斷 */
  hide?: [boolean, boolean, boolean];
}

/** 累積三角形，最後產生帶摺痕屬性的 BufferGeometry */
export class PaperBuilder {
  readonly tris: Tri[] = [];

  tri(a: Vector3, b: Vector3, c: Vector3, front: string | Color, back?: string | Color, extra: Partial<Tri> = {}): this {
    const f = typeof front === 'string' ? linear(front) : front;
    const bk = back === undefined ? f : typeof back === 'string' ? linear(back) : back;
    this.tris.push({ p: [a.clone(), b.clone(), c.clone()], front: f, back: bk, ...extra });
    return this;
  }

  /** 凸多邊形（扇形三角化；頂點逆時針＝正面朝向） */
  poly(pts: Vector3[], front: string | Color, back?: string | Color, extra: Partial<Tri> = {}): this {
    for (let i = 1; i < pts.length - 1; i++) this.tri(pts[0], pts[i], pts[i + 1], front, back, extra);
    return this;
  }

  /**
   * 有厚度的紙片：凸多邊形（共平面），正面（法線方向）用 front、背面用 back、側邊用紙芯色。
   * @param offset 整片沿法線平移（疊層用）
   */
  slab(pts: Vector3[], front: string, back: string, t = PAPER_T, offset = 0, edge: string = ZZ_COLORS.edge): this {
    const n = newellNormal(pts);
    const fp = pts.map((p) => p.clone().addScaledVector(n, offset + t / 2));
    const bp = pts.map((p) => p.clone().addScaledVector(n, offset - t / 2));
    this.poly(fp, front);
    this.poly([...bp].reverse(), back);
    const m = pts.length;
    for (let i = 0; i < m; i++) {
      const j = (i + 1) % m;
      this.tri(fp[i], bp[i], bp[j], edge, edge, { noCrease: true });
      this.tri(fp[i], bp[j], fp[j], edge, edge, { noCrease: true });
    }
    return this;
  }

  /** 凸包實心（頭、身體、腳）；color(重心, 法線) 決定每個面的顏色 */
  hull(pts: Vector3[], color: (c: Vector3, n: Vector3) => string): this {
    const h = new ConvexHull().setFromPoints(pts);
    for (const face of h.faces) {
      const vs: Vector3[] = [];
      let e = face.edge;
      do { vs.push(e.head().point.clone()); e = e.next; } while (e !== face.edge);
      const c = vs.reduce((s, v) => s.add(v), new Vector3()).multiplyScalar(1 / vs.length);
      const col = color(c, face.normal.clone());
      this.poly(vs, col);
    }
    return this;
  }

  get count(): number { return this.tris.length; }

  /**
   * 產生幾何：position、normal（平面）、color（正面色）、aBack（背面色）、aEdge（摺痕用重心座標）、uv（每個面各自的平面投影，紙纖維用）
   */
  build(uvScale = 2.6): BufferGeometry {
    const n = this.tris.length;
    const pos = new Float32Array(n * 9), nor = new Float32Array(n * 9), col = new Float32Array(n * 9), bak = new Float32Array(n * 9);
    const edg = new Float32Array(n * 9), uv = new Float32Array(n * 6);
    const normals = this.tris.map((t) => triNormal(t.p[0], t.p[1], t.p[2]));
    // 邊 → 三角形
    const key = (a: Vector3): string => `${Math.round(a.x * 1e4)},${Math.round(a.y * 1e4)},${Math.round(a.z * 1e4)}`;
    const edgeMap = new Map<string, number[]>();
    const ek = (a: Vector3, b: Vector3): string => { const ka = key(a), kb = key(b); return ka < kb ? `${ka}|${kb}` : `${kb}|${ka}`; };
    this.tris.forEach((t, i) => {
      for (let k = 0; k < 3; k++) {
        const s = ek(t.p[(k + 1) % 3], t.p[(k + 2) % 3]);
        const list = edgeMap.get(s);
        if (list) list.push(i); else edgeMap.set(s, [i]);
      }
    });
    const cosTh = Math.cos((CREASE_DEG * Math.PI) / 180);
    const up = new Vector3(0, 1, 0), ax = new Vector3(1, 0, 0);
    this.tris.forEach((t, i) => {
      const nn = normals[i];
      // 每條邊要不要畫
      const show = [false, false, false];
      for (let k = 0; k < 3; k++) {
        if (t.noCrease) break;
        if (t.hide) { show[k] = !t.hide[k]; continue; }
        const list = edgeMap.get(ek(t.p[(k + 1) % 3], t.p[(k + 2) % 3]))!;
        const others = list.filter((j) => j !== i);
        if (others.length !== 1) { show[k] = true; continue; }
        const o = others[0];
        if (this.tris[o].noCrease) { show[k] = true; continue; } // 和紙厚側邊相接＝紙的邊緣
        show[k] = nn.dot(normals[o]) < cosTh;
      }
      // 平面 UV：同一平面的三角形共用同一組軸，紙纖維不會在三角化對角線上斷開
      const U = Math.abs(nn.dot(up)) > 0.9 ? new Vector3().crossVectors(nn, ax).normalize() : new Vector3().crossVectors(up, nn).normalize();
      const V = new Vector3().crossVectors(nn, U);
      for (let k = 0; k < 3; k++) {
        const p = t.p[k], o = i * 9 + k * 3;
        pos[o] = p.x; pos[o + 1] = p.y; pos[o + 2] = p.z;
        nor[o] = nn.x; nor[o + 1] = nn.y; nor[o + 2] = nn.z;
        col[o] = t.front.r; col[o + 1] = t.front.g; col[o + 2] = t.front.b;
        bak[o] = t.back.r; bak[o + 1] = t.back.g; bak[o + 2] = t.back.b;
        for (let c = 0; c < 3; c++) edg[o + c] = c === k ? 1 : (show[c] ? 0 : 1);
        uv[i * 6 + k * 2] = p.dot(U) * uvScale; uv[i * 6 + k * 2 + 1] = p.dot(V) * uvScale;
      }
    });
    const g = new BufferGeometry();
    g.setAttribute('position', new BufferAttribute(pos, 3));
    g.setAttribute('normal', new BufferAttribute(nor, 3));
    g.setAttribute('color', new BufferAttribute(col, 3));
    g.setAttribute('aBack', new BufferAttribute(bak, 3));
    g.setAttribute('aEdge', new BufferAttribute(edg, 3));
    g.setAttribute('uv', new BufferAttribute(uv, 2));
    g.computeBoundingSphere();
    return g;
  }
}

export function triNormal(a: Vector3, b: Vector3, c: Vector3): Vector3 {
  return new Vector3().subVectors(b, a).cross(new Vector3().subVectors(c, a)).normalize();
}

export function newellNormal(pts: Vector3[]): Vector3 {
  const n = new Vector3();
  for (let i = 0; i < pts.length; i++) {
    const a = pts[i], b = pts[(i + 1) % pts.length];
    n.x += (a.y - b.y) * (a.z + b.z);
    n.y += (a.z - b.z) * (a.x + b.x);
    n.z += (a.x - b.x) * (a.y + b.y);
  }
  return n.normalize();
}

/** 紙纖維貼圖（很淡，乘在頂點色上；啞光、無高光） */
let fiberTex: CanvasTexture | null = null;
export function paperFiberTexture(): CanvasTexture {
  if (fiberTex) return fiberTex;
  const S = 256;
  const c = document.createElement('canvas');
  c.width = S; c.height = S;
  const g = c.getContext('2d')!;
  g.fillStyle = '#f6f2ec';
  g.fillRect(0, 0, S, S);
  const r = seeded(4217);
  for (let i = 0; i < 900; i++) {
    const x = r() * S, y = r() * S, len = 3 + r() * 14, a = r() * Math.PI;
    g.strokeStyle = r() < 0.55 ? `rgba(255,255,255,${0.25 + r() * 0.35})` : `rgba(120,90,60,${0.05 + r() * 0.08})`;
    g.lineWidth = 0.6 + r() * 0.9;
    // 環繞繪製，貼圖才能無縫重複
    for (const [dx, dy] of [[0, 0], [S, 0], [-S, 0], [0, S], [0, -S]]) {
      g.beginPath(); g.moveTo(x + dx, y + dy); g.lineTo(x + dx + Math.cos(a) * len, y + dy + Math.sin(a) * len); g.stroke();
    }
  }
  const t = new CanvasTexture(c);
  t.colorSpace = SRGBColorSpace;
  t.wrapS = RepeatWrapping;
  t.wrapT = RepeatWrapping;
  t.anisotropy = 4;
  t.needsUpdate = true;
  fiberTex = t;
  return t;
}

/** 存在感：紙面加一點和紙色成正比的自發光（常數，不閃），舞台燈調暗（題卡模式）時折折仍看得清楚 */
export const presenceUniform = { value: 0.06 };

export interface PaperMaterialOptions {
  /** 摺痕線的明度倍率（0.7＝暗三成） */
  crease?: number;
  /** 摺痕線寬（螢幕像素） */
  creaseWidth?: number;
  map?: Texture | null;
  /** 存在感 uniform（預設共用 presenceUniform） */
  presence?: { value: number };
  /** 燈光（主光、補光、半球光）的反應倍率 0–1。摺紙造型的大片紙用 0.5：紙片轉向時明暗起伏減半（光敏），差額由 presence 補 */
  direct?: number;
}

/** 摺紙材質：頂點色（正面）／aBack（背面）＋摺痕線＋紙纖維；雙面、平面著色、啞光 */
export function paperMaterial(o: PaperMaterialOptions = {}): MeshStandardMaterial {
  const m = new MeshStandardMaterial({
    vertexColors: true, map: o.map === undefined ? paperFiberTexture() : o.map, roughness: 0.93, metalness: 0,
    flatShading: true, side: DoubleSide,
  });
  const crease = { value: o.crease ?? 0.72 };
  const width = { value: o.creaseWidth ?? 1.15 };
  m.userData.crease = crease;
  const presence = o.presence ?? presenceUniform;
  const direct = { value: o.direct ?? 1 };
  m.userData.direct = direct;
  m.onBeforeCompile = (sh) => {
    sh.uniforms.uDirect = direct;
    sh.uniforms.uCrease = crease;
    sh.uniforms.uCreaseW = width;
    sh.uniforms.uPresence = presence;
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nattribute vec3 aEdge;\nattribute vec3 aBack;\nvarying vec3 vEdge;\nvarying vec3 vBack;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvEdge = aEdge;\nvBack = aBack;');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', '#include <common>\nuniform float uCrease;\nuniform float uCreaseW;\nuniform float uPresence;\nuniform float uDirect;\nvarying vec3 vEdge;\nvarying vec3 vBack;')
      .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\n  totalEmissiveRadiance += diffuseColor.rgb * uPresence;')
      .replace('#include <lights_fragment_end>', '#include <lights_fragment_end>\n  reflectedLight.directDiffuse *= uDirect;\n  reflectedLight.directSpecular *= uDirect;\n  reflectedLight.indirectDiffuse *= uDirect;')
      .replace('#include <color_fragment>', `#if defined( USE_COLOR )
  diffuseColor.rgb *= gl_FrontFacing ? vColor.rgb : vBack;
#endif
  {
    vec3 fw = max(fwidth(vEdge), vec3(1e-5));
    vec3 e3 = smoothstep(fw * 0.3, fw * (0.3 + uCreaseW), vEdge);
    float e = min(min(e3.x, e3.y), e3.z);
    diffuseColor.rgb *= mix(uCrease, 1.0, e);
  }`);
  };
  m.customProgramCacheKey = () => 'zhezhe-paper-v3';
  return m;
}

/** 外輪廓（背面擴張殼）：沿平滑法線外推 w，只畫背面，形成細的暖褐輪廓 */
export function outlineGeometry(src: BufferGeometry, w: number): BufferGeometry {
  const p = src.getAttribute('position') as BufferAttribute;
  const n = p.count;
  const key = (i: number): string => `${Math.round(p.getX(i) * 1e4)},${Math.round(p.getY(i) * 1e4)},${Math.round(p.getZ(i) * 1e4)}`;
  const acc = new Map<string, Vector3>();
  const a = new Vector3(), b = new Vector3(), c = new Vector3();
  for (let t = 0; t < n; t += 3) {
    a.fromBufferAttribute(p, t); b.fromBufferAttribute(p, t + 1); c.fromBufferAttribute(p, t + 2);
    const fn = new Vector3().subVectors(b, a).cross(new Vector3().subVectors(c, a));
    if (fn.lengthSq() < 1e-14) continue;
    fn.normalize();
    for (let k = 0; k < 3; k++) {
      const s = key(t + k);
      const v = acc.get(s);
      if (v) v.add(fn); else acc.set(s, fn.clone());
    }
  }
  const out = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    const s = acc.get(key(i));
    const d = s && s.lengthSq() > 1e-10 ? s.clone().normalize() : new Vector3();
    out[i * 3] = p.getX(i) + d.x * w; out[i * 3 + 1] = p.getY(i) + d.y * w; out[i * 3 + 2] = p.getZ(i) + d.z * w;
  }
  const g = new BufferGeometry();
  g.setAttribute('position', new BufferAttribute(out, 3));
  g.computeBoundingSphere();
  return g;
}

export function outlineMaterial(): MeshBasicMaterial {
  return new MeshBasicMaterial({ color: ZZ_COLORS.outline, side: BackSide });
}

/** 臉上的平面圖形（眼、嘴、鼻）：暖深褐、啞光，跟著舞台燈明暗 */
export function inkMaterial(color: string = ZZ_COLORS.ink): MeshStandardMaterial {
  return new MeshStandardMaterial({ color, roughness: 1, metalness: 0, side: DoubleSide });
}
