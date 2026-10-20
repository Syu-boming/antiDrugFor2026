// 舞台層狀態：給定（cue, 時間）算出布幕、署名卡、燈光、相機、題卡、燈籠進度。
// 這是純函式：同一個 cue 與時間永遠得到同一個畫面，所以上一步、重播、擷取都能精確重建。
//
// 舞台層動畫表（cue.animation 的 name）：
//   title.fadeOut / title.fadeIn       署名卡淡出／淡入
//   curtain.open / curtain.close       布幕打開／合攏
//   light.dim {to} / light.restore     舞台燈調暗／恢復
//   camera.move {to} / camera.cut {to} 相機移動到預設鏡位／直接切
//   quiz.show / quiz.hide / quiz.reveal  題卡出現／收起／揭答
//   lamp.light {index}                 點亮第幾盞燈
import type { CueTimeline, ResolvedAnim } from '../cues/timeline';
import { CAMERA_PRESETS, type CameraPreset } from '../stage/layers';
import { ease, lerp, clamp } from '../util/math';

export interface CameraState { pos: [number, number, number]; target: [number, number, number]; fov: number }

export interface WorldState {
  /** 0＝合攏，1＝全開 */
  curtain: number;
  /** 署名卡不透明度 */
  titleCard: number;
  /** 舞台燈 0–1 */
  light: number;
  camera: CameraState;
  /** 題卡不透明度 */
  quizVisible: number;
  /** 揭答進度 0–1（印章蓋下） */
  quizReveal: number;
  /** 八盞燈的亮度 0–1 */
  lamps: number[];
}

const presetOf = (name: unknown): CameraPreset => CAMERA_PRESETS[String(name)] ?? CAMERA_PRESETS.wide;
const cloneCam = (p: CameraPreset): CameraState => ({ pos: [...p.pos], target: [...p.target], fov: p.fov });

/** 依 cue 種類給的預設起始狀態 */
function initialWorld(tl: CueTimeline, lampsBefore: number[]): WorldState {
  const k = tl.cue.kind;
  const st = tl.cue.initialState.stage ?? {};
  const curtainDefault = k === 'title' ? 'closed' : 'open';
  const quizOn = st.quiz ?? (k === 'reveal');
  return {
    curtain: (st.curtain ?? curtainDefault) === 'open' ? 1 : 0,
    titleCard: (st.titleCard ?? k === 'title') ? 1 : 0,
    light: st.light ?? (k === 'quiz' || k === 'reveal' ? 0.55 : 1),
    camera: cloneCam(presetOf(st.camera ?? (k === 'title' || k === 'curtain' ? 'wide' : k === 'quiz' || k === 'reveal' ? 'quiz' : 'medium'))),
    quizVisible: quizOn ? 1 : 0,
    quizReveal: 0,
    lamps: Array.from({ length: 8 }, (_, i) => (lampsBefore.includes(i + 1) ? 1 : 0)),
  };
}

/** 鏡頭移動預設用正弦緩動（較慢的最高速度，光敏較安全） */
const DEFAULT_EASE: Record<string, string> = { 'camera.move': 'sine' };

function progress(a: ResolvedAnim, t: number): number {
  if (a.duration <= 0) return t >= a.start ? 1 : 0;
  return ease(a.ease ?? DEFAULT_EASE[a.name], (t - a.start) / a.duration);
}

/**
 * @param lampsBefore 這個 cue 之前已經點亮的燈（1–8）
 */
export function evaluateWorld(tl: CueTimeline, t: number, lampsBefore: number[]): WorldState {
  const w = initialWorld(tl, lampsBefore);
  for (const a of tl.anims) {
    if (a.target) continue; // 角色動畫交給 PuppetDirector
    if (t < a.start && a.duration > 0) continue; // 還沒開始
    const p = progress(a, t);
    switch (a.name) {
      case 'title.fadeOut': w.titleCard = lerp(w.titleCard, 0, p); break;
      case 'title.fadeIn': w.titleCard = lerp(w.titleCard, 1, p); break;
      case 'curtain.open': w.curtain = lerp(w.curtain, 1, p); break;
      case 'curtain.close': w.curtain = lerp(w.curtain, 0, p); break;
      case 'light.dim': w.light = lerp(w.light, Number(a.params.to ?? 0.55), p); break;
      case 'light.restore': w.light = lerp(w.light, 1, p); break;
      case 'quiz.show': w.quizVisible = lerp(w.quizVisible, 1, p); w.quizReveal = 0; break;
      case 'quiz.hide': w.quizVisible = lerp(w.quizVisible, 0, p); break;
      case 'quiz.reveal': w.quizVisible = 1; w.quizReveal = lerp(w.quizReveal, 1, p); break;
      case 'lamp.light': {
        const i = clamp(Number(a.params.index ?? tl.cue.lamp ?? 1), 1, 8) - 1;
        w.lamps[i] = Math.max(w.lamps[i], p);
        break;
      }
      case 'camera.move':
      case 'camera.cut': {
        const to = presetOf(a.params.to);
        const q = a.name === 'camera.cut' ? (t >= a.start ? 1 : 0) : p;
        w.camera = {
          pos: [lerp(w.camera.pos[0], to.pos[0], q), lerp(w.camera.pos[1], to.pos[1], q), lerp(w.camera.pos[2], to.pos[2], q)],
          target: [lerp(w.camera.target[0], to.target[0], q), lerp(w.camera.target[1], to.target[1], q), lerp(w.camera.target[2], to.target[2], q)],
          fov: lerp(w.camera.fov, to.fov, q),
        };
        break;
      }
      default: break; // 未知動畫：忽略（驗證時另外提醒）
    }
  }
  return w;
}

/** 已知的舞台層動畫名稱（給驗證與教師選單用） */
export const STAGE_ANIMS = ['title.fadeOut', 'title.fadeIn', 'curtain.open', 'curtain.close', 'light.dim', 'light.restore',
  'camera.move', 'camera.cut', 'quiz.show', 'quiz.hide', 'quiz.reveal', 'lamp.light'];
