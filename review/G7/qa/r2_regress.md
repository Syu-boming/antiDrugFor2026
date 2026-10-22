# G7 重驗：抽查改壞（修正第 1 輪＋「燈→登」配音換版之後）

- 驗收代理：重驗（抽查改壞）。日期：2026-10-23 02:0x–02:3x。
- 依據：RUBRICS.md、CLAUDE.md 兒童安全界線與固定需求、v1.3 第 4.5、8 節、v1.2 第 24 節、REVIEW.md 主線裁定（到「使用者聽感回報」）。沒有看製作提示、自評或 PROGRESS 檔。
- 證據資料夾：`review/G7/qa/r2_regress/`（下文簡寫 `r2/`）。沒有修改任何專案檔案；冒煙測試與 engine-test 都另指輸出位置或只寫暫存資料夾。
- 我聽不到聲音、看不到實際投影、不能跑 Windows exe：這些都標「未驗證」，不計分。

## 一、嚴重問題

沒有。

逐項查過、沒有變差的地方：
- 兒童安全界線 1–11：這一輪只換了 3 句配音檔、a6_c001 的 tail（5.0→4.83）、載入程式和文件。cue 檔只有 a6.json 一個欄位改了（`git diff 78330b5 cd8a2bd -- app/cues/show`）。台詞文字、八題、畫面都沒動。
- 兩句必要旁白：在 app/cues/show/a2.json 裡一字不差（只多了字幕換行）。teacher/data/檢查報告.md 第 12、13 項通過。cue 檔在這一輪沒有改過。
- 八題順序：dist 的 cues_show.js 依序是 answer 2、3、1、1、3、2、3、2。G6 驗收包 (g) 印章 [2,3,1,1,3,2,3,2]。我重跑的冒煙測試在兩個交付版都 8／8（`r2/delivery_smoke/delivery_smoke.md`）。
- 署名卡兩端都是「許博明老師製作」，片頭片尾截圖逐位元組相同（`r2/delivery_smoke/`）。
- 40 分鐘：預估總長 35:45，上限 38:00（teacher/data/timing.json totalSec 2145）。

## 二、這一輪特別要抽查的事（結果）

