# G6 修正後重驗｜驗不通過項（第 2 輪，2026-10-22 20:4x）

- 驗收者：G6 重驗代理（v1.3 §4.4：重驗 2 位，本人負責「驗不通過項」）。
- 依據：RUBRICS.md、CLAUDE.md 安全界線（第 9 條）與固定需求、v1.3 §8、v1.2 §24、REVIEW.md 主線裁定（細格 fine_32x18 ≤3；全畫面亮度相差 >20% 不得一格硬切；±1 LU 以對白響度與主奏段差 ≤2 LU 判讀）。
- 對照的上一輪報告：review/G6/qa/principal.md、director.md、tech.md。
- 材料：review/G6/pack/（INDEX.md 20:34、delivery/delivery_smoke.md 20:03）、review/G5/<段>/pack/（18:39–19:44 重產）、teacher/（20:03 重建）、交付/、app/dist（20:00 建置）。
- 自己抽的證據都在 review/G6/qa/r2_failed/：
  - `r2_brightness.py`／`r2_brightness.json`：九段播放錄製逐格解碼（320×180 area，和驗收包 128×72 不同的獨立方法）：孤立單格全畫面線性亮度比、非孤立單格大跳變、黑場（gamma 亮度 YAVG<25）次數與位置、3 秒內連兩次黑場；`step_on_ramp.json`（漸變中夾帶硬切的單格：0 筆）；`<段>_lin.npy`／`<段>_yavg.npy` 逐格序列。
  - `fingerprints_now.json`：`node tools/seg_fingerprint.mjs` 目前段落指紋，逐段和各驗收包 segment_hash.json 比對。
  - `engine_test_rerun.log`：我自己重跑 `node tools/engine-test.mjs`（138／138）。
  - `teacher_docs_check.txt`：`node tools/teacher_docs.mjs --check`（結束碼 0）。
  - `loudness_a8_r2.txt`：主奏段三段響度、a8 每秒短期響度與靜音偵測。
  - `asr3.py`／`asr3.json`／`mix_*.wav`：上一輪「可能被蓋住」的 3 句，從目前混音切出後用 faster-whisper small 與 large-v3-turbo 轉寫。
  - 影格條：`a2_c001_c004.jpg`、`a2_c013_fades.jpg`、`a4_c002_trans.jpg`、`a5_c005_open.jpg`、`a6_c007_climax.jpg`、`a6_c007_kids_crop.jpg`、`a8_c001_bows.jpg`、`a7_c002_card_end.png`（`_small.jpg`）。
- 聽感、實際投影、學校筆電、Windows 實機、110 人現場：**未驗證**，不計分。

## 一、嚴重問題逐條判定

### S1　a3_c008 一格亮度 +29.5% → **resolved**
- 驗收包：review/G5/a3/pack/isolated_cuts.json 最大 1.142（a3_c001），over_limit 0；a3_c008 那一格 1.105。
- 我自己量（r2_brightness.json，a3 第 5072→5073 格＝a3_c008 第 34.54 秒）：0.4192 → 0.4621，**1.102 倍**；之後 34.87–35.67 秒以每格 ≤1.4% 慢慢回到 0.546（light.restore，約 0.8 秒漸變），不是第二次硬切。
- 九段孤立單格比最大：a0 1.123、a1 1.116、a2 1.117、a3 1.137、a4 1.151、a5 1.129、a6 1.150、a7 1.129、a8 1.126，**>1.2：0 筆**。和驗收包 (a) 欄（1.121–1.159）一致，差 ≤0.008。
- 另查「漸變中夾帶硬切」（單格跳變 >1.2 且 >前後格變化 1.6 倍）：0 筆（step_on_ramp.json）；非孤立 >1.2 的單格都在 0.3 秒左右的 fade.out／fade.in 中、逐格均勻變化。
- 驗收工具已補上判定：act_review_pack 寫 isolated_cuts.json（>1.2 判光敏不通過），INDEX (a) 表有「孤立亮度比」欄。
- 九段官方光敏 16×9 與 fine_32x18 都 ≤3、超標 0（G6 INDEX (a)）。

