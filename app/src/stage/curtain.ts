// 布幕（佔位版摺層幾何，之後換正式布幕；FX5）：
// 兩片多段網格，打開時往兩側收攏，收攏得越緊摺子越深（布料總長大致守恆），下緣略往內垂，
// 每次更新重算法線，讓側光在摺層上產生明暗。不是兩塊平面左右滑開。
import { BufferAttribute, CanvasTexture, DoubleSide, Group, Mesh, MeshStandardMaterial, PlaneGeometry, RepeatWrapping } from 'three';
import { finishTexture, makeCanvas, fibers } from './paper';
import { ease, lerp } from '../util/math';

function curtainTexture(base: string, seed: number): CanvasTexture {
  const [c, g] = makeCanvas(256, 512);
  g.fillStyle = base;
  g.fillRect(0, 0, 256, 512);
  // 紙布的直向纖維與淡淡的橫向摺痕
  for (let x = 0; x < 256; x += 3) {
    g.fillStyle = `rgba(0,0,0,${0.03 + ((x * 37) % 11) / 200})`;
    g.fillRect(x, 0, 1, 512);
  }
  for (let y = 40; y < 512; y += 96) { g.fillStyle = 'rgba(255,230,210,0.05)'; g.fillRect(0, y, 256, 2); }
  fibers(g, 256, 512, seed, 1.2);
  // 下緣一條深色滾邊
  g.fillStyle = 'rgba(40,10,10,0.35)';
  g.fillRect(0, 488, 256, 24);
  const t = finishTexture(new CanvasTexture(c));
  t.wrapS = RepeatWrapping;
  return t;
}

interface Half { mesh: Mesh; sign: -1 | 1; u: Float32Array; v: Float32Array }

export class Curtain {
  readonly group = new Group();
  private halves: Half[] = [];
  private last = -1;
  readonly halfWidth: number;

  constructor(private o: { width: number; height: number; bottom: number; z: number; pleats: number; color: string; renderOrder: number }) {
    this.halfWidth = o.width / 2 + 0.25; // 中間略為重疊
    const tex = curtainTexture(o.color, 11);
    tex.repeat.set(o.pleats / 2, 1);
    const mat = new MeshStandardMaterial({ map: tex, side: DoubleSide, roughness: 0.82, metalness: 0 });
    for (const sign of [-1, 1] as const) {
      const geo = new PlaneGeometry(this.halfWidth, o.height, 140, 12);
      const pos = geo.attributes.position as BufferAttribute;
      const u = new Float32Array(pos.count), v = new Float32Array(pos.count);
      for (let i = 0; i < pos.count; i++) {
        // u：0＝外緣（台口側邊），1＝內緣（舞台中央）
        const lx = pos.getX(i) / this.halfWidth + 0.5;
        u[i] = sign < 0 ? lx : 1 - lx;
        v[i] = pos.getY(i) / o.height + 0.5;
      }
      const mesh = new Mesh(geo, mat);
      mesh.renderOrder = o.renderOrder;
      // 布幕不投影：在台口前方投下的大片影子會把角色壓暗（受影響者的膚色、服裝不能變）
      mesh.castShadow = false;
      mesh.receiveShadow = true;
      mesh.frustumCulled = false;
      this.group.add(mesh);
      this.halves.push({ mesh, sign, u, v });
    }
    this.group.position.z = o.z;
    this.setOpen(0);
  }

  /** 0＝合攏、1＝全開 */
  setOpen(f: number): void {
    if (Math.abs(f - this.last) < 1e-5) return;
    this.last = f;
    const e = ease('heavy', f);
    const full = this.halfWidth;
    const extent = full * lerp(1, 0.13, e); // 收攏後剩下的寬度
    const gather = 1 - extent / full;
    const depth = 0.1 + 0.34 * gather;
    const outer = this.o.width / 2 + 0.25;
    for (const h of this.halves) {
      const pos = h.mesh.geometry.attributes.position as BufferAttribute;
      for (let i = 0; i < pos.count; i++) {
        const u = h.u[i], v = h.v[i];
        // 下緣在收攏時略往中央垂（布的重量）
        const drape = 0.35 * gather * (1 - v) * (1 - v) * u;
        const x = h.sign * (outer - u * extent - drape * (1 - gather * 0.5));
        const wav = 1 + 0.15 * Math.sin(v * 3.1 + u * 7.3);
        // 摺子一律往後（-z）凹，布幕最前緣不超過台口框
        const z = -depth * wav * (0.5 - 0.5 * Math.cos(u * this.o.pleats * Math.PI * 2)) - 0.03 * u;
        pos.setXYZ(i, x, this.o.bottom + v * this.o.height, z);
      }
      pos.needsUpdate = true;
      h.mesh.geometry.computeVertexNormals();
      h.mesh.geometry.computeBoundingSphere();
    }
  }
}