| 抽查 | 結果 | 證據 |
|---|---|---|
| 引擎載入的是不是 v05 | **是**。dist 的 manifest：201 句裡 198 句 v04、3 句 v05（a0_c002_03、a6_c001_02、a6_c009_03）。三個 vo_*.js 解出來的 PCM，md5 和 v05 wav 相同、和 v04 不同。交付/browser 也一樣 | `r2/manifest_vo_versions.txt`、`r2/vo_pack_check.json`、`r2/check_vo_pack.py` |
| 嘴型 | dist 的 lipsync.js 三句和 `audio/lipsync/*_v05.json` 逐格相同（32／27／97 格）。G6 即時播放嘴型 125／127 句會動，沒動的 2 句（a1_c004_06、a5_c001_03）和上一版一樣，都不是換版的句子 | `r2/lipsync_check.txt`；review/G6/pack/live/perf.json `mouth` |
| 台詞時間、字幕 | a0_c002_03 字幕比語音早 0.134 秒，a6_c001_02 早 0.122 秒，a6_c009_03 早 0.138 秒，都在 −0.8～+0.1 的範圍內。a0 17／17、a6 29／29 頁通過。a6_c001_02 從 2.01 秒變 2.18 秒，tail 少 0.17 秒，cue 長度仍是 13.68 秒；之後的動作都用「a6_c001_02.end+…」相對時間，鏡頭切換和眨眼（end+4.20）還在 cue 裡面 | review/G5/a0/pack/subtitle_sync.json、review/G5/a6/pack/subtitle_sync.json、timeline.json；app/cues/show/a6.json |
| 光敏 | a0、a6 重產的包「整段 通過」。a6 播放錄製每秒最多明暗 2、紅色 2；孤立亮度比 a0 1.136、a6 1.137，和換版前相同 | review/G5/a0/pack/INDEX.md、a6/pack/INDEX.md；`git diff 78330b5 cd8a2bd -- review/G5/a0/pack/INDEX.md review/G5/a6/pack/INDEX.md` |
| 響度 | 配音檔 v05：−18.2／−18.2／−18.1 LUFS，峰值 −1.9 dBFS（v04 是 −18.0～−18.2）。整段 a0 −16.5、a6 −16.1 LUFS 不變。a0 真峰值 −1.2→−1.3 dBTP；對白高出背景 15.4→15.1、17.7→17.6、16.8→16.9 LU，差不多 | `r2/vo_loudness.txt`；a0、a6 INDEX「聲音」 |
| 「燈」的聲調（只量音高走勢，沒有聽） | 我自己用自相關量：v04 阿樂叔叔兩句的「燈」從 112→85 Hz、104→84 Hz 一路下降（符合第四聲）。v05 a6_c009_03 是 117→106→113（平），a6_c001_02 是 255→245→257（平），**a0_c002_03 是 125→141（上揚約 2 個半音）**。平的那兩句符合第一聲；a0 那句是不是會聽成第二聲，要人耳確認。三句的中位音高都在同角色其他句的範圍內 | `r2/f0_deng.py`、`r2/f0_deng.json`、`r2/f0_roles.txt` |
| 備援影片 a0、a6 是不是新配音 | **是**。把 backup_a0.mp4、backup_a6.mp4 的聲軌和三句 v04／v05 做正規化互相關：v05 都是 0.977–0.987，v04 只有 0.088–0.130。_check 檔的 all_ok 都是 true，聲畫差 0 | `r2/backup_vo_check.py`、`r2/backup_vo_check.json`；交付/backup_video/_check/backup_a0.json、backup_a6.json |
| 交付包和 app/dist 一致 | 自己 diff：app/dist ↔ 交付/browser 0 差異；app/dist ↔ 交付/AntidrugTheater/resources/app/dist 0 差異；Electron 外殼 4 個檔和 app/electron 相同；三個 app.js 的 sha1 都是 61bd6938… | `r2/diff_dist_browser.txt`、`r2/diff_dist_exe.txt`（都是空的） |
| 冒煙測試 | 我自己重跑 tools/delivery_smoke.mjs（輸出到 r2/），兩個交付版**全部通過**：逐檔相同 144 檔、不加參數載入 71 個 cue、配音齊全、只按 PageDown 走 Q1（等 3 秒不揭答）、八題、署名卡、外部請求 0、頁面錯誤 0、啟動說明 BOM＋CRLF | `r2/delivery_smoke/delivery_smoke.md`、`r2/delivery_smoke.log` |
| G6 驗收包是不是同一個建置 | **是**。INDEX 記的 app.js 61bd6938…、cues_show.js 30af06ef…，和我算的 app/dist 一樣。(b) 即時播放、(c) 接縫、(e) 操作都標「本次以目前建置量測」。量測時間 18:02Z，晚於建置的 16:08Z，所以量的是 v05 的資料包 | review/G6/pack/INDEX.md、build_check.json；`shasum app/dist/app.js app/dist/data/cues_show.js` |
| 效能、操作、離線 | G6 (b)：p95 16.70 ms、播放中 >100 ms 卡頓 0 次、字幕不符 0／3050（上一版是 2 筆，那是 --skip-live 的假警報）。(e)：engine-test 151／151、全劇補測 21／21。(d)：外部請求 0。和 22:05 版逐行比：數字持平，沒有變差 | review/G6/pack/INDEX.md (b)(d)(e)；`git show HEAD:review/G6/pack/INDEX.md` 對照 |
| engine-test 自己重跑 | 見第五節（只寫暫存資料夾） | `r2/engine_test.log` |
| 教師資料 | `node tools/teacher_docs.mjs --check` 結束碼 0；cue 指紋 91b90f6887 一致；九段備援影片都在。PDF 頁數：操作卡 1、故障卡 1、導覽單 1、回饋單 1、學生版題卡 8、教師版題卡 9、講稿 16、教案 4、參與小卡 1、貼紙 2、成果紀錄 2。teacher/pdf 和交付/teacher_pdf 的 11 份逐位元組相同 | `r2/teacher_docs_check.txt`、`r2/pdf_pages.txt` |
| gh-pages **分支** | origin/gh-pages 7c24591：show/ 和 app/dist 0 差異；teacher/pdf、html、img、fonts 和本機 0 差異；入口頁和 tools/pages/index.html 相同 | `r2/diff_dist_ghpages_show.txt`、`r2/diff_teacher_ghpages.txt` |
| **線上版實際送出的內容** | **不一致**，見一般問題 1 | `r2/live_site_check.md` |
| README、ASSETS、素材與授權表的 v04／v05 | README 寫「各句最新版 v04，其中 3 句 v05」。素材與授權表第 190、193、211 行、ASSETS.md 第 81 行寫的 3 句和 manifest 相同 | `r2/manifest_vo_versions.txt` |

