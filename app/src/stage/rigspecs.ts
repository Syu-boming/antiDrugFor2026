// 佔位紙偶規格（之後依 G2 母版與 P4 操偶系統規格書換成正式拆件）。
// 部件命名：A＝本地 -x 側（面向右時在畫面左邊、靠「危險方位」），B＝本地 +x 側（面向方向）。
// 臉：眼、嘴是獨立部件（眨眼、嘴型換片）；受影響時臉、膚色、服裝都不變（兒童安全界線第 2 條）。
import type { PartSpec, RigSpec } from './rig';

interface HumanDims {
  torsoW: number; torsoH: number; headW: number; headH: number;
  upperArm: number; foreArm: number; hand: number; armW: number;
  thigh: number; shin: number; foot: number; legW: number; pelvisW: number;
}

interface HumanColors { skin: string; hair: string; top: string; sleeve: string; forearm: string; bottom: string; shoe: string; cheek?: string }

/** 臉部細節畫在頭部貼圖上：眉毛與淡淡的腮紅（眼、嘴另外是部件） */
function faceDecor(colors: HumanColors, eyeY: number) {
  return (g: CanvasRenderingContext2D, W: number, H: number): void => {
    const y = H * eyeY;
    g.strokeStyle = 'rgba(60,40,30,0.8)';
    g.lineWidth = Math.max(2, W * 0.025);
    g.lineCap = 'round';
    for (const s of [-1, 1]) {
      g.beginPath();
      g.arc(W / 2 + s * W * 0.19, y - H * 0.02, W * 0.08, Math.PI * 1.15, Math.PI * 1.85);
      g.stroke();
    }
    g.fillStyle = colors.cheek ?? 'rgba(230,120,110,0.22)';
    for (const s of [-1, 1]) { g.beginPath(); g.ellipse(W / 2 + s * W * 0.25, y + H * 0.2, W * 0.08, H * 0.05, 0, 0, Math.PI * 2); g.fill(); }
  };
}

