// Cue 資料型別（v1.2 第 19.3 節欄位＋v1.3 凍結共用元件）。
// 這份型別與 app/cues/cue.schema.json 描述同一個 JSON 結構；改欄位要兩邊一起改（G4 後凍結，只有主線能改）。
//
// v1.2 第 19.3 節欄位對照：
//   id             → Cue.id（格式 a{幕}_c{三位數}，例如 a2_c002）
//   sceneId        → Cue.sceneId
//   種類           → Cue.kind
//   角色起始狀態   → Cue.initialState（含舞台狀態 stage 與角色 characters）
//   動畫           → Cue.animation
//   audioId        → 對白：Cue.lines[].audioId（逐句一檔）；段落配樂／環境音：Cue.audioId
//   字幕時間點     → Cue.lines[].start（秒，相對 cue 開始；省略時依音檔長度自動接續）
//   下一節點       → Cue.next
//   上一穩定節點   → Cue.prevStable
//   是否可略過     → Cue.skippable
//   壓縮級別       → Cue.compression（0／1／2）
//   對嘴資料 id    → Cue.lines[].lipsyncId
//   特效編號       → Cue.fx（例如 "FX5"）
//   教師提示       → Cue.teacherNote
//   查核點         → Cue.checkpoint
//
// G5 全劇（2026-10-21，主線授權的共用元件修改）：
//   cue.set／setFade      每個 cue 可指定景（覆寫檔案層級的 set）；換景時亮度漸變（≥0.6 秒）
//   cue.level1／level2    壓縮級別 1／2 時的替代版本（留哪些台詞、換掉動畫、最短長度）
//   cue.storyboard        動態分鏡底稿（劇本舞台指示＋節拍表：節拍、角色、鏡頭、聲音），給各幕代理參考，引擎不讀
//   checkpoint.escalate   查核點落後多少秒時建議啟用幾級壓縮
//   CueFile.segments      全劇（app/cues/show/）合併後的段落資訊（tools/pack.mjs 產生，作者不用寫）

/** cue 種類：title 署名卡待機／curtain 開幕閉幕／scene 劇情段／quiz 出題／reveal 揭答與回饋／wait 停住等老師／lamp 點燈 */
export type CueKind = 'title' | 'curtain' | 'scene' | 'quiz' | 'reveal' | 'wait' | 'lamp';

export type Compression = 0 | 1 | 2;

/**
 * 時間參照：數字＝秒（相對 cue 開始）；字串可寫
 *   "a2_c002_01"        該句開始
 *   "a2_c002_01.end"    該句結束
 *   "end"               cue 結束
 * 後面可接 +0.3 或 -1 位移，例如 "a2_c002_01.end+0.2"、"end-1.2"。
 * 用台詞當錨點，換上正式配音後長度改變，動作會自動跟著移。
 */
export type TimeRef = number | string;

/** 一句台詞＝一個配音檔＝一段字幕 */
export interface CueLine {
  /** 台詞編號 a{幕}_c{三位數}_{兩位數} */
  id: string;
  /** 說話者顯示名稱（例如「阿樂叔叔」「旁白」），對應 characters 名冊 */
  speaker: string;
  /** 字幕文字，與配音逐字相同 */
  text: string;
  /** 音檔 id，省略時為 "vo_" + 台詞編號（檔案 audio/vo/vo_<台詞編號>_vNN.wav） */
  audioId?: string;
  /** 字幕／配音開始時間（字幕時間點）；省略時接在上一句之後 */
  start?: TimeRef;
  /** 對嘴資料 id，省略時同台詞編號 */
  lipsyncId?: string;
  /** 落後 3 分鐘時可略過的句子 */
  skippableWhenBehind?: boolean;
}

export interface CueAnimation {
  /** 動畫名稱，見 src/engine/world.ts 與 src/stage/perform.ts 的動畫表 */
  name: string;
  /** 作用對象（角色 id）；舞台層動畫不用填 */
  target?: string;
  start: TimeRef;
  /** 秒；省略時依動畫預設 */
  duration?: number;
  /** 緩動名稱：linear／in／out／inOut／heavy */
  ease?: string;
  params?: Record<string, unknown>;
}

