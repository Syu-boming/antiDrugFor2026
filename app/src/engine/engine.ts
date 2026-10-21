// 播放引擎：cue 狀態機（v1.2 第 19.1 節）＋單一時鐘＋音訊排程＋GPU 中斷處理。
//
// | 畫面狀態       | 下一步行為               | 必要限制 |
// | 片頭待機       | 播放完整開幕段落         | 素材與音訊未就緒時，先停在準備畫面 |
// | 劇情等待       | 播放下一個劇情段落       | 不跨越整幕或整組問題（每次只推進一個節點） |
// | 劇情播放中     | 忽略意外的重複輸入       | 不因連按跳過重點 |
// | 題目出現       | 顯示正解與回饋           | 出題後沒有自動倒數揭答 |
// | 正解回饋播放中 | 忽略重複輸入             | 回饋完畢後停住，留出發獎時間 |
// | 正解等待       | 收起題卡，開始後續劇情   | 一次按鍵不會連續觸發揭答與換幕 |
// | 最後謝幕等待   | 關幕，顯示片尾署名卡     | 結束後保持畫面 |
//
// 上一鍵：回到上一個穩定節點（cue 播完後的停住畫面），停止舊音軌並重建該節點畫面；回到題目時恢復成未揭答。
// 「穩定節點」＝某個 cue 播完停住的畫面；等待狀態一律顯示該 cue 的最後一格（純函式重建）。
import type { Cue, CueFile } from '../types/cue';
import { validateCueFile, type ValidationResult } from '../cues/validate';
import { buildTimelines, type CueTimeline } from '../cues/timeline';
import { getPack, loadPackFile, loadPackFiles, type PackManifest } from '../data/packs';
import { AssetStore } from '../data/assets';
import { AudioClock, PerformanceClock, VirtualClock, type Clock } from './clock';
import { evaluateWorld, type WorldState } from './world';
import type { Mixer } from '../audio/mixer';
import type { Stage, Quality } from '../stage/stage';
import type { UI } from '../ui/ui';
import type { InputController } from './input';
import type { LipsyncData } from '../stage/perform';
import { HOLD_MUSIC_RATIO, HOLD_TC } from '../audio/ducking';
import { saveSettings, type Config } from '../config';

export type Mode = 'loading' | 'preparing' | 'waiting' | 'playing' | 'context_lost' | 'error';
export type Phase = 'loading' | 'preparing' | 'title_idle' | 'playing' | 'quiz_playing' | 'reveal_playing' | 'story_waiting'
  | 'quiz_shown' | 'reveal_waiting' | 'final_waiting' | 'ended' | 'context_lost' | 'error';

export const PHASE_LABEL: Record<Phase, string> = {
  loading: '載入中', preparing: '準備畫面', title_idle: '片頭待機', playing: '劇情播放中', quiz_playing: '出題播放中',
  reveal_playing: '正解回饋播放中', story_waiting: '劇情等待', quiz_shown: '題目出現', reveal_waiting: '正解等待',
  final_waiting: '最後謝幕等待', ended: '結束（保持署名卡）', context_lost: '畫面中斷（等待重建）', error: '錯誤',
};

/** 進入等待後這段時間內的「下一步」視為連按誤觸（毫秒；擷取模式不適用） */
const WAIT_GUARD_MS = 350;

/** 依 cue 種類的配樂基準音量：題目與發獎時很低，署名卡待機沒有音樂 */
const MUSIC_LEVEL: Record<Cue['kind'], number> = { title: 0, curtain: 0.8, scene: 0.8, wait: 0.35, quiz: 0.06, reveal: 0.06, lamp: 0.5 };

export interface EngineState {
  mode: Mode; phase: Phase; phaseLabel: string; paused: boolean; pauseReason: string | null;
  cueId: string | null; cueIndex: number; kind: string | null; title: string;
  cueTime: number; cueDuration: number; revealed: boolean; quizVisible: boolean; lampsLit: number[];
  placeholderAudio: boolean; activeVoices: number; voiceIds: string[]; voSounding: number; subtitle: string;
  missingAudio: string[]; castReport: string[]; set: string; actors: string[];
  world: { curtain: number; titleCard: number; set: number; desat: number; spot: number; light: number } | null;
  clock: string; audioState: string; avOffsetMs: number; leadInMs: number; quality: Quality; lock30: boolean; playId: number;
  ignoredInputs: number; ignoredRepeats: number; blockedKeys: number; lastBlockedKey: string | null;
  fps: number; contextLost: boolean; errors: string[]; warnings: string[]; gpu: string;
}

