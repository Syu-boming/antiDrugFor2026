// 單一時鐘（v1.2 第 18.3 節）：動畫、字幕、嘴型與配音都看同一個時間。
// - AudioClock：現場用。時間＝AudioContext.currentTime − outputLatency ＋ 聲畫偏移。
//   暫停時直接 suspend AudioContext，聲音與畫面一起停在原地。
// - PerformanceClock：沒有音訊裝置（AudioContext 不走）時的退路。
// - VirtualClock：?capture=1 擷取用，以固定步長推進，跟真實時間無關。
//
// 聲畫偏移（毫秒，正值＝畫面提前）：投影機處理影像常延遲 30–100 ms，聲音直接走 3.5mm 沒有延遲，
// 所以讓畫面提前同樣的毫秒數，觀眾看到的嘴型才會對上聲音。

export type ClockKind = 'audio' | 'performance' | 'virtual';

export interface Clock {
  readonly kind: ClockKind;
  /** 舞台時間（秒） */
  now(): number;
  readonly paused: boolean;
  pause(): void;
  resume(): void;
  /** 開新段落時要往後留多少秒，才來得及排程第一個聲音 */
  lead(): number;
  /** 舞台時間 → AudioContext 排程時間 */
  toAudioTime(stageTime: number): number;
}

type Ctx = AudioContext & { outputLatency?: number };

export class AudioClock implements Clock {
  readonly kind = 'audio' as const;
  private _paused = false;
  constructor(private ctx: Ctx, private offsetMs: () => number) {}
  latency(): number { return this.ctx.outputLatency || this.ctx.baseLatency || 0; }
  now(): number { return this.ctx.currentTime - this.latency() + this.offsetMs() / 1000; }
  get paused(): boolean { return this._paused; }
  pause(): void { this._paused = true; void this.ctx.suspend().catch(() => undefined); }
  resume(): void { this._paused = false; void this.ctx.resume().catch(() => undefined); }
  lead(): number { return 0.06 + this.latency() + Math.max(0, -this.offsetMs() / 1000); }
  // 推導：段落起點 S 以舞台時間記錄，台詞 s 秒排在 AudioContext 時間 S＋s，
  // 它會在 outputLatency 之後被聽到，正好是畫面時間走到 S＋s 的時刻（含聲畫偏移）。
  toAudioTime(stageTime: number): number { return stageTime; }
}

export class PerformanceClock implements Clock {
  readonly kind = 'performance' as const;
  private _paused = false;
  private pausedAt = 0;
  private pausedTotal = 0;
  constructor(private offsetMs: () => number, private audioNow: () => number = () => 0) {}
  private raw(): number { return (this._paused ? this.pausedAt : performance.now()) - this.pausedTotal; }
  now(): number { return this.raw() / 1000 + this.offsetMs() / 1000; }
  get paused(): boolean { return this._paused; }
  pause(): void { if (!this._paused) { this._paused = true; this.pausedAt = performance.now(); } }
  resume(): void { if (this._paused) { this._paused = false; this.pausedTotal += performance.now() - this.pausedAt; } }
  lead(): number { return 0.05; }
  toAudioTime(stageTime: number): number { return this.audioNow() + (stageTime - this.now()); }
}

export class VirtualClock implements Clock {
  readonly kind = 'virtual' as const;
  private t = 0;
  private _paused = false;
  /** @param step 固定步長（秒），預設 1/30 */
  constructor(public step = 1 / 30) {}
  now(): number { return this.t; }
  set(t: number): void { this.t = t; }
  advance(frames = 1): void { if (!this._paused) this.t += this.step * frames; }
  get paused(): boolean { return this._paused; }
  pause(): void { this._paused = true; }
  resume(): void { this._paused = false; }
  lead(): number { return 0; }
  toAudioTime(stageTime: number): number { return stageTime; }
}
