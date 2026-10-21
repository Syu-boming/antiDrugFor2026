# G5 全劇介面（給各幕代理與主線）

版本：2026-10-21 第 2 天下午（G5 開工前共用元件，引擎與全劇 cue 架構）。G4 的介面（cue 欄位、動畫名稱、操偶線、臉部換片、素材 id）見 `app/G4_INTERFACE.md`，本文件只寫 G5 新增與各幕分工。共用元件凍結，只有主線能改。

## 1. 分工：誰可以改什麼

| 誰 | 可以改 | 不可以改 |
|---|---|---|
| 各幕代理（aN） | `app/cues/show/aN.json`（自己的段落檔）；自己的程式景 `app/src/sets/<景名>.ts`＋在 `app/src/sets/registry.ts` 的 `SET_REGISTRY` 加**一行**；`assets/final/sets/<景名>/`（景片圖＋`layout.json`）；自己新增的角色姿勢圖（`assets/final/chr-<角色>_pose-<名稱>_vNN.png`）並登記到 `assets/final/rig/show_characters.json` 裡**自己角色**的 `poses`；`review/G5/aN/` | 其他段落檔、`index.json`、引擎（`src/engine/`）、`src/cues/`、`src/stage/`、`src/ui/`、`cue.schema.json`、`src/types/cue.ts`、`tools/`、G4 的 `cues/g4.json`、別人的景與角色 |
| 主線 | 全部 | — |

規則：要改共用檔才做得到的事，寫進回傳的 handoff 交給主線，不要自己改。`tools/build_show_skeleton.py` 預設不覆寫已存在的段落檔；`--force` 會蓋掉各幕的修改，只有主線能用。

段落檔與景的對照（底稿）：

| 檔 | 內容 | 景（底稿） |
|---|---|---|
| a0.json | 開場（a0_c000 片頭待機署名卡〔G4〕、a0_c001 開幕〔G4，補台詞 a0_c001_01〕～a0_c005） | workshop_g4 |
| a1.json | 第一幕（a1_c001–a1_c008，Q1） | kraft_stage |
| a2.json | 第二幕（a2_c001–a2_c013，Q2、Q3；a2_c002、a2_c004 是 G4 代表鏡頭） | workshop_g4（a2_c013 kraft_stage） |
| a3.json | 第三幕（a3_c001–a3_c008，Q4） | kraft_stage |
| a4.json | 第四幕（a4_c001–a4_c013，Q5、Q6） | kraft_stage |
| a5.json | 第五幕（a5_c001–a5_c008，Q7） | kraft_stage |
| a6.json | 第六幕（a6_c001–a6_c009，Q8） | kraft_stage（a6_c009 workshop_g4） |
| a7.json | 複習與收束（a7_c001–a7_c003） | kraft_stage |
| a8.json | 閉幕（a8_c001 謝幕、a8_c002 布幕合攏〔G4〕、a8_c003 片尾署名卡〔G4〕） | workshop_g4 |

## 2. 建置、預覽、驗證

```bash
cd app
npm run typecheck
npm run build                          # 打包時驗證 show/ 每個段落檔＋合併後的整齣，有錯就停（訊息帶檔名與 cue 編號）
node ../tools/engine-test.mjs          # 狀態機、G4、全劇（第八段）約 6 分鐘
open "dist/index.html?cues=show&nofs=1&menu=1"    # 教師選單（M 鍵）可跳 cue
cd .. && caffeinate -i node tools/act_review_pack.mjs --acts a1      # 本段驗收包 → review/G5/a1/pack/
```

- `?cues=show` 載入全劇；`?cues=g4` 仍是 G4 代表鏡頭（畫面與 G4 驗收包逐像素相同）。
- 擷取：`?capture=1&cues=show`，`window.__engine.gotoCue(id, { mode: 'before' })` 停在前一段的停格，`capture.playCue(id)`、`capture.seek(t)`；換景時 `capture.seek(負秒數)` 看得到漸暗預捲。

## 3. 全劇 cue 集（app/cues/show/）

