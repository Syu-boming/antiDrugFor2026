# G7 交付驗收｜技術 QA

- 驗收時間：2026-10-22 22:07–22:50（本機時間）。驗收代理用技術 QA 視角，effort high。
- 依據：RUBRICS.md「技術 QA」四項與嚴重問題清單、CLAUDE.md 安全界線與固定需求、v1.3 §4.5／§8、v1.2 §24、REVIEW.md 主線裁定。沒有看製作提示、自評或 PROGRESS 檔。
- 驗收對象：交付/（AntidrugTheater、browser、backup_video、teacher_pdf、三份 md）、teacher/data、review/G6/pack、review/G5/<段>/pack（抽查 a3、a5）、GitHub repo 與 gh-pages。
- 證據資料夾：`review/G7/qa/tech/`。下文路徑如果沒寫全，都相對於這個資料夾。我只寫入 `review/G7/qa/`，沒有改任何其他檔案（`git status` 只多出 review/G7/qa/）。缺檔測試用的是 scratchpad 裡的複本，不在專案內。
- **未驗證（不計分）**：聲音聽感；實際投影；學校筆電的效能與耐熱；在 Windows 上執行 AntidrugTheater.exe（PE32+ x86-64，Electron 44.9.1）；SmartScreen；羅技簡報筆的實際鍵碼；用 Windows 內建播放器播 mp4。

---

## 一、問題清單（先列問題）

### 嚴重問題：無

RUBRICS 列的嚴重項目我逐項找過證據，都沒有成立：
- 跳段、配音重疊、自動揭答：自己跑的實鍵測試和冒煙測試都沒有出現（見第二節 1、4）。
- 每秒閃爍超過 3 次：成品 mp4 的最大單格跳變都在 0.6 秒的漸暗漸亮裡（見第二節 3）。
- 八題答案或題卡不一致：沒有。
- 署名錯誤：沒有。
- 外部請求：0 個。
- 當機或無法恢復：沒有。
- 交付版和驗收版不是同一建置：不是，兩者相同。

### 一般問題（依重要性排列，共 6 項）

**G1. 交付資料夾少一個配音資料檔時，舞台卡在「資料包 81／82」，畫面上沒有原因；和使用說明寫的行為也不一樣**
- 位置：`app/src/data/packs.ts` 第 50–54 行 `loadPackFiles`（`Promise.all`，其他檔載完後還會繼續呼叫 onProgress）；`app/src/engine/engine.ts` 第 219 行與第 254–259 行。
- 證據：
  - 我在 scratchpad 複製一份 交付/browser，刪掉 `data/vo_a3_c002.js`。結果 mode＝error、`errors＝["資料包載入失敗：data/vo_a3_c002.js"]`，按鈕停用。但畫面只顯示「資料包 81／82｜準備播放（灰）｜請依上面的訊息修正後重新整理」，上面沒有任何訊息（`ops/t2_missing_vo_60s.png`；5、15、30、60 秒都一樣）。
  - 原因：catch 先寫進「無法開始」，其他資料包隨後載完時，進度回呼把狀態列覆寫回「資料包 81／82」。
  - 對照：刪掉 `data/cues_show.js` 時，「無法開始：資料包載入失敗：data/cues_show.js」會正確顯示（`ops/ops_independent.json` t1）。
  - `交付/使用說明.md` 第三節 A 寫「按『準備播放』時若出現『缺幾句配音』的提示：表示複製時漏了檔」。實際上漏了配音檔時，不會出現這個提示，也進不了 G6 加的「缺配音要按第二次確認」模式。只有 manifest 少登記時才會進那個模式。
