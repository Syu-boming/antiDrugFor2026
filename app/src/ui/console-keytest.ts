// 按鍵測試（v1.2 第 19.2 節）：顯示簡報筆實際送出的 key／code，核對預設映射；
// 測到其他鍵（例如黑屏鍵送 b）可以把它加進映射（存在本機設定，舞台與控制台共用）。
// 用在兩個地方：dist/keytest.html（獨立頁，課前測試）與教師控制台的「按鍵測試」面板。
// 只在畫面上顯示，不記錄、不上傳。
import {
  ACTION_LABEL, DEFAULT_KEYMAP, FIXED_BLOCK, InputController, keyLabel, loadKeymapOverrides, saveKeymapOverrides,
  type Action, type KeyLogEntry,
} from '../engine/input';

const CHECKS: { id: string; label: string; test: (e: KeyLogEntry) => boolean }[] = [
  { id: 'next', label: '下一步（PageDown）', test: (e) => e.action === 'next' && !e.repeat },
  { id: 'prev', label: '上一步（PageUp）', test: (e) => e.action === 'prev' && !e.repeat },
  { id: 'pause', label: '黑屏鍵：暫停／繼續（句點）', test: (e) => e.action === 'pause' && !e.repeat },
  { id: 'f5', label: '放映鍵送出 F5（已攔截）', test: (e) => e.code === 'F5' || e.key === 'F5' },
  { id: 'esc', label: '放映鍵送出 Esc（已攔截）', test: (e) => e.code === 'Escape' || e.key === 'Escape' || e.key === 'Esc' },
  { id: 'repeat', label: '長按：重複訊號已忽略', test: (e) => e.repeat && e.action !== null },
];

const REMAP: (Action | null)[] = ['next', 'prev', 'pause', 'replay', 'block', null];

export class KeyTestPanel {
  private log: (KeyLogEntry & { ms: number })[] = [];
  private seen = new Set<string>();
  private last: KeyLogEntry | null = null;
  private els: Record<string, HTMLElement> = {};
  /** 映射改了之後要重新讀取的 InputController（舞台與控制台由 storage 事件自動更新） */
  input: InputController | null = null;

  constructor(root: HTMLElement, private opts: { embedded: boolean; onClose?: () => void }) {
    root.classList.add('kt');
    root.innerHTML = `
      <div class="kt-head">
        <div class="kt-title">按鍵測試</div>
        <div class="kt-hint">簡報筆每顆鍵都按一次，也試長按；放映鍵按兩次（它會交替送出 F5 與 Esc）。${opts.embedded ? '<b>測試中按鍵不會送到劇場。</b>' : ''}</div>
        ${opts.embedded ? '<button class="kt-close" data-kt="close">關閉按鍵測試</button>' : ''}
      </div>
      <div class="kt-main">
        <div class="kt-last">
          <div class="kt-last-key" data-el="lastKey">請按簡報筆</div>
          <div class="kt-last-meta" data-el="lastMeta">key／code 會顯示在這裡</div>
          <div class="kt-last-act" data-el="lastAct"></div>
          <div class="kt-remap" data-el="remap" hidden>
            <span data-el="remapLbl"></span>
            ${REMAP.map((a) => `<button data-remap="${a ?? 'none'}">${a ? ACTION_LABEL[a] : '不做動作'}</button>`).join('')}
          </div>
        </div>
        <div class="kt-side">
          <ul class="kt-checks" data-el="checks"></ul>
          <div class="kt-sub">最近的按鍵</div>
          <ol class="kt-log" data-el="log"></ol>
        </div>
      </div>
      <div class="kt-foot">
        <div class="kt-map" data-el="map"></div>
        <button data-kt="reset">恢復預設映射</button>
        <div class="kt-note">F5／Esc 一律攔截、不能改。全螢幕時長按 Esc 約 2 秒仍會退出全螢幕（瀏覽器限制）。這一頁只在畫面上顯示按鍵，不記錄、不上傳。</div>
      </div>`;
    root.querySelectorAll<HTMLElement>('[data-el]').forEach((el) => { this.els[el.dataset.el!] = el; });
    root.addEventListener('click', (ev) => {
      const b = (ev.target as HTMLElement).closest('button');
      if (!b) return;
      b.blur();
      if (b.dataset.kt === 'close') this.opts.onClose?.();
      if (b.dataset.kt === 'reset') { saveKeymapOverrides({}); this.afterMapChange(); }
      if (b.dataset.remap && this.last) {
        const code = this.last.code || this.last.key;
        if ((FIXED_BLOCK as readonly string[]).includes(code)) return;
        const o = loadKeymapOverrides();
        const a = b.dataset.remap === 'none' ? null : (b.dataset.remap as Action);
        if (DEFAULT_KEYMAP[code] === a || (a === null && !(code in DEFAULT_KEYMAP))) delete o[code];
        else o[code] = a;
        saveKeymapOverrides(o);
        this.afterMapChange();
      }
    });
    this.render();
  }

