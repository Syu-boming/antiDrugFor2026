// 題卡疊層（v1.2 第 16.3 節，G4 後凍結樣式）：
// - 題目在上、三個選項直排；每列有大號數字＋手指圖示（比幾根手指）＋形狀標記，不只靠顏色。
// - 思考時題卡完全靜止，沒有倒數。
// - 揭答：正解蓋「正解」紙印章＋勾號＋外框，其他選項變淡；不畫紅叉、不用紅綠配對（印章與外框用靛藍）。
// - 下方八盞燈：每完成一題點亮一盞（只看完成，不看答對率），亮起是慢慢漸亮，不閃爍。
import type { QuizData } from '../types/cue';
import { clamp, ease, lerp } from '../util/math';

/** 手指圖示：伸出 n 根手指 */
function handSvg(n: number): string {
  const fingers: string[] = [];
  for (let i = 0; i < 4; i++) {
    const up = i < n;
    const x = 9 + i * 8;
    fingers.push(up
      ? `<rect x="${x}" y="3" width="6.6" height="25" rx="3.3"/>`
      : `<rect x="${x}" y="19" width="6.6" height="10" rx="3.3"/>`);
  }
  return `<svg class="ico-hand" viewBox="0 0 48 52" aria-hidden="true"><g fill="currentColor">${fingers.join('')}
    <rect x="7" y="22" width="34" height="26" rx="10"/><rect x="0" y="27" width="13" height="7" rx="3.5" transform="rotate(-25 6 30)"/></g></svg>`;
}

/** 形狀標記：1 圓形、2 三角形、3 方形 */
function shapeSvg(n: number): string {
  const shape = n === 1 ? '<circle cx="20" cy="20" r="15"/>'
    : n === 2 ? '<polygon points="20,4 37,35 3,35"/>'
      : '<rect x="5" y="5" width="30" height="30" rx="3"/>';
  return `<svg class="ico-shape" viewBox="0 0 40 40" aria-hidden="true"><g fill="currentColor">${shape}</g></svg>`;
}

function lampSvg(): string {
  return `<svg viewBox="0 0 40 52" aria-hidden="true">
    <rect class="lamp-cap" x="13" y="2" width="14" height="6" rx="2"/>
    <ellipse class="lamp-body" cx="20" cy="27" rx="16" ry="18"/>
    <ellipse class="lamp-lit" cx="20" cy="27" rx="16" ry="18"/>
    <path class="lamp-rib" d="M20 9 V45 M11 11 Q4 27 11 43 M29 11 Q36 27 29 43" fill="none"/>
    <rect class="lamp-cap" x="13" y="44" width="14" height="6" rx="2"/></svg>`;
}

export class QuizCardView {
  private card: HTMLElement;
  private rows: HTMLElement[] = [];
  private lamps: HTMLElement[] = [];
  private qid = '';

  constructor(private host: HTMLElement) {
    host.innerHTML = `<div class="quiz"><div class="quiz-q"></div><div class="quiz-opts"></div><div class="quiz-lamps"></div></div>`;
    this.card = host.querySelector('.quiz')!;
    const lampBox = host.querySelector('.quiz-lamps')!;
    for (let i = 0; i < 8; i++) {
      const d = document.createElement('div');
      d.className = 'lamp';
      d.innerHTML = lampSvg();
      lampBox.appendChild(d);
      this.lamps.push(d);
    }
    host.style.opacity = '0';
  }

  private build(q: QuizData): void {
    this.qid = q.qid;
    this.card.querySelector('.quiz-q')!.textContent = q.question;
    const box = this.card.querySelector('.quiz-opts')!;
    box.replaceChildren();
    this.rows = q.options.map((text, i) => {
      const n = i + 1;
      const row = document.createElement('div');
      row.className = `quiz-opt opt-${n}`;
      row.innerHTML = `<span class="opt-num">${n}</span>${handSvg(n)}${shapeSvg(n)}<span class="opt-text"></span>
        <span class="opt-stamp"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12.5 L9.5 18 L20 6" fill="none" stroke="currentColor" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/></svg>正解</span>`;
      row.querySelector('.opt-text')!.textContent = text;
      box.appendChild(row);
      return row;
    });
  }

  /**
   * @param visible 題卡不透明度 0–1
   * @param reveal 揭答進度 0–1
   * @param lamps 八盞燈亮度 0–1
   */
  update(quiz: QuizData | null, visible: number, reveal: number, lamps: number[]): void {
    if (!quiz || visible <= 0.001) { this.host.style.opacity = '0'; this.host.hidden = true; return; }
    if (quiz.qid !== this.qid) this.build(quiz);
    this.host.hidden = false;
    this.host.style.opacity = String(clamp(visible));
    this.card.style.transform = `translateY(${(1 - ease('out', visible)) * 4}%)`;
    const r = clamp(reveal);
    this.rows.forEach((row, i) => {
      const correct = i + 1 === quiz.answer;
      row.classList.toggle('correct', correct && r > 0);
      row.style.opacity = correct ? '1' : String(lerp(1, 0.36, r));
      const stamp = row.querySelector<HTMLElement>('.opt-stamp')!;
      if (correct && r > 0) {
        // 印章：從稍大、透明蓋下到原尺寸（0.45 秒，單次動作，不閃爍）
        const s = lerp(1.5, 1, ease('out', r));
        stamp.style.opacity = String(clamp(r * 1.6));
        stamp.style.transform = `translateY(-62%) rotate(-7deg) scale(${s})`;
        row.style.setProperty('--frame', String(clamp(r * 1.4)));
      } else {
        stamp.style.opacity = '0';
        row.style.setProperty('--frame', '0');
      }
    });
    lamps.forEach((lv, i) => this.lamps[i]?.style.setProperty('--lit', String(clamp(lv))));
  }

  get revealedVisible(): boolean { return this.rows.some((r) => r.classList.contains('correct')); }
}