- 影響：仍然「停在準備畫面」，符合技術 QA 第 4 項。但老師看到的是一個像當機、又沒有說明的畫面。故障一頁卡也沒有這個症狀。
- 修法：
  1. `loadPackFiles` 改用 `Promise.allSettled`，失敗清單交給呼叫端。vo_*／lip_* 載入失敗時，把那幾句列進 `missingVo`，走既有的缺配音確認流程（顯示缺幾句、按第二次才開演）。其他必要資料包（cues、img、manifest）失敗時，才進 error。
  2. 進 error 後，忽略之後的 onProgress（例如加一個 `failed` 旗標），或在 allSettled 之後再寫「無法開始」，訊息才不會被覆寫。
  3. 故障一頁卡加一列：「準備播放一直是灰的、停在『資料包 n／m』→ 重新複製整個資料夾，或改開 browser\index.html」。
  4. 修完後 engine-test 加一項：刪掉一個 vo 資料檔，要進缺配音確認，畫面也要顯示缺幾句。

**G2. G6 全劇驗收包 (b) 的即時效能和字幕數據不是用交付建置量的**
- 位置：`review/G6/pack/INDEX.md` (b)；`review/G6/pack/live/live_raw.json`（20:34）、`live/perf.json`。
- 證據：
  - live_raw.json 的時間是 20:34。app/dist 是 21:33 才建置，期間 a5_c005 的切點、a8 的 musicDuck 和引擎混音碼都改過（`git diff 897c8e1 78330b5 -- app/src`）。
  - 22:05 用 --skip-live 重產時，舊的播放紀錄被拿去和新時間軸比對，所以 INDEX 出現「字幕內容 3053 筆，不符 2 筆」，兩筆都在 a5_c005 t＝2.25／2.45。
  - 我在交付建置上取樣，t＝1.38–2.62 時字幕「陳伯伯——！」和 vo 發聲一致（`ops/subtitle_samples_a5c005_a8c001.json`）。所以這 2 筆是舊紀錄配新時間軸造成的假警報。
  - INDEX 的段落指紋只比對九段的 cue JSON，不比對 app.js，看不出播放紀錄過期。
- 處理：我在交付建置上重跑了一次全劇（`node tools/show_review_pack.mjs --out review/G7/qa/tech/showpack --skip-engine-test`），結果見 `showpack/INDEX.md`：
  - 影格時間 p95 16.70 ms，最大 16.8 ms。
  - 超過 100 ms 的卡頓 0 次；停格中的長格最長 100 ms。
  - 字幕 3057 筆，0 筆不符；字幕和語音時間差最大 3 ms；嘴型 125／127。
  - 外部請求 0；操作補測 21／21；八題 8／8；接縫 8／8；署名卡兩端正確。
  - 數據達標，所以不扣分，只記錄驗收包流程的缺口。
- 修法：
  - show_review_pack 用 --skip-live 時，比對 live_raw 記錄的建置時間（或 app.js 的 sha1）和目前的 app/dist。不同時，INDEX 標「即時數據來自舊建置」並列出兩個時間。
  - 驗收包也加記 app.js 和 cues_show.js 的 sha1。
  - 以後交付前一律不加 --skip-live 重跑一次（約 27 分鐘）。

**G3. 交付文件有過期敘述和沒填的佔位符，和交付程式不一致**
- `交付/素材與授權表.md` 第 35、220、277 行：寫「three.js 授權聲明沒有隨包」「FluidR3 授權檔沒有放進交付包」。實際上 `交付/browser/THIRD_PARTY_LICENSES.txt` 和 `交付/AntidrugTheater/resources/app/dist/THIRD_PARTY_LICENSES.txt` 都已經有 three.js 0.186.1 MIT 和 FluidR3_GM MIT 全文（62 行，由 app/build.mjs 產生）。
- `交付/總報告.md`：
  - 第 64、397 行還是「〔主線補〕」。
  - 第 70、361 行說「第 2 輪修正後主線會再打包一次（N6）」，但交付包 22:03 已經重新打包，而且我重跑冒煙測試全部通過。
  - 第 95 行說 a0、a3、a6 的 all_ok 是「否」，但現在九份 `_check/*.json` 的 verify.all_ok 都是 true（容差已改，見 REVIEW.md）。
  - 第 77 行說「教師網頁字型的修正要重新發布才生效」，但 gh-pages 23b30db（22:05）已經含 teacher/fonts。
  - 第 84 行 a5 寫 123.3 MB，實際 122.6 MB（README.txt 和 `ls` 都是 122.6）。
