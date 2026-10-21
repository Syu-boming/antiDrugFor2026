// a2_window：第二幕 a2_c013「說出實情」——燈籠店外的傍晚，窗內是阿樂叔叔與葉護理師，孩子在店門口等（a2 代理）。
// 底景：assets/final/sets/a2_window/layout.json（天空、後排騎樓、店內暖牆、工作台、圓凳、店面〔窗挖空〕、窗玻璃）。
// 程式部分（update 是 cue 秒數的純函式，重播、跳轉都同一格）：
//   1. FX11 天色：cue 開始 7 秒內天空由午後暖色慢慢轉成淡紫（單向漸變，不閃爍）。
//   2. FX10 剪影回憶小窗（畫面右上，不蓋到窗內的阿樂叔叔與說話者的臉、不進字幕區）：
//      a2_c013_01 開始後小窗立起 → 一隻手（剪影）捧著同樣的盒子從左邊伸進來 → a2_c013_02 時阿樂叔叔的手（剪影）從右下慢慢伸過去，
//      在碰到之前（「伸手接過的那一刻」）小窗就收起（0.35 秒）。不出現打開或使用。
//   3. 筆記本特寫：x=30 的獨立小台；cue 用 camera.cut 切到 a2_win_note 時，0.4 秒後鉛筆在第一個問號旁邊畫出第二個問號（1.4 秒）。
import {
  CanvasTexture, Group, LinearFilter, Mesh, MeshBasicMaterial, MeshStandardMaterial, PlaneGeometry, type Material,
} from 'three';
import { finishTexture, makeCanvas } from '../stage/paper';
import { LAYER } from '../stage/layers';
import { buildImageSet, readLayout } from './imageSet';
import type { SetEntry } from './types';
import { clamp, ease, lerp } from '../util/math';

type V3 = [number, number, number];
/** 鉛筆跟著筆尖移動會讓那一區每秒明暗變化超過 3 次（光敏），所以不畫鉛筆，只畫鉛筆線 */
const SHOW_PENCIL = false;
const CAMERAS: Record<string, { pos: V3; target: V3; fov: number }> = {
  a2_win_wide: { pos: [-0.6, 2.05, 20], target: [-0.6, 1.9, 0], fov: 20 },
  a2_win_kids: { pos: [-0.45, 1.98, 13.0], target: [-0.45, 1.88, 0], fov: 20 },
  a2_win_note: { pos: [30, 1.5, 5.9], target: [30, 1.5, 0], fov: 20 },
};

type TL = { lines: { line: { id: string }; start: number; end: number }[]; anims: { name: string; start: number; params: Record<string, unknown> }[] };
const lineAt = (tl: TL, id: string): { start: number; end: number } | null => tl.lines.find((l) => l.line.id === id) ?? null;

/** 紙片立起（略過頭再回正）：u 0→1 */
function popUp(u: number): number {
  if (u <= 0) return 0;
  if (u >= 1) return 1;
  return Math.min(1.04, ease('out', u) * 1.04) - Math.max(0, (u - 0.75) / 0.25) * 0.04;
}

/** 問號路徑（同 build_a2_art.py 的 qmark_path） */
function qmarkPath(cx: number, cy: number, k: number): [number, number][] {
  const pts: [number, number][] = [];
  for (let i = 0; i <= 40; i++) {
    const a = Math.PI * 1.05 - (i / 40) * Math.PI * 1.45;
    pts.push([cx + Math.cos(a) * 95 * k, cy - 120 * k - Math.sin(a) * 95 * k]);
  }
  const last = pts[pts.length - 1];
  pts.push([last[0] - 10 * k, last[1] + 40 * k], [cx, cy + 40 * k], [cx, cy + 70 * k]);
  return pts;
}

