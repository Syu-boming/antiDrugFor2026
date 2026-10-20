# 專案狀態（檢查點）

開工：2026-10-20（使用者說「開工」）。依 v1.3 三天流程執行。

| 關卡 | 狀態 | 版本／證據 | 時間上限 |
|---|---|---|---|
| 探針包 | 已交付使用者（等待學校實測結果） | probe/build/AntidrugProbe_v01.zip；Mac 冒煙測試 9/9 通過 | 第 1 天上午交付 |
| G1 劇本 | 未開始 | script/ | 第 1 天 22:00 凍結 |
| G2a 風格 | 未開始 | review/G2a/ | — |
| G2 母版與試作 | 未開始 | review/G2/ | 第 1 天 22:00 |
| G3 聲音 | 未開始 | review/G3/ | — |
| G4 代表鏡頭 | 未開始 | review/G4/ | 第 2 天 13:00 |
| G5 各幕 | 未開始 | review/G5/ | 第 3 天 09:00 |
| G6 全劇 | 未開始 | review/G6/ | 第 3 天 15:00 |
| G7 交付 | 未開始 | review/G7/ | 第 3 天晚上 |

## 技術骨架（2026-10-20 完成）
app/ 引擎骨架：build／typecheck／engine-test 45/45／capture 通過；技術 QA 無嚴重問題。G4 前待修：demo Q2 選項同步 script v02、字幕詞語邊界斷行、WAIT_GUARD 350ms、開幕後角色瞬間出現、布幕移動約 1.6 秒（規格約 2 秒）、光敏報告列出接近上限的區域、紙偶名單改讀 cue。

## 本時段目標
開工設定、探針包、劇本（主線 A）、風格樣張。

## 使用者事項
1. 探針：2026-10-20 19:16 已交付 AntidrugProbe_v01.zip（含 Electron 版、Edge kiosk .bat、file:// 單檔版），等待結果。
2. 金鑰：ElevenLabs 金鑰已存於 .env（不進 Git），但缺 text_to_speech 與 voices_read 權限，需使用者重建金鑰；Artlist MCP 接在桌面版，Claude Code 尚無法使用。
3. 第 3 天實機彩排：待排。