- 修法：
  - 素材與授權表第 35、220、277、第 6／8 節改成「已隨包：THIRD_PARTY_LICENSES.txt（兩個交付資料夾都有）」。
  - 總報告填好兩個〔主線補〕，N6 改成 resolved（22:03 打包，冒煙測試報告路徑寫 review/G7/qa/tech/smoke/delivery_smoke.md 或主線自己的一份），all_ok 那段改成「容差改後九段都是 true」，字型改成「已發布」，a5 大小改成 122.6 MB。
  - 這三份 md 只在 交付/ 裡有（專案根目錄沒有副本），直接改 交付/ 裡的檔即可。

**G4. 線上版 gh-pages 的 show/ 比公開 repo 的 main 新，原始碼追不回來**
- 證據：
  - `git ls-remote origin`：main＝fecbdb7（20:59），gh-pages＝23b30db。
  - gh-pages show/ 的 144 個檔，和本機 app/dist 的 blob hash 完全相同（`ghpages/ghpages_show_blobs.txt`、`ghpages/app_dist_blobs.txt`，diff 0）。線上網址抓回來的 index.html、app.js、data/cues_show.js、THIRD_PARTY_LICENSES.txt，hash 也相同（`ghpages/live_fetch.txt`）。
  - 但 gh-pages 的 commit 訊息寫「發布 main fecbdb7」。實際內容是本機 78330b5 的建置，含 a5_c005、a8 musicDuck 和引擎改動（`git diff --stat fecbdb7 78330b5 -- app tools`：17 檔），這些都還沒推上 origin/main。
- 原因：REVIEW.md 記錄，主線等使用者決定改寫歷史，所以暫停推送 main。這是已知的使用者待辦，不扣分。
- 修法：使用者處理強制推送後，推送 main（78330b5 或改寫後的對應 commit）。在那之前，gh-pages 的 commit 訊息或入口頁加註「建置來自本機 main 78330b5（未推送）」，總報告第七節也寫明。

**G5. 備援影片的檢查報告沒有記錄建置指紋**
- 位置：`交付/backup_video/_check/backup_*.json`（沒有 dist、app.js 或段落 sha1 欄位）。
- 證據：a0–a4、a6、a7 在 20:42–21:32 輸出，早於 21:33 的 app/dist。我自己做了三項比對：
  - 九段 71 個章節的 cue 編號和順序，和目前建置的 cues_show.js 逐一相同（`video/chapters_vs_build.json`）。
  - 各 cue 的長度和預捲，和目前時間軸相同，0 處不符（`video/durations_vs_timeline.txt`）。
  - 這段期間引擎只改了混音避讓（`git diff 897c8e1 78330b5 -- app/src/engine app/src/audio`），畫面不受影響。
  - 結論：影片內容和交付建置一致，但這是靠我推論，報告本身證明不了。
- 修法：tools/backup_video.mjs 的檢查 json 加 `build: {distBuiltAt, appJsSha1, segmentSha1}`；README.txt 第六節印出建置時間；交付冒煙測試加一項「備援影片的建置指紋＝app/dist」。

**G6. 交付冒煙測試的八題檢查是用 gotoCue 跳題，不是實際按鍵**
- 位置：`tools/delivery_smoke.mjs` 第 115–140 行。
- 證據：八題流程用 `__engine.gotoCue(id,{mode:'after'})` 直接跳到出題和揭答。實鍵推進的證據在 G6 驗收包 (g)、(e) 和我的實鍵測試（`ops/ops_independent.json` t3）裡，不在交付包測試裡。
- 影響：目前沒有缺陷，但交付包的測試沒有涵蓋「老師用 PageDown 走完一題」。
- 修法：冒煙測試加一段，用 `page.keyboard.press('PageDown')` 從 a1_c004 停格走到 a1_c008（出題→揭答→點燈→續演），每步檢查 phase 和印章。