### S2　交付包是舊建置 → **resolved**
- review/G6/pack/delivery/delivery_smoke.md（20:03）：交付/browser 與 交付/AntidrugTheater/resources/app/dist 都和 app/dist 逐檔相同（143 檔，不同 0、缺 0、多 0）；不加參數載入全劇 71 個 cue；配音、配樂音效齊全；八題印章 2、3、1、1、3、2、3、2；片頭片尾署名卡「許博明老師製作」、兩張截圖逐位元組相同；外部請求 0；頁面錯誤 0；Electron 外殼 main.js／preload.js／layout.js／package.json 和原始碼相同。
- 我自己在 20:4x 重跑 `diff -rq 交付/browser app/dist` 與 `diff -rq 交付/AntidrugTheater/resources/app/dist app/dist`：都沒有差異。app/dist 是 20:00:11 建置，段落檔最後修改 20:00:04（a2、a4、a6、a8 的 atMinute），交付包和驗收包量的是同一版。
- 段落指紋：目前 9／9 段的 source 與 built 都和各驗收包 segment_hash.json 相同，builtFromSource 9／9（fingerprints_now.json）。
- 仍未驗證：Windows 實機執行 AntidrugTheater.exe（使用者第 3 天前實測）。

## 二、上一輪一般問題逐條判定

| # | 來源 | 問題 | 判定 | 證據 |
|---|---|---|---|---|
| 1 | 校長1／導演1／技術G2 | 教師資料查核點時間比 cue 舊 | resolved | teacher_docs --check：cue 指紋 0f6f4055f3 三方一致、結束碼 0；講稿第 33–36、446 行與一頁操作卡 PDF 都是 13:15／23:48／31:25／35:00＝atMinute 13.25／23.8／31.42／35；「落後約 40 秒是正常的」已刪 |
| 2 | 校長2 | Q6、Q7 回饋先講劇情、Q7 超時 | resolved | 講稿第 385 行 Q6「……回到安全的地方找大人。等一下看看小晴和小宇怎麼做。」；第 406 行 Q7 不再提小宇，約 45 字 |
| 3 | 校長3 | 講稿留製作備註 | resolved | 講稿搜尋 v0x、v1.x、角色表、timeline.ts、指紋、時長估算：0 筆 |
| 4 | 校長4 | 備援影片還沒做 | partial | `node tools/backup_video.mjs --acts all --out 交付/backup_video` 20:36 起正在算（只有 _check/_work_a0 暫存）；teacher_docs --check 回報缺 backup_a0–a8.mp4；講稿第 499 行、故障一頁卡、觀課導覽單、教案仍寫「備援影片（暫定）」並有跳到紙本題卡的退路 |
| 5 | 校長5／技術S2 | 交付資料夾是舊版 | resolved | 見 S2 |
| 6 | 校長6／導演7／技術G1 | >100 ms 卡頓 10 次、分類有誤 | resolved | live/perf.json：stalls_over_100ms 0（播放中 0、停格中 0）、p95 16.70 ms、最大 33.3 ms；分類改成「fade 黑格內／不在」與停格；停格中 >50 ms 13 格、最長 100.0 ms（不算卡頓，學校筆電未驗證） |
| 7 | 校長7 | 人力配置三份資料不一致 | resolved | 講稿第 54 行、觀課導覽單第 52–53 行、教案第 210–213 行都是「主講 1、協助教師 1（記錄區排座位與發獎）、技術協助選配、最低配置主講＋導師」；揭答欄改「協助教師記錄區、排、座位」 |
| 8 | 校長8 | a7 口訣卡句號被切 | resolved | a7_c002_card_end.png：卡片「不碰、不試；先離開，找大人」，句尾沒有句號，整行在卡內 |
| 9 | 導演2 | 3 秒內連兩次黑場（a2_c013、a4_c002） | resolved | r2_brightness.json double_black_within_3s：九段都 0；a2_c013 只剩段首預捲一次黑（a2_c013_fades.jpg：窗景→筆記本→孩子都沒有經過全黑）；a4_c002 只剩 15.21 秒一次，之後是地圖與立起的小屋（a4_c002_trans.jpg） |
| 10 | 導演3 | 高潮 a6_c007 一排人站著 | resolved | a6_c007_kids_crop.jpg：主燈亮起後小晴、小宇、品安轉頭朝主燈，主燈明顯變亮；仍是橫排構圖（記錄，不扣到 3） |
| 11 | 導演4 | 黑場太多（45 次、a2 12 次） | resolved（達到導演設定的 a2 ≤8） | 我量全劇 40 次（a0 2、a1 3、a2 8、a3 5、a4 8、a5 4、a6 5、a7 3、a8 2），每次 0.24–0.5 秒；a2_c003、a2_c004 不再經過黑場；其中約 16 次是題卡進出、8 次是段落接縫預捲 |
| 12 | 導演5 | a5_c005 開頭空景 6.5 秒 | resolved | a5_c005_open.jpg：0–2.5 秒畫面有長椅上的阿樂叔叔與導護旗，約 3 秒切到校門孩子；沒有「叔叔不見了」的空鏡 |
| 13 | 導演6 | 謝幕只點頭、阿樂叔叔坐著 | resolved（前傾鞠躬未驗證） | a8_c001_bows.jpg：約 11–12 秒阿樂叔叔站起、舉小燈籠、有單獨的近景，之後站著和大家一起；身體前傾的幅度在每 1.5 秒抽格中看不清 |
| 14 | 導演8／技術G8 | sfx_ambulance_engine 改名、FLIP_BLINK_GAP 0.3 | not（主線裁定不改，記錄放行） | a5.json 仍 1 處引用；perform.ts 第 340–341 行仍用 FLIP_BLINK_GAP；REVIEW.md G6 第 1 輪主線裁定：名稱正確、0.3 秒維持以免動到 G4 基準 |
| 15 | 技術G3 | a8 主奏段相差 4 LU、例外理由不對 | resolved | loudness_a8_r2.txt：開幕 −19.6、謝幕 music_bows −19.3、閉幕 −17.8 LUFS，相差 1.8 LU（≤2）；對白各段最大偏差 0.4 LU；REVIEW 已撤回「閉幕淡出」理由。附帶：18.2–25.4 秒數位靜音 7.2 秒（見一般問題 3） |
| 16 | 技術G4 | a4 包比 a4.json 舊、只比長度 | resolved | 各包有 segment_hash.json；show_review_pack 比 sha1；我重算 9／9 相同 |
| 17 | 技術G5 | 缺配音仍可直接開演 | resolved | engine_test_rerun.log 第 95–96 行：缺 1 句配音時準備畫面列出、第一次按「準備播放」不開演、按鈕改「仍要播放（缺 1 句配音）」 |
| 18 | 技術G6 | 3 句在混音中兩個模型都轉錯 | partial | asr3.json（目前混音）：a1_c001_05 small 正確「你是青蛙燈嗎」（large 仍「丹」）；a0_c004_01 large「阿乐叔叔早哲哲早」讀音對、small「早早早早」；a6_c009_01 兩個模型仍都錯開頭「叔叔」（small「儲說」、large「楚叔」）。a0、a1、a6 包裡的 transcripts.json 還是 10-21 的舊檔（a0–a4 用 --skip-asr），驗收包沒有新證據 |
| 19 | 技術G7 | 資料包與載入沒有餘量 | not（未改）／學校未驗證 | app/dist/data 417 MB、交付/AntidrugTheater 795 MB；開頁到片頭 7.47 秒、JS heap 215–266 MB（perf.json） |
| 20 | 技術 (b) 補充 | 驗收包工具：孤立單格亮度比、段落指紋 | resolved | INDEX (a) 已有兩欄；isolated_cuts.json 九段都有 |

