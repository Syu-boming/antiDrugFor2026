# G5 共用美術：檢查圖與報告

2026-10-21 第 2 天下午，共用美術代理。多幕共用的角色立牌、景與道具。素材登記見 ASSETS.md「G5 共用美術」一節。

## 1. 交付了什麼

| 類別 | 檔案 | 狀態 |
|---|---|---|
| 新角色立牌 | `assets/final/chr-{pinan,lin,chen,ye}_*_v01.png`：品安（站、P-PA1 坐長椅綁燈籠、抓背帶走路）、林老師（站、P-LIN1 蹲、P-LIN2 坐）、陳伯伯（站）、葉護理師（站、P-YE1 蹲） | image_gen，每張 1 次 |
| 兒童補姿勢 | `chr-xiaoqing_pose-{cross,palmno,forehead,walk}_v06.png`、`chr-xiaoyu_pose-{cross,palmno,forehead,walk,watch-dial}_v06.png` | image_gen，每張 1 次；主色調回 v04 色票 |
| 邀請者 | `chr-inviter_hand-box_v01.png`（只有手＋貼紙盒，左緣入畫）、`props/prop-sticker-box_v01.png`（盒子特寫） | image_gen 1 次（一張兩件） |
| 臉部 | 新角色：`face/{pinan,lin,chen,ye}/` 正式換片＋`face_v01.json`；兒童新姿勢：`rig/show_characters.json` 的 `fallbackFaces` | 程式 |
| 角色設定 | `assets/final/rig/show_characters.json`（6 個角色、18 個退路臉部） | 程式 |
| 廣場景 | `sets/square/set-square_*_v01.png`（G2 拼版切件）＋`layout.json` | 不重抽 |
| 校門口景 | `sets/gate/set-gate_*_v01.png`＋`layout.json` | **程式繪製退路版**（見第 4 節） |
| 道具 | `props/prop-bench_v01.png`、`prop-truck_v01.png`、`prop-truck-wheel_v01.png` | **程式繪製退路版** |

## 2. 檢查圖（這個資料夾）

| 檔案 | 看什麼 |
|---|---|
| `contact_characters.png` | 全部角色與姿勢，依 show_characters.json 的縮放排成舞台比例（紅線地面、藍線長椅座面 0.92） |
| `contact_props_sets.png` | 邀請者、道具、景片 |
| `contact_faces.jpg`、`faces/*.png`、`faces_pieces/*.png` | 臉部放大：原圖／眼框嘴框／半閉／閉眼（兒童＝退路換片模擬；新角色＝正式換片含全部嘴型） |
| `projsim/*_sheet.jpg` | 每張圖的投影模擬四聯圖（原圖／投影 v2／灰階／綠色弱），tools/projsim.py |
| `sets/{gate,square}_preview_<鏡位>.png`、`_proj.png` | 舞台尺寸預覽（Python 針孔相機近似引擎鏡位，平光；不是引擎擷取） |
| `engine_smoke/*.png`、`smoke.json` | 在真的引擎裡（G5 段落檔現有 cue）確認新角色建得起來、臉部模式 |
| `checks_summary.json` | 逐檔自動檢查總表 |
| `import.json`、`import_props.json`、`scale_report.json`、`blink_check.json`、`blink_check_pieces.json`、`face_boxes.json`、`face_boxes_manual.json`、`sets/*_import.json`、`sets/preview_report.json` | 原始數據 |
| `raw/` | Codex 原檔（不改）、提示、參考圖清單、執行紀錄；`_run.sh` 重抽用 |
| `scripts/` | 全部產生腳本（可重跑） |

## 3. 自動檢查結果（checks_summary.json）

- 透明霧邊：19 張生成圖離輪廓 >3 px 的殘留 alpha 全部 0 px（lin 母版 3 px）。
- 白邊：紙芯白邊 7–12 px、連續（葉護理師白邊外多一圈 1–2 px 深色細線，引擎另加深色卡紙側邊，看起來一致）。
- 裁腳：原圖四邊都沒碰到畫布（邀請者的手刻意從左緣入畫）。
- 色差：兒童主色與 v04 母版 ΔE（吊帶褲 1.2–2.6、外套 2.2–4.8；上衣、短褲 ≤8）；平光（角色左右半邊 L* 中位差）≤4.1，只有小宇 cross 15.2（雙臂交叉的構圖造成，不是打光）。
- 兩眼同閉：小晴、小宇 9 個新姿勢（退路換片模擬 face.ts drawFallback）全部通過：每隻眼原本深色像素殘留 ≤2.3%、高光殘留 ≤2 px、閉眼線 ≥99 px、補片溢出到頭髮／臉緣 ≤20 px。新角色 9 個姿勢用正式換片：殘留 0%、溢出 ≤13 px。
- 真的引擎（engine_smoke/smoke.json，G5 段落檔 a1_c001、a2_c012、a3_c003、a4_c001、a5_c001）：品安、林老師、陳伯伯、葉護理師全部姿勢＝正式換片；小晴、小宇 9 個新姿勢＝退路換片（fallbackFaces 已被引擎併入）；主控台錯誤 0。layout.json 兩個景還沒有 cue 使用，引擎裡沒有實際建過（只有 Python 預覽）。typecheck、build 通過；engine-test 125／125。
- 兒童身後背景（投影 v2，平光預覽，隱藏角色重畫）：校門口 0.53–0.56（≥0.50）；廣場 0.47–0.48（差 0.02–0.03，layout.json 已給騎樓自發光 0.3，正式值請以引擎擷取為準）。

## 4. 沒做到、要注意的（照實寫）

1. **image_gen 額度用完**：15:01 啟動的 5 張（校門口遠景、中景景片、前景、小貨車、長椅）回「usage limit，19:50 後再試」，沒有產出也沒有消耗。校門口與兩個道具改用程式繪製（平塗色塊＋G2 同款紙紋，無陰影無文字）。和生成圖並排時手繪感較弱、細節較少。提示都在 `raw/`，19:50 後可在 `raw/` 執行 `./_run.sh set_gate_back_v01 set_gate_mid_v01 set_gate_fore_v01 prop_truck_v01 prop_bench_v01`，抽到的圖以 v02 放進同一位置即可（長椅換圖要重量座面高）。
2. **比例**：站著的姿勢讓引擎自動把腳底到頭頂拉成同一身高（G4 做法）；生成的姿勢圖頭身比有些微漂移（小宇 palmno、walk 頭略大，dial 低頭頭略小），翻面時頭的大小會差約 5–12%。坐、蹲以頭部大小換算虛擬 headTop。
3. **小晴 forehead／walk 的星星髮夾在另一側**（生成時把角色鏡像畫了）：等於 facing:-1 翻面的樣子，引擎翻面本來就會這樣；同一場若同時用原朝向的姿勢和這兩張，髮夾會左右跳，排戲時注意。
4. **還沒有的**：林老師背面（a4_c001 警衛室窗內）、陳伯伯 P-CH1 扶阿樂（可選）、導護旗、小晴／小宇「指右」（H2，口訣「先離開」；可暫用 reach 翻面）、P-QG2／P-XY3 坐醫院長椅、品安「偷偷回頭看」頭層（P-PA1 的頭沒有拆層）。
5. **小貨車是靜態景片**（layout.json 的 `prop-truck`，停在對面）；要開進來需要第四幕用程式景（`src/sets/<景>.ts`）移動它，輪子另有 `props/prop-truck-wheel` 可疊上去轉。
6. **聽感、實際投影、學校硬體**：無法由代理驗證。
