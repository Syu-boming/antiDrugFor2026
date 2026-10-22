# G6 全劇驗收：技術 QA（2026-10-22）

- 依據：RUBRICS.md（技術 QA 四項＋嚴重問題）、CLAUDE.md 安全界線第 9 條與固定需求、v1.3 §8、v1.2 §24、REVIEW.md 主線裁定（細格 fine_32x18 ≤3；全畫面平均亮度相差 >約 20% 不得一格硬切；±1 LU 分層規則與 G6 的 a8 例外）。
- 材料：review/G6/pack/（INDEX.md 16:33，建置 app/dist 15:39）、review/G5/<段>/pack/（抽查）、teacher/、交付/。
- 自己抽的證據：review/G6/qa/tech/（indep_cuts.py／.json：九段 playback.mp4 逐格孤立硬切；indep_flash.py／.json：簡化細格計數；indep_spikes.json：單格突亮與兩段式切換；a3_c008_cut_34.54s_pair.jpg、a3_cut_2.png／a3_cut_3.png；delivery_vs_dist.txt、cuediff.mjs；loudness_main_theme.txt；recheck_a4_c002.jpg、recheck_a6_a8_keyframes.jpg）。
- 未驗證、不計分：聽感、實際投影、學校筆電（效能、載入、記憶體、耐熱）、Windows 上的 Electron、羅技簡報筆鍵碼、實機休眠與斷網。

## 一、問題（先列問題再打分）

### 嚴重問題

**S1　a3_c008 鏡頭切換一格亮度跳 +29.5%，違反主線「>20% 不得一格硬切」（CLAUDE.md 第 9 條「切場亮度漸變」）**
- 位置：a3_c008 第 34.54 秒 `camera.cut → a3_cls_end`（a3 播放錄製第 169.1 秒，第 5072→5073 格）。
- 證據：review/G6/qa/tech/a3_cut_2.png → a3_cut_3.png，全畫面平均線性亮度 0.4256 → 0.5512（1.295 倍；Rec.601 gamma 亮度 0.634 → 0.725）。前後兩格都不動（孤立硬切，不是漸變）。九段其他所有孤立切換都在 1.16 倍以內（indep_cuts_all_gt6pct.json），和第一批最後重驗記錄的 1.09–1.16 倍一致，所以這是 a3 第 2 輪修正後新出現的，G5 第二批第 2 輪沒有派重驗代理，沒有人查到。官方光敏工具只數「每秒變化次數」，抓不到單次硬切。
- 修法（照主線更正裁定擇一）：(a) 在 a3_c008 第 33.9–34.5 秒加 `light.dim`（鏡頭不動，≥0.6 秒），把亮度降到切過去後畫面的 1.2 倍以內再切；或在 a3_cls_end 鏡位加 `light.dim to≈0.8` 讓切過去的畫面變暗、之後 ≥0.6 秒再 `light.restore`；(b) 改成 `fade.out`／`fade.in`（各 ≥0.3 秒）。改完重產 a3 驗收包，並在 tools/act_review_pack.py 加「孤立單格全畫面亮度比 >1.2 判不通過」（可直接用 review/G6/qa/tech/indep_cuts.py 的判定），以後的包都會自動抓。

**S2　交付包不是驗收過的建置，而且瀏覽器版預設不是全劇**
- 位置：交付/browser/、交付/AntidrugTheater/resources/app/dist/（10:10 版）。
- 證據：review/G6/qa/tech/delivery_vs_dist.txt。交付版的 app.js 是 `get("cues")??"demo"`，目前的 app/dist 是 `??"show"`，所以直接開 交付/browser/index.html 會播 demo，不是全劇（使用說明要老師自己在網址後面加 `?cues=show`，在 Windows 上雙擊檔案做不到）。71 個 cue 中有 38 個和 G6 驗收的 app/dist（15:39）不同（a8_c002 回台口全景、a4_c009、a1_c005、a6_c007 等動畫都是舊版），查核點 atMinute 也是舊值（13／23.45／30.82／34.55）。G6 驗收包量的全部是 app/dist，交付版的光敏、八題、署名卡、離線都沒有證據；a7、a8 在 10:0x 的版本 REVIEW.md 也寫明「還沒重產驗收包」。使用者接下來要拿交付包去學校筆電跑探針與彩排，會跑到一個沒驗過的版本。
- 修法：等 S1 修好、建置完成後，把 app/dist 整個複製到 交付/browser/ 和 交付/AntidrugTheater/resources/app/dist/（Electron 外殼的 main.js／preload.js／layout.js／package.json 和原始碼相同，不必改）；再對交付的檔案跑一次冒煙測試：用 file:// 開 交付/browser/index.html（不加參數）要載入 show、零外部請求、片頭片尾署名卡、八題答案順序；用 `diff -rq 交付/browser app/dist` 證明一致，結果寫進 REVIEW.md。G6 驗收包工具加一列「交付包與建置一致（diff 0）」。

