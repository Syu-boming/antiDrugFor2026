// 一年後的燈籠店（a6_c009）＋複習與收束（a7）＋謝幕（a8_c001；a8_c002 閉幕也在這個景，畫面＝G4 燈籠店）。G5 第六幕代理。
// 沿用 G4 燈籠店景（buildWorkshopG4，不改它），再疊上：
//   - 工作台上的小折折燈：和折折同一個程式造型（Zhezhe 的 lantern 造型，小尺寸）。a6_c009 從方形燈籠紙一摺一摺摺成燈籠，
//     阿樂叔叔道謝之後柔和亮起（2 秒漸亮）；之後一直亮著（a7、a8）。
//   - 三張大紙卡（a7_c001）：用 a3_c002、a4_c012、a5_c006 的畫面重製的紙卡插畫（assets/final/sets/a6_shop/card-1..3），標題程式排版；
//     像立體書一樣從地上立起；念到哪一張，那一張的放大版就在畫面中央浮現（約 46% 畫面寬：1.1 秒淡入＋從 90% 放大到 100%）停住，
//     念完淡出、縮回（修正第 1 輪；不讓整張卡從原位飛到中央：大面積卡片內容掃過同一區會超過光敏門檻）。
//     第二張先上下顛倒，折折跳過去碰一下，卡片輕跳、顛倒的那一面淡出＝轉正。2 級短版（a7_c001_01 被略過）只立第三張（放中央）。
//     a7_c002 開頭三張卡還立著（和 a7_c001 結尾一樣），再 1.4 秒淡出（不倒下：大面積卡片掃過同一區會超過光敏門檻）。
//   - 口訣卡（a7_c002）：四個動作小圖（card-mnemonic，程式排版文字）；a7_c003 開頭還立著，再 1 秒淡出。
//   - 謝幕（a8_c001）：阿樂叔叔站起來、把小折折燈捧在胸前鞠躬，坐回去前放回桌上（時間跟著 cue 的 puppet.sit／puppet.chest）。
//   - a8_c002 閉幕：牆上吊燈籠的影子不投到背牆（灰色橢圓影子）。
//   - 謝幕的燈籠微光（a8_c001，FX12）：亮度固定的小光點像落葉一樣慢慢飄，進出畫面淡入淡出 1 秒，cue 最後 1.5 秒全部淡出。
// 全部是時間的純函式（只依 cue、cue 內秒數決定畫面）。
import {
  AdditiveBlending, CanvasTexture, DoubleSide, Group, Mesh, MeshStandardMaterial, PlaneGeometry, Sprite, SpriteMaterial, type Material,
} from 'three';
import { buildWorkshopG4 } from '../stage/workshop';
import { Zhezhe } from '../stage/zhezhe';
import { finishTexture, makeCanvas } from '../stage/paper';
import { LAYER, type CameraPreset } from '../stage/layers';
import { clamp, lerp, seeded } from '../util/math';
import { dropped, haloTexture, lineT, sine01 } from './a6_square_night';
import type { BuiltSet, SetContext, SetEntry } from './types';

const FONT = '"Microsoft JhengHei", "PingFang TC", "Noto Sans TC", "Heiti TC", sans-serif';
const TABLE_TOP = 1.4;
/** 小折折燈（工作台上、阿樂叔叔右手邊：a6_c009 他的手就在燈籠紙上摺） */
const SMALL = { x: -1.82, z: -0.42, h: 0.72 };
/** 三張大紙卡：寬、高（世界單位）、站位 */
const CARD = { w: 3.5, h: 2.7, z: 1.65, xs: [-4.3, 0.05, 4.4] };
const MNEMO = { w: 7.4, h: 3.28, x: 0.05, z: 1.5 };
/** 謝幕時阿樂叔叔站著、手放胸前時，小折折燈的位置（捧在胸前；世界座標，量自私人擷取） */
const HAND = { x: -2.25, y: 1.62, z: 0.35 };
const TITLES = ['拒絕與離開', '安全接送', '找大人求助'];
const MNEMO_LABELS = ['不碰', '不試', '先離開', '找大人'];