export class Engine {
  file: CueFile | null = null;
  timelines: CueTimeline[] = [];
  private idIndex = new Map<string, number>();
  mode: Mode = 'loading';
  paused = false;
  pauseReason: string | null = null;
  index = 0;
  private cueStart = 0;
  private playId = 0;
  private waitEnteredAt = 0;
  ignoredInputs = 0;
  private clock: Clock;
  private lostReturn = 0;
  private recovering = false;
  private lastFrameMs = 0;
  private lastRenderMs = 0;
  private fpsEma = 0;
  private lampsCache = new Map<number, number[]>();
  private lipsync = new Map<string, LipsyncData>();
  manifest: PackManifest | null = null;
  readonly assets = new AssetStore();
  /** 配樂與音效缺檔（照常演出，準備畫面列出） */
  missingAudio: string[] = [];
  validation: ValidationResult | null = null;
  errors: string[] = [];
  avOffsetMs: number;
  /** 每段開頭的靜音（毫秒；HDMI 吞音時加長） */
  leadInMs: number;
  lock30: boolean;
  private lastWorld: WorldState | null = null;

  constructor(private cfg: Config, private stage: Stage, private ui: UI, private mixer: Mixer, private input: InputController) {
    this.avOffsetMs = cfg.avOffsetMs;
    this.leadInMs = cfg.leadInMs;
    this.lock30 = cfg.lock30;
    this.clock = cfg.capture ? new VirtualClock(1 / cfg.stepFps) : new PerformanceClock(() => this.avOffsetMs);
    stage.onContextLost = () => this.onContextLost();
    stage.onContextRestored = () => { if (this.mode === 'context_lost') this.ui.lost.show('顯示卡已恢復。請按「下一步」重新建立畫面。'); };
    // 頁面被隱藏或系統休眠才暫停；失焦不暫停。恢復後等老師按鍵，不自行發聲
    document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') this.autoPause('hidden'); });
    window.addEventListener('pagehide', () => this.autoPause('hidden'));
    document.addEventListener('freeze', () => this.autoPause('freeze'));
    if (mixer.ctx) {
      mixer.ctx.addEventListener('statechange', () => {
        const st = mixer.ctx!.state as string; // suspended／interrupted（Safari）／closed 都當成被系統停掉
        if (this.clock.kind !== 'audio') return;
        if (!this.clock.paused && st !== 'running') this.autoPause('audio');
        // 系統自己恢復了音訊、但引擎還在暫停（等老師按鍵）：再停一次，聲音與畫面保持同一個時鐘
        else if (this.paused && st === 'running') void mixer.ctx!.suspend().catch(() => undefined);
      });
    }
  }

  get capturing(): boolean { return this.cfg.capture; }
  lipsyncData = (id: string): LipsyncData | undefined => this.lipsync.get(id);

  // ---------------------------------------------------------------- 載入

