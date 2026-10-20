// 按鍵映射（v1.2 第 19.1、19.2 節）：
//   PageDown／→       下一步            PageUp／←   回上一個穩定節點
//   句點（黑屏鍵）     暫停／繼續        空白鍵      暫停／繼續（筆電備援）
//   R                 重播目前段落      F5／Esc     一律攔截、不做任何動作（放映鍵會交替送出這兩個）
//   M                 教師選單（預設隱藏）
// 忽略 key repeat（長按）；接管的按鍵一律 preventDefault，避免捲頁或重新整理。

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

/** event.code 缺漏時（少數簡報筆或遠端桌面）以 event.key 對回 code */
const KEY_TO_CODE: Record<string, string> = {
  PageDown: 'PageDown', PageUp: 'PageUp', ArrowRight: 'ArrowRight', ArrowLeft: 'ArrowLeft',
  '.': 'Period', ' ': 'Space', Spacebar: 'Space', r: 'KeyR', R: 'KeyR', F5: 'F5', Escape: 'Escape', Esc: 'Escape', m: 'KeyM', M: 'KeyM',
};

export interface KeyLogEntry { key: string; code: string; repeat: boolean; action: Action | null; at: number }

export class InputController {
  readonly log: KeyLogEntry[] = [];
  ignoredRepeats = 0;
  blocked = 0;
  lastBlockedKey: string | null = null;
  onKey?: (e: KeyLogEntry) => void;

  constructor(private onAction: (a: Action) => void, private keymap: Record<string, Action> = DEFAULT_KEYMAP) {}

  attach(target: Window = window): void {
    target.addEventListener('keydown', this.onKeyDown, { capture: true });
    target.addEventListener('keyup', this.onKeyUp, { capture: true });
  }

  detach(target: Window = window): void {
    target.removeEventListener('keydown', this.onKeyDown, { capture: true });
    target.removeEventListener('keyup', this.onKeyUp, { capture: true });
  }

  private resolve(e: KeyboardEvent): Action | null {
    const code = e.code || KEY_TO_CODE[e.key] || '';
    return this.keymap[code] ?? this.keymap[KEY_TO_CODE[e.key] ?? ''] ?? null;
  }

  private onKeyDown = (e: KeyboardEvent): void => {
    let action = this.resolve(e);
    // 有修飾鍵時只攔 F5（Ctrl＋F5 等）；其他組合鍵交還瀏覽器
    if (action && action !== 'block' && (e.ctrlKey || e.metaKey || e.altKey)) action = null;
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
