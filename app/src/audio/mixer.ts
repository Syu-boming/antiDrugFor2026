// 音訊：Web Audio 三條匯流排（對白 vo、音樂 music、音效 sfx）→ 總音量 → 輸出。
// - 對白時配樂自動避讓（壓低）；題目與發獎時配樂很低或靜音（由引擎依 cue 種類設定基準音量）。
// - 切換節點時先停掉舊台詞，避免重疊。
// - 不用 HTMLMediaElement；所有聲音都排在 AudioContext 的時間上，跟畫面同一個時鐘。
import { dataUrlToArrayBuffer } from '../data/packs';
import { duckingPlan } from './ducking';

export type Bus = 'vo' | 'music' | 'sfx';

interface Voice { src: AudioBufferSourceNode; gain: GainNode; bus: Bus; id: string; when: number; offset: number }

export class Mixer {
  readonly ctx: AudioContext | null = null;
  private master: GainNode | null = null;
  private buses: Partial<Record<Bus, GainNode>> = {};
  private musicDuck: GainNode | null = null;
  private buffers = new Map<string, AudioBuffer>();
  private voices = new Set<Voice>();
  private music: Voice | null = null;
  readonly decodeErrors: string[] = [];

  constructor() {
    try {
      const AC: typeof AudioContext | undefined = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!AC) return;
      const ctx = new AC({ latencyHint: 'interactive' });
      this.ctx = ctx;
      this.master = ctx.createGain();
      this.master.connect(ctx.destination);
      for (const b of ['vo', 'music', 'sfx'] as Bus[]) {
        const g = ctx.createGain();
        this.buses[b] = g;
      }
      // 音樂：music 匯流排（基準音量）→ duck（避讓）→ master
      this.musicDuck = ctx.createGain();
      this.buses.music!.connect(this.musicDuck);
      this.musicDuck.connect(this.master);
      this.buses.vo!.connect(this.master);
      this.buses.sfx!.connect(this.master);
      this.buses.music!.gain.value = 0;
    } catch (err) {
      console.warn('[mixer] 無法建立 AudioContext', err);
    }
  }

  get available(): boolean { return this.ctx !== null; }
  get state(): string { return this.ctx?.state ?? 'unavailable'; }
  has(id: string): boolean { return this.buffers.has(id); }
  duration(id: string): number | undefined { return this.buffers.get(id)?.duration; }
  get activeVoices(): number { return this.voices.size; }
  activeIds(): string[] { return [...this.voices].map((v) => v.id); }
  /** 已經開始發聲（排程時間已到、還沒結束）的聲音數；bus 省略＝全部 */
  sounding(bus?: Bus): number {
    const now = this.ctx?.currentTime ?? 0;
    return [...this.voices].filter((v) => (!bus || v.bus === bus) && v.when <= now + 1e-3).length;
  }

  /** 解碼資料包裡的音檔（data URL）；不需要使用者互動，準備畫面就能先做 */
  async decode(id: string, dataUrl: string): Promise<boolean> {
    if (!this.ctx) return false;
    try {
      const buf = await this.ctx.decodeAudioData(dataUrlToArrayBuffer(dataUrl));
      this.buffers.set(id, buf);
      return true;
    } catch (err) {
      this.decodeErrors.push(id);
      console.warn(`[mixer] 音檔解碼失敗 ${id}`, err);
      return false;
    }
  }

  /** 在使用者按下「準備播放」時呼叫，解除瀏覽器的自動播放限制 */
  async unlock(): Promise<boolean> {
    if (!this.ctx) return false;
    try { await this.ctx.resume(); } catch { /* 交給後面判斷 */ }
    return this.ctx.state === 'running';
  }

  /** 在指定的 AudioContext 時間播放一段已解碼的聲音；找不到音檔回傳 false（呼叫端改走暫代模式） */
  playAt(bus: Bus, id: string, when: number, opts: { gain?: number; offset?: number; loop?: boolean } = {}): boolean {
    const ctx = this.ctx;
    const buf = this.buffers.get(id);
    const out = this.buses[bus];
    if (!ctx || !buf || !out) return false;
    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.loop = !!opts.loop;
    const gain = ctx.createGain();
    gain.gain.value = opts.gain ?? 1;
    src.connect(gain).connect(out);
    // 排程時間已經過去時，從對應的位置接著播（例如暫停邊界上的誤差）
    const late = Math.max(0, ctx.currentTime - when);
    const v: Voice = { src, gain, bus, id, when: Math.max(when, ctx.currentTime), offset: (opts.offset ?? 0) + late };
    src.onended = () => { this.voices.delete(v); if (this.music === v) this.music = null; };
    src.start(v.when, v.offset);
    this.voices.add(v);
    if (bus === 'music') this.music = v;
    return true;
  }

  /** 停止某條匯流排（或全部）上的聲音，30 ms 淡出避免爆音 */
  stop(bus: Bus | 'all' = 'all', fade = 0.03): void {
    const ctx = this.ctx;
    if (!ctx) return;
    const now = ctx.currentTime;
    for (const v of [...this.voices]) {
      if (bus !== 'all' && v.bus !== bus) continue;
      try {
        v.gain.gain.cancelScheduledValues(now);
        v.gain.gain.setValueAtTime(v.gain.gain.value, now);
        v.gain.gain.linearRampToValueAtTime(0, now + fade);
        v.src.stop(now + fade + 0.01);
      } catch { /* 已經停了 */ }
      v.src.onended = null;
      this.voices.delete(v);
      if (this.music === v) this.music = null;
    }
  }

  get musicId(): string | null { return this.music?.id ?? null; }

  /**
   * 配樂交叉淡入淡出：在 when 開始把目前的配樂淡出、新的淡入（fade 秒）。id 為 "none" 只淡出。
   * 找不到音檔時回傳 false（呼叫端記為缺檔，照常演出）。
   */
  crossfadeMusic(id: string, when: number, opts: { loop?: boolean; fade?: number; gain?: number; offset?: number } = {}): boolean {
    const ctx = this.ctx;
    if (!ctx) return false;
    const fade = Math.max(0.05, opts.fade ?? 1.5);
    const t = Math.max(when, ctx.currentTime);
    for (const v of [...this.voices]) {
      if (v.bus !== 'music') continue;
      try {
        v.gain.gain.cancelScheduledValues(t);
        v.gain.gain.setValueAtTime(v.gain.gain.value, t);
        v.gain.gain.linearRampToValueAtTime(0, t + fade);
        v.src.stop(t + fade + 0.05);
      } catch { /* 已經停了 */ }
    }
    if (id === 'none') return true;
    const buf = this.buffers.get(id);
    const out = this.buses.music;
    if (!buf || !out) return false;
    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.loop = opts.loop ?? true;
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0, t);
    gain.gain.linearRampToValueAtTime(opts.gain ?? 1, t + fade);
    src.connect(gain).connect(out);
    const late = Math.max(0, ctx.currentTime - when);
    const v: Voice = { src, gain, bus: 'music', id, when: t, offset: ((opts.offset ?? 0) + late) % Math.max(0.01, buf.duration) };
    src.onended = () => { this.voices.delete(v); if (this.music === v) this.music = null; };
    src.start(t, v.offset);
    this.voices.add(v);
    this.music = v;
    return true;
  }

  /** 測試用：每個聲音的排程（AudioContext 開始時間與檔內起點），算「現在聽到檔內第幾秒」 */
  voiceTimings(): { id: string; bus: Bus; when: number; offset: number }[] {
    return [...this.voices].map((v) => ({ id: v.id, bus: v.bus, when: v.when, offset: v.offset }));
  }

  /** 測試用：目前的配樂基準音量與避讓增益 */
  levels(): { musicBus: number; duck: number; master: number } {
    return { musicBus: this.buses.music?.gain.value ?? 0, duck: this.musicDuck?.gain.value ?? 1, master: this.master?.gain.value ?? 0 };
  }

  /** 設定配樂基準音量（劇情約 0.8；題目與發獎 0.06；署名卡待機 0） */
  setMusicLevel(level: number, when?: number, timeConstant = 0.35): void {
    const ctx = this.ctx;
    const g = this.buses.music;
    if (!ctx || !g) return;
    const t = Math.max(ctx.currentTime, when ?? ctx.currentTime);
    g.gain.cancelScheduledValues(t);
    g.gain.setTargetAtTime(level, t, timeConstant);
  }

  /** 在 when 起把配樂基準音量慢慢降到 level（不取消之前的排程；教師停格用） */
  scheduleMusicLevel(level: number, when: number, timeConstant: number): void {
    const ctx = this.ctx;
    const g = this.buses.music;
    if (!ctx || !g) return;
    g.gain.setTargetAtTime(level, Math.max(ctx.currentTime, when), timeConstant);
  }

  /** 依台詞區間排好配樂避讓（排程規則見 ducking.ts 的 duckingPlan，可單獨測試） */
  scheduleDucking(intervals: [number, number][]): void {
    const ctx = this.ctx;
    const d = this.musicDuck;
    if (!ctx || !d) return;
    const now = ctx.currentTime;
    d.gain.cancelScheduledValues(now);
    d.gain.setValueAtTime(d.gain.value, now);
    for (const step of duckingPlan(intervals, now)) d.gain.setTargetAtTime(step.value, step.at, step.tc);
  }

  resetDucking(): void {
    const ctx = this.ctx;
    const d = this.musicDuck;
    if (!ctx || !d) return;
    d.gain.cancelScheduledValues(ctx.currentTime);
    d.gain.setTargetAtTime(1, ctx.currentTime, 0.1);
  }

  setMasterVolume(v: number): void {
    if (this.master && this.ctx) this.master.gain.setTargetAtTime(v, this.ctx.currentTime, 0.05);
  }
}
