// 舞台層序規則（G4 後凍結）：
// - 世界座標：x 向右、y 向上、z 朝向觀眾；地面 y=0；單位約等於舞台上的「一尺」，中景 1 單位 ≈ 140 px@1080p。
// - 每一層有固定的 z 深度與 renderOrder 基準；同一層內的紙片以 Z_STEP 的微小間距＋renderOrder 遞增排前後，
//   避免共平面閃爍。刀切邊紙片用 alphaTest 並寫入深度；半透明（和紙、光錐、影子）不寫深度，只靠 renderOrder。
// - 相機一律長焦透視（垂直視角約 20°），正交相機只給介面疊層用。

export const Z_STEP = 0.01;

export const LAYER = {
  backdrop: { z: -5.0, order: 0 },
  far: { z: -3.2, order: 100 },
  mid: { z: -0.9, order: 200 },
  actors: { z: 0.0, order: 300 },
  /** 每個角色占 20 個 renderOrder，部件在角色內再依 z 序遞增 */
  actorStride: 20,
  strings: { order: 390 },
  fore: { z: 2.4, order: 400 },
  curtain: { z: 4.0, order: 500 },
  proscenium: { z: 4.35, order: 600 },
} as const;

/** 舞台開口（台口）尺寸 */
export const STAGE_OPENING = { width: 15.6, height: 8.8, centerY: 4.3 };

export interface CameraPreset { pos: [number, number, number]; target: [number, number, number]; fov: number }

/** 相機預設（G4 後凍結）；cue 以名稱引用 */
export const CAMERA_PRESETS: Record<string, CameraPreset> = {
  /** 大全景：看得到台口與布幕 */
  wide: { pos: [0, 4.5, 31], target: [0, 4.3, 0], fov: 20 },
  /** 中景：兩個角色同框 */
  medium: { pos: [0.3, 3.3, 22], target: [0.3, 2.75, 0], fov: 20 },
  /** 沿操偶線看：手腕 */
  string_wrist: { pos: [-2.4, 3.3, 15.5], target: [-2.6, 2.9, 0], fov: 20 },
  /** 沿操偶線看：膝蓋 */
  string_knee: { pos: [-1.9, 2.2, 15.5], target: [-2.0, 1.7, 0], fov: 20 },
  /** 沿操偶線往上：線延伸出畫面 */
  string_up: { pos: [-2.3, 4.2, 16], target: [-2.4, 4.45, 0], fov: 20 },
  /** 題卡模式：鏡頭後拉露出台口 */
  quiz: { pos: [0, 4.6, 36], target: [0, 4.4, 0], fov: 20 },

  // ---- G4 燈籠店（workshop_g4）：阿樂叔叔坐在工作台左端（x≈−2.4），小晴、小宇在右側（安全方位）
  /** 開幕後的大全景（台口內的整個工作室，景片立起時用） */
  g4_wide: { pos: [0, 3.6, 27], target: [0, 3.2, 0], fov: 20 },
  /**
   * 代表鏡頭固定中景：三人同框。G4 修正第 26 項：鏡頭比第一版低 0.82（畫面內容上移約 150 px），
   * 地面在 1080p 的 y≈783，阿樂叔叔的腳和膝蓋都在字幕底板（兩行時上緣 y≈810）之上。
   */
  g4_mid: { pos: [-0.35, 1.53, 16.4], target: [-0.35, 1.3, 0], fov: 20 },
  /** 線落下時微上搖：讓線往上延伸出畫面（孩子仍完整入鏡） */
  g4_mid_up: { pos: [-0.5, 1.95, 16.4], target: [-0.62, 1.86, 0], fov: 20 },
  /**
   * 停格前慢推（a2_c002 結尾＝a2_c004 起點）。G4 修正第 24 項：只推近約 11%，兩個孩子的頭和上半身留在 90% 安全框內、
   * 阿樂叔叔被拉開的手也在畫面內；地面在 y≈790，腳與膝蓋在字幕底板之上（第 26 項）；線寬約 9 px（規格 6–10）。
   */
  g4_push: { pos: [-0.15, 1.36, 14.6], target: [-0.15, 1.19, 0], fov: 20 },
  /** a2_c004 沿線：三人同框下的小幅移動（略推近、看腕背與肘外紙環） */
  g4_c004_wrist: { pos: [-0.2, 1.33, 14.2], target: [-0.2, 1.16, 0], fov: 20 },
  /** a2_c004 沿線：略往下看膝前紙環 */
  g4_c004_knee: { pos: [-0.1, 1.24, 14.4], target: [-0.1, 1.08, 0], fov: 20 },
  /** a2_c004 沿線：略往上，線一路延伸出畫面上緣（孩子仍在安全框內、腳不進字幕區） */
  g4_c004_up: { pos: [-0.18, 1.42, 14.8], target: [-0.18, 1.23, 0], fov: 20 },
  /** 閉幕前回到台口全景 */
  g4_stage: { pos: [0, 4.4, 30], target: [0, 4.2, 0], fov: 20 },
};

/** 錨點鏡位的預設距離（"anchor:ale.wrist" 這類鏡位，dist 可在 camera.move 的 params 覆寫） */
export const ANCHOR_CAMERA = { dist: 12.5, dy: 0.15, fov: 20 };
