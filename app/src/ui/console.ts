// 教師控制台（簡報者檢視，v1.2 第 19.4 節）：筆電端以深色大字顯示下一步預告、講稿重點、本題正解與指定區、
// 授課時鐘與查核點落差、壓縮級別、fps 與音訊狀態。投影端（舞台視窗）只顯示乾淨的舞台。
//
// - 狀態來源唯一：舞台視窗的引擎。這裡只顯示舞台端連結（console-link.ts）送來的快照，按鍵與按鈕都轉成操作要求送過去。
// - 按鍵路由：鍵盤事件只會送到有焦點的視窗。控制台有焦點 → 這裡的 InputController 轉送；舞台有焦點 → 舞台自己處理。
//   兩個都沒有焦點時以大字提示「請點一下控制台」。
// - 同步顯示（只有一個畫面）時自動改走單一舞台視窗（瀏覽器版；Electron 版由主程序決定開幾個視窗）。
// - 暫停規則：舞台視窗失去焦點只在這裡提示；頁面隱藏或系統休眠才由引擎暫停。控制台本身被隱藏不影響演出。
// - 不蒐集資料、不用攝影機麥克風、不連網。
import { ACTION_LABEL, InputController, keyLabel, type Action } from '../engine/input';
import {
  COMPRESSION_LABEL, COMPRESSION_TEACHER, TRANSPORT_LABEL, classClockSec, clockText, compressionAdvice, createTransport,
  describeCue, driftText, mmss, nextStep, quizContext,
  type CmdAction, type Compression, type CueMeta, type HostLayout, type KeyReport, type Msg, type StageSnapshot,
} from './console-protocol';
import { KeyTestPanel } from './console-keytest';

const STALE_MS = 3000;
const FOCUS_GRACE_MS = 600;

const EFFECT_TEXT: Record<string, string> = {
  advanced: '已推進', back: '已回到上一個穩定節點', replayed: '重播目前段落', paused: '已暫停', resumed: '已繼續',
  ignored: '播放中或剛停住，這一下已忽略（不會跳段）', none: '沒有變化', starting: '準備播放中（啟用聲音）',
  'need-gesture': '瀏覽器規定：請在投影畫面上按「準備播放」', 'not-ready': '舞台還在載入', 'not-preparing': '已經準備好了',
  'confirm-vo': '缺配音檔（舞台畫面列出缺幾句）：確定仍要開演，請再按一次「準備播放」',
  jumped: '已跳到該段之前的停住畫面', 'goto-failed': '無法跳到這一段', recovering: '重新建立畫面中', unknown: '無法執行',
};

const AUDIO_TEXT: Record<string, string> = { running: '正常', suspended: '已暫停', closed: '已關閉', interrupted: '被系統中斷', none: '無法使用' };
const CLOCK_TEXT: Record<string, string> = { audio: '音訊時鐘', performance: '系統時鐘（聲音可能沒出來）', virtual: '虛擬時鐘（擷取）' };

