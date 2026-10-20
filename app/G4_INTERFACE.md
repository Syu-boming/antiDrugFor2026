# G4 劇場程式介面（給整合代理與各幕製作）

版本：2026-10-21 第 2 天（G4 代表鏡頭）。本文件描述 `app/` 劇場程式在 G4 時的共用介面：cue 欄位、動畫名稱、操偶線 API、臉部換片與分件紙偶的素材格式、素材 id 對照，以及整合代理接下來要做的事。G4 通過後這些介面凍結，只有主線能改。

## 1. 檔案地圖

| 檔案 | 內容 |
|---|---|
| `cues/g4.json` | G4 代表鏡頭 cue 集：署名卡待機 → 開幕 → a2_c002 → a2_c004 → 停格 → 閉幕署名卡 |
| `cues/demo.json` | 技術骨架示範流程（Q2 選項已同步 `script/八題_v03.md`） |
| `cues/cue.schema.json`、`src/types/cue.ts` | cue 欄位（兩邊同步） |
| `asset-sources.json` | 正式素材還沒到時的退路來源（`assets/final` 有同 id 就自動優先） |
| `src/engine/world.ts` | 舞台層動畫（布幕、署名卡、景片立起、燈光、降彩、追光、相機） |
| `src/stage/perform.ts` | 角色動畫、操偶線、臉部換片的表演導演（`PuppetDirector`） |
| `src/stage/cast.ts` | 依 cue 的 `characters` 名冊建立紙偶（內建設定 `BUILTIN_RIGS`） |
| `src/stage/imagerig.ts`、`rig.ts` | 圖片分件紙偶（v04 `ale_rig.json` 或 `parts.json` 格式）、整體外輪廓描邊、兩節 IK |
| `src/stage/standee.ts` | 整張圖立牌（兒童；姿勢換片＝紙片翻面；頭層可轉頭點頭） |
| `src/stage/face.ts` | 臉部換片（face.json 兩種格式＋程式畫的退路換片） |
| `src/stage/strings.ts` | 平面紙繩、紙環、固定步長擺盪模擬 |
| `src/stage/workshop.ts` | G4 燈籠店立體書景（素材圖優先，缺圖用程式畫的景片） |
| `src/stage/curtain.ts` | 摺層紙布幕（手風琴摺紙，紙長固定、收攏摺深變深） |
| `src/stage/fx.ts` | FX8 景片降彩、FX4 柔和追光 |
| `src/ui/textlayout.ts` | 字幕斷行（詞表＋動態規劃；支援手動 `\n`） |
| `src/audio/ducking.ts` | 對白壓低配樂的排程（純函式，可單獨測試） |
| `../tools/pack.mjs`、`capture.mjs`、`capture_analyze.py`、`capture_probe.py`、`engine-test.mjs` | 打包、擷取、光敏與量測、狀態機測試 |

## 2. 建置、執行、驗證

```bash
cd app
npm run typecheck          # tsc
npm run build              # esbuild → dist/app.js＋dist/index.html，接著 tools/pack.mjs 產生 dist/data/*.js
node ../tools/engine-test.mjs                      # 狀態機＋G4 流程＋確定性＋缺檔＋斷行＋避讓（約 4 分鐘，86 項）
node ../tools/capture.mjs --cues g4 --probe --out ../review/G4/capture   # 驗收包用擷取（主線決定輸出位置）
```

- file:// 直接開：`app/dist/index.html?cues=g4`（`?cues=demo` 是技術骨架流程）。
- 網址參數：`capture=1` 虛擬時鐘、`autostart=1`、`q=A|B`、`fps=30`、`av=毫秒`、`step=每秒格數`、`nofs=1`、`menu=1`。
- `window.__engine.debug`：`audioLevels()`（配樂基準音量與避讓增益）、`probe()`（操偶線螢幕位置與線寬、整條線的螢幕路徑 `path`（13 點，上端→下端）、角色外框、分件紙偶的頭部框 `headBox`、布幕開合）、`hideActors(on)`（量背景用）、`faces()`（目前眼睛與嘴型）。`getState()` 另有 `missingAudio`、`castReport`、`actors`、`set`、`world`（布幕、署名卡、景片、降彩、追光、燈光）。

### capture.mjs 新選項

