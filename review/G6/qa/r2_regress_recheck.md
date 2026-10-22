# G6 重驗（抽查改壞）結構化結果

來源：工作流 wf_7c9d4ebd-c0e 的 StructuredOutput（主線 G7 另存）。

## 帶問題放行回查

| 項目 | 判定 | 證據 |
|---|---|---|
| G4：小宇站姿半閉格眼皮雜點、閉眼補片明暗差 | 未驗證 | 驗收包沒有逐格眨眼放大圖 |
| G4：小宇 stepback 閉眼線下方眼白殘影 | 未驗證 | 驗收包沒有逐格眨眼放大圖 |
| G4：翻面到第一次眨眼 0.32 s（建議 ≥0.4 s） | not | REVIEW G6 第 1 輪主線裁定 FLIP_BLINK_GAP 維持 0.3 秒（接受） |
| G4：ASSETS／REVIEW 的 ElevenLabs 用量改指向 ledger.json | resolved | ASSETS.md 第 88、142 行以 audio/vo_el/ledger.json 為準，不再抄合計數字 |
| G4：膝前線到阿樂頭部框 21.6 px（a8_c002） | resolved | review/G5/a8/pack/INDEX.md：本段沒有操偶線 |
| G4 未達 4 分：操偶線改平面紙繩 | partial | a5_c005_001／010 線身平滑、兩側深灰邊；沒有量週期斜紋，投影未驗證 |
| G4 未達 4 分：構圖群體與景深 | partial | a6_c007、a8_c001 群體構圖成立；a5_c005_010 孩子與阿樂分在畫面兩端（劇情需要） |
| G3：自動檢查未通過的 23 句 | 未驗證 | 聽感；a0–a4 驗收包用 --skip-asr |
| G3：PSOLA 重後製角色的失真 | 未驗證 | 只能用耳朵判斷 |
| G3：全劇配音總長 14.15 分，G5 依實際句長排時間 | resolved | 預錄 1322.3 秒＋預捲 10.8 秒，教師時間加播放 35:45 ≤38（INDEX (a)） |
| G3：a2_c002＋a2_c004 46.84 s 超過 45 s | resolved | G4 已結案；全劇時間在 38 分內（teacher/data/檢查報告.md） |
| G3：a2_c002_02 small 模型轉成「竹樹」 | 未驗證 | a2 transcripts.md 是 10/21 版，這次用 --skip-asr |
| G5 共用元件：資料包約 212 MB 一次載入 | partial | 開發機 JS heap 215–266 MB、斜率 0.68 MB／分（live/perf.json）；學校筆電未驗證 |
| G5 共用元件：換景全暗那一格最長 83 ms | partial | 播放中 >50 ms 0 格；停格中預先建景仍有 13 格 >50 ms、最長 100.0 ms（INDEX (b)） |
| G5 共用元件：全劇 1391 s 比 v03 多 78 s | resolved | 現在 1333.1 秒（INDEX (a)） |
| G5 共用元件：Electron 只在 macOS 跑過 | 未驗證 | 沒有 Windows 實機 |
| G5 共用元件：控制台與引擎授課時鐘一致 | resolved | 查核點一律用 atMinute，cue、講稿、操作卡、範本一致（檢查報告.md） |
| a1：Q1 點燈後連兩次暗亮、孩子停在走路中途約 3 秒 | partial | 獨立量測只剩 a1_c007 第 4.9 秒一次暗亮，a1_c008 開頭沒有（flash_a1.json）；停在走路中途沒有查 |
| a1：小晴翻面約 0.15 秒 | 未驗證 | 沒有逐格證據 |
| a1：切近景前一格亮 11% | partial | a1_c008 9.2 秒仍有單格 1.122 倍（低於 1.2，isolated_cuts.json） |
| a1：品安轉身看不出在看柱子 | 未驗證 | a1 本輪只改音效，沒有目視證據 |
| a4：a4_c002 轉場露出俯視與深紅布幕、3.3 秒空天空 | resolved | 天空鏡頭已拿掉，改成地圖立起（r2_regress/a4c002_a5c005_a7c002_contact.jpg） |
| a4：地圖左下深紅棕色塊、斑馬線影子殘影 | 未驗證 | 接觸表解析度不夠 |
| a4：兒童身後背景投影 0.34–0.41 | 未驗證 | 投影 |
| a4：sfx_ambulance_engine 未改名 | resolved | 主線裁定名稱正確、不改（REVIEW G6 第 1 輪） |
| a2：a2_c012 求助鏡頭約 1.2 秒太短 | not | a2.json 本輪沒改 a2_c012 |
| a2：a2_c002 膝線對比 13.9／投影 9.9 | not | G4 cue，表演不改 |
| a2：手部近景手指簡化 | not | 沒有改動 |
| a0：摺紙最後縮成小點 | 未驗證 | 沒有逐格證據 |
| a0：摺放大鏡時折折被小宇擋住一半 | resolved | a0 contact_keyframes a0_c004 14.30 秒折折完整可見 |
| a0：上半部空牆 | partial | a0_c003 仍有大片空牆，a0_c004 有架上燈籠 |
| a0：門邊吊牌模糊灰影 | 未驗證 | 解析度不夠 |
| 共同：揭答蓋章聲 100 ms 上升約 47 LU | not | a4 只有配樂音效時 100 ms 最大上升 46.9 LU、a6 45.4、a5 43.3（各段 INDEX）；聽感未驗證 |
| a5：低年級小朋友幾何粗模 | 未驗證 | 沒有對應影格 |
| a5：救護人員的頭單獨浮在車身前約 0.3 秒 | 未驗證 | 沒有逐格證據 |
| a5：景片平 | not | a5_c005_010 景片仍是平面層 |
| a6：灰色無臉人影 | partial | a6 contact_keyframes 沒看到，只查了關鍵影格 |
| a6：Q8 孤字斷行 | resolved | a6_c003 題卡三行都沒有孤字（a6 contact_keyframes） |
| a6：a6_c009 沒有摺燈的手部動作 | partial | a6_c009 結尾阿樂叔叔雙手在燈前；動作過程沒有逐格查 |
| a6：夜景偏粉褐 | not | a6_c007 夜景色調大致沒變 |
| a6：a6_c007 高潮中段黑場 | resolved | 獨立量測 a6 在 137.8–158.8 秒沒有漸暗（flash_a6.json）；接觸表是台口後拉 |
| a8：合幕沒回台口 | resolved | a8_c002 1.0–4.0 秒台口全景加八盞燈（a8 contact_timeline_01） |
| a8：鞠躬只有點頭 | resolved | a8.json a8_c001 第 15.0 秒全體 bow 12°、阿樂 32° |
| a8：孩子壓扁彈起進場 | partial | 進場點頭仍帶 squash 0.14（a8.json a8_c001 第 3.6–8.75 秒） |
| a8：阿樂叔叔沒有謝幕時刻 | resolved | a8_c001 11–13 秒站起舉小折折燈致意（frames/a8_c001_012.00.jpg） |
| a3：練習卡立起佔多數「3 次」窗 | not | a3 fine_32x18 仍是 3／3（INDEX），沒有改 |
| a5：a5_c007 只縮 1.75 秒 | partial | a5 本輪又短 3.45 秒（a5_c005），a5 總長 175.6 秒 |
| a5：遠景小朋友身後看得到貨車車尾 | 未驗證 | 沒有對應影格 |
| G5 第二批：小宇手錶左右腕不一 | 未驗證 | a6_c007 鏡像姿勢下手錶看不清 |