---

## 二、逐項檢查結果

### 1. 交付版就是驗收的建置（diff 和冒煙測試）
- `diff -rq 交付/browser app/dist`：沒有差異。`diff -rq 交付/AntidrugTheater/resources/app/dist app/dist`：沒有差異。都是 144 個檔。
- 我自己跑 `node tools/delivery_smoke.mjs --out review/G7/qa/tech/smoke`，兩個資料夾各 7／8 項全部通過，結束碼 0（`smoke/delivery_smoke.md`、`smoke/run.log`）：
  - 逐檔相同。
  - Electron 外殼（main.js、preload.js、layout.js、package.json）和 app/electron 相同。
  - file:// 不加參數開 index.html → preparing、71 個 cue、9 段、第一個 cue 是 a0_c000。
  - 缺配音 0、缺配樂音效 0。
  - 印章 2、3、1、1、3、2、3、2；出題時不自動揭答 8／8。
  - 片頭和片尾都是「許博明老師製作」，兩張截圖逐位元組相同（`smoke/browser_title_end.png`）。
  - 外部請求 0／134；頁面錯誤 0。
- 段落指紋：G6 `packs/segment_hashes.json` 9／9 段 builtMatch、sourceMatch、builtFromSource 都是 true，distBuiltAt 2026-10-22T13:33:58Z（＝21:33 的建置）。我重跑的 `showpack/INDEX.md` 也是 9／9。app/ 的工作目錄沒有未提交的改動，建置來源就是 78330b5。
- Electron 的入口是 `stage.html?cues=show&nofs=1`，不是 index.html。我用 Chrome 離線開這個網址：preparing、71 個 cue、201 句配音都就緒、0 錯誤、0 外部請求。console.html 也能正常連線（`ops/electron_pages_in_chrome.json`、`ops/electron_stage_in_chrome.png`）。main.js 第 165–168 行：權限只允許 fullscreen（不開攝影機和麥克風），http、https、ws 請求一律取消，開了 prevent-display-sleep。exe 本身沒辦法執行，標「未驗證」。

### 2. 操作（自己用實鍵測，交付/browser，離線 context）
`ops/ops_independent.json` t3：
- PageDown 從準備畫面進到片頭待機，再進 a0_c001。
- a0_c001 播放中連按 5 下：cue 不變，ignoredInputs＋5。
- 長按（10 次 repeat）：ignoredRepeats＝10，不跳段。
- 句點暫停：1.2 秒內 cueTime 停在 1.16 不動；再按一次繼續，cueTime 往前走。
- R：從 0.23 秒重播同一段。
- 停格時連按 3 下：只前進一段（a0_c002）。
- 播放中按 PageUp：回到上一個穩定節點（a0_c001 停格）。
- F5、Esc 被攔截（blockedKeys＝2），cue 不變。
- 頁面錯誤 0；外部請求 0／134。

G6 驗收包 (e) 和我重跑的 `showpack/ops/ops_show.json` 都是 21／21，包含頁面隱藏、凍結、畫面中斷 4.5 秒、上一步收起字幕。G6 的 engine-test 是 144／144（review/G6/pack/ops/engine_test.log）。

另外：activeVoices 計的是所有音源，不只配音，所以我改看 voiceIds 和 voSounding。a5_c005 的取樣中，同一時間 voSounding 最多 1，沒有配音重疊。用 CDP 的 Page.setWebLifecycleState 凍結 1.5 秒後，舞台沒有自動暫停，但時間連續、cue 不變。這和 G6 的合成 freeze 事件測法不同，結果不能直接比；舞台是前景分頁，實際不太會被凍結，所以不計為問題。

### 3. 備援影片（交付/backup_video）
- **長度、編碼**：用 ffprobe 量，九段的影像長度和聲音長度完全相等：
  - a0 124.13、a1 171.97、a2 290.37、a3 166.20、a4 246.30、a5 193.83、a6 205.83、a7 54.00、a8 39.40 秒，合計 1492.0 秒＝24:52.0，和 README 一致。
  - 規格：1920×1080、30/1 fps、h264＋aac 48 kHz 立體聲。
