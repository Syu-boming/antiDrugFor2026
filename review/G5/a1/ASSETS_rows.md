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

## 修正第 1 輪（2026-10-21 晚，同一代理；程式繪製，腳本 `review/G5/a0/scripts/build_fix1_art.py`，Codex 生圖 0 張）

| 檔名 | 類型 | 角色／場景 | 部件／表情 | 使用 cue | 來源／生成參考 | 授權 | 檢視結果 | 版本 |
|---|---|---|---|---|---|---|---|---|
| assets/final/sets/workshop_a0/stand_v02.png | 道具（透明；384×174，白邊 6 px） | 燈籠店 | 空著的主燈底座 v02：圓木座＋淺色紙墊上一圈虛線印痕（骨架原本立在這裡）＋八個空插孔；掛在工作台鉸鏈上跟著立起 | a0_c001–a0_c005 | 程式繪製（stand） | 本專案自製 | 驗收「骨架不見了看不出空位」：工作台中央的 G4 燈籠骨在本景畫布上擦掉，底座放到中央 | v02（取代 v01） |
| assets/final/sets/square_a1/silbody_v02.png、silarm_v02.png、silbamboo_v02.png | 剪影（柔邊；481×857、300×300、60×260） | 窗內阿樂叔叔（FX10） | 兩階深色剪影：頭髮與圍裙（含肩帶）最深、襯衫與皮膚次深，看得出是阿樂叔叔；沒有五官、**沒有操偶線**；竹篾改短竹條（v01 一半長） | a1_c008 | 程式加工（silhouettes）；外形來源為本專案母版 chr-ale_master_v02 | 本專案自製 | 拿掉窗紙前的半透明紙（明度差 ΔL* ≥ 40）；動作：手垂著 → 舉起 0.8 秒 → 被帶往左歪 0.5 秒 → 竹條 1 秒落下（看得到）→ 窗光漸亮 | v02（取代 v01） |
| （拿掉）assets/final/sets/square_a1/townsfolk_v01.png、workshop_a0/lamps_v01.png | — | — | 景程式不再使用（半透明灰色鎮民依裁定 6 拿掉；八盞燈依裁定 3 改由引擎台口實景燈） | — | — | — | 圖檔留在資料夾（未刪），資料包仍會載入，主線可決定刪除 | — |
| assets/final/sets/square_a1/shopwall_v01.png | 景片（不透明牆面；562×577，150 px／單位＝3.75×3.85 單位） | 小鎮廣場（燈籠店門面） | 修正第 2 輪：燈籠店的窗嵌進店面牆——紙瓦屋簷、米色灰泥牆（同騎樓柱子色系、紙纖維）、左右木柱、木裙板、右邊店門（淺杏色門簾，沒有字）、門上一盞不亮的小紙燈籠；在窗紙後、騎樓柱子前（z −1.59），遮住柱子的石座與台階 | a1_c001–a1_c008（square_a1 景） | 程式繪製（review/G5/a0/scripts/build_fix2_art.py） | 本專案自製 | 驗收「窗戶像獨立立在廣場上的窗框」（b1r2_regress a1 一般問題 2）；無文字、無標誌；只接受影子、不投影子 | v01 |
| assets/final/chr-pinan_pose-sit-lantern-look1_v01.png、chr-pinan_pose-sit-lantern-look2_v01.png | 立牌姿勢（透明；597×1454，和 sit_lantern 同尺寸） | 品安 | G6 精修：品安偷偷回頭看柱子——母版 sit_lantern 的眼珠往左上移（look1 一半、look2 到左上，眼白補在下方，上眼線蓋住）、頭以下巴脖子交界為支點抬起（look1 6°、look2 12°；y＜400 全轉、400–475 平順漸變，脖子沒有接縫），燈籠、手、身體不動；存成鏡像，和 sit_lantern_back 一樣用 facing −1 | a1_c004（結尾 a1_pinan 鏡頭：look1→look2 停 1.0 秒→look1→sit_lantern_back，0 秒換圖） | 程式加工（review/G5/a0/scripts/build_polish_art.py pinan）；來源為本專案母版 | 本專案自製 | b1r3_failed a1 一般問題 3「看不出在看柱子」；show_characters.json 品安 poses 加 sit_lantern_look1／look2（feet、headTop 同 sit_lantern_back，沒有臉部換片） | v01 |
