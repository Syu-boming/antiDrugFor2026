// 舞台層狀態：給定（cue, 時間）算出布幕、署名卡、燈光、相機、題卡、燈籠進度、景片立起、降彩、追光。
// 這是純函式：同一個 cue 與時間永遠得到同一個畫面，所以上一步、重播、擷取都能精確重建。
//
// 舞台層動畫表（cue.animation 的 name，沒有 target）：
//   title.fadeOut / title.fadeIn         署名卡淡出／淡入
//   curtain.open / curtain.close         摺層紙布幕打開／合攏（預設 2.2 秒、正弦緩動）
//   set.popup / set.fold                 立體書景片依序立起／收攏（各景片的先後由舞台設定）
//   light.dim {to} / light.restore       舞台燈調暗／恢復（緩慢漸變）
//   fx.desat {to}                        FX8 場景降彩（只作用於景片）
//   fx.spot {to, target | sweep}         FX4 柔和追光（target＝角色 id；sweep＝[[x,y,z],[x,y,z]] 慢慢掃過台口）
//   camera.move {to} / camera.cut {to}   相機移動到鏡位／直接切；to 可以是預設名稱、
//                                        "anchor:<角色>.<錨點>"（沿操偶線看，dist 距離、dy 上下）或 {pos,target,fov}
//   quiz.show / quiz.hide / quiz.reveal  題卡出現／收起／揭答
//   lamp.light {index}                   點亮第幾盞燈
//   fade.out {to} / fade.in              G5：舞台亮度漸暗／漸亮（台口內整個舞台，含角色；字幕、題卡、布幕、台口不受影響；≥0.6 秒）
//   set.swap {set}                       G5：在這個時間點換景（建議在 fade.out 之後、set.fold 收平之後）；由舞台處理，這裡不算
// 換景亮度漸變：時間軸的 enterFade > 0 時，cue 從全暗開始、enterFade 秒內漸亮（dim 1 → 0）。
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
  /** 立體書景片 0＝平躺、1＝立好 */
  set: number;
  /** FX8 降彩 0–1 */
  desat: number;
  /** FX4 追光 0–1 與對象 */
  spot: number;
  spotTarget: string | null;
  /** 追光照的世界座標（沒有角色對象時；掃過台口用） */
  spotAt: [number, number, number] | null;
  /** 舞台調暗（換景亮度漸變）0＝正常、1＝全暗；只蓋台口內的舞台 */
  dim: number;
}

/** 相機鏡位解析：預設名稱、或由舞台提供的錨點鏡位（"anchor:ale.wrist"） */
export type CameraResolver = (name: string, params: Record<string, unknown>) => CameraPreset | null;

const cloneCam = (p: CameraPreset): CameraState => ({ pos: [...p.pos], target: [...p.target], fov: p.fov });

function presetOf(to: unknown, params: Record<string, unknown>, resolver?: CameraResolver): CameraPreset {
  if (to && typeof to === 'object') {
    const o = to as Partial<CameraPreset>;
    if (Array.isArray(o.pos) && Array.isArray(o.target)) return { pos: o.pos as CameraPreset['pos'], target: o.target as CameraPreset['target'], fov: Number(o.fov ?? 20) };
  }
  const name = String(to ?? 'wide');
  return CAMERA_PRESETS[name] ?? resolver?.(name, params) ?? CAMERA_PRESETS.wide;
}

/** 依 cue 種類給的預設起始狀態 */
function initialWorld(tl: CueTimeline, lampsBefore: number[], resolver?: CameraResolver): WorldState {
  const k = tl.cue.kind;
  const st = tl.cue.initialState.stage ?? {};
  const curtainDefault = k === 'title' ? 'closed' : 'open';
  const quizOn = st.quiz ?? (k === 'reveal');
  return {
    curtain: (st.curtain ?? curtainDefault) === 'open' ? 1 : 0,
    titleCard: (st.titleCard ?? k === 'title') ? 1 : 0,
    light: st.light ?? (k === 'quiz' || k === 'reveal' ? 0.55 : 1),
    camera: cloneCam(presetOf(st.camera ?? (k === 'title' || k === 'curtain' ? 'wide' : k === 'quiz' || k === 'reveal' ? 'quiz' : 'medium'), {}, resolver)),
    quizVisible: quizOn ? 1 : 0,
    quizReveal: 0,
    lamps: Array.from({ length: 8 }, (_, i) => (lampsBefore.includes(i + 1) ? 1 : 0)),
    set: st.set ?? 1,
    desat: st.desat ?? 0,
    spot: st.spot ?? 0,
    spotTarget: st.spotTarget ?? null,
    spotAt: null,
    dim: tl.enterFade > 0 ? 1 : 0,
  };
}

/** 鏡頭、布幕、燈光預設用正弦緩動（最高速度只有平均的 1.57 倍，光敏較安全） */
const DEFAULT_EASE: Record<string, string> = {
  'camera.move': 'sine', 'curtain.open': 'sine', 'curtain.close': 'sine', 'light.dim': 'sine', 'light.restore': 'sine',
  'fx.desat': 'sine', 'fx.spot': 'sine', 'set.popup': 'linear', 'set.fold': 'linear', 'title.fadeOut': 'sine', 'title.fadeIn': 'sine',
  'fade.out': 'sine', 'fade.in': 'sine',
};

