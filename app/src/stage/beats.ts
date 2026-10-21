// 表演節拍表（純資料＋純函式，不 import three）：puppet.waveTry 與 puppet.kneeTug 各拍的秒數。
// perform.ts 用它驅動紙偶；tools/g4_review_pack.mjs 用同一份資料在 8 格／秒條帶上標出時間點，
// 所以「畫面做了什麼」與「驗收包標示的時間」永遠一致。
//
// G4 修正第 1 輪（第 17、18 項）：
// waveTry  想揮手：臉先換成 X2（想打招呼：微笑＋眉抬）→ 手在線還鬆垂時自己抬到胸口高度 → 揮 2 下（≥ 0.6 秒）
//          → 線繃直（音效）→ 手被拉偏 → 至少 4 格（≥ 0.15 秒）之後才換困惑臉。
// kneeTug  想站起：臀部離開凳子到半站 → 停在半站（≥ 0.5 秒）→ 膝前線繃緊（音效）→ 膝蓋被提起、腳離地
//          → 軀幹晃 1 次（阻尼大、擺幅漸小，不重複抖動）→ 近側手（B 側）扶住桌邊並停住 → 身體往下沉到半站（sit 0.55）。
//
// G4 修正第 2 輪（第 6、7 項）：線繃直改成 0.12 秒內拉直；站起的坐姿程度 1 → 0.25（臀部離凳 ≥ 25 px）、停 0.6 秒，扶桌後沉回 0.55。

/** 想揮手的節拍（秒，從動畫起點算） */
export const WAVE_TRY = {
  /** 臉換 X2（head_greet） */
  greet: 0,
  /** 手開始自己抬起（線還鬆垂） */
  raiseStart: 0.25,
  /** 手抬到胸口高度（0.9 秒：手臂慢慢掃過，光敏細格每秒變化 ≤ 3 次） */
  raiseEnd: 1.15,
  /** 揮手（2 下，每秒 1.4 下：光敏細格分析下手掃過的小區域每秒變化 ≤ 3 次） */
  waveStart: 1.15,
  waveEnd: 2.58,
  waveHz: 1.4,
  /** 線繃直（張力 0.2 → 1；同時放繃線音效）：0.12 秒內從鬆垂弧拉成直線（G4 修正第 2 輪第 6 項） */
  tautStart: 2.63,
  tautEnd: 2.75,
  /** 手被拉偏（往 A 側、略往上） */
  pullStart: 2.93,
  pullEnd: 3.68,
  /** 換困惑臉（＝手開始被拉偏後 0.4 秒，≥ 4 格） */
  confused: 3.33,
  /** 建議的動畫長度 */
  duration: 3.8,
} as const;

/** 想站起的節拍（秒，從動畫起點算） */
export const KNEE_TUG = {
  /** 臀部離開凳子，起身到半站（坐姿程度減少 riseDepth；G4 修正第 2 輪第 7 項：臀部離凳 ≥ 25 px） */
  riseStart: 0,
  riseEnd: 0.5,
  riseDepth: 0.75,
  /** 停在半站（riseEnd → tautStart 0.6 秒） */
  /** 膝前線繃緊（張力 0.2 → 1；同時放繃線音效）：0.12 秒內拉成直線 */
  tautStart: 1.1,
  tautEnd: 1.22,
  /** 膝蓋被提起、腳離地 */
  liftStart: 1.4,
  liftEnd: 1.9,
  /** 軀幹被帶得晃一下（推力起訖；之後由阻尼大的彈簧回正） */
  swayStart: 1.45,
  swayPeak: 1.75,
  swayEnd: 2.2,
  /** 近側手扶住桌邊並停住 */
  grabStart: 1.95,
  grabEnd: 2.6,
  /** 扶住桌邊後身體往下沉一點，停在 a2_c004 的 pulled_half 半站（坐姿程度 0.55） */
  settleStart: 2.1,
  settleEnd: 2.9,
  settleSit: 0.55,
  /** 建議的動畫長度 */
  duration: 3.4,
} as const;

export interface BeatMark { label: string; t: number }

/** 動畫在 cue 內的節拍時間點（驗收包條帶標示用） */
export function beatMarks(name: string, start: number): BeatMark[] {
  if (name === 'puppet.waveTry') {
    const W = WAVE_TRY;
    return [
      { label: '臉換 X2（想打招呼）', t: start + W.greet },
      { label: '手自己抬起（線還鬆）', t: start + W.raiseStart },
      { label: '揮手 2 下', t: start + W.waveStart },
      { label: '線繃直＋音效', t: start + W.tautStart },
      { label: '手被拉偏', t: start + W.pullStart },
      { label: '換困惑臉', t: start + W.confused },
    ];
  }
  if (name === 'puppet.kneeTug') {
    const K = KNEE_TUG;
    return [
      { label: '臀部離凳、起身', t: start + K.riseStart },
      { label: '停在半站', t: start + K.riseEnd },
      { label: '膝前線繃緊＋音效', t: start + K.tautStart },
      { label: '膝蓋被提起', t: start + K.liftStart },
      { label: '軀幹晃一下', t: start + K.swayStart },
      { label: '手扶住桌邊', t: start + K.grabStart },
    ];
  }
  return [];
}