const C = (pos: [number, number, number], target: [number, number, number], fov = 20): CameraPreset => ({ pos, target, fov });
export const A6_SHOP_CAMERAS: Record<string, CameraPreset> = {
  /** 一年後的燈籠店中景：阿樂叔叔坐在工作台前，孩子在右邊、折折在桌上 */
  a6_shop_mid: C([-0.2, 1.95, 15.2], [-0.2, 1.75, -0.3]),
  /** 手與小折折燈近景（手腕上只剩一根很淡、很鬆的線） */
  a6_shop_hands: C([-1.7, 2.12, 7.8], [-1.75, 1.9, -0.35]),
  /** 群像（小折折燈亮起、孩子們笑） */
  a6_shop_group: C([-0.05, 1.85, 13.4], [-0.05, 1.66, -0.2]),
  /** 舞台全景（三張大紙卡、口訣卡） */
  a7_wide: C([0.05, 2.0, 22.5], [0.05, 1.78, 0]),
  /** 台前全景（品安往前半步） */
  a7_front: C([0.2, 1.75, 17.2], [0.2, 1.58, 0.6]),
  /** 回到舞台全景（修正第 1 輪）：台口、布幕與上方八盞燈都入鏡（主線 13.1：pos z ≥ 34） */
  a7_stage: C([0, 4.65, 35], [0, 4.45, 0]),
  /** 口訣卡：推近一級（口訣卡約半個畫面寬、兩個孩子站在卡片兩邊、約 1/3 畫面高） */
  a7_mid: C([0, 2.35, 23.5], [0, 2.05, 0]),
};
/** 念到的卡的放大版：底邊在台口前方 (0, y, z)、原尺寸 S 倍（a7_stage 鏡位下約 46% 畫面寬，上緣在八盞燈下方、下緣在字幕上方；不被台口上方的布幔擋住標題） */
const FOCUS = { x: 0.0, y: 1.8, z: 4.6, s: 2.5 };
/** 放大／縮回：放大 1.1 秒、縮回 1.0 秒（正弦緩入緩出） */
const zoomK = (t: number, a: number, b: number): number => sine01((t - a) / 1.1) * (1 - sine01((t - b) / 1.0));

/** 紙卡貼圖：卡片圖（含空白標題列）＋程式排版的標題 */
function cardTexture(img: HTMLImageElement | undefined, title: string, num: number): CanvasTexture {
  const W = 1050, H = 810;
  const [c, g] = makeCanvas(W, H);
  if (img) g.drawImage(img, 0, 0, W, H);
  else { g.fillStyle = '#f6eedc'; g.fillRect(0, 0, W, H); }
  // 標題列（卡片圖上緣的空白紙條，高約 15%）
  g.fillStyle = '#3c2e24';
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  g.font = `bold 84px ${FONT}`;
  g.fillText(title, W / 2 + 34, H * 0.098);
  // 序號圓章（圓心用標題字型量一次；修正第 1 輪：原本換成 58px 字型後再量，數字跑到圓外、疊在標題前面成了淡灰「2」）
  const cx = W / 2 - g.measureText(title).width / 2 - 34;
  g.beginPath(); g.arc(cx, H * 0.098, 40, 0, Math.PI * 2);
  g.fillStyle = '#c8763e'; g.fill();
  g.fillStyle = '#fffaf0'; g.font = `bold 58px ${FONT}`;
  g.fillText(String(num), cx, H * 0.098 + 2);
  return finishTexture(new CanvasTexture(c));
}

function mnemonicTexture(img: HTMLImageElement | undefined): CanvasTexture {
  const W = 1400, H = 620;
  const [c, g] = makeCanvas(W, H);
  if (img) g.drawImage(img, 0, 0, W, H);
  else { g.fillStyle = '#f6eedc'; g.fillRect(0, 0, W, H); }
  g.fillStyle = '#3c2e24';
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  // 「不碰、不試；先離開，找大人」：每格下面一個動作，標點緊跟在字後面
  const punct = ['、', '；', '，', '。'];
  MNEMO_LABELS.forEach((s, i) => {
    const cx = W * (0.125 + i * 0.25);
    g.font = `bold 92px ${FONT}`;
    const w = g.measureText(s).width;
    g.textAlign = 'center';
    g.fillText(s, cx, H * 0.83);
    g.font = `bold 76px ${FONT}`;
    g.textAlign = 'left';
    g.fillText(punct[i], cx + w / 2 - 4, H * 0.85);
  });
  return finishTexture(new CanvasTexture(c));
}

/** 立起程度 u（0 平躺～1 立好，略過頭再回正）→ 繞底邊的角度（平躺＝倒向觀眾） */
function popAngle(u: number): number {
  const k = u <= 0 ? 0 : u >= 1 ? 1 : Math.min(1.04, (1 - Math.pow(1 - u, 3)) * 1.04) - Math.max(0, (u - 0.75) / 0.25) * 0.04;
  return -(1 - k) * Math.PI / 2;
}