/** 依比例產生一個人形紙偶 */
function human(id: string, d: HumanDims, c: HumanColors): RigSpec {
  const hipY = d.foot * 0.85 + d.shin + d.thigh + 0.1;
  const shoulderY = d.torsoH * 0.9;
  const eyeY = d.headH * 0.5;
  const parts: PartSpec[] = [
    { id: 'pelvis', parent: null, at: [0, hipY], rect: [-d.pelvisW / 2, -0.2, d.pelvisW, 0.38], z: 6, color: c.bottom, shape: 'round' },
    { id: 'torso', parent: 'pelvis', at: [0, 0.1], rect: [-d.torsoW / 2, -0.06, d.torsoW, d.torsoH + 0.06], z: 7, color: c.top, shape: 'trapezoid' },
    { id: 'head', parent: 'torso', at: [0, d.torsoH - 0.04], rect: [-d.headW / 2, 0, d.headW, d.headH], z: 12, color: c.skin, shape: 'ellipse',
      decorate: faceDecor(c, 1 - (eyeY / d.headH)) },
    { id: 'hair', parent: 'head', at: [0, d.headH * 0.56], rect: [-d.headW * 0.54, 0, d.headW * 1.08, d.headH * 0.52], z: 13, color: c.hair, shape: 'cap' },
    { id: 'eyeL', parent: 'head', at: [-d.headW * 0.19, eyeY], rect: [-0.03, -0.038, 0.06, 0.076], z: 14, color: '#2a1d16', shape: 'ellipse' },
    { id: 'eyeR', parent: 'head', at: [d.headW * 0.19, eyeY], rect: [-0.03, -0.038, 0.06, 0.076], z: 14, color: '#2a1d16', shape: 'ellipse' },
    { id: 'mouth', parent: 'head', at: [0, d.headH * 0.24], rect: [-0.065, -0.035, 0.13, 0.07], z: 14, color: '#6e3a32', shape: 'ellipse' },
    // A 側手臂（操偶線扣在這隻手）
    { id: 'upperArmA', parent: 'torso', at: [-d.torsoW * 0.52, shoulderY], rect: [-d.armW / 2, -d.upperArm - 0.06, d.armW, d.upperArm + 0.14], z: 8, color: c.sleeve, shape: 'capsule' },
    { id: 'foreArmA', parent: 'upperArmA', at: [0, -d.upperArm], rect: [-d.armW * 0.42, -d.foreArm - 0.04, d.armW * 0.84, d.foreArm + 0.1], z: 9, color: c.forearm, shape: 'capsule' },
    { id: 'handA', parent: 'foreArmA', at: [0, -d.foreArm], rect: [-d.hand * 0.42, -d.hand, d.hand * 0.84, d.hand * 1.12], z: 10, color: c.skin, shape: 'hand' },
    // B 側手臂（面向方向）
    { id: 'upperArmB', parent: 'torso', at: [d.torsoW * 0.52, shoulderY], rect: [-d.armW / 2, -d.upperArm - 0.06, d.armW, d.upperArm + 0.14], z: 15, color: c.sleeve, shape: 'capsule' },
    { id: 'foreArmB', parent: 'upperArmB', at: [0, -d.upperArm], rect: [-d.armW * 0.42, -d.foreArm - 0.04, d.armW * 0.84, d.foreArm + 0.1], z: 16, color: c.forearm, shape: 'capsule' },
    { id: 'handB', parent: 'foreArmB', at: [0, -d.foreArm], rect: [-d.hand * 0.42, -d.hand, d.hand * 0.84, d.hand * 1.12], z: 17, color: c.skin, shape: 'hand' },
    // 腿（每個部件 z 不同，避免共平面）
    { id: 'thighA', parent: 'pelvis', at: [-d.pelvisW * 0.27, -0.1], rect: [-d.legW / 2, -d.thigh - 0.05, d.legW, d.thigh + 0.12], z: 2, color: c.bottom, shape: 'capsule' },
    { id: 'shinA', parent: 'thighA', at: [0, -d.thigh], rect: [-d.legW * 0.42, -d.shin - 0.04, d.legW * 0.84, d.shin + 0.1], z: 1, color: c.bottom, shape: 'capsule' },
    { id: 'footA', parent: 'shinA', at: [0, -d.shin], rect: [-d.legW * 0.4, -d.foot * 0.9, d.foot * 2.3, d.foot * 1.1], z: 0, color: c.shoe, shape: 'foot' },
    { id: 'thighB', parent: 'pelvis', at: [d.pelvisW * 0.27, -0.1], rect: [-d.legW / 2, -d.thigh - 0.05, d.legW, d.thigh + 0.12], z: 5, color: c.bottom, shape: 'capsule' },
    { id: 'shinB', parent: 'thighB', at: [0, -d.thigh], rect: [-d.legW * 0.42, -d.shin - 0.04, d.legW * 0.84, d.shin + 0.1], z: 4, color: c.bottom, shape: 'capsule' },
    { id: 'footB', parent: 'shinB', at: [0, -d.shin], rect: [-d.legW * 0.4, -d.foot * 0.9, d.foot * 2.3, d.foot * 1.1], z: 3, color: c.shoe, shape: 'foot' },
  ];
  return {
    id,
    parts,
    anchors: {
      // 手腕背側、手肘外側、膝蓋正面（不扣其他地方）
      wrist: { part: 'foreArmA', local: [-d.armW * 0.32, -d.foreArm * 0.88] },
      elbow: { part: 'upperArmA', local: [-d.armW * 0.42, -d.upperArm * 0.95] },
      knee: { part: 'thighA', local: [d.legW * 0.42, -d.thigh * 0.97] },
    },
    limbs: {
      armA: { upper: 'upperArmA', lower: 'foreArmA', end: 'handA', bend: 1 },
      armB: { upper: 'upperArmB', lower: 'foreArmB', end: 'handB', bend: -1 },
      legA: { upper: 'thighA', lower: 'shinA', end: 'footA', bend: 1 },
      legB: { upper: 'thighB', lower: 'shinB', end: 'footB', bend: 1 },
    },
  };
}

/** 阿樂叔叔（紙燈籠師傅）佔位：成人約 6 頭身，工作圍裙 */
export const RIG_ALE: RigSpec = human('ale', {
  torsoW: 0.74, torsoH: 1.16, headW: 0.54, headH: 0.64,
  upperArm: 0.66, foreArm: 0.62, hand: 0.24, armW: 0.21,
  thigh: 0.82, shin: 0.76, foot: 0.15, legW: 0.26, pelvisW: 0.62,
}, { skin: '#e6b98f', hair: '#3b2c24', top: '#c48a4c', sleeve: '#b67c41', forearm: '#e0b089', bottom: '#4d5b6f', shoe: '#3a2e28' });

/** 小晴佔位：兒童約 4.3 頭身、短髮 */
export const RIG_XIAOQING: RigSpec = human('xiaoqing', {
  torsoW: 0.5, torsoH: 0.62, headW: 0.46, headH: 0.5,
  upperArm: 0.36, foreArm: 0.34, hand: 0.15, armW: 0.15,
  thigh: 0.42, shin: 0.4, foot: 0.1, legW: 0.17, pelvisW: 0.42,
}, { skin: '#efc9a2', hair: '#2b2220', top: '#4f8bd0', sleeve: '#4a82c4', forearm: '#efc9a2', bottom: '#38455a', shoe: '#c9573c' });
