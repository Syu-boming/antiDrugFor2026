// 音訊：Web Audio 三條匯流排（對白 vo、音樂 music、音效 sfx）→ 總音量 → 輸出。
// - 對白時配樂自動避讓（壓低）；題目與發獎時配樂很低或靜音（由引擎依 cue 種類設定基準音量）。
// - 切換節點時先停掉舊台詞，避免重疊。
// - 不用 HTMLMediaElement；所有聲音都排在 AudioContext 的時間上，跟畫面同一個時鐘。
import { dataUrlToArrayBuffer } from '../data/packs';

export type Bus = 'vo' | 'music' | 'sfx';

interface Voice { src: AudioBufferSourceNode; gain: GainNode; bus: Bus; id: string }

/** 對白時配樂壓到這個比例（約 -10 dB） */
const DUCK_LEVEL = 0.32;

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
    const v: Voice = { src, gain, bus, id };
    src.onended = () => { this.voices.delete(v); if (this.music === v) this.music = null; };
    // 排程時間已經過去時，從對應的位置接著播（例如暫停邊界上的誤差）
    const late = Math.max(0, ctx.currentTime - when);
    src.start(Math.max(when, ctx.currentTime), (opts.offset ?? 0) + late);
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

  /** 設定配樂基準音量（劇情約 0.8；題目與發獎 0.06；署名卡待機 0） */
  setMusicLevel(level: number, when?: number, timeConstant = 0.35): void {
    const ctx = this.ctx;
    const g = this.buses.music;
    if (!ctx || !g) return;
    const t = Math.max(ctx.currentTime, when ?? ctx.currentTime);
    g.gain.cancelScheduledValues(t);
    g.gain.setTargetAtTime(level, t, timeConstant);
  }

  /** 依台詞區間排好配樂避讓：說話前 0.15 秒壓低，說完 0.3 秒後回升（相鄰句子之間不回升） */
  scheduleDucking(intervals: [number, number][]): void {
    const ctx = this.ctx;
    const d = this.musicDuck;
    if (!ctx || !d) return;
    const now = ctx.currentTime;
    d.gain.cancelScheduledValues(now);
    d.gain.setValueAtTime(d.gain.value, now);
    const sorted = [...intervals].sort((a, b) => a[0] - b[0]);
    for (let i = 0; i < sorted.length; i++) {
      const [s, e] = sorted[i];
      d.gain.setTargetAtTime(DUCK_LEVEL, Math.max(now, s - 0.15), 0.06);
      const nextStart = sorted[i + 1]?.[0];
      if (nextStart === undefined || nextStart - e > 0.9) d.gain.setTargetAtTime(1, Math.max(now, e + 0.3), 0.25);
    }
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
