// 字幕疊層（v1.2 第 16.2 節、第 15.3 節）：
// 半透明深色紙條底板、白字、約 2–3 px 細描邊（CSS 以 em 比例計算）、角色名牌與小頭像（先用色塊）。
// 字級＝舞台高度 × 68/1080，每行 ≤16 字、最多兩行（斷行在 timeline 階段就算好）。
// 不用 CSS 轉場：顯示與否完全由時間決定，虛擬時鐘擷取時才會逐格一致。
import type { CueTimeline, ResolvedLine, SubtitlePage } from '../cues/timeline';
import { speakerInfo } from './characters';

/** 兩句之間的空檔短於這個秒數時，字幕條不收起（避免來回閃現） */
const BRIDGE = 0.8;

export class SubtitleView {
  private strip: HTMLElement;
  private avatar: HTMLElement;
  private name: HTMLElement;
  private text: HTMLElement;
  private lastKey = '';

  constructor(private host: HTMLElement) {
    host.innerHTML = `
      <div class="sub-strip" hidden>
        <div class="sub-tag"><span class="sub-avatar"></span><span class="sub-name"></span></div>
        <div class="sub-text"></div>
      </div>`;
    this.strip = host.querySelector('.sub-strip')!;
    this.avatar = host.querySelector('.sub-avatar')!;
    this.name = host.querySelector('.sub-name')!;
    this.text = host.querySelector('.sub-text')!;
  }

  private find(tl: CueTimeline, t: number): { line: ResolvedLine; page: SubtitlePage } | null {
    for (const l of tl.lines) {
      if (t >= l.start && t < l.end) {
        for (const p of l.pages) if (t >= p.start && t < p.end) return { line: l, page: p };
      }
    }
    // 短空檔：保留上一句的最後一頁，直到下一句開始
    for (let i = 0; i < tl.lines.length; i++) {
      const l = tl.lines[i], n = tl.lines[i + 1];
      if (n && t >= l.end && t < n.start && n.start - l.end < BRIDGE) return { line: l, page: l.pages[l.pages.length - 1] };
    }
    return null;
  }

  update(tl: CueTimeline | null, t: number, hidden: boolean): void {
    const cur = !hidden && tl ? this.find(tl, t) : null;
    const key = cur ? `${cur.line.line.id}|${cur.page.start}` : '';
    if (key === this.lastKey) return;
    this.lastKey = key;
    if (!cur) { this.strip.hidden = true; return; }
    const sp = speakerInfo(cur.line.line.speaker);
    this.avatar.style.background = sp.color;
    this.name.textContent = sp.name;
    this.text.replaceChildren(...cur.page.rows.map((r) => {
      const d = document.createElement('div');
      d.className = 'sub-row';
      d.textContent = r;
      return d;
    }));
    this.strip.hidden = false;
  }

  get currentText(): string { return this.strip.hidden ? '' : this.text.textContent ?? ''; }
  get element(): HTMLElement { return this.host; }
}