/** 角色起始狀態 */
export interface CharacterStart {
  x?: number;
  y?: number;
  z?: number;
  /** 1＝面向右（本地 +x 朝畫面右），-1＝面向左 */
  facing?: 1 | -1;
  visible?: boolean;
  /** 姿勢預設名稱：stand（站立）／pulled（手被線拉向一旁） */
  pose?: string;
  /** cue 開始時已經扣上的操偶線錨點（wrist 手腕背側／elbow 手肘外側／knee 膝蓋正面） */
  strings?: string[];
  /** 操偶線張力 0–1（0＝鬆垂，1＝繃緊） */
  stringTension?: number;
  /** 立起程度：0＝平躺（等待隨景片立起，見 puppet.popup），1＝站好（預設） */
  popup?: number;
  /** 坐姿程度（正面分件紙偶）：1＝坐、0.5＝半站、0＝站（預設 0；pose:"sit" 也會設成 1） */
  sit?: number;
  /** 起始情緒：smile／greet（X2 想打招呼）／neutral／confused／worried／surprised（臉部換片） */
  emotion?: string;
  /** B 側手的起始位置：chest（手放胸前）／grab（扶著桌邊）／lap（放膝上，預設） */
  hand?: 'chest' | 'grab' | 'lap';
}

/** 舞台起始狀態 */
export interface StageStart {
  curtain?: 'open' | 'closed';
  titleCard?: boolean;
  /** 相機預設名稱，見 src/stage/layers.ts 的 CAMERA_PRESETS */
  camera?: string;
  /** 舞台燈 0–1（題卡模式會調暗） */
  light?: number;
  /** 題卡是否已經在畫面上（quiz 之後的 reveal 用） */
  quiz?: boolean;
  /** 立體書景片：0＝平躺（開幕前）、1＝立好（預設） */
  set?: number;
  /** FX8 場景降彩 0–1（只作用於景片，不作用於角色、操偶線、字幕與題卡） */
  desat?: number;
  /** FX4 柔和追光 0–1 與追光對象（角色 id） */
  spot?: number;
  spotTarget?: string;
}

export interface CueInitialState {
  stage?: StageStart;
  characters?: Record<string, CharacterStart>;
}

export interface QuizData {
  /** 題號 Q1–Q8 */
  qid: string;
  /** 第幾題（1–8），也是點亮第幾盞燈 */
  number: number;
  question: string;
  options: [string, string, string];
  /** 正解 1／2／3 */
  answer: 1 | 2 | 3;
}

export interface Checkpoint {
  /** 查核點說明，例如「第二幕結束」 */
  label: string;
  /** 預定授課分鐘（從開演起算） */
  atMinute: number;
  /** 落後 ≥ behindSec 秒時建議啟用 level 級壓縮（時長估算_v03.md 第 5 節） */
  escalate?: { behindSec: number; level: 1 | 2 };
}

/** 壓縮時的替代版本（壓縮級別 1 或 2 啟用時套用；2 級會先套 1 級再套 2 級） */
export interface CueVariant {
  /** 只留這些台詞（台詞編號）；其他台詞不播、不上字幕（時間軸上收成 0 秒，錨在它們上的動作照樣解析） */
  lines?: string[];
  /** 整組換掉的動畫 */
  animation?: CueAnimation[];
  minDuration?: number;
  voStart?: number;
  tail?: number;
}

/** 動態分鏡底稿（tools/build_show_skeleton.py 由劇本與節拍表產生；引擎不讀，只給製作參考） */
export interface Storyboard {
  /** 節拍表「節拍」欄 */
  beat?: string;
  /** 節拍表「角色（姿勢／手型／表情）」欄 */
  cast?: string;
  /** 節拍表「鏡頭」欄 */
  camera?: string;
  /** 節拍表「聲音」欄 */
  sound?: string;
  /** 劇本的舞台指示（括號內文字，依出現順序） */
  directions?: string[];
  /** 劇本 cue 資訊的估計秒數與動作秒數 */
  estimateSec?: number;
  actionSec?: number;
}

export interface SfxEvent {
  id: string;
  at: TimeRef;
  gain?: number;
}

/** 段落內的配樂切換（交叉淡入淡出）。id 為 "none" 時淡出停止 */
export interface MusicEvent {
  id: string;
  at: TimeRef;
  /** 是否循環（預設 true；片頭、片尾這類一次性的曲子設 false） */
  loop?: boolean;
  /** 交叉淡入淡出秒數（預設 1.5） */
  fade?: number;
  gain?: number;
  /** 從曲子的第幾秒開始播（對齊配樂同步點用） */
  offset?: number;
}

export interface Cue {
  id: string;
  sceneId: string;
  kind: CueKind;
  /** 給人看的標題 */
  title?: string;
  initialState: CueInitialState;
  animation: CueAnimation[];
  /** 段落配樂／環境音 id（音樂匯流排）；null＝沿用目前的配樂；"none"＝停止配樂 */
  audioId: string | null;
  lines: CueLine[];
  /** 下一節點；null＝最後一個節點（保持畫面） */
  next: string | null;
  /** 上一穩定節點：按「上一步」回到這個 cue 播完後的停住畫面；null＝沒有上一步 */
  prevStable: string | null;
  skippable: boolean;
  compression: Compression;
  fx: string[];
  teacherNote: string;
  checkpoint: Checkpoint | null;

