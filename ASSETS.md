# 素材與授權表

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
- **授權**：Starter 付費方案（2026-10-21 06:30 起），官方說明付費方案含商用授權（Beta 服務除外；eleven_v3 不是 Beta），聲線庫聲線附免費商用授權。ElevenLabs 使用政策「Use by and for Minors」要求兒童對象的產品取得書面核准：**使用者 2026-10-21 已申請、待回覆**；核准信件取得後記在本節。證據：review/G3/el/license_evidence.md。
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
