# 專案狀態（檢查點）

開工：2026-10-20（使用者說「開工」）。依 v1.3 三天流程執行。

| 關卡 | 狀態 | 版本／證據 | 時間上限 |
|---|---|---|---|
| 探針包 | 已交付使用者（等待學校實測結果） | probe/build/AntidrugProbe_v01.zip；Mac 冒煙測試 9/9 通過 | 第 1 天上午交付 |
| G1 劇本 | 帶一般問題放行，凍結 v03（主線小修 3 句） | script/*_v03.md；REVIEW.md | 第 1 天 22:00 凍結 |
| G2a 風格 | 選定 S4 立體童書厚卡紙 | review/G2a/ | — |
| G2 母版與試作 | 以退路通過（D-G2-06；畫面品質併入 G4 驗收） | review/G2/*_v04；contrast_v04.json | 第 1 天 22:00（超時約 5 小時） |
| G3 聲音 | 帶一般問題放行（13:50）；全劇配音改 ElevenLabs（使用者 D-G3-07），v04 已上線；a2_c003_02 使用者選 5 號（D-G3-08）；試聽頁 A–G 使用者確認 OK | REVIEW.md G3 關卡決定；review/G3/el/full/；audio/vo/promoted_el.json | 第 2 天 13:00 前 |
| G4 代表鏡頭 | 帶一般問題放行（13:00）；嚴重問題（小宇站姿眨眼）主線修正、新代理複驗通過；共用元件凍結 | REVIEW.md G4 關卡決定；review/G4/qa/recheck_r4/ | 第 2 天 13:00 |
| G5 各幕 | 未開始 | review/G5/ | 第 3 天 09:00 |
| G6 全劇 | 未開始 | review/G6/ | 第 3 天 15:00 |
| G7 交付 | 未開始 | review/G7/ | 第 3 天晚上 |

## 技術骨架（2026-10-20 完成）
app/ 引擎：G4 版（影像紙偶、整體描邊、紙繩操偶線、摺疊布幕、FX4／FX8、臉部換片與對嘴）；typecheck／build 通過，engine-test 86/86，capture 0 錯誤 0 外部請求。第 1 天 QA 待修 7 項已全部修完（commit bc116ad）。
配音（2026-10-21 更新）：Starter 付費方案；全劇 201 句 ElevenLabs eleven_v3（11 個聲線庫聲線），tools/vo_el_prod.py 合成＋自動檢查 → tools/vo_el_promote.py 升為 audio/vo 的 v04；edge-tts 舊檔封存在 audio/_archive_edge/、不打包。兒童用途書面核准待 ElevenLabs 回覆。配樂與音效全部自製（FluidR3_GM，MIT）。engine-test 102/102。

## 本時段目標（第 2 天下午起）
G5 各幕兩批（第 3 天 09:00）：素材量產、六幕 cue 與表演、教師控制台。G4 未達 4 分的美術項目不當基準，改用 REVIEW.md G4 關卡決定列的目標（操偶線平面紙繩 v02 已做好；同場角色組成群體與前後景深）。

## 使用者事項
1. 探針：2026-10-20 19:16 已交付 AntidrugProbe_v01.zip（含 Electron 版、Edge kiosk .bat、file:// 單檔版），等待結果。
2. 金鑰：ElevenLabs 新金鑰可用（TTS、讀聲線、聲線設計），存於 .env（不進 Git）。配樂與音效改自製，Artlist 不再需要。
3. 第 3 天實機彩排：待排。
4. 試聽頁 https://claude.ai/artifact/35yBSYoPKVCWFSDB8m6r3y ：已完成（5 號定版；A–G 使用者回覆 OK）。
5. ElevenLabs 兒童用途書面核准：取得後轉給主線記進 ASSETS.md。