- **章節**：6＋8＋13＋8＋13＋8＋9＋3＋3＝71＝cue 數。章節標題裡的 cue 編號和建置的順序逐一相同（`video/chapters_vs_build.json`，allOk true）。
- **聲畫同步**（自己算，不用製作端的數字）：拿配音檔起頭 1 秒，和成品 AAC 做正規化互相關。抽 8 句，涵蓋 a0、a2×2、a4、a5×2（含第 2 輪新切點 a5_c005_01）、a6_c009_01、a8_c001_01：誤差都在 −0.3 到 +0.3 ms，相關係數 0.975–0.994（`video/av_sync_independent.jsonl`）。
- **字幕跟上新時間**：a5 第 87.0 秒的畫格顯示小宇頭像加「陳伯伯——！」，和第 2 輪修正後的時間一致（`video/frames/a5_c005_01_subtitle.jpg`）。
- **開頭與結尾署名卡**：a0 第一格和 a8 最後一格都是布幕加「許博明老師製作」署名卡；其他段的頭尾都接在劇情畫面上（`video/first_last_contact.jpg`）。
- **光敏**（在 mp4 上重算）：
  - 每段全畫面 sRGB 亮度最大的 5 個單格跳變都在 0.6 秒漸暗漸亮的連續斜坡裡（in_ramp＝true，ctx 是單調序列），沒有孤立跳變（`video/fullframe_steps_srgb.json`）。
  - a3_c008 切場（第 162.07 秒）單格亮度比 1.061（G6 S1 已修好）。
  - 我用粗略方法數 32×18 格的變化，a1、a3、a4、a7 有幾格算出 4–5 次。抽看 a3 第 3–4 秒，是小晴走路時頭髮上下擺動造成的格線邊緣變化，是物體移動，不是閃爍（`video/a3_osc/`、`video/flash_on_mp4.log`）。紅色數字偏高，也是紅色外套移動造成的。
  - 正式判定以 G5 各段驗收包為準：16×9 和 fine_32x18 都 ≤3，孤立亮度比最大 1.159。
- **檔名與說明**：
  - 檔名只有英數：backup_a0–a8.mp4、README.txt，還有 _check/ 資料夾。
  - README.txt 是 UTF-8 BOM＋CRLF，Windows 記事本可以正常顯示。內容有用法、各段長度、每個 cue 的開始和停格時間、哪裡要暫停、畫質、怎麼重新產生，並標明「播放器操作未驗證」。

### 4. 離線與載入失敗
- 外部請求：冒煙測試 0／134 ×2；我重跑全劇時，即時播放、接縫、操作補測都是 0／134；實鍵測試是離線 context，0。
- Build 字串裡只有 jcgt.org 論文網址和 w3.org XHTML namespace 兩個 URL，都是程式註解或常數，不會發出請求。字型只用系統字（Microsoft JhengHei 優先），沒有 @font-face。
- 載入失敗：少了 cues_show.js → 停在準備畫面，並顯示原因（通過）。少了一個 vo 資料檔 → 停在準備畫面，但原因被蓋掉（見 G1）。

### 5. 效能（v1.2 §24 #5，開發機）
- 交付建置重跑（`showpack/INDEX.md` (b)；Apple M4、Chrome 無頭、1920×1080、畫質 A；系統負載平均 1.62）：
  - 播放中 80,366 格：p95 16.70 ms（門檻 ≤34），最大 16.8 ms。
  - 超過 100 ms 的卡頓 0 次（門檻 ≤2）；在對白或揭答中 0 次。
  - 停格預先建景時，超過 50 ms 的格 13 個，最長 100 ms，畫面靜止。
  - 載入：開頁到片頭待機 7.46 秒。
  - JS heap 215–266 MB，播放中每分鐘增加 0.70 MB。