  async load(): Promise<void> {
    this.mode = 'loading';
    this.ui.ready.setStatus([{ label: '資料包', value: '載入中…', ok: null }]);
    try {
      const man = getPack<PackManifest>('manifest');
      if (!man) throw new Error('找不到 data/manifest.js。請先在 app 資料夾執行 npm run build。');
      this.manifest = man;
      const packFile = man.cueSets[this.cfg.cues];
      if (!packFile) throw new Error(`資料包裡沒有 cue 檔「${this.cfg.cues}」（可用：${Object.keys(man.cueSets).join('、') || '無'}）`);
      await loadPackFile(packFile);
      const file = getPack<CueFile>(`cues:${this.cfg.cues}`);
      this.validation = validateCueFile(file);
      if (!this.validation.ok || !file) throw new Error(`cue 檔有錯誤：\n${this.validation.errors.join('\n')}`);
      this.file = file;

      // 素材（圖像、分件資料、臉部換片），然後依 cue 檔建立景與演員
      this.ui.ready.setStatus([{ label: '素材', value: '載入中…', ok: null }]);
      await this.assets.load(man, (d, n) => this.ui.ready.setStatus([{ label: '素材', value: `${d}／${n}`, ok: null }]));
      this.stage.setScene(file, this.assets);
      const paper = getPack<string>('img:tex-titlecard-paper');
      if (paper) this.ui.title.setPaper(paper);

      // 音檔與對嘴資料：找得到就載入並解碼，找不到的句子進暫代模式；配樂與音效缺檔照常演出
      const audioIds = new Set<string>();
      const lipIds = new Set<string>();
      const nonVo = new Set<string>();
      for (const c of file.cues) {
        for (const l of c.lines) { audioIds.add(l.audioId ?? `vo_${l.id}`); lipIds.add(l.lipsyncId ?? l.id); }
        if (c.audioId && c.audioId !== 'none') { audioIds.add(c.audioId); nonVo.add(c.audioId); }
        for (const s of c.sfx ?? []) { audioIds.add(s.id); nonVo.add(s.id); }
        for (const m of c.music ?? []) if (m.id !== 'none') { audioIds.add(m.id); nonVo.add(m.id); }
      }
      const files = new Set<string>();
      for (const id of audioIds) if (man.audio[id]) files.add(man.audio[id].file);
      for (const id of lipIds) if (man.lipsync[id]) files.add(man.lipsync[id].file);
      await loadPackFiles(files, (d, n) => this.ui.ready.setStatus([{ label: '資料包', value: `${d}／${n}`, ok: null }]));
      let decoded = 0;
      await Promise.all([...audioIds].map(async (id) => {
        const data = getPack<string>(`audio:${id}`);
        if (data && await this.mixer.decode(id, data)) decoded++;
      }));
      for (const id of lipIds) { const d = getPack<LipsyncData>(`lip:${id}`); if (d) this.lipsync.set(id, d); }
      this.missingAudio = [...nonVo].filter((id) => !man.audio[id] || (this.mixer.available && !this.mixer.has(id))).sort();

      this.timelines = buildTimelines(file, (id) => this.mixer.duration(id));
      this.idIndex = new Map(this.timelines.map((t) => [t.cue.id, t.index]));
      this.lampsCache.clear();
      const voTotal = file.cues.reduce((n, c) => n + c.lines.length, 0);
      const voReal = this.timelines.reduce((n, t) => n + t.lines.filter((l) => !l.placeholder).length, 0);
      this.index = 0;
      this.mode = 'preparing';
      this.renderNow(performance.now());
      this.ui.ready.setStatus([
        { label: 'cue 檔', value: `${file.title}（${file.cues.length} 個 cue）`, ok: true },
        { label: '配音', value: voReal === voTotal ? `${voReal} 句全部就緒` : `${voReal}／${voTotal} 句有音檔，其餘用暫代音訊`, ok: voReal === voTotal ? true : null },
        { label: '音訊', value: this.mixer.available ? `可用（已解碼 ${decoded} 個音檔）` : '無法建立音訊（只顯示字幕）', ok: this.mixer.available },
        { label: '配樂音效', value: this.missingAudio.length ? `缺 ${this.missingAudio.length} 個檔（照常演出、該處無聲）：${this.missingAudio.join('、')}` : '全部就緒', ok: this.missingAudio.length ? null : true },
        { label: '紙偶', value: `${[...this.stage.actors.keys()].join('、') || '無'}${this.stage.castReport.length ? `；${this.stage.castReport.join('；')}` : ''}`, ok: this.stage.castReport.length ? null : true },
        { label: '顯示卡', value: this.stage.gpuInfo, ok: !/SwiftShader|llvmpipe|Software/i.test(this.stage.gpuInfo) },
        ...(this.validation.warnings.length ? [{ label: '提醒', value: this.validation.warnings.join('；'), ok: null }] : []),
      ]);
      this.ui.ready.setReady(true);
    } catch (err) {
      this.mode = 'error';
      const msg = err instanceof Error ? err.message : String(err);
      this.errors.push(msg);
      this.ui.ready.setStatus([{ label: '無法開始', value: msg, ok: false }]);
      this.ui.ready.setReady(false, '請依上面的訊息修正後重新整理。');
      console.error('[engine]', err);
    }
  }

