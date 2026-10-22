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
//
// G5 全劇（?cues=show）：
// - 換景亮度漸變：要播的 cue 從暗開始（時間軸 enterFade > 0，例如換景）時，先把目前畫面漸暗 PREROLL_SEC 秒（預捲，
//   在 cue 時間 0 之前；擷取時 seek 負的秒數看得到），cue 再從暗漸亮。上一步、章節跳轉換到別的景時（只在即時播放），
//   也是先漸暗 0.6 秒再漸亮 0.6 秒，不會突然由亮轉暗（v1.2 第 17.3 節第 5 條）。
// - 壓縮級別 0／1／2（setCompression）：重建時間軸；播放中設定的話等這段播完才套用。
// - 查核點：記錄開演時間與每個查核點的實際分鐘，算落後秒數與建議的壓縮級別（checkpointReport）。
// - window.__engineShow：章節、壓縮、查核點、景的狀態（教師控制台與測試用；主線之後可併進 window.__engine）。
import type { Cue, CueFile } from '../types/cue';
import { validateCueFile, type ValidationResult } from '../cues/validate';
import { buildTimelines, type CueTimeline } from '../cues/timeline';
import { getPack, loadPackFile, loadPackFiles, type PackManifest } from '../data/packs';
import { AssetStore } from '../data/assets';
import { AudioClock, PerformanceClock, VirtualClock, type Clock } from './clock';
import { evaluateWorld, setsUsed, type WorldState } from './world';
import type { Mixer } from '../audio/mixer';
import type { Stage, Quality } from '../stage/stage';
import type { UI } from '../ui/ui';
import type { InputController } from './input';
import type { LipsyncData } from '../stage/perform';
import { HOLD_MUSIC_RATIO, HOLD_TC } from '../audio/ducking';
import { saveSettings, type Config } from '../config';
import { ease } from '../util/math';

/** 換景漸暗預捲（秒）：要播的 cue 從暗開始時，先把目前畫面漸暗這麼久（≥0.6，v1.2 第 17.3 節） */
export const PREROLL_SEC = 0.6;
/** 上一步、章節跳轉換景時的漸暗／漸亮（秒；只在即時播放） */
export const NAV_FADE_SEC = 0.6;

export type CompressionLevel = 0 | 1 | 2;

export interface ChapterInfo { id: string; title: string; firstCue: string; lastCue: string; cueCount: number; durationSec: number; sets: string[] }

export interface CheckpointStatus {
  cueId: string; label: string; plannedMin: number;
  /** 實際到達的授課分鐘（從片頭第一次按下一步起算；離開該 cue 時記錄，沒離開則用播完時） */
  actualMin: number | null;
  /** 落後秒數（正＝落後、負＝超前） */
  behindSec: number | null;
  escalate: { behindSec: number; level: 1 | 2 } | null;
  /** 落後達到 escalate 門檻 */
  triggered: boolean;
}

/** window.__engineShow：全劇介面（教師控制台與 tools/engine-test.mjs 用） */
export interface ShowAPI {
  chapters(): ChapterInfo[];
  compression(): CompressionLevel;
  setCompression(level: number): CompressionLevel | 'pending';
  checkpoints(): { elapsedSec: number | null; suggested: CompressionLevel; list: CheckpointStatus[] };
  resetShowClock(): void;
  sets(): { active: string; built: number; disposed: number; lastBuildMs: number; liveSetGroups: number; lastSwapMs: number; preparedHits: number; prepared: { name: string; pending: number; compiled: boolean }[] };
}

interface Transition { kind: 'preroll' | 'nav'; fromIndex: number; fromT: number; fromKey: string; start: number; out: number; inn: number; wall: boolean }

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
/** 全劇缺配音時「準備播放」要按第二次確認；第一次之後這段時間內再按視為連按誤觸（毫秒） */
const VO_CONFIRM_GUARD_MS = 800;
/** 換景預先準備：停格時每格最多花這麼久（毫秒；建一個景本身不切開，一格最多建一個） */
const PREFETCH_BUDGET_MS = 6;

