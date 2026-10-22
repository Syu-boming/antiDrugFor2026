// HTML 疊層：署名卡、準備畫面、GPU 中斷畫面、暫代音訊標示、暫停標示、教師選單（預設隱藏）。

/** 署名卡「許博明老師製作」（片頭待機與片尾共用同一款） */
export class TitleCardView {
  constructor(private el: HTMLElement) {
    el.innerHTML = `<div class="sig-card"><div class="sig-text">許博明老師製作</div></div>`;
  }
  /** 換上素材的署名卡紙（assets/final/tex-titlecard-paper；字仍由程式排版） */
  setPaper(dataUrl: string): void {
    const card = this.el.querySelector<HTMLElement>('.sig-card')!;
    card.classList.add('papered');
    card.style.backgroundImage = `url("${dataUrl}")`;
  }
  update(opacity: number): void {
    this.el.hidden = opacity <= 0.001;
    this.el.style.opacity = String(opacity);
  }
}

export interface ReadyStatus { label: string; value: string; ok: boolean | null }

/** 準備畫面：素材檢查、啟用聲音、確認全螢幕；素材沒就緒時「準備播放」按鈕不能按 */
export class ReadyScreen {
  private list: HTMLElement;
  private btn: HTMLButtonElement;
  private msg: HTMLElement;
  onStart?: () => void;

  constructor(private el: HTMLElement) {
    el.innerHTML = `
      <div class="ready-box">
        <div class="ready-title">反毒剪紙劇場</div>
        <div class="ready-sub">許博明老師製作</div>
        <ul class="ready-list"></ul>
        <button class="ready-btn" disabled>準備播放</button>
        <div class="ready-msg">按「準備播放」會啟用聲音並切換全螢幕，然後停在署名卡，等簡報筆按「下一步」。</div>
      </div>`;
    this.list = el.querySelector('.ready-list')!;
    this.btn = el.querySelector('.ready-btn')!;
    this.msg = el.querySelector('.ready-msg')!;
    this.btn.addEventListener('click', () => this.onStart?.());
  }

  setStatus(items: ReadyStatus[]): void {
    this.list.replaceChildren(...items.map((s) => {
      const li = document.createElement('li');
      li.className = s.ok === false ? 'bad' : s.ok ? 'good' : '';
      li.innerHTML = '<span class="k"></span><span class="v"></span>';
      li.querySelector('.k')!.textContent = s.label;
      li.querySelector('.v')!.textContent = s.value;
      return li;
    }));
  }

  setReady(ready: boolean, message?: string): void {
    this.btn.disabled = !ready;
    if (message) this.msg.textContent = message;
    if (ready) this.btn.focus();
  }

  /** 全劇缺配音：第一次按「準備播放」後改成確認按鈕（再按一次才開演）；files＝載不到的配音／嘴型資料檔（G7） */
  confirmMissingVo(n: number, files: string[] = []): void {
    const lip = files.filter((f) => !f.startsWith('vo_'));
    const what = [n ? `缺 ${n} 句配音：這些句子只有字幕、沒有聲音。` : '', lip.length ? `缺嘴型資料：角色說話時嘴巴不會動。` : ''].join('');
    const fileNote = files.length ? `缺的檔：${files.slice(0, 4).map((f) => `data/${f}`).join('、')}${files.length > 4 ? '…' : ''}。` : '';
    this.btn.textContent = n ? `仍要播放（缺 ${n} 句配音）` : '仍要播放（缺嘴型資料）';
    this.btn.classList.add('confirm');
    this.msg.textContent = `${what}${fileNote}請先確認交付資料夾是否完整複製（最好把整個交付資料夾重新複製到本機硬碟）；確定仍要開演，請再按一次「準備播放」（簡報筆按「下一步」也可以）。`;
    this.msg.classList.add('warn');
    this.btn.focus();
  }

  show(on: boolean): void { this.el.hidden = !on; document.body.classList.toggle('show-cursor', on); }
  get visible(): boolean { return !this.el.hidden; }
}

/** GPU 中斷畫面：停止聲音、停在這裡，老師按一次後重建 */
export class LostScreen {
  private text: HTMLElement;
  constructor(private el: HTMLElement) {
    el.innerHTML = `<div class="lost-box"><div class="lost-title">畫面暫停</div><div class="lost-text"></div></div>`;
    this.text = el.querySelector('.lost-text')!;
  }
  show(text: string): void { this.text.textContent = text; this.el.hidden = false; }
  hide(): void { this.el.hidden = true; }
  get visible(): boolean { return !this.el.hidden; }
}

