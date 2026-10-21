// 教師控制台 ↔ 舞台視窗的訊息格式、傳輸與顯示用的純函式（v1.2 第 19.4 節）。
//
// 狀態來源唯一：舞台視窗裡的引擎（window.__engine）。舞台端的連結（console-link.ts）定時送出狀態快照，
// 控制台只顯示快照、送出操作要求（下一步、上一步、暫停…），不自己推算演出狀態。授課時鐘與查核點紀錄也放在舞台端。
//
// 傳輸：
//   Electron：preload 提供 window.theaterHost（IPC），主程序把訊息轉給另一個視窗。
//   瀏覽器：BroadcastChannel（同一個瀏覽器設定檔、同來源；file:// 在 Chrome／Edge 也可以）。
//   都沒有時退回 localStorage 的 storage 事件。
// 只在本機兩個視窗之間傳遞，不連網、不寫檔、不蒐集任何資料。

export const CHANNEL = 'antidrug-theater-console/1';

export type Role = 'stage' | 'console' | 'keytest';
export type CmdAction = 'next' | 'prev' | 'pause' | 'replay' | 'start' | 'goto';
export type Compression = 0 | 1 | 2;

export interface QuizMeta { qid: string; number: number; question: string; options: string[]; answer: number; zone: string }

/** 控制台需要的 cue 資料（由舞台端從 cue 檔與引擎解析結果組合） */
export interface CueMeta {
  id: string;
  index: number;
  kind: string;
  title: string;
  /** 章節名（全劇 cue 集的段落；跳到選單分組用） */
  chapter: string;
  teacherNote: string;
  /** 查核點；escalate＝落後多少秒時建議啟用幾級壓縮（cue 檔有寫就以它為準） */
  checkpoint: { label: string; atMinute: number; escalate: { behindSec: number; level: 1 | 2 } | null } | null;
  compression: Compression;
  /** 本 cue 的題目；reveal、lamp 沒寫時沿用前一個 quiz */
  quiz: QuizMeta | null;
  lamp: number | null;
  next: string | null;
  prevStable: string | null;
  duration: number;
  shortVersion: string | null;
  skippableLines: string[];
  /** 目前的壓縮級別會整段略過 */
  skipped: boolean;
  /** 目前的壓縮級別略過的句子 */
  droppedLines: string[];
  autoAdvance: boolean;
}

export interface EngineSnap {
  mode: string; phase: string; phaseLabel: string; paused: boolean; pauseReason: string | null;
  cueId: string | null; cueIndex: number; kind: string | null; title: string; cueTime: number; cueDuration: number;
  revealed: boolean; quizVisible: boolean; lampsLit: number[]; placeholderAudio: boolean; missingAudio: string[];
  subtitle: string; clock: string; audioState: string; avOffsetMs: number; leadInMs: number; quality: string; lock30: boolean;
  playId: number; ignoredInputs: number; ignoredRepeats: number; blockedKeys: number; fps: number; contextLost: boolean;
  errors: string[]; gpu: string;
}

export interface KeyReport { key: string; code: string; repeat: boolean; action: string | null; window: Role; at: number }

export interface CheckpointRecord { at: number; clockSec: number; driftSec: number }

export interface StageSnapshot {
  sessionId: string;
  at: number;
  host: 'electron' | 'browser';
  /** 能否由控制台遠端按「準備播放」（Electron 允許自動播放；瀏覽器要在舞台視窗本身操作一次才能啟用聲音） */
  canRemoteStart: boolean;
  cueSet: string;
  engine: EngineSnap;
  win: { focused: boolean; visible: boolean; dpr: number; w: number; h: number; extended: boolean | null };
  /** 授課時鐘：startedAt＝開幕那一刻（Date.now 毫秒）；offsetSec＝起跳值與老師調整 */
  clock: { startedAt: number | null; offsetSec: number; reached: Record<string, CheckpointRecord> };
  /** 查核點到達時間的來源：engine＝引擎的紀錄（window.__engineShow），link＝舞台端連結自己記（舊版引擎） */
  checkpointSource: 'engine' | 'link';
  compressionLevel: Compression;
  /** 播放中改了壓縮級別：這段播完才套用 */
  pendingCompression: Compression | null;
  /** 引擎是否支援壓縮級別（window.__engineShow.setCompression） */
  engineCompression: boolean;
  lastKey: KeyReport | null;
}

export interface HostLayout { mode: 'single' | 'dual' | 'dual-test'; reason: string; stageDisplay?: number; consoleDisplay?: number; displays?: number }