/** 依 cue 種類的配樂基準音量：題目與發獎時很低，署名卡待機沒有音樂 */
const MUSIC_LEVEL: Record<Cue['kind'], number> = { title: 0, curtain: 0.8, scene: 0.8, wait: 0.35, quiz: 0.06, reveal: 0.06, lamp: 0.5 };

export interface EngineState {
  mode: Mode; phase: Phase; phaseLabel: string; paused: boolean; pauseReason: string | null;
  cueId: string | null; cueIndex: number; kind: string | null; title: string;
  cueTime: number; cueDuration: number; revealed: boolean; quizVisible: boolean; lampsLit: number[];
  placeholderAudio: boolean; activeVoices: number; voiceIds: string[]; voSounding: number; subtitle: string;
  missingAudio: string[]; castReport: string[]; set: string; actors: string[];
  world: { curtain: number; titleCard: number; set: number; desat: number; spot: number; light: number; dim: number } | null;
  clock: string; audioState: string; avOffsetMs: number; leadInMs: number; quality: Quality; lock30: boolean; playId: number;
  ignoredInputs: number; ignoredRepeats: number; blockedKeys: number; lastBlockedKey: string | null;
  fps: number; contextLost: boolean; errors: string[]; warnings: string[]; gpu: string;
  /** G5 全劇：段落、章節名、壓縮級別、建議級別、開演後秒數、這段的換景漸亮秒數、目前的預捲秒數、舞台調暗 */
  segment: string | null; chapter: string; compression: CompressionLevel; suggestedCompression: CompressionLevel;
  showElapsedSec: number | null; enterFade: number; prerollSec: number; dim: number;
  /** G6：缺配音的台詞編號（用暫代音訊）；全劇模式缺配音時「準備播放」要按第二次確認（voConfirmPending＝已按第一次、等確認） */
  missingVo: string[]; voConfirmPending: boolean;
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
  /** 缺配音的台詞（暫代音訊）；全劇模式要老師再按一次「準備播放」確認 */
  missingVo: string[] = [];
  /** 缺配音確認：第一次按「準備播放」的時間（0＝還沒按） */
  private voConfirmAt = 0;
  validation: ValidationResult | null = null;
  errors: string[] = [];
  avOffsetMs: number;
  /** 每段開頭的靜音（毫秒；HDMI 吞音時加長） */
  leadInMs: number;
  lock30: boolean;
  private lastWorld: WorldState | null = null;
  /** 換景漸暗（預捲或上一步、章節跳轉） */
  private trans: Transition | null = null;
  compression: CompressionLevel = 0;
  private pendingCompression: CompressionLevel | null = null;
  private showStartMs: number | null = null;
  private cpLog = new Map<string, { reachedMs?: number; leftMs?: number }>();

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
    const api: ShowAPI = {
      chapters: () => this.chapters(),
      compression: () => this.compression,
      setCompression: (l) => this.setCompression(l),
      checkpoints: () => this.checkpointReport(),
      resetShowClock: () => { this.showStartMs = null; this.cpLog.clear(); },
      sets: () => ({ active: this.stage.setName, built: this.stage.setStats.built, disposed: this.stage.setStats.disposed, lastBuildMs: Math.round(this.stage.setStats.lastBuildMs), liveSetGroups: this.stage.liveSetGroups,
        lastSwapMs: Math.round(this.stage.setStats.lastSwapMs * 10) / 10, preparedHits: this.stage.setStats.preparedHits, prepared: this.stage.preparedSets }),
    };
    (window as unknown as { __engineShow?: ShowAPI }).__engineShow = api;
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

