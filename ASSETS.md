# 素材與授權表

> 本檔是製作過程的流水帳（含舊版）。**最後演出實際用到的素材與授權，請看交付版整理 review/G7/素材與授權表.md**；先前漏登記的 50 檔已併在本檔最後一節。

## 正式版本（G2 第 3 輪，待 G2 第 3 輪重驗）

第 3 輪只重做有問題的部分。三位角色母版（chr-*_master_v02.png）與阿樂困惑換片頭（chr-ale_head-worried_v02.png）**不變、繼續是正式版**；被取代的是 kit_ale_v02／parts/ale_v02（改由母版直接切件）與 bg-square_v02（改成分層景片）。生成方式與第 2 輪相同：`codex exec` 內建 image_gen，附 review/G2a/S4.png＋第二張參考圖（review/G2/raw/_run_batch.sh；提示檔 review/G2/raw/<id>.prompt.txt、第二張參考圖路徑 <id>.ref2）。第一次批次（2026-10-20 23:10）因 ChatGPT 用量上限全部失敗（錯誤訊息「You’ve hit your usage limit … try again at 02:17」；失敗紀錄已被重跑覆寫），額度恢復後 2026-10-21 02:19 重跑，8 張都是第 1 次生成成功、未修改。

| 檔名 | 類型 | 角色／場景 | 部件／表情 | 使用 cue | 來源／生成參考 | 授權 | 檢視結果 | 版本 |
|---|---|---|---|---|---|---|---|---|
| assets/generated/chr-xiaoqing_pose-reach-worried_v03.png | 表演姿勢圖（透明 PNG，1024×1536） | 小晴 | 身體轉向左（阿樂）、前傾，近側手往左上指向手腕的線、另一手收在胸前；擔心表情 | a2_c002（試作） | Codex image_gen（第 1 次生成，未修改）；原檔 review/G2/raw/pose_xiaoqing_reach_v03.png；提示 pose_xiaoqing_reach_v03.prompt.txt；參考 S4＋chr-xiaoqing_master_v02.png | 使用者 ChatGPT 方案生成 | 無文字；星星髮夾摺層清楚、筆記本有線圈且封面空白；服色同母版；4.50 頭身（review/G2/proportion_grid_v03.png） | v03 |
| assets/generated/chr-xiaoyu_pose-stepback-surprised_v03.png | 表演姿勢圖（透明 PNG，1024×1536） | 小宇 | 側身、重心後移半步、雙手縮到胸前，視線看向左上（阿樂的手腕）；驚訝表情 | a2_c002（試作） | Codex image_gen（第 1 次生成，未修改）；原檔 review/G2/raw/pose_xiaoyu_stepback_v03.png；提示 pose_xiaoyu_stepback_v03.prompt.txt；參考 S4＋chr-xiaoyu_master_v02.png | 使用者 ChatGPT 方案生成 | 無文字；圓框眼鏡、小背包；外套 #E1572C，和母版 #D95429 差 ΔE00 1.85（同色，未加深）；4.12 頭身（後退姿勢使垂直高度略短） | v03 |
| assets/generated/bg-square-sky_v03.png | 景片：天空（不透明 PNG，1536×1024） | 廣場 | 和紙天空＋撕紙雲 | —（待 G2 重驗） | Codex image_gen（第 1 次，未修改）；原檔 review/G2/raw/bgL0_sky_v03.png；參考 S4＋review/G2/raw/stage_square_v02.png | 使用者 ChatGPT 方案生成 | 無文字；舞台上降彩 ×0.78 | v03 |
| assets/generated/bg-square-mountains_v03.png | 景片：遠山（透明 PNG） | 廣場 | 兩層撕紙山 | — | 同上；原檔 bgL1_mountains_v03.png | 使用者 ChatGPT 方案生成 | 無霧；舞台上降彩 ×0.78 | v03 |
| assets/generated/bg-square-backrow_v03.png | 景片：後排建築（透明 PNG） | 廣場 | 五間紅磚街屋 | — | 同上；原檔 bgL2_backrow_v03.png | 使用者 ChatGPT 方案生成 | 無文字、無匾額；山牆只有幾何紋 | v03 |
| assets/generated/bg-square-arcade_v03.png | 景片：前排騎樓立面（透明 PNG） | 廣場 | 二樓紅磚＋一個大拱廊開口（兩根柱） | — | 同上；原檔 bgL3_arcade_v03.png | 使用者 ChatGPT 方案生成 | 開口內透明，後面放程式畫的「騎樓陰影內牆＋門洞」局部背板 | v03 |
| assets/generated/bg-square-trees_v03.png | 景片：行道樹兩棵（透明 PNG） | 廣場 | 三層色紙樹冠 | — | 同上；原檔 bgL4_trees_v03.png | 使用者 ChatGPT 方案生成 | 兩棵分開、可各自切出 | v03 |
| assets/generated/bg-square-planters_v03.png | 景片：洗石子花台三個（透明 PNG） | 廣場 | 高、中、長矮三種 | — | 同上；原檔 bgL5_planters_v03.png | 使用者 ChatGPT 方案生成 | 角色身後兩個當局部亮背板（去掉頂上植物、石材往紙白提亮 ×0.18）；右側一個保留原樣 | v03 |
| assets/parts/ale_v03/*.png（12 件）＋ parts.json、_labels.png | 分件紙偶部件（透明 PNG，母版畫布 1024×1656 座標） | 阿樂叔叔 | head、torso（含圍裙）、upper_arm_r/l、forearm_r/l、hand_r/l、thigh_r/l、shin_r/l | a2_c002（試作） | **以正式母版 chr-ale_master_v02.png 直接切件**：tools/split_parts.py --layout master_v03（實作 tools/master_cut.py）；不生成、不縮放（全部 ×1.000） | 使用者 ChatGPT 方案生成（母版） | 站姿組回 vs 母版 IoU 0.9984；逐件輪廓誤差 95 百分位最大 6.8 px（目標 ≤30）；部件本身無白邊，部件間 2.5 px 深色接縫；上臂在軀幹後層、肩部舌片藏在軀幹肩球後；舉臂／受拉兩姿勢關節空洞 0 px（review/G2/kit_ale_v03_poses.png、kit_ale_v03_assembly.json） | v03 |

程式產出的驗收圖（不是素材）：review/G2/stage_composite_v03.png（含 43、1024×768、nosub）、stage_layers_v03.png、stage_grade_compare_v03.png、stage_feet_closeup_v03.png、contrast_table_v03.png、contrast_rings_v03.png、contrast_v03.json、intent_force_demo_v03.png、kit_ale_v03_*、proportion_grid_v03.png、quizcard_q1_*_v03.png／.json、quizcard_q1_sims_v03.png、interaction_storyboard_v03.png、review/G2/sim/*_v03_*。

## 第 2 輪版本（母版與換片頭仍是正式版；kit_ale_v02、parts/ale_v02、bg-square_v02 已被第 3 輪取代）

| 檔名 | 類型 | 角色／場景 | 部件／表情 | 使用 cue | 來源／生成參考 | 授權 | 檢視結果 | 版本 |
|---|---|---|---|---|---|---|---|---|
| assets/generated/chr-ale_master_v02.png | 角色母版（透明 PNG，1024×1656） | 阿樂叔叔 | **正式母版**：全身 3/4 站姿、中性微笑 | —（待 G2 重驗） | chr-ale_master_v01.png（＝review/G2/raw/master_ale_propfix.png，6.15 頭身）→ tools/flatten_shading.py --preset ale（移除圍裙斜向暗面、褲管暗褶、襯衫暗面；alpha<24 淡霧清除）；對照 review/G2/ale_flatten_v02.png、數據 review/G2/flatten_ale_v02.json | 使用者 ChatGPT 方案生成 | 6.15 頭身（review/G2/proportion_grid_v02.png）；各服裝區塊中位色 ΔE76 ≤0.4（固有色不變）；臉、手、鞋未處理。review/G2/raw/master_ale.png 是**未採用**的原始生成（5.68 頭身），不得當母版使用 | v02 |
| assets/generated/chr-xiaoqing_master_v02.png | 角色母版（透明 PNG，1024×1536） | 小晴 | 全身 3/4 站姿、中性微笑 | —（待 G2 重驗） | review/G2/raw/master_xiaoqing.png → tools/flatten_shading.py --preset xiaoqing（移除吊帶褲右側暗面、上衣暗面；alpha<24 淡霧清除）；對照 review/G2/xiaoqing_flatten_v02.png | 使用者 ChatGPT 方案生成 | 4.45 頭身；服色中位數不變（ΔE76 ≤0.2）；星星髮夾摺層、筆記本空白封面保留 | v02 |
| assets/generated/chr-xiaoyu_master_v02.png | 角色母版（透明 PNG，1024×1496） | 小宇 | 全身 3/4 站姿、中性微笑 | —（待 G2 重驗） | review/G2/raw/master_xiaoyu_propfix.png（**外套還原基準橘紅 #D95429，L* 53.2**，不再壓暗）→ tools/flatten_shading.py --preset xiaoyu（移除外套、短褲、腿部暗面；臉不處理）；色票與色差 review/G2/jacket_deltaE_v02.png | 使用者 ChatGPT 方案生成 | 4.45 頭身；外套與原始生成同位置 ΔE00 0.5–1.4（5 點中 4 點；1 點落在拉鍊旁 6.0） | v02 |
| assets/generated/chr-ale_head-worried_v02.png | 換片頭（透明 PNG，1254×1254） | 阿樂叔叔 | 困惑、需要幫忙（不微笑） | a2_c002（試作） | Codex image_gen（第 1 次生成）；提示 review/G2/raw/head_ale_worried_v02.prompt.txt；參考 review/G2a/S4.png＋review/G2/raw/ref_ale_head_v01.png | 使用者 ChatGPT 方案生成 | 無文字；髮型、鬍渣、膚色與母版一致；對齊微笑頭 IoU 0.89（rig 部件 assets/parts/ale_v02/rig/head_worried.png） | v02 |
| assets/generated/chr-ale_kit_v02.png | 分件套件圖（透明 PNG，1536×1024） | 阿樂叔叔 | 13 件（圍裙下襬獨立成件） | — | Codex image_gen（第 1 次生成）；提示 review/G2/raw/kit_ale_v02.prompt.txt；參考 review/G2a/S4.png＋chr-ale_master_v02.png；原檔 review/G2/raw/kit_ale_v02.png | 使用者 ChatGPT 方案生成 | 13 件齊全、互不相連（review/G2/kit_ale_v02_parts_sheet.png）；生成比例仍偏差（頭大、手大、軀幹短），原樣組裝 IoU 0.78 → 逐件校正後 0.87（review/G2/kit_ale_v02_assembly.png） | v02 |
| assets/generated/bg-square_v02.png | 景板（PNG，1672×941，16:9） | 廣場（暖色日光） | 分層厚卡紙景片（遠山兩層、騎樓、樹、側景），騎樓一樓為淺色牆面與鐵捲門 | —（待 G2 重驗） | Codex image_gen（第 1 次生成，未修改）；提示 review/G2/raw/stage_square_v02.prompt.txt；參考 review/G2a/S4.png＋review/G2/raw/stage_square.png | 使用者 ChatGPT 方案生成 | 無文字、無招牌、無人物；主光左上；舞台調色（遠景降彩、表演區只提亮淺色牆面與地面）在 tools/compose_stage.py，不改原檔；對照 review/G2/stage_wash_compare_v02.png | v02 |
| assets/parts/ale_v02/*.png（13 件）＋ parts.json | 分件紙偶部件（透明 PNG，kit 原尺度） | 阿樂叔叔 | head、torso、apron_skirt、upper_arm_r/l、forearm_r/l、hand_r/l、thigh_r/l、shin_r/l | — | chr-ale_kit_v02.png → tools/split_parts.py --layout v02 --alpha-floor 24 | 使用者 ChatGPT 方案生成 | 命名與左右正確（左／右＝角色自身） | v02 |
| assets/parts/ale_v02/rig/*.png（13 件＋head_worried）＋ assets/parts/ale_v02/rig.json | rig 部件（母版尺度） | 阿樂叔叔 | 同上＋困惑換片頭 | a2_c002（試作） | tools/rig_ale.py build：依正式母版關節距離逐件等比縮放（軀幹頸→腰帶 360 px＝肩到臀約 2.3 頭高；圍裙下襬口袋帶 ×1.2、口袋以下素色帶 ×2.6 加長到大腿中段）；重做 11 px 白色紙芯邊；腕部空白舌片補膚色；軀幹腰帶以下改由圍裙下襬蓋住（只留蝴蝶結垂帶） | 使用者 ChatGPT 方案生成 | 組裝 vs 母版 IoU 0.867；逐件外輪廓平均誤差 4–26 px（母版尺度，頭高 258 px），見 review/G2/kit_ale_v02_assembly.json；圍裙下襬比母版長（刻意，依第 1 輪美術總監意見） | v02 |

| assets/generated/chr-xiaoyu_master_v04.png | 角色母版（透明 PNG，1024×1496） | 小宇 | **正式母版（G2 退路 D-G2-06）**：外套同色相加深 L* 53.4→39（中位 #D95429→#AC2D03） | 全劇 | chr-xiaoyu_master_v02.png → tools/recolor_garment.py | 使用者 ChatGPT 方案生成＋程式調色 | G2 退路：投影 v2 外套 p10 3.03（contrast_v04.json） | v04 |
| assets/generated/chr-xiaoyu_pose-stepback-surprised_v04.png | 整張姿勢 | 小宇 | 側身退半步、雙手縮胸前（驚訝） | a2_c002 | chr-xiaoyu_pose-stepback-surprised_v03.png → tools/recolor_garment.py | 同上 | 同上 | v04 |
| assets/generated/chr-xiaoqing_master_v04.png | 角色母版（透明 PNG，1024×1536） | 小晴 | **正式母版（D-G2-06）**：吊帶褲同色相加深 L* 43.2→37（中位 #326F6F→#216060） | 全劇 | chr-xiaoqing_master_v02.png → tools/recolor_garment.py | 同上 | 投影 v2 吊帶褲 p10 3.10 | v04 |
| assets/generated/chr-xiaoqing_pose-reach-worried_v04.png | 整張姿勢 | 小晴 | 轉身伸手指向手腕的線（擔心） | a2_c002 | chr-xiaoqing_pose-reach-worried_v03.png → tools/recolor_garment.py | 同上 | 同上 | v04 |
| assets/generated/bg-square-{sky,mountains,backrow,arcade,trees,planters}_v03.png | 分層景片（透明 PNG） | 廣場 | 天空、遠山、後排建築、前排騎樓立面（中間開口）、行道樹、花台 | a2（G2 試作） | Codex image_gen（G2 第 3 輪） | 使用者 ChatGPT 方案生成 | 景片本身可用；v03 的黑色局部背板已撤回 | v03 |

## 舊版本（第 1 輪，保留不覆寫；不再使用）

| 檔名 | 類型 | 角色／場景 | 部件／表情 | 使用 cue | 來源／生成參考 | 授權 | 檢視結果 | 版本 |
|---|---|---|---|---|---|---|---|---|
| assets/generated/chr-xiaoqing_master_v01.png | 角色母版（透明 PNG，1024×1536） | 小晴 | 全身母版（3/4 正面站姿、中性微笑、平光無影） | —（被 v02 取代） | Codex image_gen；原檔 review/G2/raw/master_xiaoqing.png（第 2 次生成，未修改）；提示 review/G2/raw/master_xiaoqing.prompt.txt；參考 review/G2a/S4.png | 使用者 ChatGPT 方案生成 | 4.45 頭身；G2 第 1 輪：吊帶褲右側烘焙暗面（第 4 條）；外圍 alpha<24 淡霧 | v01 |
| assets/generated/chr-xiaoyu_master_v01.png | 角色母版（透明 PNG，1024×1496） | 小宇 | 全身母版 | —（被 v02 取代） | review/G2/raw/master_xiaoyu.png → fix_proportion ×0.869 → deepen_color 外套明度 ×0.82 | 使用者 ChatGPT 方案生成 | G2 第 1 輪：外套壓暗成磚紅（#B23E19，第 5 條退回）、短褲與腿部烘焙暗面 | v01 |
| assets/generated/chr-ale_master_v01.png | 角色母版（透明 PNG，1024×1656） | 阿樂叔叔 | 全身母版 | —（被 v02 取代） | review/G2/raw/master_ale.png（第 2 次生成）→ tools/fix_proportion.py ×1.250（5.68→6.15 頭身） | 使用者 ChatGPT 方案生成 | 6.15 頭身；G2 第 1 輪：圍裙斜向暗面、褲管暗褶（第 4 條） | v01 |
| assets/generated/bg-square_v01.png | 景板（PNG，1672×941） | 廣場 | 舞台景板 | —（被 v02 取代） | review/G2/raw/stage_square.png（第 1 次生成，未修改） | 使用者 ChatGPT 方案生成 | G2 第 1 輪：分層與卡紙側邊不足、騎樓暗門洞讓角色融入背景（第 6、10、18 條） | v01 |
| assets/parts/ale/*.png（12 件）＋ parts.json | 分件紙偶部件 | 阿樂叔叔 | 12 件（無圍裙下襬件） | —（被 ale_v02 取代） | review/G2/raw/kit_ale.png → tools/split_parts.py | 使用者 ChatGPT 方案生成 | 部件比例與母版不一致（粗估 4.3 頭身） | v01 |

## 配樂與音效（G3，自製，2026-10-21 第 2 天約 03:30）

重建方式：`caffeinate -i tools/.venv/bin/python tools/music/build_all.py`（譜：tools/music/compose.py；音效：tools/music/sfx.py；量測：review/G3/music_metrics.json；說明：review/G3/music.md；圖：review/G3/music_waveforms.png）。格式為 48 kHz／16-bit PCM，配樂立體聲、音效單聲道。聽感全部未驗證，要等許老師聽過。

| 檔名 | 類型 | 角色／場景 | 部件 | 使用 cue | 來源 | 授權 | 檢視結果 | 版本 |
|---|---|---|---|---|---|---|---|---|
| audio/music/music_opening_v01.wav | 配樂（一次播完 15.0 s） | 開幕：署名卡→布幕→景片 | M1 開場版 | a0_c001／G4 開幕 | 自製（程式作曲）＋FluidR3_GM 音色庫（MIT） | 原創；音色庫 MIT（audio/LICENSES/FluidR3_GM_copyright.txt） | −20.0 LUFS、真峰值 −7.1 dBTP；同步點 1.0／3.0／3.0–7.5／11.0 s；聽感未驗證 | v01 |
| audio/music/music_town_v01.wav | 配樂（無縫循環 30.0 s） | 小燈鎮 | M1 底樂 | 開幕後、a2_c001 | 自製（程式作曲）＋FluidR3_GM 音色庫（MIT） | 同上 | −24.0 LUFS、−10.5 dBTP；接縫樣本差 36 LSB；聽感未驗證 | v01 |
| audio/music/music_m4_strings_v01.wav | 配樂（一次播完 46.0 s） | 燈籠店 | M4 操偶線動機主版 | a2_c002 | 自製（程式作曲）＋FluidR3_GM 音色庫（MIT） | 同上 | −24.0 LUFS、−10.4 dBTP；100 ms 內最大跳升 4.6 dB；無驚嚇音、無低音不協和團塊；聽感未驗證 | v01 |
| audio/music/music_m4_light_v01.wav | 配樂（無縫循環 32.0 s） | 燈籠店 | M4 很輕版 | a2_c004、停格 | 自製（程式作曲）＋FluidR3_GM 音色庫（MIT） | 同上 | −27.0 LUFS、−12.9 dBTP；接縫樣本差 6 LSB；聽感未驗證 | v01 |
| audio/music/music_closing_v01.wav | 配樂（一次播完 10.0 s） | 閉幕：布幕合攏→署名卡 | M1 閉幕版 | G4 結尾、a8_c002 | 自製（程式作曲）＋FluidR3_GM 音色庫（MIT） | 同上 | −20.0 LUFS、−5.8 dBTP；署名卡進入 2.0 s；聽感未驗證 | v01 |
| audio/music/drafts/music_m1_bows_v01.wav | 配樂草稿（20.0 s） | 謝幕 | M1 謝幕版 | 未對 cue（a8） | 自製（程式作曲）＋FluidR3_GM 音色庫（MIT） | 同上 | 草稿；−20.0 LUFS；不會打包進演出 | v01 |
| audio/music/drafts/music_m2_zhezhe_v01.wav | 配樂草稿（9.5 s） | 折折 | M2 | 未對 cue | 自製（程式作曲）＋FluidR3_GM 音色庫（MIT） | 同上 | 草稿；−24.0 LUFS | v01 |
| audio/music/drafts/music_m3_shiny_v01.wav | 配樂草稿（14.0 s） | 閃亮盒子 | M3（不恐怖、無低頻） | 未對 cue | 自製（程式作曲）＋FluidR3_GM 音色庫（MIT） | 同上 | 草稿；−24.0 LUFS | v01 |
| audio/music/drafts/music_m5_road_v01.wav | 配樂草稿（14.0 s） | 紙上的路 | M5（無時鐘滴答、不像警報） | 未對 cue | 自製（程式作曲）＋FluidR3_GM 音色庫（MIT） | 同上 | 草稿；−24.0 LUFS | v01 |
| audio/music/drafts/music_m6_courage_v01.wav | 配樂草稿（16.0 s） | 拒絕、找大人 | M6 | 未對 cue | 自製（程式作曲）＋FluidR3_GM 音色庫（MIT） | 同上 | 草稿；−24.0 LUFS | v01 |
| audio/music/drafts/music_m7_recovery_v01.wav | 配樂草稿（20.0 s） | 醫院走廊、四季 | M7 | 未對 cue | 自製（程式作曲）＋FluidR3_GM 音色庫（MIT） | 同上 | 草稿；−24.0 LUFS | v01 |
| audio/sfx/sfx_curtain_open_v01.wav | 音效（2.30 s） | 布幕 | S1 布幕開 | G4 開幕、a0_c001 | 自製（程式合成） | 原創 | 峰值 −9.0 dBFS、−9.0 dBTP；起音 247 ms；聽感未驗證 | v01 |
| audio/sfx/sfx_curtain_close_v01.wav | 音效（2.30 s） | 布幕 | S1 布幕合 | G4 結尾、a8_c002 | 自製（程式合成） | 原創 | 峰值 −8.2 dBFS；起音 240 ms；聽感未驗證 | v01 |
| audio/sfx/sfx_paper_rustle_v01.wav | 音效（1.30 s） | 通用 | S1 紙張摩擦 | 通用 | 自製（程式合成） | 原創 | 峰值 −8.1 dBFS；聽感未驗證 | v01 |
| audio/sfx/sfx_string_drop_v01.wav | 音效（1.00 s） | 燈籠店 | 紙繩落下＋紙環輕扣（扣上點 0.50 s） | a2_c002 | 自製（程式合成） | 原創 | 峰值 −8.0 dBFS；聽感未驗證 | v01 |
| audio/sfx/sfx_string_taut_v01.wav | 音效（0.75 s） | 燈籠店 | 紙繩繃緊（不陰森） | a2_c002、a2_c008 | 自製（程式合成） | 原創 | 峰值 −8.0 dBFS；無低頻長音；聽感未驗證 | v01 |
| audio/sfx/sfx_lamp_on_v01.wav | 音效（3.40 s） | 台口八盞燈 | S5 點燈輕鈴 | 各題點燈 cue | 自製（程式合成） | 原創 | 峰值 −12.2 dBFS；起音 6.9 ms；聽感未驗證 | v01 |
| audio/sfx/sfx_stamp_v01.wav | 音效（0.75 s） | 題卡 | S4「正解」紙印章 | 各題揭答 cue | 自製（程式合成） | 原創 | 峰值 −8.0 dBFS；起音 7.1 ms；聽感未驗證 | v01 |
| audio/sfx/sfx_fold_v01.wav | 音效（0.95 s） | 折折 | S2 摺紙 | a0_c002 等 | 自製（程式合成） | 原創 | 峰值 −8.0 dBFS；聽感未驗證 | v01 |
| audio/sfx/sfx_card_in_v01.wav | 音效（1.35 s） | 題卡 | 題卡摺開送上 | 各題出題 cue | 自製（程式合成） | 原創 | 峰值 −8.0 dBFS；聽感未驗證 | v01 |
| audio/sfx/sfx_quiet_fold_v01.wav | 音效（2.80 s） | 折折 | S3 收摺音效（收聲訊號，加做） | 題卡模式開頭、教師插話點 | 自製（程式合成） | 原創 | 峰值 −11.4 dBFS；聽感未驗證 | v01 |

## 配音（正式：ElevenLabs v04，2026-10-21 13:4x 起；使用者決定 DECISIONS.md D-G3-07）
- **正式檔**：audio/vo/vo_<台詞編號>_v04.wav（201 句）＋audio/lipsync/<台詞編號>_v04.json；來源 audio/vo_el/vo_<id>_el01.wav（tools/vo_el_prod.py 合成＋自動檢查）→ tools/vo_el_promote.py 複製升版。逐句來源、sha1、自動檢查狀態、request_id 見 `audio/vo/promoted_el.json`；聲線、模型、seed、逐次計費見 `audio/vo_el/build_report_el.json`、`audio/vo_el/FILES.md`、`audio/vo_el/ledger.json`；人工指定採用的句子記在 build_report_el.json 的 manual_pick。
- **服務與聲線**：ElevenLabs eleven_v3，全部是聲線庫聲線（旁白 Door Chow、折折 Chloe、小晴 Tiffy、小宇 Vivian、阿樂叔叔 Kuo Yu、品安 Yui、葉護理師 Devon、林老師 Jui、陳伯伯 Neil Chuang、邀請者 Chihiro Yoko、執勤人員 Angel；voice_id 見 audio/vo/casting.json 的 official_engine）。
- **授權**：Starter 付費方案（2026-10-21 06:30 起），官方說明付費方案含商用授權（Beta 服務除外；eleven_v3 不是 Beta），聲線庫聲線附免費商用授權。ElevenLabs 使用政策「Use by and for Minors」要求兒童對象的產品取得書面核准：**2026-10-21 已取得 ElevenLabs 書面回覆**（教育用途、有適當監督時允許；學生用專案優先用聲線庫聲線），本專案三項條件都符合，原文與對照見 review/G3/el/elevenlabs_reply_20261021.md；原始郵件由使用者保存。證據：review/G3/el/license_evidence.md。
- **edge-tts**：不再用於演出。舊 v01–v03 檔移到 audio/_archive_edge/（只封存、不打包）；下方「配音（G3 選角提案＋G4 代表鏡頭正式台詞）」與兩輪修正紀錄是歷史紀錄。

## 配音（歷史：edge-tts 版，已封存；G3 選角提案＋G4 代表鏡頭正式台詞，2026-10-21 配音代理）

- 產生：`tools/vo_build.py --set g4`（讀 `audio/vo/casting.json`、`audio/vo/pronounce.json`、`script/劇本_v03.md`）；字幕一律用劇本原文，替身字只送進合成器（本批只有 a2_c004_01 的「阿樂」→「阿勒」）。母帶：頭 120 ms／尾 250 ms 靜音、−18 LUFS（ffmpeg loudnorm 兩段式；短句與 loudnorm 轉動態模式時改用量測值線性增益）、真峰值 ≤ −1.5 dBTP（4 倍超取樣限制器）、48 kHz／單聲道／16-bit PCM。選角理由與量測：`review/G3/casting.md`。
- **授權（edge-tts）**：edge-tts 7.3.1 是社群開發的非官方工具，呼叫 Edge 線上朗讀服務，微軟條款沒有明確授權這種用途。v1.2 第 20.2 節只作暫用、不放進正式交付包；v1.3 第 6 節允許在記錄風險下使用。正式交付前建議以 Azure AI Speech 同名聲線一鍵重建（`tools/vo_build.py --all --service azure`，需使用者金鑰；後端已寫好未實測），或由主線決定。
- ElevenLabs（G3 修正第 2 輪更正；**13:4x 起已改為正式配音**，本條保留當時紀錄）：當時正式配音沒有使用任何 ElevenLabs 輸出（G4 計費 0）。**方案與授權**：2026-10-21 06:27 以前是免費方案——API 不能用聲線庫（含台灣）聲線與聲線設計；**免費方案的產出只限非商業用途，公開時必須標註 elevenlabs.io，沒有商用授權**。06:30 使用者升級 Starter 付費方案（含商用授權，Beta 服務除外）。另受 ElevenLabs 使用政策「Use by and for Minors」：給 18 歲以下對象的產品須經 ElevenLabs 書面核准（review/G3/el/license_evidence.md），未取得前 ElevenLabs 輸出一律不進演出。**用量**：以 `audio/vo_el/ledger.json`（EL 全劇版，回應標頭 character-cost 逐筆累加、失敗呼叫不計）與 `audio/vo/elevenlabs_usage.jsonl`（全部呼叫）為準，本檔不再抄寫合計數字（參考：2026-10-21 13:10 ledger total_billed 6916、833 次呼叫）。G3 試音 283 字元在免費方案下產生（樣本 `review/G3/samples/A_*`、`B_*jessica*` 不是正式素材，受免費方案限制）。試作檔登記見本節「ElevenLabs 試作」。
- 聽感一律未驗證（Claude 聽不到聲音），第 3 天彩排確認。

| 檔名 | 類型 | 角色／場景 | 部件／表情 | 使用 cue | 來源／生成參考 | 授權 | 檢視結果 | 版本 |
|---|---|---|---|---|---|---|---|---|
| audio/vo/vo_a2_c001_01_v01.wav | 配音（3.52 s） | 小宇 | 「叔叔，你還好嗎？竹篾掉了。」 | a2_c001 | edge-tts zh-TW-HsiaoYuNeural，rate +12%、pitch +20Hz，句中停頓上限 550 ms | edge-tts 暫用（見本節授權說明） | 兩個轉寫模型只有同音字（竹篾→竹滅／逐滅，zhú miè）；−18.1 LUFS／−1.9 dBTP／0 削波；F0 中位 226 Hz；聽感未驗證 | v01 |
| audio/vo/vo_a2_c001_02_v01.wav | 配音（3.16 s） | 阿樂叔叔 | 「沒事、沒事，手滑了一下。」（受影響段） | a2_c001 | edge-tts zh-TW-YunJheNeural，rate −6%、pitch +0Hz，停頓上限 900 ms | edge-tts 暫用 | 轉寫一致；−18.2 LUFS／−1.9 dBTP／0 削波；3.23 字/秒；聽感未驗證 | v01 |
| audio/vo/vo_a2_c001_03_v01.wav | 配音（5.43 s） | 折折 | 「大家仔細看，叔叔的手上，是不是多了什麼？看到的舉手。」 | a2_c001 | edge-tts zh-TW-HsiaoYuNeural，rate +22%、pitch +60Hz，停頓上限 550 ms | edge-tts 暫用 | 轉寫一致；−17.9 LUFS／−1.9 dBTP／0 削波；F0 中位 279 Hz（全劇最高）；聽感未驗證 | v01 |
| audio/vo/vo_a2_c002_01_v01.wav | 配音（4.26 s） | 阿樂叔叔 | 「咦？我想揮手……手怎麼跑到旁邊去了？」（受影響段） | a2_c002 | edge-tts zh-TW-YunJheNeural，rate −6%、pitch +0Hz，停頓上限 900 ms | edge-tts 暫用 | 「咦」兩個模型都轉成「1」，F0 走勢與二聲「移」相同（review/G3/tone_check_yi.json），其餘一致；−18.0 LUFS／−1.6 dBTP／0 削波；聽感未驗證 | v01 |
| audio/vo/vo_a2_c002_02_v01.wav | 配音（1.72 s） | 小晴 | 「叔叔，小心！」 | a2_c002 | edge-tts zh-TW-HsiaoChenNeural，rate +0%、pitch +40Hz，停頓上限 550 ms | edge-tts 暫用 | 轉寫一致；−18.0 LUFS／−3.6 dBTP／0 削波；聽感未驗證 | v01 |
| audio/vo/vo_a2_c004_01_v01.wav | 配音（4.68 s） | 旁白 | 「阿樂叔叔身上這一條一條的線，叫做操偶線。」 | a2_c004 | edge-tts zh-TW-HsiaoChenNeural，rate −14%、pitch +0Hz；合成用「阿勒」 | edge-tts 暫用 | 轉寫「阿勒叔叔…操偶線」（同音，讀音 lè 一致）；−17.8 LUFS／−3.0 dBTP／0 削波；4.18 字/秒；聽感未驗證 | v01 |
| audio/vo/vo_a2_c004_02_v01.wav | 配音（11.57 s） | 旁白 | 必要旁白一（合成文字與劇本逐字相同） | a2_c004 | edge-tts zh-TW-HsiaoChenNeural，rate −8%、pitch +0Hz，三句分開合成、句間停頓 1.3 秒 | edge-tts 暫用 | turbo 轉寫與劇本一致（同音「現世」），small 有轉寫誤差；−18.0 LUFS／−3.4 dBTP／0 削波；3.39 字/秒；聽感未驗證 | v01 |
| audio/lipsync/a2_c001_01_v01.json … a2_c004_02_v01.json（7 檔） | 對嘴資料（{"fps":12,"frames":[0–3]}） | 同上 7 句 | 0 閉、1 半開、2 大開、3 圓唇（依 app/src/stage/perform.ts mouthOpen()） | a2_c001、a2_c002、a2_c004 | 由正式 WAV 自動產生（tools/vo_lib.py lipsync()：帶通 RMS 包絡＋遲滯門檻＋90 ms 最短停留＋每秒 12 格） | 原創（程式產生） | 格數＝ceil(秒數×12)；首尾靜音為 0；review/G3/vo_waveforms_g4.png 疊圖檢視 | v01 |
| audio/vo/timings.json | 長度表 | — | 每句 seconds、speech_start、speech_end、file、lipsync | a2_c001、a2_c002、a2_c004 | tools/vo_build.py 自動產生 | 原創（程式產生） | 與 WAV 實際長度一致 | v01 |

### G3 修正第 1 輪（2026-10-21，聲音代理；v01 保留不覆寫，tools/pack.mjs 自動取最新版）

| 檔案 | 類型 | 角色 | 內容 | 用途 | 製作 | 授權 | 檢查 | 版本 |
|---|---|---|---|---|---|---|---|---|
| audio/vo/vo_a2_c001_01_v02.wav | 配音（3.52 s） | 小宇 | 「叔叔，你還好嗎？竹篾掉了。」 | a2_c001 | edge-tts zh-TW-HsiaoYuNeural，rate +12%、pitch +20Hz；10 ms 淡入／20 ms 淡出剪接、去孤立爆音 | edge-tts 暫用（見本節授權說明） | 兩個模型都轉寫一致或只有同音字（small：叔叔你還好嗎逐滅掉了；large-v3-turbo：叔叔你還好嗎竹滅掉了）；-18.1 LUFS／-1.9 dBTP／0 削波；F0 中位 225.8 Hz；停頓突波 0；聽感未驗證 | v02 |
| audio/vo/vo_a2_c001_02_v02.wav | 配音（3.16 s） | 阿樂叔叔 | 「沒事、沒事，手滑了一下。」 | a2_c001 | edge-tts zh-TW-YunJheNeural，rate -6%、pitch +0Hz；10 ms 淡入／20 ms 淡出剪接、去孤立爆音 | edge-tts 暫用（見本節授權說明） | 兩個模型都轉寫一致或只有同音字（small：沒事沒事手滑了一下；large-v3-turbo：沒事沒事手滑了一下）；-18.2 LUFS／-1.9 dBTP／0 削波；F0 中位 94.3 Hz；停頓突波 0；聽感未驗證 | v02 |
| audio/vo/vo_a2_c001_03_v02.wav | 配音（5.42 s） | 折折 | 「大家仔細看，叔叔的手上，是不是多了什麼？看到的舉手。」 | a2_c001 | edge-tts zh-TW-HsiaoYuNeural，rate +22%、pitch +90Hz；10 ms 淡入／20 ms 淡出剪接、去孤立爆音 | edge-tts 暫用（見本節授權說明） | 兩個模型都轉寫一致或只有同音字（small：大家仔細看叔叔的手上是不是多了什麼看到的舉手；large-v3-turbo：大家仔細看叔叔的手上是不是多了什麼看到的舉手）；-17.9 LUFS／-1.9 dBTP／0 削波；F0 中位 296.0 Hz；停頓突波 0；聽感未驗證 | v02 |
| audio/vo/vo_a2_c002_01_v02.wav | 配音（4.89 s） | 阿樂叔叔 | 「咦？我想揮手……手怎麼跑到旁邊去了？」 | a2_c002 | edge-tts zh-TW-YunJheNeural，rate -6%（分段 -8%／-18%／-18%）、pitch +0Hz；分三段、停頓 350／550 ms（[[break]]）、「咦？」PSOLA 二聲上揚（終點／起點 1.24）；10 ms 淡入／20 ms 淡出剪接、去孤立爆音 | edge-tts 暫用（見本節授權說明） | 兩個模型都轉寫一致或只有同音字（small：姨我想揮手手怎麼跑到旁邊去了；large-v3-turbo：咦我想揮手手怎麼跑到旁邊去了）；-18.0 LUFS／-1.9 dBTP／0 削波；F0 中位 109.9 Hz；停頓突波 0；聽感未驗證 | v02 |
| audio/vo/vo_a2_c002_02_v02.wav | 配音（1.72 s） | 小晴 | 「叔叔，小心！」 | a2_c002 | edge-tts zh-TW-HsiaoChenNeural，rate +0%、pitch +56Hz；10 ms 淡入／20 ms 淡出剪接、去孤立爆音 | edge-tts 暫用（見本節授權說明） | 兩個模型都轉寫一致或只有同音字（small：叔叔小心；large-v3-turbo：叔叔小心）；-18.0 LUFS／-3.7 dBTP／0 削波；F0 中位 393.6 Hz；停頓突波 0；聽感未驗證 | v02 |
| audio/vo/vo_a2_c004_01_v02.wav | 配音（4.69 s） | 旁白 | 「阿樂叔叔身上這一條一條的線，叫做操偶線。」 | a2_c004 | edge-tts zh-TW-HsiaoChenNeural，rate -14%、pitch -10Hz；10 ms 淡入／20 ms 淡出剪接、去孤立爆音 | edge-tts 暫用（見本節授權說明） | 兩個模型都轉寫一致或只有同音字（small：阿勒叔叔身上這一條一條的線叫做操偶線；large-v3-turbo：阿勒叔叔身上這一條一條的線叫做操偶線）；-17.8 LUFS／-2.9 dBTP／0 削波；F0 中位 197.4 Hz；停頓突波 0；聽感未驗證 | v02 |
| audio/vo/vo_a2_c004_02_v02.wav | 配音（11.60 s） | 旁白 | 「這些線是故事的比喻。毒品可能讓人的頭腦和身體受到影響，不聽使喚。人不會真的變成喪屍。」 | a2_c004 | edge-tts zh-TW-HsiaoChenNeural，rate -8%、pitch -10Hz；三句分開合成、句間 1.3 秒；10 ms 淡入／20 ms 淡出剪接、去孤立爆音 | edge-tts 暫用（見本節授權說明） | 只有單一模型出現差異（多半是轉寫誤差）（small：這些現實故事的比喻毒品可能讓人的頭腦和身體受到影響不停使喚人不會真的變成喪屍；large-v3-turbo：這些現世故事的比喻毒品可能讓人的頭腦和身體受到影響不聽使喚人不會真的變成喪屍）；-18.0 LUFS／-3.4 dBTP／0 削波；F0 中位 185.5 Hz；停頓突波 0；聽感未驗證 | v02 |
| audio/music/music_m4_light_v02.wav | 配樂（無縫循環 32.0 s） | 燈籠店 | M4 很輕版（同譜，響度 −27 → −24 LUFS） | a2_c004 | 自製（程式作曲）＋FluidR3_GM 音色庫（MIT）；tools/music/build_all.py | 原創 | -24.0 LUFS、-9.9 dBTP；理由見 review/G3/mix_r1.json；聽感未驗證 | v02 |

### G3 修正第 2 輪（2026-10-21 約 09:00–10:00，聲音代理；新版號 v03，不覆寫 v01／v02）

- 參數：`audio/vo/casting.json` v03（葉護理師 −20%／+55Hz，a2_c012_03 −28%、a2_c012_05／a5_c008_01 −25%；小晴三句「品安」分段＋PSOLA 半三聲）；`audio/vo/pronounce.json` 加「119」→「一一九」。`defaults.version` 改 v03，之後重建不會覆寫已採用的 v02。
- 這 11 句不在 G4 代表鏡頭內（G4 的 7 句 v02 不變、未重建）；`tools/pack.mjs` 會依 cue 另成資料包，G5 直接引用。證據：`review/G3/metrics.json` 的 round2、`review/G3/tone_check_pinan_r2.json／.png`、`review/G3/vo_waveforms_r2.png`。
- `review/G3/r2/*.wav` 是驗收用的試音與對照檔（含「平安」對照、修正前整句合成），**不是正式素材**。

| 檔案 | 類型 | 角色 | 內容 | 用途 | 製作 | 授權 | 檢查 | 版本 |
|---|---|---|---|---|---|---|---|---|
| audio/vo/vo_a1_c001_01_v03.wav | 配音（2.81 s） | 小晴 | 「品安！你的燈籠好漂亮。」 | a1_c001（G5） | edge-tts zh-TW-HsiaoChenNeural，rate +0%、pitch +56Hz；「品安」單獨一段合成＋PSOLA 半三聲（品最低約 203 Hz，比「平安」對照低約 5.1–5.6 半音）；10 ms 淡入／20 ms 淡出剪接、去孤立爆音 | edge-tts 暫用（見本節授權說明） | 兩個模型（正式提示）都把人名轉成「平安」（語言模型偏好；通過條件改用 F0 對照，見 tone_check_pinan_r2.json）（small：平安你的燈籠好漂亮；large-v3-turbo：平安你的燈籠好漂亮）；-18.0 LUFS／-3.9 dBTP／0 削波；淨語速 4.81（驗收者算法 4.86）字/秒；F0 中位 275.3 Hz；停頓突波 0；聽感未驗證 | v03 |
| audio/vo/vo_a1_c004_05_v03.wav | 配音（3.46 s） | 小晴 | 「品安，快來，我們去跟阿樂叔叔說。」 | a1_c004（G5） | edge-tts zh-TW-HsiaoChenNeural，rate +0%、pitch +56Hz；「品安」單獨一段合成＋PSOLA 半三聲（品最低約 203 Hz，比「平安」對照低約 5.1–5.6 半音）；10 ms 淡入／20 ms 淡出剪接、去孤立爆音 | edge-tts 暫用（見本節授權說明） | 兩個模型（正式提示）都把人名轉成「平安」（語言模型偏好；通過條件改用 F0 對照，見 tone_check_pinan_r2.json）（small：平安快來我們去跟阿樂叔叔說；large-v3-turbo：平安快來我們去跟阿樂叔叔說）；-18.0 LUFS／-4.5 dBTP／0 削波；淨語速 4.21（驗收者算法 4.58）字/秒；F0 中位 318.2 Hz；停頓突波 0；聽感未驗證 | v03 |
| audio/vo/vo_a2_c012_01_v03.wav | 配音（5.73 s） | 葉護理師 | 「阿樂，你哪裡不舒服？我陪你去看醫生，好嗎？」 | a2_c012（G5） | edge-tts zh-TW-YunJheNeural，rate -20%、pitch +55Hz；10 ms 淡入／20 ms 淡出剪接、去孤立爆音 | edge-tts 暫用（見本節授權說明） | 兩個模型都轉寫一致或只有同音字（small：阿樂你哪裡不舒服我陪你去看醫生好嗎；large-v3-turbo：阿樂你哪裡不舒服我陪你去看醫生好嗎）；-18.0 LUFS／-1.9 dBTP／0 削波；淨語速 4.45（驗收者算法 4.27）字/秒；F0 中位 160.8 Hz；停頓突波 0；聽感未驗證 | v03 |
| audio/vo/vo_a2_c012_03_v03.wav | 配音（3.98 s） | 葉護理師 | 「你家人的電話沒人接，我晚一點再打。」 | a2_c012（G5） | edge-tts zh-TW-YunJheNeural，rate -28%、pitch +55Hz；10 ms 淡入／20 ms 淡出剪接、去孤立爆音 | edge-tts 暫用（見本節授權說明） | 兩個模型都轉寫一致或只有同音字（small：你家人的電話沒人接我晚一點再打；large-v3-turbo：你家人的電話沒人接我晚一點再打）；-17.8 LUFS／-1.9 dBTP／0 削波；淨語速 4.66（驗收者算法 4.81）字/秒；F0 中位 161.5 Hz；停頓突波 0；聽感未驗證 | v03 |
| audio/vo/vo_a2_c012_05_v03.wav | 配音（4.13 s） | 葉護理師 | 「謝謝你們告訴我，我會請警察去看看。」 | a2_c012（G5） | edge-tts zh-TW-YunJheNeural，rate -25%、pitch +55Hz；10 ms 淡入／20 ms 淡出剪接、去孤立爆音 | edge-tts 暫用（見本節授權說明） | 兩個模型都轉寫一致或只有同音字（small：謝謝你們告訴我我會請警察去看看；large-v3-turbo：謝謝你們告訴我我會請警察去看看）；-18.0 LUFS／-2.3 dBTP／0 削波；淨語速 4.57（驗收者算法 4.67）字/秒；F0 中位 150.4 Hz；停頓突波 0；聽感未驗證 | v03 |
| audio/vo/vo_a2_c013_03_v03.wav | 配音（4.86 s） | 葉護理師 | 「這幾天先不要開車。我會一直打給你的家人。」 | a2_c013（G5） | edge-tts zh-TW-YunJheNeural，rate -20%、pitch +55Hz；10 ms 淡入／20 ms 淡出剪接、去孤立爆音 | edge-tts 暫用（見本節授權說明） | 兩個模型都轉寫一致或只有同音字（small：這幾天先不要開車我會一直打給你的家人；large-v3-turbo：這幾天先不要開車我會一直打給你的家人）；-18.1 LUFS／-2.3 dBTP／0 削波；淨語速 4.72（驗收者算法 4.84）字/秒；F0 中位 160.0 Hz；停頓突波 0；聽感未驗證 | v03 |
| audio/vo/vo_a5_c008_01_v03.wav | 配音（5.51 s） | 葉護理師 | 「阿樂叔叔現在有醫生和護理師照顧，他的家人也來了。」 | a5_c008（G5） | edge-tts zh-TW-YunJheNeural，rate -25%、pitch +55Hz；10 ms 淡入／20 ms 淡出剪接、去孤立爆音 | edge-tts 暫用（見本節授權說明） | 兩個模型都轉寫一致或只有同音字（small：阿樂叔叔現在有一生和護理師照顧他的家人也來了；large-v3-turbo：阿勒叔叔現在有醫生和護理師照顧他的家人也來了）；-17.8 LUFS／-1.9 dBTP／0 削波；淨語速 4.64（驗收者算法 4.58）字/秒；F0 中位 181.9 Hz；停頓突波 0；聽感未驗證 | v03 |
| audio/vo/vo_a5_c008_03_v03.wav | 配音（5.31 s） | 葉護理師 | 「不是喔。你們找大人、打 119，是在幫他。」 | a5_c008（G5） | edge-tts zh-TW-YunJheNeural，rate -20%、pitch +55Hz；10 ms 淡入／20 ms 淡出剪接、去孤立爆音 | edge-tts 暫用（見本節授權說明） | 兩個模型都把句末「喔」寫成「哦」（同一個語氣詞的不同寫法，第 1 輪 r1 版也一樣）；small 把「一一九」轉成「依舊」，turbo 轉成「119」（small：不是你們找大人打依舊是在幫他；large-v3-turbo：不是哦你們找大人打119是在幫他）；-17.9 LUFS／-1.9 dBTP／0 削波；淨語速 4.64（驗收者算法 3.55）字/秒；F0 中位 150.8 Hz；停頓突波 0；聽感未驗證 | v03 |
| audio/vo/vo_a5_c008_05_v03.wav | 配音（6.13 s） | 葉護理師 | 「他需要治療，也需要時間。大家會陪著他，慢慢來。」 | a5_c008（G5） | edge-tts zh-TW-YunJheNeural，rate -20%、pitch +55Hz；10 ms 淡入／20 ms 淡出剪接、去孤立爆音 | edge-tts 暫用（見本節授權說明） | 兩個模型都轉寫一致或只有同音字（small：它需要治療也需要時間大家會陪著它慢慢來；large-v3-turbo：他需要治療也需要時間大家會陪著他慢慢來）；-17.9 LUFS／-2.3 dBTP／0 削波；淨語速 4.34（驗收者算法 4.28）字/秒；F0 中位 172.6 Hz；停頓突波 0；聽感未驗證 | v03 |
| audio/vo/vo_a6_c006_01_v03.wav | 配音（3.54 s） | 小晴 | 「品安，我在乎你，我們一起找人幫忙。」 | a6_c006（G5） | edge-tts zh-TW-HsiaoChenNeural，rate +0%、pitch +56Hz；「品安」單獨一段合成＋PSOLA 半三聲（品最低約 203 Hz，比「平安」對照低約 5.1–5.6 半音）；10 ms 淡入／20 ms 淡出剪接、去孤立爆音 | edge-tts 暫用（見本節授權說明） | 兩個模型（正式提示）都把人名轉成「平安」（語言模型偏好；通過條件改用 F0 對照，見 tone_check_pinan_r2.json）（small：平安我在Honey我們一起找人幫忙；large-v3-turbo：平安我在呼你我們一起找人幫忙）；-18.1 LUFS／-3.0 dBTP／0 削波；淨語速 4.42（驗收者算法 5.2）字/秒；F0 中位 263.4 Hz；停頓突波 0；聽感未驗證 | v03 |
| audio/vo/vo_a6_c006_06_v03.wav | 配音（3.19 s） | 葉護理師 | 「說出來，就是在保護自己。」 | a6_c006（G5） | edge-tts zh-TW-YunJheNeural，rate -20%、pitch +55Hz；10 ms 淡入／20 ms 淡出剪接、去孤立爆音 | edge-tts 暫用（見本節授權說明） | 兩個模型都轉寫一致或只有同音字（small：說出來就是在保護自己；large-v3-turbo：說出來就是在保護自己）；-18.1 LUFS／-1.9 dBTP／0 削波；淨語速 4.02（驗收者算法 4.05）字/秒；F0 中位 156.3 Hz；停頓突波 0；聽感未驗證 | v03 |
| audio/lipsync/a1_c001_01_v03.json … a6_c006_06_v03.json（11 檔） | 對嘴資料 | 同上 11 句 | 0 閉、1 半開、2 大開、3 圓唇 | 同上 | 由正式 WAV 自動產生（tools/vo_lib.py lipsync()） | 原創（程式產生） | 格數＝ceil(秒數×12)；review/G3/vo_waveforms_r2.png 疊圖 | v03 |
| audio/vo/timings.json、build_report.json | 長度表、逐句量測 | — | 新增上列 11 句；speech_segments 修正句尾假段落（tools/vo_lib.py speech_segments：句尾衰減不再切出 10 ms 的段落） | 引擎、驗收 | tools/vo_build.py 自動產生 | 原創（程式產生） | 與 WAV 實際長度一致 | — |

### ElevenLabs 全劇版：audio/vo_el/、audio/lipsync_el/（登記時間 2026-10-21 10:00；**13:4x 起升為正式 v04**，見本檔「配音（正式：ElevenLabs v04）」）

- **狀態**：全部是 ElevenLabs 全劇版試作（tools/vo_el_prod.py，主線工作流 wf_42597e72-70b，使用者 08:1x 指示「先做再說」）。〔13:4x 更新〕使用者決定全劇採用（D-G3-07），由 tools/vo_el_promote.py 複製成 audio/vo 的 v04 後打包；本資料夾仍是來源與工作檔，不直接打包。兒童用途書面核准待 ElevenLabs 回覆（license_evidence.md 第 5–8 節）。
- **授權**：這些檔在 Starter 付費方案下產生（06:30 升級；商用授權，Beta 服務除外）。免費方案（06:27 以前）的產出只限非商業用途、公開時須標註 elevenlabs.io，本節沒有免費方案的檔案；免費方案時期的 G3 試音另見本節上方 ElevenLabs 一條。
- **逐檔紀錄**以 `audio/vo_el/build_report_el.json`（每句 voice_id、模型、seed、request_id、計費、自動檢查結果）與 `audio/vo_el/ledger.json`（點數帳）為準；全部檔案清單見 `audio/vo_el/FILES.md`（自動產生，193 檔）；點數以 ledger.json 為準。`audio/vo_el/_attempts/`（每句最多 6 次嘗試的母帶）、`audio/vo_el/_raw/`（原始 mp3）、`audio/vo_el/casting/*.json`（角色設定）、`timings_el.json` 與 `*.lock` 都是工作檔，同樣不使用。

| 檔案 | 角色 | 台詞 | 聲線／模型 | request_id | 計費（字元） | 自動檢查 | 狀態 |
|---|---|---|---|---|---|---|---|
| audio/vo_el/vo_a0_c001_01_el01.wav；audio/lipsync_el/a0_c001_01_el01.json | 旁白 | 「這裡是小燈鎮。每年秋天，鎮上都會辦紙燈節。」 | Door Chow（qDeYqHQrKRH839xMU4nb）／eleven_v3 | hvfSMtjncxPgBbfqhS1t | 60 | fail | 已升正式 v04 |
| audio/vo_el/vo_a1_c005_02_el01.wav；audio/lipsync_el/a1_c005_02_el01.json | 旁白 | 「有人拿出包裝漂亮的電子煙，說「這個很安全」。可以相信嗎？」 | Door Chow（qDeYqHQrKRH839xMU4nb）／eleven_v3 | v2z0SQIFPCAuzp4WVUzH | 13 | pass | 已升正式 v04 |
| audio/vo_el/vo_a1_c005_03_el01.wav；audio/lipsync_el/a1_c005_03_el01.json | 旁白 | 「一，可以，包裝漂亮就很安全。」 | Door Chow（qDeYqHQrKRH839xMU4nb）／eleven_v3 | OcjGb8o9wipoSvW0P8Cc | 14 | pass | 已升正式 v04 |
| audio/vo_el/vo_a2_c012_01_el01.wav；audio/lipsync_el/a2_c012_01_el01.json | 葉護理師 | 「阿樂，你哪裡不舒服？我陪你去看醫生，好嗎？」 | Devon - Relaxed, Natural and Warm（qV41hPnIn6kbvO8hMtPG）／eleven_v3 | KxWQ3ErzEpVT9VcZRTOd | 20 | pass | 已升正式 v04 |
| audio/vo_el/vo_a3_c003_02_el01.wav；audio/lipsync_el/a3_c003_02_el01.json | 林老師 | 「謝謝你們告訴我。老師會請警衛伯伯和警察處理。」 | Jui - Calm, Warm & Pleasing（5ypmms5LDLZQ1fRMo16H）／eleven_v3 | OBNgJLH0THLHOykpcBMl | 10 | pass | 已升正式 v04 |
| audio/vo_el/vo_a3_c003_03_el01.wav；audio/lipsync_el/a3_c003_03_el01.json | 林老師 | 「你們沒有拿，還馬上來找我，做得很好。」 | Jui - Calm, Warm & Pleasing（5ypmms5LDLZQ1fRMo16H）／eleven_v3 | Usl7fHhhX8WWWIrcK5P7 | 9 | pass | 已升正式 v04 |
| audio/vo_el/vo_a3_c008_01_el01.wav；audio/lipsync_el/a3_c008_01_el01.json | 林老師 | 「今天紙燈節，學校提早放學。」 | Jui - Calm, Warm & Pleasing（5ypmms5LDLZQ1fRMo16H）／eleven_v3 | gcPfKHaqKtu5XwP4trN5 | 42 | pass | 已升正式 v04 |
| audio/vo_el/vo_a3_c008_02_el01.wav；audio/lipsync_el/a3_c008_02_el01.json | 林老師 | 「小晴、小宇，你們家長前幾天就拜託阿樂叔叔，開車來接你們去廣場。」 | Jui - Calm, Warm & Pleasing（5ypmms5LDLZQ1fRMo16H）／eleven_v3 | cWhkGzuHlV7fz9sIfU5f | 14 | pass | 已升正式 v04 |
| audio/vo_el/vo_a3_c008_04_el01.wav；audio/lipsync_el/a3_c008_04_el01.json | 林老師 | 「謝謝你告訴老師。老師先打電話給你們家人；如果叔叔先到，你們先待在校門裡面。」 | Jui - Calm, Warm & Pleasing（5ypmms5LDLZQ1fRMo16H）／eleven_v3 | vhvC8fWCcGLkHc52X3ge | 16 | pass | 已升正式 v04 |
| audio/vo_el/vo_a4_c012_04_el01.wav；audio/lipsync_el/a4_c012_04_el01.json | 林老師 | 「你們先待在校門裡面。老師繼續打給你們家人，也打給阿樂叔叔的家人。」 | Jui - Calm, Warm & Pleasing（5ypmms5LDLZQ1fRMo16H）／eleven_v3 | vmzXWjbypdWTtKRgjyhS | 14 | pass | 已升正式 v04 |
| audio/vo_el/vo_a5_c006_01_el01.wav；audio/lipsync_el/a5_c006_01_el01.json | 執勤人員 | 「119 您好，請問發生什麼事？在哪裡？」 | Angel - Narration（aQwAQvuS5kErJvZlR7wN）／eleven_v3 | qQN9srfagLXGSwlp0vRz | 27 | pass | 已升正式 v04 |

## G4 代表鏡頭美術（2026-10-21 第 2 天約 03:30–05:00，美術代理）

生成方式：`codex exec` 內建 image_gen（ChatGPT 方案，不用 API key），附 review/G2a/S4.png＋review/G2/stage_composite_v04.png 兩張參考圖；提示檔 review/G4/art/raw/<id>.prompt.txt、執行腳本 review/G4/art/raw/_run.sh、原檔與紀錄 review/G4/art/raw/<id>.png／.txt／.log。共生成 6 張，都是第 1 次生成成功；未採用 wk_back_v01（像 3D 室內渲染，不像剪紙）、wk_table_v01（看得到透視桌面）。後製腳本都在 review/G4/art/scripts/。投影模擬：review/G4/art/sim/（tools/projsim.py v2）。

| 檔名 | 類型 | 角色／場景 | 部件／表情 | 使用 cue | 來源／生成參考 | 授權 | 檢視結果 | 版本 |
|---|---|---|---|---|---|---|---|---|
| assets/generated/bg-workshop-back_v02.png → assets/final/bg-workshop-back_v02.jpg | 景片：後牆（不透明；生成 1536×1024 → 延伸成 2964×1415＝22×10.5 舞台單位） | 騎樓下燈籠工作室 | 淺暖米色灰泥＋淺木柱、上方兩層層架（未點亮紙燈籠、竹篾束、紙卷）、右側門洞（看到淡色騎樓） | a2_c001–a2_c004（a2 固定中景） | Codex image_gen（wk_back_v02）；extend_wall.py 只用同一張圖的灰泥、柱、樑、踢腳板鏡射拼貼延伸，柱子提亮 40% | 使用者 ChatGPT 方案生成 | 無文字、招牌、商標、紅十字；無外部陰影；投影 v2 下孩子軀幹高度背景亮度中位 0.586（p10 0.49，柱子造成） | v02 |
| assets/generated/bg-workshop-lanterns_v01.png → assets/final/bg-workshop-lanterns_v01.png | 景片：中景懸掛燈籠（透明，裁成 1536×414） | 同上 | 竹竿＋5 盞未點亮和紙燈籠（短繩） | a2_c001–a2_c004 | Codex image_gen（wk_lanterns_v01）；process_set.py 清 alpha、裁邊、顏色外擴 | 使用者 ChatGPT 方案生成 | 燈籠上沒有字或符號、不發光；建議只放畫面右半，阿樂上方留白給操偶線 | v01 |
| assets/generated/bg-workshop-table_v02.png → assets/final/bg-workshop-table_v02.png | 前景：工作台（透明，1479×791） | 同上 | 厚卡紙工作台（桌面切口看得到紙層、封閉前板），桌上竹篾、燈籠紙、小剪刀、燈籠骨架；右三分之一淨空 | a2_c001–a2_c008 | Codex image_gen（wk_table_v02，正立面）；process_set.py | 使用者 ChatGPT 方案生成 | 無文字；剪刀小、闔起、不特寫；擺在阿樂前面 z≈0.3（不是 fore 層） | v02 |
| assets/generated/bg-workshop-wing_v01.png → assets/final/bg-workshop-wing_v01.png | 前景：側翼竹束（透明，599×1536；右側用鏡射） | 同上 | 一束竹子＋腳邊撕紙屑 | a2_c001–a2_c004 | Codex image_gen（wk_wing_v01）；process_set.py | 使用者 ChatGPT 方案生成 | 無文字；只佔畫面左右邊緣 | v01 |
| assets/final/bg-workshop-floor_v01.jpg | 地板貼圖（1024×512，四方連續） | 同上 | 淺暖木板 | a2_c001–a2_c004 | 程式產生（make_textures.py） | 原創（程式產生） | 取代偏暗的程式地板；無字 | v01 |
| assets/final/tex-curtain-paper_v01.png | 布幕紙材貼圖（512×1024，左右連續） | 台口 | 酒紅和紙＋下緣滾邊與芥末黃紙條 | 片頭、片尾 | 程式產生（make_textures.py） | 原創（程式產生） | 無字、不烘焙光影 | v01 |
| assets/final/tex-titlecard-paper_v01.png | 署名卡底紙（1600×900） | 片頭／片尾 | 奶油色厚卡紙＋細框＋四角幾何剪紙花 | 片頭、片尾 | 程式產生（make_textures.py） | 原創（程式產生） | 圖裡沒有任何字，「許博明老師製作」由程式排字 | v01 |
| assets/final/chr-xiaoqing_pose-reach-worried_v04.png、chr-xiaoyu_pose-stepback-surprised_v04.png、chr-xiaoqing_master_v04.png、chr-xiaoyu_master_v04.png | 孩子採用圖（透明，裁邊＋16 px、顏色外擴） | 小晴、小宇 | a2_c002 伸手提醒／擔心後退；站姿母版 | a2_c002、a2_c004 | assets/generated 同名 v04（G2 退路正式版）；process_kids.py（裁切位移記在 review/G4/art/kids_crop.json） | 使用者 ChatGPT 方案生成 | 半透明白邊 0 px、零碎雜點 0；圖像內容未改 | v04 |
| assets/final/chr-xiaoqing_pose-reach-worried-head_v04.png／-body_v04.png、chr-xiaoyu_pose-stepback-surprised-head_v04.png／-body_v04.png | 孩子頭層＋身體層（透明） | 小晴、小宇 | 頭可繞頸部樞紐轉 ±2.5°（G2 問題 4） | a2_c002、a2_c004 | split_kid_heads.py（身體層的頭部範圍是模糊底色、朝外 12 px 挖空） | 使用者 ChatGPT 方案生成（原圖） | 0° 疊回與原圖只差 ≤12 px 邊緣；±2.5° 無重影（review/G4/art/kid_heads_check.png） | v04 |
| assets/final/rig/chr-ale_*_v04.png（12 部件＋head-worried）、chr-ale_*-outline_v04.png（13 張）、ale_rig.json、ale_attach.json、README.md | 分件紙偶 v04＋整體描邊底圖＋操偶線扣點 | 阿樂叔叔 | 接縫修正（肩球、膝舌片弧線；G2 問題 3）、乾淨困惑頭；扣點 wrist_back、elbow_out、knee_front | a2_c001–a2_c004 | assets/parts/ale_v03 → build_ale_rig.py（不改原檔）；姿勢 ale_a2_poses.py；扣點 ale_attach.py | 使用者 ChatGPT 方案生成（母版） | 部件比例不變（×1.000）；修正前後對照 review/G4/art/ale_a2_poses_before.png／_fixed.png；6 個 a2 姿勢著地腳誤差 ±8 px | v04 |
| assets/final/face/{xiaoqing,xiaoyu,ale}/chr-<角色>_{mouth_closed,mouth_half,mouth_open,mouth_round,mouth_worried,eyes_open,eyes_half,eyes_closed}_v01.png（24 片）＋face.json（3 份） | 臉部換片（透明蓋片，同組同錨點同尺寸） | 小晴、小宇、阿樂叔叔 | 嘴 5 種、眼 3 種；小晴、小宇的圓唇＝原圖、阿樂的擔心抿嘴＝原圖、三人的睜眼＝原圖 | a2_c002、a2_c004（對嘴、眨眼） | build_faces.py：原圖局部調和填補＋同強度紙紋＋程式畫剪紙風線條（顏色取自原圖） | 使用者 ChatGPT 方案生成（原圖）＋程式繪製 | 只改眼、嘴框內；臉型、膚色、髮型、眼鏡不變（review/G4/art/face_sheet.png） | v01 |
| assets/final/g4_manifest.json | 素材清單 | G4 代表鏡頭 | 每個素材的 id、檔案、層、建議世界座標與縮放、錨點；a2 六個姿勢（度與 three.js 弧度）、扣點世界座標、時間提示 | 片頭、a2_c002、a2_c004、片尾 | build_manifest.py（數值來自 layout_test.py 試排） | 原創（程式產生） | 試排 review/G4/art/a2_layout_test.png；對比 review/G4/art/contrast_g4.json | v01 |

## 劇場程式產生的視覺素材（G4 引擎代理，2026-10-21 第 2 天）

全部在載入時由程式產生（沒有外部圖檔、沒有文字烘進圖裡）；重建方式：`cd app && npm run build`。驗證：`node tools/engine-test.mjs`（86 項）、`node tools/capture.mjs --cues g4 --probe --analysis-fps 30`。

| 檔名 | 類型 | 角色／場景 | 部件 | 使用 cue | 來源 | 授權 | 檢視結果 | 版本 |
|---|---|---|---|---|---|---|---|---|
| app/src/stage/curtain.ts（程式幾何＋程式紋理） | 摺層紙布幕 | 台口 | 左右兩片手風琴摺紙各 16 摺、下緣深色紙邊＋金線 | a0_c000、a0_c001、a8_c002、a8_c003 | 程式產生 | 原創 | 布幕色 #8c4632（R/(R+G+B) < 0.8，非飽和紅）；合攏時中央重疊 0.3；30 fps 光敏分析通過；素材 tex-curtain-paper 因飽和紅（0.815）暫不採用 | v01 |
| app/src/stage/strings.ts（程式紋理） | 操偶線紙繩＋紙環 | 阿樂叔叔 | 腕背、肘外、膝前 3 條；紙環＝包住肢體的米白紙帶 | a2_c002、a2_c004 | 程式產生 | 原創 | 平面中灰紙帶（L*≈48）＋兩側深灰邊＋左受光邊，無扭絞紋；近景線寬 12–16 px；腕、肘線 ΔL*≈40（投影 v2 ≈28）；膝前線對工作褲 ΔL* 8–12 | v01 |
| app/src/stage/workshop.ts（程式畫景片） | 立體書景片 | 燈籠店 | 抽屜櫃、竹篾架、圓凳、左下燈籠堆、右下紙卷（素材背牆／地板／工作台缺圖時另有程式畫的同位置景片）；所有景片烘進 5–6 px 卡紙厚度 | a0_c001、a2_c002、a2_c004、a8_c002 | 程式產生 | 原創 | 無文字；兒童站位背景投影 v2 亮度中位數 0.56–0.58（開幕景片立起途中 0.42） | v01 |
| app/src/stage/face.ts（FALLBACK_FACES，程式畫） | 臉部換片退路 | 阿樂叔叔一般頭、小晴 stand、小宇 stand | 閉眼、半閉眼、嘴型（閉、半開、大開、圓唇、擔心、微笑） | a0_c001、a2_c002 | 程式產生（膚色取自原圖） | 原創 | 正式 face.json 指向該圖時自動改用正式換片 | v01 |
| app/src/ui/overlays.ts＋theater.css | 署名卡排字 | 署名卡 | 「許博明老師製作」（程式字型排版） | a0_c000、a0_c001、a8_c003 | 程式排版（系統字型 Microsoft JhengHei／PingFang TC） | — | 底紙採用 assets/final/tex-titlecard-paper（素材代理）；片頭片尾同款 | v01 |

## G4 整合與驗收包（整合代理，2026-10-21 第 2 天）

只追加 G4 整合新產生的檔案；圖、配音、配樂、音效沿用各製作代理的列（本代理沒有重新生成任何素材）。驗收包內的混音與播放錄製是驗收用的衍生檔，不進演出包。

| 檔名 | 類型 | 角色／場景 | 部件／表情 | 使用 cue | 來源／生成參考 | 授權 | 檢視結果 | 版本 |
|---|---|---|---|---|---|---|---|---|
| app/cues/g4.json | cue 集（代表鏡頭） | 燈籠店（G4） | 署名卡待機→開幕→線落下來→操偶線（必要旁白一）→布幕合攏→片尾署名卡 | a0_c000、a0_c001、a2_c002、a2_c004、a8_c002、a8_c003 | 引擎代理建立；整合代理修正 a8_c003 配樂音量（閉幕曲不再於署名卡出現時被壓到無聲） | 原創 | 台詞與劇本 v03 逐字相同（驗收包 safety_data.json、transcripts.md）；a2_c002＋a2_c004 長度見 review/G4/pack/durations.json | v01 |
| review/G4/pack/audio/g4_mix.wav | 驗收用最終混音（48 kHz 立體聲 16-bit） | G4 全段 | 配音 7 句中的 4 句、配樂 4 首、音效 5 種依 cue 時間混音 | G4 全段 | tools/g4_review_pack.py 依引擎混音規則離線混音（來源：audio/vo、audio/music、audio/sfx 各檔） | 衍生自各來源檔（edge-tts 配音風險見配音列；配樂音效自製原創） | 響度數據 review/G4/pack/audio/loudness.json；聽感未驗證 | v01 |
| review/G4/pack/g4_playback.mp4 | 驗收用播放錄製（1920×1080、30 fps、H.264＋AAC） | G4 全段 | 固定步長逐格＋g4_mix.wav | G4 全段 | tools/g4_review_pack.mjs（虛擬時鐘逐格截圖）＋ffmpeg | 衍生自上列素材與劇場程式畫面 | 由腳本產生、不挑畫面；不進演出包 | v01 |

## G4 修正第 1 輪美術（2026-10-21 第 2 天約 05:40–，美術代理）

對應 G4 驗收問題 16、17、21、22、23、25、27、33、34。v04／v01 檔案全部保留不覆寫；`tools/pack.mjs` 每個 id 取最新版本，新檔一放進 assets/final 打包就自動換用（id 不變）。腳本都在 review/G4/art/scripts/；投影模擬在 review/G4/art/sim/（tools/projsim.py v2）。引擎介面變更見 assets/final/rig/README.md 第 9 節、g4_manifest.json 的 `string_render`、`round1_art`、`characters.xiaoqing`。

| 檔名 | 類型 | 角色／場景 | 部件／表情 | 使用 cue | 來源／生成參考 | 授權 | 檢視結果 | 版本 |
|---|---|---|---|---|---|---|---|---|
| assets/final/tex-string-rope_v01.png | 操偶線紙繩貼圖（64×256，不透明，上下四方連續） | 阿樂叔叔 | 淡灰紙繩身（平均 sRGB≈178）＋斜向扭紋＋紙纖維、兩側深灰邊、左側淡色受光邊 | a2_c002、a2_c004、a8_c002 | 程式產生（make_string_tex.py）；畫法依 review/G4/art/ale_a2_poses_fixed.png 與 v1.2 第 15.2 節「灰色扭紋紙繩」 | 原創（程式產生） | 8 px 寬時深灰邊各約 1.5 px、扭紋間距約 10.7 px，1:1 看得到扭紋（review/G4/art/string_preview_v01.png）；線身對淺牆 ΔL* 18、深灰邊對牆 64、線身對工作褲 32（string_tex_v01.json） | v01 |
| assets/final/tex-string-rope_v02.png | 操偶線紙繩貼圖 v02（64×256，不透明，上下四方連續；pack 自動取最新版） | 阿樂叔叔 | 平面淡灰紙繩：繩身平均 sRGB≈184（L* 74.7）＋不規則短纖維點紋（無扭紋）、兩側深灰邊、左側淡色受光邊 | 全劇操偶線 | 程式產生（review/G4/art/scripts/make_string_tex_v02.py）；G4 關卡決定：去掉規則斜向扭絞紋（REVIEW.md G4 關卡決定） | 原創（程式產生） | 沿線亮度自相關（週期 8–14 px）0.133（v01 為 0.974）；對照圖 review/G4/art/string_tex_v01_v02_4x.png；舞台 ΔL* 於 G5 驗收包重量 | v02 |
| assets/final/tex-string-ring_v01.png | 紙環貼圖（128×128，透明） | 阿樂叔叔 | 圓環：外深灰細線＋白紙芯邊＋淡灰紙環身＋內深灰細線，中間透明 | 同上 | 程式產生（make_string_tex.py） | 原創（程式產生） | 不是矩形帶、鉚釘或扁板；建議直徑 0.103 世界單位（中景約 19 px） | v01 |
| assets/final/rig/ale_attach_v05.json | 操偶線扣點 v05 | 阿樂叔叔 | 腕背、肘外、膝前扣點內移，整個紙環在肢體剪影內（離外形 ≥ 26.5 母版 px） | a2_c002、a2_c004 | ale_attach_v05.py | 原創（程式產生） | 六個 a2 姿勢紙環都在剪影內（review/G4/art/ale_attach_v05_check.json、ale_a2_poses_v05.png） | v05 |
| assets/final/rig/chr-ale_forearm-{l,r}_v05.png、-outline_v05.png | 分件：前臂（透明） | 阿樂叔叔 | 移除切件帶進來的襯衫碎片（左 403 px、右 1217 px）、補 3 px 深棕線稿、膚色區補紙紋 | a2_c001–a2_c004 | assets/final/rig 同名 v04 → fix_forearms_v05.py | 使用者 ChatGPT 方案生成（母版）＋程式修整 | 尺寸、樞紐不變；前後對照 review/G4/art/forearm_fix_v05.png | v05 |
| assets/final/rig/chr-ale_head-greet_v05.png、-outline_v05.png | 替換頭（透明） | 阿樂叔叔 | X2 想打招呼：一般頭的微笑＋眉毛上抬 9 px（外端再抬 2 px） | a2_c002（揮手意圖） | assets/final/rig/chr-ale_head_v04.png → make_ale_greet_head.py（不重新生成） | 使用者 ChatGPT 方案生成（母版）＋程式修整 | 只動眉毛 1698 px；臉型、膚色、髮型不變（review/G4/art/ale_head_greet_v05.png） | v05 |
| assets/final/rig/ale_rig_v05.json | 分件資料 v05 | 阿樂叔叔 | 同 v04，前臂換 v05、加替換部件 head_greet | a2_c001–a2_c004 | ale_attach_v05.py、make_ale_greet_head.py | 原創（程式產生） | JSON id 仍是 rig/ale_rig | v05 |
| assets/final/face/{xiaoqing,xiaoyu,ale}/chr-<角色>_eyes_closed_v02.png＋face_v02.json | 臉部換片：閉眼 | 小晴、小宇、阿樂叔叔 | 中性閉眼（往下彎的眼皮線），取代 v01 向上拱的笑眼 | a2_c002、a2_c004（眨眼） | build_faces_v05.py（build_faces.py 加 closed_curve 參數） | 使用者 ChatGPT 方案生成（原圖）＋程式繪製 | 其餘換片沿用 v01；review/G4/art/face_sheet_v05.png | v02 |
| assets/final/bg-workshop-back_v03.jpg | 景片：後牆（不透明 2964×1415） | 燈籠工作室 | 只把最下方踢腳板（45 px）由偏橘 #DFB683 一帶提亮成淺木色 #F0DEC0，上緣留切口線 | a0_c001、a2_c001–a2_c012 | assets/final/bg-workshop-back_v02.jpg → make_back_v03.py | 使用者 ChatGPT 方案生成＋程式修整 | 開幕 5.30 s 小晴量測區投影 v2 亮度預估 0.42→0.55（wall_v03.json；正式數據待重擷取）；review/G4/art/wall_v03_compare.png | v03 |
| assets/final/ui/ui-speaker_{narrator,ale,xiaoqing,xiaoyu}_v01.png | 字幕說話者小頭像（128×128 透明圓形徽章） | 旁白、阿樂叔叔、小晴、小宇 | 旁白＝未點亮的和紙燈籠（程式畫）；角色＝從正式母版裁頭肩 | 全劇字幕（v1.2 第 15.3 節） | make_speaker_icons.py | 原創（程式產生）／使用者 ChatGPT 方案生成（母版裁切） | 圖中無字；字幕框深底上與投影 v2 都清楚（review/G4/art/speaker_icons_v01.png）；是否採用由主線決定 | v01 |
| assets/generated/chr-xiaoqing_pose-watch_v05.png → assets/final/chr-xiaoqing_pose-watch_v05.png | 表演姿勢圖（透明；生成 1024×1536 → 裁成 544×1520） | 小晴 | watch：3/4 側身朝畫面左、手輕扶吊帶、抬頭注視阿樂、微笑（取代 a2_c002 開場的正面立正母版） | a2_c002 開場 | Codex image_gen（pose_xq_watch_v05，第 1 次生成、未修改；附 review/G2a/S4.png＋assets/generated/chr-xiaoqing_master_v04.png）；吊帶褲 L* 39.0 → recolor_garment 同色相調到 37.0（同 D-G2-06）；process_xq_v05.py 裁邊、alpha 254→255 | 使用者 ChatGPT 方案生成 | 無文字（筆記本封面空白）、星星髮夾摺痕清楚；放進 a2_c002 實際畫面吊帶褲對背景 3.42:1（投影 v2，review/G4/art/xq_v05_stage_check.png） | v05 |
| assets/generated/chr-xiaoqing_pose-palm_v05.png → assets/final/chr-xiaoqing_pose-palm_v05.png | 表演姿勢圖（透明；846×1517） | 小晴 | palm：「叔叔，小心！」伸出手掌示意（掌心向外、手指併攏、手在胸口高度，沒有指人）、另一手在胸前、擔心叫喚的圓嘴 | a2_c002（a2_c002_02 句，≤1.5 秒後換回 worried） | 同上（pose_xq_palm_v05）；吊帶褲 L* 38.7 → 37.1 | 使用者 ChatGPT 方案生成 | 無文字；不靠近、不碰阿樂；3.48:1 | v05 |
| assets/generated/chr-xiaoqing_pose-worried_v05.png → assets/final/chr-xiaoqing_pose-worried_v05.png | 表演姿勢圖（透明；528×1468） | 小晴 | worried：雙手輕握在胸前、3/4 側身朝畫面左、擔心看著阿樂（不指人） | a2_c002 喊完之後、a2_c004 全段 | 同上（pose_xq_worried_v05）；吊帶褲 L* 38.6 → 37.0 | 使用者 ChatGPT 方案生成 | 無文字；3.44:1 | v05 |
| assets/final/face/xiaoqing/chr-xiaoqing_{watch,palm,worried}-{mouth_closed,mouth_half,mouth_open,mouth_round,mouth_worried,eyes_open,eyes_half,eyes_closed}_v01.png（watch 另有 mouth_smile）＋face-{watch,palm,worried}_v01.json＋face_v03.json | 臉部換片（透明蓋片） | 小晴 | 三張新姿勢各 8–9 片（閉眼一律中性閉眼）；face_v03.json＝引擎原生 FaceConfig（perPose：reach、watch、palm、worried；stand 照舊用退路換片） | a2_c002、a2_c004 | build_faces_xq_v05.py（眼、嘴位置手量：review/G4/art/xq_v05_face_cfg.json） | 使用者 ChatGPT 方案生成（原圖）＋程式繪製 | 只改眼、嘴框內（review/G4/art/face_sheet_xq_v05.png）；現有引擎 build 煙霧測試：小晴 watch／palm／worried＝正式換片、阿樂 head_greet＝退路換片，無錯誤 | v01／v03 |
| assets/final/g4_manifest.json | 素材清單（就地更新到 v05） | G4 代表鏡頭 | 後牆改 v03、rig 改 v05、新增紙繩／紙環貼圖、說話者小頭像、小晴三張新姿勢；新增 string_render、round1_art、characters.xiaoqing（cast.ts 會用它覆寫小晴的立牌姿勢表，預設姿勢仍是 stand） | 片頭、a2_c002、a2_c004、片尾 | build_manifest_v05.py | 原創（程式產生） | — | v05 |

## G4 修正第 2 輪美術（2026-10-21 第 2 天，美術代理）

對應 G4 第 2 輪問題 1、5、9（兩眼同閉）與 8（米白紙環）。舊檔全部保留不覆寫；圖像 id 不含版本號，`tools/pack.mjs` 自動取最新版（已用 `node tools/pack.mjs --out <暫存>` 確認選到下列新檔）。沒有新生成圖（不需要 image_gen），全部是以原圖局部填補＋程式繪製。腳本在 review/G4/art/scripts/；投影模擬在 review/G4/art/sim/。引擎介面見 assets/final/rig/README.md 第 10 節、g4_manifest.json 的 `round2_art`。

| 檔名 | 類型 | 角色／場景 | 部件／表情 | 使用 cue | 來源／生成參考 | 授權 | 檢視結果 | 版本 |
|---|---|---|---|---|---|---|---|---|
| assets/final/face/xiaoqing/chr-xiaoqing_eyes_half_v02.png、chr-xiaoqing_eyes_closed_v03.png | 臉部換片：半閉、閉眼（reach 姿勢頭層） | 小晴 | 兩眼同步：閉眼＝近乎平直、略往下彎的中性閉眼線（不是笑眼）；半閉＝上半眼改眼皮 | a2_c002、a2_c004（眨眼） | build_faces_r2.py（chr-xiaoqing_pose-reach-worried_v04 原圖局部填補＋程式繪製；取代 v01／v02 的單眼閉合） | 使用者 ChatGPT 方案生成（原圖）＋程式繪製 | 每隻眼原本眼白／眼珠殘留 ≤0.3%、閉眼線 139／180 px（blink_check_r2.json）；review/G4/art/face_sheet_v06.png | v02／v03 |
| assets/final/face/xiaoqing/chr-xiaoqing_{watch,palm,worried}-eyes_half_v02.png、-eyes_closed_v02.png | 臉部換片：半閉、閉眼（三張新姿勢） | 小晴 | 同上；修正第 1 輪畫面左側那隻眼沒閉（舞台上像眨單眼） | a2_c002、a2_c004 | build_faces_r2.py（chr-xiaoqing_pose-{watch,palm,worried}_v05 原圖） | 使用者 ChatGPT 方案生成（原圖）＋程式繪製 | 兩眼殘留皆 0%、閉眼線 103–186 px；投影 v2 下閉眼線對皮膚約 5.6:1；review/G4/art/face_sheet_xq_v06.png、sim/face_sheet_xq_v06_stress_sheet.png | v02 |
| assets/final/face/xiaoyu/chr-xiaoyu_eyes_half_v02.png、chr-xiaoyu_eyes_closed_v03.png | 臉部換片：半閉、閉眼 | 小宇 | 兩眼同步（左眼不再只剩淡化殘影）；眼鏡框保留不蓋 | a2_c002、a2_c004 | build_faces_r2.py（chr-xiaoyu_pose-stepback-surprised_v04 原圖） | 使用者 ChatGPT 方案生成（原圖）＋程式繪製 | 兩眼殘留 0%、閉眼線 115／147 px；投影 v2 約 6.5:1；face_sheet_v06.png | v02／v03 |
| assets/final/face/xiaoqing/face_v04.json、face-{watch,palm,worried}_v02.json；assets/final/face/xiaoyu/face_v03.json | 臉部換片設定 | 小晴、小宇 | face_v04＝引擎原生 FaceConfig（perPose 與 v03 相同，只更新紀錄）；其餘為素材代理格式，換成新檔名 | a2_c002、a2_c004 | build_faces_r2.py | 原創（程式產生） | 錨點、尺寸、圖像 id 不變 | v04／v02／v03 |
| assets/final/tex-string-ring_v02.png | 紙環貼圖（128×128，透明） | 阿樂叔叔 | 米白紙環：紙面 sRGB≈(251,242,222)、紙紋、左下紙帶接口、暖深棕描邊、右下單側厚紙陰影；沒有金屬漸層或高光 | a2_c002、a2_c004、a8_c002 | make_ring_tex_v02.py（程式產生；取代灰色像墊圈的 v01） | 原創（程式產生） | 貼圖紙面 luma 242、色相 41.6°、彩度 0.115；換到 G4 擷取影格的示意（light 1.0）環身 luma 中位數 238、最低 227（v01 擷取 194、彩度 0.074）；review/G4/art/ring_crops_v02_preview.png、ring_tex_v02.json。正式量測待引擎重擷取 | v02 |
| assets/final/g4_manifest.json | 素材清單（就地更新到 v06） | G4 代表鏡頭 | tex-string-ring 改指 v02；新增 round2_art、string_render.ring | a2_c002、a2_c004、a8_c002 | build_manifest_r2.py | 原創（程式產生） | — | v06 |

## G5 共用美術（2026-10-21 第 2 天下午，共用美術代理）

G5 開工前的多幕共用角色與景。image_gen 用量：19 張角色／道具圖各生成 1 次（0 次重抽）；15:01 起 5 張景片／道具（校門口三張、小貨車、長椅）回「usage limit，19:50 後再試」，沒有產出也沒有消耗，改用程式繪製退路版（提示都在 review/G5/shared_art/raw/，19:50 後可用 `_run.sh` 重抽，換圖用新版本號 v02）。兒童新姿勢的主色依 D-G2-06 同色相調回 v04 色票（吊帶褲 L* 37、外套 L* 39）。自動檢查、接觸表、投影模擬、舞台預覽都在 review/G5/shared_art/（INDEX.md）。所有生成圖沒有文字、標誌、紅十字、真實品牌或物流配色。

| 檔名 | 類型 | 角色／場景 | 部件／表情 | 使用 cue | 來源／生成參考 | 授權 | 檢視結果 | 版本 |
|---|---|---|---|---|---|---|---|---|
| assets/generated/chr-xiaoqing_pose-cross_v06.png → assets/final/chr-xiaoqing_pose-cross_v06.png | 表演姿勢圖（透明；576×1504） | xiaoqing | cross：P-QG1 口訣「不碰」：雙手前臂在胸前交叉成 X，正面、堅定微表情 | a3_c004、a7_c002 | Codex image_gen（review/G5/shared_art/raw/pose_xq_cross_v06.png，第 1 次生成、未重抽；參考 S4＋assets/generated/chr-xiaoqing_master_v04.png）；未調整（L* 與 v04 差 ≤ 1）；process_chars.py 去雜點、裁邊＋16 px | 使用者 ChatGPT 方案生成 | 白邊 9 px、霧邊 0 px、腳沒裁到（原圖邊距 下 29 px）、左右明度差 1.3；湖水綠吊帶褲 #236364 L*38.0（與 v04 ΔE 1.2）；芥末黃上衣 #F3A924 L*74.4（與 v04 ΔE 1.1）；兩眼同閉：通過（退路換片模擬）；投影模擬 review/G5/shared_art/projsim/chr-xiaoqing_pose-cross_v06_sheet.jpg | v06 |
| assets/generated/chr-xiaoqing_pose-palmno_v06.png → assets/final/chr-xiaoqing_pose-palmno_v06.png | 表演姿勢圖（透明；729×1498） | xiaoqing | palmno：掌心向外平穩說「不要／不試」（朝畫面左、手在胸口高度、不指人） | a1_c004、a3_c004（不試）、a4_c012 | Codex image_gen（review/G5/shared_art/raw/pose_xq_palmno_v06.png，第 1 次生成、未重抽；參考 S4＋assets/generated/chr-xiaoqing_master_v04.png）；主色同色相調回 v04 色票（D-G2-06）；process_chars.py 去雜點、裁邊＋16 px | 使用者 ChatGPT 方案生成 | 白邊 10 px、霧邊 0 px、腳沒裁到（原圖邊距 下 33 px）、左右明度差 1.8；湖水綠吊帶褲 #146164 L*37.1（與 v04 ΔE 2.6）；芥末黃上衣 #FCB72F L*79.0（與 v04 ΔE 6.3）；兩眼同閉：通過（退路換片模擬）；投影模擬 review/G5/shared_art/projsim/chr-xiaoqing_pose-palmno_v06_sheet.jpg | v06 |
| assets/generated/chr-xiaoyu_pose-cross_v06.png → assets/final/chr-xiaoyu_pose-cross_v06.png | 表演姿勢圖（透明；553×1462） | xiaoyu | cross：P-XY1 口訣「不碰」：雙手胸前交叉；左腕兒童手錶可見 | a3_c004、a7_c002 | Codex image_gen（review/G5/shared_art/raw/pose_xy_cross_v06.png，第 1 次生成、未重抽；參考 S4＋assets/generated/chr-xiaoyu_master_v04.png）；主色同色相調回 v04 色票（D-G2-06）；process_chars.py 去雜點、裁邊＋16 px | 使用者 ChatGPT 方案生成 | 白邊 12 px、霧邊 0 px、腳沒裁到（原圖邊距 下 45 px）、左右明度差 15.2；橘紅外套 #B12400 L*38.9（與 v04 ΔE 4.8）；卡其短褲 #B99164 L*63.0（與 v04 ΔE 7.2）；兩眼同閉：通過（退路換片模擬）；投影模擬 review/G5/shared_art/projsim/chr-xiaoyu_pose-cross_v06_sheet.jpg | v06 |
| assets/generated/chr-xiaoyu_pose-watch-dial_v06.png → assets/final/chr-xiaoyu_pose-watch-dial_v06.png | 表演姿勢圖（透明；630×1494） | xiaoyu | dial：P-XY2 舉手錶撥號：左腕舉到胸前、右手食指按錶面、低頭看；錶面只有電話圖示 | a5_c005–a5_c007（a7_c001 大圖來源） | Codex image_gen（review/G5/shared_art/raw/pose_xy_watch_v06.png，第 1 次生成、未重抽；參考 S4＋assets/generated/chr-xiaoyu_master_v04.png）；主色同色相調回 v04 色票（D-G2-06）；process_chars.py 去雜點、裁邊＋16 px | 使用者 ChatGPT 方案生成 | 白邊 12 px、霧邊 0 px、腳沒裁到（原圖邊距 下 22 px）、左右明度差 0.8；橘紅外套 #AF2901 L*39.0（與 v04 ΔE 2.2）；卡其短褲 #BB8F5F L*62.4（與 v04 ΔE 5.6）；兩眼同閉：通過（退路換片模擬）；投影模擬 review/G5/shared_art/projsim/chr-xiaoyu_pose-watch-dial_v06_sheet.jpg | v06 |
| assets/generated/chr-pinan_master_v01.png → assets/final/chr-pinan_master_v01.png | 角色母版站姿（透明；573×1515） | pinan | stand：母版站姿：低馬尾＋齊瀏海、竹編髮圈、茄紫上衣＋米白針織背心、深灰長褲、橄欖綠書包 | a1、a3_c003、a6、a7_c003 | Codex image_gen（review/G5/shared_art/raw/chr_pinan_stand_v01.png，第 1 次生成、未重抽；參考 S4＋chr-xiaoqing_master_v04＋chr-xiaoyu_master_v04）；process_chars.py 去雜點、裁邊＋16 px | 使用者 ChatGPT 方案生成 | 白邊 7 px、霧邊 0 px、腳沒裁到（原圖邊距 下 29 px）、左右明度差 0.7；茄紫上衣 #653F4F L*31.5；兩眼同閉：通過（正式換片）；投影模擬 review/G5/shared_art/projsim/chr-pinan_master_v01_sheet.jpg | v01 |
| assets/generated/chr-lin_master_v01.png → assets/final/chr-lin_master_v01.png | 角色母版站姿（透明；456×1546） | lin | stand：母版站姿：低髮髻、酒紅開襟毛衣、米白上衣、深灰長褲、空白識別證 | a3_c003、a3_c008、a4_c012、a4_c013、a5_c007、a6_c006 | Codex image_gen（review/G5/shared_art/raw/chr_lin_stand_v01.png，第 1 次生成、未重抽；參考 S4＋chr-xiaoqing_master_v04＋chr-ale_master_v02）；process_chars.py 去雜點、裁邊＋16 px | 使用者 ChatGPT 方案生成 | 白邊 7 px、霧邊 3 px、腳沒裁到（原圖邊距 下 12 px）、左右明度差 0.7；酒紅毛衣 #782D2F L*29.6；兩眼同閉：通過（正式換片）；投影模擬 review/G5/shared_art/projsim/chr-lin_master_v01_sheet.jpg | v01 |
| assets/generated/chr-chen_master_v01.png → assets/final/chr-chen_master_v01.png | 角色母版站姿（透明；649×1522） | chen | stand：母版站姿：灰白平頭、淺灰制服（無徽章字樣）、黃綠導護背心（米白反光條不發光） | a4_c001、a4_c012、a4_c013、a5_c001、a5_c007 | Codex image_gen（review/G5/shared_art/raw/chr_chen_stand_v01.png，第 1 次生成、未重抽；參考 S4＋chr-xiaoqing_master_v04＋chr-ale_master_v02）；process_chars.py 去雜點、裁邊＋16 px | 使用者 ChatGPT 方案生成 | 白邊 10 px、霧邊 0 px、腳沒裁到（原圖邊距 下 22 px）、左右明度差 4.1；黃綠背心 #D6D94B L*84.2；淺灰制服 #D5C9B5 L*81.6；兩眼同閉：通過（正式換片）；投影模擬 review/G5/shared_art/projsim/chr-chen_master_v01_sheet.jpg | v01 |
| assets/generated/chr-ye_master_v01.png → assets/final/chr-ye_master_v01.png | 角色母版站姿（透明；564×1536） | ye | stand：母版站姿：鼠尾草綠護理服、識別證只有手捧愛心圖示、胸前插筆、手錶（無紅十字） | a2_c012、a2_c013、a5_c008、a6_c006 | Codex image_gen（review/G5/shared_art/raw/chr_ye_stand_v01.png，第 1 次生成、未重抽；參考 S4＋chr-xiaoqing_master_v04＋chr-ale_master_v02）；process_chars.py 去雜點、裁邊＋16 px | 使用者 ChatGPT 方案生成 | 白邊 10 px、霧邊 0 px、腳沒裁到（原圖邊距 下 21 px）、左右明度差 2.3；鼠尾草綠護理服 #929C85 L*63.0；兩眼同閉：通過（正式換片）；投影模擬 review/G5/shared_art/projsim/chr-ye_master_v01_sheet.jpg | v01 |
| assets/generated/chr-xiaoyu_pose-palmno_v06.png → assets/final/chr-xiaoyu_pose-palmno_v06.png | 表演姿勢圖（透明；753×1480） | xiaoyu | palmno：a3_c002 掌心向外平穩拒絕（朝畫面左） | a1_c004、a3_c002、a3_c004 | Codex image_gen（review/G5/shared_art/raw/pose_xy_palmno_v06.png，第 1 次生成、未重抽；參考 S4＋assets/generated/chr-xiaoyu_master_v04.png）；主色同色相調回 v04 色票（D-G2-06）；process_chars.py 去雜點、裁邊＋16 px | 使用者 ChatGPT 方案生成 | 白邊 11 px、霧邊 0 px、腳沒裁到（原圖邊距 下 28 px）、左右明度差 1.3；橘紅外套 #B12500 L*38.9（與 v04 ΔE 4.5）；卡其短褲 #C29566 L*64.9（與 v04 ΔE 8.1）；兩眼同閉：通過（退路換片模擬）；投影模擬 review/G5/shared_art/projsim/chr-xiaoyu_pose-palmno_v06_sheet.jpg | v06 |
| assets/generated/chr-xiaoqing_pose-forehead_v06.png → assets/final/chr-xiaoqing_pose-forehead_v06.png | 表演姿勢圖（透明；665×1485） | xiaoqing | forehead：口訣「找大人」：手放額前張望（朝畫面右） | a3_c004、a7_c002 | Codex image_gen（review/G5/shared_art/raw/pose_xq_forehead_v06.png，第 1 次生成、未重抽；參考 S4＋assets/generated/chr-xiaoqing_master_v04.png）；主色同色相調回 v04 色票（D-G2-06）；process_chars.py 去雜點、裁邊＋16 px | 使用者 ChatGPT 方案生成 | 白邊 9 px、霧邊 0 px、腳沒裁到（原圖邊距 下 31 px）、左右明度差 1.2；湖水綠吊帶褲 #1B6161 L*37.2（與 v04 ΔE 1.2）；芥末黃上衣 #F1AA28 L*74.5（與 v04 ΔE 1.0）；兩眼同閉：通過（退路換片模擬）；投影模擬 review/G5/shared_art/projsim/chr-xiaoqing_pose-forehead_v06_sheet.jpg | v06 |
| assets/generated/chr-xiaoyu_pose-forehead_v06.png → assets/final/chr-xiaoyu_pose-forehead_v06.png | 表演姿勢圖（透明；680×1537） | xiaoyu | forehead：口訣「找大人」：手放額前張望（朝畫面右） | a3_c004、a7_c002 | Codex image_gen（review/G5/shared_art/raw/pose_xy_forehead_v06.png，第 1 次生成、未重抽；參考 S4＋assets/generated/chr-xiaoyu_master_v04.png）；主色同色相調回 v04 色票（D-G2-06）；process_chars.py 去雜點、裁邊＋16 px | 使用者 ChatGPT 方案生成 | 白邊 11 px、霧邊 0 px、腳沒裁到（原圖邊距 下 22 px）、左右明度差 0.5；橘紅外套 #AE2900 L*39.0（與 v04 ΔE 2.4）；卡其短褲 #B7895A L*60.5（與 v04 ΔE 3.5）；兩眼同閉：通過（退路換片模擬）；投影模擬 review/G5/shared_art/projsim/chr-xiaoyu_pose-forehead_v06_sheet.jpg | v06 |
| assets/generated/chr-xiaoqing_pose-walk_v06.png → assets/final/chr-xiaoqing_pose-walk_v06.png | 表演姿勢圖（透明；880×1448） | xiaoqing | walk：行走側身（往畫面右，3/4 側面） | 跨場移動（a1_c004、a3_c002、a4_c012 等） | Codex image_gen（review/G5/shared_art/raw/pose_xq_walk_v06.png，第 1 次生成、未重抽；參考 S4＋assets/generated/chr-xiaoqing_master_v04.png）；主色同色相調回 v04 色票（D-G2-06）；process_chars.py 去雜點、裁邊＋16 px | 使用者 ChatGPT 方案生成 | 白邊 10 px、霧邊 0 px、腳沒裁到（原圖邊距 下 74 px）、左右明度差 1.8；湖水綠吊帶褲 #186163 L*37.2（與 v04 ΔE 1.8）；芥末黃上衣 #FBB736 L*78.9（與 v04 ΔE 5.8）；兩眼同閉：通過（退路換片模擬）；投影模擬 review/G5/shared_art/projsim/chr-xiaoqing_pose-walk_v06_sheet.jpg | v06 |
| assets/generated/chr-xiaoyu_pose-walk_v06.png → assets/final/chr-xiaoyu_pose-walk_v06.png | 表演姿勢圖（透明；850×1496） | xiaoyu | walk：行走側身（往畫面右） | 跨場移動 | Codex image_gen（review/G5/shared_art/raw/pose_xy_walk_v06.png，第 1 次生成、未重抽；參考 S4＋assets/generated/chr-xiaoyu_master_v04.png）；主色同色相調回 v04 色票（D-G2-06）；process_chars.py 去雜點、裁邊＋16 px | 使用者 ChatGPT 方案生成 | 白邊 11 px、霧邊 0 px、腳沒裁到（原圖邊距 下 46 px）、左右明度差 1.2；橘紅外套 #B02600 L*39.0（與 v04 ΔE 3.7）；卡其短褲 #C29261 L*64.1（與 v04 ΔE 7.0）；兩眼同閉：通過（退路換片模擬）；投影模擬 review/G5/shared_art/projsim/chr-xiaoyu_pose-walk_v06_sheet.jpg | v06 |
| assets/generated/chr-ye_pose-crouch_v01.png → assets/final/chr-ye_pose-crouch_v01.png | 表演姿勢圖（透明；969×1310） | ye | crouch：P-YE1 蹲下平視、掌心朝上「我陪你」 | a2_c012、a2_c013、a5_c008 | Codex image_gen（review/G5/shared_art/raw/chr_ye_crouch_v01.png，第 1 次生成、未重抽；參考 S4＋該角色 G5 母版 v01）；process_chars.py 去雜點、裁邊＋16 px | 使用者 ChatGPT 方案生成 | 白邊 13 px、霧邊 0 px、腳沒裁到（原圖邊距 下 88 px）、左右明度差 3.7；鼠尾草綠護理服 #949F88 L*64.1；兩眼同閉：通過（正式換片）；投影模擬 review/G5/shared_art/projsim/chr-ye_pose-crouch_v01_sheet.jpg | v01 |
| assets/generated/chr-pinan_pose-sit-lantern_v01.png → assets/final/chr-pinan_pose-sit-lantern_v01.png | 表演姿勢圖（透明；597×1454） | pinan | sit_lantern：P-PA1 坐長椅綁竹燈籠（長椅不畫在圖裡，另用 props/prop-bench） | a1_c001、a1_c004 | Codex image_gen（review/G5/shared_art/raw/chr_pinan_sit_v01.png，第 1 次生成、未重抽；參考 S4＋該角色 G5 母版 v01）；process_chars.py 去雜點、裁邊＋16 px | 使用者 ChatGPT 方案生成 | 白邊 9 px、霧邊 0 px、腳沒裁到（原圖邊距 下 46 px）、左右明度差 3.9；茄紫上衣 #623E4E L*30.9；兩眼同閉：通過（正式換片）；投影模擬 review/G5/shared_art/projsim/chr-pinan_pose-sit-lantern_v01_sheet.jpg | v01 |
| assets/generated/chr-pinan_pose-walk-straps_v01.png → assets/final/chr-pinan_pose-walk-straps_v01.png | 表演姿勢圖（透明；765×1486） | pinan | walk_straps：a3_c003 雙手抓書包背帶、低頭快步走（往畫面右） | a3_c003、a6_c001 | Codex image_gen（review/G5/shared_art/raw/chr_pinan_walk_v01.png，第 1 次生成、未重抽；參考 S4＋該角色 G5 母版 v01）；process_chars.py 去雜點、裁邊＋16 px | 使用者 ChatGPT 方案生成 | 白邊 9 px、霧邊 0 px、腳沒裁到（原圖邊距 下 47 px）、左右明度差 1.2；茄紫上衣 #6C4252 L*33.4；兩眼同閉：通過（正式換片）；投影模擬 review/G5/shared_art/projsim/chr-pinan_pose-walk-straps_v01_sheet.jpg | v01 |
| assets/generated/chr-lin_pose-crouch_v01.png → assets/final/chr-lin_pose-crouch_v01.png | 表演姿勢圖（透明；820×1312） | lin | crouch：P-LIN1 蹲在小宇旁、對著舉起的手錶說話 | a5_c007 | Codex image_gen（review/G5/shared_art/raw/chr_lin_crouch_v01.png，第 1 次生成、未重抽；參考 S4＋該角色 G5 母版 v01）；process_chars.py 去雜點、裁邊＋16 px | 使用者 ChatGPT 方案生成 | 白邊 11 px、霧邊 0 px、腳沒裁到（原圖邊距 下 138 px）、左右明度差 0.9；酒紅毛衣 #7C2B31 L*30.0；兩眼同閉：通過（正式換片）；投影模擬 review/G5/shared_art/projsim/chr-lin_pose-crouch_v01_sheet.jpg | v01 |
| assets/generated/chr-lin_pose-sit_v01.png → assets/final/chr-lin_pose-sit_v01.png | 表演姿勢圖（透明；647×1520） | lin | sit：P-LIN2 坐長椅（長椅另用 props/prop-bench） | a5_c008 | Codex image_gen（review/G5/shared_art/raw/chr_lin_sit_v01.png，第 1 次生成、未重抽；參考 S4＋該角色 G5 母版 v01）；process_chars.py 去雜點、裁邊＋16 px | 使用者 ChatGPT 方案生成 | 白邊 10 px、霧邊 0 px、腳沒裁到（原圖邊距 下 24 px）、左右明度差 1.5；酒紅毛衣 #832E32 L*31.8；兩眼同閉：通過（正式換片）；投影模擬 review/G5/shared_art/projsim/chr-lin_pose-sit_v01_sheet.jpg | v01 |
| assets/generated/chr-inviter_kit_v01.png → assets/final/chr-inviter_hand-box_v01.png、assets/final/props/prop-sticker-box_v01.png | 邀請者的手＋盒子（透明；手從左緣入畫，左側是袖口切口不留白邊）／盒子特寫 | 邀請者 | H10 掌心朝上遞盒子；炭灰素色袖口、中間膚色、無飾品刺青；盒子＝一層蓋一層的俗豔貼紙（抽象星點漩渦、邊角翹起、角落露出一小截灰色紙線），無字、無品牌、無卡通角色、無真實產品外形、無煙 | a1_c002、a1_c003（特寫）、a2_c013（剪影版由程式壓暗）、a3_c001 | Codex image_gen（raw/prop_inviter_v01.png，第 1 次、一張圖兩件）；process_props.py 依連通區切開 | 使用者 ChatGPT 方案生成 | 白邊 9 px、霧邊 0；盒子反光是固定白點（不閃）；projsim/chr-inviter_hand-box_v01_sheet.jpg | v01 |
| assets/final/face/{pinan,lin,chen,ye}/chr-<角色>_<姿勢>-eyes_{half,closed}_v01.png、-mouth_<形狀>_v01.png＋face_v01.json | 臉部正式換片（透明蓋片）＋原生 FaceConfig（perPose） | 品安、林老師、陳伯伯、葉護理師 | 每個姿勢：眼睛半閉、閉眼（兩眼同一張＝同時閉；中性閉眼線）；嘴型 closed／half／open／round／worried／smile 中除了原圖本來那個以外的全部 | 這四位出場的所有 cue | build_faces_new.py：補片只畫在膚色＋這隻眼自己的像素，頭髮、臉緣線、白邊、透明背景一律保護（遠側眼貼髮際時退路換片會蓋到頭髮，所以做正式換片）；局部取樣膚色＋紙紋雜訊 | 使用者 ChatGPT 方案生成（原圖）＋程式繪製 | 9 個姿勢兩眼殘留 0%、閉眼線 72–388 px、溢出 ≤13 px（blink_check_pieces.json）；放大圖 faces_pieces/*.png、contact_faces.jpg | v01 |
| assets/final/rig/show_characters.json | 角色立牌設定（StandeeCharConfig×6＋fallbackFaces×18） | 小晴、小宇、品安、林老師、陳伯伯、葉護理師 | 姿勢表（含 G4 既有姿勢）、身高（兒童 2.42–2.5、成人 3.42–3.58）、坐蹲姿勢的虛擬 headTop、坐姿 feet（座面對齊長椅 0.92）；fallbackFaces＝face.ts FALLBACK_FACES 同格式（深色連通區實量，ref＝alpha≥128 左上角） | G5 各幕 | build_show_characters.py、measure_faces.py（人工更正 face_boxes_manual.json） | 原創（程式產生） | 小晴、小宇 9 個新姿勢退路眨眼模擬全部兩眼同閉（殘留 ≤2.3%、補片溢出 ≤20 px，blink_check.json、faces/*.png）；比例 contact_characters.png、scale_report.json | v01 |
| assets/final/sets/square/set-square_{sky,mountains,backrow,arcade,tree-a,tree-b,planter-tall,planter-mid,planter-long}_v01.png＋layout.draft.json | 景片：小鎮廣場分層景（天空不透明，其餘透明） | 小鎮廣場 | 由 G2 拼版切成單件（不重抽）；layout 草稿給世界座標、層、寬高 | 第一幕、第二幕 a2_c012（求助站）、第六幕 a6_c006、廣場段 | assets/generated/bg-square-*_v03.png（G2 Codex image_gen）→ build_square.py | 使用者 ChatGPT 方案生成 | 平光預覽兒童身後投影 v2 中位 0.47–0.48（差一點到 0.50，layout 註明引擎比照 G4 後牆給自發光）；sets/square_preview_*.png | v01 |
| assets/final/sets/gate/set-gate_{school-building,pillar,folding-gate,school-wall,guard-house,floor}_v01.png＋layout.draft.json | 景片：校門口分層景（透明；地面不透明；警衛室窗玻璃挖空） | 校門口（第三、四、五幕） | 三層樓走廊式校舍、洗石子門柱、伸縮門、圍牆＋樹籬、警衛室（右側校內）、地面（柏油路＋斑馬線、人行道、黃色接送線）；沿用廣場天空、遠山、對街騎樓、行道樹、花台；無校徽、無字 | a3_c003、a4_c001–a4_c013、a5_c001–a5_c007 | 程式繪製退路版（build_gate.py＋paperdraw.py；紙紋取自 G2 天空景片）：15:01 啟動的 image_gen 回「usage limit，19:50 後再試」，提示已備妥（raw/set_gate_*_v01.prompt.txt） | 原創（程式產生） | 平光預覽兒童身後投影 v2 中位 0.53–0.56（≥0.50）；sets/gate_preview_{medium,wide,mid_low}.png、preview_report.json | v01 |
| assets/final/props/prop-bench_v01.png | 道具：長椅（透明，白色紙芯邊） | 共用（廣場、校門外、醫院走廊） | 木條長椅正面略俯視、灰綠鐵腳、三人座；座面世界高 0.92 | a1_c001、a1_c004、a4_c013、a5_c001、a5_c007、a5_c008 | 程式繪製（build_gate.py；image_gen 額度用完的退路） | 原創（程式產生） | 品安 P-PA1、林老師 P-LIN2 坐上去座面對齊（contact_characters.png 藍線、square_preview_medium.png） | v01 |
| assets/final/props/prop-truck_v01.png、prop-truck-wheel_v01.png | 道具：阿樂叔叔的小貨車（側面、車頭朝右）＋可轉動輪子 | 第四幕 | 淡米色車身、無標誌無車牌字、帆布車斗、後窗旁露出竹篾貓耳尖；頭燈尾燈不亮 | a4_c001、a4_c008、a4_c013 | 程式繪製（build_gate.py；額度用完的退路，提示 raw/prop_truck_v01.prompt.txt） | 原創（程式產生） | 不用真實品牌或物流配色；輪心、貓耳尖、後窗、車門位置寫在 sets/gate/layout.draft.json | v01 |

## G5 第一批（各幕代理與配樂音效代理，主線 2026-10-21 21:1x 合併）

### 來源：review/G5/a1/ASSETS_rows.md

# 開場＋第一幕（a0、a1）新素材：資產表列（給主線併進 ASSETS.md）

2026-10-21 第 2 天傍晚，G5 開場＋第一幕代理。Codex image_gen 額度用完（約 19:50 恢復），本批**全部程式繪製**（Pillow＋G2 同款紙紋，`review/G5/shared_art/scripts/paperdraw.py`；腳本 `review/G5/a0/scripts/build_a01_art.py` 可重跑），沒有呼叫 codex、沒有用到任何外部圖。圖裡沒有任何文字、數字、標誌、紅十字、真實品牌或物流配色。三張角色補姿勢是既有母版／姿勢圖的程式加工（加手錶、左右鏡像）。

| 檔名 | 類型 | 角色／場景 | 部件／表情 | 使用 cue | 來源／生成參考 | 授權 | 檢視結果 | 版本 |
|---|---|---|---|---|---|---|---|---|
| assets/final/sets/workshop_a0/design_v01.png | 景片（透明；450×555） | 燈籠店 workshop_a0 | 牆上的主燈設計圖：微黃圖紙，鉛筆線摺紙貓燈（折折同色系）、竹骨架小草圖、沒有數字的尺寸虛線、四顆黃銅圖釘 | a0_c002–a0_c005 | 程式繪製（build_a01_art.py design） | 本專案自製 | 無文字、無數字；引擎內 a0_c003 設計圖近景可辨識 | v01 |
| assets/final/sets/workshop_a0/stand_v01.png | 道具（透明；339×132，白邊 6 px） | 燈籠店 | 工作台上空著的主燈底座：圓木座＋四個空插孔 | a0_c002–a0_c005 | 程式繪製（stand） | 本專案自製 | 「工作台中央空了一大塊」的視覺線索 | v01 |
| assets/final/sets/workshop_a0/chime_v01.png | 道具（透明；193×470） | 燈籠店門口 | 風鈴：淺色玻璃鈴、舌、淺橙紙籤（沒有字） | a0_c004（S6 輕擺） | 程式繪製（chime） | 本專案自製 | 擺幅 ≤0.13 rad、0.85 Hz 阻尼漸停 | v01 |
| assets/final/sets/workshop_a0/lamps_v01.png | 景片（透明；1984×248） | 台口 | 台口上方一串八盞還沒亮的紙燈（和題卡燈同造型：圓燈身、竹骨線、上下木蓋），下垂細繩 | a0_c005（後拉露出） | 程式繪製（lamps） | 本專案自製 | 不發光、不閃 | v01 |
| assets/final/sets/workshop_a0/memoryframe_v01.png | 畫面疊層（透明；1920×1080） | 燈籠店 | 回憶小窗：暖杏色厚紙框、手撕邊圓角窗、窗緣紙芯白邊、窗內淡暖暈 | a0_c002 | 程式繪製（memoryframe） | 本專案自製 | 收進來 1.4 秒（單向漸變一次） | v01 |
| assets/final/sets/workshop_a0/notebook_v01.png | 畫面疊層底圖（透明；900×600） | 燈籠店 | 小晴的小筆記本（攤開、格線、沒有字）；竹骨架與問號由程式逐筆畫 | a0_c004 | 程式繪製（notebook）＋app/src/sets/workshop_a0.ts 逐筆畫線 | 本專案自製 | 無文字 | v01 |
| assets/final/sets/square_a1/pillar_v01.png | 景片（透明；172×870） | 廣場 square_a1 | 畫面左側的紅磚柱子（米色柱頭柱腳） | a1_c002–a1_c004 | 程式繪製（pillar） | 本專案自製 | 邀請者的手從後面伸出（左＝危險方位） | v01 |
| assets/final/sets/square_a1/garland_v01.png | 景片（透明；1500×150） | 廣場 | 騎樓下的小燈籠串（白天、未點亮、粉彩） | a1 全段 | 程式繪製（garland） | 本專案自製 | — | v01 |
| assets/final/sets/square_a1/townsfolk_v01.png | 景片（透明；780×390） | 廣場遠景 | 布置燈節的鎮民剪影三人（梯子掛燈籠、竿子挑燈籠、抱一箱燈籠）；淡暖灰平塗（引擎自發光 0.5，像隔著一層空氣）、沒有五官、沒有年齡族群標記 | a1 大全景右後方（遠景） | 程式繪製（townsfolk） | 本專案自製 | 中性設計（安全界線第 10 條） | v01 |
| assets/final/sets/square_a1/wrapper_v01.png | 道具（透明；800×550，1000 px／單位） | 廣場 | 被風吹來的撕破包裝紙（貼紙花紋＝盒子同色系）＋撕口白色紙背＋一團灰色紙線（淺灰繩身＋深灰邊，同操偶線紙繩配色） | a1_c008（推近特寫） | 程式繪製（wrapper） | 本專案自製 | 沒有煙、沒有器具；台詞稱「一團細細的線」 | v01 |
| assets/final/sets/square_a1/shopwindow_v01.png | 景片（透明；375×382） | 廣場騎樓 | 騎樓下燈籠店的窗：木窗框、格子窗洞（挖空）、窗台、只有燈籠圖示的小招牌 | a1 全段（窗內剪影只在 a1_c008） | 程式繪製（shopwindow） | 本專案自製 | 無文字 | v01 |
| assets/final/sets/square_a1/windowpaper_v01.png | 景片（不透明；360×330） | 廣場騎樓 | 窗紙（暖色，屋裡點著燈；引擎自發光 0.75） | a1 全段 | 程式繪製（windowpaper） | 本專案自製 | — | v01 |
| assets/final/sets/square_a1/silbody_v01.png、silarm_v01.png、silbamboo_v01.png | 剪影（半透明柔邊；481×857、300×300、60×520） | 窗內阿樂叔叔（FX10） | 上半身剪影（取自 assets/generated/chr-ale_master_v02.png 的外形，填暖深褐、柔化）、可轉動的右臂、竹篾；**沒有操偶線** | a1_c008 | 程式加工（silhouettes）；外形來源為本專案母版 | 本專案自製 | 隔一層半透明窗紙；手往旁一歪 0.45 秒、竹篾 0.7 秒落下（S7） | v01 |
| assets/final/sets/square_a1/boxclose_v01.png | 特寫小窗圖（透明；616×533） | 邀請者的貼紙盒 | 盒子特寫：貼紙一層蓋一層、邊角翹起、一小截灰色線頭、沒有任何說明 | a1_c003（找找看 1）、a1_c004 開頭收起 | assets/final/props/prop-sticker-box_v01.png（G5 共用美術）只把透明處的雜色清掉、透明度二值化 | 使用者 ChatGPT 方案生成（同來源圖） | 無真實產品外形、品牌、卡通角色；固定反光不閃 | v01 |
| assets/final/chr-xiaoyu_pose-standwatch_v01.png | 表演姿勢圖（透明；528×1446） | xiaoyu | standwatch：v04 母版站姿＋左腕兒童手錶（深藍錶帶、淺色錶面、只有四個圓點，沒有字）；透明度與母版完全相同，臉部沿用 xiaoyu:stand 退路換片 | a0_c004 起全段（伏筆）、a1 | 程式加工 chr-xiaoyu_master_v04.png（build_a01_art.py xiaoyu_watch） | 同母版 | 引擎：退路換片（同站姿） | v01 |
| assets/final/chr-pinan_pose-sit-lantern-back_v01.png | 表演姿勢圖（透明；597×1454） | pinan | sit_lantern_back：P-PA1 坐長椅綁燈籠的左右鏡像（a1_c004「偷偷回頭看柱子」翻面；臉部沒有換片，這個姿勢不說話） | a1_c004 結尾、Q1 題卡、—— | 程式加工 chr-pinan_pose-sit-lantern_v01.png（左右鏡像） | 同來源圖 | 引擎：臉部「無」（不說話、只停 2–3 秒＋題卡背景） | v01 |
| assets/final/chr-xiaoqing_pose-walkl_v01.png | 表演姿勢圖（透明；880×1448） | xiaoqing | walk_l：走路姿勢的左右鏡像（往畫面左走；星星髮夾回到和站姿同一側；臉部沒有換片，只在走進來的 2–3 秒用） | a0_c004、a1_c001 | 程式加工 chr-xiaoqing_pose-walk_v06.png（左右鏡像） | 同來源圖 | 引擎：臉部「無」 | v01 |

另外沿用、沒有新增檔案但第一次在引擎裡用到：`props/prop-bench`（長椅）、`chr-inviter_hand-box`（邀請者的手）、`sets/square/*`（layout.json：天空加寬到 32、遠山加寬到 30 並下移、地面往前延伸到 z=10，站位與地標不變）。小宇往右走用 a2 代理新增的 `walk_r`（chr-xiaoyu_pose-walk-r_v01.png）。

希望額度恢復後重抽（主線決定）：提示詞與用途寫在製作代理回報的 handoff（設計圖、包裝紙、燈籠店窗、鎮民剪影；換圖不改位置與尺寸）。

### 來源：review/G5/a2/ASSETS_rows.md

# 第二幕（a2）新素材：資產表列（給主線併入 ASSETS.md）

2026-10-21 第 2 天下午，a2 代理。Codex image_gen 額度用完（約 19:50 恢復），本段新圖全部是程式繪製退路版：`review/G5/a2/scripts/build_a2_art.py`（Pillow＋G5 共用美術 paperdraw.py 的 G2 同款紙紋、暖深灰細線、無陰影無方向光）。圖裡沒有任何文字、數字、標誌、紅十字、真實品牌或物流配色；求助站用手捧愛心圖示（同葉護理師識別證）。重抽提示寫在回報的 handoff。

| 檔名 | 類型 | 角色／場景 | 部件／表情 | 使用 cue | 來源／生成參考 | 授權 | 檢視結果 | 版本 |
|---|---|---|---|---|---|---|---|---|
| assets/final/chr-xiaoyu_pose-walk-r_v01.png | 表演姿勢圖（透明；850×1496） | xiaoyu | walk_r：`chr-xiaoyu_pose-walk_v06` 左右翻轉。名冊 facing:-1 時引擎再翻一次，畫面上就是原圖往畫面右走（小宇在 a2 一直面向左看阿樂叔叔，往右走時才不必換 facing） | a2_c001、a2_c012 | 程式（PIL ImageOps.mirror）；show_characters.json 新增 `xiaoyu.poses.walk_r` 與 `fallbackFaces["xiaoyu:walk_r"]`（眼框、嘴框依原圖鏡射） | 衍生自使用者 ChatGPT 方案生成圖 | 引擎擷取 review/G5/a2/pack/capture/keyframes（a2_c001、a2_c012）；翻面前後同一張原圖，不會左右跳 | v01 |
| assets/final/sets/a2_memory/mem-box_v01.png | 景片（透明毛邊紙卡；1040×800） | a2_memory | 褪色回想小窗①：廣場地磚上的貼紙盒（a1_c003 的盒子） | a2_c003 | 程式：props/prop-sticker-box_v01 合成到程式畫的地磚上，降彩、偏暖（回憶）、米白毛邊紙框 | 衍生自使用者 ChatGPT 方案生成圖＋程式繪製 | 無文字；盒子只是俗豔貼紙層，沒有真實產品外形 | v01 |
| assets/final/sets/a2_memory/mem-wrapper_v01.png | 景片（透明毛邊紙卡；1040×800） | a2_memory | 褪色回想小窗②：撕破的包裝紙（盒子貼紙紋）與撕口裡一團灰色紙線（a1_c008） | a2_c003 | 程式：取 prop-sticker-box 的貼紙紋裁成撕紙形、白色紙芯邊；灰線用操偶線同色（淡灰身＋深灰邊） | 同上 | 無文字；不出現打開或使用 | v01 |
| assets/final/sets/a2_memory/layout.json | 景設定 | a2_memory | 燈籠店背牆（bg-workshop-back）、地板、兩張回想紙卡；鏡位 a2_memory_cu | a2_c003 | 手寫；小窗開合與翻面在 app/src/sets/a2_memory.ts | — | — | — |
| assets/final/sets/a2_helpdesk/tent_v01.png | 景片（透明；1011×858） | a2_helpdesk | 廣場另一頭正在搭的求助站：鼠尾草綠三角篷、米白扇形垂邊、圓牌手捧愛心圖示（暖珊瑚色，不是飽和紅）、白桌布長桌、水杯、毛巾籃 | a2_c012 | 程式繪製 | 程式繪製（本專案） | 無紅十字、無文字 | v01 |
| assets/final/sets/a2_helpdesk/crate_v01.png | 道具景片（透明；220×176） | a2_helpdesk | 紙箱 | a2_c012 | 程式繪製 | 程式繪製（本專案） | — | v01 |
| assets/final/sets/a2_helpdesk/layout.json | 景設定 | a2_helpdesk | 天空、遠山、後排騎樓、行道樹、花台沿用 sets/square；帳篷、紙箱；鏡位 a2_help_mid | a2_c012 | 手寫 | — | — | — |
| assets/final/sets/a2_window/sky_v01.png | 背牆（1600×760） | a2_window | 傍晚天空：淡紫→粉紫→暖杏漸層＋幾片剪紙雲 | a2_c013 | 程式繪製；cue 內 7 秒由暖轉淡紫（a2_window.ts，FX11） | 程式繪製（本專案） | — | v01 |
| assets/final/sets/a2_window/facade_v01.png | 景片（透明；2400×1240） | a2_window | 燈籠店店面：瓦簷、一排紙燈籠（沒點亮）、左邊大窗（挖空）、右邊木門、門口石階、盆栽 | a2_c013 | 程式繪製 | 程式繪製（本專案） | 無招牌、無文字 | v01 |
| assets/final/sets/a2_window/interior_v01.png | 景片（1200×800） | a2_window | 窗裡的店內暖牆、木架上的燈籠 | a2_c013 | 程式繪製（引擎另給暖色自發光，不套傍晚紫色分級） | 程式繪製（本專案） | — | v01 |
| assets/final/sets/a2_window/stool_v01.png | 道具景片（透明；198×215） | a2_window | 阿樂叔叔坐的圓凳（同 G4 燈籠店的凳子造型） | a2_c013 | 程式繪製 | 程式繪製（本專案） | — | v01 |
| assets/final/sets/a2_window/glass_v01.png | 半透明景片（64×64） | a2_window | 窗玻璃淡暖色（opacity 0.12） | a2_c013 | 程式 | 程式繪製（本專案） | — | v01 |
| assets/final/sets/a2_window/sil-frame_v01.png | 景片（透明毛邊；1000×720） | a2_window | 剪影回憶小窗的背光紙框（中間亮、四周暖暗） | a2_c013 | 程式繪製；小窗內容由 a2_window.ts 畫在 canvas 上（裁在框內） | 程式繪製（本專案） | — | v01 |
| assets/final/sets/a2_window/sil-hand-box_v01.png | 剪影（透明；866×377） | a2_window | 邀請者的手捧盒子（剪影，看不到膚色與衣著；中性） | a2_c013 | 程式：chr-inviter_hand-box_v01 的外形填暖深褐 | 衍生自使用者 ChatGPT 方案生成圖 | 剪影，不出現打開或使用 | v01 |
| assets/final/sets/a2_window/sil-ale-hand_v01.png | 剪影（透明；243×311） | a2_window | 阿樂叔叔伸出去的前臂與手（剪影） | a2_c013 | 程式：rig/chr-ale_forearm-l_v05＋chr-ale_hand-l_v04 合成、旋轉、填暖深褐 | 衍生自使用者 ChatGPT 方案生成圖 | 小窗在手碰到盒子之前就收起 | v01 |
| assets/final/sets/a2_window/notebook_v01.png | 景片（1500×960） | a2_window | 小晴的筆記本：淡格線（無字）、左頁燈籠竹骨架速寫、右頁一個鉛筆問號；第二個問號與鉛筆由 a2_window.ts 程式畫 | a2_c013 | 程式繪製 | 程式繪製（本專案） | 只有問號符號，沒有文字；和 a0 的筆記本特寫要由主線統一樣式 | v01 |
| assets/final/sets/a2_window/layout.json | 景設定 | a2_window | 天空、後排騎樓、店內暖牆、工作台（bg-workshop-table）、圓凳、店面、窗玻璃；鏡位 a2_win_wide／a2_win_kids／a2_win_note | a2_c013 | 手寫；天色漸變、剪影小窗、筆記本在 app/src/sets/a2_window.ts | — | — | — |

### 來源：review/G5/a4/ASSETS_rows.md

# 第四幕（a4）新素材：資產表列（給主線併入 ASSETS.md）

2026-10-21，G5 第四幕代理。Codex image_gen 額度用完（約 19:50 恢復），全部用 Pillow＋G2 同款紙紋程式繪製（review/G5/a4/scripts/build_a4_art.py，借用 review/G5/shared_art/scripts/paperdraw.py 的畫法；可重跑）。圖裡沒有任何文字、數字、品牌、標誌、紅十字；車子是通用小車、路人與剪影是通用人形。show_characters.json 只新增 chen.poses.receive、lin.poses.standr 與對應的 fallbackFaces（chen:receive、lin:standr，眼嘴範圍由母版平移／鏡射）。

| 檔名 | 類型 | 角色／場景 | 部件／表情 | 使用 cue | 來源／生成參考 | 授權 | 檢視結果 | 版本 |
|---|---|---|---|---|---|---|---|---|
| assets/final/sets/a4_roadmap/set-a4map_map_v01.png | 景片（俯視地圖，不透明）；3240×1620 | a4_roadmap（紙上的路） | 牛皮紙地圖：主路＋支路、人行道與行道樹、斑馬線、停止線、公園水池、校園花圃與球場線、右下屋頂、3×2 摺痕、紙星指北（無字母） | a4_c002（後半，gate 景也用同一張淡入）–a4_c008（前半） | 程式繪製（review/G5/a4/scripts/build_a4_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a4/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a4_roadmap/set-a4map_house-a_v01.png | 立體書小屋（透明，白邊）；420×343 | a4_roadmap | 平房：赤陶屋頂 | 同上 | 程式繪製（review/G5/a4/scripts/build_a4_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a4/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a4_roadmap/set-a4map_house-b_v01.png | 立體書小屋（透明，白邊）；420×409 | a4_roadmap | 二樓透天：灰綠屋頂 | 同上 | 程式繪製（review/G5/a4/scripts/build_a4_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a4/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a4_roadmap/set-a4map_house-c_v01.png | 立體書小屋（透明，白邊）；464×321 | a4_roadmap | 小店：素色遮雨棚（不放招牌字） | 同上 | 程式繪製（review/G5/a4/scripts/build_a4_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a4/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a4_roadmap/set-a4map_house-d_v01.png | 立體書小屋（透明，白邊）；376×354 | a4_roadmap | 兩層小屋：石板灰屋頂 | 同上 | 程式繪製（review/G5/a4/scripts/build_a4_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a4/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a4_roadmap/set-a4map_school_v01.png | 立體書景片（透明，白邊）；1035×453 | a4_roadmap | 地圖上的學校（無校徽、無字） | 同上 | 程式繪製（review/G5/a4/scripts/build_a4_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a4/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a4_roadmap/set-a4map_gatepost_v01.png | 立體書景片（透明，白邊）；88×209 | a4_roadmap | 地圖上的校門柱 | 同上 | 程式繪製（review/G5/a4/scripts/build_a4_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a4/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a4_roadmap/set-a4map_tree_v01.png | 立體書景片（透明，白邊）；231×297 | a4_roadmap | 圓樹 | 同上 | 程式繪製（review/G5/a4/scripts/build_a4_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a4/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a4_roadmap/set-a4map_walker_v01.png | 立體書小人（透明，白邊）；192×368 | a4_roadmap | 斑馬線上背書包的路人（背影、往學校走；通用人形） | a4_c002–a4_c004、a4_c008 | 程式繪製（review/G5/a4/scripts/build_a4_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a4/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a4_roadmap/set-a4map_car_v01.png | 道具（俯視，透明，白邊）；344×203 | a4_roadmap | 紙剪小車：通用小車、灰綠色、無標誌（不是阿樂叔叔的小貨車） | a4_c002–a4_c008 | 程式繪製（review/G5/a4/scripts/build_a4_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a4/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a4_roadmap/set-a4map_screen_v01.png | 剪影幕（不透明）；2200×1040 | a4_roadmap | 背光紙幕：暖米色、中央亮四周暗、背光下紙纖維較明顯、牛皮紙摺邊框 | a4_c004–a4_c008（FX10） | 程式繪製（review/G5/a4/scripts/build_a4_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a4/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a4_roadmap/set-a4map_sil-ground_v01.png | 剪影（透明）；2132×124 | a4_roadmap | 地面剪影：路面＋路緣，右段斑馬線用亮縫表示 | 同上 | 程式繪製（review/G5/a4/scripts/build_a4_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a4/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a4_roadmap/set-a4map_sil-car_v01.png | 剪影（透明）；680×324 | a4_roadmap | 車子側面剪影（車頭朝右）：前窗駕駛（雙手握方向盤）、後窗乘客；窗挖空透出背光 | 同上 | 程式繪製（review/G5/a4/scripts/build_a4_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a4/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a4_roadmap/set-a4map_sil-walker_v01.png | 剪影（透明）；190×390 | a4_roadmap | 背書包的路人側面剪影（往右走） | 同上 | 程式繪製（review/G5/a4/scripts/build_a4_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a4/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/gate/set-gate_a4-key_v01.png | 道具（透明，白邊）；424×244 | gate（校門口） | 車鑰匙：圓環鑰匙頭、鑰匙齒、灰色鑰匙圈、青綠小紙牌（無字）；跟著阿樂叔叔／陳伯伯的手 | a4_c001、a4_c002、a4_c008–a4_c011、a4_c013 | 程式繪製（review/G5/a4/scripts/build_a4_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a4/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/gate/set-gate_a4-flag_v01.png | 道具（透明，白邊）；336×544 | gate | 導護旗：黃綠色小旗（無字、無圖案）＋竹柄；陳伯伯另一手拿著 | a4_c001、a4_c012、a4_c013 | 程式繪製（review/G5/a4/scripts/build_a4_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a4/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/gate/set-gate_a4-phone_v01.png | 道具（透明，白邊）；152×262 | gate | 林老師的手機：深灰圓角、螢幕淡灰沒有內容 | a4_c012、a4_c013 | 程式繪製（review/G5/a4/scripts/build_a4_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a4/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/gate/set-gate_a4-lin-back_v01.png | 景片（透明，白邊）；307×352 | gate | 警衛室窗內林老師的小背影：低髮髻、酒紅開襟衫、拿手機貼耳（看不到臉） | a4_c001 | 程式繪製（review/G5/a4/scripts/build_a4_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a4/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/gate/set-gate_a4-lantern_v01.png | 景片（透明）；138×300 | gate | 騎樓下的小紙燈籠（暖米橘、低彩度、不發光）＋吊繩 | gate 景常駐；a4_c008 風吹擺動 | 程式繪製（review/G5/a4/scripts/build_a4_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a4/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/gate/set-gate_a4-walkers-a_v01.png | 遠景剪影（透明）；221×403 | gate | 家長牽孩子離開（灰藍平塗剪影、沒有五官、大人提袋） | a4_c001 | 程式繪製（review/G5/a4/scripts/build_a4_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a4/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/gate/set-gate_a4-walkers-b_v01.png | 遠景剪影（透明）；221×403 | gate | 家長牽孩子離開（灰綠平塗剪影、沒有五官） | a4_c001、a4_c008 | 程式繪製（review/G5/a4/scripts/build_a4_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a4/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/chr-chen_pose-receive_v01.png | 表演姿勢圖（透明）；819×1522 | chen | receive：伸手接鑰匙——畫面左側（他的右手）整段手臂以袖口下為軸往外轉 38°（轉軸藏在袖子後面）；頭臉、身體與 chr-chen_master_v01 相同；往左加寬 170 px | a4_c013 | 由 assets/final/chr-chen_master_v01.png 改畫前臂（build_a4_art.py chen_receive） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a4/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/chr-lin_pose-standr_v01.png | 表演姿勢圖（透明）；456×1546 | lin | standr：林老師站姿左右鏡射（臉朝畫面右）——說完話轉身走進辦公室前紙片翻面用 | a4_c013 | assets/final/chr-lin_master_v01.png 左右鏡射（build_a4_art.py lin_standr） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a4/pack/）；投影與聽感依驗收包 | v01 |

另：assets/final/sets/gate/layout.json 改兩處擺位（第四幕代理）：sq-tree-a 由 x −4.9 移到 −10.4（原位置擋住對面小貨車駕駛座與阿樂叔叔）；prop-bench 由 x −3.2 移到 −2.3（整張長椅在人行道上、不擋住車旁的阿樂叔叔），benchSeat 地標、marks.ale、gate_bench 鏡位同步更新。小貨車、警衛室、接送線、貓耳地標都沒動。

### 來源：review/G5/audio/ASSETS_rows.md

# G5 配樂與音效｜ASSETS.md 待合併列（主線合併）

放在 ASSETS.md「配樂與音效」表下面（同欄位）。重建：`caffeinate -i tools/.venv/bin/python tools/music/build_all.py`；量測：review/G5/audio/metrics.json；對點：review/G5/audio/CUES.md；圖：review/G5/audio/waveforms_music.png、waveforms_sfx.png。聽感全部未驗證。

| 檔名 | 類型 | 角色／場景 | 部件 | 使用 cue | 來源 | 授權 | 檢視結果 | 版本 |
|---|---|---|---|---|---|---|---|---|
| audio/music/music_zhezhe_v02.wav | 配樂（無縫循環 16.0 s） | 折折 | M2 折折動機（短句 0–4 s＋循環底） | a0_c002、a0_c004、a3_c001、a7_c001 | 自製（程式作曲）＋FluidR3_GM 音色庫（MIT）；tools/music/compose.py | 原創；音色庫 MIT（audio/LICENSES/FluidR3_GM_copyright.txt） | -24.0 LUFS、-6.6 dBTP；100 ms 最大跳升 5.7 dB；接縫樣本差 42 LSB；聽感未驗證 | v02（G5 正式版；v01 主線佔位保留） |
| audio/music/music_shiny_v02.wav | 配樂（無縫循環 15.0 s） | 閃亮盒子 | M3 閃亮動機（音樂盒圓舞曲、增三和弦；最低音 C4、高通 200 Hz） | a1_c002–a1_c003、a2_c003、a2_c013、a3_c001 | 自製（程式作曲）＋FluidR3_GM 音色庫（MIT）；tools/music/compose.py | 原創；音色庫 MIT（audio/LICENSES/FluidR3_GM_copyright.txt） | -24.0 LUFS、-11.1 dBTP；100 ms 最大跳升 3.5 dB；接縫樣本差 125 LSB；聽感未驗證 | v02（G5 正式版；v01 主線佔位保留） |
| audio/music/music_road_v02.wav | 配樂（無縫循環 20.0 s） | 紙上的路 | M5（木塊 3+3+2，不是時鐘滴答、不像警報） | a4_c002、a4_c003、a4_c008 | 自製（程式作曲）＋FluidR3_GM 音色庫（MIT）；tools/music/compose.py | 原創；音色庫 MIT（audio/LICENSES/FluidR3_GM_copyright.txt） | -24.0 LUFS、-10.6 dBTP；100 ms 最大跳升 3.0 dB；接縫樣本差 42 LSB；聽感未驗證 | v02（G5 正式版；v01 主線佔位保留） |
| audio/music/music_road_hold_v01.wav | 配樂（無縫循環 16.0 s） | 背光剪影 | M5 長音（加做、可選） | a4_c004 | 自製（程式作曲）＋FluidR3_GM 音色庫（MIT）；tools/music/compose.py | 原創；音色庫 MIT（audio/LICENSES/FluidR3_GM_copyright.txt） | -24.0 LUFS、-13.4 dBTP；100 ms 最大跳升 0.8 dB；接縫樣本差 149 LSB；聽感未驗證 | v01（G5 正式版；加做） |
| audio/music/music_courage_v02.wav | 配樂（無縫循環 30.0 s） | 拒絕、找大人 | M6 勇氣動機（M1 上行變奏） | a1_c004、a2_c012、a3_c002、a3_c004、a4_c012、a5_c005–a5_c007、a6_c006、a7_c002 | 自製（程式作曲）＋FluidR3_GM 音色庫（MIT）；tools/music/compose.py | 原創；音色庫 MIT（audio/LICENSES/FluidR3_GM_copyright.txt） | -24.0 LUFS、-10.6 dBTP；100 ms 最大跳升 5.8 dB；接縫樣本差 26 LSB；聽感未驗證 | v02（G5 正式版；v01 主線佔位保留） |
| audio/music/music_recovery_v02.wav | 配樂（無縫循環 24.0 s＝四季一輪） | 醫院走廊、四季 | M7 復原動機（M1 慢版鋼琴＋弦） | a5_c008、a6_c008、a6_c009 | 自製（程式作曲）＋FluidR3_GM 音色庫（MIT）；tools/music/compose.py | 原創；音色庫 MIT（audio/LICENSES/FluidR3_GM_copyright.txt） | -24.0 LUFS、-11.0 dBTP；100 ms 最大跳升 2.0 dB；接縫樣本差 180 LSB；聽感未驗證 | v02（G5 正式版；v01 主線佔位保留） |
| audio/music/music_town_night_v02.wav | 配樂（無縫循環 30.0 s） | 燈節夜晚廣場 | M1 夜晚版 | a6_c001、a6_c002 | 自製（程式作曲）＋FluidR3_GM 音色庫（MIT）；tools/music/compose.py | 原創；音色庫 MIT（audio/LICENSES/FluidR3_GM_copyright.txt） | -24.0 LUFS、-12.0 dBTP；100 ms 最大跳升 1.9 dB；接縫樣本差 17 LSB；聽感未驗證 | v02（G5 正式版；v01 主線佔位保留） |
| audio/music/music_bows_v02.wav | 配樂（一次播完 18.0 s） | 謝幕 | M1 謝幕版（7 組鞠躬對小節頭 1／3／…／13 s，15.0 s 最後和弦） | a8_c001 | 自製（程式作曲）＋FluidR3_GM 音色庫（MIT）；tools/music/compose.py | 原創；音色庫 MIT（audio/LICENSES/FluidR3_GM_copyright.txt） | -20.0 LUFS、-7.6 dBTP；100 ms 最大跳升 4.2 dB；檔尾 10 ms 峰值 -90.3 dBFS；聽感未驗證 | v02（G5 正式版；v01 主線佔位保留） |
| audio/sfx/sfx_windchime_v01.wav | 音效（4.2 s，單聲道） | 燈籠店門 | S6 風鈴 | a0_c004 | 自製（程式合成）；tools/music/sfx.py | 原創 | 最大瞬間 -24.0 LUFS、峰值 -14.9 dBFS、-14.9 dBTP；起音 97.6 ms；聽感未驗證 | v01（G5 原地覆寫紙張摩擦佔位） |
| audio/sfx/sfx_bamboo_drop_v01.wav | 音效（1.0 s，單聲道） | 窗內剪影 | S7 竹篾輕落地 | a1_c008 | 自製（程式合成）；tools/music/sfx.py | 原創 | 最大瞬間 -28.0 LUFS、峰值 -12.0 dBFS、-12.0 dBTP；起音 6.0 ms；聽感未驗證 | v01（G5 原地覆寫紙張摩擦佔位） |
| audio/sfx/sfx_wind_v01.wav | 音效（30.0 s，單聲道） | 廣場、校門口 | S8 風聲（無縫循環 30.0 s，3.0 s 一陣風） | a1_c008、a5_c001、a5_c005 | 自製（程式合成）；tools/music/sfx.py | 原創 | 整合 -30.0 LUFS、峰值 -14.0 dBFS、-14.0 dBTP；接縫樣本差 12 LSB；聽感未驗證 | v01（G5 原地覆寫紙張摩擦佔位） |
| audio/sfx/sfx_school_bell_v01.wav | 音效（7.0 s，單聲道） | 教室 | S9 下課鐘（柔；西敏寺鐘聲前兩句，公有領域旋律） | a3_c008 | 自製（程式合成）；tools/music/sfx.py | 原創 | 最大瞬間 -24.0 LUFS、峰值 -14.1 dBFS、-14.1 dBTP；起音 605.3 ms；聽感未驗證 | v01（G5 原地覆寫紙張摩擦佔位） |
| audio/sfx/sfx_gate_ambience_v01.wav | 音效（40.0 s，單聲道） | 校門口 | S10 校門口環境聲（無縫循環 40.0 s；人聲只有母音、聽不出字） | a3_c003、a4_c001、a4_c008 | 自製（程式合成）；tools/music/sfx.py | 原創 | 整合 -36.0 LUFS、峰值 -19.6 dBFS、-19.6 dBTP；接縫樣本差 4 LSB；聽感未驗證 | v01（G5 原地覆寫紙張摩擦佔位） |
| audio/sfx/sfx_watch_dial_v01.wav | 音效（2.2 s，單聲道） | 校門口 | S11 兒童手錶撥號音（輕；不是 DTMF） | a5_c005／a5_c006 | 自製（程式合成）；tools/music/sfx.py | 原創 | 最大瞬間 -28.0 LUFS、峰值 -18.2 dBFS、-18.2 dBTP；起音 6.2 ms；聽感未驗證 | v01（G5 原地覆寫紙張摩擦佔位） |
| audio/sfx/sfx_phone_bed_v01.wav | 音效（40.0 s，單聲道） | 119 通話 | S12 電話音色底音（無縫循環 40.0 s；沒有電信撥號／回鈴音） | a5_c006 | 自製（程式合成）；tools/music/sfx.py | 原創 | 整合 -38.0 LUFS、峰值 -24.5 dBFS、-24.5 dBTP；接縫樣本差 7 LSB；聽感未驗證 | v01（G5 原地覆寫紙張摩擦佔位） |
| audio/sfx/sfx_ambulance_engine_v01.wav | 音效（16.0 s，單聲道） | 校門口 | S13 救護車引擎聲（無警笛、喇叭、煞車尖響） | a5_c007 | 自製（程式合成）；tools/music/sfx.py | 原創 | 最大瞬間 -24.0 LUFS、峰值 -16.2 dBFS、-16.2 dBTP；起音 5369.9 ms；聽感未驗證 | v01（G5 原地覆寫紙張摩擦佔位） |
| audio/sfx/sfx_plane_whoosh_v01.wav | 音效（1.6 s，單聲道） | 騎樓、校門口 | S14 紙飛機咻聲（輕） | a3_c001、a4_c002 | 自製（程式合成）；tools/music/sfx.py | 原創 | 最大瞬間 -26.0 LUFS、峰值 -15.5 dBFS、-15.5 dBTP；起音 387.0 ms；聽感未驗證 | v01（G5 原地覆寫紙張摩擦佔位） |
| audio/sfx/sfx_crowd_far_v01.wav | 音效（40.0 s，單聲道） | 廣場 | S15 廣場人聲遠景（無縫循環 40.0 s；聽不出字） | a1_c001、a6_c001 | 自製（程式合成）；tools/music/sfx.py | 原創 | 整合 -34.0 LUFS、峰值 -18.4 dBFS、-18.4 dBTP；接縫樣本差 12 LSB；聽感未驗證 | v01（G5 原地覆寫紙張摩擦佔位） |
| audio/sfx/sfx_footsteps_v01.wav | 音效（4.0 s，單聲道） | 通用 | S16 紙偶腳步（8 步、每步 0.5 s） | 走路往右的 cue | 自製（程式合成）；tools/music/sfx.py | 原創 | 最大瞬間 -31.0 LUFS、峰值 -12.0 dBFS、-12.0 dBTP；起音 7.0 ms；聽感未驗證 | v01（G5 原地覆寫紙張摩擦佔位） |

另：`audio/sfx/_placeholders.txt` 已清空（11 個音效與 music_town_night 都有正式檔）。

## G5 修正第 1 輪與第二批（主線 2026-10-22 06:0x 合併）

### 來源：review/G5/engine/ASSETS_rows_fix1.md

# G5 修正第 1 輪｜共用元件代理｜ASSETS.md 待合併列（主線合併）

| 檔名 | 類型 | 角色／場景 | 部件 | 使用 cue | 來源 | 授權 | 檢視結果 | 版本 |
|---|---|---|---|---|---|---|---|---|
| assets/final/ui/ui-speaker_{zhezhe,pinan,nurse,teacher,guard,inviter}_v01.png | 字幕說話者小頭像（128×128 透明圓形徽章） | 折折、品安、葉護理師、林老師、陳伯伯、邀請者 | 折折＝從折折程式畫面（review/G5/zhezhe/look.png）裁頭部；品安、葉護理師、林老師、陳伯伯＝從正式母版 chr-*_master_v01.png 裁頭肩；邀請者＝中性灰紙手掌（程式畫，沒有臉、膚色、飾品） | 全劇字幕（v1.2 第 15.3 節；b1_art a2 一般問題 5） | review/G5/engine/scripts/make_speaker_icons_fix1.py（沿用 G4 make_speaker_icons.py 的徽章） | 原創（程式產生）／使用者 ChatGPT 方案生成（母版裁切） | 圖中無字；字幕框深底上與投影 v2 都清楚（review/G5/engine/art/speaker_icons_fix1.png） | v01 |
| app/src/stage/lamps.ts（程式繪製，沒有圖檔） | 台口八盞燈（剪紙紙燈＋木條＋柔和光暈） | 全劇台口 | 未亮灰白紙色＋深棕細邊；亮＝暖黃＋加法光暈 | 全劇（quiz 鏡位看得到） | 程式繪製（canvas） | 原創 | quiz 鏡位 1080p y≈13–90 px、寬約畫面 60%；只隨 world.lamps 單向漸變 | — |

### 來源：review/G5/audio/ASSETS_rows_fix1.md

# G5 修正第 1 輪｜短音效（佔位檔換正式）｜ASSETS.md 待合併列（主線合併）

放在 ASSETS.md「配樂與音效」表下面（同欄位）。原檔名原地覆寫 audio/sfx/_placeholders.txt 列的四個佔位檔（之前是 1.3 秒紙張摩擦的複本），做完已清空 _placeholders.txt。
重建：`caffeinate -i tools/.venv/bin/python tools/music/build_all.py --only sfx_gust,sfx_phone_noanswer,sfx_truck_arrive,sfx_crowd_short`；
量測：review/G5/audio/metrics.json（44 檔，其他 40 檔數值不變）；圖：review/G5/audio/waveforms_sfx.png。規格照 G3／G5：樣本峰值、最大瞬間響度個別上限（sfx.py SFX_LEVEL）、真峰值 ≤ −2 dBTP、起音 ≥ 5 ms、6 kHz 以上能量很低、沒有突發巨響。聽感全部未驗證（Claude 聽不到音訊）。

| 檔名 | 類型 | 角色／場景 | 部件 | 使用 cue | 來源 | 授權 | 檢視結果 | 版本 |
|---|---|---|---|---|---|---|---|---|
| audio/sfx/sfx_gust_v01.wav | 音效（2.6 s，單聲道） | 廣場、校門口 | S17 一陣風（1.0 s 最強、最後 0.6 s 退去；不呼嘯、低通 4.5 kHz） | 目前沒有 cue 使用（各幕可用） | 自製（程式合成）；tools/music/sfx.py | 原創 | 最大瞬間 -28.0 LUFS、峰值 -17.0 dBFS、-17.0 dBTP；起音 558.6 ms；100 ms 最大跳升 10.4 dB；聽感未驗證 | v01（G5 修正第 1 輪原地覆寫佔位） |
| audio/sfx/sfx_phone_noanswer_v01.wav | 音效（2.6 s，單聲道） | 求助站（葉護理師打電話） | S18 撥號沒人接（兩聲柔和鈴 520／650 Hz＋14 Hz 顫音，0.05／1.35 s 各 0.8 s；電話線音色；不用真實電信業者的回鈴音、撥號音、忙線音） | a2_c012 | 自製（程式合成）；tools/music/sfx.py | 原創 | 最大瞬間 -28.0 LUFS、峰值 -19.4 dBFS、-19.4 dBTP；起音 17.8 ms；100 ms 最大跳升 21.4 dB（從靜音到 -28 LUFS 的輕鈴）；聽感未驗證 | v01（G5 修正第 1 輪原地覆寫佔位） |
| audio/sfx/sfx_truck_arrive_v01.wav | 音效（5.0 s，單聲道） | 校門口（阿樂叔叔的小貨車） | S19 小貨車輕聲開近、停下、怠速（0–3.0 s 開近、3.0–3.6 s 停、3.6–5.0 s 怠速；不按喇叭、沒有煞車尖響） | a4_c001 | 自製（程式合成）；tools/music/sfx.py | 原創 | 最大瞬間 -27.0 LUFS、峰值 -17.1 dBFS、-17.1 dBTP；起音 1509.7 ms；100 ms 最大跳升 3.5 dB；聽感未驗證 | v01（G5 修正第 1 輪原地覆寫佔位） |
| audio/sfx/sfx_crowd_short_v01.wav | 音效（4.0 s，單聲道） | 廣場 | S20 廣場人聲短版（約 10 個聲音只有母音、低通 2.2 kHz、殘響推遠，聽不出任何字；0.6 s 淡入、最後 0.8 s 淡出） | a2_c012 | 自製（程式合成）；tools/music/sfx.py | 原創 | 最大瞬間 -30.0 LUFS、峰值 -18.8 dBFS、-18.8 dBTP；起音 645.4 ms；100 ms 最大跳升 5.3 dB；聽感未驗證 | v01（G5 修正第 1 輪原地覆寫佔位） |

### 來源：review/G5/a3/ASSETS_rows.md

# 第三幕（a3）新素材：資產表列（給主線併進 ASSETS.md）

2026-10-21 第 2 天晚上，G5 第三幕代理（第二批）。Codex image_gen 只用在角色新姿勢 3 張（上限 4，沒有重抽；紀錄 `review/G5/a3/codex_log.md`）；景片、練習卡、回想小窗、教室全部程式繪製（Pillow＋G2 同款紙紋 `review/G5/shared_art/scripts/paperdraw.py`；腳本 `review/G5/a3/scripts/build_a3_art.py`、`build_a3_art2.py` 可重跑）。生成圖與景片裡沒有任何文字、數字、標誌、紅十字、真實品牌或物流配色；練習卡上的字是程式排版（Noto Sans TC，SIL OFL 1.1，字型檔只在建置時用，放在 `review/G5/a3/fonts/`，不隨演出打包）。

| 檔名 | 類型 | 角色／場景 | 部件／表情 | 使用 cue | 來源／生成參考 | 授權 | 檢視結果 | 版本 |
|---|---|---|---|---|---|---|---|---|
| assets/final/chr-xiaoqing_pose-pointr_v07.png（原檔 assets/generated/ 同名） | 角色姿勢（透明；883×1458） | 小晴 | 「先離開」手指向右（H2；舞台角色指向安全方向） | a3_c004（練習卡口訣第 3 個動作）；練習卡小圖 | Codex image_gen（母版 chr-xiaoqing_master_v04 為參考）；星星髮夾生成在另一側，程式搬回母版同側（scripts/fix_star.py，原位以頭髮內插補上） | 使用者 ChatGPT 方案生成 | 白邊 11 px、霧邊 0、吊帶褲 ΔE 1.8、上衣 ΔE 2.2；退路眨眼兩眼同閉通過（review/G5/a3/blink_check.json） | v07 |
| assets/final/chr-xiaoyu_pose-pointr_v07.png（原檔 assets/generated/ 同名） | 角色姿勢（透明） | 小宇（戴兒童手錶） | 「先離開」戴手錶的手指向右 | a3_c004 | Codex image_gen（母版 chr-xiaoyu_master_v04、standwatch 為參考） | 使用者 ChatGPT 方案生成 | 白邊 12 px、霧邊 0、ΔE 3.7／7.0；兩眼同閉通過 | v07 |
| assets/final/chr-xiaoyu_pose-glasses_v07.png（原檔 assets/generated/ 同名） | 角色姿勢（透明） | 小宇 | 推推眼鏡想一想（H8，臉朝畫面左） | a3_c002「等一下，我想一想」 | Codex image_gen | 使用者 ChatGPT 方案生成 | 白邊 12 px、霧邊 0、ΔE 4.2／4.7；指尖在鼻樑；退路眨眼人工量框、兩眼同閉通過 | v07 |
| assets/final/chr-xiaoqing_pose-forehead-l_v01.png | 角色姿勢（透明；665×1485） | 小晴 | chr-xiaoqing_pose-forehead_v06 左右翻轉：手放額前朝畫面左張望，星星髮夾回到母版同一側 | a3_c004（練習卡口訣第 4 個動作「找大人」） | 程式鏡射（build_a3_art.py poses） | 本專案自製（來源為本專案姿勢圖） | 和 stand／cross／palmno／pointr 同一場時髮夾不跳邊 | v01 |
| assets/final/chr-lin_pose-stand-m_v01.png | 角色姿勢（透明；456×1546） | 林老師 | 站姿左右翻轉（臉朝畫面左）；退路眼框、嘴框依 lin:stand 鏡射（show_characters.json fallbackFaces lin:stand_m） | a3_c008（站在孩子右邊跟全班說話；走出教室時翻回 stand 朝右） | 程式鏡射（build_a3_art2.py） | 本專案自製 | — | v01 |
| assets/final/sets/a3_gate/card_v01.png | 景片（透明；2400×1360，世界寬 6.0） | 台口前緣練習卡 a3_card | 攤開的大紙卡：上排拒絕句「不用，我不試。我先離開。」、下排口訣四格（不碰／不試／先離開／找大人，每格有動作小圖＋口訣） | a3_c004（1.9 秒起立起）、a3_c005 出題時收平 | 程式排版（Noto Sans TC 粗體 weight 850）；動作小圖取自本專案姿勢圖（小晴 cross、小宇 palmno、小晴 pointr、小宇 forehead）膝蓋以上 | 本專案自製；字型 SIL OFL 1.1 | 字是程式排版、不是生成；投影下字高約 45–50 px（1080p） | v01 |
| assets/final/sets/a3_arcade/memory_v01.png | 畫面疊層（透明；640×640） | 騎樓上學路 a3_arcade | 回想小圓窗：第二幕 a2_c002 結尾被操偶線拉偏的手（腕背、肘外兩個紙環、往上延伸的線），褪色、奶油色手撕紙框；**不含阿樂叔叔的臉** | a3_c002（0.8 秒打開、「我想一想」說完收起） | 程式加工：第二幕驗收包關鍵影格 review/G5/a2/pack/capture/keyframes/a2_c002_025.18_after.png 裁切（build_a3_art.py memory） | 本專案自製（來源為本專案引擎畫面） | 扣點只有腕背、肘外（同第二幕）；不恐怖、不吊掛 | v01 |
| assets/final/sets/a3_classroom/outside_v01.png | 背景（不透明；1040×360） | 教室 a3_classroom | 窗外：午後淡藍天空、雲、對面騎樓屋頂（小窗格，沒有招牌） | a3_c008 | 程式繪製（outside） | 本專案自製 | 無文字 | v01 |
| assets/final/sets/a3_classroom/backwall_v01.png | 景片（透明窗洞；2400×800，世界寬 24） | 教室 | 後牆：奶油色上牆＋鼠尾草綠護牆板、三扇十字窗（玻璃挖空）、沒有數字的時鐘、布告欄（燈籠、貓、房子三張畫，沒有字）、開著的後門 | a3_c008 | 程式繪製（backwall） | 本專案自製 | 無文字、無數字 | v01 |
| assets/final/sets/a3_classroom/board_v01.png | 景片（透明；420×224） | 教室 | 黑板（淺墨綠）＋粉筆畫燈籠、三顆星、燈籠串；**沒有字** | a3_c008 | 程式繪製（board） | 本專案自製 | 無文字 | v01 |
| assets/final/sets/a3_classroom/desk_v01.png、teacherdesk_v01.png | 道具（透明；170×125、160×155） | 教室 | 課桌椅一組；講桌（作業簿封面空白、小燈籠） | a3_c008 | 程式繪製（desk、teacherdesk） | 本專案自製 | 無文字 | v01 |
| assets/final/sets/a3_classroom/students_v02.png | 景片（透明；700×240） | 教室後排 | 同學的背影 6 人：頭髮蓋住整個後腦（背面，本來就看不到臉）、低彩度衣服、有的背書包；不透明紙片小人（取代 v01 的灰色無五官人形，主線裁定第 6 條） | a3_c008（遠景，講桌後） | 程式繪製（build_a3_art2.py students） | 本專案自製 | 中性設計：不以年齡、族群、髮色作標記 | v02 |
| assets/final/sets/a3_classroom/floor_v01.png、garland_v01.png | 地板（2048×512）；景片（透明；600×70） | 教室 | 橫向木地板；窗外燈籠串（7 盞粉彩，沿用 square_a1 燈籠串配色） | a3_c008（燈籠串週期 3.4 秒、幅度 ≤0.024 rad 輕擺） | 程式繪製（floor、garland） | 本專案自製 | 不發光、不閃 | v01 |

沿用（沒有新增檔）：sets/square/*（騎樓景，a3_arcade 拿掉長椅、改早晨色彩分級）、sets/square_a1/pillar、garland、chr-inviter_hand-box（邀請者的手）、sets/gate/*（a3_gate／a3_card 用 gate.ts 建構器，拿掉小貨車）、sets/gate/set-gate_a4-phone（林老師的手機）。

未打包的中間檔：assets/final/sets/a3_classroom/students_v01.png（被 v02 取代，pack 只取最新版本；可刪）。

### 來源：review/G5/a5/ASSETS_rows.md

# 第五幕（a5）新素材：資產表列（給主線併入 ASSETS.md）

2026-10-21，G5 第五幕代理。Codex image_gen 5 張（上限 8；review/G5/a5/codex_log.md），其餘用 Pillow＋G2 同款紙紋程式繪製（review/G5/a5/scripts/build_a5_art.py、phone_icon_v2.py，借用 review/G5/shared_art/scripts/paperdraw.py）。圖裡沒有任何文字、數字、品牌、標誌、紅十字；救護車、救護人員臂章、醫院走廊都只用自訂的「手捧愛心」圖示。show_characters.json 新增：chen.poses.standr／shoutr、xiaoqing.poses.sitb、xiaoyu.poses.sitb、characters.medic_a／medic_b，以及 fallbackFaces chen:standr、chen:shoutr、xiaoqing:sitb、xiaoyu:sitb、medic_a:stand、medic_b:stand（眼嘴範圍由圖量得；鏡射者由母版換算）。

| 檔名 | 類型 | 角色／場景 | 部件／表情 | 使用 cue | 來源／生成參考 | 授權 | 檢視結果 | 版本 |
|---|---|---|---|---|---|---|---|---|
| assets/final/sets/a5_gate/a5-corner_v01.png | 景片（透明）；286×594 | a5_gate（校門口） | 街角兩層小店（轉角柱在右緣、拉下的鐵捲門、雨遮；沒有招牌字）；陳伯伯與小朋友轉過去就被擋住 | a5_c001、a5_c005、a5_c007 | 程式繪製（review/G5/a5/scripts/build_a5_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（私人建置試拍 review/G5/a5/checks/snaps、引擎擷取 review/G5/a5/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a5_gate/a5-student_v01.png | 遠景小人（透明）；209×450 | a5_gate | 轉角的低年級小朋友：黃色小帽、深藍上衣、灰短褲、綠書包；中性、沒有五官細節（只有一點眼睛） | a5_c001 | 程式繪製（review/G5/a5/scripts/build_a5_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（私人建置試拍 review/G5/a5/checks/snaps、引擎擷取 review/G5/a5/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a5_gate/a5-student-arm_v01.png | 部件（透明）；66×136 | a5_gate | 小朋友揮手的手臂（以肩為支點擺動） | a5_c001 | 程式繪製（review/G5/a5/scripts/build_a5_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（私人建置試拍 review/G5/a5/checks/snaps、引擎擷取 review/G5/a5/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a5_gate/a5-ambulance_v01.png | 道具（透明）；840×375 | a5_gate | 救護車側面（車頭朝右）：米白車身、鼠尾草綠腰帶、車廂側面白底圓牌「手捧愛心」自訂圖示；沒有紅十字、沒有文字、沒有真實救護單位的配色與標誌；輪子另疊（借 props/prop-truck-wheel） | a5_c007 | 程式繪製（review/G5/a5/scripts/build_a5_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（私人建置試拍 review/G5/a5/checks/snaps、引擎擷取 review/G5/a5/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a5_gate/a5-ambulance-light_v01.png | 道具（透明）；330×84 | a5_gate | 救護車駕駛艙頂燈條：暖米黃、恆亮（不是紅藍警示燈、不閃） | a5_c007 | 程式繪製（review/G5/a5/scripts/build_a5_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（私人建置試拍 review/G5/a5/checks/snaps、引擎擷取 review/G5/a5/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a5_gate/a5-gurney_v01.png | 道具（透明）；440×210 | a5_gate | 擔架床（側面）：淺灰金屬架、米白床墊、鼠尾草綠摺好的毯子；空的（不畫躺著的人） | a5_c007 | 程式繪製（review/G5/a5/scripts/build_a5_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（私人建置試拍 review/G5/a5/checks/snaps、引擎擷取 review/G5/a5/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a5_gate/a5-phone_v02.png | 圖示（透明）；260×260 | a5_gate | 119 執勤人員的紙剪電話圖示：米白圓牌＋深青綠話筒剪影（自畫幾何）；v01 兩端畫成楔形像彎箭頭，已刪 | a5_c006 | 程式繪製（review/G5/a5/scripts/phone_icon_v2.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（私人建置試拍 review/G5/a5/checks/snaps、引擎擷取 review/G5/a5/pack/）；投影與聽感依驗收包 | v02 |
| assets/final/sets/a5_gate/a5-phone-arc1_v01.png | 圖示（透明）；88×88 | a5_gate | 電話聲波弧線（小） | a5_c006 | 程式繪製（review/G5/a5/scripts/build_a5_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（私人建置試拍 review/G5/a5/checks/snaps、引擎擷取 review/G5/a5/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a5_gate/a5-phone-arc2_v01.png | 圖示（透明）；140×140 | a5_gate | 電話聲波弧線（中） | a5_c006 | 程式繪製（review/G5/a5/scripts/build_a5_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（私人建置試拍 review/G5/a5/checks/snaps、引擎擷取 review/G5/a5/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a5_gate/a5-phone-arc3_v01.png | 圖示（透明）；192×192 | a5_gate | 電話聲波弧線（大） | a5_c006 | 程式繪製（review/G5/a5/scripts/build_a5_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（私人建置試拍 review/G5/a5/checks/snaps、引擎擷取 review/G5/a5/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a5_hospital/wall_v01.png | 背牆（不透明）；1536×1024 | a5_hospital（醫院走廊，傍晚） | 暖黃走廊牆：兩扇窗外是傍晚天空與屋頂、風景小畫、木扶手、右側診間木門（霧面窗）、時鐘、門旁空白小牌；沒有文字、沒有紅十字 | a5_c008 | Codex 生成（review/G5/a5/raw/a5_hosp_wall_v01，codex_log 第 5 次）→ assets/generated/bg-hospital-wall_v01.png | Codex 內建 image_gen（ChatGPT 額度）生成，附專案母版當參考；使用者自有 | 代理目視（私人建置試拍 review/G5/a5/checks/snaps、引擎擷取 review/G5/a5/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a5_hospital/floor_v01.png | 地板（不透明）；1024×512 | a5_hospital | 長條木紋地板 | a5_c008 | 程式繪製（review/G5/a5/scripts/build_a5_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（私人建置試拍 review/G5/a5/checks/snaps、引擎擷取 review/G5/a5/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a5_hospital/bench_v01.png | 景片（透明）；919×380 | a5_hospital | 候診長椅（四個連座：淺木色座面與椅背、鐵灰橫樑與椅腳；座面上緣世界 0.94） | a5_c008 | 程式繪製（review/G5/a5/scripts/build_a5_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（私人建置試拍 review/G5/a5/checks/snaps、引擎擷取 review/G5/a5/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/chr-chen_pose-shoutr_v01.png | 表演姿勢圖（透明）；724×1530 | chen | shoutr：手圍在嘴邊朝畫面右（辦公室方向）大聲交代、嘴張開；另一手握拳垂下 | a5_c001 | Codex 生成（附 chr-chen_master_v01 當參考；codex_log 第 1 次）→ assets/generated/chr-chen_pose-shoutr_v01.png；review/G5/a5/scripts/process_a5.py 去背、白邊、主色 ΔE 檢查（背心 4.9、制服 1.9） | Codex 內建 image_gen（ChatGPT 額度）生成，附專案母版當參考；使用者自有 | 代理目視（私人建置試拍 review/G5/a5/checks/snaps、引擎擷取 review/G5/a5/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/chr-chen_pose-standr_v01.png | 表演姿勢圖（透明）；649×1522 | chen | standr：站姿左右鏡射（臉朝畫面右：看校門、聽林老師回答） | a5_c001、a5_c007 | assets/final/chr-chen_master_v01.png 左右鏡射（build_a5_art.py chen_standr） | 自製（程式繪製／由專案母版改畫） | 代理目視（私人建置試拍 review/G5/a5/checks/snaps、引擎擷取 review/G5/a5/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/chr-xiaoqing_pose-sitb_v01.png | 表演姿勢圖（透明）；575×1332 | xiaoqing | sitb＝P-QG2：坐醫院長椅、低頭自責（臉朝畫面右下）、雙手放膝上 | a5_c008 | Codex 生成（附 chr-xiaoqing_master_v04 當參考；codex_log 第 2 次）；吊帶褲重新上色到母版 L*（ΔE 1.4、上衣 4.3） | Codex 內建 image_gen（ChatGPT 額度）生成，附專案母版當參考；使用者自有 | 代理目視（私人建置試拍 review/G5/a5/checks/snaps、引擎擷取 review/G5/a5/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/chr-xiaoyu_pose-sitb_v01.png | 表演姿勢圖（透明）；675×1366 | xiaoyu | sitb＝P-XY3：坐醫院長椅（臉朝畫面右）、戴兒童手錶 | a5_c008 | Codex 生成（附 chr-xiaoyu_master_v04 當參考；codex_log 第 3 次）；外套重新上色到母版 L*（ΔE 5.4、短褲 4.5） | Codex 內建 image_gen（ChatGPT 額度）生成，附專案母版當參考；使用者自有 | 代理目視（私人建置試拍 review/G5/a5/checks/snaps、引擎擷取 review/G5/a5/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/chr-medic-a_stand_v01.png | 角色立牌（透明）；434×1040 | medic_a（救護人員 A） | 站姿：深灰藍工作服、反光條、臂章只有手捧愛心圖示（無紅十字、無真實單位標誌）；臉朝畫面右 | a5_c007 | Codex 生成（一張兩人，codex_log 第 4 次）→ assets/generated/chr-medic_pair_v01.png 切開；外圍 alpha<32 淡霧清掉 | Codex 內建 image_gen（ChatGPT 額度）生成，附專案母版當參考；使用者自有 | 代理目視（私人建置試拍 review/G5/a5/checks/snaps、引擎擷取 review/G5/a5/pack/）；投影與聽感依驗收包 | v01 |
| assets/final/chr-medic-b_stand_v01.png | 角色立牌（透明）；351×964 | medic_b（救護人員 B） | 站姿：同 A 的工作服、手捧愛心臂章；綁馬尾；臉朝畫面右 | a5_c007 | 同上（切開的右半） | Codex 內建 image_gen（ChatGPT 額度）生成，附專案母版當參考；使用者自有 | 代理目視（私人建置試拍 review/G5/a5/checks/snaps、引擎擷取 review/G5/a5/pack/）；投影與聽感依驗收包 | v01 |

另外：assets/generated/ 的 Codex 原圖（bg-hospital-wall_v01、chr-chen_pose-shoutr_v01、chr-xiaoqing_pose-sitb_v01、chr-xiaoyu_pose-sitb_v01、chr-medic_pair_v01）是上表的生成來源，不直接進演出。

### 來源：review/G5/a6/ASSETS_rows.md

# 第六幕＋複習＋閉幕（a6／a7／a8）新素材：資產表列（給主線併入 ASSETS.md）

2026-10-21，G5 第六幕代理。Codex image_gen 共 3 張（上限 6；紀錄 review/G5/a6/codex_log.md）：謝幕鞠躬兩張拼版（孩子、大人）、阿琴阿姨站姿。其餘全部 Pillow＋G2 同款紙紋程式繪製（review/G5/a6/scripts/build_a6_art.py、build_a6_art2.py、make_cards.py，借用 review/G5/shared_art/scripts/paperdraw.py；可重跑）。圖裡沒有任何文字、數字、品牌、標誌、紅十字；紙卡標題與口訣文字由 app/src/sets/a6_shop.ts 在執行時排版。程式景片（主燈大摺紙貓、騎樓燈籠串、光流、小折折燈、謝幕微光）在 app/src/sets/a6_square_night.ts、a6_shop.ts，沒有圖檔。
show_characters.json 只新增：xiaoqing/xiaoyu/pinan/chen/lin/ye 的 bow、xiaoqing.stand_m、xiaoyu.standwatch_m、pinan.stand_m／walk_straps_m、新角色 aqin，與對應 fallbackFaces（aqin:stand、xiaoqing:stand_m、xiaoyu:standwatch_m、pinan:stand_m、pinan:walk_straps_m）。

| 檔名 | 類型 | 角色／場景 | 部件／表情 | 使用 cue | 來源／生成參考 | 授權 | 檢視結果 | 版本 |
|---|---|---|---|---|---|---|---|---|
| assets/final/chr-xiaoqing_pose-bow_v01.png | 表演姿勢圖（透明，白邊）；419×976 | 小晴 | bow：謝幕鞠躬（上身前傾約 30°、雙手垂在大腿前、閉眼微笑）；headTop 虛擬頭頂讓頭寬和站姿母版同大 | a8_c001 | Codex image_gen（第 1 次，1 張拼版切件）；原檔 review/G5/a6/raw/bow_kids_v01.png；提示 bow_kids_v01.prompt.txt；參考 S4＋三位兒童母版；切件、白邊與 alpha 整理 review/G5/a6/scripts/process_a6_chars.py；小晴吊帶褲、小宇外套主色調回 v04 色票 | 使用者 ChatGPT 方案生成 | 無文字；三人分開；白邊完整；主色 ΔE 見 review/G5/a6/chars_import.json | v01 |
| assets/final/chr-xiaoyu_pose-bow_v01.png | 表演姿勢圖（透明，白邊）；382×985 | 小宇 | bow：謝幕鞠躬（上身前傾約 30°、雙手垂在大腿前、閉眼微笑）；headTop 虛擬頭頂讓頭寬和站姿母版同大 | a8_c001 | Codex image_gen（第 1 次，1 張拼版切件）；原檔 review/G5/a6/raw/bow_kids_v01.png；提示 bow_kids_v01.prompt.txt；參考 S4＋三位兒童母版；切件、白邊與 alpha 整理 review/G5/a6/scripts/process_a6_chars.py；小晴吊帶褲、小宇外套主色調回 v04 色票 | 使用者 ChatGPT 方案生成 | 無文字；三人分開；白邊完整；主色 ΔE 見 review/G5/a6/chars_import.json | v01 |
| assets/final/chr-pinan_pose-bow_v01.png | 表演姿勢圖（透明，白邊）；410×974 | 品安 | bow：謝幕鞠躬（上身前傾約 30°、雙手垂在大腿前、閉眼微笑）；headTop 虛擬頭頂讓頭寬和站姿母版同大 | a8_c001 | Codex image_gen（第 1 次，1 張拼版切件）；原檔 review/G5/a6/raw/bow_kids_v01.png；提示 bow_kids_v01.prompt.txt；參考 S4＋三位兒童母版；切件、白邊與 alpha 整理 review/G5/a6/scripts/process_a6_chars.py；小晴吊帶褲、小宇外套主色調回 v04 色票 | 使用者 ChatGPT 方案生成 | 無文字；三人分開；白邊完整；主色 ΔE 見 review/G5/a6/chars_import.json | v01 |
| assets/final/chr-chen_pose-bow_v01.png | 表演姿勢圖（透明，白邊）；435×963 | 陳伯伯 | bow：謝幕鞠躬（上身前傾、閉眼微笑） | a8_c001 | Codex image_gen（第 1 次，1 張拼版切件）；原檔 review/G5/a6/raw/bow_adults_v01.png；提示 bow_adults_v01.prompt.txt；參考 S4＋三位大人母版；切件 process_a6_chars.py | 使用者 ChatGPT 方案生成 | 無文字、無紅十字（葉護理師識別證只有手捧愛心圖示）；三人分開 | v01 |
| assets/final/chr-lin_pose-bow_v01.png | 表演姿勢圖（透明，白邊）；312×948 | 林老師 | bow：謝幕鞠躬（上身前傾、閉眼微笑） | a8_c001 | Codex image_gen（第 1 次，1 張拼版切件）；原檔 review/G5/a6/raw/bow_adults_v01.png；提示 bow_adults_v01.prompt.txt；參考 S4＋三位大人母版；切件 process_a6_chars.py | 使用者 ChatGPT 方案生成 | 無文字、無紅十字（葉護理師識別證只有手捧愛心圖示）；三人分開 | v01 |
| assets/final/chr-ye_pose-bow_v01.png | 表演姿勢圖（透明，白邊）；398×954 | 葉護理師 | bow：謝幕鞠躬（上身前傾、閉眼微笑） | a8_c001 | Codex image_gen（第 1 次，1 張拼版切件）；原檔 review/G5/a6/raw/bow_adults_v01.png；提示 bow_adults_v01.prompt.txt；參考 S4＋三位大人母版；切件 process_a6_chars.py | 使用者 ChatGPT 方案生成 | 無文字、無紅十字（葉護理師識別證只有手捧愛心圖示）；三人分開 | v01 |
| assets/final/chr-aqin_master_v01.png | 角色母版（透明，白邊）；456×1526 | 阿琴阿姨（新角色，不說話） | stand：四分之三側面朝畫面左、雙手輕握在腰前；深棕開襟外套、燕麥色圍巾、耳下短髮兩鬢微白 | a6_c001、a6_c007、a6_c008 | Codex image_gen（第 1 次）；原檔 review/G5/a6/raw/chr_aqin_stand_v01.png；參考 S4＋阿樂叔叔＋林老師母版；處理 process_a6_chars.py | 使用者 ChatGPT 方案生成 | 無文字、無標誌；6.2 頭身；退路眨眼兩眼殘留 ≤0.4%（fallbackFaces aqin:stand） | v01 |
| assets/final/chr-pinan_pose-stand-m_v01.png | 表演姿勢圖（透明，白邊）；573×1515 | pinan | stand_m：品安站姿左右鏡射（朝畫面右） | a6、a7 | 由專案母版 PIL 左右鏡射（process_a6_chars.py、add_xq_stand_m.py）；退路臉部範圍鏡射登記 fallbackFaces | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a6/pack 等）；投影與聽感依驗收包 | v01 |
| assets/final/chr-pinan_pose-walk-straps-m_v01.png | 表演姿勢圖（透明，白邊）；765×1486 | pinan | walk_straps_m：抓背帶低頭走路左右鏡射（往畫面右） | a6、a7 | 由專案母版 PIL 左右鏡射（process_a6_chars.py、add_xq_stand_m.py）；退路臉部範圍鏡射登記 fallbackFaces | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a6/pack 等）；投影與聽感依驗收包 | v01 |
| assets/final/chr-xiaoyu_pose-standwatch-m_v01.png | 表演姿勢圖（透明，白邊）；528×1446 | xiaoyu | standwatch_m：小宇戴錶站姿左右鏡射（朝畫面右） | a6、a7 | 由專案母版 PIL 左右鏡射（process_a6_chars.py、add_xq_stand_m.py）；退路臉部範圍鏡射登記 fallbackFaces | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a6/pack 等）；投影與聽感依驗收包 | v01 |
| assets/final/chr-xiaoqing_pose-stand-m_v01.png | 表演姿勢圖（透明，白邊）；535×1492 | xiaoqing | stand_m：小晴站姿左右鏡射（朝畫面左；紙片翻面用） | a6、a7 | 由專案母版 PIL 左右鏡射（process_a6_chars.py、add_xq_stand_m.py）；退路臉部範圍鏡射登記 fallbackFaces | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a6/pack 等）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a6_square_night/sky_v01.png | 背牆（不透明）；2048×1024 | a6_square_night | 紙燈節夜空：靛藍→暖紫→地平線暖色；剪紙雲、剪紙月亮、紙星星（固定、不發光） | a6_c001–a6_c007 | 程式繪製（review/G5/a6/scripts/build_a6_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a6/pack 等）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a6_square_night/rack_v02.png | 景片（透明）；1100×1100 | a6_square_night | 燈籠架：兩根竹竿＋橫樑、五盞圓紙燈籠、晾著的燈籠紙（燈籠在孩子頭頂上方；孩子站在架子後的角落） | a6_c001–a6_c007 | 程式繪製（review/G5/a6/scripts/build_a6_art2.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a6/pack 等）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a6_square_night/folk-a_v01.png | 景片（透明，白邊）；584×1004 | a6_square_night | 一起糊燈籠紙的鎮民：背影、兩手往右上把燈籠紙貼到骨架上（不透明紙片小人、沒有五官、中性設計） | a6_c001–a6_c007 | 程式繪製（review/G5/a6/scripts/build_a6_art2.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a6/pack 等）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a6_square_night/folk-b_v01.png | 景片（透明，白邊）；584×1004 | a6_square_night | 鎮民背影（灰髮、往左上貼紙；layout flipX） | a6_c001–a6_c007 | 程式繪製（review/G5/a6/scripts/build_a6_art2.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a6/pack 等）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a6_square_night/folk-c_v01.png | 景片（透明，白邊）；384×784 | a6_square_night | 孩子背影（雙手舉著燈籠紙） | a6_c001–a6_c007 | 程式繪製（review/G5/a6/scripts/build_a6_art2.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a6/pack 等）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a6_square_night/folk-d_v01.png | 景片（透明，白邊）；444×1004 | a6_square_night | 鎮民背影（雙手垂下，在糊紙桌旁看） | a6_c001–a6_c007 | 程式繪製（review/G5/a6/scripts/build_a6_art2.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a6/pack 等）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a6_square_night/table_v01.png | 景片（透明）；900×380 | a6_square_night | 糊紙用的長桌：漿糊碗、紙捲、一疊剪好的燈籠紙（無字） | a6_c001–a6_c007 | 程式繪製（review/G5/a6/scripts/build_a6_art2.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a6/pack 等）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a6_window/room_v01.png | 景片（窗洞透明）；2080×1088 | a6_window | 室內牆：暖米色紙、木腰板、踢腳板、木窗框十字窗櫺、窗台、兩側束起的布簾 | a6_c008 | 程式繪製（review/G5/a6/scripts/build_a6_art2.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a6/pack 等）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a6_window/sky-autumn_v01.png | 景片（不透明）；1024×640 | a6_window | 窗外天空・秋（淡藍到暖黃、剪紙雲） | a6_c008 | 程式繪製（review/G5/a6/scripts/build_a6_art2.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a6/pack 等）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a6_window/sky-winter_v01.png | 景片（不透明）；1024×640 | a6_window | 窗外天空・冬（灰藍、雲多） | a6_c008 | 程式繪製（review/G5/a6/scripts/build_a6_art2.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a6/pack 等）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a6_window/sky-spring_v01.png | 景片（不透明）；1024×640 | a6_window | 窗外天空・春（淡藍） | a6_c008 | 程式繪製（review/G5/a6/scripts/build_a6_art2.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a6/pack 等）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a6_window/sky-summer_v01.png | 景片（不透明）；1024×640 | a6_window | 窗外天空・夏（晴藍、剪紙太陽） | a6_c008 | 程式繪製（review/G5/a6/scripts/build_a6_art2.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a6/pack 等）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a6_window/tree-autumn_v01.png | 景片（透明）；663×977 | a6_window | 窗外的樹・秋（sets/square/set-square_tree-a 葉子重新上色成橘黃） | a6_c008 | 程式繪製（review/G5/a6/scripts/build_a6_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a6/pack 等）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a6_window/tree-summer_v01.png | 景片（透明）；663×977 | a6_window | 窗外的樹・夏（同一棵樹、綠葉加深） | a6_c008 | 程式繪製（review/G5/a6/scripts/build_a6_art.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a6/pack 等）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a6_window/tree-winter_v02.png | 景片（透明）；663×977 | a6_window | 窗外的樹・冬（去葉、程式畫的光禿枝條從樹幹分岔長出） | a6_c008 | 程式繪製（review/G5/a6/scripts/build_a6_art2.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a6/pack 等）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a6_window/tree-spring_v02.png | 景片（透明）；663×977 | a6_window | 窗外的樹・春（冬天的枝條＋枝梢淺綠新芽與淡粉小花） | a6_c008 | 程式繪製（review/G5/a6/scripts/build_a6_art2.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a6/pack 等）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a6_window/shelf_v01.png | 景片（透明）；520×560 | a6_window | 室內矮櫃＋沒點的小紙燈籠＋一疊摺紙 | a6_c008 | 程式繪製（review/G5/a6/scripts/build_a6_art2.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a6/pack 等）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a6_window/plant_v01.png | 景片（透明）；420×700 | a6_window | 室內盆栽 | a6_c008 | 程式繪製（review/G5/a6/scripts/build_a6_art2.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a6/pack 等）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a6_window/leaf_v01.png | 景片（透明）；120×90 | a6_window | 秋天飄落的葉子（一片，窗外） | a6_c008 | 程式繪製（review/G5/a6/scripts/build_a6_art2.py） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a6/pack 等）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a6_shop/card-1_v01.png | 紙卡（透明）；1050×810 | a6_shop | 大紙卡 1「拒絕與離開」：a3_c002 小宇在騎樓下說不要的畫面重製成紙卡插畫；上方空白標題列（標題程式排版） | a7_c001 | make_cards.py（來源 review/G5/a6/cards_src/a3_c002_9.0.png，capture_cards.mjs 從引擎擷取、不含字幕） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a6/pack 等）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a6_shop/card-2_v01.png | 紙卡（透明）；1050×810 | a6_shop | 大紙卡 2「安全接送」：a4_c012 兩個孩子回到校門（陳伯伯旁）的畫面重製 | a7_c001 | make_cards.py（來源 cards_src/a4_c012_6.0.png） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a6/pack 等）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a6_shop/card-3_v01.png | 紙卡（透明）；1050×810 | a6_shop | 大紙卡 3「找大人求助」：a5_c006 小宇用手錶打 119 的畫面重製 | a7_c001 | make_cards.py（來源 cards_src/a5_c006_6.0.png） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a6/pack 等）；投影與聽感依驗收包 | v01 |
| assets/final/sets/a6_shop/card-mnemonic_v01.png | 紙卡（透明）；1400×620 | a6_shop | 口訣卡：四格動作小圖（小晴雙手交叉＝不碰、小宇掌心向外＝不試、小晴指右＝先離開、小宇手放額前＝找大人；取自現有姿勢圖）；文字「不碰、不試；先離開，找大人」程式排版 | a7_c002、a7_c003 | make_cards.py（姿勢圖 chr-xiaoqing_pose-cross_v06、chr-xiaoyu_pose-palmno_v06、chr-xiaoqing_pose-pointr_v07、chr-xiaoyu_pose-forehead_v06） | 自製（程式繪製／由專案母版改畫） | 代理目視（引擎擷取，review/G5/a6/pack 等）；投影與聽感依驗收包 | v01 |

另有原始生成圖（不改、已複製進 assets/generated/）：assets/generated/chr-{xiaoqing,xiaoyu,pinan,chen,lin,ye}_pose-bow_v01.png（拼版依透明連通區切開的原像素）、assets/generated/chr-aqin_master_v01.png。


## G7 合併：最後演出用到、先前未登記的素材（主線 2026-10-22 21:4x）

依 review/G7/素材與授權表.md 第 2.5 節：app/dist 資料包裡有、本表先前沒有登記的 50 個檔。來源取自各幕代理的 review/G5/<幕>/ASSETS_rows.md 與進度紀錄；3 份 layout.json 取自 git 歷史。

| 檔案 | 來源 | 授權 | 紀錄出處 |
|---|---|---|---|
| assets/final/chr-lin_pose-phone_v01.png | Codex 生成 | 生成圖（ChatGPT 方案的 Codex 內建圖像生成）；依 OpenAI 使用條款產出歸使用者 | review/G5/a3/ASSETS_rows.md |
| assets/final/chr-pinan_pose-sit-lantern-look1_v01.png | 品安姿勢圖程式加工（眼珠、抬頭） | 生成圖（Codex，ChatGPT 方案）的程式加工；依 OpenAI 使用條款產出歸使用者 | review/G5/a1/ASSETS_rows.md |
| assets/final/chr-pinan_pose-sit-lantern-look2_v01.png | 品安姿勢圖程式加工（眼珠、抬頭） | 生成圖（Codex，ChatGPT 方案）的程式加工；依 OpenAI 使用條款產出歸使用者 | review/G5/a1/ASSETS_rows.md |
| assets/final/chr-ye_pose-crouchphone_v01.png | Codex 生成 | 生成圖（ChatGPT 方案的 Codex 內建圖像生成）；依 OpenAI 使用條款產出歸使用者 | review/G5/a2/ASSETS_rows.md |
| assets/final/sets/a2_shop/insert-ale-forearm-l_v01.png | 阿樂分件程式加工（母版為 Codex 生成） | 生成圖（ChatGPT 方案的 Codex 內建圖像生成）與其程式加工；依 OpenAI 使用條款產出歸使用者 | review/G5/a2/ASSETS_rows.md |
| assets/final/sets/a2_shop/insert-ale-forearm-l-outline_v01.png | 阿樂分件程式加工（母版為 Codex 生成） | 生成圖（ChatGPT 方案的 Codex 內建圖像生成）與其程式加工；依 OpenAI 使用條款產出歸使用者 | review/G5/a2/ASSETS_rows.md |
| assets/final/sets/a2_shop/insert-ale-forearm-r_v01.png | 阿樂分件程式加工（母版為 Codex 生成） | 生成圖（ChatGPT 方案的 Codex 內建圖像生成）與其程式加工；依 OpenAI 使用條款產出歸使用者 | review/G5/a2/ASSETS_rows.md |
| assets/final/sets/a2_shop/insert-ale-forearm-r-outline_v01.png | 阿樂分件程式加工（母版為 Codex 生成） | 生成圖（ChatGPT 方案的 Codex 內建圖像生成）與其程式加工；依 OpenAI 使用條款產出歸使用者 | review/G5/a2/ASSETS_rows.md |
| assets/final/sets/a2_shop/insert-ale-hand-l-outline_v01.png | 阿樂分件程式加工（母版為 Codex 生成） | 生成圖（ChatGPT 方案的 Codex 內建圖像生成）與其程式加工；依 OpenAI 使用條款產出歸使用者 | review/G5/a2/ASSETS_rows.md |
| assets/final/sets/a2_shop/insert-ale-hand-r-outline_v01.png | 阿樂分件程式加工（母版為 Codex 生成） | 生成圖（ChatGPT 方案的 Codex 內建圖像生成）與其程式加工；依 OpenAI 使用條款產出歸使用者 | review/G5/a2/ASSETS_rows.md |
| assets/final/sets/a2_shop/insert-ale-hand-l_v02.png | 阿樂分件程式加工（母版為 Codex 生成） | 生成圖（ChatGPT 方案的 Codex 內建圖像生成）與其程式加工；依 OpenAI 使用條款產出歸使用者 | review/G5/a2/ASSETS_rows.md |
| assets/final/sets/a2_shop/insert-ale-hand-r_v02.png | 阿樂分件程式加工（母版為 Codex 生成） | 生成圖（ChatGPT 方案的 Codex 內建圖像生成）與其程式加工；依 OpenAI 使用條款產出歸使用者 | review/G5/a2/ASSETS_rows.md |
| assets/final/sets/a2_memory/mem-box_v02.png | 盒子特寫圖程式加工（底圖為 Codex 生成） | 生成圖（ChatGPT 方案的 Codex 內建圖像生成）與其程式加工；依 OpenAI 使用條款產出歸使用者 | review/G5/a2/ASSETS_rows.md |
| assets/final/sets/a2_window/sil-ale-hand_v02.png | 程式繪製 | 原創（程式產生） | review/G5/a2/ASSETS_rows.md |
| assets/final/sets/a3_arcade/handbox_v01.png | 邀請者手圖程式加工（拿掉盒角灰色短棒；底圖為 Codex 生成） | 生成圖（ChatGPT 方案的 Codex 內建圖像生成）與其程式加工；依 OpenAI 使用條款產出歸使用者 | review/G5/a3/ASSETS_rows.md |
| assets/final/sets/a3_classroom/classmate-a_v01.png | Codex 生成 | 生成圖（ChatGPT 方案的 Codex 內建圖像生成）；依 OpenAI 使用條款產出歸使用者 | review/G5/a3/ASSETS_rows.md |
| assets/final/sets/a3_classroom/classmate-b_v01.png | Codex 生成 | 生成圖（ChatGPT 方案的 Codex 內建圖像生成）；依 OpenAI 使用條款產出歸使用者 | review/G5/a3/ASSETS_rows.md |
| assets/final/sets/a4_roadmap/set-a4map_sil-car_v02.png | 程式繪製 | 原創（程式產生） | review/G5/a4/ASSETS_rows.md |
| assets/final/sets/a4_roadmap/set-a4map_sil-walker_v02.png | 程式繪製 | 原創（程式產生） | review/G5/a4/ASSETS_rows.md |
| assets/final/sets/a5_gate/a5-ambulance_v03.png | 程式繪製 | 原創（程式產生） | review/G5/a5/ASSETS_rows.md |
| assets/final/sets/a5_gate/a5-ambulance-door_v02.png | 程式繪製 | 原創（程式產生） | review/G5/a5/ASSETS_rows.md |
| assets/final/sets/a5_gate/a5-corner_v02.png | 程式繪製 | 原創（程式產生） | review/G5/a5/ASSETS_rows.md |
| assets/final/sets/a5_gate/a5-flag_v01.png | 程式繪製 | 原創（程式產生） | review/G5/a5/ASSETS_rows.md |
| assets/final/sets/a5_gate/a5-flag-back_v01.png | 程式繪製 | 原創（程式產生） | review/G5/a5/ASSETS_rows.md |
| assets/final/sets/a5_gate/a5-gurney_v03.png | 程式繪製 | 原創（程式產生） | review/G5/a5/ASSETS_rows.md |
| assets/final/sets/a5_gate/a5-student_v03.png | Codex 生成 | 生成圖（ChatGPT 方案的 Codex 內建圖像生成）；依 OpenAI 使用條款產出歸使用者 | review/G5/a5/ASSETS_rows.md |
| assets/final/sets/a5_gate/a5-student-arm_v03.png | Codex 生成（從同一張切出） | 生成圖（ChatGPT 方案的 Codex 內建圖像生成）；依 OpenAI 使用條款產出歸使用者 | review/G5/a5/ASSETS_rows.md |
| assets/final/sets/a5_gate/set-gate_school-building_v01.png | 程式繪製景片再加紙感（paperize.py） | 原創（程式產生） | review/G5/a5/ASSETS_rows.md |
| assets/final/sets/a5_gate/set-gate_school-wall_v01.png | 程式繪製景片再加紙感（paperize.py） | 原創（程式產生） | review/G5/a5/ASSETS_rows.md |
| assets/final/sets/a5_gate/set-gate_folding-gate_v01.png | 程式繪製景片再加紙感（paperize.py） | 原創（程式產生） | review/G5/a5/ASSETS_rows.md |
| assets/final/sets/a5_gate/set-gate_guard-house_v01.png | 程式繪製景片再加紙感（paperize.py） | 原創（程式產生） | review/G5/a5/ASSETS_rows.md |
| assets/final/sets/a5_gate/set-gate_pillar_v01.png | 程式繪製景片再加紙感（paperize.py） | 原創（程式產生） | review/G5/a5/ASSETS_rows.md |
| assets/final/sets/a6_square_night/folk-a_v02.png | 程式繪製 | 原創（程式產生） | review/G5/a6/ASSETS_rows.md |
| assets/final/sets/a6_square_night/folk-b_v02.png | 程式繪製 | 原創（程式產生） | review/G5/a6/ASSETS_rows.md |
| assets/final/sets/a6_square_night/folk-c_v02.png | 程式繪製 | 原創（程式產生） | review/G5/a6/ASSETS_rows.md |
| assets/final/sets/a6_square_night/folk-d_v02.png | 程式繪製 | 原創（程式產生） | review/G5/a6/ASSETS_rows.md |
| assets/final/sets/gate/set-gate_a4-truck_v01.png | 程式繪製（由程式畫的小貨車改畫） | 原創（程式產生） | review/G5/a4/ASSETS_rows.md |
| assets/final/sets/gate/set-gate_a4-truck-tip_v01.png | 程式繪製（由程式畫的小貨車改畫） | 原創（程式產生） | review/G5/a4/ASSETS_rows.md |
| assets/final/sets/gate/set-gate_a4-walkers-a_v02.png | 程式繪製 | 原創（程式產生） | review/G5/a4/ASSETS_rows.md |
| assets/final/sets/gate/set-gate_a4-walkers-b_v02.png | 程式繪製 | 原創（程式產生） | review/G5/a4/ASSETS_rows.md |
| assets/final/sets/square_a1/shopwall_v01.png | 程式繪製 | 原創（程式產生） | review/G5/a1/ASSETS_rows.md |
| assets/final/sets/square_a1/silbody_v02.png | 阿樂母版外形程式加工（底圖為 Codex 生成） | 生成圖（ChatGPT 方案的 Codex 內建圖像生成）與其程式加工；依 OpenAI 使用條款產出歸使用者 | review/G5/a1/ASSETS_rows.md |
| assets/final/sets/square_a1/silarm_v02.png | 阿樂母版外形程式加工（底圖為 Codex 生成） | 生成圖（ChatGPT 方案的 Codex 內建圖像生成）與其程式加工；依 OpenAI 使用條款產出歸使用者 | review/G5/a1/ASSETS_rows.md |
| assets/final/sets/square_a1/silbamboo_v02.png | 阿樂母版外形程式加工（底圖為 Codex 生成） | 生成圖（ChatGPT 方案的 Codex 內建圖像生成）與其程式加工；依 OpenAI 使用條款產出歸使用者 | review/G5/a1/ASSETS_rows.md |
| assets/final/sets/workshop_a0/hanglamps_v01.png | 燈籠店吊燈籠景片程式加工（底圖為 Codex 生成） | 生成圖（ChatGPT 方案的 Codex 內建圖像生成）與其程式加工；依 OpenAI 使用條款產出歸使用者 | review/G5/a0/ASSETS_rows.md |
| assets/final/sets/workshop_a0/stand_v02.png | 程式繪製 | 原創（程式產生） | review/G5/a1/ASSETS_rows.md |
| assets/final/sets/a5_hospital/layout.json | G5 第二批各幕代理撰寫的場景擺位設定（原創資料，只寫圖層位置與燈光，不含圖；首次提交 f7d722a） | 原創（程式產生） | git 歷史（f7d722a）；app/src/sets/ |
| assets/final/sets/a6_square_night/layout.json | G5 第二批各幕代理撰寫的場景擺位設定（原創資料，只寫圖層位置與燈光，不含圖；首次提交 f7d722a） | 原創（程式產生） | git 歷史（f7d722a）；app/src/sets/ |
| assets/final/sets/a6_window/layout.json | G5 第二批各幕代理撰寫的場景擺位設定（原創資料，只寫圖層位置與燈光，不含圖；首次提交 f7d722a） | 原創（程式產生） | git 歷史（f7d722a）；app/src/sets/ |
| audio/sfx/sfx_stamp_v02.wav | 程式合成（tools/music/sfx.py 重建、音量降約 3 dB） | 原創（程式合成） | review/G5/a4/PROGRESS_polish.md（11:33 那筆）、review/G6/qa/tech.md |
