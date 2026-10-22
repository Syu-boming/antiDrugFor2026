# 第二幕修正第 1 輪 Codex image_gen 紀錄（上限 2 張；只用在驗收指出的問題）

| 次 | 時間 | 檔名（raw） | 用途（對應驗收） | 結果 |
|---|---|---|---|---|
| 1 | 2026-10-21 22:27 | a2_ye_phone_v01 | 葉護理師蹲姿手機貼耳（導演一般問題 4：a2_c012 打電話沒演） | 22:30 完成，採用：裁到不透明範圍＋16 px、清掉 alpha<32 的淡霧 → assets/final/chr-ye_pose-crouchphone_v01.png（原圖 assets/generated/ 同名）；show_characters.json 葉護理師加 crouchphone（headTop 依 crouch 比例換算） |

合計 1 張（上限 2）；沒有重抽。

## 修正第 2 輪（2026-10-22）
- 生成 0 張（上限 2）。新素材全部程式繪製或母版加工：square_a1/shopwall_v01（燈籠店門面牆）、a2_shop/insert-ale-*（手部近景的母版分件處理版）；腳本 review/G5/a0/scripts/build_fix2_art.py、review/G5/a2/scripts/build_fix2_a2_art.py。

## G6 精修（2026-10-22）
- 生成 0 張（上限 2）。新素材都是母版或 G2 景片加工：品安看柱子 look1／look2、手部近景 hand v02、牆上吊燈籠 hanglamps；腳本 review/G5/a0/scripts/build_polish_art.py。