      this.timelines = buildTimelines(file, (id) => this.mixer.duration(id), { compression: this.compression });
      this.idIndex = new Map(this.timelines.map((t) => [t.cue.id, t.index]));
      this.lampsCache.clear();
      const voTotal = file.cues.reduce((n, c) => n + c.lines.length, 0);
      const voReal = this.timelines.reduce((n, t) => n + t.lines.filter((l) => !l.placeholder).length, 0);
      this.missingVo = this.timelines.flatMap((t) => t.lines.filter((l) => l.placeholder).map((l) => l.line.id));
      this.voConfirmAt = 0;
      const voConfirm = this.needsVoConfirm();
      this.index = 0;
      this.mode = 'preparing';
      this.renderNow(performance.now());
      this.ui.ready.setStatus([
        { label: 'cue 檔', value: `${file.title}（${file.cues.length} 個 cue）`, ok: true },
        voConfirm
          ? { label: '配音', value: `缺 ${voTotal - voReal} 句配音（這些句子只有字幕、沒有聲音）：${this.missingVo.slice(0, 6).join('、')}${this.missingVo.length > 6 ? '…' : ''}`, ok: false }
          : { label: '配音', value: voReal === voTotal ? `${voReal} 句全部就緒` : `${voReal}／${voTotal} 句有音檔，其餘用暫代音訊`, ok: voReal === voTotal ? true : null },
        { label: '音訊', value: this.mixer.available ? `可用（已解碼 ${decoded} 個音檔）` : '無法建立音訊（只顯示字幕）', ok: this.mixer.available },
        { label: '配樂音效', value: this.missingAudio.length ? `缺 ${this.missingAudio.length} 個檔（照常演出、該處無聲）：${this.missingAudio.join('、')}` : '全部就緒', ok: this.missingAudio.length ? null : true },
        ...(file.segments?.length ? [{ label: '全劇', value: `${file.segments.length} 段：${file.segments.map((sg) => sg.title).join('、')}；景 ${[...new Set(this.timelines.map((t) => t.set))].join('、')}`, ok: true }] : []),
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
    // 全劇缺配音（例如複製交付資料夾時漏了檔、重新打包時少了音檔）：第一次按只顯示「缺 N 句配音」，再按一次才開演；
    // 配樂、音效缺檔照常演出（只列在準備畫面）
    if (this.needsVoConfirm()) {
      const now = performance.now();
      if (!this.voConfirmAt) { this.voConfirmAt = now; this.ui.ready.confirmMissingVo(this.missingVo.length); return; }
      if (now - this.voConfirmAt < VO_CONFIRM_GUARD_MS) { this.ignoredInputs++; return; }
    }
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

  /** 全劇模式（?cues=show）缺任何配音時要老師確認；擷取與自動開始（工具、測試）不問 */
  private needsVoConfirm(): boolean {
    return this.cfg.cues === 'show' && !this.cfg.capture && !this.cfg.autostart && this.missingVo.length > 0;
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
        this.stage.apply(world, tl, t, `warm#${tl.index}`, { keepSet: true });
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
    // 查核點與開演時間：從片頭待機第一次按下一步＝開演；離開查核點 cue 時記錄
    const cur = this.timelines[this.index];
    if (this.showStartMs === null && cur?.cue.kind === 'title' && this.mode === 'waiting' && i !== this.index) this.showStartMs = performance.now();
    if (cur?.cue.checkpoint && this.mode === 'waiting' && i !== this.index) { const e = this.cpLog.get(cur.cue.id) ?? {}; e.leftMs ??= performance.now(); this.cpLog.set(cur.cue.id, e); }
    // 換景漸暗預捲：要播的 cue 從暗開始，而目前畫面布幕開著、還沒暗 → 先把目前這一格漸暗 PREROLL_SEC 秒
    const fw = this.lastWorld;
    const pre = tl.enterFade > 0 && fw && fw.curtain > 0.01 && fw.dim < 0.99 && this.timelines.length ? PREROLL_SEC : 0;
    const from = { fromIndex: this.index, fromT: this.displayTime(), fromKey: String(this.playId) };
    this.mixer.stop('vo');
    this.mixer.stop('sfx');
    this.index = i;
    this.playId++;
    this.mode = 'playing';
    // 預捲時舊的一格繼續用舊的模擬狀態（不重設，換到新 cue 時 PuppetDirector 會自己重設）
    if (!pre) this.stage.director.reset();
    if (this.clock instanceof VirtualClock) this.cueStart = this.clock.now() + pre;
    else {
      // 瀏覽器在背景時可能把 AudioContext 停掉；按鍵當下恢復
      if (this.clock.kind === 'audio' && this.mixer.ctx && this.mixer.ctx.state !== 'running') void this.mixer.ctx.resume();
      // 每段開頭的靜音（HDMI 吞音時由教師選單加長）：畫面停在第一格、聲音一起延後
      this.cueStart = this.clock.now() + pre + this.clock.lead() + this.leadInMs / 1000;
    }
    this.trans = pre ? { kind: 'preroll', ...from, start: this.cueStart - pre - (this.clock instanceof VirtualClock ? 0 : this.clock.lead() + this.leadInMs / 1000), out: pre, inn: 0, wall: false } : null;
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
    else if (!music && !this.mixer.musicId && !tl.music.some((m) => m.at < 0.05)) {
      // 上一步、章節跳轉後沒有配樂在播：補上照流程這時候應該在播的循環配樂（往前找最近一次的配樂設定）
      const bg = this.effectiveMusic(tl.index);
      if (bg) this.mixer.crossfadeMusic(bg.id, at(0), { loop: true, fade: 1.0, gain: bg.gain });
    }
    for (const m of tl.music) this.mixer.crossfadeMusic(m.id, at(m.at), { loop: m.loop, fade: m.fade, gain: m.gain, offset: m.offset });
    const level = tl.cue.musicLevel ?? MUSIC_LEVEL[tl.cue.kind] ?? 0.6;
    this.mixer.setMusicLevel(level, at(0));
    // 教師停格：劇情段落播完、停住等老師時，配樂慢慢降到約 −20 dB（3 秒內 ≤ −35 LUFS）
    if (tl.cue.kind === 'scene' && !tl.cue.autoAdvance) this.mixer.scheduleMusicLevel(level * HOLD_MUSIC_RATIO, at(tl.duration), HOLD_TC);
    this.mixer.scheduleDucking(intervals);
  }

  /** 照流程在第 i 個 cue 開始時應該在播的循環配樂（往前找最近的 music 事件或 audioId；一次播完的曲子、"none" 都算沒有） */
  private effectiveMusic(i: number): { id: string; gain: number } | null {
    for (let j = i - 1; j >= 0; j--) {
      const t = this.timelines[j];
      const last = t.music[t.music.length - 1];
      if (last) return last.id !== 'none' && last.loop ? { id: last.id, gain: last.gain } : null;
      const a = t.cue.audioId;
      if (a === 'none') return null;
      if (a) return (t.cue.musicLoop ?? true) ? { id: a, gain: 1 } : null;
    }
    return null;
  }

  private enterWaiting(i: number, opts: { keepAudio?: boolean } = {}): void {
    if (!opts.keepAudio) { this.mixer.stop('all', 0.05); this.mixer.resetDucking(); }
    // 上一步、章節跳轉到別的景（布幕開著）：即時播放時先漸暗再漸亮（不突然由亮轉暗）
    const fw = this.lastWorld;
    const from = { fromIndex: this.index, fromT: this.displayTime(), fromKey: String(this.playId) };
    const target = this.timelines[i];
    this.trans = null;
    if (!opts.keepAudio && !this.capturing && fw && target && fw.curtain > 0.01 && fw.dim < 0.99 && target.endSet !== this.stage.setName) {
      this.trans = { kind: 'nav', ...from, start: performance.now() / 1000, out: NAV_FADE_SEC, inn: NAV_FADE_SEC, wall: true };
    }
    this.index = i;
    this.mode = 'waiting';
    this.playId++;
    this.waitEnteredAt = performance.now();
    if (this.pendingCompression !== null) this.applyCompression(this.pendingCompression);
    if (!opts.keepAudio && this.clock.kind === 'audio') { const c = this.timelines[i].cue; this.mixer.setMusicLevel(c.musicLevel ?? MUSIC_LEVEL[c.kind] ?? 0.6); }
    this.renderNow(performance.now());
    this.prefetchIdle = false;
    // 擷取模式：停格當下就把下一段的景準備好（虛擬時鐘，不分格；和即時播放走同一條換景路徑）
    if (this.capturing) this.prefetch(Infinity);
  }

  /** 換景預先準備已做完（這次停格不用再呼叫 stage.prepareSets） */
  private prefetchIdle = false;
  /** renderNow 次數（每格判斷這一格有沒有重畫） */
  private renderCount = 0;

  /**
   * 換景預先準備（G6 效能修正）：停格等老師時（不在上一步、章節跳轉的漸變中），把按下一步要播的 cue 會用到的景
   * 先建好、上傳貼圖、編譯著色器（stage.prepareSets；預備景不在場景裡，畫面不變）。換景那一格只要換上，不卡頓。
   * @param budget 這一格最多花幾毫秒（Infinity＝一次做完）
   */
  private prefetch(budget: number): void {
    if (this.prefetchIdle || this.mode !== 'waiting' || this.stage.contextLost || this.transActive()) return;
    const tl = this.timelines[this.index];
    const nx = tl && tl.nextIndex >= 0 ? this.timelines[tl.nextIndex] : undefined;
    const busy = this.stage.prepareSets(nx ? setsUsed(nx) : [], performance.now() + budget);
    if (!busy) this.prefetchIdle = true;
  }

  private finishCue(): void {
    const tl = this.timelines[this.index];
    if (tl.cue.checkpoint) { const e = this.cpLog.get(tl.cue.id) ?? {}; e.reachedMs ??= performance.now(); this.cpLog.set(tl.cue.id, e); }
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
    const renders = this.renderCount;
    this.tick();
    if (this.shouldRender(ms)) this.renderNow(ms);
    // 換景預先準備只用沒有重畫的格（停格時每 100 ms 才重畫一次）：大張貼圖上傳不和重畫擠在同一格
    if (!this.capturing && this.renderCount === renders) this.prefetch(PREFETCH_BUDGET_MS);
  };

  private tick(): void {
    if (this.mode !== 'playing' || this.paused) return;
    const tl = this.timelines[this.index];
    if (this.clock.now() - this.cueStart >= tl.duration) this.finishCue();
  }

  private shouldRender(ms: number): boolean {
    if (this.mode === 'context_lost' || this.stage.contextLost || !this.timelines.length) return false;
    if (this.capturing) return true;
    if (this.trans && this.transActive()) return true; // 換景漸暗中：每格都畫
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

  /** 換景漸暗是否還在進行（預捲：時鐘還沒走到 cue 開始；上一步：漸暗＋漸亮還沒完） */
  private transActive(): boolean {
    const tr = this.trans;
    if (!tr) return false;
    const el = (tr.wall ? performance.now() / 1000 : this.clock.now()) - tr.start;
    return el < tr.out + tr.inn;
  }

  /** 漸暗中的舊畫面（上一個 cue 的那一格，dim 疊上漸暗進度） */
  private renderFrom(tr: Transition, dim: number): void {
    const tl = this.timelines[tr.fromIndex];
    if (!tl) return;
    const world = evaluateWorld(tl, tr.fromT, this.lampsBefore(tr.fromIndex), this.stage.cameraResolver(tl));
    world.dim = Math.max(world.dim, dim);
    this.lastWorld = world;
    this.stage.apply(world, tl, tr.fromT, tr.fromKey);
    this.ui.update({ tl, t: tr.fromT, world, showSubs: false, placeholder: false, paused: this.paused });
    if (!this.stage.contextLost) this.stage.render();
  }

  renderNow(ms: number): void {
    const tl = this.timelines[this.index];
    if (!tl) return;
    this.renderCount++;
    let extraDim = 0;
    const tr = this.trans;
    if (tr) {
      const el = (tr.wall ? performance.now() / 1000 : this.clock.now()) - tr.start;
      // 1e-6：虛擬時鐘在 cue 第 0 秒時 el 可能因浮點誤差差一點點，不能還停在預捲
      if (el < tr.out - 1e-6 && (tr.kind === 'nav' || this.mode === 'playing')) { this.renderFrom(tr, ease('sine', el / tr.out)); this.lastRenderMs = ms; return; }
      if (tr.kind === 'nav') {
        if (el < tr.out + tr.inn) extraDim = 1 - ease('sine', (el - tr.out) / tr.inn);
        else this.trans = null;
      }
    }
    const t = this.displayTime();
    const world = evaluateWorld(tl, t, this.lampsBefore(this.index), this.stage.cameraResolver(tl));
    if (extraDim > 0) world.dim = Math.max(world.dim, extraDim);
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
      world: w ? { curtain: w.curtain, titleCard: w.titleCard, set: w.set, desat: w.desat, spot: w.spot, light: w.light, dim: Math.round(w.dim * 1000) / 1000 } : null,
      clock: this.clock.kind, audioState: this.mixer.state, avOffsetMs: this.avOffsetMs, leadInMs: this.leadInMs,
      quality: this.stage.quality, lock30: this.lock30, playId: this.playId,
      ignoredInputs: this.ignoredInputs, ignoredRepeats: this.input.ignoredRepeats, blockedKeys: this.input.blocked,
      lastBlockedKey: this.input.lastBlockedKey, fps: Math.round(this.fpsEma * 10) / 10, contextLost: this.stage.contextLost,
      errors: [...this.errors], warnings: this.validation?.warnings ?? [], gpu: this.stage.gpuInfo,
      segment: tl?.cue.segment ?? null, chapter: this.file?.segments?.find((sg) => sg.id === tl?.cue.segment)?.title ?? '',
      compression: this.compression, suggestedCompression: this.checkpointReport().suggested,
      showElapsedSec: this.showStartMs === null ? null : Math.round((performance.now() - this.showStartMs) / 100) / 10,
      enterFade: tl?.enterFade ?? 0, prerollSec: this.trans?.kind === 'preroll' && this.mode === 'playing' ? this.trans.out : 0,
      dim: w ? Math.round(w.dim * 1000) / 1000 : 0,
      missingVo: [...this.missingVo], voConfirmPending: this.mode === 'preparing' && this.voConfirmAt > 0,
    };
  }

  getCues(): {
    id: string; kind: string; title: string; duration: number; placeholder: boolean; next: string | null; prevStable: string | null;
    segment: string | null; chapter: string; set: string; enterFade: number; compression: number; skipped: boolean; droppedLines: string[];
    checkpoint: Cue['checkpoint']; teacherNote: string; quiz: { qid: string; number: number; answer: number } | null; lamp: number | null; lines: number;
  }[] {
    const segTitle = new Map((this.file?.segments ?? []).map((sg) => [sg.id, sg.title]));
    return this.timelines.map((t) => ({
      id: t.cue.id, kind: t.cue.kind, title: t.cue.title ?? '', duration: t.duration, placeholder: t.placeholder,
      next: t.nextIndex >= 0 ? this.timelines[t.nextIndex].cue.id : null,
      prevStable: t.prevStableIndex >= 0 ? this.timelines[t.prevStableIndex].cue.id : null,
      segment: t.cue.segment ?? null, chapter: segTitle.get(t.cue.segment ?? '') ?? '', set: t.set, enterFade: t.enterFade,
      compression: t.cue.compression, skipped: t.skipped, droppedLines: [...t.droppedLines],
      checkpoint: t.cue.checkpoint, teacherNote: t.cue.teacherNote,
      quiz: t.cue.kind === 'quiz' || t.cue.kind === 'reveal' ? (t.quiz ? { qid: t.quiz.qid, number: t.quiz.number, answer: t.quiz.answer } : null) : null,
      lamp: t.cue.lamp ?? null, lines: t.lines.length,
    }));
  }

  /** 章節（全劇＝各段落；一般 cue 檔＝一章） */
  chapters(): ChapterInfo[] {
    const segs = this.file?.segments;
    const groups = segs?.length
      ? segs.map((sg) => ({ id: sg.id, title: sg.title, ids: sg.cueIds }))
      : [{ id: this.file?.id ?? '', title: this.file?.title ?? '', ids: this.timelines.map((t) => t.cue.id) }];
    return groups.map((g) => {
      const tls = g.ids.map((id) => this.timelines[this.idIndex.get(id) ?? -1]).filter(Boolean);
      return {
        id: g.id, title: g.title, firstCue: g.ids[0], lastCue: g.ids[g.ids.length - 1], cueCount: g.ids.length,
        durationSec: Math.round(tls.filter((t) => !t.skipped).reduce((n, t) => n + t.duration, 0) * 10) / 10,
        sets: [...new Set(tls.map((t) => t.set))],
      };
    });
  }

  /** 壓縮級別：播放中設定的話等這段播完才套用（回傳 'pending'） */
  setCompression(level: number): CompressionLevel | 'pending' {
    const L = (Math.max(0, Math.min(2, Math.round(Number(level) || 0)))) as CompressionLevel;
    if (this.mode === 'playing') { this.pendingCompression = L; return 'pending'; }
    this.applyCompression(L);
    return L;
  }

  private applyCompression(L: CompressionLevel): void {
    this.pendingCompression = null;
    const changed = L !== this.compression;
    this.compression = L;
    if (!changed || !this.file) return;
    this.timelines = buildTimelines(this.file, (id) => this.mixer.duration(id), { compression: L });
    this.idIndex = new Map(this.timelines.map((t) => [t.cue.id, t.index]));
    this.lampsCache.clear();
    this.stage.resetCaches();
    if (this.mode === 'waiting') this.renderNow(performance.now());
  }

  /** 查核點：預定分鐘、實際分鐘、落後秒數、建議壓縮級別（時長估算_v03.md 第 5 節的門檻寫在 cue 的 checkpoint.escalate） */
  checkpointReport(): { elapsedSec: number | null; suggested: CompressionLevel; list: CheckpointStatus[] } {
    const start = this.showStartMs;
    let suggested: CompressionLevel = 0;
    const list: CheckpointStatus[] = this.timelines.filter((t) => t.cue.checkpoint).map((t) => {
      const cp = t.cue.checkpoint!;
      const log = this.cpLog.get(t.cue.id);
      const at = log?.leftMs ?? log?.reachedMs;
      const actualMin = start !== null && at !== undefined ? (at - start) / 60000 : null;
      const behindSec = actualMin === null ? null : Math.round((actualMin - cp.atMinute) * 60);
      const triggered = !!cp.escalate && behindSec !== null && behindSec >= cp.escalate.behindSec;
      if (triggered && cp.escalate!.level > suggested) suggested = cp.escalate!.level;
      return { cueId: t.cue.id, label: cp.label, plannedMin: cp.atMinute, actualMin: actualMin === null ? null : Math.round(actualMin * 100) / 100, behindSec, escalate: cp.escalate ?? null, triggered };
    });
    return { elapsedSec: start === null ? null : Math.round((performance.now() - start) / 100) / 10, suggested, list };
  }

  // ---------------------------------------------------------------- 擷取（?capture=1）

  /** 擷取：把虛擬時鐘設到目前 cue 的第 t 秒，同步更新並渲染一格 */
  captureSeek(t: number): { t: number; mode: Mode; phase: Phase } {
    if (!(this.clock instanceof VirtualClock)) throw new Error('只有 ?capture=1 才能逐格擷取');
    const tl = this.timelines[this.index];
    // 負的秒數＝換景漸暗預捲（只有這次播放有預捲時）
    const pre = this.trans?.kind === 'preroll' ? this.trans.out : 0;
    this.clock.set(this.cueStart + Math.max(-pre, t));
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