  /** 「準備播放」：啟用聲音、確認全螢幕、預先編譯，然後停在署名卡 */
  async start(): Promise<void> {
    if (this.mode !== 'preparing') return;
    this.mode = 'loading';
    // 全螢幕必須在使用者操作的當下呼叫
    if (!this.cfg.noFullscreen && !document.fullscreenElement) {
      document.documentElement.requestFullscreen?.().then(() => {
        const kb = (navigator as unknown as { keyboard?: { lock?: (keys: string[]) => Promise<void> } }).keyboard;
        return kb?.lock?.(['Escape', 'F5']);
      }).catch(() => undefined);
    }
    if (!this.cfg.capture && this.mixer.ctx) {
      const ok = await this.mixer.unlock();
      const ctx = this.mixer.ctx;
      const t0 = ctx.currentTime;
      await new Promise((r) => setTimeout(r, 250));
      this.clock = ok && ctx.currentTime > t0 ? new AudioClock(ctx, () => this.avOffsetMs) : new PerformanceClock(() => this.avOffsetMs, () => ctx.currentTime);
      if (this.clock.kind !== 'audio') this.errors.push('音訊時鐘沒有前進，改用系統時鐘（聲音可能無法播放）');
    }
    if (this.stage.contextLost) await this.stage.rebuild();
    else await this.stage.precompile();
    this.warmUp();
    this.ui.ready.show(false);
    this.enterWaiting(0);
  }

  // ---------------------------------------------------------------- 老師操作

  next(): void {
    if (this.mode === 'context_lost') { void this.recover(); return; }
    if (this.mode === 'preparing') { void this.start(); return; }
    if (this.mode !== 'waiting' && this.mode !== 'playing') return;
    if (this.paused) { this.resume(); return; } // 暫停中：先繼續，不前進
    if (this.mode === 'playing') { this.ignoredInputs++; return; } // 播放中忽略重複輸入
    if (!this.capturing && performance.now() - this.waitEnteredAt < WAIT_GUARD_MS) { this.ignoredInputs++; return; }
    const tl = this.timelines[this.index];
    if (tl.nextIndex < 0) { this.ignoredInputs++; return; } // 結束後保持畫面
    this.playCue(tl.nextIndex);
  }

  prev(): void {
    if (this.mode === 'context_lost') { void this.recover(); return; }
    if (this.mode !== 'waiting' && this.mode !== 'playing') return;
    const tl = this.timelines[this.index];
    const target = tl.prevStableIndex;
    if (target < 0) {
      if (this.mode === 'waiting') { this.ignoredInputs++; return; }
      this.enterWaiting(0);
      return;
    }
    if (this.paused) this.resume();
    this.enterWaiting(target);
  }

  togglePause(): void {
    if (this.mode === 'context_lost') { void this.recover(); return; }
    if (this.mode !== 'waiting' && this.mode !== 'playing') return;
    if (this.paused) this.resume(); else this.pause('teacher');
  }

  replay(): void {
    if (this.mode === 'context_lost') { void this.recover(); return; }
    if (this.mode !== 'waiting' && this.mode !== 'playing') return;
    const tl = this.timelines[this.index];
    if (tl.duration <= 0) { this.ignoredInputs++; return; } // 署名卡待機沒有可重播的段落
    if (this.paused) this.resume();
    this.playCue(this.index);
  }