### 一般問題（依重要性，最多 8 項）

**G1　>100 ms 卡頓 10 次（v1.2 §24 上限 2），而且分類有誤**
- 證據：review/G6/pack/live/perf.json `stalls_over_100ms`。10 次全部發生在「漸暗 → 換景 → 漸亮」那一刻：8 次在跨段換景（cueTime 0.14–0.37 秒），另外 2 次（a4_c002 16.12 秒、a4_c007 6.02 秒）INDEX 標成「不是換景」，其實也是段內的 `fade.out → set.swap → fade.in`（a4 timeline：set.swap 15.98／5.86 秒，fade.in 16.01／5.91 秒）。REVIEW.md 寫「2 次在 a4、a5」也不對：兩次都在 a4，a5_c001 那次是跨段換景。
- 看得到嗎：從 seams/a4_a5/flash_playback_plot.png 的亮度曲線看，cueTime 0 到約 0.2 秒畫面接近全黑（亮度 <0.01），0.37 秒時大約只有完整亮度的 15%。所以在 M4 上，卡住的那一格幾乎都是黑的或很暗，看不太出來（最長那次 a5_c001 183 ms，漸亮會頓一下，跳大約 12% 的亮度）。判定：在開發機上看不到、也沒有壓到對白或揭答，但次數沒有達到門檻。風險在學校筆電：卡頓結束時間離第一句台詞只剩 0.4–0.6 秒（a2_c004 第一句 0.8 秒、a5_c001 0.95 秒），筆電慢 3 倍就會拖進漸亮後段，甚至壓到台詞開頭。a4_c002 的 sfx_paper_rustle（16.06 秒）就落在卡頓窗內。
- 修法：照主線授權，在前一個 cue 的等待階段（story_waiting／final_waiting）先建下一個景：`renderer.initTexture()`（或 compileAsync＋把隱藏的景 render 一次）預先上傳貼圖、編譯材質，set.swap 時只切可見性。驗收：重跑 show_review_pack，>100 ms 要 ≤2，逐像素比對不變；分類改成「在 fade 的黑格內（亮度 <0.05）／不在」，不要再用 cue 名稱判斷。

**G2　教師資料比建置舊：控制台目標時間不一致**
- 證據：teacher/教師講稿.md 第 35–38、103、134、159、436 行與 teacher/data/檢查報告.md 寫的控制台目標是 13:00／23:27／30:49／34:33，產生時間 15:38:55；app/cues/show/a2、a4、a6、a8.json 在 15:39:10 才把 atMinute 改成 13.27／23.82／31.48／35.08，dist 用的是新值，也就是 13:16／23:49／31:29／35:05。講稿裡「控制台在 Q8 前後可能顯示落後約 40 秒，這是正常的」現在是錯的（實際落差約 0）。REVIEW 第一階段要求「G6 回查兩邊一致」：沒有一致。
- 修法：cue 定版後重跑 `node tools/teacher_docs.mjs`（含 PDF）；在檢查報告加一項「講稿 cue 指紋＝app/dist/data/cues_show.js 指紋」，不一致就讓結束碼為 1。

**G3　a8 響度例外的理由不成立；主奏段之間差 4 LU**
- 證據：review/G6/qa/tech/loudness_main_theme.txt。a8 整段 −19.4 LUFS，主要原因不是「署名卡上的閉幕音樂淡出」：謝幕音樂 music_bows（a8_c001 0–13.4 秒，沒有台詞）只有 −21.8 LUFS（短期響度 −22～−20）；閉幕音樂 a8_c002 反而有 −17.8；另外 20.5–25 秒將近 4.5 秒沒有聲音（謝幕音樂結束後的教師停格，到合幕音樂出來之前）。照主線 12:30 的分層規則，「主奏段（開幕、閉幕、署名卡）」同一組要在 ±1 LU 以內（最大減最小 ≤2 LU）：開幕 −19.6、謝幕 −21.8、閉幕 −17.8，相差 4.0 LU，不符合。對白響度（−14.7，偏差 0.2 LU）符合。
- 判讀：用「對白響度」判 ±1 LU 時 a8 通過；用「主奏段」那一組判時不通過。整段響度在主線規則裡只是參考，不能拿整段來判。
- 修法：music_bows 在 a8_c001 的 gain 或 musicLevel 加約 +2.5 dB（讓它落在 −19.5±1）；確認 a8_c001 結束後停格期間要不要繼續鋪一層低音量的音樂。改完重算主奏段三段，寫進 REVIEW.md 取代「閉幕淡出」這個理由。聽感由第 3 天彩排確認。

