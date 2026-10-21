// 按鍵映射（v1.2 第 19.1、19.2 節）：
//   PageDown／→       下一步            PageUp／←   回上一個穩定節點
//   句點（黑屏鍵）     暫停／繼續        空白鍵      暫停／繼續（筆電備援）
//   R                 重播目前段落      F5／Esc     一律攔截、不做任何動作（放映鍵會交替送出這兩個）
//   M                 教師選單（預設隱藏）
// 忽略 key repeat（長按）；接管的按鍵一律 preventDefault，避免捲頁或重新整理。
//
// 舞台視窗、教師控制台、按鍵測試頁共用這個模組（同一份映射）。
// 「正式映射以這支簡報筆的測試結果為準」：按鍵測試頁可以把實測到的其他鍵（例如黑屏鍵送 b）加進映射，
// 存在本機設定（localStorage，讀寫失敗就用預設；只存按鍵對應，不存任何使用紀錄）。F5／Esc 固定攔截，不能改。

export type Action = 'next' | 'prev' | 'pause' | 'replay' | 'block' | 'menu';

export const DEFAULT_KEYMAP: Record<string, Action> = {
  PageDown: 'next',
  ArrowRight: 'next',
  PageUp: 'prev',
  ArrowLeft: 'prev',
  Period: 'pause',
  NumpadDecimal: 'pause',
  Space: 'pause',
  KeyR: 'replay',
  F5: 'block',
  Escape: 'block',
  KeyM: 'menu',
};

/** 按鍵測試頁與控制台顯示用的中文名稱 */
export const ACTION_LABEL: Record<Action, string> = {
  next: '下一步', prev: '上一步（回穩定節點）', pause: '暫停／繼續', replay: '重播目前段落', block: '攔截（不動作）', menu: '教師選單',
};

/** 一律攔截、不能改映射的鍵（放映鍵交替送出 F5 與 Esc） */
export const FIXED_BLOCK = ['F5', 'Escape'] as const;

/** event.code 缺漏時（少數簡報筆或遠端桌面）以 event.key 對回 code */
const KEY_TO_CODE: Record<string, string> = {
  PageDown: 'PageDown', PageUp: 'PageUp', ArrowRight: 'ArrowRight', ArrowLeft: 'ArrowLeft',
  '.': 'Period', ' ': 'Space', Spacebar: 'Space', r: 'KeyR', R: 'KeyR', F5: 'F5', Escape: 'Escape', Esc: 'Escape', m: 'KeyM', M: 'KeyM',
};

/** 本機設定裡的映射覆寫：code → 動作；null＝取消預設映射 */
export const KEYMAP_STORAGE_KEY = 'antidrug-theater-keymap';
export type KeymapOverrides = Record<string, Action | null>;

export function loadKeymapOverrides(): KeymapOverrides {
  try {
    const raw = JSON.parse(localStorage.getItem(KEYMAP_STORAGE_KEY) ?? '{}') as unknown;
    if (!raw || typeof raw !== 'object') return {};
    const out: KeymapOverrides = {};
    for (const [code, a] of Object.entries(raw as Record<string, unknown>)) {
      if ((FIXED_BLOCK as readonly string[]).includes(code)) continue;
      if (a === null || (typeof a === 'string' && a in ACTION_LABEL)) out[code] = a as Action | null;
    }
    return out;
  } catch { return {}; }
}

/** 寫入覆寫；回傳是否成功（私密模式、kiosk 可能失敗，失敗時本次仍可用預設映射演出） */
export function saveKeymapOverrides(o: KeymapOverrides): boolean {
  try {
    const clean = Object.fromEntries(Object.entries(o).filter(([code]) => !(FIXED_BLOCK as readonly string[]).includes(code)));
    if (Object.keys(clean).length) localStorage.setItem(KEYMAP_STORAGE_KEY, JSON.stringify(clean));
    else localStorage.removeItem(KEYMAP_STORAGE_KEY);
    return true;
  } catch { return false; }
}