## 三、一般問題（依重要性排序，最多 8 項）

### 1. 線上版還在送 22:05 的舊版：配音念「鄧」、「本課自行設計」、導覽單「暫定」都還在，總報告卻寫已經發布
- **位置**：https://syu-boming.github.io/antiDrugFor2026/ ；總報告 1.3 節「線上版」那一列、1.5 第 3 項、5.7「主線收尾」。
- **證據**（`r2/live_site_check.md`，02:12 量）：
  - GitHub Pages 對 7c24591 的建置從 17:33:12Z 起一直是 `building`，Actions「pages build and deployment」是 `queued`（排了 39 分鐘以上）。上一次成功的是 23b30db（14:09Z）。
  - 線上 show/app.js 的 sha1 是 42a04b59…，不是 61bd6938…。加了 ?nocache 的 manifest.js，builtAt 還是 2026-10-22T13:33:58Z，a0_c002_03 的來源是 **v04**。
  - 線上觀課導覽單還有「本課自行設計，不是官方口號」和「日期與場地：暫定」；入口頁頁尾還是「使用生成式 AI 工具輔助」。這些都是 G7 第 1 輪已經指出、修正第 1 輪改掉的字句。
- **影響**：正式演出用離線版，課堂演出不受影響。但這個網站是公開的，「預覽與練習」看到的是念錯的配音和不實的 AI 說明。總報告說線上版已經是新版，和實際不符。
- **修法**：
  1. `gh api repos/Syu-boming/antiDrugFor2026/pages/builds/latest` 看到 `built` 才算發布完成。如果一直卡在 queued，就用 `gh run rerun <run-id>` 重跑那個 Actions，或用 `gh api -X POST repos/Syu-boming/antiDrugFor2026/pages/builds` 重新觸發。
  2. 發布完成後，用 `curl -s "https://syu-boming.github.io/antiDrugFor2026/show/data/manifest.js?x=$(date +%s)" | grep -o 'builtAt":"[^"]*'` 確認是 `2026-10-22T16:08:11.962Z`，用 shasum 確認 show/app.js 是 61bd6938…。
  3. 把第 2 步加進 tools/deploy_pages.sh 的最後，對不上就結束碼 1。總報告 1.3 寫的狀態要以這個驗證為準。

### 2. 素材與授權表第 5 行的建置時間過期，「逐位元相同」的說法現在不成立
- **位置**：交付/素材與授權表.md（也就是 review/G7/素材與授權表.md）第 4–5 行；第 278、307 行的「22:03 打包」。
- **證據**：第 5 行寫依據是 manifest「建置時間 2026-10-22 21:33（builtAt 13:33:58Z）」，還說交付裡的兩份清單和它「逐位元相同」、「素材清單除了建置時間以外完全相同」。實際上 app/dist 和交付的 manifest.js 都是 builtAt 2026-10-22T16:08:11.962Z，而且內容不同：3 句來源換成 v05、長度也變了（`r2/manifest_vo_versions.txt`；app/dist/data/manifest.js）。交付是 01:29 打包的，不是 22:03。
- **修法**：第 5 行改成「建置時間 2026-10-23 00:08（builtAt 2026-10-22T16:08:11.962Z）；和 21:33 版相比，只有 3 句配音換 v05（第 190 行）」。第 278、307 行的「22:03 打包」改成「10-23 01:29 打包」。第 4 行日期加上 10-23 的更新。

