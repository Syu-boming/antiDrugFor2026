// 給老師看的文字整理：八題回饋不提前講劇情、教師背景拿掉製作備註，以及共用的人力配置、備援影片說法。
// 八題定稿（script/八題_v03.md）由主線維護；這裡只在產生教師資料時改寫，不改定稿檔。
// 定稿之後若已同步成新寫法，下面的改寫自動不生效（找不到舊句子就照定稿原文）。

/** 人力配置（講稿、教案、觀課導覽單三份一字不差，checks.mjs 會比對） */
export const STAFF_LINE = '主講 1 名、協助教師 1 名（記錄區、排、座位與發獎），技術協助選配；最低配置為主講加導師';

// ───────────────────────────── 八題「對全班說」：不提前講還沒演的劇情 ─────────────────────────────

/** 舊句子 → 新句子（G6 校長代理意見 2）。from 找不到就不動 */
const SAY_FIX = {
  // Q6 揭答在 a4_c010，小晴和小宇回校門找警衛與老師在 a4_c012 才演：改成預告
  Q6: [{ from: '回到安全的地方找大人，像小晴和小宇回到校門找警衛伯伯和老師。', to: '回到安全的地方找大人。等一下看看小晴和小宇怎麼做。' }],
  // Q7 揭答在 a5_c003，小宇撥 119 在 a5_c005–c006 才演：刪掉「就像小宇……」整句（照念句約 10 秒，回饋預算 12 秒內）
  Q7: [{ from: /就像小宇[^。]*。/, to: '' }],
};

/** 明確會洩漏後面劇情的說法（checks.mjs 用；回饋與「若不少人選了」都不能出現） */
export const SPOILERS = {
  Q6: ['回到校門找警衛', '像小晴和小宇回到校門'],
  Q7: ['就像小宇', '校門裡撥 119', '先叫陳伯伯'],
};
/** 任何一題都不用「（就）像小晴／小宇……」引用劇情當答案 */
export const SPOILER_RE = /(就?像)(小晴|小宇|品安|阿樂叔叔)/;

// ───────────────────────────── 教師背景：拿掉製作備註 ─────────────────────────────

/** 依序套用；每條都是「版本沿革、檔名、程式路徑、規劃書章節號」改成老師看得懂的說法 */
const BG_FIX = [
  // Q2：版本沿革
  [/v0\d 起選項 1 不再用「逗大家開心」，避免把受影響的樣子說成娛樂；回饋也不要拿叔叔的動作開玩笑/, '選項 1 的說法不把受影響的樣子當成表演或娛樂；回饋也不要拿叔叔的動作開玩笑', '版本沿革改成說明'],
  // Q4：版本沿革
  [/；v0\d 選項 2 的寫法本身像在提供試用的份量與停止時機，v0\d 已改掉，教師回饋也不要再提那種說法。/, '。', '刪掉版本沿革'],
  // Q7：檔名
  [/（見 `?角色表_v\d+\.md`? ?[^）]*）/, '', '刪掉檔名'],
  // Q7：製作核對紀錄
  [/劇本 (a\d_c\d{3}) 的對白依此核對；該頁沒有列出執勤人員的固定受理用語，劇中問句是一般說法。/, '劇中 $1 的報案對話依這些原則撰寫。', '製作核對紀錄改成一句說明'],
  // Q8：規劃書章節號
  [/後擱置（v1\.\d 第 [\d.]+ 節）。/, '後擱置，一律依學校兒少保護通報流程辦理。', '規劃書章節號改成「依學校兒少保護通報流程」'],
  // 製作規則的條號（老師沒有那份清單）
  [/（安全界線第 \d+ 條）/g, '', '刪掉製作規則條號'],
  // 台詞編號 → cue 編號（講稿與控制台只用 cue 編號）
  [/（(a\d_c\d{3})_\d{2}）/g, '（$1）', '台詞編號改成 cue 編號'],
  // 其他規劃書章節號（萬一新增）
  [/（v1\.\d 第 [\d.]+ 節）/g, '', '刪掉規劃書章節號'],
];

function fixText(s, rules, log, where) {
  let out = s;
  for (const [re, to, label] of rules) {
    const next = out.replace(re, to);
    if (next !== out) { log.push(`${where}：${label}`); out = next; }
  }
  return out;
}

/**
 * 八題資料 → 給老師看的版本（不改題卡文字、揭答句、正解、指定區；那些另外和 cue 比對）。
 * @returns {{ eight, changes: string[] }}
 */
