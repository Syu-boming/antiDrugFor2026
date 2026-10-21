// a5_gate：第五幕「找得到的幫手」的校門口（a5_c001–a5_c007）。G5 第五幕代理。
// 底景＝第四幕的 gate 建構器（app/src/sets/gate.ts：layout.json 底景＋第四幕的程式道具；gate.ts 一字不改，
// 第四幕的 setTrack 動作照樣能用）；本檔再加第五幕需要程式的東西：
//   - 街角小店（畫面左、近側人行道的轉角）：陳伯伯帶低年級小朋友轉過去就被擋住、看不見
//   - 轉角的低年級小朋友（遠景小尺寸、中性、沒有五官細節；只會揮手、往左走）
//   - 轉角後只露出的導護旗一角（a5_c005 環顧鏡頭）
//   - 陳伯伯手上的導護旗（換姿勢時跟著換手）
//   - 救護車（自訂「手捧愛心」圖示、沒有紅十字、沒有真實單位配色；頂燈恆亮不閃）、擔架
//   - 畫面右上方的紙剪電話圖示（跟著鏡頭；執勤人員說話時聲波弧線慢慢起伏，每秒 < 1 次）
//   - 阿樂叔叔叫不醒時一直閉著眼睛（引擎的臉部換片只有眨眼；本景把他困惑頭的眼睛換片固定在 closed，
//     不改引擎，只動畫面上已有的換片網格的 visible；離開這個景或 sleep 關掉時還原）
//
// cue 的 setTrack（格式同 gate.ts：時間參照同 animation.start；數值軌從 0 開始依序套用）：
//   { "do": "student", "to": 1 }                                      轉角小朋友出現（0 不顯示）
//   { "do": "studentWave", "start": …, "duration": … }                揮手（以肩為支點慢慢擺，每秒 1 下）
//   { "do": "studentGo", "dx": -2.4, "start": …, "duration": … }      往左走（走進街角後面）
//   { "do": "flagPeek", "to": 1, "start": …, "duration": 0.8 }        轉角後露出導護旗一角（慢慢出現；旗面輕微擺動、不轉過來）
//   { "do": "chenFlag", "to": 1, "at": [x, y], "dir": 1, "start": … } 陳伯伯手上的導護旗：at＝立牌身體座標（世界單位）的握點，
//                                                                      dir＝旗面朝向（1 畫面右、−1 畫面左）；換姿勢時排一筆新的 at
//   { "do": "ambulance", "from": -11, "start": …, "duration": 6 }     救護車從畫面左外開進來、減速停在長椅前（輪子轉）
//   { "do": "gurney", "x0": -6.4, "x1": -3.6, "start": …, "duration": … , "to": 1 }   擔架（to 0 不顯示）
//   { "do": "phone", "to": 1, "start": …, "duration": 0.6 }           電話圖示出現／收起（透明度漸變）
//   { "do": "phoneTalk", "start": "<台詞>.start", "until": "<台詞>.end" }   聲波弧線起伏的時段（執勤人員說話；until 也可改寫 duration）
//   { "do": "sleep", "to": 1, "start": …, "duration": 0.7 }         阿樂叔叔閉著眼睛（0.25–0.75 半閉、> 0.75 閉眼；0 秒＝一開始就閉著）
// 所有量都是時間的純函式（同一秒同一格）。
import { Color, Mesh, MeshBasicMaterial, MeshStandardMaterial, Object3D, Vector3, type Material } from 'three';
import { buildGate, GATE } from './gate';
import { imagePlane, refTime, trackOf, trackValue } from './a4_roadmap';
import { clamp, ease } from '../util/math';
import type { CameraPreset } from '../stage/layers';
import type { BuiltSet, SetContext, SetEntry } from './types';