## 三、這一輪的一般問題（照重要程度，可照做的修法）

1. **備援影片還沒完成，教師資料仍寫「暫定」**（v1.3 §8 交付物、v1.2 §24 第 13 項「3 分鐘內切到備援」）。
   - 位置：交付/backup_video/（目前只有 _check/_work_a0 暫存）；teacher/教師講稿.md 第 499 行；故障一頁卡、觀課導覽單、教案 PDF。
   - 修法：等 backup_video.mjs 跑完，確認 backup_a0–a8.mp4 九檔、每 cue 一章；刪掉 `交付/backup_video/_check`；重跑 `node tools/teacher_docs.mjs`（自動改寫實際檔名、拿掉「暫定」），`--check` 結束碼 0；在 delivery_smoke 加一項「備援影片 9 檔、章節數＝cue 數、可播放」，再跑一次。
2. **a6_c009_01「叔叔，又到紙燈節了！」在混音中兩個模型仍都轉錯開頭；a0–a4 與 a6 包的轉寫是舊檔**。
   - 證據：r2_failed/asr3.json；review/G5/a0、a1、a6/pack/transcripts.json 修改時間 10-21。
   - 修法：在 a6_c009 第一句前後 0.3 秒把 musicLevel 再壓 2–3 dB（或換曲淡入延後到第一句結束）；九段驗收包不加 --skip-asr 重跑轉寫，讓 transcripts.json 對應目前混音；彩排時人耳確認這三句。