export function teacherFacingEight(eight) {
  const changes = [];
  const out = {};
  for (const [qid, e] of Object.entries(eight)) {
    const q = { ...e, ifMany: e.ifMany.map((x) => ({ ...x })), background: [...e.background] };
    if (q.say) {
      let s = q.say;
      for (const f of SAY_FIX[qid] ?? []) {
        const next = s.replace(f.from, f.to);
        if (next !== s) { changes.push(`${qid} 對全班說：改成不提前講劇情`); s = next; }
      }
      q.say = s.replace(/\s+$/, '');
    }
    q.background = q.background.map((b, i) => fixText(b, BG_FIX, changes, `${qid} 教師背景 ${i + 1}`)).filter((b) => b.trim());
    out[qid] = q;
  }
  return { eight: out, changes };
}

/** 照念長度（秒）：中文每字、每個數字各算一拍，每秒 4 字（principal.md 的估法） */
export function speechSeconds(text) {
  const n = (String(text).match(/[一-鿿0-9A-Za-z]/g) ?? []).length;
  return { chars: n, sec: n / 4 };
}

/** 製作備註的樣子（checks.mjs 掃所有給老師、學校、學生的輸出） */
export const PRODUCTION_NOTE_PATTERNS = [
  { name: '版本沿革（v01、v02…）', re: /(^|[^A-Za-z0-9])v0\d(?![0-9])/ },
  { name: '規劃書版本（v1.x）', re: /(^|[^A-Za-z0-9])v1\.\d/ },
  { name: '規劃書章節號（第 x.x 節）', re: /第 ?\d+\.\d+ ?節/ },
  { name: '製作規則條號（安全界線第 N 條）', re: /安全界線第/ },
  { name: '製作文件名（時長估算、角色表、八題定稿檔）', re: /時長估算|角色表_|八題_v/ },
  { name: '程式或專案路徑', re: /(^|[^A-Za-z])(app|tools|script|review|assets|audio|teacher)\/[A-Za-z0-9_]/ },
  { name: '程式檔名（.mjs .ts .py .json .md）', re: /[A-Za-z0-9_一-鿿]\.(mjs|ts|py|json|md)(?![A-Za-z])/ },
  { name: '台詞編號（a1_c001_01）', re: /a\d_c\d{3}_\d{2}/ },
];

// ───────────────────────────── 備援影片的說法 ─────────────────────────────

/**
 * 依 data.mjs backupVideoStatus() 的結果產生說法。還沒產生（或缺檔）時保留「暫定」。
 * label：退路名稱；inline：一句話（導覽單、教案）；how：用法（講稿、故障卡）；step：故障卡退路方塊的小字。
 */
export function backupVideoText(bv) {
  if (!bv?.ready) {
    return {
      ready: false,
      label: '備援影片（暫定）',
      inline: '分幕備援影片（暫定）',
      step: '分幕影片，製作中',
      short: '分幕影片還在製作，完成後放在 backup_video 資料夾；在那之前跳過這一層，改用紙本題卡＋講稿。',
      how: '分幕影片還在製作，完成後會放在演出資料夾的 backup_video 資料夾（每段一檔、每個 cue 一章）；在那之前跳過這一層，直接用紙本題卡＋講稿。',
    };
  }
  const range = `${bv.first}–${bv.last}`;
  return {
    ready: true,
    label: '備援影片',
    inline: `分幕備援影片（backup_video 資料夾 ${range}，每段一檔、每個 cue 一章；題卡處按空白鍵暫停作答）`,
    step: `backup_video 資料夾`,
    short: `用 Windows「媒體播放器」依序開 ${bv.first} → … → ${bv.last}，全螢幕；Win＋P 選「同步顯示」。出題停 3 秒時按**筆電空白鍵**暫停，揭答說完再按空白鍵繼續${bv.readme ? '；暫停點見 README.txt' : ''}。`,
    range,
    how: `依序播放 backup_video 資料夾的 ${bv.first} → … → ${bv.last}（每段一檔、每個 cue 一章），用 Windows 內建「媒體播放器」全螢幕播放，Win＋P 選「同步顯示」。影片不會停下來等老師：每題的出題畫面會停 3 秒，這時按**筆電的空白鍵**暫停，全班比完、揭答與回饋說完再按空白鍵繼續；規則說明、找找看、練習等要說話的地方也先按空白鍵暫停。簡報筆的翻頁鍵在播放器裡不一定有效。${bv.readme ? '每段在哪裡暫停，見 backup_video 資料夾的 README.txt。' : ''}`,
  };
}