| 選項 | 用途 |
|---|---|
| `--cues g4` | 擷取 G4 cue 集 |
| `--only a2_c002,a2_c004` | 只擷取指定 cue |
| `--dense a2_c002 --dense-fps 30` | 指定 cue 每格都存（`frames_dense/<cue>/`） |
| `--video` | 把高密度逐格組成 H.264 預覽影片（無聲） |
| `--probe` | 量測：`probe.json`＋`probe_report.json`（操偶線線寬、線與相鄰處 ΔL*、兒童站位背景亮度；背景是同一格隱藏角色重畫） |
| `--analysis-fps 30` | 光敏分析取樣率（預設 10） |

`flash_report.json` 新增 `near_limit`：每秒 2–3 次變化（未超標但接近上限）的區域，含畫面像素範圍、所在 cue 與 cue 內秒數。

## 3. cue 欄位（G4 新增的部分）

既有欄位見 `src/types/cue.ts` 開頭的 v1.2 第 19.3 節對照。G4 新增：

| 位置 | 欄位 | 說明 |
|---|---|---|
| cue 檔 | `set` | 舞台景：`workshop_g4`（G4 燈籠店立體書景）、`workshop`（技術骨架佔位景，預設） |
| cue 檔 | `characters.<id>` | `{ name, rig, x, z, facing }`。`rig`：`ale_v03`（圖片分件）、`standee:xiaoqing`／`standee:xiaoyu`（立牌）、`adult`／`child`（程式佔位）。紙偶名單完全由這裡決定 |
| `initialState.stage` | `set` | 景片 0 平躺～1 立好（開幕前 0） |
| | `desat` | FX8 降彩 0–1（只作用於景片） |
| | `spot`、`spotTarget` | FX4 追光亮度與對象角色 |
| `initialState.characters.<id>` | `popup` | 0＝平躺（等 `puppet.popup` 立起），1＝站好 |
| | `sit` | 正面分件紙偶坐姿：1 坐、0.5 半站、0 站 |
| | `pose` | 分件紙偶姿勢預設：`sit`、`pulled_sit`、`pulled_half`（a2_c002 結尾：半站、腕被拉到旁邊、膝被提起、左手扶桌）；立牌填姿勢名（`stand`、`reach`、`stepback`） |
| | `emotion` | `smile`／`neutral`／`confused`／`worried`／`surprised`（臉部換片；阿樂叔叔非笑時換困惑頭） |
| | `hand` | B 側手起始：`chest`／`grab`／`lap` |
| cue | `music` | 段落內配樂切換 `[{ id, at, loop, fade, gain, offset }]`，交叉淡入淡出；`id:"none"` 淡出 |
| cue | `musicLevel` | 配樂基準音量（省略時依種類：劇情 0.8、題卡 0.06、署名卡 0） |
| cue | `musicLoop` | `audioId` 那首是否循環（預設 true） |
| `lines[].text` | 手動換行 | `\n` 強制換行、`\n\n` 強制換頁；只影響排版，配音比對與字數統計會去掉（`plainText()`） |
| `quiz.question`、`quiz.options` | 手動換行 | 題卡以 `white-space: pre-line` 顯示 `\n` |

時間參照（`start`、`at`）可寫台詞編號：`"a2_c002_01"`、`"a2_c002_01.end+0.25"`、`"end-1.0"`。**換上正式配音後長度改變，動作會自動跟著移**——G4 的揮手、扯膝、小晴換姿勢、慢推都錨在台詞上。

## 4. 動畫名稱表

### 舞台層（沒有 `target`）

| 名稱 | 參數 | 預設長度／緩動 | 說明 |
|---|---|---|---|
| `title.fadeOut` / `title.fadeIn` | — | 1.0／0.9 s，sine | 署名卡淡出／淡入 |
| `curtain.open` / `curtain.close` | — | 2.2 s，sine | 摺層紙布幕（G4 用 2.0 s 對齊開幕曲 3.0 s 落點） |
| `set.popup` / `set.fold` | — | 3.0／2.4 s | 景片依序立起／收攏；各景片的先後在 `workshop.ts`（G4 對齊開幕曲 3／4／5／6／7 s 的鐵琴點） |
| `light.dim` {to} / `light.restore` | to＝0.55 | 1.0 s，sine | 舞台燈 |
| `fx.desat` {to} | to＝0.55 | 3.0 s，sine | FX8 景片降彩（角色、操偶線、字幕、題卡不降彩） |
| `fx.spot` {to, target} 或 {to, sweep} | to＝1 | 2.0 s，sine | FX4 追光；`sweep:[[x,y,z],[x,y,z]]` 慢慢掃過台口（開幕用） |
| `camera.move` / `camera.cut` {to} | — | 2.5 s，sine | `to`：預設鏡位名、`"anchor:<角色>.<wrist|elbow|knee|up>"`（另可給 `dist`、`dx`、`dy`）、或 `{pos,target,fov}` |
| `quiz.show` / `quiz.hide` / `quiz.reveal`、`lamp.light` {index} | | | 不變 |