  /** 跳到某個 cue：before＝停在它的前一個穩定節點（按下一步就播它）、after＝停在它播完的畫面、play＝直接播放 */
  gotoCue(id: string, opts: { mode?: 'before' | 'after' | 'play' } = {}): boolean {
    const i = this.idIndex.get(id);
    if (i === undefined || (this.mode !== 'waiting' && this.mode !== 'playing')) return false;
    if (this.paused) this.resume();
    const m = opts.mode ?? 'before';
    if (m === 'play') this.playCue(i);
    else if (m === 'after') this.enterWaiting(i);
    else {
      const pred = this.timelines.findIndex((t) => t.nextIndex === i && !t.cue.autoAdvance);
      this.enterWaiting(pred >= 0 ? pred : Math.max(0, this.timelines[i].prevStableIndex));
    }
    return true;
  }

  pause(reason: string): void {
    if (this.paused) return;
    this.paused = true;
    this.pauseReason = reason;
    this.clock.pause();
  }

  resume(): void {
    if (!this.paused) return;
    this.paused = false;
    this.pauseReason = null;
    this.clock.resume();
  }

  private autoPause(reason: string): void {
    if (this.mode === 'playing' && !this.paused && !this.capturing) this.pause(reason);
  }

  /**
   * 預熱（G4 修正第 28 項）：開演前在準備畫面後面把每個 cue 的開頭、中間、結尾各畫一次，
   * 讓錨點鏡位、紙偶姿勢、臉部換片與陰影的貼圖上傳和著色器變體都先做完，播放中不會第一次才做而卡一下。
   */
  private warmUp(): void {
    if (this.stage.contextLost || !this.timelines.length) return;
    const t0 = performance.now();
    for (const tl of this.timelines) {
      for (const t of [0, tl.duration * 0.5, tl.duration]) {
        const world = evaluateWorld(tl, t, this.lampsBefore(tl.index), this.stage.cameraResolver(tl));
        this.stage.apply(world, tl, t, `warm#${tl.index}`);
        this.stage.render();
      }
    }
    this.stage.director.reset();
    this.warmMs = performance.now() - t0;
  }
  warmMs = 0;

  // ---------------------------------------------------------------- 狀態轉換

  private playCue(i: number): void {
    const tl = this.timelines[i];
    if (!tl) return;
    this.mixer.stop('vo');
    this.mixer.stop('sfx');
    this.index = i;
    this.playId++;
    this.mode = 'playing';
    this.stage.director.reset();
    if (this.clock instanceof VirtualClock) this.cueStart = this.clock.now();
    else {
      // 瀏覽器在背景時可能把 AudioContext 停掉；按鍵當下恢復
      if (this.clock.kind === 'audio' && this.mixer.ctx && this.mixer.ctx.state !== 'running') void this.mixer.ctx.resume();
      // 每段開頭的靜音（HDMI 吞音時由教師選單加長）：畫面停在第一格、聲音一起延後
      this.cueStart = this.clock.now() + this.clock.lead() + this.leadInMs / 1000;
    }
    this.scheduleAudio(tl);
    this.renderNow(performance.now());
  }

  private scheduleAudio(tl: CueTimeline): void {
    if (this.clock.kind !== 'audio') return;
    const at = (s: number): number => this.clock.toAudioTime(this.cueStart + s);
    const intervals: [number, number][] = [];
    for (const l of tl.lines) {
      if (this.mixer.playAt('vo', l.audioId, at(l.start))) intervals.push([at(l.start), at(l.end)]);
    }
    for (const s of tl.sfx) this.mixer.playAt('sfx', s.id, at(s.at), { gain: s.gain });
    const music = tl.cue.audioId;
    if (music === 'none') this.mixer.crossfadeMusic('none', at(0), { fade: 1.0 });
    else if (music && this.mixer.musicId !== music) this.mixer.crossfadeMusic(music, at(0), { loop: tl.cue.musicLoop ?? true, fade: 1.0 });
    for (const m of tl.music) this.mixer.crossfadeMusic(m.id, at(m.at), { loop: m.loop, fade: m.fade, gain: m.gain, offset: m.offset });
    const level = tl.cue.musicLevel ?? MUSIC_LEVEL[tl.cue.kind] ?? 0.6;
    this.mixer.setMusicLevel(level, at(0));
    // 教師停格：劇情段落播完、停住等老師時，配樂慢慢降到約 −20 dB（3 秒內 ≤ −35 LUFS）
    if (tl.cue.kind === 'scene' && !tl.cue.autoAdvance) this.mixer.scheduleMusicLevel(level * HOLD_MUSIC_RATIO, at(tl.duration), HOLD_TC);
    this.mixer.scheduleDucking(intervals);
  }