- `index.json`：`{ "format": "antidrug-show/1", "id": "show", "title": …, "segments": ["a0.json", …, "a8.json"] }`（只有主線改）。
- 段落檔＝一般 cue 檔（`format: antidrug-cues/1`），檔案層級的 `set`（景）、`characters`（本段名冊）只管本段。
- 合併（`app/src/cues/show.ts`，`tools/pack.mjs` 打包時做）：每個 cue 填上 `set`（cue.set ＞ 段落 set ＞ kraft_stage）與 `segment`；名冊保留在 `segments[]`，說話者對角色、紙偶站位都依段落名冊。
- 跨段落流程：`next`／`prevStable` 可以直接寫別段的 cue 編號（底稿就是這樣寫的）；也可以在本段最後一個 cue 寫 `next: null`、第一個 cue 寫 `prevStable: null`，合併時自動接上（最後一段的 `next: null`＝演出結束）。驗證會檢查從片頭沿 next 走得到每個 cue。
- 題目流程固定：出題（quiz）→ 揭答（reveal，prevStable＝出題）→ 點燈（lamp，`lamp: N`，prevStable＝揭答）→ 續演。不要改成揭答直接接劇情，也不要把點燈併進揭答（engine-test 第八段會擋）。
- 每個 cue 都有 `storyboard`（劇本舞台指示＋節拍表的節拍、角色、鏡頭、聲音、估計秒數），是給你的底稿參考，引擎不讀，可以留著也可以刪。
- 不能改的內容：台詞編號、說話者、字幕文字（一字不改，engine-test 比對劇本 v03）；兩句必要旁白；八題題目、選項、答案；cue 編號與順序。

## 4. cue 的 G5 新欄位

| 欄位 | 說明 |
|---|---|
| `set` | 這個 cue 的景（覆寫段落層級）。景名見第 5 節。 |
| `setFade` | 進入這個 cue 時從暗漸亮的秒數（≥0.6）。**跟流程上前一個 cue 的景不同時自動套用 0.8 秒**，不用寫；景相同但想從暗開始（例如時間跳躍）才寫。 |
| `level1`／`level2` | 壓縮 1／2 級時的替代版本：`{ lines: [只留的台詞編號], animation: [整組替換], minDuration, voStart, tail }`。1 級另外自動略過 `lines[].skippableWhenBehind: true` 的句子；2 級套用於 `compression: 2` 的 cue（底稿已依劇本寫好 a6_c008、a7_c001 的 `level2.lines`）。略過的句子在時間軸上收成 0 秒，錨在它上面的動作照樣解析。 |
| `checkpoint.escalate` | `{ behindSec, level }`：查核點落後多少秒建議啟用幾級（底稿：Q3 a2_c011 90 秒→1 級、Q6 a4_c011 120 秒→1 級、Q8 a6_c005 150 秒→2 級；時長估算_v03.md 第 5 節）。 |
| `storyboard` | 動態分鏡底稿（引擎不讀）。 |
| `segment` | 合併時填入，作者不用寫。 |
| 名冊 `fallback` | `adult`／`child`：rig 找不到時用哪種程式佔位紙偶。 |

新動畫（舞台層，沒有 target）：

| 名稱 | 參數 | 說明 |
|---|---|---|
| `fade.out` | `to`（預設 1）、duration（預設 0.8，**≥0.6**） | 整個畫面漸暗（字幕、題卡是 HTML 不受影響） |
| `fade.in` | duration ≥0.6 | 漸亮 |
| `set.swap` | `params.set`（景名） | 在這個時間點換景（同一個 cue 內換景）。一定要排在 `fade.out` 全暗之後再 `fade.in`，或在 `set.fold` 收平之後再 `set.popup`（立體書翻頁式換景），不可以亮著硬切。 |
| `zhezhe.*` | 見第 6.3 節 | 折折的程式動作（由折折自己解讀） |

## 5. 景

### 5.1 找景的順序

`app/src/sets/registry.ts` 的 `SET_REGISTRY` → `assets/final/sets/<景名>/layout.json`（資料驅動的通用景，不必寫程式）→ 都沒有就用 `kraft_stage` 並在準備畫面列出。

已登記：`workshop_g4`（G4 燈籠店，畫面與 G4 驗收包相同；實作在 `src/stage/workshop.ts`）、`kraft_stage`（中性牛皮紙舞台佔位景，沒有任何文字）、`workshop`（技術骨架，demo 用）。

### 5.2 換景（全部自動）

