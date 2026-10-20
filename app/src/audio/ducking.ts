// 對白壓低配樂（ducking）的排程規則：純函式，tools/engine-test.mjs 會直接用 Node 執行它做單元測試。
// 這個檔只能用 `import type`。

/** 對白時配樂壓到這個比例（約 −10 dB） */
export const DUCK_LEVEL = 0.32;
/** 說話前多久開始壓低（秒）、壓低的時間常數 */
export const DUCK_LEAD = 0.15;
export const DUCK_TC_DOWN = 0.06;
/** 說完後多久回升（秒）、回升的時間常數；相鄰兩句間隔短於 BRIDGE 秒時中間不回升 */
export const DUCK_RELEASE = 0.3;
export const DUCK_TC_UP = 0.25;
export const DUCK_BRIDGE = 0.9;

export interface DuckStep { at: number; value: number; tc: number }

/** 依台詞區間（AudioContext 時間）排出 setTargetAtTime 步驟 */
export function duckingPlan(intervals: [number, number][], now = 0): DuckStep[] {
  const sorted = [...intervals].sort((a, b) => a[0] - b[0]);
  const out: DuckStep[] = [];
  for (let i = 0; i < sorted.length; i++) {
    const [s, e] = sorted[i];
    out.push({ at: Math.max(now, s - DUCK_LEAD), value: DUCK_LEVEL, tc: DUCK_TC_DOWN });
    const next = sorted[i + 1]?.[0];
    if (next === undefined || next - e > DUCK_BRIDGE) out.push({ at: Math.max(now, e + DUCK_RELEASE), value: 1, tc: DUCK_TC_UP });
  }
  return out;
}

/** 依排程算出某時間的避讓增益（模擬 Web Audio 的 setTargetAtTime；測試用） */
export function duckGainAt(plan: DuckStep[], t: number, start = 1): number {
  let v = start;
  let cur = { at: -Infinity, value: start, tc: 1 };
  let from = start;
  for (const step of plan) {
    if (step.at > t) break;
    // 前一段推進到這一步開始
    from = cur.at === -Infinity ? from : cur.value + (from - cur.value) * Math.exp(-(step.at - cur.at) / cur.tc);
    cur = step;
  }
  v = cur.at === -Infinity ? start : cur.value + (from - cur.value) * Math.exp(-(t - cur.at) / cur.tc);
  return v;
}