export const A2_WINDOW: SetEntry = {
  title: '燈籠店外的傍晚（第二幕）',
  cameras: CAMERAS,
  build(ctx) {
    const layout = readLayout(ctx, 'a2_window');
    if (!layout) throw new Error('缺 sets/a2_window/layout');
    const base = buildImageSet(ctx, layout);
    base.cameras = { ...CAMERAS, ...(base.cameras ?? {}) };
    const report = base.report ?? [];
    const mats = (base.materials ?? []) as MeshStandardMaterial[];
    const wallMat = mats[0];
    const wallColor0 = wallMat?.color.clone();
    // 店內（窗裡）是暖黃燈光：不套傍晚的紫色分級，另給暖色自發光
    for (const id of ['interior', 'bench', 'stool']) {
      const m = (base.group.getObjectByName(`pop:${id}`)?.children[0] as Mesh | undefined)?.material as MeshStandardMaterial | undefined;
      if (!m) continue;
      m.color.set('#fff4e4');
      m.emissive.set(id === 'interior' ? '#ffe0a8' : '#f6d6a6');
      m.emissiveIntensity = id === 'interior' ? 0.62 : 0.4;
    }
    const wallEm0 = wallMat?.emissiveIntensity ?? 0.36;

    // ---- 剪影回憶小窗
    const frameImg = ctx.image('sets/a2_window/sil-frame');
    const boxImg = ctx.image('sets/a2_window/sil-hand-box');
    const handImg = ctx.image('sets/a2_window/sil-ale-hand');
    if (!frameImg || !boxImg || !handImg) report.push('景 a2_window：缺剪影小窗素材（sil-frame／sil-hand-box／sil-ale-hand）');
    const IW = 1000, IH = 720;
    const [ic, ig] = makeCanvas(IW, IH);
    const itex = finishTexture(new CanvasTexture(ic));
    itex.minFilter = LinearFilter;
    itex.generateMipmaps = false;
    const insetMat = new MeshBasicMaterial({ map: itex, transparent: true, depthWrite: false, toneMapped: false });
    const insetW = 2.6, insetH = insetW * IH / IW;
    const insetGeo = new PlaneGeometry(insetW, insetH);
    insetGeo.translate(0, insetH / 2, 0);
    const inset = new Mesh(insetGeo, insetMat);
    inset.renderOrder = LAYER.fore.order + 60;
    const insetHinge = new Group();
    insetHinge.name = 'a2:silInset';
    insetHinge.position.set(3.15, 2.55, 2.3);
    insetHinge.add(inset);
    base.group.add(insetHinge);
    let insetKey = '';
    const drawInset = (boxX: number, hand: number): void => {
      const key = `${boxX.toFixed(1)}|${hand.toFixed(3)}`;
      if (key === insetKey) return;
      insetKey = key;
      ig.clearRect(0, 0, IW, IH);
      if (frameImg) ig.drawImage(frameImg, 0, 0, IW, IH);
      ig.save();
      ig.beginPath();
      ig.rect(40, 40, IW - 80, IH - 80);
      ig.clip();
      if (boxImg) {
        const bw = 560, bh = bw * boxImg.naturalHeight / boxImg.naturalWidth;
        ig.drawImage(boxImg, boxX, 262, bw, bh);
      }
      if (handImg && hand > 0) {
        const hw = 300, hh = hw * handImg.naturalHeight / handImg.naturalWidth;
        const x = lerp(760, 548, hand), y = lerp(IH + 10, 318, hand);
        ig.drawImage(handImg, x, y, hw, hh);
      }
      ig.restore();
      itex.needsUpdate = true;
    };

    // ---- 筆記本特寫（x=30 的獨立小台）
    const noteImg = ctx.image('sets/a2_window/notebook');
    if (!noteImg) report.push('景 a2_window：缺筆記本素材 notebook');
    const NW = 1500, NH = 960;
    const [nc, ng] = makeCanvas(NW, NH);
    const ntex = finishTexture(new CanvasTexture(nc));
    ntex.minFilter = LinearFilter;
    ntex.generateMipmaps = false;
    const noteMat = new MeshBasicMaterial({ map: ntex, transparent: true, toneMapped: false });
    const noteW = 3.1, noteH = noteW * NH / NW;
    const note = new Mesh(new PlaneGeometry(noteW, noteH), noteMat);
    note.position.set(30, 1.5, 0);
    note.renderOrder = LAYER.mid.order + 50;
    base.group.add(note);
    // 筆記本底下一張暖色桌面（特寫的背景）
    const deskMat = new MeshStandardMaterial({ color: '#c79a6a', roughness: 0.95 });
    const desk = new Mesh(new PlaneGeometry(6, 4), deskMat);
    desk.position.set(30, 1.5, -0.05);
    desk.renderOrder = LAYER.mid.order + 49;
    base.group.add(desk);
    const extraMats: Material[] = [insetMat, noteMat, deskMat];
    const Q2 = qmarkPath(NW * 0.84, NH * 0.46, 0.92);
    const segLen: number[] = [];
    let total = 0;
    for (let i = 1; i < Q2.length; i++) { const d = Math.hypot(Q2[i][0] - Q2[i - 1][0], Q2[i][1] - Q2[i - 1][1]); segLen.push(d); total += d; }
    let noteKey = '';
    const drawNote = (u: number, pencil: number): void => {
      const key = `${u.toFixed(3)}|${pencil.toFixed(2)}`;
      if (key === noteKey) return;
      noteKey = key;
      ng.clearRect(0, 0, NW, NH);
      if (noteImg) ng.drawImage(noteImg, 0, 0, NW, NH);
      const col = '#5c5660';
      ng.strokeStyle = col;
      ng.lineWidth = 12;
      ng.lineCap = 'round';
      ng.lineJoin = 'round';
      let tip: [number, number] = Q2[0];
      if (u > 0) {
        const L = Math.min(1, u / 0.9) * total;
        ng.beginPath();
        ng.moveTo(Q2[0][0], Q2[0][1]);
        let acc = 0;
        for (let i = 1; i < Q2.length; i++) {
          const d = segLen[i - 1];
          if (acc + d >= L) { const k = (L - acc) / d; tip = [lerp(Q2[i - 1][0], Q2[i][0], k), lerp(Q2[i - 1][1], Q2[i][1], k)]; ng.lineTo(tip[0], tip[1]); break; }
          ng.lineTo(Q2[i][0], Q2[i][1]);
          acc += d;
          tip = Q2[i];
        }
        ng.stroke();
      }
      const dotC: [number, number] = [NW * 0.84, NH * 0.46 + 133 * 0.92];
      if (u >= 0.97) { ng.fillStyle = col; ng.beginPath(); ng.arc(dotC[0], dotC[1], 12, 0, Math.PI * 2); ng.fill(); tip = dotC; }
      if (SHOW_PENCIL && pencil > 0.01) {
        // 鉛筆（往右上斜；畫完往右上抬走）
        const lift = 1 - pencil;
        const px = tip[0] + lift * 220, py = tip[1] - lift * 160;
        ng.save();
        ng.translate(px, py);
        ng.rotate(-0.95);
        ng.fillStyle = '#4e463f'; ng.beginPath(); ng.moveTo(0, 0); ng.lineTo(14, -9); ng.lineTo(14, 9); ng.closePath(); ng.fill();
        ng.fillStyle = '#efd9b4'; ng.beginPath(); ng.moveTo(12, -10); ng.lineTo(46, -24); ng.lineTo(46, 24); ng.lineTo(12, 10); ng.closePath(); ng.fill();
        ng.fillStyle = '#e8b64a'; ng.fillRect(46, -24, 300, 48);
        ng.fillStyle = 'rgba(120,80,20,0.25)'; ng.fillRect(46, 8, 300, 6);
        ng.fillStyle = '#c98b6a'; ng.fillRect(346, -24, 40, 48);
        ng.strokeStyle = '#4e3e33'; ng.lineWidth = 3; ng.strokeRect(46, -24, 340, 48);
        ng.restore();
      }
      ntex.needsUpdate = true;
    };
    drawInset(-600, 0);
    drawNote(0, 0);

    base.materials = [...(base.materials ?? []), ...extraMats];
    const baseUpdate = base.update;
    base.update = (o) => {
      baseUpdate?.(o);
      const tl = o.tl as unknown as TL;
      const t = o.t;
      // 1. 天色：7 秒內由暖轉淡紫
      if (wallMat && wallColor0) {
        const s = ease('sine', clamp(t / 7));
        wallMat.color.copy(wallColor0).multiplyScalar(lerp(1.12, 0.92, s));
        wallMat.emissiveIntensity = lerp(wallEm0 * 1.35, wallEm0 * 0.85, s);
      }
      // 2. 剪影小窗
      const l1 = lineAt(tl, 'a2_c013_01'), l2 = lineAt(tl, 'a2_c013_02');
      if (l1 && l2) {
        const open0 = l1.start + 0.15, close0 = l2.end - 0.35;
        const up = t < close0 ? popUp((t - open0) / 0.6) : 1 - ease('inOut', clamp((t - close0) / 0.35));
        insetHinge.visible = up > 0.02;
        insetHinge.rotation.x = -(1 - Math.min(1, up)) * Math.PI / 2 + Math.max(0, up - 1) * 0.5;
        if (insetHinge.visible) {
          const slide = ease('inOut', clamp((t - (l1.start + 0.7)) / 2.6));
          const hand = ease('inOut', clamp((t - (l2.start + 0.5)) / Math.max(0.5, (close0 - 0.15) - (l2.start + 0.5))));
          drawInset(lerp(-600, 40, slide), hand);
        }
      } else insetHinge.visible = false;
      // 3. 筆記本：切到 a2_win_note 之後 0.4 秒開始畫
      const cut = tl.anims.find((a) => (a.name === 'camera.cut' || a.name === 'camera.move') && a.params.to === 'a2_win_note');
      if (cut) {
        const s0 = cut.start + 0.4;
        const u = clamp((t - s0) / 1.4);
        const pencil = t < s0 ? 0 : t < s0 + 1.45 ? 1 : 1 - clamp((t - s0 - 1.45) / 0.5);
        drawNote(u, Math.max(0, Math.min(1, t < s0 ? clamp((t - cut.start) / 0.4) : pencil)));
      }
    };
    base.report = report;
    return base;
  },
};