  private afterMapChange(): void {
    this.input?.reloadKeymap();
    if (this.last && this.input) this.last = { ...this.last, action: this.input.map[this.last.code || this.last.key] ?? null };
    this.render();
  }

  handleKey(e: KeyLogEntry): void {
    this.last = e;
    this.log.unshift({ ...e, ms: Date.now() });
    if (this.log.length > 14) this.log.pop();
    for (const c of CHECKS) if (c.test(e)) this.seen.add(c.id);
    this.render();
  }

  render(): void {
    const e = this.last;
    const { lastKey, lastMeta, lastAct, remap, remapLbl, checks, log, map } = this.els;
    if (e) {
      lastKey.textContent = keyLabel(e.key, e.code);
      lastMeta.textContent = `key=${JSON.stringify(e.key)}　code=${e.code || '（空）'}${e.repeat ? '　長按重複（已忽略）' : ''}`;
      lastAct.textContent = e.action ? `→ ${ACTION_LABEL[e.action]}` : '→ 這顆鍵目前沒有作用';
      lastAct.className = `kt-last-act ${e.action ? (e.action === 'block' ? 'blocked' : 'mapped') : 'unmapped'}`;
      const code = e.code || e.key;
      const fixed = (FIXED_BLOCK as readonly string[]).includes(code);
      remap.hidden = fixed || e.repeat;
      remapLbl.textContent = `把「${keyLabel(e.key, e.code)}」設成：`;
    }
    checks.replaceChildren(...CHECKS.map((c) => {
      const li = document.createElement('li');
      li.className = this.seen.has(c.id) ? 'ok' : '';
      li.textContent = `${this.seen.has(c.id) ? '✓' : '○'} ${c.label}`;
      return li;
    }));
    log.replaceChildren(...this.log.map((k) => {
      const li = document.createElement('li');
      li.textContent = `${keyLabel(k.key, k.code)}　code=${k.code || '（空）'}${k.repeat ? '　（長按重複）' : ''}　${k.action ? `→ ${ACTION_LABEL[k.action]}` : '→ 無作用'}`;
      return li;
    }));
    const o = loadKeymapOverrides();
    const custom = Object.entries(o).map(([code, a]) => `${code} → ${a ? ACTION_LABEL[a] : '不做動作'}`);
    map.textContent = `預設：PageDown／→ 下一步，PageUp／← 上一步，句點／空白鍵 暫停繼續，R 重播，F5／Esc 攔截。${custom.length ? `本機加設：${custom.join('、')}` : '沒有本機加設。'}`;
  }
}

/** 獨立的按鍵測試頁（dist/keytest.html） */
function mountPage(): void {
  const root = document.getElementById('keytest-root');
  if (!root || document.body.dataset.page !== 'keytest') return;
  const panel = new KeyTestPanel(root, { embedded: false });
  const input = new InputController(() => undefined);
  panel.input = input;
  input.onKey = (e) => panel.handleKey(e);
  input.attach();
  document.addEventListener('contextmenu', (e) => e.preventDefault());
}

if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mountPage);
  else mountPage();
}
