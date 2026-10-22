# 第六幕＋複習＋閉幕（a6／a7／a8）進度紀錄

每完成一個大步驟附加一行：時間｜完成什麼｜下一步。

- 10-21 21:20–21:34（第一次執行，額度中斷）｜Codex 3 張（bow_kids、bow_adults、chr_aqin_stand）生成並處理成立牌（chr-*_pose-bow_v01、chr-aqin_master_v01、鏡像 pinan stand-m／walk-straps-m、xiaoyu standwatch-m）；show_characters.json 已加 bow、aqin、*_m 鍵；程式繪製 a6_square_night/sky、rack，a6_window/tree-四季｜下一步：景程式、段落檔
- 10-21 （第二次執行）開工｜確認上次成果；段落檔 a6/a7/a8.json 尚未動｜下一步：讀介面文件、建景 a6_square_night.ts、a6_window.ts
- 10-21 22:41｜程式繪製第二批（冬春樹修正、室內窗、四季天空、燈籠架 v02、鎮民背影、長桌、小物）；小晴 stand_m 鏡射＋退路臉；景 a6_square_night.ts（主燈摺紙貓、騎樓燈籠串、台口八盞燈、光流）、a6_window.ts、a6_shop.ts（小折折燈、紙卡、口訣卡、微光）＋registry 三行；typecheck 過｜下一步：紙卡圖 make_cards.py、段落檔產生器 make_a678.py、私人建置試拍
- 10-21 22:46｜make_a678.py 產生 a6/a7/a8.json（全排、驗證通過）｜下一步：私人建置＋快照檢查構圖
- 10-21 22:51｜a6 廣場重排（全部收在台口內、主燈放大、夜色紗、燈籠串減量、林老師從帳篷走出）｜下一步：試拍 a6_c008/a6_c009/a7/a8
- 10-21 22:58｜紙卡 make_cards.py（來源 capture_cards.mjs 擷取目前 a3_c002 9.0s、a4_c012 6.0s、a5_c006 6.0s，不含字幕）、口訣卡；a7/a8 試拍、鏡位修正（台口側幕不入鏡）｜下一步：量 cue 長度、共用 build、engine-test、驗收包
- 10-21 23:05｜主線已做台口八盞燈（src/stage/lamps.ts）→ 景的備用燈列關掉、光流改從台口燈下方出發；共用 build 過；engine-test 130/134（失敗 4 項都是別段：a0_c001 G4 原樣、a2_shop 換景三項）｜下一步：驗收包 a6,a7,a8
