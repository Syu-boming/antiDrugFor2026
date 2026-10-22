// 共用：HTML 外殼、字型、簡單的文件區塊（同一份內容輸出成 Markdown 與 HTML）。

export const BYLINE = '許博明老師製作';
export const SHOW_TITLE = '紙燈節';

export const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

/** 行內格式：**粗體**、`代碼`；換行 → <br> */
export function inline(s) {
  return esc(s)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`(.+?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>');
}
const mdCell = (s) => String(s ?? '').replace(/\|/g, '｜').replace(/\n+/g, '<br>');

/**
 * 文件區塊：{ h: 1|2|3, text } 標題；{ p } 段落；{ ul: [...] }；{ ol: [...] }；
 * { table: { head: [...], rows: [[...]], cls, widths } }；{ quote } 引言（要照念的話）；{ note } 小字；{ pagebreak: true }；{ html, md } 自訂
 */
export function toMarkdown(blocks) {
  const out = [];
  for (const b of blocks) {
    if (b.h) out.push(`${'#'.repeat(b.h)} ${b.text}`, '');
    else if (b.p !== undefined) out.push(b.p, '');
    else if (b.ul) out.push(...b.ul.map((x) => `- ${String(x).replace(/\n/g, '\n  ')}`), '');
    else if (b.ol) out.push(...b.ol.map((x, i) => `${i + 1}. ${String(x).replace(/\n/g, '\n   ')}`), '');
    else if (b.quote) out.push(...String(b.quote).split('\n').map((l) => `> ${l}`), '');
    else if (b.note) out.push(`<small>${b.note}</small>`, '');
    else if (b.table) {
      const t = b.table;
      out.push(`| ${t.head.map(mdCell).join(' | ')} |`, `|${t.head.map(() => '---').join('|')}|`);
      for (const r of t.rows) out.push(`| ${r.map(mdCell).join(' | ')} |`);
      out.push('');
    } else if (b.md !== undefined) out.push(b.md, '');
  }
  return out.join('\n').replace(/\n{3,}/g, '\n\n');
}

export function toHtml(blocks) {
  const out = [];
  for (const b of blocks) {
    if (b.h) out.push(`<h${b.h}${b.id ? ` id="${b.id}"` : ''}${b.cls ? ` class="${b.cls}"` : ''}>${inline(b.text)}</h${b.h}>`);
    else if (b.p !== undefined) out.push(`<p${b.cls ? ` class="${b.cls}"` : ''}>${inline(b.p)}</p>`);
    else if (b.ul) out.push(`<ul${b.cls ? ` class="${b.cls}"` : ''}>${b.ul.map((x) => `<li>${inline(x)}</li>`).join('')}</ul>`);
    else if (b.ol) out.push(`<ol${b.cls ? ` class="${b.cls}"` : ''}>${b.ol.map((x) => `<li>${inline(x)}</li>`).join('')}</ol>`);
    else if (b.quote) out.push(`<blockquote>${inline(b.quote)}</blockquote>`);
    else if (b.note) out.push(`<p class="note">${inline(b.note)}</p>`);
    else if (b.pagebreak) out.push('<div class="pb"></div>');
    else if (b.table) {
      const t = b.table;
      const cols = t.widths ? `<colgroup>${t.widths.map((w) => `<col style="width:${w}">`).join('')}</colgroup>` : '';
      out.push(`<table class="${t.cls ?? ''}">${cols}<thead><tr>${t.head.map((h) => `<th>${inline(h)}</th>`).join('')}</tr></thead><tbody>${t.rows.map((r, i) => `<tr${t.rowCls?.[i] ? ` class="${t.rowCls[i]}"` : ''}>${r.map((c) => `<td>${inline(c)}</td>`).join('')}</tr>`).join('')}</tbody></table>`);
    } else if (b.html !== undefined) out.push(b.html);
  }
  return out.join('\n');
}

/** 字型：teacher/fonts 的 Noto Sans TC（SIL OFL 1.1）；PDF 用依實際用字縮小的固定字重（src/fonts.mjs），找不到時退回可變字型。HTML 放在 teacher/html，所以相對路徑是 ../fonts */
export const FONT_CSS = [400, 700, 800, 900].map((w) => `@font-face { font-family: "Noto Sans TC Local"; src: url("../fonts/subset/NotoSansTC-${w}.ttf") format("truetype"), url("../fonts/NotoSansTC-wght.ttf") format("truetype"); font-weight: ${w}; font-style: normal; }`).join('\n');

export const BASE_CSS = `
${FONT_CSS}
:root {
  --ink: #1f1a16; --ink2: #4a3f36; --muted: #6f6359; --line: #b9ab9b; --paper: #fbf7f0; --accent: #7a4e2d; --indigo: #2f4a7a; --soft: #f1e8da;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #fff; color: var(--ink); }
body { font-family: "Noto Sans TC Local", "PingFang TC", "Microsoft JhengHei", sans-serif; font-weight: 400; line-height: 1.55; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
h1, h2, h3 { line-height: 1.3; margin: 0.6em 0 0.35em; font-weight: 800; }
p { margin: 0.3em 0 0.5em; }
strong { font-weight: 800; }
code { font-family: inherit; background: var(--soft); padding: 0 0.25em; border-radius: 3px; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 0.6pt solid var(--line); padding: 3pt 5pt; vertical-align: top; text-align: left; }
th { background: var(--soft); font-weight: 800; }
blockquote { margin: 0.4em 0 0.6em; padding: 0.35em 0.7em; border-left: 3pt solid var(--accent); background: var(--paper); }
.note { color: var(--muted); font-size: 0.86em; }
.pb { break-after: page; height: 0; }
.byline { color: var(--muted); }
`;

export function htmlPage({ title, css = '', body, lang = 'zh-Hant-TW' }) {
  return `<!doctype html>
<html lang="${lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)}</title>
<style>${BASE_CSS}
${css}</style>
</head>
<body>
${body}
</body>
</html>
`;
}

/** 形狀標記（同 app/src/ui/quizcard.ts：1 圓形、2 三角形、3 方形） */
export function shapeSvg(n, cls = 'ico-shape') {
  const shape = n === 1 ? '<circle cx="20" cy="20" r="15"/>'
    : n === 2 ? '<polygon points="20,4 37,35 3,35"/>'
      : '<rect x="5" y="5" width="30" height="30" rx="3"/>';
  return `<svg class="${cls}" viewBox="0 0 40 40" aria-hidden="true"><g fill="currentColor">${shape}</g></svg>`;
}

/** 手指圖示：伸出 n 根手指（同 app/src/ui/quizcard.ts） */
export function handSvg(n, cls = 'ico-hand') {
  const fingers = [];
  for (let i = 0; i < 4; i++) {
    const up = i < n;
    const x = 9 + i * 8;
    fingers.push(up ? `<rect x="${x}" y="3" width="6.6" height="25" rx="3.3"/>` : `<rect x="${x}" y="19" width="6.6" height="10" rx="3.3"/>`);
  }
  return `<svg class="${cls}" viewBox="0 0 48 52" aria-hidden="true"><g fill="currentColor">${fingers.join('')}<rect x="7" y="22" width="34" height="26" rx="10"/><rect x="0" y="27" width="13" height="7" rx="3.5" transform="rotate(-25 6 30)"/></g></svg>`;
}

/** 紙燈小圖（題卡下方八盞燈的同款造型） */
export function lampSvg(lit = false, cls = 'ico-lamp') {
  return `<svg class="${cls}" viewBox="0 0 40 52" aria-hidden="true">
<rect x="13" y="2" width="14" height="6" rx="2" fill="#5a4636"/>
<ellipse cx="20" cy="27" rx="16" ry="18" fill="${lit ? '#f3c76a' : '#fffaf0'}" stroke="#5a4636" stroke-width="1.6"/>
<path d="M20 9 V45 M11 11 Q4 27 11 43 M29 11 Q36 27 29 43" fill="none" stroke="#5a4636" stroke-width="1.3"/>
<rect x="13" y="44" width="14" height="6" rx="2" fill="#5a4636"/></svg>`;
}

/** 數字轉國字（一、二、三） */
export const zh = (n) => '〇一二三四五六七八九十'[n] ?? String(n);
