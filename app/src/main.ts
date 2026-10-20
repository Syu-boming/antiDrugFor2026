// 劇場程式進入點：建立舞台、音訊、疊層與引擎，掛上按鍵，並提供 window.__engine 給測試與擷取腳本。
import { readConfig } from './config';
import { Mixer } from './audio/mixer';
import { Stage } from './stage/stage';
import { UI } from './ui/ui';
import { Engine, type EngineState } from './engine/engine';
import { InputController, type Action } from './engine/input';
import { TeacherMenu } from './ui/overlays';

declare global {
  interface Window {
    __engine?: EngineAPI;
  }
}

/** 給測試（tools/engine-test.mjs）與擷取（tools/capture.mjs）用的程式介面 */
export interface EngineAPI {
  next(): void;
  prev(): void;
  pause(): void;
  replay(): void;
  gotoCue(id: string, opts?: { mode?: 'before' | 'after' | 'play' }): boolean;
  getState(): EngineState;
  getCues(): ReturnType<Engine['getCues']>;
  start(): Promise<void>;
  ready(): boolean;
  capture: {
    playCue(id: string): { duration: number; id: string };
    seek(t: number): ReturnType<Engine['captureSeek']>;
    step(frames?: number): ReturnType<Engine['captureStep']>;
  };
  debug: {
    loseContext(): boolean;
    restoreContext(): boolean;
    keyLog(): unknown[];
    setAvOffset(ms: number): void;
  };
}

function boot(): void {
  const cfg = readConfig();
  document.body.classList.toggle('capture', cfg.capture);
  const ui = new UI();
  const mixer = new Mixer();
  let engine: Engine | null = null;
  const stage = new Stage({ host: ui.stageBox, quality: cfg.quality, capture: cfg.capture, lipsync: (id) => engine?.lipsyncData(id) });

  let menu: TeacherMenu | null = null;
  const onAction = (a: Action): void => {
    if (!engine) return;
    if (a === 'menu') { if (!cfg.capture) menu?.toggle(); return; }
    if (a === 'next') engine.next();
    else if (a === 'prev') engine.prev();
    else if (a === 'pause') engine.togglePause();
    else if (a === 'replay') engine.replay();
    menu?.refresh();
  };
  const input = new InputController(onAction);
  engine = new Engine(cfg, stage, ui, mixer, input);
  const eng = engine;
  input.onKey = (e) => menu?.showKey(e.key, e.code);
  input.attach();

  menu = new TeacherMenu(document.getElementById('teacher-menu')!, {
    getAvOffset: () => eng.avOffsetMs,
    setAvOffset: (ms) => eng.setAvOffset(ms),
    getQuality: () => stage.quality,
    setQuality: (q) => eng.setQuality(q),
    getLock30: () => eng.lock30,
    setLock30: (on) => eng.setLock30(on),
    cues: () => eng.getCues().map((c) => ({ id: c.id, title: c.title })),
    gotoCue: (id) => { eng.gotoCue(id, { mode: 'before' }); },
    status: () => {
      const s = eng.getState();
      return `${s.phaseLabel}｜${s.cueId ?? '—'}｜${s.cueTime.toFixed(1)}／${s.cueDuration.toFixed(1)} 秒｜時鐘 ${s.clock}｜音訊 ${s.audioState}｜${s.fps} fps｜${s.gpu}`;
    },
  });
  if (cfg.menu) menu.toggle();
  ui.ready.onStart = () => { void eng.start(); };
  ui.ready.show(true);

  const onResize = (): void => eng.resize();
  window.addEventListener('resize', onResize);
  document.addEventListener('fullscreenchange', onResize);
  // 舞台視窗移到不同縮放比例的螢幕時，依新的 devicePixelRatio 重設解析度
  const watchDpr = (): void => {
    const mq = matchMedia(`(resolution: ${window.devicePixelRatio}dppx)`);
    mq.addEventListener('change', () => { onResize(); watchDpr(); }, { once: true });
  };
  watchDpr();
  document.addEventListener('contextmenu', (e) => { if (!cfg.capture) e.preventDefault(); });

  window.__engine = {
    next: () => eng.next(),
    prev: () => eng.prev(),
    pause: () => eng.togglePause(),
    replay: () => eng.replay(),
    gotoCue: (id, opts) => eng.gotoCue(id, opts),
    getState: () => eng.getState(),
    getCues: () => eng.getCues(),
    start: () => eng.start(),
    ready: () => eng.mode !== 'loading' && eng.mode !== 'preparing',
    capture: {
      playCue: (id) => {
        if (!eng.gotoCue(id, { mode: 'play' })) throw new Error(`找不到 cue ${id}`);
        const s = eng.getState();
        return { duration: s.cueDuration, id };
      },
      seek: (t) => eng.captureSeek(t),
      step: (n) => eng.captureStep(n),
    },
    debug: {
      loseContext: () => stage.loseContextForTest(),
      restoreContext: () => stage.restoreContextForTest(),
      keyLog: () => [...input.log],
      setAvOffset: (ms) => eng.setAvOffset(ms),
    },
  };

  eng.resize();
  eng.start_loop();
  void eng.load().then(() => { if (cfg.autostart) void eng.start(); });
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
else boot();
