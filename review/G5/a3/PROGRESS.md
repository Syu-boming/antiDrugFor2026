# 第三幕（a3）進度紀錄（每完成一大步附加一行：時間｜完成什麼｜下一步）

- 2026-10-21 21:34（前一位，22:0x 額度中斷前）｜Codex 3 張（小晴/小宇 pointr、小宇 glasses）處理完、show_characters.json 加鍵；程式繪製教室零件、練習卡 card_v01、回想小圓窗 memory_v01、小晴 forehead-l｜寫景 .ts、排 a3.json
- 2026-10-21 22:2x（接續）｜檢查既有成果、讀規格｜寫 a3 景（a3_arcade 騎樓、a3_gate 校門口＋練習卡、a3_classroom 教室）
- 2026-10-21 22:29｜教室同學背影 students_v02、林老師 stand_m（鏡射＋退路臉）登記 show_characters.json｜寫 app/src/sets/a3.ts（四個景）
- 2026-10-21 22:39｜app/src/sets/a3.ts 四個景＋registry 一行；make_a3_cues.py 產生 a3.json（8 cue 全排）；私人建置快照檢查構圖（scripts/snap.mjs）｜共用 build、engine-test、驗收包
- 2026-10-21 22:44｜registry 改成每個景一行（engine-test 靠 name: CONST 行找景）；構圖修正第 2 輪；開始產驗收包（act_review_pack --acts a3）｜看驗收包、修問題、重產
- 2026-10-21 23:13｜驗收包第 1 次：細格 32×18 光敏超標（c001 鏡頭橫移、c002 出口走位、c003 進場與品安、c004 翻面太密、c005/c007 紙卡收放、c008 林老師出場）｜改：硬切取代橫移、走位放慢縮短、口訣兩人輪流（和卡上小圖一致）、紙卡加底座不收、c008 重排
