// 摺層紙布幕（FX5；v1.2 第 13.2 節「不能把兩塊平面左右滑開當成最終成品」）：
// 兩片手風琴式摺紙。每片由 P 個平面摺頁組成，紙的總長固定：收攏時每頁的水平投影變短、摺深就變深
// （d = √(w² − s²)），像真的摺紙往兩側收；摺頁是平面（每頁一個法線），主光從左上打下來，
// 摺頁一明一暗。下緣有一條深色紙邊與金色細線。合攏時仍保留淺摺痕，看得出是摺紙。
// 光敏：布幕顏色是暗紅褐（R/(R+G+B) < 0.8，不算飽和紅），摺頁明暗差小，區域平均亮度的變化遠低於門檻。
import { BufferAttribute, BufferGeometry, CanvasTexture, DoubleSide, Group, LinearMipmapLinearFilter, Mesh, MeshStandardMaterial, type Material } from 'three';
import { finishTexture, makeCanvas, fibers } from './paper';
import { lerp } from '../util/math';

function curtainTexture(base: string, seed: number): CanvasTexture {
  const [c, g] = makeCanvas(256, 1024);
  g.fillStyle = base;
  g.fillRect(0, 0, 256, 1024);
  // 紙的直向纖維
  for (let x = 0; x < 256; x += 3) { g.fillStyle = `rgba(0,0,0,${0.025 + ((x * 37) % 11) / 260})`; g.fillRect(x, 0, 1, 1024); }
  fibers(g, 256, 1024, seed, 1.4);
  // 下緣：深色紙邊＋金色細線
  g.fillStyle = 'rgba(45,16,12,0.55)'; g.fillRect(0, 960, 256, 64);
  g.fillStyle = '#c9a25a'; g.fillRect(0, 948, 256, 7);
  const t = finishTexture(new CanvasTexture(c));
  t.minFilter = LinearMipmapLinearFilter;
  return t;
}

interface Half { mesh: Mesh; sign: -1 | 1; pos: Float32Array; nor: Float32Array }

export class Curtain {
  readonly group = new Group();
  readonly material: Material;
  private halves: Half[] = [];
  private last = -1;
  readonly halfWidth: number;
  private readonly rows = 10;

  constructor(private o: { width: number; height: number; bottom: number; z: number; pleats: number; color: string; renderOrder: number }) {
    this.halfWidth = o.width / 2 + 0.25; // 中間略為重疊
    const tex = curtainTexture(o.color, 11);
    const mat = new MeshStandardMaterial({ map: tex, side: DoubleSide, roughness: 0.86, metalness: 0, flatShading: false });
    this.material = mat;
    const P = o.pleats;
    for (const sign of [-1, 1] as const) {
      // 每個摺頁獨立的頂點（摺線處不共用頂點 → 每頁一個平面法線）
      const vCount = P * (this.rows + 1) * 2;
      const pos = new Float32Array(vCount * 3), nor = new Float32Array(vCount * 3), uv = new Float32Array(vCount * 2);
      const idx: number[] = [];
      for (let p = 0; p < P; p++) {
        for (let r = 0; r <= this.rows; r++) {
          const base = (p * (this.rows + 1) + r) * 2;
          const v = r / this.rows;
          uv.set([(p) / P * (P / 3), v, (p + 1) / P * (P / 3), v], base * 2);
          if (r < this.rows) {
            // 讓正面朝向觀眾（左片的摺頁由外往內是 +x，右片是 −x，繞行方向相反）
            const a = base, b = base + 1, c = base + 2, d = base + 3;
            if (sign < 0) idx.push(a, b, c, b, d, c); else idx.push(a, c, b, b, c, d);
          }
        }
      }
      const geo = new BufferGeometry();
      geo.setAttribute('position', new BufferAttribute(pos, 3));
      geo.setAttribute('normal', new BufferAttribute(nor, 3));
      geo.setAttribute('uv', new BufferAttribute(uv, 2));
      geo.setIndex(idx);
      const mesh = new Mesh(geo, mat);
      mesh.renderOrder = o.renderOrder;
      // 布幕不投影：在台口前方投下的大片影子會把角色壓暗
      mesh.castShadow = false;
      mesh.receiveShadow = false;
      mesh.frustumCulled = false;
      this.group.add(mesh);
      this.halves.push({ mesh, sign, pos, nor });
    }
    this.group.position.z = o.z;
    this.setOpen(0);
  }

  /** 0＝合攏、1＝全開（緩動由 cue 的 ease 決定，這裡是線性對應） */
  setOpen(f: number): void {
    if (Math.abs(f - this.last) < 1e-5) return;
    this.last = f;
    const P = this.o.pleats;
    const full = this.halfWidth;
    // 紙長固定（比半幅寬一點，合攏時兩片在中央重疊 0.3、仍留淺摺痕）
    const w0 = (full + 0.75) / P;
    const extent = lerp(full + 0.3, full * 0.12, f); // 每片目前的水平寬度
    const s = extent / P;
    const depth = Math.sqrt(Math.max(0, w0 * w0 - s * s));
    const outer = this.o.width / 2 + 0.25;
    for (const h of this.halves) {
      for (let p = 0; p < P; p++) {
        // 摺頁 p 從摺線 p 到 p+1；z 在 0 與 −depth 之間交替
        const za = p % 2 === 0 ? 0 : -depth, zb = p % 2 === 0 ? -depth : 0;
        const xa = h.sign * (outer - p * s), xb = h.sign * (outer - (p + 1) * s);
        // 法線：摺頁平面的法線（朝向觀眾）
        const tx = xb - xa, tz = zb - za;
        let nx = -tz, nz = tx;
        if (nz < 0) { nx = -nx; nz = -nz; }
        const nl = Math.hypot(nx, nz) || 1;
        nx /= nl; nz /= nl;
        for (let r = 0; r <= this.rows; r++) {
          const v = r / this.rows;
          // 下緣在收攏時略往中央垂（紙的重量），越靠內緣越明顯
          const sag = 0.18 * f * (1 - v) * (1 - v);
          const base = (p * (this.rows + 1) + r) * 2;
          const y = this.o.bottom + v * this.o.height;
          const k = base * 3;
          h.pos[k] = xa - h.sign * sag * (p / P); h.pos[k + 1] = y; h.pos[k + 2] = za;
          h.pos[k + 3] = xb - h.sign * sag * ((p + 1) / P); h.pos[k + 4] = y; h.pos[k + 5] = zb;
          h.nor[k] = nx; h.nor[k + 1] = 0; h.nor[k + 2] = nz;
          h.nor[k + 3] = nx; h.nor[k + 4] = 0; h.nor[k + 5] = nz;
        }
      }
      // 右片略往前，中央重疊處不會共平面閃爍
      if (h.sign > 0) for (let k = 2; k < h.pos.length; k += 3) h.pos[k] += 0.025;
      const geo = h.mesh.geometry;
      geo.attributes.position.needsUpdate = true;
      geo.attributes.normal.needsUpdate = true;
      geo.computeBoundingSphere();
    }
  }

  /** 目前每片的可見寬度比例（測試用：布幕移動時間） */
  get openAmount(): number { return this.last; }
}