- 景不同的兩個 cue 之間：老師按下一步 → 引擎先把目前這一格**漸暗 0.6 秒**（預捲，在 cue 第 0 秒之前，聲音也延後）→ 全暗時釋放舊景（幾何、材質、貼圖）、建新景 → 新 cue 從暗**漸亮 0.8 秒**（`setFade` 可加長）。台詞照常從 `voStart` 開始，想等亮了再說就把 `voStart` 設 ≥0.8。
- 上一步、章節跳轉換到別的景：即時播放時一樣先漸暗 0.6 秒再漸亮 0.6 秒（不突然由亮轉暗，v1.2 第 17.3 節第 5 條）。
- 換景亮度變化是單向漸變（正弦緩動），光敏分析算一次變化。

### 5.3 資料驅動景：assets/final/sets/<景名>/layout.json

圖放在同一個資料夾，檔名加版本號（`back_v01.png`），圖像 id＝`sets/<景名>/<檔名去版本號>`；layout.json 裡寫短名（`"back"`）即可，要用別處的圖（例如 `props/prop-bench`）就寫完整 id。

```json
{
  "format": "antidrug-set/1",
  "title": "小鎮廣場（放學後）",
  "wall":  { "image": "back", "width": 21, "y": 0, "z": -3.6, "emissive": 0.32 },
  "floor": { "image": "floor", "repeat": [10, 4], "color": "#d8c09a" },
  "layers": [
    { "id": "arcade",  "image": "arcade",  "x": -4.2, "y": 0, "z": -2.4, "width": 6.0, "layer": "far",  "popup": [0.05, 0.3] },
    { "id": "bench",   "image": "props/prop-bench", "x": 0.2, "z": -0.6, "height": 0.92, "layer": "mid", "popup": [0.3, 0.5] },
    { "id": "leaves",  "image": "leaves",  "x": -6.8, "y": -0.05, "z": 2.3, "width": 2.4, "layer": "fore", "popup": [0.7, 0.92], "parallax": 0 }
  ],
  "grade":  { "preset": "day_warm" },
  "light":  { "key": [-7, 13, 16], "keyColor": "#ffe9c8" },
  "marks":  { "pinan": { "x": 0.4, "z": -0.3 } },
  "landmarks": { "benchSeat": { "x0": -0.6, "x1": 1.0, "y": 0.92, "z": -0.6 } },
  "cameras":   { "plaza_wide": { "pos": [0, 2.4, 28], "target": [0, 2.1, 0], "fov": 20 } }
}
```

- `wall`：背牆（不立起，底邊在 y）；`emissive` 自發光讓舞台燈調暗時兒童身後仍夠亮（D-G2-06，建議 0.3）。`floor`：地板（沒圖用 color）。
- `layers`（後面的畫在前面）：`width` 或 `height` 擇一（另一邊依圖比例），`scale` 再乘；`layer`＝backdrop／far／mid／fore（層序見 `src/stage/layers.ts`）、`order` 同層內再加；`popup:[from,to]`＝在 `set.popup`／`set.fold` 進度中這張景片立起的區間（立起順序與時間；省略＝一直站著）；`thick` 卡紙厚度像素（預設 5）；`shadow` 投影（預設 true）；`parallax` 鏡頭橫移時額外跟著移的比例；`opacity<1` 半透明（霧、光、和紙）；`flipX`、`rotationY`、`emissive`。
- `grade.preset`（FX8 色彩分級，只作用在景片，角色、操偶線、字幕、題卡不受影響）：neutral、morning_gold、day_warm、cool_shadow、dusk_purple、classroom_afternoon、kraft_map、silhouette、muted、hospital_evening、night_warm、memory_faded；或直接給 `tint`（乘色）與 `saturation`。對照節拍表 0.4 色彩腳本。
- `light`：主光位置、顏色、強度倍率（`keyIntensity`、`hemiIntensity`、`fillIntensity`）、半球光顏色；沒寫就用 G4 燈光預設。
- `marks`：名冊沒寫 x、z 的角色站在這裡（名冊有寫以名冊為準）。`landmarks`：量測用地標（驗收包投影到螢幕）。
- `cameras`：本景鏡位，cue 的 `initialState.stage.camera` 與 `camera.move` 的 `to` 直接寫名稱。
- 景片圖裡不放任何文字、品牌、真實標誌；求助站不用紅十字；外送／物流不用真實配色（安全界線第 10 條）。

### 5.4 需要程式的景：app/src/sets/<景名>.ts