G4 鏡位（`src/stage/layers.ts`）：`g4_wide`、`g4_mid`（三人同框、下方 20% 留字幕）、`g4_mid_up`（線落下時微上搖）、`g4_push`（停格前慢推）、`g4_stage`（閉幕回台口）。錨點鏡位以該 cue t=0 的姿勢計算，整段固定（純函式）。

### 角色（`target`＝角色 id）

| 名稱 | 參數 | 說明 |
|---|---|---|
| `puppet.popup` | — | 以腳底為鉸鏈立起（略過頭再回正）；有這個動畫的角色在開始前是平躺的 |
| `puppet.enter` {from} / `puppet.exit` {to} | dx（世界單位，預設 ∓6） | 走進／走出（帶走路起伏） |
| `puppet.sit` {to} | to＝1 | 坐姿程度 |
| `puppet.waveTry` {emotion} | | 想揮手：0–30% 手抬起（意圖）→ 30–45% 線繃緊 → 42–67% 手被拉向旁邊；50% 換情緒（預設 confused）＋加眨一次；B 側手放到胸前 |
| `puppet.kneeTug` {at:[x,y]} | at＝桌邊世界座標 | 想站起（起身到半站）→ 22–34% 膝前線繃緊 → 36–50% 膝蓋被提起、腳離地 → 身體晃一下 → 44–66% B 側手扶住 `at` |
| `puppet.reach` / `puppet.wave` / `puppet.chest` {to} / `puppet.grab` {at,to} | | B 側手 |
| `puppet.lean` {to} / `puppet.move` {dx} / `puppet.tilt` {to} | | 傾身、移動、歪頭（歪頭加眨一次） |
| `puppet.pose` {pose} | 0.24 s | 立牌換姿勢＝紙片翻面（水平壓扁→換圖→展開），不交叉淡化 |
| `puppet.face` {emotion} | 瞬間 | 情緒換片＋加眨一次 |
| `puppet.blink` | 瞬間 | 加眨一次 |
| `strings.*` | 見第 5 節 | 操偶線 |

所有角色量都是時間的純函式；擺盪用 1/120 秒固定步長的彈簧阻尼模擬，每個 cue 開始（含重播、上一步、擷取跳轉）重設，所以同一時間永遠同一格（engine-test 逐像素驗證）。

## 5. 操偶線 API

| 動畫 | 參數 | 效果 |
|---|---|---|
| `strings.drop` | `anchors`（預設三條）、`stagger`（0.9 s）、`each`（每條落下時間） | 線從畫面上方一根根落下，82% 時落地、紙環由 0.6 倍彈到原尺寸扣上；落下時左右晃、扣上後擺盪幾下停住 |
| `strings.tension` | `anchors`、`to` | 張力 0 鬆垂（弧度大）～1 繃緊（拉直） |
| `strings.loosen` | `anchors`、`to`（預設 0） | 變鬆：張力降、拉力歸零；腕線鬆了手臂也慢慢放下 |
| `strings.fade` | `anchors`、`to`（預設 0.35） | 變淡（不透明度） |
| `strings.detach` | `anchors`、`stagger`（0.6 s） | 脫落：紙環打開、線往上飄出畫面。**沒有「剪斷」** |

起始狀態用 `characters.<id>.strings: ["wrist","elbow","knee"]` 與 `stringTension`。各幕的復原段（第六幕「一天一天變鬆、變淡、一根一根脫落」）用 `strings.loosen` → `strings.fade` → `strings.detach` 依序排，時間拉長（例如各 4–8 秒），就是「不是答對就好、要時間」。