function progress(a: ResolvedAnim, t: number): number {
  if (a.duration <= 0) return t >= a.start ? 1 : 0;
  return ease(a.ease ?? DEFAULT_EASE[a.name], (t - a.start) / a.duration);
}

/**
 * @param lampsBefore 這個 cue 之前已經點亮的燈（1–8）
 * @param resolver 錨點鏡位解析（舞台提供；沒有就只用預設鏡位）
 */
export function evaluateWorld(tl: CueTimeline, t: number, lampsBefore: number[], resolver?: CameraResolver): WorldState {
  const w = initialWorld(tl, lampsBefore, resolver);
  // 換景亮度漸變（正弦緩動；最快的亮度變化也只有平均的 1.57 倍）
  if (tl.enterFade > 0) w.dim = 1 - ease('sine', t / tl.enterFade);
  for (const a of tl.anims) {
    if (a.target) continue; // 角色動畫交給 PuppetDirector
    if (t < a.start && a.duration > 0) continue; // 還沒開始
    const p = progress(a, t);
    switch (a.name) {
      case 'title.fadeOut': w.titleCard = lerp(w.titleCard, 0, p); break;
      case 'title.fadeIn': w.titleCard = lerp(w.titleCard, 1, p); break;
      case 'curtain.open': w.curtain = lerp(w.curtain, 1, p); break;
      case 'curtain.close': w.curtain = lerp(w.curtain, 0, p); break;
      case 'set.popup': w.set = lerp(w.set, 1, p); break;
      case 'set.fold': w.set = lerp(w.set, 0, p); break;
      case 'light.dim': w.light = lerp(w.light, Number(a.params.to ?? 0.55), p); break;
      case 'light.restore': w.light = lerp(w.light, 1, p); break;
      case 'fx.desat': w.desat = lerp(w.desat, Number(a.params.to ?? 0.55), p); break;
      case 'fx.spot': {
        // to：亮度；target：角色 id；sweep：[[起點],[終點]] 在這段時間內慢慢掃過（亮度先漸亮、最後 20% 漸暗）
        if (Array.isArray(a.params.sweep)) {
          const [p0, p1] = a.params.sweep as [number, number, number][];
          const u = clamp((t - a.start) / Math.max(1e-6, a.duration));
          const e = ease('sine', u);
          w.spotAt = [lerp(p0[0], p1[0], e), lerp(p0[1], p1[1], e), lerp(p0[2], p1[2], e)];
          w.spotTarget = null;
          w.spot = Number(a.params.to ?? 0.8) * Math.min(ease('sine', u / 0.2), 1 - ease('sine', (u - 0.8) / 0.2));
          break;
        }
        w.spot = lerp(w.spot, Number(a.params.to ?? 1), p);
        if (a.params.target) { w.spotTarget = String(a.params.target); w.spotAt = null; }
        break;
      }
      case 'quiz.show': w.quizVisible = lerp(w.quizVisible, 1, p); w.quizReveal = 0; break;
      case 'quiz.hide': w.quizVisible = lerp(w.quizVisible, 0, p); break;
      case 'quiz.reveal': w.quizVisible = 1; w.quizReveal = lerp(w.quizReveal, 1, p); break;
      case 'fade.out': w.dim = lerp(w.dim, clamp(Number(a.params.to ?? 1)), p); break;
      case 'fade.in': w.dim = lerp(w.dim, 0, p); break;
      case 'lamp.light': {
        const i = clamp(Number(a.params.index ?? tl.cue.lamp ?? 1), 1, 8) - 1;
        w.lamps[i] = Math.max(w.lamps[i], p);
        break;
      }
      case 'camera.move':
      case 'camera.cut': {
        const to = presetOf(a.params.to, a.params, resolver);
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
export const STAGE_ANIMS = ['title.fadeOut', 'title.fadeIn', 'curtain.open', 'curtain.close', 'set.popup', 'set.fold', 'light.dim', 'light.restore',
  'fx.desat', 'fx.spot', 'camera.move', 'camera.cut', 'quiz.show', 'quiz.hide', 'quiz.reveal', 'lamp.light', 'set.swap', 'fade.out', 'fade.in'];

/** 時間 t 時應該顯示的景：最後一個已經開始的 set.swap，沒有就是 cue 開始時的景 */
export function setAt(tl: CueTimeline, t: number): string {
  let s = tl.set;
  for (const a of tl.anims) if (a.name === 'set.swap' && t >= a.start && typeof a.params.set === 'string') s = a.params.set;
  return s;
}

/** 這個 cue 從頭到尾會用到的景（開始時的景＋之後 set.swap 換上的景，依出現順序、不重複；換景預先準備用） */
export function setsUsed(tl: CueTimeline): string[] {
  const out = [setAt(tl, 0)];
  for (const a of tl.anims) if (a.name === 'set.swap' && typeof a.params.set === 'string' && !out.includes(a.params.set)) out.push(a.params.set);
  return out;
}

/** 已知的角色動畫名稱 */
export const ACTOR_ANIMS = ['strings.drop', 'strings.tension', 'strings.loosen', 'strings.fade', 'strings.detach',
  'puppet.popup', 'puppet.enter', 'puppet.exit', 'puppet.sit', 'puppet.waveTry', 'puppet.kneeTug', 'puppet.reach', 'puppet.wave',
  'puppet.chest', 'puppet.grab', 'puppet.lean', 'puppet.move', 'puppet.tilt', 'puppet.pose', 'puppet.face', 'puppet.blink', 'puppet.nod'];
