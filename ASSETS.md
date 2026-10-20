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