外觀與規則（兒童安全界線第 2 條、v1.2 第 15.2 節、G2 一般問題第 2 項）：
- 平面紙繩：中灰紙帶（L*≈48）＋紙纖維、兩側深灰邊線、左側受光邊；不做扭絞紋。線寬 0.066 世界單位＝中景約 9 px、沿線近景 12–16 px（≥ 8 px）。不受燈光明暗影響（只跟舞台燈總量走），量得到的 ΔL* 穩定。
- 扣點只有手腕背側、手肘外側、膝蓋正面；紙環是包住肢體的紙帶（寬＝扣點處的肢體寬）。
- 線往上延伸出畫面（上端 y=15），不畫操控者。腕、肘線往畫面左（危險方位）上方；膝前線往外側上方（斜率約 0.2），走身體外側、避開頭頸。
- 深度：腕、肘線在所有部件前；膝前線在軀幹、大腿前，但在 B 側前臂與手後面（扶桌的手從線前經過，不會像多扣一處）。
- 受力順序：意圖 → 線先繃緊 → 肢體被拉偏（`waveTry`、`kneeTug` 內建時序）。

量測（`capture.mjs --probe`，2026-10-21 本機）：沿線近景線寬 12.4–16.5 px；腕、肘線 ΔL* 約 40（投影 v2 約 28）；膝前線緊鄰的是深色工作褲，ΔL* 約 8–12（靠深灰邊與受光邊分出）。

## 6. 臉部換片

- 對嘴 JSON：`audio/lipsync/<台詞編號>_v01.json`，`{ "fps": 12, "frames": [...] }`，整數 **0 閉、1 半開、2 大開、3 圓唇**（`perform.ts` 的 `LIP_SHAPES`）。沒有對嘴資料的句子用字幕時間產生佔位開合。
- 不說話時：依 `emotion` 顯示嘴型（smile→原圖或 smile；confused／worried→worried；surprised→round；其他→closed）。face.json 有 `rest_mouth` 時以它為原圖嘴型。
- 眨眼：每個角色以「角色＋cue」為種子 3–6 秒一次（重播一致），情緒轉折、歪頭、換姿勢時加眨一次；half 0.05 s → closed 0.07 s → half 0.05 s。
- 沒說話的角色：呼吸（以腳底為支點的極輕伸縮）、重心擺動；別人說話時微微傾向說話者，有頭層的立牌改為頭轉向說話者（±2.5° 內）並在句首輕點頭。

### face.json（兩種格式都接受）

1. **素材代理格式（目前 `assets/final/face/<角色>/face.json`）**：`head_image.image_id`＝錨點所依據的圖；`groups.mouth|eyes.anchor_px`＝**換片左上角**、`size`；`pieces.<mouth_closed|...>.image_id`；`rest_mouth`、`rest_eyes`。立牌拆頭時另有 `head_image.offset_in_pose_image_px`、`pivot_px` 與 `pose_image.image_id`，引擎就改用 `<姿勢圖>-body` 當身體、頭層獨立。
2. **原生格式**：`{ baseImage, mouth: { anchor:[中心x,中心y], size, z, shapes:{closed:"圖像id",...} }, eyes: {...}, perPose: {...} }`。

只有掛在 `head_image.image_id` 那張圖上時才用正式換片；其他圖（例如阿樂叔叔的一般笑臉頭、兒童的 stand 姿勢）用程式畫的退路換片（量好的眼睛、嘴巴範圍，見 `face.ts` 的 `FALLBACK_FACES`；圖被重新裁切時依不透明範圍自動平移）。換片圖 id 可以只寫檔名（例如 `chr-ale_mouth_closed`），素材庫會用檔名找到 `face/ale/chr-ale_mouth_closed`。

## 7. 分件紙偶（阿樂叔叔）

- 分件資料：`assets/final/rig/ale_rig.json`（素材代理 v04 格式：部件圖已裁切、`origin_master`、`pivot_master`、`layers_back_to_front`；`head_worried` 這類「名稱_變體」自動當同樞紐替換部件）。缺 v04 時退回 `assets/parts/ale_v03/parts.json`（整張畫布格式，`asset-sources.json`）。
- 扣點：`assets/final/rig/ale_attach.json` 的 `points.wrist_back|elbow_out|knee_front.master_px`（母版座標）；沒有就由部件外形自動找。紙環寬＝扣點處沿肢體法線量到的寬度。
- 整體外輪廓描邊：每個部件依外形膨脹出背板（白色紙芯 12 px＋深色卡紙側邊 6 px，往右下偏 3–4 px 像紙厚），所有背板放在所有部件後面 → 只描整體外輪廓（素材的 `-outline` 圖目前不用）。
- 接縫：v04 已修正（`fix_log`）就不處理；v03 退路會清除肩、膝舌片的深色弧線（只在舌片圓內、下面有後層部件的邊緣帶）。
- 正面視角姿勢：坐姿＝大腿透視縮短（朝鏡頭）、小腿近乎垂直；半站＝骨盆升高、大腿變長；扯膝＝膝蓋往上提、小腿垂下（腳離地）。扣膝前線那條腿坐著時張得較開，讓膝前線走身體外側。
- 頭部替換：`emotion` 為 smile 用 `head`，其他用 `head_worried`（面部換片在 `head_worried` 上用正式圖，在 `head` 上用退路眨眼）。