  private enterWaiting(i: number, opts: { keepAudio?: boolean } = {}): void {
    if (!opts.keepAudio) { this.mixer.stop('all', 0.05); this.mixer.resetDucking(); }
    this.index = i;
    this.mode = 'waiting';
    this.playId++;
    this.waitEnteredAt = performance.now();
    if (!opts.keepAudio && this.clock.kind === 'audio') { const c = this.timelines[i].cue; this.mixer.setMusicLevel(c.musicLevel ?? MUSIC_LEVEL[c.kind] ?? 0.6); }
    this.renderNow(performance.now());
  }

  private finishCue(): void {
    const tl = this.timelines[this.index];
    this.enterWaiting(this.index, { keepAudio: true });
    if (tl.cue.autoAdvance && tl.nextIndex >= 0 && !this.capturing) this.playCue(tl.nextIndex);
  }

  // ---------------------------------------------------------------- GPU 中斷

  private onContextLost(): void {
    if (this.mode === 'context_lost') return;
    if (this.mode === 'preparing' || this.mode === 'loading') return; // 開演前：按「準備播放」時重建
    const tl = this.timelines[this.index];
    this.lostReturn = this.mode === 'playing' ? Math.max(0, tl.prevStableIndex) : this.index;
    this.mixer.stop('all', 0.02);
    this.paused = false;
    this.clock.pause();
    this.mode = 'context_lost';
    this.ui.lost.show('顯示卡連線中斷（可能是投影機或螢幕切換）。聲音已停止。請按「下一步」重新建立畫面。');
  }

  private async recover(): Promise<void> {
    if (this.recovering) return;
    this.recovering = true;
    this.ui.lost.show('重新建立畫面中…');
    try {
      await this.stage.rebuild();
      this.clock.resume();
      this.ui.layout();
      this.ui.lost.hide();
      this.enterWaiting(this.lostReturn);
    } catch (err) {
      this.ui.lost.show(`重建失敗：${err instanceof Error ? err.message : String(err)}。請改用分幕影片與靜態題卡。`);
    } finally {
      this.recovering = false;
    }
  }

  // ---------------------------------------------------------------- 每格更新

  start_loop(): void { requestAnimationFrame(this.frame); }

  private frame = (ms: number): void => {
    requestAnimationFrame(this.frame);
    // 休眠偵測：畫面更新中斷超過 4 秒（系統睡眠喚醒）就暫停
    if (this.lastFrameMs && ms - this.lastFrameMs > 4000 && document.visibilityState === 'visible') this.autoPause('sleep');
    this.lastFrameMs = ms;
    if (this.clock instanceof VirtualClock && this.cfg.autostep && this.mode === 'playing') this.clock.advance();
    this.tick();
    if (this.shouldRender(ms)) this.renderNow(ms);
  };

  private tick(): void {
    if (this.mode !== 'playing' || this.paused) return;
    const tl = this.timelines[this.index];
    if (this.clock.now() - this.cueStart >= tl.duration) this.finishCue();
  }

  private shouldRender(ms: number): boolean {
    if (this.mode === 'context_lost' || this.stage.contextLost || !this.timelines.length) return false;
    if (this.capturing) return true;
    let interval = 100; // 等待、暫停：畫面靜止，降低更新率
    if (this.mode === 'playing' && !this.paused) interval = this.lock30 ? 1000 / 30 - 4 : 0;
    else if (this.mode === 'preparing' || (this.mode === 'waiting' && this.index === 0)) interval = 250; // 署名卡待機降載
    return ms - this.lastRenderMs >= interval;
  }

  /** 目前顯示的 cue 時間：播放中＝時鐘；等待中＝該 cue 的最後一格 */
  displayTime(): number {
    const tl = this.timelines[this.index];
    if (!tl) return 0;
    if (this.mode === 'playing') return Math.min(tl.duration, Math.max(0, this.clock.now() - this.cueStart));
    return tl.duration;
  }