```ts
import type { SetEntry } from './types';
import { buildImageSet, readLayout } from './imageSet';
export const MAP_A4: SetEntry = {
  title: '紙上的路（第四幕）',
  cameras: { map_top: { pos: [0, 14, 6], target: [0, 0, 0], fov: 20 } },
  build(ctx) {
    const base = buildImageSet(ctx, readLayout(ctx, 'map_a4')!);   // 可以先用 layout.json 建底，再加程式景片
    // …加自己的 Mesh 到 base.group，回傳 pieces／materials／update（每格呼叫，必須是時間的純函式）
    return base;
  },
};
```

在 `registry.ts` 加 `import { MAP_A4 } from './map_a4';` 與 `SET_REGISTRY` 裡一行 `map_a4: MAP_A4,`（註明幕別，只動自己的行）。介面（`BuiltSet`：group、pieces、materials、marks、tableEdge、landmarks、light、cameras、update、dispose、report）見 `src/sets/types.ts`。舞台換景時會自動釋放 group 裡的幾何、材質、貼圖；自己另外建的資源寫在 `dispose`。

## 6. 角色

### 6.1 名冊（段落檔 `characters`）

`{ "pinan": { "name": "品安", "rig": "standee:pinan", "x": 4.5, "z": -0.1, "facing": -1, "fallback": "child" } }`

- `name` 必須和台詞的說話者完全相同（對嘴、聆聽反應靠它）。底稿的角色 id：ale、xiaoqing、xiaoyu、zhezhe、pinan、ye、lin、chen（角色表 v03 第 8 條）。邀請者（只出現手，`chr-inviter_hand-box`）、119 執勤人員（只有聲音）、旁白沒有放進名冊；手請做成景片或立牌，不要用人形佔位紙偶。
- 名冊順序＝層序（第 j 個角色 renderOrder 基準＝300＋20j）；a2 的 ale、xiaoqing、xiaoyu 排前三個，G4 兩個代表鏡頭才會和 G4 一模一樣。
- 每個 cue 只有 `initialState.characters` 列出的角色在台上（沒列＝不在台上）。

### 6.2 立牌角色：assets/final/rig/show_characters.json（共用美術代理維護）

- `characters[角色 id]`：完整的 `StandeeCharConfig`（`{ rig: 'standee', height, defaultPose, face, poses: { 姿勢名: { image, face?, feet?, headTop? } } }`），或只寫要覆寫的欄位；`poses` 會和 G4 的姿勢表合併（只列新姿勢也不會蓋掉 G4 的）。
- `rigs[rig 名稱]`：同格式（用 rig 名稱登記，名冊的 `rig` 指向它）。
- `fallbackFaces["角色:姿勢"]`：`FALLBACK_FACES` 同格式（退路眨眼與嘴型範圍），引擎併進內建表。
- 查找順序：g4_manifest.json 的 characters（照舊有效）→ show_characters.json 的 characters → rigs → 內建 BUILTIN_RIGS；找不到就用名冊 `fallback` 的程式佔位紙偶並列在準備畫面。
- 各幕新增姿勢：圖放 `assets/final/chr-<角色>_pose-<名稱>_vNN.png`，在 show_characters.json 該角色的 `poses` 加一筆（只動自己的角色、自己的姿勢；同一角色多幕都要用時先在 handoff 說，避免兩幕同時改同一筆）。cue 用 `initialState.characters.<id>.pose` 或 `puppet.pose { pose }`（紙片翻面）。
- 品安身上永遠沒有操偶線；操偶線只在阿樂叔叔（分件紙偶 ale_v03）身上，扣點只有 wrist／elbow／knee（驗收包量）。

### 6.3 折折（程式角色 rig: "zhezhe"）

- 名冊 `"zhezhe": { "name": "折折", "rig": "zhezhe" }`。`app/src/stage/zhezhe.ts`（折折代理）由主線接上之前，畫面上是「佔位小紙片」（白底淺橙的小摺紙，只會進出場、移動、立起、說話時輕輕彈動），準備畫面會寫「程式角色 zhezhe 還沒接上」。
- 接上之後（主線做，見 handoff），cue 用下列動畫（target＝"zhezhe"，時間參照同其他動畫）：`zhezhe.fold {form, scale, fumble}`（form：idle／card／plane／megaphone／magnifier／lantern／hat／sheet）、`zhezhe.emote {emotion}`（neutral／happy／curious／worried／proud／sad）、`zhezhe.walkTo {pos}`、`zhezhe.hopTo {pos, height}`、`zhezhe.flyTo {pos, height}`、`zhezhe.glideTo {pos}`、`zhezhe.turn {yaw}`、`zhezhe.look {yaw}`、`zhezhe.hush`（收摺收聲訊號 S3）、`zhezhe.glow {to}`、`zhezhe.rise`、`zhezhe.twitch {side}`、`zhezhe.blink`；`puppet.enter／exit／move` 也可用。對嘴自動取台詞的 lipsync。參數意義見 `src/stage/zhezhe.ts` 檔頭。

