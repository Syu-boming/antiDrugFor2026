// 景的共用介面（G5 全劇）：景名 → 建構器（app/src/sets/registry.ts），舞台（stage.ts）依 cue 的 set 建立、換景時釋放舊景。
// 各幕代理新增需要程式的景：在 app/src/sets/<景名>.ts 匯出一個 SetEntry，registry.ts 加一行；
// 只要放圖的景：assets/final/sets/<景名>/layout.json（格式見 imageSet.ts 與 app/SHOW_INTERFACE.md），不必寫程式。
import type { Group, Material, PerspectiveCamera } from 'three';
import type { PopPiece } from '../stage/workshop';
import type { CameraPreset } from '../stage/layers';
import type { CueTimeline } from '../cues/timeline';
import type { WorldState } from '../engine/world';

export type { PopPiece };

export interface SetContext {
  /** 景名（cue 的 set） */
  name: string;
  /** 畫質 A 才開 alphaToCoverage */
  alphaToCoverage: boolean;
  quality: 'A' | 'B';
  /** 素材圖（assets/final；id＝相對路徑去副檔名與版本號，例如 sets/plaza/back） */
  image(id: string): HTMLImageElement | undefined;
  /** 素材 JSON（例如 sets/plaza/layout） */
  json<T = unknown>(id: string): T | undefined;
}

/** 景的主光與環境光（省略的欄位用舞台預設；G4 燈光預設見 stage.ts） */
export interface SetLight {
  /** 主光位置（世界座標；光朝向 [0, 2.5, -2]） */
  key?: [number, number, number];
  keyColor?: string;
  /** 主光強度倍率（預設 1） */
  keyIntensity?: number;
  hemiSky?: string;
  hemiGround?: string;
  /** 半球光強度倍率（預設 1） */
  hemiIntensity?: number;
  /** 補光強度倍率（預設 1） */
  fillIntensity?: number;
}

export interface SetLandmark { x0: number; x1: number; y: number; z: number }

export interface SetUpdate {
  world: WorldState;
  tl: CueTimeline;
  /** cue 內秒數 */
  t: number;
  camera: PerspectiveCamera;
}

/** 建好的景（舞台持有；換景時呼叫 dispose 後丟掉） */
export interface BuiltSet {
  group: Group;
  /** 立體書景片（set.popup／set.fold 依序立起／收攏） */
  pieces?: PopPiece[];
  /** 套用 FX8 降彩的材質（省略時舞台把 group 裡所有材質都套上） */
  materials?: Material[];
  /** 角色站位（名冊沒寫 x、z 時用） */
  marks?: Record<string, { x: number; z: number }>;
  /** 扶桌點（puppet.kneeTug 預設的 at） */
  tableEdge?: [number, number] | null;
  /** 量測用地標（驗收包投影到螢幕） */
  landmarks?: Record<string, SetLandmark>;
  /** 這個景的燈光 */
  light?: SetLight;
  /** 這個景的鏡位（cue 的 camera／camera.move 可以直接用名稱） */
  cameras?: Record<string, CameraPreset>;
  /** 每格呼叫（純函式：只依 world、t 決定畫面，重播一致） */
  update?(o: SetUpdate): void;
  /** 額外的釋放（舞台會先自動釋放 group 裡的幾何、材質與貼圖） */
  dispose?(): void;
  /** 準備畫面的提醒（例如缺圖用了退路） */
  report?: string[];
}

export interface SetEntry {
  /** 給人看的名稱 */
  title: string;
  build(ctx: SetContext): BuiltSet;
  /** 不必先建景就知道的鏡位（時間軸算鏡頭時用；和 BuiltSet.cameras 一樣即可） */
  cameras?: Record<string, CameraPreset>;
}