  lampsBefore(i: number): number[] {
    const hit = this.lampsCache.get(i);
    if (hit) return hit;
    const out: number[] = [];
    for (let j = 0; j < i; j++) for (const a of this.timelines[j].anims) if (a.name === 'lamp.light') out.push(Number(a.params.index ?? this.timelines[j].cue.lamp ?? 0));
    this.lampsCache.set(i, out);
    return out;
  }

  renderNow(ms: number): void {
    const tl = this.timelines[this.index];
    if (!tl) return;
    const t = this.displayTime();
    const world = evaluateWorld(tl, t, this.lampsBefore(this.index), this.stage.cameraResolver(tl));
    this.lastWorld = world;
    this.stage.apply(world, tl, t, String(this.playId));
    this.ui.update({
      tl, t, world,
      showSubs: this.mode === 'playing',
      placeholder: tl.placeholder && (this.mode === 'playing' || this.mode === 'waiting'),
      paused: this.paused,
    });
    if (!this.stage.contextLost) this.stage.render();
    if (this.mode === 'playing' && this.lastRenderMs) {
      const dt = ms - this.lastRenderMs;
      if (dt > 0 && dt < 500) this.fpsEma = this.fpsEma ? this.fpsEma * 0.9 + (1000 / dt) * 0.1 : 1000 / dt;
    }
    this.lastRenderMs = ms;
  }

  resize(): void {
    const L = this.ui.layout();
    this.stage.resize(L.stage.w, L.stage.h);
    this.renderNow(performance.now());
  }

  // ---------------------------------------------------------------- 設定

  setAvOffset(ms: number): void { this.avOffsetMs = Math.round(ms); saveSettings({ avOffsetMs: this.avOffsetMs }); }
  setLeadIn(ms: number): void { this.leadInMs = Math.max(0, Math.min(2000, Math.round(ms))); saveSettings({ leadInMs: this.leadInMs }); }

  /**
   * 測試用：每個正在播的配音「現在被聽到的檔內秒數」與字幕時間軸的差（毫秒）。
   * 聽到的位置＝AudioContext 時間 − 輸出延遲 − 開始時間＋檔內起點；字幕時間軸＝目前 cue 時間 − 該句起點。
   */
  voiceSync(): { id: string; heard: number; expected: number; diffMs: number }[] {
    const ctx = this.mixer.ctx as (AudioContext & { outputLatency?: number }) | null;
    const tl = this.timelines[this.index];
    if (!ctx || !tl) return [];
    const lat = ctx.outputLatency || ctx.baseLatency || 0;
    const t = this.displayTime();
    const out: { id: string; heard: number; expected: number; diffMs: number }[] = [];
    for (const v of this.mixer.voiceTimings()) {
      if (v.bus !== 'vo') continue;
      const l = tl.lines.find((x) => x.audioId === v.id);
      if (!l) continue;
      const heard = ctx.currentTime - lat - v.when + v.offset;
      if (heard < 0 || t < l.start) continue; // 還沒開始
      const expected = t - l.start;
      out.push({ id: v.id, heard: Math.round(heard * 1000) / 1000, expected: Math.round(expected * 1000) / 1000, diffMs: Math.round((heard - expected) * 1000) });
    }
    return out;
  }
  setLock30(on: boolean): void { this.lock30 = on; saveSettings({ lock30: on }); }
  setQuality(q: Quality): void { this.stage.setQuality(q); saveSettings({ quality: q }); this.resize(); }

  // ---------------------------------------------------------------- 查詢

  phase(): Phase {
    const tl = this.timelines[this.index];
    switch (this.mode) {
      case 'loading': return 'loading';
      case 'preparing': return 'preparing';
      case 'error': return 'error';
      case 'context_lost': return 'context_lost';
      case 'playing': return tl.cue.kind === 'quiz' ? 'quiz_playing' : tl.cue.kind === 'reveal' ? 'reveal_playing' : 'playing';
      case 'waiting': {
        const k = tl.cue.kind;
        if (k === 'title' && this.index === 0) return 'title_idle';
        if (tl.nextIndex < 0) return 'ended';
        if (k === 'quiz') return 'quiz_shown';
        if (k === 'reveal') return 'reveal_waiting';
        const n = this.timelines[tl.nextIndex];
        if (n && n.cue.kind === 'curtain' && n.cue.initialState.stage?.curtain === 'open') return 'final_waiting';
        return 'story_waiting';
      }
      default: return 'error';
    }
  }

