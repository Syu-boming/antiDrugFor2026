# 折折（FX13）預覽與量測

產生：2026-10-21T07:37:54.866Z（`node tools/zhezhe_preview.mjs`；製作代理不挑畫面，取樣時間由節拍固定）

## 檔案

| 檔案 | 內容 |
|---|---|
| `a0_c002_intro_contact.jpg` | 開場影片每 0.5 秒一格 |
| `a0_c002_intro_preview.mp4` | a0_c002 開場自我介紹預覽（配 vo_a0_c002_01／02） |
| `compare_fold_vs_cut_close.png` | 摺紙 vs 剪紙近景並排 |
| `compare_g4_mid_with_kids.png` | G4 中景（g4_mid）整格：折折在工作台上、兩個孩子立牌 |
| `compare_quiz_card.png` | 題卡模式（quiz 鏡位、燈 0.55）折折攤開題卡 |
| `contact_actions.png` | 收摺訊號、耳朵動、走路、跳、摺錯、情緒轉換 |
| `contact_states.png` | 情緒 × 嘴型 × 眨眼 |
| `contrast.json` | 投影模擬明度差 |
| `contrast_proj_sheet.png` | 原圖／投影模擬 v2 對照 |
| `determinism.json` | 確定性（同一秒同一格） |
| `flash.json` | 光敏（每秒變化次數） |
| `folds/fold_card.png` | 貓 ↔ 造型的逐格（dur 等距 12 格＋落定） |
| `folds/fold_hat.png` | 貓 ↔ 造型的逐格（dur 等距 12 格＋落定） |
| `folds/fold_lantern.png` | 貓 ↔ 造型的逐格（dur 等距 12 格＋落定） |
| `folds/fold_magnifier.png` | 貓 ↔ 造型的逐格（dur 等距 12 格＋落定） |
| `folds/fold_megaphone.png` | 貓 ↔ 造型的逐格（dur 等距 12 格＋落定） |
| `folds/fold_plane.png` | 貓 ↔ 造型的逐格（dur 等距 12 格＋落定） |
| `folds/fold_sheet_intro.png` | a0_c002 登場：燈籠紙立起 → 摺、摺、摺 → 貓 |
| `look.png` | 總覽 |
| `perf.json` | 三角面數、繪製呼叫、每格時間 |
| `spin/spin_card.png` | 旋轉掃描 12 方位 × 2 仰角（中性灰底） |
| `spin/spin_hat.png` | 旋轉掃描 12 方位 × 2 仰角（中性灰底） |
| `spin/spin_idle.png` | 旋轉掃描 12 方位 × 2 仰角（中性灰底） |
| `spin/spin_lantern.png` | 旋轉掃描 12 方位 × 2 仰角（中性灰底） |
| `spin/spin_magnifier.png` | 旋轉掃描 12 方位 × 2 仰角（中性灰底） |
| `spin/spin_megaphone.png` | 旋轉掃描 12 方位 × 2 仰角（中性灰底） |
| `spin/spin_plane.png` | 旋轉掃描 12 方位 × 2 仰角（中性灰底） |
| `spin/spin_sheet.png` | 旋轉掃描 12 方位 × 2 仰角（中性灰底） |

`preview/index.html`：直接用瀏覽器開啟的互動預覽（按鈕切換摺紙造型、情緒、動作；「a0_c002 開場」播放登場）。

## 光敏

專案標準（16×9 區域，同 tools/capture_analyze.py）在舞台鏡位（g4_mid、medium）：每秒最多 3 次（上限 3）；飽和紅 0 次；整個畫面 0 次。
壓力測試特寫（close，折折超過畫面一半高）16×9：5 次——變形、跳躍不要在這種特寫裡做。細格 64×36（約 30 px）舞台鏡位：10 次（移動的紙片邊緣掃過小區域；專案標準不採這個尺度，列出供驗收參考）。

各序列「16×9／64×36／飽和紅」：