export type Msg =
  | { t: 'hello'; from: Role; id: string }
  | { t: 'state'; s: StageSnapshot }
  | { t: 'cues'; sessionId: string; cueSet: string; title: string; cues: CueMeta[] }
  | { t: 'cmd'; seq: number; action: CmdAction; id?: string; from: Role; consoleId: string }
  | { t: 'ack'; seq: number; consoleId: string; ok: boolean; effect: string; phase: string }
  | { t: 'clock'; op: 'start' | 'reset' | 'adjust' | 'restore'; sec?: number; startedAt?: number | null; offsetSec?: number }
  | { t: 'compression'; level: Compression }
  | { t: 'key'; k: KeyReport }
  | { t: 'host'; event: 'display-metrics' | 'layout'; layout?: HostLayout };

/** Electron preload 提供的介面（app/electron/preload.js） */
export interface TheaterHost {
  kind: 'electron';
  send(m: unknown): void;
  on(cb: (m: unknown) => void): () => void;
  info(): Promise<{ layout: HostLayout; versions: Record<string, string>; role: string }>;
}

declare global {
  interface Window { theaterHost?: TheaterHost }
}

export interface Transport {
  kind: 'ipc' | 'broadcast' | 'storage' | 'none';
  send(m: Msg): void;
  onMessage(cb: (m: Msg) => void): void;
  close(): void;
}

export function createTransport(): Transport {
  const listeners: ((m: Msg) => void)[] = [];
  const emit = (m: unknown): void => {
    if (!m || typeof m !== 'object' || typeof (m as Msg).t !== 'string') return;
    for (const l of listeners) { try { l(m as Msg); } catch (err) { console.error('[console]', err); } }
  };
  const host = window.theaterHost;
  if (host && typeof host.send === 'function' && typeof host.on === 'function') {
    const off = host.on(emit);
    return { kind: 'ipc', send: (m) => host.send(m), onMessage: (cb) => { listeners.push(cb); }, close: () => off() };
  }
  try {
    const bc = new BroadcastChannel(CHANNEL);
    bc.onmessage = (e) => emit(e.data);
    return { kind: 'broadcast', send: (m) => bc.postMessage(m), onMessage: (cb) => { listeners.push(cb); }, close: () => bc.close() };
  } catch { /* 沒有 BroadcastChannel：試 storage 事件 */ }
  try {
    const key = `${CHANNEL}:msg`;
    localStorage.setItem(`${key}:probe`, '1');
    localStorage.removeItem(`${key}:probe`);
    const onStorage = (e: StorageEvent): void => {
      if (e.key !== key || !e.newValue) return;
      try { emit((JSON.parse(e.newValue) as { m: Msg }).m); } catch { /* 忽略 */ }
    };
    window.addEventListener('storage', onStorage);
    return {
      kind: 'storage',
      send: (m) => { try { localStorage.setItem(key, JSON.stringify({ m, n: Math.random() })); } catch { /* 忽略 */ } },
      onMessage: (cb) => { listeners.push(cb); },
      close: () => window.removeEventListener('storage', onStorage),
    };
  } catch { /* 都不能用 */ }
  return { kind: 'none', send: () => undefined, onMessage: () => undefined, close: () => undefined };
}

export const TRANSPORT_LABEL: Record<Transport['kind'], string> = {
  ipc: 'Electron IPC', broadcast: 'BroadcastChannel', storage: '本機儲存事件', none: '無法連線',
};

// ---------------------------------------------------------------- 顯示用的純函式

/** Q1–Q8 輪區 A→B→C→D 各兩次 */
export function zoneFor(n: number): string {
  return 'ABCD'[((Math.max(1, Math.round(n)) - 1) % 4 + 4) % 4];
}