## 7. 排表演、鏡頭、FX、題卡、點燈

- 時間參照錨在台詞（`"a3_c002_01.end+0.3"`），換配音長度動作會跟著移；動畫名稱、操偶線 API、臉部換片見 G4_INTERFACE.md 第 4–6 節。
- 句長：引擎依實際配音（v04）長度排；`audio/vo/timings.json` 有每句秒數與句中段落（`speech_segments`），對嘴 `audio/lipsync/<台詞編號>_v04.json`。
- 鏡位：G4 的 `g4_wide／g4_mid／g4_mid_up／g4_push／g4_stage`；G5 共用 `show_mid`（x −6.3～6.9 同框、腳在字幕之上，底稿的預設）、`show_wide`、`show_close`；景自己的 `cameras`；錨點鏡位 `anchor:ale.wrist` 等；或直接 `{pos,target,fov}`。下方 20% 留給字幕，說話者的臉不進去；重要內容在 90% 安全框內。鏡頭移動用預設正弦緩動、慢（光敏）。
- G4 驗收提出、G5 要做到的目標（REVIEW.md「G4 代表鏡頭：關卡決定」）：同場角色組成群體（孩子與受影響者外框水平距離 ≤ 畫面寬 15%，或前景角色縮放 ≥1.05 並遮擋，做出前後景深）；長段落不能只靠慢推與漂移。
- FX：`fx.desat`、`fx.spot`、`light.dim`、`set.popup／fold`、`fade.out／in`、景的 `grade`；不做閃爍、晃動、重影、色散、綠霧、發光眼；燈慢慢亮（單盞 ≥1 秒）。
- 題卡三段（底稿模板，可以調時間但不要改結構）：
  - 出題 quiz：`sfx_quiet_fold`（收聲訊號）at 0 → `camera.move {to: quiz}` 2.4 s、`light.dim {to: 0.55}` → `quiz.show` 0.7 s（`sfx_card_in`）→ 折折引言＋題目＋三個選項（題卡在畫面上時字幕條自動收起）。`quiz` 資料照八題_v03.md，不要改。
  - 揭答 reveal：起始 `quiz: true`、`camera: quiz`、`light: 0.55` → `quiz.reveal` 0.3 s（`sfx_stamp`）→ 揭答旁白。
  - 點燈 lamp：`lamp: N` → `lamp.light {index: N}` 0.3 s 起 1.5 s 漸亮（`sfx_lamp_on`）→ 折折那句 → 句末 +0.3 s `quiz.hide`、`light.restore`、`camera.move` 回故事鏡位。燈籠在題卡卡片裡（`src/ui/quizcard.ts`），題卡收起燈也一起收起。

## 8. 壓縮級別、查核點、章節（給教師控制台）

`window.__engineShow`（引擎建立時掛上；主線之後可併進 `window.__engine`）：

| 方法 | 回傳 |
|---|---|
| `chapters()` | `[{ id, title, firstCue, lastCue, cueCount, durationSec, sets }]`（全劇＝9 段） |
| `compression()`／`setCompression(0|1|2)` | 目前級別；播放中設定回傳 `'pending'`，這段播完才套用（重建時間軸） |
| `checkpoints()` | `{ elapsedSec, suggested, list: [{ cueId, label, plannedMin, actualMin, behindSec, escalate, triggered }] }`；開演＝片頭待機第一次按下一步，查核點在離開該 cue 時記錄（沒離開用播完時） |
| `resetShowClock()` | 重設開演時間與查核點紀錄 |
| `sets()` | `{ active, built, disposed, lastBuildMs, liveSetGroups }` |

`getCues()` 多了 `segment、chapter、set、enterFade、compression、skipped、droppedLines、checkpoint、teacherNote、quiz {qid, number, answer}、lamp、lines`；`getState()` 多了 `segment、chapter、compression、suggestedCompression、showElapsedSec、enterFade、prerollSec、dim`、`world.dim`。