function boot(): void {
  const rootEl = document.getElementById('console-root');
  if (!rootEl) return;
  const root: HTMLElement = rootEl;
  const params = new URLSearchParams(location.search);
  const isElectron = !!window.theaterHost;
  const consoleId = Math.random().toString(36).slice(2, 10);
  const transport = createTransport();
  document.body.classList.toggle('electron', isElectron);

  root.innerHTML = `
    <header class="c-top">
      <div class="c-brand">教師控制台<small>反毒剪紙劇場｜許博明老師製作</small></div>
      <div class="c-pill" data-el="link">舞台：未連線</div>
      <div class="c-pill" data-el="focus">焦點：—</div>
      <div class="c-clockbox"><small>授課時鐘</small><b data-el="clock">--:--</b></div>
    </header>
    <div class="c-banner c-focus-warn" data-el="focusWarn" hidden>
      <b>請點一下控制台</b>
      <span>兩個視窗都沒有焦點：簡報筆的按鍵現在不會送到劇場。點一下這個視窗任何地方即可。</span>
    </div>
    <div class="c-banner c-single" data-el="single" hidden>
      <b data-el="singleTitle">只有一個畫面</b>
      <span data-el="singleText"></span>
      <span class="c-banner-btns"><button data-act="single-go">立刻改用單一舞台視窗</button><button data-act="single-stay">留在控制台</button></span>
    </div>
    <main class="c-grid">
      <div class="c-col c-left">
        <section class="card c-next" data-el="nextCard">
          <div class="lbl">下一步</div>
          <div class="next-main" data-el="nextMain">—</div>
          <div class="next-sub" data-el="nextSub"></div>
          <div class="c-now"><span class="c-phase" data-el="phase">—</span><span class="c-cue" data-el="cue"></span></div>
          <div class="c-progress"><div data-el="bar"></div></div>
          <div class="c-meta"><span data-el="time"></span><span data-el="prev"></span></div>
        </section>
        <section class="card c-note">
          <div class="lbl">講稿重點 <span class="lbl-id" data-el="noteCue"></span></div>
          <div class="note" data-el="note">—</div>
          <div class="lbl sm">接下來 <span class="lbl-id" data-el="noteNextCue"></span></div>
          <div class="note-next" data-el="noteNext">—</div>
          <div class="lbl sm">目前字幕</div>
          <div class="subline" data-el="sub">—</div>
        </section>
      </div>
      <div class="c-col c-right">
        <section class="card c-quiz" data-el="quizCard">
          <div class="lbl" data-el="quizLbl">本題</div>
          <div class="quiz-big">
            <div><small>正解</small><b data-el="ans">—</b></div>
            <div class="quiz-zone"><small>指定區</small><b data-el="zone">—</b></div>
          </div>
          <div class="quiz-q" data-el="q"></div>
          <ol class="quiz-opts" data-el="opts"></ol>
        </section>
        <section class="card c-time">
          <div class="lbl">查核點與時間</div>
          <div class="cp-next" data-el="cpNext">—</div>
          <ul class="cp-list" data-el="cpList"></ul>
          <div class="lbl sm">壓縮級別</div>
          <div class="comp-row">
            <span data-el="compCue"></span>
            <span class="comp-btns">啟用：<button data-comp="0">0 級</button><button data-comp="1">1 級</button><button data-comp="2">2 級</button></span>
          </div>
          <div class="comp-advice" data-el="advice"></div>
          <div class="comp-teacher" data-el="compTeacher"></div>
        </section>
        <section class="card c-status">
          <div class="lbl">狀態</div>
          <dl class="st-grid" data-el="status"></dl>
        </section>
      </div>
    </main>
    <footer class="c-controls">
      <div class="c-btns">
        <button data-cmd="prev">上一步<small>PageUp</small></button>
        <button data-cmd="pause">暫停／繼續<small>句點（黑屏鍵）</small></button>
        <button data-cmd="next" class="primary">下一步<small>PageDown</small></button>
        <button data-cmd="replay">重播<small>R</small></button>
        <button data-cmd="start" data-el="startBtn" hidden>準備播放<small>啟用聲音</small></button>
        <button data-act="open-stage" data-el="openStage" hidden>開啟舞台視窗<small>放到投影螢幕</small></button>
      </div>
      <div class="c-tools">
        <label>跳到 <select data-el="jump"></select></label><button data-act="jump">前往</button>
        <span class="sep"></span>
        <span>時鐘</span><button data-clock="adjust:-30">−30 秒</button><button data-clock="adjust:30">＋30 秒</button><button data-clock="start">從 00:00 開始</button><button data-clock="reset">歸零</button>
        <span class="sep"></span>
        <button data-act="keytest">按鍵測試</button>
      </div>
      <div class="c-keys" data-el="keys">最後按鍵：—</div>
    </footer>
    <div class="c-overlay" data-el="ktOverlay" hidden><div class="c-overlay-box" data-el="ktBox"></div></div>`;

  const el: Record<string, HTMLElement> = {};
  root.querySelectorAll<HTMLElement>('[data-el]').forEach((x) => { el[x.dataset.el!] = x; });

  // ---------------------------------------------------------------- 狀態（只存快照與控制台自己的顯示狀態）
  let snap: StageSnapshot | null = null;
  let lastStateAt = 0;
  let cues: CueMeta[] = [];
  let cuesSession = '';
  const byId = new Map<string, CueMeta>();
  let lastSession = '';
  let rememberedClock: { startedAt: number; offsetSec: number } | null = null;
  let seq = 0;
  let lastCmd: { action: string; seq: number; at: number; effect: string | null; ok: boolean | null } | null = null;
  let lastKey: KeyReport | null = null;
  let consoleKeyRepeats = 0;
  let consoleFocused = document.hasFocus();
  let noFocusSince: number | null = null;
  let keytestOpen = false;
  let layout: HostLayout | null = null;
  let singleTimer: number | null = null;
  let singleDismissed = false;

  const connected = (): boolean => !!snap && Date.now() - lastStateAt < STALE_MS;

  const setCues = (sessionId: string, list: CueMeta[]): void => {
    cues = list;
    cuesSession = sessionId;
    byId.clear();
    for (const c of list) byId.set(c.id, c);
    // 跳到選單：依章節分組（全劇 cue 集）；目前壓縮級別會略過的段落標示出來
    const sel = el.jump as HTMLSelectElement;
    const keep = sel.value;
    const groups = new Map<string, CueMeta[]>();
    for (const c of list) { const g = c.chapter || ''; if (!groups.has(g)) groups.set(g, []); groups.get(g)!.push(c); }
    const opt = (c: CueMeta): HTMLOptionElement => {
      const o = document.createElement('option');
      o.value = c.id;
      o.textContent = `${c.id}　${c.title}${c.skipped ? '（目前略過）' : ''}`;
      return o;
    };
    sel.replaceChildren(...[...groups].flatMap(([g, cs]) => {
      if (!g) return cs.map(opt);
      const og = document.createElement('optgroup');
      og.label = g;
      og.append(...cs.map(opt));
      return [og];
    }));
    if (keep && byId.has(keep)) sel.value = keep;
  };

  transport.onMessage((m: Msg) => {
    switch (m.t) {
      case 'state': {
        const s = m.s;
        if (s.sessionId !== lastSession) {
          // 舞台重新載入：要 cue 資料；若原本授課時鐘在走，幫舞台接回去（老師要重來可以按「歸零」）
          if (lastSession && rememberedClock && s.clock.startedAt == null) {
            transport.send({ t: 'clock', op: 'restore', startedAt: rememberedClock.startedAt, offsetSec: rememberedClock.offsetSec });
          }
          lastSession = s.sessionId;
          if (cuesSession !== s.sessionId) transport.send({ t: 'hello', from: 'console', id: consoleId });
        }
        snap = s;
        lastStateAt = Date.now();
        if (s.clock.startedAt != null) rememberedClock = { startedAt: s.clock.startedAt, offsetSec: s.clock.offsetSec };
        if (s.lastKey && (!lastKey || s.lastKey.at > lastKey.at)) lastKey = s.lastKey;
        scheduleRender();
        break;
      }
      case 'cues': setCues(m.sessionId, m.cues); scheduleRender(); break;
      case 'ack':
        if (m.consoleId === consoleId && lastCmd && lastCmd.seq === m.seq) { lastCmd.effect = m.effect; lastCmd.ok = m.ok; scheduleRender(); }
        break;
      case 'key': if (!lastKey || m.k.at >= lastKey.at) { lastKey = m.k; scheduleRender(); } break;
      case 'hello': if (m.from === 'stage') transport.send({ t: 'hello', from: 'console', id: consoleId }); break;
      case 'host': if (m.layout) { layout = m.layout; scheduleRender(); } break;
      default: break;
    }
  });
  transport.send({ t: 'hello', from: 'console', id: consoleId });
  // 還沒拿到 cue 資料時每 2 秒問一次（舞台晚開也接得上）
  setInterval(() => { if (!cues.length || (snap && cuesSession !== snap.sessionId)) transport.send({ t: 'hello', from: 'console', id: consoleId }); }, 2000);

  // ---------------------------------------------------------------- 操作
  const sendCmd = (action: CmdAction, id?: string): void => {
    seq++;
    lastCmd = { action, seq, at: Date.now(), effect: connected() ? null : '舞台未連線，這一下沒有送出', ok: connected() ? null : false };
    if (connected()) transport.send({ t: 'cmd', seq, action, id, from: 'console', consoleId });
    scheduleRender();
  };

  const input = new InputController((a: Action) => {
    if (keytestOpen) return;
    if (a === 'next' || a === 'prev' || a === 'pause' || a === 'replay') sendCmd(a);
  });
  let ktPanel: KeyTestPanel | null = null;
  input.onKey = (k) => {
    if (k.repeat && k.action) consoleKeyRepeats++;
    lastKey = { key: k.key, code: k.code, repeat: k.repeat, action: k.action, window: 'console', at: Date.now() };
    if (keytestOpen) ktPanel?.handleKey(k);
    scheduleRender();
  };
  input.attach();

  const setKeytest = (on: boolean): void => {
    keytestOpen = on;
    el.ktOverlay.hidden = !on;
    if (on && !ktPanel) {
      ktPanel = new KeyTestPanel(el.ktBox, { embedded: true, onClose: () => setKeytest(false) });
      ktPanel.input = input;
    }
  };

  const stageUrl = (): string => {
    const p = new URLSearchParams(location.search);
    for (const k of ['dual', 'fallbackDelay', 'host']) p.delete(k);
    if (!p.has('cues')) p.set('cues', 'show');
    return `stage.html?${p.toString()}`;
  };

  let stageWin: Window | null = null;
  const openStage = async (): Promise<void> => {
    let features = 'popup';
    try {
      const w = window as Window & { getScreenDetails?: () => Promise<{ screens: (Screen & { availLeft: number; availTop: number; isPrimary: boolean })[]; currentScreen: Screen }> };
      if (w.getScreenDetails) {
        const sd = await w.getScreenDetails();
        const other = sd.screens.find((x) => x !== sd.currentScreen && !x.isPrimary) ?? sd.screens.find((x) => x !== sd.currentScreen);
        if (other) features += `,left=${other.availLeft},top=${other.availTop},width=${other.availWidth},height=${other.availHeight}`;
      }
    } catch { /* 沒有視窗管理權限：開在旁邊，請老師拖到投影螢幕 */ }
    if (features === 'popup') features += ',width=1280,height=720';
    stageWin = window.open(stageUrl(), 'antidrug-stage', features);
    stageWin?.focus();
  };

  root.addEventListener('click', (ev) => {
    const b = (ev.target as HTMLElement).closest('button');
    if (!b) return;
    b.blur();
    if (b.dataset.cmd) sendCmd(b.dataset.cmd as CmdAction);
    if (b.dataset.clock) {
      const [op, sec] = b.dataset.clock.split(':');
      transport.send({ t: 'clock', op: op as 'start' | 'reset' | 'adjust', sec: sec ? Number(sec) : 0 });
      if (op === 'reset') rememberedClock = null;
    }
    if (b.dataset.comp) transport.send({ t: 'compression', level: Number(b.dataset.comp) as Compression });
    switch (b.dataset.act) {
      case 'jump': sendCmd('goto', (el.jump as HTMLSelectElement).value); break;
      case 'keytest': setKeytest(!keytestOpen); break;
      case 'open-stage': void openStage(); break;
      case 'single-go': goSingle(); break;
      case 'single-stay': singleDismissed = true; if (singleTimer) clearTimeout(singleTimer); el.single.hidden = true; break;
      default: break;
    }
  });
  (el.jump as HTMLSelectElement).addEventListener('change', (e) => (e.target as HTMLElement).blur());
  document.addEventListener('contextmenu', (e) => e.preventDefault());

  // ---------------------------------------------------------------- 焦點
  const onFocusChange = (): void => { consoleFocused = document.hasFocus(); scheduleRender(); };
  window.addEventListener('focus', onFocusChange);
  window.addEventListener('blur', onFocusChange);
  setInterval(onFocusChange, 300);

  // ---------------------------------------------------------------- 單一舞台視窗退路（瀏覽器版）
  const extended = (): boolean | null => {
    const v = (screen as Screen & { isExtended?: boolean }).isExtended;
    return typeof v === 'boolean' ? v : null;
  };
  function goSingle(): void { location.replace(stageUrl()); }
  function checkSingle(): void {
    if (isElectron || singleDismissed) return;
    const forced = params.get('dual') === 'force' || params.get('dual') === '1';
    if (forced) return;
    if (extended() !== false) { if (singleTimer) { clearTimeout(singleTimer); singleTimer = null; } el.single.hidden = true; return; }
    el.single.hidden = false;
    if (connected()) {
      // 舞台已經開著（同一個畫面）：不再開第二個舞台，只提醒
      el.singleTitle.textContent = '只有一個畫面：控制台會被投影出去';
      el.singleText.textContent = '目前是同步顯示（或沒接投影機）。請在 Windows 按 Win＋P 改成「延伸」，或關掉控制台、只用舞台視窗演出。';
      if (singleTimer) { clearTimeout(singleTimer); singleTimer = null; }
      return;
    }
    const delay = Math.max(0, Number(params.get('fallbackDelay') ?? 5000));
    el.singleTitle.textContent = '只有一個畫面：改用單一舞台視窗';
    el.singleText.textContent = `目前是同步顯示（或沒接投影機），控制台會被投影出去。${Math.round(delay / 1000)} 秒後自動改成單一舞台視窗（用簡報筆照常操作；M 鍵是教師選單）。`;
    if (singleTimer == null) singleTimer = window.setTimeout(goSingle, delay);
  }
  // 先等一下看舞台是否已經開著，再決定
  setTimeout(checkSingle, Number(params.get('fallbackDelay') ?? 5000) === 0 ? 0 : 1200);
  (screen as Screen & { addEventListener?: (t: string, f: () => void) => void }).addEventListener?.('change', checkSingle);
  if (isElectron) void window.theaterHost!.info().then((i) => { layout = i.layout; scheduleRender(); }).catch(() => undefined);

  // ---------------------------------------------------------------- 畫面更新
  let renderQueued = false;
  function scheduleRender(): void {
    if (renderQueued) return;
    renderQueued = true;
    requestAnimationFrame(() => { renderQueued = false; render(); });
  }
  setInterval(render, 250);

  const setText = (e: HTMLElement, t: string): void => { if (e.textContent !== t) e.textContent = t; };

  function render(): void {
    const ok = connected();
    const s = ok ? snap : null;
    const e = s?.engine;
    const cur = e?.cueId ? byId.get(e.cueId) : undefined;
    const nxt = cur?.next ? byId.get(cur.next) : undefined;

    // 頂列：連線、焦點、時鐘
    setText(el.link, ok ? `舞台：已連線（${TRANSPORT_LABEL[transport.kind]}）` : snap ? '舞台：連線中斷' : '舞台：未連線');
    el.link.className = `c-pill ${ok ? 'good' : 'warn'}`;
    const stageFocused = !!s?.win.focused;
    const owner = consoleFocused ? 'console' : stageFocused ? 'stage' : 'none';
    if (owner === 'none') { if (noFocusSince == null) noFocusSince = Date.now(); } else noFocusSince = null;
    const showWarn = owner === 'none' && Date.now() - (noFocusSince ?? Date.now()) >= FOCUS_GRACE_MS;
    setText(el.focus, owner === 'console' ? '焦點：控制台（簡報筆可用）' : owner === 'stage' ? '焦點：舞台視窗（簡報筆可用）' : '焦點：都沒有');
    el.focus.className = `c-pill ${owner === 'console' ? 'good' : owner === 'stage' ? 'note' : 'warn'}`;
    el.focusWarn.hidden = !showWarn;
    document.body.classList.toggle('no-focus', showWarn);
    const cs = classClockSec(s?.clock);
    setText(el.clock, cs == null ? '未開始' : clockText(cs));

    // 下一步
    const ns = nextStep(s, byId, ok);
    setText(el.nextMain, ns.main);
    setText(el.nextSub, ns.sub);
    el.nextCard.dataset.tone = ns.tone;
    setText(el.phase, e ? (e.paused ? `暫停中｜${e.phaseLabel}` : e.phaseLabel) : '—');
    setText(el.cue, cur ? `${cur.id}　${cur.title}` : '');
    const frac = e && e.cueDuration > 0 ? Math.min(1, e.cueTime / e.cueDuration) : 0;
    el.bar.style.width = `${(frac * 100).toFixed(1)}%`;
    setText(el.time, e ? `${e.cueTime.toFixed(1)}／${e.cueDuration.toFixed(1)} 秒` : '');
    const prevCue = cur?.prevStable ? byId.get(cur.prevStable) : undefined;
    setText(el.prev, !cur ? '' : prevCue ? `上一步會回到：〈${prevCue.title || prevCue.id}〉停住的畫面` : cur.index === 0 ? '上一步：已在片頭署名卡' : '上一步：回到片頭署名卡');
    (el.startBtn as HTMLButtonElement).hidden = !(s && e?.mode === 'preparing' && s.canRemoteStart);
    el.openStage.hidden = isElectron || ok;

    // 講稿重點
    setText(el.noteCue, cur?.id ?? '');
    setText(el.note, cur?.teacherNote || (cur ? '（這一段沒有講稿提示）' : '—'));
    setText(el.noteNextCue, nxt ? `${nxt.id}　${describeCue(nxt)}` : '');
    setText(el.noteNext, nxt ? (nxt.teacherNote || '（沒有講稿提示）') : '—');
    setText(el.sub, e?.subtitle?.replace(/\s+/g, ' ') || '—');

    // 題目
    const qc = quizContext(s, byId);
    el.quizCard.hidden = !qc;
    if (qc) {
      setText(el.quizLbl, qc.upcoming ? `下一題 ${qc.quiz.qid}（預告）` : `本題 ${qc.quiz.qid}${e?.revealed ? '（已揭曉）' : ''}`);
      setText(el.ans, String(qc.quiz.answer));
      setText(el.zone, `${qc.quiz.zone} 區`);
      setText(el.q, qc.quiz.question.replace(/\n/g, ''));
      const sig = `${qc.quiz.qid}|${qc.quiz.answer}`;
      if (el.opts.dataset.sig !== sig) {
        el.opts.dataset.sig = sig;
        el.opts.replaceChildren(...qc.quiz.options.map((o, i) => {
          const li = document.createElement('li');
          li.className = i + 1 === qc.quiz.answer ? 'correct' : '';
          li.textContent = `${i + 1}　${o.replace(/\n/g, '')}${i + 1 === qc.quiz.answer ? '　✓ 正解' : ''}`;
          return li;
        }));
      }
    }

    // 查核點
    const cps = cues.filter((c) => c.checkpoint && c.checkpoint.atMinute > 0 && c.index > 0);
    const reached = s?.clock.reached ?? {};
    const nextCp = cps.find((c) => !reached[c.id]);
    if (!cps.length) setText(el.cpNext, '這個 cue 集沒有查核點');
    else if (nextCp) {
      const target = nextCp.checkpoint!.atMinute * 60;
      const left = cs == null ? null : target - cs;
      setText(el.cpNext, `下一個查核點：${nextCp.checkpoint!.label}（${nextCp.id}）目標 ${clockText(target)}${left == null ? '' : left >= 0 ? `，還有 ${mmss(left)}` : `，已超過 ${mmss(left)}`}`);
    } else setText(el.cpNext, '查核點都過了');
    const cpSig = `${cps.map((c) => c.id).join(',')}|${JSON.stringify(reached)}`;
    if (el.cpList.dataset.sig !== cpSig) {
      el.cpList.dataset.sig = cpSig;
      el.cpList.replaceChildren(...cps.map((c) => {
        const li = document.createElement('li');
        const r = reached[c.id];
        li.className = r ? (r.driftSec >= 30 ? 'behind' : r.driftSec <= -30 ? 'ahead' : 'ontime') : 'pending';
        li.textContent = `${c.checkpoint!.label}　目標 ${clockText(c.checkpoint!.atMinute * 60)}　${r ? `實際 ${clockText(r.clockSec)}，${driftText(r.driftSec)}` : '尚未到'}`;
        return li;
      }));
    }
    const level = s?.compressionLevel ?? 0;
    setText(el.compCue, cur ? `本段：${COMPRESSION_LABEL[cur.compression]}` : '本段：—');
    root.querySelectorAll<HTMLButtonElement>('button[data-comp]').forEach((b) => b.classList.toggle('on', Number(b.dataset.comp) === level));
    const adv = compressionAdvice(cues, reached);
    setText(el.advice, adv.level > level ? `建議啟用 ${adv.level} 級：${adv.reason}` : adv.level > 0 ? `已依建議啟用（${adv.reason}）` : '目前不需要壓縮。');
    el.advice.className = `comp-advice ${adv.level > level ? 'warn' : ''}`;
    let teacher = `目前 ${level} 級：${COMPRESSION_TEACHER[level]}`;
    if (s?.pendingCompression != null) teacher = `已選 ${s.pendingCompression} 級：這段播完後套用。${teacher}`;
    if (level >= 2 && cur?.shortVersion) teacher += `　本段短版：${cur.shortVersion}`;
    if (level >= 1 && s?.engineCompression && cur?.droppedLines.length) teacher += `　本段略過：${cur.droppedLines.map((x) => x.replace(/^a\d_c\d{3}/, '')).join('、')}`;
    if (s && !s.engineCompression && level > 0) teacher += '　（這版引擎不會自動略過，請依紙本講稿處理）';
    setText(el.compTeacher, teacher);

    // 狀態
    const rows: [string, string, string?][] = e && s ? [
      ['更新率', e.mode === 'playing' && !e.paused ? `${e.fps.toFixed(0)} fps` : '等待中（降載）', e.mode === 'playing' && !e.paused && e.fps > 0 && e.fps < 28 ? 'warn' : ''],
      e.mode === 'preparing' || e.mode === 'loading'
        ? ['聲音', '開演前（按「準備播放」後啟用）']
        : ['聲音', `${AUDIO_TEXT[e.audioState] ?? e.audioState}｜${CLOCK_TEXT[e.clock] ?? e.clock}`, e.audioState !== 'running' || e.clock !== 'audio' ? 'warn' : ''],
      ['配音', e.placeholderAudio ? '這一段用暫代音訊' : '正式配音', e.placeholderAudio ? 'warn' : ''],
      ['缺檔', e.missingAudio.length ? `配樂音效缺 ${e.missingAudio.length} 個（該處無聲）` : '沒有', e.missingAudio.length ? 'warn' : ''],
      ['畫質', `${e.quality} 級${e.lock30 ? '｜鎖 30 fps' : ''}｜開頭靜音 ${e.leadInMs} ms｜聲畫偏移 ${e.avOffsetMs} ms`],
      ['舞台畫面', `${s.win.w}×${s.win.h}｜縮放 ${s.win.dpr}｜${s.win.visible ? '顯示中' : '被隱藏'}`, s.win.visible ? '' : 'warn'],
      ['視窗', layout ? (layout.mode === 'single' ? '單一舞台視窗' : layout.mode === 'dual' ? '雙視窗（延伸顯示）' : '雙視窗（測試）') : (s.host === 'electron' ? 'Electron' : '瀏覽器雙視窗')],
      ['忽略的輸入', `連按 ${e.ignoredInputs}｜長按 ${e.ignoredRepeats + consoleKeyRepeats}｜F5／Esc 攔截 ${e.blockedKeys}`],
      ['顯示卡', e.gpu.replace(/^ANGLE \(|\)$/g, '').slice(0, 60)],
      ...(e.errors.length ? [['訊息', e.errors[e.errors.length - 1], 'warn'] as [string, string, string]] : []),
    ] : [['連線', ok ? '—' : '等待舞台視窗…', 'warn']];
    const stSig = JSON.stringify(rows);
    if (el.status.dataset.sig !== stSig) {
      el.status.dataset.sig = stSig;
      el.status.replaceChildren(...rows.flatMap(([k, v, cls]) => {
        const dt = document.createElement('dt'); dt.textContent = k;
        const dd = document.createElement('dd'); dd.textContent = v; if (cls) dd.className = cls;
        return [dt, dd];
      }));
    }

    // 最後按鍵與操作回應
    const parts: string[] = [];
    if (lastKey) parts.push(`最後按鍵：${keyLabel(lastKey.key, lastKey.code)}（${lastKey.window === 'stage' ? '舞台視窗' : '控制台'}）→ ${lastKey.action ? ACTION_LABEL[lastKey.action as Action] ?? lastKey.action : '無作用'}${lastKey.repeat ? '（長按重複，已忽略）' : ''}`);
    else parts.push('最後按鍵：—');
    if (lastCmd) parts.push(`${ACTION_LABEL[lastCmd.action as Action] ?? (lastCmd.action === 'goto' ? '跳到' : lastCmd.action === 'start' ? '準備播放' : lastCmd.action)}：${lastCmd.effect ? (EFFECT_TEXT[lastCmd.effect] ?? lastCmd.effect) : '送出中…'}`);
    if (keytestOpen) parts.push('按鍵測試中：按鍵不會送到劇場');
    setText(el.keys, parts.join('　｜　'));
    el.keys.className = `c-keys ${lastCmd && lastCmd.ok === false ? 'warn' : ''}`;

    document.body.dataset.phase = e?.phase ?? 'none';
    checkSingleLive();
  }

  function checkSingleLive(): void {
    if (!el.single.hidden && connected() && singleTimer != null) checkSingle();
  }

  // 控制台移到不同縮放的螢幕：CSS 依視窗大小排版，這裡只重畫一次
  const watchDpr = (): void => {
    const mq = matchMedia(`(resolution: ${window.devicePixelRatio}dppx)`);
    mq.addEventListener('change', () => { scheduleRender(); watchDpr(); }, { once: true });
  };
  watchDpr();

  (window as Window & { __console?: unknown }).__console = {
    transport: transport.kind,
    connected,
    snapshot: () => snap,
    cues: () => cues,
    focusOwner: () => (consoleFocused ? 'console' : snap?.win.focused ? 'stage' : 'none'),
    lastCmd: () => lastCmd,
    lastKey: () => lastKey,
    keytestOpen: () => keytestOpen,
    input,
  };
  render();
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
else boot();