## 8. 立牌（小晴、小宇）

`BUILTIN_RIGS['standee:xiaoqing']`：`poses: { stand: chr-xiaoqing_master, reach: chr-xiaoqing_pose-reach-worried }`、高 2.5；小宇 `stand`／`stepback`、高 2.42（cue 裡 `facing: -1` 讓他面向阿樂叔叔）。各姿勢以腳底中心對齊，頭頂自動偵測（舉起的手不算），讓不同姿勢圖的角色高度一致。原圖已有白邊，程式只加深色卡紙側邊。

## 9. 景（workshop_g4）

| 素材 id（assets/final） | 用途 | 缺圖時 |
|---|---|---|
| `bg-workshop-back` | 背牆（寬 21、底邊對齊地面；自發光 0.32 讓兒童身後在投影 v2 ≥ 0.50） | 程式畫的和紙牆 |
| `bg-workshop-floor` | 地板（重複貼） | 程式畫的木地板 |
| `bg-workshop-table` | 工作台（桌面板在圖高 216 px 處 → 桌面 1.40；左端 x=−2.32） | 程式畫的工作台 |
| `bg-workshop-lanterns` | 吊燈籠（右上高處，只在大全景看得到） | 不放 |
| `bg-workshop-wing` | 左側竹篾束前景 | 不放 |
| `tex-titlecard-paper` | 署名卡紙（字由程式排「許博明老師製作」） | CSS 紙卡 |
| （程式畫） | 抽屜櫃、竹篾架、圓凳、左下燈籠堆、右下紙卷、摺層布幕、台口 | — |

站位：阿樂叔叔 x=−2.6（左＝危險方位）、小晴 x=1.85、小宇 x=3.35（右＝安全方位）。每張景片烘進 5–6 px 卡紙厚度，投柔影（PCF、強度 0.45）。

`tex-curtain-paper` **目前不用**：平均 R/(R+G+B)=0.815（飽和紅），布幕收攏時摺頁明暗交替，飽和紅區域的變化會被光敏分析計入。布幕用程式畫的暗紅褐紙（#8c4632，非飽和紅）。若主線要用素材紙紋，請先把色相往褐色移到比值 < 0.8。

## 10. 音訊

| id | 用在 | 說明 |
|---|---|---|
| `music_opening` | a0_c001 at 0（不循環） | 3.0 s 落點＝布幕全開 |
| `music_m4_strings` | a2_c002 at 0（不循環，`offset: 4.0`） | 從第 4 秒開始，第一條線落地對上 11.5 s 撥弦短句 |
| `music_m4_light` | a2_c004 at 0（循環） | 很輕版，停格時繼續 |
| `music_closing` | a8_c002 at 0.9（不循環） | 布幕合攏 → 署名卡 |
| `music_town` | （G4 未用） | 留給 a2_c001 |
| `sfx_curtain_open`／`sfx_curtain_close` | 布幕開始動時 | |
| `sfx_string_drop` | 每條線落地前 0.5 s（音效扣上點在 0.5 s） | |
| `sfx_string_taut` | 腕線繃緊、膝前線繃緊 | |
| `sfx_paper_rustle` | 景片立起 | |

缺檔：準備畫面與 `getState().missingAudio` 列出，該處無聲，照常演出（engine-test 第五段）。對白避讓：說話前 0.15 s 壓到 0.32（約 −10 dB），相鄰兩句間隔 < 0.9 s 不回升，最後一句後 0.3 s 回升（`ducking.ts`，engine-test 第二、六段）。

## 11. 時間與長度（目前素材）

署名卡待機 → 開幕 10.6 s → a2_c002 22.8 s → a2_c004 19.5 s → 閉幕 3.1 s＋署名卡 1.4 s。a2_c002＋a2_c004＝42.3 s（規格 30–45 s）。正式配音換版後長度會變，動作錨在台詞上會跟著移；換版後請重跑 `engine-test` 與 `capture`，確認仍在 30–45 s。