## 9. 本段驗收包

```bash
cd app && npm run build && cd ..
caffeinate -i node tools/act_review_pack.mjs --acts a1          # → review/G5/a1/pack/（a1 約 15–25 分鐘；--skip-asr 省掉逐字稿）
```

產出（固定規則取樣，製作代理不挑畫面）：每個 cue 前中後關鍵影格（`capture/keyframes/`）、每秒接觸表（`capture/contact_timeline_*.png`）、與 G4 同尺寸並排（`compare_g4/`）、投影模擬（`proj/`）、播放錄製 30 格／秒（含換景漸暗預捲與教師停格假設）的光敏分析（`flash_playback.json`、`flash_variants.json`）與影片（`<段>_playback.mp4`）、該段混音響度與各句對白響度（`audio/loudness.json`）、字幕與語音時間差（`subtitle_sync.json`）、配音逐字稿差異（`transcripts.md`，v04）、長度對照時長估算_v03.md 預算（`durations.json`）、安全量測（`safety_data.json`：操偶線扣點、線到頭部框距離、線是否經過兒童、必要旁白一字不差、台詞與劇本逐字比對、字幕排版、隱私）；`INDEX.md` 只列數字與檔案。

## 10. 各幕代理第一步

1. 讀本文件、`app/G4_INTERFACE.md` 第 3–6 節、自己的段落檔（每個 cue 的 `storyboard`）、劇本與節拍表自己那一段、REVIEW.md「G4 代表鏡頭：關卡決定」。
2. `cd app && npm run build`，開 `dist/index.html?cues=show&nofs=1&menu=1`，用教師選單跳到自己那段看底稿（牛皮紙佔位景＋現有紙偶，每句配音、字幕都在）。
3. 先做景：`assets/final/sets/<景名>/` 放圖＋寫 `layout.json`（多半不必寫程式），段落檔的 `set` 或 cue 的 `set` 改成新景名；需要程式（地圖翻摺、四季窗景、回憶小窗）才寫 `src/sets/<景名>.ts` 並在 registry 加一行。
4. 再排表演：每個 cue 的 `initialState.characters`、動畫、鏡頭、配樂、音效；題卡三段只調時間。
5. `npm run build`（驗證）→ `node ../tools/engine-test.mjs`（全劇第八段要全過）→ `node tools/act_review_pack.mjs --acts aN` → 把 `review/G5/aN/pack/` 交驗收。

## 11. 已知限制

- 素材載入：引擎開演前一次載入並解碼所有圖像（data 資料包約 210 MB，含全部 201 句配音）；景的貼圖只在換景時建立、舊景會釋放，但原始圖一直在記憶體裡。學校筆電的記憶體與載入時間未驗證（G6 實測）。
- 換景是在全暗那一格同步建景；複雜的程式景可能在全暗時多花幾十毫秒（畫面是暗的，聲音照音訊時鐘走，不會不同步）。
- 上一步、章節跳轉後按下一步：如果這段沒寫 `audioId`、開頭也沒有 `music` 事件、而且當下沒有配樂在播，引擎會往前找最近一次的循環配樂補上（一次播完的曲子不補）。各段第一個 cue 仍建議明寫 `audioId`。
- 程式角色（折折）不經過 PuppetDirector：其他立牌聽折折說話時不會轉頭看他；`debug.faces()` 不含折折。
- 底稿的「誰在台上」是從說話者與節拍表角色欄推得的，常常不對（例如 a5_c001 長椅上的阿樂叔叔不在名單上），請依劇本修正。

## 附錄：主線把折折接進來（app/src/stage/zhezhe.ts → 程式角色 rig:"zhezhe"）

1. 新增 `app/src/stage/zhezhe_program.ts`（介面依 zhezhe.ts 檔頭；若折折代理之後改了 API，照檔頭對應）：