export const A6_SHOP: SetEntry = {
  title: '燈籠店（一年後、複習、謝幕：G4 燈籠店＋小折折燈、三張大紙卡、口訣卡、燈籠微光）',
  cameras: A6_SHOP_CAMERAS,
  build(ctx: SetContext): BuiltSet {
    const ws = buildWorkshopG4({ alphaToCoverage: ctx.alphaToCoverage, image: (id) => ctx.image(id) });
    const group = ws.group;
    group.name = 'set:a6_shop';
    const mats: Material[] = [...ws.materials];
    const report: string[] = [];
    const im = (n: string): HTMLImageElement | undefined => { const i = ctx.image(`sets/a6_shop/${n}`); if (!i) report.push(`景 a6_shop：缺圖 ${n}`); return i; };

    // 牆上吊燈籠的影子不投到背牆（a8_c002 收景拉回台口時是一排灰色橢圓；本景限定，G4 燈籠店不變）
    group.traverse((o) => { if (o.name === 'pop:lanterns') o.traverse((m) => { (m as Mesh).castShadow = false; }); });

    // ---- 小折折燈
    const small = new Zhezhe({ position: [SMALL.x, TABLE_TOP, SMALL.z], height: SMALL.h, seed: 31, renderOrder: LAYER.mid.order + 30, contactShadow: true });
    group.add(small.group);
    let smallKey = '';

    // ---- 三張大紙卡＋口訣卡（底邊鉸鏈）
    const mkCard = (tex: CanvasTexture, w: number, h: number, x: number, z: number, order: number): { hinge: Group; spin: Group; mesh: Mesh } => {
      const mat = new MeshStandardMaterial({ map: tex, side: DoubleSide, roughness: 0.92, metalness: 0, alphaTest: 0.5 });
      mat.emissiveMap = tex; mat.emissive.setRGB(1, 1, 1); mat.emissiveIntensity = 0.18;
      mats.push(mat);
      const mesh = new Mesh(new PlaneGeometry(w, h), mat);
      mesh.renderOrder = order;
      mesh.castShadow = true;
      const spin = new Group();          // 上下顛倒→轉正（繞卡片中心）
      spin.position.y = h / 2 + 0.06;
      spin.add(mesh);
      const hinge = new Group();
      hinge.position.set(x, 0.0, z);
      hinge.add(spin);
      hinge.visible = false;
      group.add(hinge);
      return { hinge, spin, mesh };
    };
    const cards = [0, 1, 2].map((i) => mkCard(cardTexture(im(`card-${i + 1}`), TITLES[i], i + 1), CARD.w, CARD.h, CARD.xs[i], CARD.z, LAYER.fore.order - 30 + i));
    const mnemo = mkCard(mnemonicTexture(im('card-mnemonic')), MNEMO.w, MNEMO.h, MNEMO.x, MNEMO.z, LAYER.fore.order - 20);
    // 第二張卡上下顛倒的那一面（疊在正面前面，轉正時淡出）
    const flipMat = (cards[1].mesh.material as MeshStandardMaterial).clone();   // 同樣受光（和正面同色）
    flipMat.transparent = true; flipMat.alphaTest = 0.02; flipMat.depthWrite = false;
    mats.push(flipMat);
    const flipMesh = new Mesh(new PlaneGeometry(CARD.w, CARD.h), flipMat);
    flipMesh.rotation.z = Math.PI;
    flipMesh.position.z = 0.004;
    flipMesh.renderOrder = LAYER.fore.order - 25;
    flipMesh.visible = false;
    cards[1].spin.add(flipMesh);
    // 三張卡的放大版（同一張貼圖；透明度＝放大程度）
    const bigs = cards.map((c, i) => {
      const m = (c.mesh.material as MeshStandardMaterial).clone();
      m.transparent = true; m.alphaTest = 0.01; m.depthWrite = false; m.opacity = 0;
      mats.push(m);
      const mesh = new Mesh(new PlaneGeometry(CARD.w, CARD.h), m);
      mesh.renderOrder = LAYER.fore.order + 30 + i;
      mesh.visible = false;
      group.add(mesh);
      return mesh;
    });

    // ---- 謝幕的燈籠微光
    const motes: { s: Sprite; x0: number; period: number; phase: number; sway: number; size: number }[] = [];
    const halo = haloTexture();
    const rnd = seeded(8801);
    for (let i = 0; i < 26; i++) {
      const s = new Sprite(new SpriteMaterial({ map: halo, color: rnd() < 0.5 ? '#ffd69a' : '#ffc27e', transparent: true, opacity: 0, depthWrite: false, blending: AdditiveBlending }));
      const size = 0.16 + 0.1 * rnd();
      s.scale.set(size, size, 1);
      s.renderOrder = LAYER.fore.order + 40;
      s.visible = false;
      group.add(s);
      motes.push({ s, x0: -6.2 + 12.8 * rnd(), period: 7 + 4 * rnd(), phase: rnd(), sway: 0.25 + 0.3 * rnd(), size });
    }

    // u ≥ 0：立起程度（略過頭再回正）；u < 0：收平中（−u＝收平進度，正弦緩動、不過頭，慢慢倒下）
    const pop = (c: { hinge: Group }, u: number): void => {
      if (u < 0) { c.hinge.visible = u > -0.999; c.hinge.rotation.x = -(Math.PI / 2) * -u; return; }
      c.hinge.visible = u > 0.001; c.hinge.rotation.x = popAngle(u);
    };
    return {
      group, pieces: ws.pieces, materials: mats, marks: ws.marks, tableEdge: ws.tableEdge,
      landmarks: { ...ws.landmarks, smallLantern: { x0: SMALL.x - 0.25, x1: SMALL.x + 0.25, y: TABLE_TOP, z: SMALL.z } },
      cameras: A6_SHOP_CAMERAS, report,
      update({ tl, t }) {
        const id = tl.cue.id;
        // ---- 小折折燈：a6_c009 從燈籠紙摺成燈籠、最後亮起；其他 cue 一直亮著
        if (smallKey !== id) {
          smallKey = id;
          if (id === 'a6_c009') {
            // 一摺、一摺：三個手部循環（a6.json 的 puppet.grab：手抬起 0.55 秒 → 0.7 秒時按下去）各摺一次：方紙 → 對摺 → 帽形 → 燈籠
            small.reset({ pos: [SMALL.x, TABLE_TOP, SMALL.z], form: 'sheet', rise: 1, glow: 0, emotion: 'neutral' });
            const s2 = lineT(tl, 'a6_c009_02', 'start', 4), s3 = lineT(tl, 'a6_c009_03', 'start', 12);
            small.fold('card', 0.9 as never, s2 + 0.9 + 0.75, { scale: 0.45 });   // dur 的型別在 zhezhe.ts 是字面值（同 zhezhe_program.ts）
            small.fold('hat', 0.9 as never, s2 + 3.5 + 0.75);
            small.fold('lantern', 1.1 as never, s3 + 0.9 + 0.75);
            small.glow(1, 2.0, lineT(tl, 'a6_c009_04', 'end', 20) + 0.35);
          } else small.reset({ pos: [SMALL.x, TABLE_TOP, SMALL.z], form: 'lantern', glow: 1, emotion: 'neutral' });
        }
        small.update(t);

        // ---- 紙卡（修正第 1 輪：cue 接縫前後狀態一致——a7_c002 開頭三張卡還立著、a7_c003 開頭口訣卡還立著，不先清空再加回）
        let u = [0, 0, 0], flip = 0, um = 0, fade = 1, mfade = 1;
        const focus = [0, 0, 0];
        if (id === 'a7_c001') {
          if (dropped(tl, 'a7_c001_01')) {
            const s3 = lineT(tl, 'a7_c001_03', 'start', 2), e3 = lineT(tl, 'a7_c001_03', 'end', 8);
            u = [0, 0, clamp((t - 0.35) / 1.2)];
            focus[2] = zoomK(t, s3 + 0.4, e3 + 0.2);
            flip = 1;
          } else {
            const s1 = lineT(tl, 'a7_c001_01', 'start', 2), e1 = lineT(tl, 'a7_c001_01', 'end', 7);
            const s2 = lineT(tl, 'a7_c001_02', 'start', 11), e2 = lineT(tl, 'a7_c001_02', 'end', 16);
            const s3 = lineT(tl, 'a7_c001_03', 'start', 17), e3 = lineT(tl, 'a7_c001_03', 'end', 24);
            // 一次只動一張：第一張立起 → 念時放大 → 縮回 → 第二張（顛倒）立起 → 折折碰一下、轉正 → 放大 → 縮回 → 第三張立起 → 放大 → 縮回
            u = [clamp((t - 0.5) / 1.2), clamp((t - e1 - 1.3) / 1.2), clamp((t - e2 - 0.6) / 1.0)];
            flip = sine01((t - (e1 + 2.65)) / 1.2);
            focus[0] = zoomK(t, s1 - 0.2, e1 + 0.1);
            focus[1] = zoomK(t, s2 - 0.2, e2);
            focus[2] = zoomK(t, Math.max(s3 + 1.2, e2 + 1.7), e3 + 0.2);
          }
        } else if (id === 'a7_c002') {
          // 開頭和 a7_c001 結尾一樣（三張卡立著）→ 1.4 秒淡出 → 鏡頭推近後口訣卡立起（一次只動一件事：光敏）
          u = [1, 1, 1];
          flip = 1;
          fade = 1 - sine01((t - 0.1) / 1.4);
          um = clamp((t - 4.3) / 1.3);
        } else if (id === 'a7_c003') { um = 1; mfade = 1 - sine01((t - 0.4) / 1.0); }
        const setFade = (m: MeshStandardMaterial, a: number): void => {
          const f = a < 0.999;
          m.transparent = f; m.opacity = f ? a : 1; m.alphaTest = f ? 0.01 : 0.5; m.depthWrite = !f;
        };
        cards.forEach((c, i) => {
          pop(c, u[i]);
          if (fade <= 0.002) c.hinge.visible = false;
          setFade(c.mesh.material as MeshStandardMaterial, fade);
          c.hinge.position.x = i === 2 && id === 'a7_c001' && dropped(tl, 'a7_c001_01') ? 0.05 : CARD.xs[i];
          // 念到的卡：放大版在中央淡入（90% → 100%），念完淡出
          const k = focus[i], b = bigs[i];
          b.visible = k > 0.002;
          if (b.visible) {
            const sc = FOCUS.s * (0.9 + 0.1 * k);
            b.scale.set(sc, sc, 1);
            b.position.set(FOCUS.x, FOCUS.y + (CARD.h / 2 + 0.06) * FOCUS.s, FOCUS.z);
            (b.material as MeshStandardMaterial).opacity = k;
          }
        });
        // 第二張：一開始上下顛倒；折折跳過去碰一下，卡片輕輕跳起、顛倒的那一面淡出（1.2 秒）＝轉正
        //（不整張旋轉或收平：大面積卡片內容掃過同一區域會超過光敏門檻）
        const upside = id === 'a7_c001' ? 1 - flip : 0;
        flipMesh.visible = upside > 0.002 && cards[1].hinge.visible;
        flipMat.opacity = upside;
        cards[1].spin.position.y = CARD.h / 2 + 0.06 + (id === 'a7_c001' ? 0.16 * Math.sin(Math.PI * clamp(flip)) : 0);
        pop(mnemo, um);
        if (mfade <= 0.002) mnemo.hinge.visible = false;
        setFade(mnemo.mesh.material as MeshStandardMaterial, mfade);

        // ---- 謝幕：阿樂叔叔捧著小折折燈（a8_c001 的 puppet.chest：手放到胸前＝拿起，放下＝放回桌上）
        if (id === 'a8_c001') {
          const ch = tl.anims.filter((a) => a.target === 'ale' && a.name === 'puppet.chest');
          const up = ch.find((a) => Number(a.params.to ?? 1) > 0.5), down = ch.find((a) => Number(a.params.to ?? 1) < 0.5);
          if (up && down) {
            const k = sine01((t - up.start) / Math.max(0.3, up.duration)) * (1 - sine01((t - down.start) / Math.max(0.3, down.duration)));
            const nod = tl.anims.filter((a) => a.target === 'ale' && a.name === 'puppet.nod').reduce((m, a) => {
              const u2 = (t - a.start) / a.duration; return u2 > 0 && u2 < 1 ? Math.max(m, Math.sin(Math.PI * u2) ** 2) : m;
            }, 0);
            const hx = HAND.x, hy = HAND.y - 0.06 * nod, hz = HAND.z;
            small.group.position.set(lerp(SMALL.x, hx, k), lerp(TABLE_TOP, hy, k) + 0.25 * Math.sin(Math.PI * k), lerp(SMALL.z, hz, k));
          }
        } else small.group.position.set(SMALL.x, TABLE_TOP, SMALL.z);

        // ---- 謝幕的燈籠微光
        const on = id === 'a8_c001';
        const fadeAll = on ? clamp(t / 1.0) * (1 - clamp((t - (tl.duration - 1.5)) / 1.5)) : 0;
        motes.forEach((m) => {
          m.s.visible = fadeAll > 0.002;
          if (!m.s.visible) return;
          const ph = ((t / m.period) + m.phase) % 1;
          const y = lerp(5.6, 0.4, ph);
          m.s.position.set(m.x0 + m.sway * Math.sin(ph * Math.PI * 2 * 1.5 + m.phase * 6), y, 1.2 + 1.2 * m.phase);
          const edge = clamp(Math.min(ph * m.period / 1.0, (1 - ph) * m.period / 1.0));
          (m.s.material as SpriteMaterial).opacity = 0.42 * edge * fadeAll;
        });
      },
    };
  },
};