```
{
 "fold_card": {
  "g4_mid": "3/5/0",
  "medium": "3/8/0",
  "close": "5/9/0"
 },
 "fold_plane": {
  "g4_mid": "1/6/0",
  "medium": "3/8/0",
  "close": "4/11/0"
 },
 "fold_megaphone": {
  "g4_mid": "1/6/0",
  "medium": "3/7/0",
  "close": "4/9/0"
 },
 "fold_magnifier": {
  "g4_mid": "2/4/0",
  "medium": "2/7/0",
  "close": "4/9/0"
 },
 "fold_lantern": {
  "g4_mid": "2/5/0",
  "medium": "2/6/0",
  "close": "4/9/0"
 },
 "fold_hat": {
  "g4_mid": "1/5/0",
  "medium": "2/8/0",
  "close": "3/10/0"
 },
 "fold_sheet_intro": {
  "g4_mid": "2/5/0",
  "medium": "2/10/0",
  "close": "4/13/0"
 },
 "fumble_hat": {
  "g4_mid": "1/5/0",
  "medium": "2/8/0",
  "close": "3/12/0"
 },
 "hush": {
  "g4_mid": "0/2/0",
  "medium": "0/3/0",
  "close": "1/6/0"
 },
 "lantern_glow": {
  "g4_mid": "1/1/0",
  "medium": "1/3/0",
  "close": "1/3/0"
 },
 "walk": {
  "g4_mid": "2/4/0",
  "medium": "2/10/0",
  "close": "3/8/0"
 },
 "hop": {
  "g4_mid": "2/7/0",
  "medium": "3/7/0",
  "close": "5/8/0"
 },
 "fold_card_dur1.8": {
  "g4_mid": "3/4/0",
  "medium": "4/7/0",
  "close": "4/8/0"
 },
 "fold_plane_dur1.8": {
  "g4_mid": "3/6/0",
  "medium": "3/7/0",
  "close": "4/9/0"
 },
 "fold_megaphone_dur1.8": {
  "g4_mid": "1/5/0",
  "medium": "3/6/0",
  "close": "4/9/0"
 },
 "fold_magnifier_dur1.8": {
  "g4_mid": "2/3/0",
  "medium": "2/6/0",
  "close": "3/8/0"
 },
 "hop_dur1.3": {
  "g4_mid": "2/5/0",
  "medium": "3/7/0",
  "close": "5/14/0"
 },
 "talk_wag_happy": {
  "g4_mid": "0/2/0",
  "medium": "0/2/0",
  "close": "0/7/0"
 }
}
```

## 投影模擬 v2 後與背景的明度差

```
{
 "table_g4_mid": {
  "mean_abs_dL_proj": 15.08,
  "edge_outline_median_proj": 21.43,
  "edge_paper_median_proj": 14.42,
  "frac_ge10_proj": 0.668,
  "L_cat": 64.9,
  "L_bg": 79.7
 },
 "table_g4_mid_no_outline": {
  "mean_abs_dL_proj": 11.57,
  "edge_outline_median_proj": 12.14,
  "edge_paper_median_proj": 12.37,
  "frac_ge10_proj": 0.621,
  "L_cat": 68.8,
  "L_bg": 80
 },
 "floor_g4_mid": {
  "mean_abs_dL_proj": 11.95,
  "edge_outline_median_proj": 13.63,
  "edge_paper_median_proj": 7.6,
  "frac_ge10_proj": 0.571,
  "L_cat": 64.8,
  "L_bg": 61.4
 },
 "table_g4_wide": {
  "mean_abs_dL_proj": 14.68,
  "edge_outline_median_proj": 20.82,
  "edge_paper_median_proj": 14.02,
  "frac_ge10_proj": 0.653,
  "L_cat": 64.4,
  "L_bg": 78.2
 },
 "table_close": {
  "mean_abs_dL_proj": 14.66,
  "edge_outline_median_proj": 24.56,
  "edge_paper_median_proj": 36.77,
  "frac_ge10_proj": 0.578,
  "L_cat": 65.3,
  "L_bg": 77.1
 },
 "apron_quiz_light055": {
  "mean_abs_dL_proj": 9.97,
  "edge_outline_median_proj": 6,
  "edge_paper_median_proj": 5.8,
  "frac_ge10_proj": 0.518,
  "L_cat": 57.7,
  "L_bg": 54.1
 },
 "apron_quiz_light055_presence020": {
  "mean_abs_dL_proj": 12.03,
  "edge_outline_median_proj": 6.04,
  "edge_paper_median_proj": 6.23,
  "frac_ge10_proj": 0.59,
  "L_cat": 61.3,
  "L_bg": 54.1
 },
 "apron_quiz_card": {
  "mean_abs_dL_proj": 20.47,
  "edge_outline_median_proj": 7.49,
  "edge_paper_median_proj": 15.64,
  "frac_ge10_proj": 0.832,
  "L_cat": 74.5,
  "L_bg": 54.6
 },
 "apron_quiz_card_presence020": {
  "mean_abs_dL_proj": 24.47,
  "edge_outline_median_proj": 7.95,
  "edge_paper_median_proj": 19.83,
  "frac_ge10_proj": 0.838,
  "L_cat": 78.6,
  "L_bg": 54.6
 },
 "table_lantern_lit": {
  "mean_abs_dL_proj": 7.14,
  "edge_outline_median_proj": 11.52,
  "edge_paper_median_proj": 10.78,
  "frac_ge10_proj": 0.136,
  "L_cat": 73.7,
  "L_bg": 80.6
 }
}
```

## 效能

折折三角面（含外輪廓、所有造型）2234；畫面上可見（依造型）{"idle":842,"card":146,"plane":122,"megaphone":290,"magnifier":522,"lantern":1034,"hat":266,"sheet":194}；
每格 update 0.0126 ms（最慢一批平均 0.027）；整格 有折折 3.06 ms／沒有 2.14 ms（ANGLE (Apple, ANGLE Metal Renderer: Apple M4, Unspecified Version)）

## a0_c002 預覽影片

13.37 秒；_01 句從 4.7 s、_02 句從 7.75 s。影片本身逐格光敏（16×9／64×36／飽和紅）：3／11／0 次每秒。

## 確定性

通過：9 個時間點以五種順序重建，整格像素雜湊完全相同；cue 時間軸轉事件表（zhezheTrackFromTimeline）檢查通過。
