# 第三幕（a3）新素材：資產表列（給主線併進 ASSETS.md）

2026-10-21 第 2 天晚上，G5 第三幕代理（第二批）。Codex image_gen 只用在角色新姿勢 3 張（上限 4，沒有重抽；紀錄 `review/G5/a3/codex_log.md`）；景片、練習卡、回想小窗、教室全部程式繪製（Pillow＋G2 同款紙紋 `review/G5/shared_art/scripts/paperdraw.py`；腳本 `review/G5/a3/scripts/build_a3_art.py`、`build_a3_art2.py` 可重跑）。生成圖與景片裡沒有任何文字、數字、標誌、紅十字、真實品牌或物流配色；練習卡上的字是程式排版（Noto Sans TC，SIL OFL 1.1，字型檔只在建置時用，放在 `review/G5/a3/fonts/`，不隨演出打包）。

| 檔名 | 類型 | 角色／場景 | 部件／表情 | 使用 cue | 來源／生成參考 | 授權 | 檢視結果 | 版本 |
|---|---|---|---|---|---|---|---|---|
| assets/final/chr-xiaoqing_pose-pointr_v07.png（原檔 assets/generated/ 同名） | 角色姿勢（透明；883×1458） | 小晴 | 「先離開」手指向右（H2；舞台角色指向安全方向） | a3_c004（練習卡口訣第 3 個動作）；練習卡小圖 | Codex image_gen（母版 chr-xiaoqing_master_v04 為參考）；星星髮夾生成在另一側，程式搬回母版同側（scripts/fix_star.py，原位以頭髮內插補上） | 使用者 ChatGPT 方案生成 | 白邊 11 px、霧邊 0、吊帶褲 ΔE 1.8、上衣 ΔE 2.2；退路眨眼兩眼同閉通過（review/G5/a3/blink_check.json） | v07 |
| assets/final/chr-xiaoyu_pose-pointr_v07.png（原檔 assets/generated/ 同名） | 角色姿勢（透明） | 小宇（戴兒童手錶） | 「先離開」戴手錶的手指向右 | a3_c004 | Codex image_gen（母版 chr-xiaoyu_master_v04、standwatch 為參考） | 使用者 ChatGPT 方案生成 | 白邊 12 px、霧邊 0、ΔE 3.7／7.0；兩眼同閉通過 | v07 |
| assets/final/chr-xiaoyu_pose-glasses_v07.png（原檔 assets/generated/ 同名） | 角色姿勢（透明） | 小宇 | 推推眼鏡想一想（H8，臉朝畫面左） | a3_c002「等一下，我想一想」 | Codex image_gen | 使用者 ChatGPT 方案生成 | 白邊 12 px、霧邊 0、ΔE 4.2／4.7；指尖在鼻樑；退路眨眼人工量框、兩眼同閉通過 | v07 |
| assets/final/chr-xiaoqing_pose-forehead-l_v01.png | 角色姿勢（透明；665×1485） | 小晴 | chr-xiaoqing_pose-forehead_v06 左右翻轉：手放額前朝畫面左張望，星星髮夾回到母版同一側 | a3_c004（練習卡口訣第 4 個動作「找大人」） | 程式鏡射（build_a3_art.py poses） | 本專案自製（來源為本專案姿勢圖） | 和 stand／cross／palmno／pointr 同一場時髮夾不跳邊 | v01 |
| assets/final/chr-lin_pose-stand-m_v01.png | 角色姿勢（透明；456×1546） | 林老師 | 站姿左右翻轉（實際臉朝畫面右；修正第 2 輪更正）；退路眼框、嘴框依 lin:stand 鏡射（show_characters.json fallbackFaces lin:stand_m） | （修正第 2 輪起第三幕林老師不再使用；小晴 stand_m 另有一張） | 程式鏡射（build_a3_art2.py） | 本專案自製 | — | v01 |
| assets/final/sets/a3_gate/card_v01.png | 景片（透明；2400×1360，世界寬 6.0） | 台口前緣練習卡 a3_card | 攤開的大紙卡：上排拒絕句「不用，我不試。我先離開。」、下排口訣四格（不碰／不試／先離開／找大人，每格有動作小圖＋口訣） | a3_c004（1.9 秒起立起）、a3_c005 出題時收平 | 程式排版（Noto Sans TC 粗體 weight 850）；動作小圖取自本專案姿勢圖（小晴 cross、小宇 palmno、小晴 pointr、小宇 forehead）膝蓋以上 | 本專案自製；字型 SIL OFL 1.1 | 字是程式排版、不是生成；投影下字高約 45–50 px（1080p） | v01 |
| assets/final/sets/a3_arcade/handbox_v01.png | 景片（透明；866×377） | 騎樓上學路 a3_arcade | 邀請者的手＋貼紙盒（第三幕副本）：拿掉盒子右上角的灰色短棒與白色圓錐紙角（安全界線第 3 條：避免被看成吸嘴），紙邊與盒子上緣補直、盒面用周圍顏色補平；整張彩度 −15%（不搶焦點） | a3_c001、a3_c002 | 程式加工：chr-inviter_hand-box_v01（第一幕共用圖，不改）→ review/G5/a3/scripts/build_a3_fix1_art.py；對照圖 review/G5/a3/art/handbox_fix1_check.png | 本專案自製（來源為本專案 Codex 圖） | 修正第 1 輪（2026-10-22）；沒有真實產品外形、品牌、卡通角色 | v01 |
| assets/final/sets/a3_arcade/memory_v01.png | 畫面疊層（透明；640×640） | 騎樓上學路 a3_arcade | 回想小圓窗：第二幕 a2_c002 結尾被操偶線拉偏的手（腕背、肘外兩個紙環、往上延伸的線），褪色、奶油色手撕紙框；**不含阿樂叔叔的臉** | a3_c002（0.8 秒打開、「我想一想」說完收起） | 程式加工：第二幕驗收包關鍵影格 review/G5/a2/pack/capture/keyframes/a2_c002_025.18_after.png 裁切（build_a3_art.py memory） | 本專案自製（來源為本專案引擎畫面） | 扣點只有腕背、肘外（同第二幕）；不恐怖、不吊掛 | v01 |
| assets/final/sets/a3_classroom/outside_v01.png | 背景（不透明；1040×360） | 教室 a3_classroom | 窗外：午後淡藍天空、雲、對面騎樓屋頂（小窗格，沒有招牌） | a3_c008 | 程式繪製（outside） | 本專案自製 | 無文字 | v01 |
| assets/final/sets/a3_classroom/backwall_v01.png | 景片（透明窗洞；2400×800，世界寬 24） | 教室 | 後牆：奶油色上牆＋鼠尾草綠護牆板、三扇十字窗（玻璃挖空）、沒有數字的時鐘、布告欄（燈籠、貓、房子三張畫，沒有字）、開著的後門 | a3_c008 | 程式繪製（backwall） | 本專案自製 | 無文字、無數字 | v01 |
| assets/final/sets/a3_classroom/board_v01.png | 景片（透明；420×224） | 教室 | 黑板（淺墨綠）＋粉筆畫燈籠、三顆星、燈籠串；**沒有字** | a3_c008 | 程式繪製（board） | 本專案自製 | 無文字 | v01 |
| assets/final/sets/a3_classroom/desk_v01.png、teacherdesk_v01.png | 道具（透明；170×125、160×155） | 教室 | 課桌椅一組；講桌（作業簿封面空白、小燈籠） | a3_c008 | 程式繪製（desk、teacherdesk） | 本專案自製 | 無文字 | v01 |
| ~~assets/final/sets/a3_classroom/students_v02.png~~ | （修正第 2 輪刪除） | 教室後排 | 幾何背影（美術 b2r2 抽查：工藝低於主角），由 classmate-a／b_v01 取代 | — | — | — | — | v02（已刪） |
| assets/final/sets/a3_classroom/classmate-a_v01.png | 景片（透明；378×997） | 教室後排 | 同學 A 背影：短黑髮、淺藍 T 恤、深藍短褲、鵝黃書包（背面，看不到臉；不透明紙片、紙纖維） | a3_c008（開場教室中景，右後方課桌後） | Codex image_gen（set_a3_classmates_v01，參考 G2a/S4 畫風＋小宇母版比例），程式切片（build_a3_fix2_art.py） | 使用者 ChatGPT 方案生成 | 白邊 10 px、霧邊 0；配色和主角不同、無飽和紅；中性設計 | v01 |
| assets/final/sets/a3_classroom/classmate-b_v01.png | 景片（透明；381×946） | 教室後排 | 同學 B 背影：深棕低馬尾、淡紫上衣、淺灰長褲、鼠尾草綠書包（背面，看不到臉） | a3_c008（同上） | 同上 | 使用者 ChatGPT 方案生成 | 白邊 10 px、霧邊 0 | v01 |
| assets/final/chr-lin_pose-phone_v01.png（原檔 assets/generated/ 同名） | 角色姿勢（透明；470×1524） | 林老師 | 朝右（3/4）、右手拿素面深灰手機貼耳講電話，臉完整露出；登記 show_characters.json lin.poses.phone | a3_c008（說完最後一句轉身講電話、慢慢走出教室） | Codex image_gen（pose_lin_phone_v01，參考 G2a/S4、chr-lin_master_v01、chr-xiaoyu_master_v04） | 使用者 ChatGPT 方案生成 | 白邊 8 px、霧邊 0、左右 L* 差 0.8、酒紅毛衣 ΔE 2.6；手機無螢幕內容、無標誌 | v01 |
| assets/final/sets/a3_classroom/floor_v01.png、garland_v01.png | 地板（2048×512）；景片（透明；600×70） | 教室 | 橫向木地板；窗外燈籠串（7 盞粉彩，沿用 square_a1 燈籠串配色） | a3_c008（燈籠串週期 3.4 秒、幅度 ≤0.024 rad 輕擺） | 程式繪製（floor、garland） | 本專案自製 | 不發光、不閃 | v01 |

沿用（沒有新增檔）：sets/square/*（騎樓景，a3_arcade 拿掉長椅、改早晨色彩分級）、sets/square_a1/pillar、garland、chr-inviter_hand-box（邀請者的手；修正第 1 輪起第三幕改用副本 sets/a3_arcade/handbox，第一幕仍用原圖——原圖盒角的灰色短棒請主線決定第一幕是否同樣換掉）、sets/gate/*（a3_gate／a3_card 用 gate.ts 建構器，拿掉小貨車）、sets/gate/set-gate_a4-phone（林老師的手機）。

未打包的中間檔：students_v01／v02 已在修正第 2 輪刪除。另：chr-lin_pose-stand-m_v01 其實是臉朝畫面右（母版 stand 臉朝畫面左）；修正第 2 輪起 a3_c008 林老師說話時用 stand（面向孩子），stand-m 第三幕不再使用。