  // ---- 以下為選填的時間與流程參數 ----
  /** 最短長度（秒），沒有台詞的段落用 */
  minDuration?: number;
  /** 第一句台詞開始前的留白（秒） */
  voStart?: number;
  /** 最後一句之後的停留（秒） */
  tail?: number;
  /** 播完自動進入下一節點（只用在「閉幕→片尾署名卡」這類同一次按鍵內的連續動作） */
  autoAdvance?: boolean;
  /** quiz／reveal 的題目資料；reveal 省略時沿用前一個 quiz */
  quiz?: QuizData;
  /** 這個 cue 點亮第幾盞燈（1–8） */
  lamp?: number;
  sfx?: SfxEvent[];
  /** 段落內的配樂切換（在 audioId 之後套用） */
  music?: MusicEvent[];
  /** 配樂基準音量（0–1）；省略時依 cue 種類（劇情 0.8、題卡 0.06、署名卡 0） */
  musicLevel?: number;
  /** audioId 的配樂是否循環（預設 true） */
  musicLoop?: boolean;
  /** 落後 6 分鐘時的短版說明（壓縮級別 2 用） */
  shortVersion?: string;

  // ---- G5 全劇 ----
  /** 這個 cue 的舞台景（景名見 app/src/sets/registry.ts 或 assets/final/sets/<景名>/layout.json）；省略時用檔案層級的 set */
  set?: string;
  /**
   * 換景時的亮度漸變秒數（從暗漸亮；最少 0.6）。跟前一個 cue 的景不同時自動套用（預設 0.8）；
   * 景相同但想從暗漸亮也可以寫。進入時從暗開始的 cue，引擎會先把前一格畫面漸暗 0.6 秒再開始。
   */
  setFade?: number;
  /** 壓縮級別 1 啟用時的替代版本（例如去掉搬運鏡頭） */
  level1?: CueVariant;
  /** 壓縮級別 2 啟用時的替代版本（短版，例如只播 _03） */
  level2?: CueVariant;
  /** 動態分鏡底稿（引擎不讀） */
  storyboard?: Storyboard;
  /** 所屬段落 id（全劇合併時由 tools/pack.mjs 填入，作者不用寫） */
  segment?: string;
}

/** 角色名冊（cue 檔內）：角色 id → 顯示名稱 */
export interface CharacterRoster {
  /**
   * rig：紙偶種類。adult／child＝程式佔位紙偶（側面）；ale_v03＝圖片分件（parts.json）；
   * standee:<角色>＝整張圖立牌（例如 standee:xiaoqing）。assets/final/g4_manifest.json 的 characters 可覆寫。
   * x、z、facing：預設站位（cue 的 initialState.characters 可再覆寫）。
   */
  [id: string]: {
    name: string; rig?: string; x?: number; z?: number; facing?: 1 | -1;
    /** rig 找不到時的程式佔位紙偶（adult／child；省略時 ale 用 adult、其他用 child） */
    fallback?: 'adult' | 'child';
  };
}

/** 全劇合併後的段落資訊（tools/pack.mjs 由 app/cues/show/index.json 產生） */
export interface SegmentInfo {
  /** 段落 id（＝段落檔的 id，例如 a2） */
  id: string;
  title: string;
  /** 段落檔名（例如 a2.json） */
  file: string;
  /** 段落檔層級的景 */
  set?: string;
  /** 段落檔的角色名冊 */
  characters?: CharacterRoster;
  /** 這個段落的 cue（依序） */
  cueIds: string[];
}

/** app/cues/show/index.json：全劇的段落清單 */
export interface ShowIndex {
  format: 'antidrug-show/1';
  id: string;
  title: string;
  /** 依演出順序的段落檔名（同資料夾） */
  segments: string[];
}

export interface CueFile {
  format: 'antidrug-cues/1';
  id: string;
  title: string;
  /** 舞台景（workshop＝技術骨架佔位景；workshop_g4＝G4 燈籠店立體書景；kraft_stage＝全劇牛皮紙佔位景；其他見 app/SHOW_INTERFACE.md） */
  set?: string;
  characters?: CharacterRoster;
  cues: Cue[];
  /** 全劇合併後才有：各段落的名冊與景（作者不用寫） */
  segments?: SegmentInfo[];
}