3. **a8 謝幕音樂結束到閉幕音樂之間有 7.2 秒數位靜音**（loudness_a8_r2.txt：silence 18.20–25.42 秒；a8_c001 播完後的停格加上 a8_c002 開頭約 3.3 秒）。現場老師停得越久，靜音越長，布幕合攏前會「斷電感」。
   - 修法：music_closing 在 a8_c002 第 0 秒就淡入（0.8 秒），或在 a8_c001 停格期間鋪一層 −28 LUFS 左右的低音量延音；改完重算主奏段三段，差 ≤2 LU。
4. **驗收包的 engine-test 記錄 137／138（「再按句點鍵繼續」）**：G6 INDEX (e)、ops/engine_test.log 第 14 行（暫停後 500 ms 只走 0.256 秒，門檻 0.3）。我在背景有備援影片算圖的負載下重跑仍是 138／138（engine_test_rerun.log 第 13 行 1.428→1.924），判斷是系統負載造成的時間邊界值，不是功能壞掉。
   - 修法：engine-test 這一項改成輪詢到 1 秒內 cueTime 前進 ≥0.3 秒就通過；驗收包在負載低時重跑一次，讓 INDEX 不留失敗紀錄。
5. **學校筆電上的停格預先建景沒有餘量的證據**：停格中 >50 ms 13 格、最長 100.0 ms（M4）；資料 417 MB、載入 7.5 秒。學校筆電慢 3 倍時，預先建景可能還沒完成老師就按下一步。
   - 修法：探針回來後用 `show_review_pack --perf-only` 在學校筆電跑畫質 B 與鎖 30 fps 兩種；加一項測試「cue 播完 0.2 秒就按下一步」，確認 set.swap 會等預先建景完成並藏在 fade 黑格內；故障卡寫明第一次開啟約要等多久。

## 四、低於 4 分的項目重新評分（1–5；4＝G4 基準）

| 項目 | 上一輪 | 這一輪 | 理由與證據 |
|---|---|---|---|
| 導演｜表演與節奏 | 3 | 4 | 3 秒內兩次黑場 0（r2_brightness.json）；黑場 45→40、a2 12→8；a6_c007 孩子轉頭看主燈、主燈加亮（a6_c007_kids_crop.jpg）；a5_c005 空鏡縮到約 2.5 秒且有阿樂叔叔（a5_c005_open.jpg）；a8 阿樂叔叔站起舉燈（a8_c001_bows.jpg）。不給 5：高潮仍是橫排構圖、黑場仍約 33 秒一次、a8 有 7 秒靜音 |
| 技術｜效能 | 3 | 4 | >100 ms 卡頓 0、p95 16.70 ms、最大 33.3 ms、JS heap 215–266 MB、斜率 0.68 MB／分（live/perf.json）。不給 5：學校筆電、耐熱都未驗證，停格長格最長 100 ms、資料 417 MB 沒有餘量證據 |
| 技術｜同步（含光敏） | 3 | 4 | S1 修好：孤立單格比全劇最大 1.151（我量）／1.159（包），>1.2 0；九段官方光敏 ≤3、超標 0；字幕時間差最大 3 ms、內容 3054 筆 0 不符；嘴型 125／127。不給 5：a6_c009_01 在混音中兩模型仍轉錯、a0–a4 轉寫沒有重跑 |
| 技術｜穩定與離線 | 3 | 4 | 交付包與建置逐檔相同、冒煙測試全部通過、外部請求 0、頁面錯誤 0；缺配音要二次確認；engine-test 重跑 138／138。不給 5：Windows 實機未驗證、備援影片還沒完成、驗收包的 engine-test 紀錄留著 1 項時間邊界失敗 |

其餘項目上一輪都 ≥4（校長 4／4／5／4；導演其他 4 項 4；技術操作 4），本輪不重評。重評後三視角：校長平均 4.25、導演 4.0、技術 4.0；各項中位數都 ≥4。

## 五、帶問題放行項目回查（G3、G4、G5 兩批）

