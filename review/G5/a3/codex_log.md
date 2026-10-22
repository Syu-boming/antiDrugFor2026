# 第三幕（a3）Codex 生成紀錄

上限 4 張（每週額度剩約 40%，撐到 10/27）。作法：review/G5/a3/raw/_run.sh（codex exec 內建 image_gen，輸出 ~/.codex/generated_images/，原檔複製到 raw/，處理後進 assets/generated、assets/final）。同一張最多重抽 1 次。

| 第幾次 | 時間 | 檔名（raw） | 用途 | 結果 |
|---|---|---|---|---|
| 1 | 2026-10-21 21:21 | pose_xq_pointr_v07 | 小晴「先離開」手指向右（H2，a3_c004 口訣；舞台角色指向安全方向） | 採用（21:24 產出）。星星髮夾畫在另一側，程式搬回母版同側（scripts/fix_star.py → raw/pose_xq_pointr_v07_fix.png），髮夾原位用頭髮內插補上（近看有淡淡的補痕，舞台尺寸約 15 px）；自動檢查通過（白邊 11 px、霧 0、ΔE 1.8／2.2） |
| 2 | 2026-10-21 21:21 | pose_xy_pointr_v07 | 小宇「先離開」手指向右（H2，戴手錶的左手指） | 採用（21:24）；白邊 12 px、霧 0、ΔE 3.7／7.0 |
| 3 | 2026-10-21 21:21 | pose_xy_glasses_v07 | 小宇推推眼鏡想一想（H8，a3_c002「等一下，我想一想」） | 採用（21:24）；指尖在鼻樑、碰到遠側眼睛右下角一點；白邊 12 px、霧 0、ΔE 4.2／4.7；退路眨眼人工量框、兩眼同閉通過 |

合計 3 次（上限 4），沒有重抽。處理：scripts/process_a3_chars.py（import.json）、scripts/measure_a3_faces.py（face_boxes.json、blink_check.json、faces/）。

2026-10-21 22:5x（接續）：沒有再生成。其餘全部程式繪製或鏡射：小晴 forehead-l（forehead_v06 鏡射）、林老師 stand-m（母版鏡射）、教室同學背影 students_v02（取代 v01 灰色人形）。上限 4 張用了 3 張，剩 1 張未用。

2026-10-22 修正第 1 輪：沒有生成（上限 2 張，用 0 張）。盒角灰色短棒用程式修圖（review/G5/a3/scripts/build_a3_fix1_art.py → assets/final/sets/a3_arcade/handbox_v01.png）；品安、林老師、孩子的新走位都用既有姿勢（walk_straps_m、stand、stand_m、standwatch）。