/** 預設映射＋本機覆寫（F5／Esc 永遠是攔截） */
export function effectiveKeymap(overrides: KeymapOverrides = loadKeymapOverrides()): Record<string, Action> {
  const map: Record<string, Action> = { ...DEFAULT_KEYMAP };
  for (const [code, a] of Object.entries(overrides)) {
    if (a === null) delete map[code];
    else map[code] = a;
  }
  for (const k of FIXED_BLOCK) map[k] = 'block';
  return map;
}

/** event 對應的 code（code 缺漏時用 key 推回） */
export function keyCode(e: Pick<KeyboardEvent, 'code' | 'key'>): string {
  return e.code || KEY_TO_CODE[e.key] || '';
}

/** 依映射解析動作（純函式；有修飾鍵時只攔 F5，其他組合鍵交還瀏覽器） */
export function resolveAction(e: Pick<KeyboardEvent, 'code' | 'key' | 'ctrlKey' | 'metaKey' | 'altKey'>, keymap: Record<string, Action>): Action | null {
  const code = keyCode(e);
  let action: Action | null = keymap[code] ?? keymap[KEY_TO_CODE[e.key] ?? ''] ?? null;
  if (action && action !== 'block' && (e.ctrlKey || e.metaKey || e.altKey)) action = null;
  return action;
}

/** 顯示用的按鍵名稱（空白鍵、句點等看不見的字） */
export function keyLabel(key: string, code: string): string {
  if (key === ' ' || code === 'Space') return '空白鍵';
  if (key === '.' || code === 'Period') return '句點（黑屏鍵）';
  if (key === 'Escape' || key === 'Esc') return 'Esc';
  return key || code || '（空）';
}

export interface KeyLogEntry { key: string; code: string; repeat: boolean; action: Action | null; at: number }

export class InputController {
  readonly log: KeyLogEntry[] = [];
  ignoredRepeats = 0;
  blocked = 0;
  lastBlockedKey: string | null = null;
  onKey?: (e: KeyLogEntry) => void;
  private target: Window | null = null;
  /** 建構時沒有指定映射：跟著本機覆寫（按鍵測試頁改了映射，其他視窗即時更新） */
  private followOverrides: boolean;

  constructor(private onAction: (a: Action) => void, private keymap: Record<string, Action> = effectiveKeymap()) {
    this.followOverrides = arguments.length < 2;
  }

  get map(): Readonly<Record<string, Action>> { return this.keymap; }

  /** 重新讀取本機覆寫（按鍵測試頁存檔後呼叫；其他視窗由 storage 事件自動呼叫） */
  reloadKeymap(): void { this.keymap = effectiveKeymap(); }

  attach(target: Window = window): void {
    this.target = target;
    target.addEventListener('keydown', this.onKeyDown, { capture: true });
    target.addEventListener('keyup', this.onKeyUp, { capture: true });
    target.addEventListener('storage', this.onStorage);
  }

  detach(target: Window = this.target ?? window): void {
    target.removeEventListener('keydown', this.onKeyDown, { capture: true });
    target.removeEventListener('keyup', this.onKeyUp, { capture: true });
    target.removeEventListener('storage', this.onStorage);
    this.target = null;
  }

  private resolve(e: KeyboardEvent): Action | null {
    return resolveAction(e, this.keymap);
  }

  private onStorage = (e: StorageEvent): void => {
    if (this.followOverrides && (e.key === KEYMAP_STORAGE_KEY || e.key === null)) this.reloadKeymap();
  };

  private onKeyDown = (e: KeyboardEvent): void => {
    const action = this.resolve(e);
    const entry: KeyLogEntry = { key: e.key, code: e.code, repeat: e.repeat, action, at: performance.now() };
    this.log.push(entry);
    if (this.log.length > 50) this.log.shift();
    this.onKey?.(entry);
    if (!action) return;
    e.preventDefault();
    e.stopPropagation();
    if (e.repeat) { this.ignoredRepeats++; return; }
    if (action === 'block') { this.blocked++; this.lastBlockedKey = e.code || e.key; return; }
    this.onAction(action);
  };

  private onKeyUp = (e: KeyboardEvent): void => {
    const action = this.resolve(e);
    if (action) { e.preventDefault(); e.stopPropagation(); }
  };
}