**G4　a4 驗收包比 a4.json 舊，「與建置一致」只比了長度**
- 證據：review/G5/a4/pack/INDEX.md 產生於 12:34:51；app/cues/show/a4.json 修改時間 15:39:10（和 a2、a6、a8 同一秒，應該是查核點批次更新）。a2、a6、a8 有重產包，a4 沒有。G6 INDEX (a)「與建置一致 9／9」只比 cue 長度。大概只改了 a4_c011 的 checkpoint，但沒有證據。
- 修法：act_review_pack 把段落檔的 sha1（去掉 checkpoint 欄）寫進包裡，show_review_pack 改成比雜湊；或附 `git diff` 證明 a4.json 只改了 atMinute。

**G5　缺配音檔時仍然可以開演（缺音風險）**
- 證據：review/G6/pack/ops/engine_test.log 第 91–95 行：「缺配樂、音效、配音時仍可按『準備播放』」「缺檔下開幕照常播放」。RUBRICS 技術 QA 第 4 項要求「載入失敗停在準備畫面」。如果複製交付包時漏了資料檔，全劇模式會沒有對白照樣演下去（字幕有、配音沒有），就是嚴重問題清單的「缺音」。
- 修法：全劇模式（cues=show）缺任何 vo_ 檔時，「準備播放」改成需要老師再按一次確認（顯示「缺 N 句配音」）；缺配樂、音效可以照常演。engine-test 加一項。

**G6　有 3 句只在混音中兩個轉寫模型都轉錯（可能被配樂或音效蓋住）**
- 證據：review/G5/a6/pack/transcripts.json a6_c009_01「叔叔，又到紙燈節了！」單檔 small 正確，混音中 small／large 的 PER 是 0.25／0.375；a1_c001_05「青蛙燈」在混音中兩個模型都轉成「青蛙丹」（單檔都正確）；a0_c004_01 混音中 small 轉成「早早早早」。字幕內容 0 不符、時間差 ≤5 ms，同步沒問題；可能是那幾個時刻的 ducking 不夠。
- 修法：檢查這 3 句時段的配樂與音效增益（a6_c009 換曲、a1_c001 的 sfx_crowd_far／footsteps），必要時多壓 2–3 dB；彩排時人耳確認。

**G7　資料包與載入時間在學校筆電上沒有餘量**
- 證據：app/dist/data 417 MB（第一階段記錄是約 212 MB）；M4 上開頁到可以按「準備播放」要 5.7 秒、到片頭 7.45 秒，JS heap 215–271 MB，Chrome 各程序 RSS 合計 4.0–4.8 GB（live/perf.json、memory_plot.png）。學校筆電 8 GB 記憶體時有被換頁或卡頓的風險，未驗證。
- 修法：探針一回來就用同一支 show_review_pack 在學校筆電跑一次（畫質 B／鎖 30 fps 兩種）；預先準備「只載入目前段落±1」或把貼圖降成 WebP 的退路，並在故障卡寫清楚第一次開啟要等多久。

**G8　放行項目還沒處理的技術小項**
- 翻面後到第一次眨眼仍是 0.32 秒（app/src/stage/perform.ts:379 `FLIP_BLINK_GAP = 0.3`；G4 建議 ≥0.4）；`sfx_ambulance_engine` 仍沿用舊名（app/cues/show/a5.json、audio/sfx/sfx_ambulance_engine_v01.wav）；Electron 只在 macOS 跑過。
- 修法：GAP 改 0.4 秒並跑 engine-test 眨眼項；把音效改成中性名稱（例如 sfx_van_engine）並重新打包；Windows 實機由使用者在第 3 天前跑一次 AntidrugTheater.exe。

