// 對白壓低配樂（ducking）的排程規則：純函式，tools/engine-test.mjs 會直接用 Node 執行它做單元測試。
// 這個檔只能用 `import type`。

/**
 * 對白時配樂壓到這個比例（約 −5 dB）。G3 修正第 9 項：台詞比背景約高 15–18 LU、必要旁白句間停頓的背景維持在約 −30 LUFS
 *（review/G3/mix_r1.json 的離線模擬；配樂 music_m4_light 同步改為 v02 −24 LUFS）。
 */
export const DUCK_LEVEL = 0.56;
/** 說話前多久開始壓低（秒）、壓低的時間常數 */
export const DUCK_LEAD = 0.15;
export const DUCK_TC_DOWN = 0.06;
/**
 * 說完後多久回升（秒）、回升的時間常數；相鄰兩句間隔短於 BRIDGE 秒時中間不回升。
 * 同一個配音檔內的句間停頓（例如必要旁白一三句之間 1.3 秒）整段都算說話中，不回升也不再往下壓。
 */
export const DUCK_RELEASE = 0.3;
export const DUCK_TC_UP = 0.25;
export const DUCK_BRIDGE = 0.9;

/** 教師停格（場景 cue 播完、等老師按鍵）時配樂降到基準音量的這個比例（約 −20 dB），時間常數 HOLD_TC 秒：3 秒內 ≤ −35 LUFS（G3 修正第 11 項） */
export const HOLD_MUSIC_RATIO = 0.1;
export const HOLD_TC = 0.6;

export interface DuckStep { at: number; value: number; tc: number }

/**
 * 依台詞區間（AudioContext 時間）排出 setTargetAtTime 步驟。
 * level＝說話時的避讓增益：cue 的 musicDuck（G6 修正第 2 輪；只有少數配樂較大聲的 cue 會寫），省略時用 DUCK_LEVEL。
 * 離線混音 tools/g4_review_pack.py 的 duck_plan 用同一條規則（level＝cue 的 musicDuck）。
 */
export function duckingPlan(intervals: [number, number][], now = 0, level: number = DUCK_LEVEL): DuckStep[] {
  const sorted = [...intervals].sort((a, b) => a[0] - b[0]);
  const out: DuckStep[] = [];
  for (let i = 0; i < sorted.length; i++) {
    const [s, e] = sorted[i];
    out.push({ at: Math.max(now, s - DUCK_LEAD), value: level, tc: DUCK_TC_DOWN });
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
