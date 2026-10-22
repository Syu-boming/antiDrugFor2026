# 交付包冒煙測試

- 產生：tools/delivery_smoke.mjs（2026-10-22T17:29:40.519Z，143 秒）；對照建置 `app/dist`。本檔只列結果。
- 整體：通過。

## 交付/browser：通過

| 檢查 | 結果 | 說明 |
|---|---|---|
| 與建置逐檔相同（diff 0） | 通過 | 與 app/dist 不同 0、缺少 0、多出 0（144 個檔） |
| 不加參數開 index.html 載入全劇（71 個 cue） | 通過 | 網址參數「」、preparing、71 個 cue（應為 71）、第一個 a0_c000（段落 a0）、9 段 |
| 配音、配樂音效齊全 | 通過 | 缺配音 0、缺配樂音效 0 |
| 實際按 PageDown 走一題（出題→揭答→點燈→續演，不自動揭答） | 通過 | 起點：a1_c004 停格✓（a1_c004 story_waiting、燈 0）；出題✓（a1_c005 quiz_shown、燈 0）；出題後等 3 秒（不自動揭答）✓（a1_c005 quiz_shown、燈 0）；揭答✓（a1_c006 reveal_waiting、印章 2、燈 0）；點燈✓（a1_c007 story_waiting、燈 1）；續演✓（a1_c008 playing、燈 1） |
| 八題順序與正解 2、3、1、1、3、2、3、2 | 通過 | 8 題、順序 1、2、3、4、5、6、7、8；cue 正解 2、3、1、1、3、2、3、2；印章 2、3、1、1、3、2、3、2（應為 2、3、1、1、3、2、3、2）；出題不自動揭答 8／8 |
| 署名卡兩端「許博明老師製作」 | 通過 | 片頭「許博明老師製作」顯示（a0_c000 title_idle）；片尾「許博明老師製作」顯示（a8_c003 ended）；兩張截圖逐位元組相同 是 |
| 零外部請求 | 通過 | 請求 134 個、外部 0 個 |
| 沒有頁面錯誤 | 通過 | 0 則 |

- 署名卡截圖：browser_title_start.png、browser_title_end.png

實際按鍵走一題（從 a1_c004 停格開始，只按 PageDown；正解 2、點第 1 盞燈）：

| 步驟 | 按鍵 | 應到 | 實際 cue／phase | 剛按下 | 題卡 | 揭答 | 印章 | 亮燈 | 被忽略 | 結果 |
|---|---|---|---|---|---|---|---|---|---|---|
| 起點：a1_c004 停格 | — | a1_c004 story_waiting | a1_c004 story_waiting | — | 收起 | 否 | 無 | 無 | — | 通過 |
| 出題 | PageDown | a1_c005 quiz_shown | a1_c005 quiz_shown | a1_c005 quiz_playing | 顯示 | 否 | 無 | 無 | 0 | 通過 |
| 出題後等 3 秒（不自動揭答） | — | a1_c005 quiz_shown | a1_c005 quiz_shown | — | 顯示 | 否 | 無 | 無 | — | 通過 |
| 揭答 | PageDown | a1_c006 reveal_waiting | a1_c006 reveal_waiting | a1_c006 reveal_playing | 顯示 | 是 | 2 | 無 | 0 | 通過 |
| 點燈 | PageDown | a1_c007 story_waiting | a1_c007 story_waiting | a1_c007 playing | 收起 | 否 | 無 | 1 | 0 | 通過 |
| 續演 | PageDown | a1_c008 playing | a1_c008 playing | — | 收起 | 否 | 無 | 1 | 0 | 通過 |

## 交付/AntidrugTheater/resources/app/dist：通過

| 檢查 | 結果 | 說明 |
|---|---|---|
| 與建置逐檔相同（diff 0） | 通過 | 與 app/dist 不同 0、缺少 0、多出 0（144 個檔） |
| Electron 外殼與 app/electron 相同 | 通過 | main.js 相同、preload.js 相同、layout.js 相同、package.json 相同 |
| 可攜版資料夾有「啟動說明.txt」 | 通過 | 交付/AntidrugTheater/啟動說明.txt：3064 位元組、BOM 有、CRLF 44 行、單獨 LF 0、含署名「許博明老師製作」與啟動步驟 |
| 不加參數開 index.html 載入全劇（71 個 cue） | 通過 | 網址參數「」、preparing、71 個 cue（應為 71）、第一個 a0_c000（段落 a0）、9 段 |
| 配音、配樂音效齊全 | 通過 | 缺配音 0、缺配樂音效 0 |
| 實際按 PageDown 走一題（出題→揭答→點燈→續演，不自動揭答） | 通過 | 起點：a1_c004 停格✓（a1_c004 story_waiting、燈 0）；出題✓（a1_c005 quiz_shown、燈 0）；出題後等 3 秒（不自動揭答）✓（a1_c005 quiz_shown、燈 0）；揭答✓（a1_c006 reveal_waiting、印章 2、燈 0）；點燈✓（a1_c007 story_waiting、燈 1）；續演✓（a1_c008 playing、燈 1） |
| 八題順序與正解 2、3、1、1、3、2、3、2 | 通過 | 8 題、順序 1、2、3、4、5、6、7、8；cue 正解 2、3、1、1、3、2、3、2；印章 2、3、1、1、3、2、3、2（應為 2、3、1、1、3、2、3、2）；出題不自動揭答 8／8 |
| 署名卡兩端「許博明老師製作」 | 通過 | 片頭「許博明老師製作」顯示（a0_c000 title_idle）；片尾「許博明老師製作」顯示（a8_c003 ended）；兩張截圖逐位元組相同 是 |
| 零外部請求 | 通過 | 請求 134 個、外部 0 個 |
| 沒有頁面錯誤 | 通過 | 0 則 |

- 署名卡截圖：AntidrugTheater_resources_app_dist_title_start.png、AntidrugTheater_resources_app_dist_title_end.png

實際按鍵走一題（從 a1_c004 停格開始，只按 PageDown；正解 2、點第 1 盞燈）：

| 步驟 | 按鍵 | 應到 | 實際 cue／phase | 剛按下 | 題卡 | 揭答 | 印章 | 亮燈 | 被忽略 | 結果 |
|---|---|---|---|---|---|---|---|---|---|---|
| 起點：a1_c004 停格 | — | a1_c004 story_waiting | a1_c004 story_waiting | — | 收起 | 否 | 無 | 無 | — | 通過 |
| 出題 | PageDown | a1_c005 quiz_shown | a1_c005 quiz_shown | a1_c005 quiz_playing | 顯示 | 否 | 無 | 無 | 0 | 通過 |
| 出題後等 3 秒（不自動揭答） | — | a1_c005 quiz_shown | a1_c005 quiz_shown | — | 顯示 | 否 | 無 | 無 | — | 通過 |
| 揭答 | PageDown | a1_c006 reveal_waiting | a1_c006 reveal_waiting | a1_c006 reveal_playing | 顯示 | 是 | 2 | 無 | 0 | 通過 |
| 點燈 | PageDown | a1_c007 story_waiting | a1_c007 story_waiting | a1_c007 playing | 收起 | 否 | 無 | 1 | 0 | 通過 |
| 續演 | PageDown | a1_c008 playing | a1_c008 playing | — | 收起 | 否 | 無 | 1 | 0 | 通過 |