### 觀察（不列問題）
- 光敏：九段官方結果 16×9 與 fine_32x18 都 ≤3、超標 0（review/G5/*/pack/flash_variants.json）。我用 H.264 錄影＋簡化計數重算（indep_flash.json），a1 第 33.7 秒（a1_c002 約 1.9 秒）、a4 第 60.1 秒（a4_c003 約 9.5 秒）各有一個 60×60 細格算出 4 次；官方用無損影格、同一時間鄰近細格是 3 次（near_limit_3）。判斷是方法差異造成的邊界值，不當成問題，但 a1／a4 的 near_limit_3 各有 121 個窗，幾乎沒有餘量；投影機的伽瑪不同時可能被放大。
- 單格突亮、light.restore 比 camera.cut 早一格的兩段式切換：九段都是 0（indep_spikes.json），a1「切近景前一格亮 11%」已解決。
- 離線：三次擷取共 402 個請求，外部 0；建置只有兩個字串網址（jcgt.org 論文註解、w3.org XHTML 命名空間），不是請求。localStorage 只存按鍵設定與控制台通道，沒有姓名或使用紀錄；沒有 getUserMedia（安全界線第 11 條）。
- 署名卡：片頭與片尾都是 DOM「許博明老師製作」、可見；title_start.png 和 title_end.png 每個位元組都相同（同款卡）。
- 八題：8／8，印章 [2,3,1,1,3,2,3,2]，不會自動揭答，八盞燈依序點亮；題卡 PDF 112 項文字比對一致；Q8 題卡沒有孤字斷行（recheck_a6_a8_keyframes.jpg）。
- 交付檔名：交付/AntidrugTheater 與 交付/browser 裡所有檔名都是英數（只有上層的 交付/ 和使用說明是中文）。

## 二、評分（技術 QA；1–5，4＝G4 基準）

| 項目 | 分數 | 理由與證據 |
|---|---|---|
| 1 操作 | 4 | engine-test 134／134、全劇補測 21／21（連按 5 下只開幕一次、長按全部忽略、出題連按只進揭答、揭答中按上一步會恢復未揭答、跨段上一步 8／8、暫停與 R 之後時間差 0 ms、頁面隱藏／凍結／休眠模擬都停住等老師按；review/G6/pack/ops/）。70／70 個 cue 依序播完、頁面錯誤 0。扣分在交付包（S2）與缺檔仍可開演（G5），實體簡報筆未驗證。 |
| 2 效能 | 3 | p95 16.70 ms（門檻 34），各段 p95 ≤16.8；但 >100 ms 卡頓 10 次（上限 2），雖然都在換景黑格、不在對白或揭答中（perf.json），學校筆電餘量不足（G1、G7）。耐熱未驗證。 |
| 3 同步（含光敏） | 3 | 字幕與語音時間差最大 5 ms、>50 ms 0 次；字幕內容 3054 筆 0 不符；嘴型 125／127；九段官方光敏通過、8 個接縫沒有硬切。但 a3_c008 一格亮度跳 1.30 倍（S1），另有 3 句在混音中被蓋住的跡象（G6）。 |
| 4 穩定與離線 | 3 | 外部請求 0／402、頁面錯誤 0、GPU 中斷有處理；但交付包是沒驗過的舊建置、瀏覽器版預設 demo（S2），而且缺配音檔仍可開演，和「載入失敗停在準備畫面」不符（G5）。 |

平均 3.25。有 2 項嚴重問題 → 技術 QA 判定**不通過**。S1、S2 都是小改動：S1 改一個 cue 再重產 a3 包，S2 重新複製交付包再跑冒煙測試。修好後重驗只要看 a3 包、交付包 diff 與冒煙測試結果。

## 三、帶問題放行項目回查

| 項目（來源） | 判定 | 證據 |
|---|---|---|
| G3：自動檢查標未通過 23 句 | 未驗證（狀態沒變） | audio/vo/promoted_el.json：pass 177、fail 23、incomplete 1；使用者 G3 聽過全劇並接受，混音中兩模型都錯的只有 G6 列的 3 句 |
| G3：PSOLA 重後製失真 | 未驗證 | 只能靠人耳 |
| G3：全劇配音 14.15 分，G5 依實際句長排時間 | resolved | 預錄 1325.8 s；教師時間＋播放 35.83 分 ≤38（packs/show_table.json、teacher/data/timing.json） |
| G3／G4：a2_c002＋a2_c004 47.09 秒，G6 依全劇時間檢查 | resolved | 全劇總長在 38 分內，有 130 秒餘量 |
| G3：a2_c002_02 small 轉成「竹樹」 | partial | 單一模型分歧；G5 a2 transcripts 沒有兩個模型都錯 |
| G4：半閉眼皮雜點、閉眼補片明暗差 | 未驗證 | 技術 QA 沒有逐格看臉部 |
| G4：小宇 stepback 閉眼眼白殘影 | 未驗證 | 同上 |
| G4：翻面到第一次眨眼 0.32 s（建議 ≥0.4） | not | app/src/stage/perform.ts:379 FLIP_BLINK_GAP=0.3 |
| G4：ASSETS／REVIEW 的 ElevenLabs 用量改指向 ledger.json | resolved | ASSETS.md 第 88、142 行改指向 ledger.json，說明不再抄數字（REVIEW 第 10 行是歷史紀錄） |
| G4 第 2 輪：膝前線到頭部框 21.6 px | 未驗證（交安全視角） | G6 INDEX (a)：各段線到頭部框最短 a2 17.2、a4 16.9、a5 10.4、a6 54.0 px，a5 比 G4 記錄的 21.6 px 更近；線經過兒童 0。是否算「繞頸」由安全與事實判讀，技術 QA 只提出數字 |
| G5 一階：資料包約 212 MB | not（變大） | app/dist/data 417 MB；JS heap 215–271 MB（G7） |
| G5 一階：換景全暗那格最長 83 ms | not（變差） | 現在 183 ms，>100 ms 10 次（G1） |
| G5 一階：cue 合計 1391 s 比 1313 s 多 78 s | resolved | 1325.8 s |
| G5 一階：Electron 只在 macOS 跑過 | 未驗證 | 交付包又是舊建置（S2） |
| G5 一階：授課時鐘控制台與引擎一致 | partial | 引擎查核點已更新，教師講稿仍是舊目標（G2） |
| G5 第一批 a1：Q1 點燈後連兩次暗亮、孩子停在走路中途 3 秒 | partial | a1_c007 只有一次漸暗漸亮，a1_c008 改成輕微 dim（0.48→0.36，indep 亮度序列）；停在走路中途沒看 |
| a1：小晴翻面約 0.15 s | 未驗證 | — |
| a1：切近景前一格亮 11% | resolved | indep_spikes.json：a1 單格突亮與兩段式切換 0 |
| a1：品安轉身看不出在看柱子 | 未驗證 | — |
| a4：a4_c002 轉場露出景片俯視與深紅布幕、3.3 s 空天空 | partial | set.swap 15.98 s 藏在 fade.out 黑格裡，看不到俯視與布幕；天空鏡約 1.7 s、有紙飛機（recheck_a4_c002.jpg）；但 13.0–16.6 s 內連兩次全黑漸暗漸亮 |
| a4：地圖左下深紅棕色塊、斑馬線旁影子殘影 | 未驗證 | — |
| a4：兒童身後背景投影 0.34–0.41 | 未驗證 | — |
| a4：sfx_ambulance_engine 未改名 | not | app/cues/show/a5.json 仍引用 |
| a2：a2_c012 廣場求助鏡頭約 1.2 s | 未驗證 | a2_c012 切點 1.47／4.15／5.37 s，第 2 個鏡頭約 2.7 s，是不是同一個鏡頭沒確認 |
| a2：a2_c002 膝線對比 13.9／投影 9.9 | 未驗證 | — |
| a2：手部近景手指簡化 | 未驗證 | — |
| a0：摺紙縮成小點、折折被擋一半、上半部空牆、門邊吊牌灰影 | 未驗證 | — |
| 共同：揭答蓋章聲 100 ms 上升 47 LU | partial | 改用 sfx_stamp_v02：起始 −47 dB、20 ms 到峰值 −17.4 dB（v01 是 −25.5／−13.7）；峰值降 3.7 dB，仍是快速起音，聽感未驗證 |
| G5 第二批 a5：低年級小朋友粗模、救護人員頭浮在車前 0.3 s、景片平 | 未驗證 | — |
| a6：灰色無臉人影 | 未驗證 | — |
| a6：Q8 孤字斷行 | resolved | a6_c003 題卡沒有孤字（recheck_a6_a8_keyframes.jpg） |
| a6：a6_c009 沒有摺燈手部動作；夜景偏粉褐 | 未驗證 | — |
| a6：a6_c007 高潮中段黑場 | partial | 中間影格不黑；a6 全段亮度序列沒有長時間 <0.05 的段落，但我沒有逐秒看 |
| a8：合幕沒回台口 | resolved | a8_c002 2.7 s 已是台口全景、八盞燈全亮（a8_c002_002.70_mid.png） |
| a8：鞠躬只有點頭、孩子壓扁彈起進場 | 未驗證 | — |
| 第 2 輪自述未修：a3 練習卡「3 次」窗、印章音效、a5_c007 只縮 1.75 s、遠景小朋友身後看得到貨車車尾 | partial／未驗證 | a3 細格 3／3 通過但貼上限；印章見上；其他未看 |
| G6 包：>100 ms 卡頓（主線授權修） | not | 程式與建置在包產生後都沒改（app/src 最新 a6_shop.ts，早於包） |
| G6 包：a8 整段響度例外 | partial | 對白 ±0.2 LU 通過；主奏段之間差 4.0 LU，例外的理由不對（G3） |
