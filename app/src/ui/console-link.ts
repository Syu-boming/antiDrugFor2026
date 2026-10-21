// 舞台端連結（console-link.js）：放在舞台視窗，讀 window.__engine 的狀態送給教師控制台，並執行控制台送來的操作。
//
// - 狀態來源唯一＝這個視窗的引擎；控制台只顯示快照。
//   壓縮級別與查核點到達時間：引擎有 window.__engineShow（G5 全劇介面）就用引擎的；舊版引擎才由這裡自己記。
//   授課時鐘（從老師上台起算，開幕時 00:30 起跳，老師可 ±30 秒）存在這裡，查核點落差以它換算。
// - 不改引擎、不畫任何東西在舞台上（投影端只顯示乾淨的舞台）。
// - 載入方式：dist/stage.html（console.build.mjs 由 index.html 產生，多一個 <script src="console-link.js">）；
//   Electron 的舞台視窗也載入 stage.html。沒有控制台時它只是安靜地等，不影響演出。
// - 瀏覽器規定聲音要在舞台視窗本身啟用，所以瀏覽器版不接受遠端「準備播放」（Electron 允許自動播放，可以）。
import type { EngineAPI } from '../main';
import type { Cue, CueFile } from '../types/cue';
import { effectiveKeymap, resolveAction } from '../engine/input';
import {
  CLOCK_START_OFFSET, createTransport, zoneFor,
  type CheckpointRecord, type Compression, type CueMeta, type KeyReport, type Msg, type QuizMeta, type StageSnapshot,
} from './console-protocol';

interface LinkHandle { transport: string; sessionId: string; snapshot(): StageSnapshot | null; cues(): CueMeta[] }

declare global {
  interface Window { __consoleLink?: LinkHandle }
}

/** 引擎的全劇介面（engine.ts 的 ShowAPI；只用到這些，欄位不在時自動退回） */
interface ShowLike {
  compression?: () => number;
  setCompression?: (level: number) => number | 'pending';
  checkpoints?: () => { elapsedSec: number | null; suggested: number; list: { cueId: string; actualMin: number | null }[] };
  resetShowClock?: () => void;
}

/** getCues() 在 G5 引擎多出來的欄位（沒有就當沒有） */
interface ResolvedExtra { chapter?: string; skipped?: boolean; droppedLines?: string[]; teacherNote?: string }