/** 街角小店：x 中心、z（在陳伯伯走的路線 z 0.62 前面，他往左走就被擋住；右緣 x −5.1，放在台口摺幕內側，全景也看得到轉角） */
const CORNER = { x: -6.4, z: 1.0, w: 2.6 };
/** 轉角小朋友的站位 */
const STUDENT = { x: -4.55, z: 0.85, w: 0.95 };
/** 救護車停的位置（車廂後段擋住長椅上的阿樂叔叔） */
const AMB = { x: -2.3, z: 0.95, w: 7.0 };
/** 救護車圖是依 5.6 寬畫的（review/G5/a5/art_meta.json）；放大到 AMB.w 時輪子、頂燈一起放大（車廂頂約 3.0，擋住長椅上的阿樂叔叔，頭也不會從車頂露出來） */
const AK = AMB.w / 5.6;

export const A5_GATE_CAMERAS: Record<string, CameraPreset> = {
  /** 校門內越肩：前景右邊是兩個孩子（背影側），中景長椅、小貨車 */
  a5_ots: { pos: [6.4, 1.8, 14.2], target: [-0.9, 1.5, 0], fov: 25 },
  /** 遠景轉角：長椅＋陳伯伯＋街角小店與轉角的小朋友（台口內） */
  a5_corner: { pos: [0.0, 2.0, 19.5], target: [-2.3, 1.75, 0], fov: 20 },
  /** 長椅中景（陳伯伯對阿樂叔叔說話、朝辦公室大聲交代；畫面右邊留給辦公室方向） */
  a5_bench_chen: { pos: [-1.3, 1.6, 14.6], target: [-1.3, 1.42, 0], fov: 20 },
  /** 長椅中景（阿樂叔叔，不特寫臉） */
  a5_bench: { pos: [-2.55, 1.45, 13.0], target: [-2.55, 1.3, 0], fov: 20 },
  /** 孩子在前景（右）、長椅在後（左）：門內外分界、前後景深 */
  a5_deep: { pos: [3.1, 1.6, 12.8], target: [0.3, 1.42, 0], fov: 26 },
  /** 兩個孩子＋折折（折折把問題交給觀眾；停格） */
  a5_kids_z: { pos: [3.55, 1.25, 12.6], target: [3.55, 1.1, 1.9], fov: 20 },
  /** 環顧（小宇的視線，往左平移、不轉向：側看會看到景的邊緣）：起點＝空空的接送區 */
  a5_pov_a: { pos: [0.1, 1.7, 10.5], target: [0.1, 1.55, 0], fov: 22 },
  /** 環顧第三格：轉角後只露出導護旗一角 */
  /** 環顧第二格：長椅上的阿樂叔叔 */
  a5_pov_m: { pos: [-2.4, 1.7, 10.5], target: [-2.4, 1.55, 0], fov: 22 },
  a5_pov_b: { pos: [-3.9, 1.7, 10.5], target: [-3.9, 1.55, 0], fov: 22 },
  /** 雙人（門內） */
  a5_kids: { pos: [3.95, 1.35, 11.6], target: [3.95, 1.2, 1.9], fov: 20 },
  /** 小宇中景（舉手錶） */
  a5_xy: { pos: [4.25, 1.3, 9.6], target: [4.15, 1.2, 1.75], fov: 20 },
  /** 小宇近景（打電話；右上方留給電話圖示） */
  a5_xy_close: { pos: [4.05, 1.55, 8.0], target: [3.85, 1.48, 1.75], fov: 20 },
  /** 小宇在前景、長椅在後：他說的「門口的椅子」 */
  a5_xy_deep: { pos: [7.2, 1.75, 11.5], target: [0.6, 1.4, 0], fov: 26 },
  /** 從街上看小宇在門裡（門柱、接送線在畫面裡） */
  a5_xy_inside: { pos: [2.6, 1.5, 12.0], target: [2.6, 1.32, 0.8], fov: 20 },
  /** 全景（門內外分界清楚：長椅、校門、孩子） */
  a5_wide: { pos: [0.6, 1.95, 21.5], target: [0.6, 1.75, 0], fov: 20 },
  /** 救護車遠景（不特寫擔架上的臉；門內的林老師與孩子也在畫面裡＝門內外分界） */
  a5_amb: { pos: [0.0, 1.95, 21.5], target: [0.0, 1.75, 0], fov: 20 },
  /** 林老師（蹲著）與孩子中景 */
  a5_lin_kids: { pos: [3.7, 1.45, 12.6], target: [3.7, 1.3, 1.4], fov: 20 },
  /** 林老師站起來稱讚孩子（站姿的頭也在畫面裡） */
  a5_lin_kids2: { pos: [3.4, 1.9, 15.0], target: [3.6, 1.75, 1.2], fov: 20 },
};

