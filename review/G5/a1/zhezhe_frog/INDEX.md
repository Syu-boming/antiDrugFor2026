# 折折（FX13）預覽與量測

產生：2026-10-21T08:46:53.001Z（`node tools/zhezhe_preview.mjs`；製作代理不挑畫面，取樣時間由節拍固定）

## 檔案

| 檔案 | 內容 |
|---|---|
| `determinism.json` | 確定性（同一秒同一格） |

`preview/index.html`：直接用瀏覽器開啟的互動預覽（按鈕切換摺紙造型、情緒、動作；「a0_c002 開場」播放登場）。

## 確定性

通過：9 個時間點以五種順序重建，整格像素雜湊完全相同；cue 時間軸轉事件表（zhezheTrackFromTimeline）檢查通過。