### 3. 總報告的時間、commit 時刻和幾個數字和實際不同
- **位置**：交付/總報告.md 第 91–93、112、116、123、124 行。
- **證據**：
  - 第 112、116 行寫交付在「10-23 00:5x」重新打包。交付/browser/app.js、啟動說明.txt 的 mtime 是 **01:29**，冒煙測試在 17:29:40Z（01:29）。
  - 第 123、124 行寫 cd8a2bd、gh-pages 7c24591 是「00:5x」。git 記的是 **01:33:03、01:33:05**。
  - 第 91 行引用技術 QA 在舊建置上的「字幕 3057 筆、最大 3 毫秒」。最後建置的 G6 包是 **3050 筆、0 不符、最大 5 ms**（review/G6/pack/INDEX.md (b)）。
  - 第 92、93 行寫 1322.3 秒、1333.1 秒。目前是 **1322.2＋10.8＝1333.0 秒**（G6 INDEX (a)；teacher/data/檢查報告.md「預錄播放 0 級 1322.2 秒」）。這是 a0_c002、a6_c009 各短 0.03 秒造成的；22:02、22:13、35:45 不受影響。
  - 1.5 第 2 項寫 G6 全劇包「已完成」。總報告寫於 01:35–01:36，G6 INDEX 卻是 02:03 產生的（即時播放在 02:02 量完）。現在已經是真的，但寫的當下還沒完成。
- **修法**：照上面改成實際時刻與數字。1.1 改引用 review/G6/pack/INDEX.md (b)（3050／0／5 ms）。改完再複製到交付/總報告.md。