## 分數

| 項目 | 分數 | 證據 |
|---|---|---|
| 技術 QA 1 操作 | 4 | 自己重跑 engine-test 138／138（review/G6/qa/r2_regress/engine_test_r2regress.log）；全劇補測 21／21（review/G6/pack/ops/ops_show.json）。驗收包的 ops/engine_test.log 是 137／138：計時型測試在高負載下失敗，不是程式改壞 |
| 技術 QA 2 效能 | 4 | review/G6/pack/live/perf.json、INDEX (b)：p95 16.70 ms，播放中 >100 ms 0 格、>50 ms 0 格；停格中最長 100.0 ms（13 格 >50 ms）；學校筆電未驗證 |
| 技術 QA 3 同步與光敏 | 4 | 字幕時間差最大 3 ms、字幕內容 0 不符、嘴型 125／127（INDEX (b)）；自己獨立量九段 playback.mp4：沒有 >1.2 倍的單格硬切，16×9 每秒 ≤3、紅色 0（review/G6/qa/r2_regress/flash_a0…a8.json、indep_flash_r2.py） |
| 技術 QA 4 穩定與離線 | 4 | 外部請求 0、頁面錯誤 0（live/network.json）；diff -rq app/dist 交付/browser 與 交付/AntidrugTheater/resources/app/dist 都 0 差異；gh-pages show/ 143／143、teacher 42／42 個 blob 與本機相同 |
| 校長／教育專業 3 用語與安全 | 4 | teacher/data/檢查報告.md 21／21；node tools/teacher_docs.mjs --check：cue 指紋一致；r2_regress.md 逐條核對安全界線 |
| 校長／教育專業 4 課堂可行 | 3 | 教師時間加播放 35:45（≤38 分）、查核點與 atMinute 一致；但 交付/使用說明_初步完成說明.md 停在 10:10 的舊內容，備援影片也還沒產生 |
| 兒童劇場導演 3 表演與節奏 | 4 | a6_c007 孩子轉頭看燈、品安點頭（r2_regress/a6_c007_kids_5s_vs_14s.jpg）；a8_c001 阿樂叔叔站起舉燈致意、全體鞠躬（review/G5/a8/pack/capture/contact_timeline_01.png）；a5_c005 開頭鏡頭容易誤認人物 |
| 兒童劇場導演 5 情感 | 4 | a8_c001 11–13 秒阿樂叔叔舉燈致意（frames/a8_c001_012.00.jpg）；a6_c007 主燈亮起時角色有反應（r2_regress/a6_c007_9-14s.jpg） |