const tmpV = new Vector3();
const tmpF = new Vector3();
const tmpR = new Vector3();
const tmpU = new Vector3();

function sceneRoot(o: Object3D): Object3D {
  let s = o;
  while (s.parent) s = s.parent;
  return s;
}

export function buildA5Gate(ctx: SetContext): BuiltSet {
  const base = buildGate(ctx);
  const group = base.group;
  const mats: Material[] = [...(base.materials ?? [])];
  const report = [...(base.report ?? [])];
  const tint = new Color('#fff6e6');
  const img = (n: string): HTMLImageElement | undefined => {
    const im = ctx.image(n);
    if (!im) report.push(`景 a5_gate：缺圖 ${n}`);
    return im;
  };
  const prop = (n: string, w: number, order: number, shadow = true): Mesh | null => {
    const m = imagePlane(img(n), w);
    if (!m) return null;
    ((m.material as MeshStandardMaterial).color).copy(tint);
    mats.push(m.material as Material);
    m.castShadow = shadow;
    m.renderOrder = order;
    group.add(m);
    return m;
  };

  // ---- 街角小店（一直站著；轉角柱在右緣）
  const corner = prop('sets/a5_gate/a5-corner', CORNER.w, 260);
  if (corner) corner.position.set(CORNER.x, -0.02, CORNER.z);

  // ---- 轉角的低年級小朋友（身體＋揮手的手臂；手臂樞紐在肩）
  const student = prop('sets/a5_gate/a5-student', STUDENT.w, 255);
  const arm = prop('sets/a5_gate/a5-student-arm', 0.3, 256, false);
  if (student) { student.position.set(STUDENT.x, 0, STUDENT.z); student.visible = false; }
  if (arm && student) {
    arm.geometry.translate(0, -0.06, 0);                 // 肩膀在手臂圖的下緣稍上
    group.remove(arm);
    student.add(arm);
    arm.position.set(0.21, 1.3, 0.01);
    arm.renderOrder = 256;
  }

  // ---- 轉角後露出的導護旗一角
  const peek = prop('sets/gate/set-gate_a4-flag', 0.78, 250, false);
  if (peek) {
    peek.geometry.translate(0.78 * 0.5 - 0.78 * 0.14, -0.42, 0);
    // 握點在街角右緣後面一點（z 0.3，被街角小店擋住），旗面往右只露出一角（a5_pov_b 鏡位下約露出旗面的 0.4）
    peek.position.set(-5.6, 1.22, 0.3);
    peek.visible = false;
  }
  const peekMat = peek ? (peek.material as MeshStandardMaterial) : null;
  if (peekMat) { peekMat.transparent = true; peekMat.depthWrite = false; peekMat.alphaTest = 0.02; }

  // ---- 陳伯伯手上的導護旗（握點在原點）
  const flag = prop('sets/gate/set-gate_a4-flag', 0.78, 394, true);
  if (flag) { flag.geometry.translate(0.78 * 0.5 - 0.78 * 0.14, -0.42, 0); flag.visible = false; }

  // ---- 救護車：車身＋兩個輪子（借小貨車的輪子圖）＋頂燈（恆亮；MeshBasic 不受舞台燈影響，亮度固定）
  const amb = prop('sets/a5_gate/a5-ambulance', AMB.w, 262);
  const ambWheels: Mesh[] = [];
  const wheelR = 0.42 * AK;
  let ambLight: Mesh | null = null;
  if (amb) {
    amb.visible = false;
    for (const [cx, cy] of [[-1.8 * AK, 0.4467 * AK], [1.75 * AK, 0.4467 * AK]] as [number, number][]) {
      const w = imagePlane(img('props/prop-truck-wheel'), wheelR * 2);
      if (!w) continue;
      ((w.material as MeshStandardMaterial).color).copy(tint);
      mats.push(w.material as Material);
      w.geometry.translate(0, -wheelR, 0);
      w.position.set(cx, cy, 0.02);
      w.renderOrder = 263;
      amb.add(w);
      ambWheels.push(w);
    }
    const li = img('sets/a5_gate/a5-ambulance-light');
    const l = imagePlane(li, 1.1 * AK, { basic: true, color: '#fff3dc' });
    if (l) {
      l.position.set(1.45 * AK, 2.04 * AK, -0.01);
      l.renderOrder = 261;
      amb.add(l);
      ambLight = l;
    }
  }
  void ambLight;

  // ---- 擔架
  const gurney = prop('sets/a5_gate/a5-gurney', 2.2, 258);
  if (gurney) { gurney.position.set(-6.4, 0, 0.5); gurney.visible = false; }

  // ---- 電話圖示（跟著鏡頭的紙牌；不寫深度、永遠在角色前面；字幕是 HTML，不受影響）
  const phoneParts: { m: Mesh; mat: MeshBasicMaterial; k: number }[] = [];
  const phoneRoot = new Object3D();
  phoneRoot.visible = false;
  group.add(phoneRoot);
  {
    const mk = (id: string, w: number, x: number, y: number, k: number, flip = false): void => {
      const m = imagePlane(img(id), w, { basic: true, transparent: true });
      if (!m) return;
      const mat = m.material as MeshBasicMaterial;
      mat.depthTest = false;
      m.geometry.translate(0, -(m.userData.h as number) / 2, 0);
      m.position.set(x, y, 0);
      if (flip) m.scale.x = -1;
      m.renderOrder = 880 + phoneParts.length;
      phoneRoot.add(m);
      phoneParts.push({ m, mat, k });
    };
    // 單位＝畫面高度（下面依相機換算成世界尺寸）；聲波弧線在圖示左邊（朝小宇）
    mk('sets/a5_gate/a5-phone', 0.2, 0, 0, -1);
    // 三條弧線同一個圓心（弧線圖的畫布＝2R＋20 px，R＝34／60／86），圓心在圖示左緣外一點 → 同心的「（」往小宇那邊擴散
    const H3 = 0.22, CX = -0.115;
    mk('sets/a5_gate/a5-phone-arc1', H3 * 88 / 192, CX, 0, 0, true);
    mk('sets/a5_gate/a5-phone-arc2', H3 * 140 / 192, CX, 0, 1, true);
    mk('sets/a5_gate/a5-phone-arc3', H3, CX, 0, 2, true);
  }

  // ---- 阿樂叔叔閉眼：找困惑頭的眼睛換片網格（貼圖＝face/ale/chr-ale_eyes_*）
  const eyeImg = { closed: ctx.image('face/ale/chr-ale_eyes_closed'), half: ctx.image('face/ale/chr-ale_eyes_half'), open: ctx.image('face/ale/chr-ale_eyes_open') };
  let eyeMeshes: { closed: Mesh | null; all: Mesh[]; open: Mesh | null; half: Mesh | null } | null = null;
  let forced = false;
  const findEyes = (): typeof eyeMeshes => {
    if (eyeMeshes && eyeMeshes.closed?.parent) return eyeMeshes;
    const root = sceneRoot(group);
    const rig = root.getObjectByName('rig:ale');
    if (!rig || !eyeImg.closed) return null;
    let closed: Mesh | null = null;
    rig.traverse((o) => {
      const m = o as Mesh;
      if (!closed && m.isMesh && (m.material as MeshStandardMaterial).map?.image === eyeImg.closed) closed = m;
    });
    if (!closed) return null;
    const all = ((closed as Mesh).parent?.children ?? []).filter((c): c is Mesh => (c as Mesh).isMesh);
    const open = all.find((m) => (m.material as MeshStandardMaterial).map?.image === eyeImg.open) ?? null;
    const half = all.find((m) => (m.material as MeshStandardMaterial).map?.image === eyeImg.half) ?? null;
    eyeMeshes = { closed, all, open, half };
    return eyeMeshes;
  };
  const restoreEyes = (): void => {
    if (!forced) return;
    forced = false;
    const e = eyeMeshes;
    if (!e) return;
    for (const m of e.all) m.visible = m === e.open;
  };

  return {
    ...base, group, materials: mats, report,
    cameras: { ...(base.cameras ?? {}), ...A5_GATE_CAMERAS },
    update(o) {
      base.update?.(o);
      const { tl, t, camera } = o;
      const ev = trackOf(tl);
      const scene = sceneRoot(group);

      // 轉角小朋友：揮手、往左走（走進街角後面就被擋住）
      if (student) {
        student.visible = trackValue(tl, 'student', t, 0, 'linear') > 0.5;
        let dx = 0, walking = false, wave = 0;
        for (const e of ev) {
          if (e.do === 'studentGo' && t >= e.start) {
            const u = e.duration > 0 ? clamp((t - e.start) / e.duration) : 1;
            dx += Number(e.p.dx ?? -2.4) * ease('sine', u);   // 正弦：中段速度只有平均的 1.57 倍（光敏）
            if (u > 0 && u < 1) walking = true;
          }
          if (e.do === 'studentWave' && t >= e.start && t <= e.start + e.duration) {
            const u = (t - e.start) / Math.max(1e-6, e.duration);
            wave = Math.min(1, u * 6, (1 - u) * 6);
          }
        }
        student.position.set(STUDENT.x + dx, walking ? Math.abs(Math.sin(t * Math.PI * 1.5)) * 0.02 : 0, STUDENT.z);   // 走路起伏慢、小（光敏）
        if (arm) {
          // 手臂：揮手時舉起、以肩為支點左右擺（每秒 1 下）；不揮手時放下貼著身體
          const up = wave;
          arm.rotation.z = -(1 - up) * Math.PI * 0.93 + up * (-0.22 + 0.26 * Math.sin(t * Math.PI * 2));
        }
      }

      // 轉角後的導護旗一角
      if (peek && peekMat) {
        const v = trackValue(tl, 'flagPeek', t, 0);
        peek.visible = v > 0.002;
        peekMat.opacity = v;
        peek.rotation.z = 0.04 * Math.sin((t / 2.8) * Math.PI * 2);
      }

      // 陳伯伯手上的導護旗
      if (flag) {
        let on = 0, at: [number, number] = [0.587, 1.329], dir = 1;
        for (const e of ev) {
          if (e.do !== 'chenFlag' || t < e.start) continue;
          on = Number(e.p.to ?? 1);
          if (Array.isArray(e.p.at)) at = [Number(e.p.at[0]), Number(e.p.at[1])];
          dir = Number(e.p.dir ?? 1);
        }
        const chen = scene.getObjectByName('standee:chen');
        flag.visible = on > 0.5 && !!chen && chen.visible;
        if (flag.visible && chen) {
          const body = chen.children[0];
          body.updateWorldMatrix(true, false);
          tmpV.set(at[0], at[1], 0.06).applyMatrix4(body.matrixWorld);
          flag.position.copy(tmpV);
          const sx = Math.sign(body.matrixWorld.elements[0]) || 1;
          flag.scale.set(dir * sx, 1, 1);
          flag.rotation.z = 0.03 * Math.sin((t / 3.1) * Math.PI * 2);
        }
      }

      // 救護車：從畫面左外開進來，越近越慢，停在長椅前
      if (amb) {
        let vis = false, dx = 0;
        for (const e of ev) {
          if (e.do !== 'ambulance') continue;
          const from = Number(e.p.from ?? -11);
          if (t < e.start) { dx = from; vis = false; continue; }
          vis = true;
          const u = e.duration > 0 ? clamp((t - e.start) / e.duration) : 1;
          dx = from * Math.pow(1 - u, 2.2);
        }
        amb.visible = vis;
        amb.position.set(AMB.x + dx, -0.02, AMB.z);
        for (const w of ambWheels) w.rotation.z = dx / wheelR;
      }

      // 擔架
      if (gurney) {
        let vis = false, x = -6.4;
        for (const e of ev) {
          if (e.do !== 'gurney' || t < e.start) continue;
          vis = Number(e.p.to ?? 1) > 0.5;
          const u = e.duration > 0 ? clamp((t - e.start) / e.duration) : 1;
          x = Number(e.p.x0 ?? -6.4) + (Number(e.p.x1 ?? -6.4) - Number(e.p.x0 ?? -6.4)) * ease('inOut', u);
        }
        gurney.visible = vis;
        gurney.position.set(x, 0.0, 0.5);
      }

      // 電話圖示：放在相機前方、畫面右上（NDC 約 0.66, 0.6），大小以畫面高度計
      const pv = trackValue(tl, 'phone', t, 0);
      phoneRoot.visible = pv > 0.002;
      if (phoneRoot.visible) {
        const dist = 3.0;
        const halfH = dist * Math.tan((camera.fov * Math.PI) / 360);
        const halfW = halfH * camera.aspect;
        tmpF.set(0, 0, -1).applyQuaternion(camera.quaternion);
        tmpR.set(1, 0, 0).applyQuaternion(camera.quaternion);
        tmpU.set(0, 1, 0).applyQuaternion(camera.quaternion);
        phoneRoot.position.copy(camera.position).addScaledVector(tmpF, dist).addScaledVector(tmpR, 0.66 * halfW).addScaledVector(tmpU, 0.6 * halfH);
        phoneRoot.quaternion.copy(camera.quaternion);
        phoneRoot.scale.setScalar(2 * halfH);
        // 聲波：執勤人員說話時依序慢慢起伏（每條 0.8 Hz，不透明度只在 0.5–1 之間平滑變化）；沒說話時固定淡淡的
        let talk = 0;
        for (const e of ev) {
          if (e.do !== 'phoneTalk') continue;
          const end = e.p.until !== undefined ? refTime(tl, e.p.until) : e.start + e.duration;
          if (t < e.start - 0.4 || t > end + 0.4) continue;
          talk = Math.max(talk, Math.min(1, (t - e.start + 0.4) / 0.4, (end + 0.4 - t) / 0.4));
        }
        for (const p of phoneParts) {
          if (p.k < 0) { p.mat.opacity = pv; continue; }
          const wave = 0.5 + 0.5 * Math.sin((t * 0.8 - p.k * 0.22) * Math.PI * 2);
          p.mat.opacity = pv * (0.5 + talk * 0.5 * wave);
        }
      }

      // 阿樂叔叔閉眼（叫不醒）：sleep 0.25–0.75 半閉、> 0.75 閉眼（從睜眼慢慢閉上時經過半閉一格以上）
      const sv = trackValue(tl, 'sleep', t, 0, 'linear');
      if (sv > 0.25) {
        const e = findEyes();
        const show = e ? (sv > 0.75 ? e.closed : e.half ?? e.closed) : null;
        if (e && show) {
          for (const m of e.all) m.visible = m === show;
          forced = true;
        }
      } else restoreEyes();
    },
    dispose() {
      restoreEyes();
      base.dispose?.();
    },
  };
}

export const A5_GATE: SetEntry = {
  title: '校門口（第五幕：叫不醒、分頭求助、大人接手）',
  cameras: { ...(GATE.cameras ?? {}), ...A5_GATE_CAMERAS },
  build: (ctx) => buildA5Gate(ctx),
};