function install(): void {
  if (window.__consoleLink) return;
  const params = new URLSearchParams(location.search);
  if (params.get('capture') === '1') return; // 擷取模式不需要控制台
  const transport = createTransport();
  const sessionId = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
  const cueSetName = params.get('cues') ?? 'demo';
  const host: StageSnapshot['host'] = window.theaterHost ? 'electron' : 'browser';
  const canRemoteStart = host === 'electron';

  let cues: CueMeta[] = [];
  let cuesSig = '';
  let cueTitle = '';
  const clock: StageSnapshot['clock'] = { startedAt: null, offsetSec: CLOCK_START_OFFSET, reached: {} };
  /** 只在引擎沒有壓縮介面時使用 */
  let localCompression: Compression = 0;
  let pendingCompression: Compression | null = null;
  let lastKey: KeyReport | null = null;
  let keymap = effectiveKeymap();
  let prev: { mode: string; index: number } | null = null;
  let lastPub = 0;
  let lastSig = '';
  let latest: StageSnapshot | null = null;

  const eng = (): EngineAPI | undefined => window.__engine;
  const show = (): ShowLike | undefined => (window as unknown as { __engineShow?: ShowLike }).__engineShow;
  const engineCompression = (): boolean => typeof show()?.setCompression === 'function';
  const currentCompression = (): Compression => {
    const s = show();
    return (engineCompression() && typeof s?.compression === 'function' ? Math.max(0, Math.min(2, Math.round(s.compression()))) : localCompression) as Compression;
  };

  // ---------------------------------------------------------------- cue 資料

  function cueFile(): CueFile | null {
    const packs: Record<string, unknown> = window.__packs ?? {};
    const f = packs[`cues:${cueSetName}`] ?? Object.entries(packs).find(([k]) => k.startsWith('cues:'))?.[1];
    return (f as CueFile | undefined) ?? null;
  }

  function buildCues(e: EngineAPI): CueMeta[] {
    const resolved = e.getCues() as (ReturnType<EngineAPI['getCues']>[number] & ResolvedExtra)[];
    if (!resolved.length) return [];
    const file = cueFile();
    cueTitle = file?.title ?? '';
    const byId = new Map<string, Cue>((file?.cues ?? []).map((c) => [c.id, c]));
    let lastQuiz: QuizMeta | null = null;
    return resolved.map((r, index) => {
      const c = byId.get(r.id);
      if (c?.quiz) {
        lastQuiz = { qid: c.quiz.qid, number: c.quiz.number, question: c.quiz.question, options: [...c.quiz.options], answer: c.quiz.answer, zone: zoneFor(c.quiz.number) };
      }
      const usesQuiz = r.kind === 'quiz' || r.kind === 'reveal' || r.kind === 'lamp';
      const cp = c?.checkpoint;
      return {
        id: r.id, index, kind: r.kind, title: r.title || c?.title || '',
        chapter: r.chapter ?? '',
        teacherNote: c?.teacherNote ?? r.teacherNote ?? '',
        checkpoint: cp ? { label: cp.label, atMinute: Number(cp.atMinute), escalate: cp.escalate ? { behindSec: cp.escalate.behindSec, level: cp.escalate.level } : null } : null,
        compression: (c?.compression ?? 0) as Compression,
        quiz: usesQuiz || c?.quiz ? lastQuiz : null,
        lamp: c?.lamp ?? null,
        next: r.next, prevStable: r.prevStable, duration: r.duration,
        shortVersion: c?.shortVersion ?? null,
        skippableLines: (c?.lines ?? []).filter((l) => l.skippableWhenBehind).map((l) => l.id),
        skipped: !!r.skipped,
        droppedLines: r.droppedLines ? [...r.droppedLines] : [],
        autoAdvance: !!c?.autoAdvance,
      };
    });
  }

  function refreshCues(e: EngineAPI): void {
    const list = buildCues(e);
    if (!list.length) return;
    const sig = list.map((c) => `${c.id}:${c.duration.toFixed(2)}:${c.skipped ? 1 : 0}:${c.next}`).join('|');
    if (sig === cuesSig) return;
    cues = list;
    cuesSig = sig;
    sendCues();
  }

  function sendCues(): void {
    if (!cues.length) return;
    transport.send({ t: 'cues', sessionId, cueSet: cueSetName, title: cueTitle, cues });
  }

  // ---------------------------------------------------------------- 授課時鐘與查核點

  function classClockAt(dateMs: number): number | null {
    return clock.startedAt == null ? null : (dateMs - clock.startedAt) / 1000 + clock.offsetSec;
  }

  function record(cueId: string, atDateMs: number): void {
    const c = cues.find((x) => x.id === cueId);
    if (!c?.checkpoint || c.checkpoint.atMinute <= 0 || c.index === 0) return;
    const sec = classClockAt(atDateMs);
    if (sec == null) return;
    clock.reached[c.id] = { at: atDateMs, clockSec: Math.round(sec), driftSec: Math.round(sec - c.checkpoint.atMinute * 60) };
  }

  /**
   * 引擎有查核點紀錄時：把引擎的「開演後幾分鐘到達」換成授課時鐘（含 00:30 起跳與老師調整）。
   * 引擎的開演時間是「片頭待機按下一步」那一刻；還沒開始（例如直接用跳到選單）時回傳 null，改用這裡自己記的。
   */
  function engineReached(): Record<string, CheckpointRecord> | null {
    const rep = show()?.checkpoints?.();
    if (!rep || rep.elapsedSec == null) return null;
    const startDate = Date.now() - rep.elapsedSec * 1000;
    const saved = clock.reached;
    clock.reached = {};
    for (const it of rep.list) if (it.actualMin != null) record(it.cueId, startDate + it.actualMin * 60000);
    const out = clock.reached;
    clock.reached = saved;
    return out;
  }

  // ---------------------------------------------------------------- 快照

  function snapshot(e: EngineAPI): StageSnapshot {
    const st = e.getState();
    const level = currentCompression();
    if (pendingCompression !== null && pendingCompression === level) pendingCompression = null;
    const reached = engineReached();
    return {
      sessionId, at: Date.now(), host, canRemoteStart, cueSet: cueSetName,
      engine: {
        mode: st.mode, phase: st.phase, phaseLabel: st.phaseLabel, paused: st.paused, pauseReason: st.pauseReason,
        cueId: st.cueId, cueIndex: st.cueIndex, kind: st.kind, title: st.title, cueTime: st.cueTime, cueDuration: st.cueDuration,
        revealed: st.revealed, quizVisible: st.quizVisible, lampsLit: st.lampsLit, placeholderAudio: st.placeholderAudio,
        missingAudio: st.missingAudio, subtitle: st.subtitle, clock: st.clock, audioState: st.audioState,
        avOffsetMs: st.avOffsetMs, leadInMs: st.leadInMs, quality: st.quality, lock30: st.lock30, playId: st.playId,
        ignoredInputs: st.ignoredInputs, ignoredRepeats: st.ignoredRepeats, blockedKeys: st.blockedKeys, fps: st.fps,
        contextLost: st.contextLost, errors: st.errors.slice(-3), gpu: st.gpu,
      },
      win: {
        focused: document.hasFocus(), visible: document.visibilityState === 'visible',
        dpr: window.devicePixelRatio || 1, w: window.innerWidth, h: window.innerHeight,
        extended: typeof (screen as Screen & { isExtended?: boolean }).isExtended === 'boolean' ? (screen as Screen & { isExtended?: boolean }).isExtended! : null,
      },
      clock: { startedAt: clock.startedAt, offsetSec: clock.offsetSec, reached: reached ?? { ...clock.reached } },
      checkpointSource: reached ? 'engine' : 'link',
      compressionLevel: level, pendingCompression, engineCompression: engineCompression(), lastKey,
    };
  }

  function publish(force = false): void {
    const e = eng();
    if (!e) return;
    const s = snapshot(e);
    latest = s;
    const sig = `${s.engine.mode}|${s.engine.phase}|${s.engine.cueId}|${s.engine.paused}|${s.win.focused}|${s.win.visible}|${s.engine.audioState}|${s.compressionLevel}|${s.pendingCompression}|${Object.keys(s.clock.reached).length}`;
    const now = performance.now();
    const interval = s.engine.mode === 'playing' && !s.engine.paused ? 250 : 1000;
    if (!force && sig === lastSig && now - lastPub < interval) return;
    lastSig = sig;
    lastPub = now;
    transport.send({ t: 'state', s });
  }

  // ---------------------------------------------------------------- 狀態轉換：開幕、查核點（舊版引擎）

  function track(e: EngineAPI): void {
    const st = e.getState();
    if (st.mode !== 'loading' && st.mode !== 'error') refreshCues(e);
    // 開幕（第一次開始播放）時授課時鐘起跳 00:30
    if (clock.startedAt == null && st.mode === 'playing') clock.startedAt = Date.now();
    if (prev && prev.mode === 'playing') {
      const c = cues[prev.index];
      const finished = c && ((st.mode === 'waiting' && st.cueIndex === prev.index)
        || (st.mode === 'playing' && c.autoAdvance && cues[st.cueIndex]?.id === c.next));
      if (finished && !clock.reached[c.id]) record(c.id, Date.now());
    }
    prev = { mode: st.mode, index: st.cueIndex };
  }

  // ---------------------------------------------------------------- 控制台的操作

  function classify(before: ReturnType<EngineAPI['getState']>, after: ReturnType<EngineAPI['getState']>, action: string): string {
    if (after.ignoredInputs > before.ignoredInputs) return 'ignored';
    if (before.paused && !after.paused && after.playId === before.playId) return 'resumed';
    if (!before.paused && after.paused) return 'paused';
    if (before.mode === 'context_lost') return 'recovering';
    if (after.playId !== before.playId || after.cueId !== before.cueId) return action === 'prev' ? 'back' : action === 'replay' ? 'replayed' : 'advanced';
    return 'none';
  }

  function onCmd(m: Extract<Msg, { t: 'cmd' }>): void {
    const e = eng();
    const ack = (ok: boolean, effect: string): void => {
      transport.send({ t: 'ack', seq: m.seq, consoleId: m.consoleId, ok, effect, phase: e?.getState().phase ?? 'loading' });
    };
    if (!e) { ack(false, 'not-ready'); return; }
    const before = e.getState();
    if (m.action === 'start' || (m.action === 'next' && before.mode === 'preparing')) {
      if (before.mode !== 'preparing') { ack(false, 'not-preparing'); return; }
      if (!canRemoteStart) { ack(false, 'need-gesture'); return; }
      void e.start().then(() => publish(true));
      ack(true, 'starting');
      publish(true);
      return;
    }
    switch (m.action) {
      case 'next': e.next(); break;
      case 'prev': e.prev(); break;
      case 'pause': e.pause(); break;
      case 'replay': e.replay(); break;
      case 'goto': if (!m.id || !e.gotoCue(m.id, { mode: 'before' })) { ack(false, 'goto-failed'); return; } break;
      default: ack(false, 'unknown'); return;
    }
    const after = e.getState();
    ack(true, m.action === 'goto' ? 'jumped' : classify(before, after, m.action));
    track(e);
    publish(true);
  }

  transport.onMessage((m) => {
    switch (m.t) {
      case 'hello': if (m.from === 'console') { sendCues(); publish(true); } break;
      case 'cmd': onCmd(m); break;
      case 'clock':
        if (m.op === 'start') { clock.startedAt = Date.now(); clock.offsetSec = m.sec ?? 0; }
        else if (m.op === 'reset') { clock.startedAt = null; clock.offsetSec = CLOCK_START_OFFSET; clock.reached = {}; show()?.resetShowClock?.(); }
        else if (m.op === 'adjust') clock.offsetSec += m.sec ?? 0;
        else if (m.op === 'restore' && clock.startedAt == null && m.startedAt != null) { clock.startedAt = m.startedAt; clock.offsetSec = m.offsetSec ?? clock.offsetSec; }
        publish(true);
        break;
      case 'compression': {
        const s = show();
        if (engineCompression() && s?.setCompression) {
          const r = s.setCompression(m.level);
          pendingCompression = r === 'pending' ? m.level : null;
        } else localCompression = m.level;
        const e = eng();
        if (e) refreshCues(e);
        publish(true);
        break;
      }
      case 'host':
        // Electron 回報顯示器縮放改變：讓舞台依新的 devicePixelRatio 重設解析度（main.ts 也會自己偵測，這裡是保險）
        if (m.event === 'display-metrics' || m.event === 'layout') window.dispatchEvent(new Event('resize'));
        break;
      default: break;
    }
  });

  // 舞台視窗收到的按鍵也回報給控制台（只讀，不攔截；動作由舞台自己的 InputController 處理）
  window.addEventListener('keydown', (ev) => {
    lastKey = { key: ev.key, code: ev.code, repeat: ev.repeat, action: resolveAction(ev, keymap), window: 'stage', at: Date.now() };
    transport.send({ t: 'key', k: lastKey });
    setTimeout(() => publish(true), 30);
  }, { capture: true, passive: true });
  window.addEventListener('storage', () => { keymap = effectiveKeymap(); });
  window.addEventListener('focus', () => publish(true));
  window.addEventListener('blur', () => publish(true));
  document.addEventListener('visibilitychange', () => setTimeout(() => publish(true), 20));

  // 舞台視窗移到不同縮放的螢幕：main.ts 用 matchMedia 偵測；有些情況（只有縮放改、視窗大小沒變）不會觸發，
  // 這裡每 100 ms 比對一次 devicePixelRatio，變了就送 resize，讓引擎依新的比例重設繪圖解析度。
  let lastDpr = window.devicePixelRatio || 1;
  setInterval(() => {
    const dpr = window.devicePixelRatio || 1;
    if (dpr !== lastDpr) { lastDpr = dpr; window.dispatchEvent(new Event('resize')); }
    const e = eng();
    if (!e) return;
    try { track(e); publish(); } catch (err) { console.error('[console-link]', err); }
  }, 100);

  window.__consoleLink = { transport: transport.kind, sessionId, snapshot: () => latest, cues: () => cues };
  transport.send({ t: 'hello', from: 'stage', id: sessionId });
}

try { install(); } catch (err) { console.error('[console-link] 無法啟動（演出不受影響）', err); }
