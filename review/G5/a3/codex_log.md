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

## 2026-10-22 修正第 2 輪（polish；上限 2 張，用 2 張，沒有重抽）

| 第幾次 | 時間 | 檔名（raw） | 用途 | 結果 |
|---|---|---|---|---|
| 1 | 2026-10-22 11:1x | pose_lin_phone_v01 | 林老師朝右、手機貼耳講電話（a3_c008 說完最後一句轉身講電話、走出教室；導演 b2r2 G1「老師走出畫面前舉起手機」） | 採用。參考圖：G2a/S4 畫風、chr-lin_master_v01、chr-xiaoyu_master_v04（比例）。手機是素面深灰圓角長方形（沒有螢幕內容、標誌、鏡頭）、臉完整露出；白邊 8 px、霧邊 0、左右 L* 差 0.8、酒紅毛衣 ΔE 2.6（對母版）。處理：scripts/build_a3_fix2_art.py → assets/final/chr-lin_pose-phone_v01.png，登記 show_characters.json lin.poses.phone（只加這一筆） |
| 2 | 2026-10-22 11:1x | set_a3_classmates_v01 | 教室後排兩個同學的背影（取代 students_v02 的幾何背影；美術 b2r2 抽查第 3 項） | 採用。背面（看不到臉）、同畫風、不透明、有紙纖維；衣服淺色低彩度（淺藍 T 恤＋鵝黃書包、淡紫上衣＋鼠尾草綠書包），和小晴、小宇的配色不同、沒有飽和紅；白邊 10 px、霧邊 0。程式切成兩片 → assets/final/sets/a3_classroom/classmate-a_v01.png、classmate-b_v01.png；students_v01／v02 已刪除（沒有地方再用） |

紀錄：review/G5/a3/import.json（pose_lin_phone_v01、set_a3_classmates_v01）。
