# 第五幕製作進度（每完成一大步附加一行）

- 2026-10-21 22:1x（接續前已完成，由接續代理盤點）：Codex 5 張（陳伯伯 shoutr、小晴／小宇 sitb、救護人員 A/B、醫院牆）處理完放進 assets/final；程式繪製 a5_gate 景片（救護車、頂燈、轉角、擔架、電話、低年級學生）與 a5_hospital（長椅、地板）；尚未：show_characters.json a5 鍵、app/src/sets/a5_gate.ts／a5_hospital.ts、registry、a5.json 表演。下一步：讀規格→登記姿勢→寫景→排 cue。
- 2026-10-21 22:26 show_characters.json 新增 chen standr/shoutr、xiaoqing/xiaoyu sitb、medic_a/medic_b 角色與 6 筆 fallbackFaces。下一步：寫 app/src/sets/a5_gate.ts、a5_hospital（layout.json）。
- 22:33 寫好 app/src/sets/a5_gate.ts（gate 建構器＋街角、轉角小朋友、旗、救護車、擔架、電話圖示、閉眼）與 a5_hospital/layout.json；電話圖示重畫成 v02。下一步：registry 加一行、build、試拍。
- 22:48 a5.json 第一版表演排好（8 cue，私人建置試拍：鏡位避開台口摺幕、救護車放大到 7.0 擋住長椅、林老師坐姿用 0 秒 puppet.pose）。下一步：npm run build、engine-test、驗收包。
- 22:52 npm run build 通過；engine-test 126/130（失敗 4 項都在 a0、a1→a2 換景，非本段）；驗收包第 1 次背景執行中（review/G5/a5/checks/pack_run1.log）。下一步：看驗收包、修、重產。
- 23:27 驗收包第 1 次看完：細格光敏（c001 走位與推鏡、c002/c004 題卡推鏡、c005 環顧搖鏡、c007 進場與救護車）、腕肘線碰到頭部框（頭往左垂）、停格時風聲與電話底音沒降 → 已改（硬切、放慢、錯開、頭往右垂、陣風代替 30 秒風聲、電話底音 0.5）。下一步：npm run build、engine-test、驗收包第 2 次（--skip-asr 沿用逐字稿）。