- 和 G6 20:34 那次結果一致。耐熱測試（待機 30 分鐘＋演出 40 分鐘）和學校筆電：未驗證。

### 6. 第三方授權
- THIRD_PARTY_LICENSES.txt（兩個交付資料夾都有）：開頭一句署名和配音來源（ElevenLabs 付費方案、聲線庫聲線），接著是 three.js 0.186.1 的 MIT 全文、FluidR3_GM 的 MIT 全文（含 Debian 包裝的 GPL 註記，那部分不隨本專案散布）。
- Electron：`交付/AntidrugTheater/LICENSE` 和 `LICENSES.chromium.html` 都在。
- 執行時的依賴只有 three（app/package.json），沒有其他要附的授權。素材與授權表的過期敘述見 G3。

### 7. 線上版
- gh-pages 的 show/ 和 app/dist 完全相同（144 個檔，blob hash diff 0），線上 URL 抓回的檔 hash 也相同，回應 200。
- teacher/pdf 的 11 份 PDF：本機 teacher/pdf、交付/teacher_pdf、gh-pages 三處 hash 都相同（`ghpages/teacher_pdf_compare.txt`）。
- /teacher/ 目錄本身回 404，但入口頁只連到各個 html 和 pdf 檔，所以不影響使用。

### 8. 教師資料和程式版本對得上
- teacher/data/檢查報告.md 的 cue 指紋是 cca5916cc3。我自己照它寫的方法算（依 index.json 順序串接 9 個段落檔原始內容的 SHA-1 前 10 碼），也是 cca5916cc3。教師講稿上印的版本碼也是 cca5916cc3。檢查 21／21 項。
- timing.json：35:45，上限 38:00，緩衝 135 秒。

---

## 三、評分（1–5；4＝達到 G4 基準）

| 項目 | 分數 | 理由與證據 |
|---|---|---|
| 1. 操作 | 4 | 自己用實鍵測連按、長按、暫停與繼續、重播、上一步、停格時連按、F5／Esc 攔截，全部正確（`ops/ops_independent.json`）。全劇補測 21／21，含隱藏、凍結、休眠（`showpack/ops/ops_show.json`）；engine-test 144／144（G6）。交付包冒煙測試的八題是用跳題做的（G6 問題），Windows exe 和簡報筆未驗證，所以不給 5。 |
| 2. 效能 | 4 | 在交付建置上重跑：p95 16.70 ms、超過 100 ms 的卡頓 0、heap 斜率 0.70 MB／分（`showpack/INDEX.md` (b)）。G6 驗收包的即時數據是舊建置量的（G2 問題），已由這次重跑補上。學校筆電和耐熱未驗證。 |
| 3. 同步與光敏 | 4 | 交付建置的字幕和語音時間差最大 3 ms，字幕 3057 筆 0 不符，嘴型 125／127（`showpack`）。備援影片聲畫誤差 ±0.3 ms（自己算的互相關，`video/av_sync_independent.jsonl`）。九段光敏都通過，指紋和交付建置一致；mp4 上沒有孤立跳變，a3_c008 1.061。嘴型有 2 句沒有換片，所以不給 5。 |
| 4. 穩定與離線 | 4 | 外部請求全部是 0，頁面錯誤 0；Electron 擋掉網路，權限只開 fullscreen；載入失敗會停在準備畫面。少了一個配音檔時，畫面看不到原因，和使用說明也不一致（G1），所以不給 5。 |

平均 4.0。沒有嚴重問題。

## 四、給主線的建議（照重要性）
1. 修 G1（allSettled、vo 缺檔走缺配音確認、錯誤訊息不被覆寫、故障卡加一列），修完重建並重跑冒煙測試。
2. G3：交付文件的過期敘述和兩個〔主線補〕，要在交給使用者前填好、改正。
3. G2、G5、G6：工具補上建置指紋和實鍵八題，下次交付前用。
4. G4：等使用者處理推送後，讓 main 和線上版對得上。
