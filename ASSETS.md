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

## 配音（G3 選角提案＋G4 代表鏡頭正式台詞，2026-10-21 配音代理）

- 產生：`tools/vo_build.py --set g4`（讀 `audio/vo/casting.json`、`audio/vo/pronounce.json`、`script/劇本_v03.md`）；字幕一律用劇本原文，替身字只送進合成器（本批只有 a2_c004_01 的「阿樂」→「阿勒」）。母帶：頭 120 ms／尾 250 ms 靜音、−18 LUFS（ffmpeg loudnorm 兩段式；短句與 loudnorm 轉動態模式時改用量測值線性增益）、真峰值 ≤ −1.5 dBTP（4 倍超取樣限制器）、48 kHz／單聲道／16-bit PCM。選角理由與量測：`review/G3/casting.md`。
- **授權（edge-tts）**：edge-tts 7.3.1 是社群開發的非官方工具，呼叫 Edge 線上朗讀服務，微軟條款沒有明確授權這種用途。v1.2 第 20.2 節只作暫用、不放進正式交付包；v1.3 第 6 節允許在記錄風險下使用。正式交付前建議以 Azure AI Speech 同名聲線一鍵重建（`tools/vo_build.py --all --service azure`，需使用者金鑰；後端已寫好未實測），或由主線決定。
- ElevenLabs：本批正式檔**沒有**使用（金鑰為免費方案，API 不可用台灣共享聲線與聲線設計；免費方案條款限非商業並須標註 ElevenLabs）。G3 試音用了 283 字元（`audio/vo/elevenlabs_usage.jsonl`），試音樣本 `review/G3/samples/A_*`、`B_*jessica*` 不是正式素材。
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
