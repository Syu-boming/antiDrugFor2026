// 執行參數：URL 參數優先，其次是本機設定（localStorage 只存個人化設定，讀寫失敗也能正常演出）。
//   ?cues=demo        要載入的 cue 檔（app/cues/<名稱>.json）
//   ?capture=1        虛擬時鐘擷取模式（固定步長，不發聲）
//   ?autostart=1      跳過「準備播放」按鈕（擷取與測試用）
//   ?q=A|B            畫質等級
//   ?fps=30           鎖 30 fps
//   ?av=60            聲畫偏移（毫秒，正值＝畫面提前）
//   ?step=30          虛擬時鐘每秒格數（擷取用）
//   ?autostep=1       虛擬時鐘每個畫面更新自動前進一格（預覽擷取結果用）
//   ?nofs=1           按「準備播放」時不切換全螢幕
//   ?menu=1           一開始就打開教師選單（含按鍵測試）
import type { Quality } from './stage/stage';

export interface Config {
  cues: string;
  capture: boolean;
  autostart: boolean;
  autostep: boolean;
  quality: Quality;
  lock30: boolean;
  avOffsetMs: number;
  stepFps: number;
  noFullscreen: boolean;
  menu: boolean;
}

const KEY = 'antidrug-theater-settings';

function stored(): Partial<Config> {
  try { return JSON.parse(localStorage.getItem(KEY) ?? '{}') as Partial<Config>; } catch { return {}; }
}

export function saveSettings(patch: Partial<Pick<Config, 'quality' | 'lock30' | 'avOffsetMs'>>): void {
  try { localStorage.setItem(KEY, JSON.stringify({ ...stored(), ...patch })); } catch { /* 私密模式或 kiosk：不保存也沒關係 */ }
}

export function readConfig(search = location.search): Config {
  const p = new URLSearchParams(search);
  const s = stored();
  const flag = (k: string): boolean => p.get(k) === '1' || p.get(k) === 'true';
  const capture = flag('capture');
  const q = (p.get('q') ?? s.quality ?? 'A').toUpperCase();
  return {
    cues: p.get('cues') ?? 'demo',
    capture,
    autostart: flag('autostart') || capture,
    autostep: flag('autostep'),
    quality: q === 'B' ? 'B' : 'A',
    lock30: p.has('fps') ? p.get('fps') === '30' : !!s.lock30,
    avOffsetMs: p.has('av') ? Number(p.get('av')) || 0 : Number(s.avOffsetMs ?? 0),
    stepFps: Math.max(1, Number(p.get('step') ?? 30) || 30),
    noFullscreen: flag('nofs') || capture,
    menu: flag('menu'),
  };
}