## 12. 整合代理要做的事

1. **輸出驗收包**：`node tools/capture.mjs --cues g4 --probe --out review/G4/<子資料夾>`（加 `--dense a2_c002,a2_c004 --video` 可做逐格與預覽影片），交給投影模擬、並排、響度等其他 tools 腳本。
2. **正式素材對照**：目前所有角色、景、臉部換片、音訊都已從 `assets/final`、`audio/` 接上（退路只剩 `rig/ale_v03` 的整張畫布部件，`ale_rig.json` 在時不會用到）。若素材代理改了檔名或格式，請對照第 6–9 節；需要覆寫時可在 `assets/final/g4_manifest.json` 寫 `{"characters": {"ale": { "rig":"parts", "parts":"rig/ale_rig", "height":3.55, ... }}}`（欄位見 `cast.ts` 的 `PartsCharConfig`／`StandeeCharConfig`）。
3. **退路換片換正式圖**（建議）：阿樂叔叔一般笑臉頭的眨眼、小晴與小宇 `stand` 姿勢的眨眼與嘴型，目前是程式畫的；素材代理若補 face.json（`head_image` 指向 `chr-ale_head`、`chr-xiaoqing_master`、`chr-xiaoyu_master`），引擎會自動改用。face.json 一個角色只能有一個基準圖；要多張時用原生格式的 `perPose`。
4. **坐姿腿**：角色表 1.3 說有「站姿腿與坐姿腿兩組」；目前坐姿是大腿透視縮短做的。若素材代理產出坐姿腿件，可做成 `thigh_l_sit` 這類替換部件（命名規則同 `head_worried`），需要在 `perform.ts` 的 `poseFront` 依 `sit` 切換（目前只切頭）。
5. **布幕紙紋**：見第 9 節，素材紙紋需先調色。
6. **配音換版後**：檢查 a2_c002 的揮手（9.9 s）與第一句（13.0 s 起）之間的空檔、`music_m4_strings` 撥弦點是否還對得上；需要時只改 g4.json 的時間數字。
7. **Windows 學校筆電**：本機只在 Apple M4 驗過效能；請以 `?q=B` 對照 A 級，並把探針結果回填（B 級關閉 alphaToCoverage、陰影 1024）。

## 12a. 整合代理變更（2026-10-21 第 2 天）

| 檔案 | 變更 |
|---|---|
| `cues/g4.json` | `a8_c003`（片尾署名卡）加 `musicLevel: 0.8`。原本署名卡種類預設配樂音量 0，閉幕曲在署名卡出現（主題句進入）時會被壓到無聲；現在閉幕曲照 `review/G3/music.md` 的同步點播完、自然淡出。片頭 `a0_c000` 仍是 0（待機無配樂）。 |
| `src/stage/strings.ts`、`src/stage/stage.ts` | 只加量測欄位：`PaperString.last.bow`、`probe()` 的 `strings[].path` 與 `actors[].headBox`（驗收包量線到頭部框的距離、線是否經過兒童立牌）。畫面不變。 |
| `../tools/g4_review_pack.mjs`、`g4_review_pack.py`、`g4_transcripts.py` | G4 驗收包產生器（輸出 `review/G4/pack/`，見該處 INDEX.md）：capture.mjs 30 格／秒光敏＋量測、播放錄製（固定步長 30 格／秒＋依引擎規則離線混音）、a2_c002 每秒 8 格條帶、4:3 關鍵影格、投影模擬、效能（即時播放）、響度、逐字稿差異。 |

## 13. 已知限制

- FX7 景深（逐層模糊）沒做；長焦透視＋層間柔影提供深度。
- 阿樂叔叔是正面紙偶，轉頭只做歪頭；兒童只有拆了頭層的姿勢能轉頭（±2.5°）。
- 膝前線與工作褲的 ΔL* 約 8–12（腕、肘線約 40）；線的深灰邊與受光邊仍分得出，請驗收者判斷是否接受。
- 光敏：10 格／秒分析通過（最多每秒 3 次）；`near_limit` 主要是沿線鏡頭移動與字幕換頁。要更嚴謹請用 `--analysis-fps 30` 重跑。
- 聽感、實際投影、學校硬體效能都無法由代理驗證。
