# a8 驗收包（閉幕）

- 產生：tools/act_review_pack.mjs（2026-10-22T11:09Z）；段落檔 `app/cues/show/a8.json`；本檔只列數字與檔案。
- 聽感、實際投影、學校硬體：未驗證。
- 段落指紋（sha1，去掉 checkpoint 欄；tools/seg_fingerprint.mjs）：段落檔 `3fc48e344e24120a672608aabd1b8879298c8b31`；app/dist 合併後這一段 `7316245cf5b2e1fd7745f567e700d7847016cd80`；建置用的是目前段落檔：是。

## 檔案

| 項目 | 檔案 |
|---|---|
| 關鍵影格（每個 cue 前／中／後，1920×1080） | capture/keyframes/、capture/contact_keyframes.png |
| 每秒接觸表 | capture/contact_timeline_*.png、capture/frames/ |
| 投影模擬 v2 | proj/16x9/、proj/contact_proj_16x9.png |
| 與 G4 同尺寸並排 | compare_g4/compare_g4_01.png |
| 播放錄製（30 格／秒＋混音） | a8_playback.mp4 |
| 混音與響度 | audio/a8_mix.wav、audio/loudness.json、audio/a8_mix_plot.png |
| 光敏 | flash_playback.json、flash_playback_plot.png、flash_variants.json、capture/flash_report.json、isolated_cuts.json（孤立單格亮度比） |
| 字幕與語音時間差 | subtitle_sync.json |
| 逐字稿 | transcripts.md、transcripts.json |
| 長度對照預算 | durations.json |
| 安全量測 | safety_data.json、probe_dense.json、capture/probe.json、capture/probe_report.json |
| 時間軸與排程 | timeline.json |
| 段落指紋 | segment_hash.json |

## 長度

- 本段 cue 總長 24.8 秒＋換景漸暗預捲 0.6 秒；時長估算_v03.md 預錄合計 30.5 秒；差 -5.1 秒；逐 cue 估計合計 30.5 秒。
- 播放錄製（含教師按鍵間隔假設）30.9 秒。

| cue | 種類 | 長度 | 預捲 | 估計 | 差 | 台詞秒 | 句數 |
|---|---|---|---|---|---|---|---|
| a8_c001 | scene | 18 | 0.6 | 18.5 | -0.5 | 3.05 | 1 |
| a8_c002 | curtain | 5.4 | 0 | 12.0 | -6.6 | 0 | 0 |
| a8_c003 | title | 1.4 | 0 | — | — | 0 | 0 |

## 光敏（任一區域明暗或飽和紅色每秒變化 ≤ 3 次）

- 播放錄製 30 格／秒（16×9 區域＋全畫面，含換景預捲與停住格）：每秒最多 明暗 2、紅色 2；超標 0；接近上限（2–3 次）91；分析 927 格。
- fine_32x18：每秒最多 明暗 3、紅色 2；超標 0；3 次 13。
- proj_16x9：每秒最多 明暗 2、紅色 0；超標 0；3 次 0。
- proj_32x18：每秒最多 明暗 3、紅色 0；超標 0；3 次 3。
- 孤立單格全畫面亮度比（G6 修正：前後格不動、只有一格跳變；> 1.2 判不通過；isolated_cuts.json）：最大 1.128（a8_c001 10.5 秒，播放錄製第 11.1 秒，0.4449→0.5018）；> 1.2 共 0 處。
- **通過判定**（主線裁定 1：16×9 與 fine_32x18 的明暗、紅色每秒都 ≤ 3；G6 起加孤立單格亮度比 ≤ 1.2）：16×9 通過；fine_32x18 通過（明暗 3、紅色 2；超標格 0）；孤立單格亮度比 通過；整段 通過。
- capture.mjs 逐 cue（30 格／秒）：{"ok": true, "max_changes_per_sec": {"luma": 2, "red": 2}}
- cue 接縫全畫面亮度差最大 0.004；區域亮度差最大 0.070。

## 聲音

- 整段：-18.2 LUFS、真峰值 -2.0 dBTP、取樣峰值 -1.97 dBFS、削波 0 個。
- 各句對白：配音檔響度差 0.00 LU、混音中響度差 0.00 LU。
- 瞬間響度最大 -12.3 LUFS；1 秒內最大上升 54.0 LU；100 ms 最大上升 29.0 LU。
- 教師停格 3 秒後配樂 ≤ −35 LUFS：1／1 段通過。
- 只有配樂與音效（不含配音）：瞬間響度最大 -15.7 LUFS（a8_c002 4.4 秒）；100 ms 最大上升 29.0 LU（a8_c002 3.4 秒）；1 秒內最大上升 54.0 LU；取樣峰值 -7.04 dBFS（a8_c002 4.11 秒）、真峰值 -7.0 dBTP（G4 基準：瞬間最大 -15.7 LUFS、100 ms 上升 18.6 LU；不高於 G4 最大值：True）。

| 台詞 | 說話者 | 配音檔 LUFS | 混音中 LUFS | 對白−背景 LU |
|---|---|---|---|---|
| a8_c001_01 | 折折 | -18.0 | -14.5 | 9.2 |

## 字幕與語音時間差（字幕頁起點 − 語音起點，範圍 −0.8～+0.1 秒）

- 1／1 頁在範圍內；最大 -0.124 秒、最小 -0.124 秒。
- 語音起點偵測：ffmpeg silencedetect -40 dB、最短靜音 0.05 秒（G5 修正第 1 輪起；G4 是 −45 dB、0.1 秒，抓不到句中短停頓）。
- 退路（G6 精修）：某頁在範圍內找不到停頓時，改用 -30 dB、最短靜音 0.12 秒重找那一頁；本段用到退路 0 頁。

## 逐字稿（v04 配音）

- small：配音檔逐字正確 0／1 句、混音中 0／1 句。
- large-v3-turbo：配音檔逐字正確 1／1 句、混音中 0／1 句。
- 配音檔都是 v04：True；cue 文字與劇本相同：1／1。

## 安全量測

- 操偶線扣點：本段沒有操偶線（只限 wrist／elbow／knee：True）；有操偶線的角色：無。
- 有操偶線的量測格 0；線到頭部框最短 — px（只算頭部框在畫面內的格；畫面外略過 0 條）；線經過兒童立牌外框 0 格。
- 必要旁白：本段沒有必要旁白。
- 台詞與劇本 v03 逐字不同：0 句（共 1 句）。
- 字幕：每行最多 14 字、每頁最多 1 行。
- 隱私：app.js getUserMedia 0 次、mediaDevices 0 次；擷取時外部網路請求 0 個、主控台錯誤 0 則。
- capture_probe.py 量測：capture/probe_report.json（操偶線 ΔL*、紙環是否在剪影內、兒童站位背景亮度）。

## 其他

- 換景漸暗預捲：{"a8_c001": 0.6}；景：a6_shop；景的建立／釋放 {"active": "a6_shop", "built": 3, "disposed": 2, "lastBuildMs": 10, "liveSetGroups": 1, "lastSwapMs": 9.9, "preparedHits": 0, "prepared": []}。
- 逐格擷取時的頁面錯誤 0 則。