/** 角落小標示（暫代音訊、暫停） */
export class Badge {
  constructor(private el: HTMLElement, text: string) { el.textContent = text; el.hidden = true; }
  set(on: boolean): void { if (this.el.hidden === on) this.el.hidden = !on; }
}

export interface TeacherMenuHandlers {
  getAvOffset(): number;
  setAvOffset(ms: number): void;
  getQuality(): string;
  setQuality(q: 'A' | 'B'): void;
  getLock30(): boolean;
  setLock30(on: boolean): void;
  getLeadIn(): number;
  setLeadIn(ms: number): void;
  cues(): { id: string; title: string }[];
  gotoCue(id: string): void;
  status(): string;
}

/** 教師選單（M 鍵開關，預設隱藏）：聲畫偏移、開頭靜音（HDMI 吞音）、畫質、鎖 30 fps、跳到 cue、按鍵測試 */
export class TeacherMenu {
  private keyLine: HTMLElement;
  private statusLine: HTMLElement;
  private avValue: HTMLElement;
  constructor(private el: HTMLElement, private h: TeacherMenuHandlers) {
    el.innerHTML = `
      <div class="tm-title">教師選單（M 鍵關閉）</div>
      <div class="tm-row"><span>聲畫偏移</span><button data-av="-10">−10</button><b class="tm-av"></b><button data-av="10">＋10</button><span class="tm-hint">毫秒，正值＝畫面提前</span></div>
      <div class="tm-row"><span>開頭靜音</span><button data-lead="0">0</button><button data-lead="200">200</button><button data-lead="400">400</button><span class="tm-hint">毫秒；接投影機時第一個字被吃掉就加長</span></div>
      <div class="tm-row"><span>畫質</span><button data-q="A">A 級</button><button data-q="B">B 級</button></div>
      <div class="tm-row"><span>更新率</span><button data-lock="1">鎖 30 fps</button><button data-lock="0">不鎖</button></div>
      <div class="tm-row"><span>跳到</span><select class="tm-cue"></select><button data-go="1">前往</button></div>
      <div class="tm-row tm-key">按鍵測試：—</div>
      <div class="tm-row tm-status"></div>`;
    this.keyLine = el.querySelector('.tm-key')!;
    this.statusLine = el.querySelector('.tm-status')!;
    this.avValue = el.querySelector('.tm-av')!;
    el.addEventListener('click', (e) => {
      const b = (e.target as HTMLElement).closest('button');
      if (!b) return;
      if (b.dataset.av) h.setAvOffset(h.getAvOffset() + Number(b.dataset.av));
      if (b.dataset.q) h.setQuality(b.dataset.q as 'A' | 'B');
      if (b.dataset.lead) h.setLeadIn(Number(b.dataset.lead));
      if (b.dataset.lock) h.setLock30(b.dataset.lock === '1');
      if (b.dataset.go) h.gotoCue((el.querySelector('.tm-cue') as HTMLSelectElement).value);
      b.blur();
      this.refresh();
    });
    el.hidden = true;
  }
  toggle(): void { this.el.hidden = !this.el.hidden; if (!this.el.hidden) this.fillCues(); this.refresh(); document.body.classList.toggle('show-cursor', !this.el.hidden); }
  get visible(): boolean { return !this.el.hidden; }
  private fillCues(): void {
    const sel = this.el.querySelector('.tm-cue') as HTMLSelectElement;
    sel.replaceChildren(...this.h.cues().map((c) => { const o = document.createElement('option'); o.value = c.id; o.textContent = `${c.id} ${c.title}`; return o; }));
  }
  showKey(key: string, code: string): void { this.keyLine.textContent = `按鍵測試：key=${JSON.stringify(key)} code=${code || '（空）'}`; }
  refresh(): void {
    if (this.el.hidden) return;
    this.avValue.textContent = String(this.h.getAvOffset());
    this.statusLine.textContent = this.h.status();
    this.el.querySelectorAll<HTMLButtonElement>('button[data-q]').forEach((b) => b.classList.toggle('on', b.dataset.q === this.h.getQuality()));
    this.el.querySelectorAll<HTMLButtonElement>('button[data-lead]').forEach((b) => b.classList.toggle('on', Number(b.dataset.lead) === this.h.getLeadIn()));
    this.el.querySelectorAll<HTMLButtonElement>('button[data-lock]').forEach((b) => b.classList.toggle('on', (b.dataset.lock === '1') === this.h.getLock30()));
  }
}