```ts
import { Group, type Object3D } from 'three';
import { Zhezhe, type ZhezheEmotion } from './zhezhe';
import { registerProgramRig, type ProgramContext, type ProgramPerformer, type ProgramRigOptions } from './cast';
import type { ActorPlacement } from './perform';
import type { CueTimeline } from '../cues/timeline';
import type { CharacterStart } from '../types/cue';

const EMO: Record<string, ZhezheEmotion> = { smile: 'happy', greet: 'happy', neutral: 'neutral', confused: 'curious', worried: 'worried', surprised: 'curious' };
type V3 = [number, number, number];

class ZhezheProgram implements ProgramPerformer {
  readonly kind = 'program' as const;
  readonly root = new Group();
  private zz: Zhezhe;
  private key = '';
  constructor(readonly place: ActorPlacement, o: ProgramRigOptions) {
    this.zz = new Zhezhe({ position: [place.x, 0, place.z], height: Number(o.config.height ?? 1.0), renderOrder: o.orderBase + 15 });
    this.root.add(this.zz.group);
  }
  get id(): string { return this.place.id; }
  addTo(parent: Object3D): void { parent.add(this.root); }
  apply(tl: CueTimeline, t: number, start: CharacterStart | undefined, ctx: ProgramContext): void {
    this.root.visible = !!start && start.visible !== false;
    if (!this.root.visible) return;
    if (ctx.playKey !== this.key) {           // 換 cue、重播、上一步：重排事件（update 是時間的純函式）
      this.key = ctx.playKey;
      this.zz.reset({ pos: [start!.x ?? this.place.x, start!.y ?? 0, start!.z ?? this.place.z], emotion: EMO[start!.emotion ?? 'smile'] ?? 'neutral' });
      for (const a of tl.anims) {
        if (a.target !== this.id) continue;
        const p = a.params as Record<string, unknown>;
        switch (a.name) {
          case 'zhezhe.fold': this.zz.fold(p.form as never, a.duration as never, a.start, { scale: p.scale as number, fumble: p.fumble as never }); break;  // dur 的型別在 zhezhe.ts 是字面值
          case 'zhezhe.emote': this.zz.emote(p.emotion as ZhezheEmotion, a.start); break;
          case 'zhezhe.walkTo': this.zz.walkTo(p.pos as V3, a.duration, a.start); break;
          case 'zhezhe.hopTo': this.zz.hopTo(p.pos as V3, a.duration, p.height as number, a.start); break;
          case 'zhezhe.flyTo': this.zz.flyTo(p.pos as V3, a.duration, p.height as number, a.start); break;
          case 'zhezhe.glideTo': this.zz.glideTo(p.pos as V3, a.duration, a.start); break;
          case 'zhezhe.turn': this.zz.turn(Number(p.yaw ?? 0), a.duration, a.start); break;
          case 'zhezhe.look': this.zz.look(Number(p.yaw ?? 0), a.duration, a.start); break;
          case 'zhezhe.hush': this.zz.hush(a.start); break;
          case 'zhezhe.glow': this.zz.glow(Number(p.to ?? 1), a.duration, a.start); break;
          case 'zhezhe.rise': this.zz.rise(a.duration, a.start); break;
          case 'zhezhe.twitch': this.zz.twitch((p.side as 'l' | 'r' | 'both') ?? 'both', a.start); break;
          case 'zhezhe.blink': this.zz.blink(a.start); break;
          default: break;
        }
      }
      for (const l of tl.lines) if (l.actorId === this.id) { const lip = ctx.lipsync(l.line.lipsyncId ?? l.line.id); if (lip) this.zz.say(lip, l.start); }
    }
    // 題卡模式舞台燈調暗時提高存在感（light 0.55→1 對應 presence 0.2→0.06）
    this.zz.update(t, { presence: 0.06 + 0.14 * Math.min(1, Math.max(0, (1 - ctx.light) / 0.45)) });
  }
}

registerProgramRig('zhezhe', (o) => new ZhezheProgram(o.place, o));
```

2. `app/src/main.ts` 最上面加一行 `import './stage/zhezhe_program';`（只要在 `new Stage(...)` 之前執行即可；登記是 import 時的副作用）。
3. （可選）`main.ts` 的 `debug.faces` 併入 `stage.programs`（`zz.probe()` 的眼睛、嘴型），驗收包才量得到折折的眨眼與對嘴。
4. `npm run typecheck && npm run build`；準備畫面的「紙偶」不再出現「程式角色 zhezhe 還沒接上」；`node ../tools/engine-test.mjs` 全過；`?cues=show&capture=1` 看 a0_c002 折折登場。
5. 各幕 cue 的折折動作改寫成 `zhezhe.*` 動畫（第 6.3 節）；佔位小紙片支援的 `puppet.enter／exit／move` 仍可用，但真正的折折以 `zhezhe.walkTo` 等為準。