| 來源 | 項目 | 判定 | 證據 |
|---|---|---|---|
| G3 | 自動檢查未通過 23 句 | 未驗證 | 要聽感；混音中兩模型都錯的剩 a6_c009_01（asr3.json） |
| G3 | PSOLA 重後製失真 | 未驗證 | 要聽感 |
| G3 | 配音 14.15 分，G5 依實際句長排時間 | resolved | 預錄 1322.3 秒，教師時間＋播放 35.75 分 ≤38（INDEX (a)） |
| G3／G4 | a2_c002＋c004 超過 45 秒 | resolved | 以全劇時間判，餘 135 秒 |
| G4 | a2_c002_02 被 sfx 蓋住開頭 | 未驗證 | a2 包轉寫沒有用目前混音重跑 |
| G4 | 半閉格眼皮雜點、閉眼補片明暗差 | 未驗證 | 本輪沒有逐格放大臉部 |
| G4 | 小宇 stepback 眼白殘影 | 未驗證 | 同上 |
| G4 | 翻面到第一次眨眼 0.32 秒 | not（主線裁定維持） | perform.ts 第 340–341 行 |
| G4 | ElevenLabs 用量指向 ledger.json | resolved | ASSETS.md 第 88、142 行 |
| G4 第 2 輪 | 膝前線到頭部框距離 | 未驗證（交安全視角） | INDEX (a) 線到頭部最短 a5 10.4 px、線經過兒童 0 |
| G5 一階 | 控制台與教師資料查核點一致 | resolved | teacher_docs --check 結束碼 0 |
| G5 一階 | 換景全暗格 83 ms | resolved | >100 ms 0 次（perf.json） |
| G5 一階 | 全劇 1391 秒多於預估 | resolved | 1322.3 秒 |
| G5 一階 | 資料包 212 MB、學校記憶體 | not（417 MB）／未驗證 | du app/dist/data |
| G5 一階 | Electron 只在 macOS 跑過 | 未驗證 | 交付包已是新建置，Windows 待實測 |
| G5 第一批 a1 | Q1 點燈後連兩次暗亮 | resolved | a1 黑場只在 a1_c007 4.94 秒一次，a1_c008 沒有 |
| a1 | 切近景前一格亮 11% | resolved | a1 孤立最大 1.116、漸變夾硬切 0 |
| a1 | 小晴翻面 0.15 秒、品安轉身 | 未驗證 | — |
| a4 | a4_c002 轉場露俯視與布幕、空天空 | resolved | a4_c002_trans.jpg：一次黑場後直接到地圖與立起小屋，沒有天空鏡 |
| a4 | 地圖色塊與影子殘影、兒童身後投影 | 未驗證 | — |
| a4 | sfx_ambulance_engine 改名 | not（主線裁定不改） | a5.json 1 處 |
| a2 | a2_c012 求助鏡頭太短 | 未驗證 | 本輪未抽 |
| a2 | 膝線對比、手部簡化 | 未驗證 | — |
| a0 | 摺紙縮成點、折折被擋、空牆、吊牌 | 未驗證 | — |
| 共同 | 揭答蓋章聲起音 | partial | sfx_stamp_v02 峰值降 3.7 dB（上一輪技術 QA 數據），聽感未驗證 |
| G5 第二批 a5 | 小朋友粗模、救護人員頭浮、景片平 | 未驗證 | — |
| a6 | 灰色無臉人影 | resolved（抽樣） | a6_c007 影格條沒有出現 |
| a6 | Q8 孤字斷行 | resolved | 上一輪三位都確認，題卡文字未改（quiz.json 8／8） |
| a6 | a6_c007 中段黑場 | resolved | a6 黑場 5 次都不在 a6_c007（r2_brightness.json） |
| a6 | 夜景偏粉褐、a6_c009 摺燈手部 | 未驗證 | — |
| a8 | 合幕沒回台口 | resolved | 上一輪已確認；a8 指紋未變以外的檢查同 INDEX |
| a8 | 鞠躬只有點頭 | resolved（前傾幅度未驗證） | a8_c001_bows.jpg |
| a8 | 孩子壓扁彈起進場 | 未驗證 | — |
| 第 2 輪自述 | a3 練習卡 3 次窗 | partial | 細格 3／3 通過但貼上限（flash_variants near_limit_3） |
| 第 2 輪自述 | a5_c007 只縮 1.75 秒 | resolved | 全劇時間 ≤38 |
| 第 2 輪自述 | 遠景小朋友身後看得到貨車車尾 | 未驗證 | — |

## 六、結論

- S1、S2：**resolved**，有自己量測的證據。
- 上一輪一般問題 20 項：resolved 16、partial 2（備援影片、混音轉寫）、not 2（主線裁定不改的 sfx 名稱與眨眼間隔、資料包大小未改）。
- 低於 4 分的 4 項重評都到 4；三視角各項中位數 ≥3、平均 ≥4。
- 本輪沒有新的嚴重問題。本人（驗不通過項）判定：**通過，帶一般問題 1–5 放行**；第 1 項（備援影片＋教師資料去掉「暫定」）建議在 G7 前完成。
- 未驗證：聽感（a6_c009_01、蓋章聲、a8 靜音段）、實際投影、學校筆電效能與耐熱、Windows 實機、羅技簡報筆、110 人現場。