/** 秒 → m:ss（負數取絕對值） */
export function mmss(sec: number): string {
  const s = Math.round(Math.abs(sec));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

/** 授課時鐘 mm:ss（兩位數分鐘） */
export function clockText(sec: number): string {
  const s = Math.max(0, Math.floor(sec));
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
}

/** 落差文字：正＝落後、負＝超前；30 秒內算準時 */
export function driftText(driftSec: number): string {
  if (Math.abs(driftSec) < 30) return `準時（${driftSec >= 0 ? '+' : '−'}${mmss(driftSec)}）`;
  return driftSec > 0 ? `落後 ${mmss(driftSec)}` : `超前 ${mmss(driftSec)}`;
}

/** 授課時鐘目前秒數 */
export function classClockSec(clock: StageSnapshot['clock'] | null | undefined, now = Date.now()): number | null {
  if (!clock || clock.startedAt == null) return null;
  return (now - clock.startedAt) / 1000 + clock.offsetSec;
}

/** 開幕時授課時鐘的起跳值：時長估算 v03 第 4 節，課前問候 00:00–00:30，開場從 00:30 起 */
export const CLOCK_START_OFFSET = 30;

/**
 * 時間應變觸發點（時長估算_v03.md 第 5 節）：查核點落後達門檻就建議啟用壓縮級別。
 * 以 cue 編號對應（查核點欄位在 cue 檔），標籤含題號時也認得。
 */
export const COMPRESSION_RULES: { cue: string; label: RegExp; behindSec: number; level: Compression; text: string }[] = [
  { cue: 'a2_c011', label: /Q3/, behindSec: 90, level: 1, text: 'Q3 查核點落後 ≥ 1:30 → 啟用 1 級，之後一直維持' },
  { cue: 'a4_c011', label: /Q6/, behindSec: 120, level: 1, text: 'Q6 查核點落後 ≥ 2:00 → 啟用 1 級（若還沒啟用）' },
  { cue: 'a6_c005', label: /Q8/, behindSec: 150, level: 2, text: 'Q8 查核點落後 ≥ 2:30 → 啟用 2 級（1 級一併啟用）' },
];

/** 查核點的觸發門檻：cue 檔的 checkpoint.escalate 優先，沒寫才用上表 */
export function ruleFor(cue: CueMeta): { behindSec: number; level: Compression; text: string } | null {
  const esc = cue.checkpoint?.escalate;
  if (esc) {
    const r = COMPRESSION_RULES.find((x) => x.cue === cue.id);
    return { behindSec: esc.behindSec, level: esc.level, text: r?.text ?? `${cue.checkpoint!.label}落後 ≥ ${mmss(esc.behindSec)} → 啟用 ${esc.level} 級` };
  }
  return COMPRESSION_RULES.find((r) => r.cue === cue.id) ?? (cue.checkpoint ? COMPRESSION_RULES.find((r) => r.label.test(cue.checkpoint!.label)) ?? null : null);
}

/** 依已到達的查核點，建議的壓縮級別與理由 */
export function compressionAdvice(cues: CueMeta[], reached: Record<string, CheckpointRecord>): { level: Compression; reason: string } {
  let level: Compression = 0;
  let reason = '';
  for (const c of cues) {
    const r = ruleFor(c);
    const rec = reached[c.id];
    if (!r || !rec) continue;
    if (rec.driftSec >= r.behindSec && r.level >= level) { level = r.level; reason = `${r.text}（實際落後 ${mmss(rec.driftSec)}）`; }
  }
  return { level, reason };
}

export const COMPRESSION_LABEL: Record<Compression, string> = {
  0: '0 級（必保，不略過）', 1: '1 級（落後時略過標示的句子或鏡頭）', 2: '2 級（落後較多時改短版）',
};

/** 各級別教師端的做法（時長估算_v03.md 第 5 節） */
export const COMPRESSION_TEACHER: Record<Compression, string> = {
  0: '照預設進行；超前時只讓更多學生說理由，不加題。',
  1: '學生說理由縮成一句；找找看縮成 15 秒；可選補充不講。',
  2: '1 級全部照做；教師結語縮成 30 秒；四季、三張大圖、謝幕改短版。',
};

export const PAUSE_REASON: Record<string, string> = {
  teacher: '老師按了暫停', hidden: '舞台視窗被隱藏或縮小', freeze: '系統凍結了頁面', audio: '系統停掉了聲音', sleep: '系統休眠後喚醒',
};

/** 一個 cue 的簡短描述（「下一步：…」用） */
export function describeCue(c: CueMeta | undefined | null): string {
  if (!c) return '（沒有下一段）';
  const t = c.title || c.id;
  switch (c.kind) {
    case 'quiz': return c.quiz ? `出題 ${c.quiz.qid}` : t;
    case 'reveal': return c.quiz ? `揭曉答案 ${c.quiz.qid}` : t;
    case 'lamp': return `點燈（第 ${c.lamp ?? c.quiz?.number ?? '?'} 盞）`;
    case 'scene': return `播放〈${t}〉`;
    default: return t;
  }
}

export interface NextStep { main: string; sub: string; tone: 'go' | 'play' | 'wait' | 'warn' | 'idle' }

/** 下一步預告：依舞台快照與 cue 資料（純函式） */
export function nextStep(s: StageSnapshot | null, byId: Map<string, CueMeta>, connected: boolean): NextStep {
  if (!s || !connected) return { main: '舞台未連線', sub: '開啟舞台視窗後會自動連線；按鍵暫時不會送到劇場。', tone: 'warn' };
  const e = s.engine;
  const cur = e.cueId ? byId.get(e.cueId) : undefined;
  const nxt = cur?.next ? byId.get(cur.next) : undefined;
  switch (e.mode) {
    case 'loading': return { main: '載入中…', sub: '素材與音檔載入中，請稍候。', tone: 'idle' };
    case 'error': return { main: '舞台無法開始', sub: e.errors[e.errors.length - 1] ?? '請看投影畫面上的訊息。', tone: 'warn' };
    case 'preparing':
      return s.canRemoteStart
        ? { main: '下一步：準備播放', sub: '按簡報筆「下一步」或下方「準備播放」：啟用聲音，停在署名卡等待。', tone: 'go' }
        : { main: '請在投影畫面上按「準備播放」', sub: '瀏覽器規定聲音要在舞台視窗本身啟用：把滑鼠移到投影畫面點一下按鈕（或在舞台視窗按一下鍵盤）。', tone: 'warn' };
    case 'context_lost': return { main: '下一步：重新建立畫面', sub: '顯示卡中斷（可能是投影機切換），聲音已停止。按一次「下一步」重建，回到目前的穩定節點。', tone: 'warn' };
    default: break;
  }
  if (e.paused) return { main: '暫停中', sub: `${PAUSE_REASON[e.pauseReason ?? ''] ?? '已暫停'}。按「下一步」或黑屏鍵繼續，不會跳段。`, tone: 'warn' };
  const quizTxt = (q: QuizMeta | null | undefined): string => (q ? `${q.qid} 正解 ${q.answer}（指定 ${q.zone} 區）` : '');
  switch (e.phase) {
    case 'playing': case 'quiz_playing': case 'reveal_playing': {
      const after = cur?.autoAdvance && nxt ? `播完會自動接〈${nxt.title || nxt.id}〉。` : `播完後停住；接著按下一步：${describeCue(nxt)}。`;
      return { main: `播放中：${cur?.title || e.title}`, sub: `${after}播放中按下一步會被忽略（不會跳段）。`, tone: 'play' };
    }
    case 'title_idle': return { main: `下一步：${nxt?.title || '開幕'}`, sub: '署名卡待機中。學生坐定後按下一步開演（授課時鐘會從 00:30 起跳）。', tone: 'go' };
    case 'story_waiting': return { main: `下一步：${describeCue(nxt)}`, sub: nxt?.kind === 'quiz' ? `下一題 ${quizTxt(nxt.quiz)}` : (nxt?.teacherNote ? `接下來：${firstSentence(nxt.teacherNote)}` : ''), tone: 'go' };
    case 'quiz_shown': return { main: '下一步：揭曉答案', sub: `${quizTxt(cur?.quiz)}。出題後沒有倒數，等全班比完、點人說理由再按。`, tone: 'go' };
    case 'reveal_waiting':
      return nxt?.kind === 'lamp'
        ? { main: `下一步：點燈（第 ${nxt.lamp ?? nxt.quiz?.number ?? '?'} 盞）`, sub: '說「大家一起，捧燈手——」說完就按；燈亮後做安靜手勢。', tone: 'go' }
        : { main: `下一步：收起題卡，${describeCue(nxt)}`, sub: '回饋完停住，留出發獎時間。', tone: 'go' };
    case 'final_waiting': return { main: '下一步：關幕，顯示片尾署名卡', sub: '一次按鍵完成：布幕合攏後停在署名卡。', tone: 'go' };
    case 'ended': return { main: '演出結束：保持片尾署名卡', sub: '按下一步不會再動作。接著教師結語。', tone: 'idle' };
    default: return { main: e.phaseLabel || e.phase, sub: '', tone: 'idle' };
  }
}

export function firstSentence(t: string): string {
  const m = /^(.{0,60}?[。！？；]|.{0,60})/.exec(t.replace(/\s+/g, ' ').trim());
  return m ? m[1] : t;
}

/** 目前要顯示的題目：題目 cue（含揭答、點燈沿用）；劇情等待時預告下一題 */
export function quizContext(s: StageSnapshot | null, byId: Map<string, CueMeta>): { quiz: QuizMeta; upcoming: boolean } | null {
  if (!s?.engine.cueId) return null;
  const cur = byId.get(s.engine.cueId);
  if (!cur) return null;
  if ((cur.kind === 'quiz' || cur.kind === 'reveal' || cur.kind === 'lamp') && cur.quiz) return { quiz: cur.quiz, upcoming: false };
  const nxt = cur.next ? byId.get(cur.next) : undefined;
  if (nxt?.kind === 'quiz' && nxt.quiz && s.engine.mode === 'waiting') return { quiz: nxt.quiz, upcoming: true };
  return null;
}