  getState(): EngineState {
    const tl = this.timelines[this.index];
    const phase = this.phase();
    const w = this.lastWorld;
    return {
      mode: this.mode, phase, phaseLabel: PHASE_LABEL[phase], paused: this.paused, pauseReason: this.pauseReason,
      cueId: tl?.cue.id ?? null, cueIndex: this.index, kind: tl?.cue.kind ?? null, title: tl?.cue.title ?? '',
      cueTime: Math.round(this.displayTime() * 1000) / 1000, cueDuration: tl?.duration ?? 0,
      revealed: !!w && tl?.cue.kind === 'reveal' && w.quizReveal >= 0.5,
      quizVisible: !!w && w.quizVisible > 0.5,
      lampsLit: w ? w.lamps.map((v, i) => (v >= 0.99 ? i + 1 : 0)).filter(Boolean) : [],
      placeholderAudio: !!tl?.placeholder, activeVoices: this.mixer.activeVoices, voiceIds: this.mixer.activeIds(), voSounding: this.mixer.sounding('vo'),
      subtitle: this.ui.subs.currentText, missingAudio: [...this.missingAudio], castReport: [...this.stage.castReport], set: this.stage.setName,
      actors: [...this.stage.actors.keys()],
      world: w ? { curtain: w.curtain, titleCard: w.titleCard, set: w.set, desat: w.desat, spot: w.spot, light: w.light } : null,
      clock: this.clock.kind, audioState: this.mixer.state, avOffsetMs: this.avOffsetMs, leadInMs: this.leadInMs,
      quality: this.stage.quality, lock30: this.lock30, playId: this.playId,
      ignoredInputs: this.ignoredInputs, ignoredRepeats: this.input.ignoredRepeats, blockedKeys: this.input.blocked,
      lastBlockedKey: this.input.lastBlockedKey, fps: Math.round(this.fpsEma * 10) / 10, contextLost: this.stage.contextLost,
      errors: [...this.errors], warnings: this.validation?.warnings ?? [], gpu: this.stage.gpuInfo,
    };
  }

  getCues(): { id: string; kind: string; title: string; duration: number; placeholder: boolean; next: string | null; prevStable: string | null }[] {
    return this.timelines.map((t) => ({
      id: t.cue.id, kind: t.cue.kind, title: t.cue.title ?? '', duration: t.duration, placeholder: t.placeholder,
      next: t.nextIndex >= 0 ? this.timelines[t.nextIndex].cue.id : null,
      prevStable: t.prevStableIndex >= 0 ? this.timelines[t.prevStableIndex].cue.id : null,
    }));
  }

  // ---------------------------------------------------------------- 擷取（?capture=1）

  /** 擷取：把虛擬時鐘設到目前 cue 的第 t 秒，同步更新並渲染一格 */
  captureSeek(t: number): { t: number; mode: Mode; phase: Phase } {
    if (!(this.clock instanceof VirtualClock)) throw new Error('只有 ?capture=1 才能逐格擷取');
    const tl = this.timelines[this.index];
    this.clock.set(this.cueStart + Math.max(0, t));
    if (t < tl.duration) {
      if (this.mode === 'waiting') this.mode = 'playing'; // 回到播放中（同一次播放，不重設）
      this.tick();
    } else if (this.mode === 'playing') {
      this.finishCue();
    }
    this.renderNow(performance.now());
    return { t: this.displayTime(), mode: this.mode, phase: this.phase() };
  }

  captureStep(frames = 1): { t: number; mode: Mode } {
    if (!(this.clock instanceof VirtualClock)) throw new Error('只有 ?capture=1 才能逐格擷取');
    this.clock.advance(frames);
    this.tick();
    this.renderNow(performance.now());
    return { t: this.displayTime(), mode: this.mode };
  }
}