### 4. 最後一批成果都還沒 commit
- **位置**：工作區（`git status`）。
- **證據**：HEAD 是 cd8a2bd（01:33）。之後的 G6 全劇驗收包重跑（INDEX 02:03、build_check.json、live/*、seams/*，還有 seams/_work 一千多個刪除）、README.md、ASSETS.md、PROJECT_STATE.md、review/G7/總報告.md、素材與授權表.md 都是「已修改、未 commit」。總報告第 123 行卻把 cd8a2bd 寫成目前版本。gh-pages 的 commit 訊息「發布 main cd8a2bd」只代表程式，不代表這批文件。
- **修法**：G7 決定之後，依 CLAUDE.md「每過一關更新 PROJECT_STATE.md 並 git commit」把這些一起 commit。總報告 1.3 的「本機 commit」改成新的 commit 號，再複製到交付。

### 5. a0、a6 驗收包的逐字稿小節還寫「（v04 配音）」「配音檔都是 v04：False」，容易被誤讀成出錯
- **位置**：review/G5/a0/pack/INDEX.md、review/G5/a6/pack/INDEX.md「逐字稿」小節（產生工具 tools/act_review_pack.mjs）。
- **證據**：這兩段本來就該有 v05，所以 False 是對的，但標題和措辭還是舊的「都是 v04」檢查。engine-test 已經改成以 timings.json 的版號為準。
- **修法**：工具改成「配音檔都是 timings.json 記的正式版：是（v04 N 句、v05 M 句）」，標題拿掉「v04」。下次重產時生效，不必為這個重跑。

### 6. a0_c002_03 v05 的「燈」量起來是上揚，不是平的
- **位置**：audio/vo/vo_a0_c002_03_v05.wav（開場第一次出現口訣）。
- **證據**：`r2/f0_deng.json`。0.04 秒窗、0.02 秒步進量到 125→126→131→137→141 Hz，約上揚 2 個半音。另外兩句 v05 是平的。REVIEW.md 寫三句「新版都量成第一聲」，這一句只是不再下降。
- **影響**：2 個半音的輕微上揚，多半聽起來還是一聲，但這句正是許老師聽出念錯的那一句。
- **修法**：不用改檔。總報告第四節 #20 的試聽提醒加一句「a0_c002_03 特別聽是不是像『騰』」。不滿意的話用 tools/vo_el_promote.py 換候選。聽感：未驗證。

### 7. 故障一頁卡只寫「準備播放是灰的」，沒有寫這一輪新出現的「仍要播放（缺 N 句配音）」
- **位置**：交付/teacher_pdf/故障一頁卡.pdf「準備播放是灰的、停在『資料包 n／m』」那一列。
- **證據**：修正第 1 輪後，缺配音資料檔時按鈕**不是灰的**，而是變成「仍要播放（缺 N 句配音）」，要再按一次（engine-test 第五節新項；啟動說明.txt 第五節有寫）。故障卡沒寫這個症狀，老師可能直接按第二次，就在缺對白的情況下開演。
- **修法**：把那一列的症狀改成「準備播放是灰的，或按鈕寫『仍要播放（缺 N 句配音）』」，第一個動作寫「不要按第二次；關掉程式，把整個交付資料夾重新複製再開」。改完確認仍是 1 頁（teacher_docs 的頁數檢查）。

## 四、未驗證（不計分）

- 三句 v05 和 a2_c013_05 的聽感、聲調、PSOLA 0.72 倍的音質（a6_c001_02）。
- Windows 可攜版實際執行、SmartScreen、啟動說明.txt 在記事本裡的顯示。
- 實際投影、最後一排、學校筆電效能（探針）、待機 30 分鐘＋演出 40 分鐘的耐熱測試。
- 備援影片在 Windows 媒體播放器裡的播放與暫停。
- 線上版 Pages 什麼時候會發布完成（在我量的 02:12 還沒完成）。

## 五、自己重跑的 engine-test

- `node tools/engine-test.mjs`（02:1x，在最後的建置上）：**151／151 通過**，結束碼 0。其中「201 句配音都打包進資料包、都是 ElevenLabs 正式版」一項列出新版 a0_c002_03:v05、a6_c001_02:v05、a6_c009_03:v05。缺配音資料檔、缺 sfx.js、缺 img_ui.js 的三組新項目也都通過（`r2/engine_test.log`）。
- 02:15 再查一次線上版：Pages 仍是 `building 7c24591`，線上 manifest 仍是 13:33:58Z 的建置（`r2/live_site_check.md` 最後一節）。

## 六、分數（重驗（抽查改壞）視角；只對有證據的項目打分）

| 項目 | 分數 | 證據 |
|---|---|---|
| 技術 QA 1 操作 | 4 | G6 (e) engine-test 151／151、全劇補測 21／21（同一建置）；冒煙測試實按 PageDown 走 Q1、八題 8／8（`r2/delivery_smoke/`）；engine-test 重跑見第五節 |
| 技術 QA 2 效能 | 4 | G6 (b) p95 16.70 ms、>100 ms 卡頓 0、停格中最長 99.9 ms，和 22:05 版持平；建置 sha1 相同 |
| 技術 QA 3 同步與光敏 | 4 | 三句字幕差 −0.12～−0.14 秒；嘴型資料＝v05；voiceSync 最大 5 ms、字幕不符 0／3050；a0、a6 光敏整段通過、孤立亮度比不變 |
| 技術 QA 4 穩定與離線 | 4 | 外部請求 0（G6 (d)、`r2/delivery_smoke`）；頁面錯誤 0；缺資料包流程有 engine-test 項目 |
| 完整性 1 交付清單齊全 | 4 | 交付/ 有可攜版（含啟動說明）、瀏覽器版、9 段備援影片＋README、11 份 PDF、使用說明、素材與授權表、總報告；備援 a0、a6 是新配音（`r2/backup_vo_check.json`） |
| 完整性 2 文件與程式版本一致、署名正確 | 3 | 署名正確、v04／v05 說法正確；但線上版實際是舊版（一般問題 1）、素材與授權表建置時間過期（2）、總報告時刻與數字不符（3）、最後一批沒 commit（4） |
| 完整性 3 總報告列出決定、未驗證、已知問題 | 4 | 「燈」修正列在第 1 頁第 19 項、3.3 C12、第四節 #20（未驗證）、5.7；決定、未驗證、已知問題都有；時刻問題算在完整性 2 |
| 校長／教育專業 3 用語與安全 | 4 | 交付內容的必要旁白、八題、用語檢查 25／25；AI 說明在交付 PDF 已照實寫。線上版仍是舊字句（一般問題 1），不影響離線交付 |
| 校長／教育專業 4 課堂可行 | 4 | 教師資料 --check 通過、頁數符合、35:45＜38:00、操作卡與啟動說明一致；故障卡少一個症狀（一般問題 7） |

平均 3.89；中位數 4。沒有嚴重問題。
