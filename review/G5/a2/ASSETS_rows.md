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

## G5 修正第 1 輪（2026-10-21 晚，a2 代理）

| 檔名 | 類型 | 角色／場景 | 部件／表情 | 使用 cue | 來源／生成參考 | 授權 | 檢視結果 | 版本 |
|---|---|---|---|---|---|---|---|---|
| assets/final/chr-ye_pose-crouchphone_v01.png | 表演姿勢圖（透明；862×1449） | ye | crouchphone：蹲姿、左手（畫面右）拿手機貼耳等人接，另一手放在膝上；表情擔心 | a2_c012 | Codex image_gen（review/G5/a2/raw/a2_ye_phone_v01.png，參考 G2a S4、chr-ye_pose-crouch_v01、chr-ye_master_v01）；裁到不透明範圍＋16 px、清掉 alpha<32；原圖 assets/generated/chr-ye_pose-crouchphone_v01.png。show_characters.json `ye.poses.crouchphone`（headTop −743，依 crouch 比例換算） | 使用者 ChatGPT 方案生成圖 | 手機是無字的深灰圓角長方形，沒有螢幕畫面、按鍵、標誌；識別證只有手捧愛心；臉、髮型、制服與 crouch 一致 | v01 |
| assets/final/sets/a2_memory/mem-box_v02.png | 景片（透明毛邊紙卡；1040×800） | a2_memory | 褪色回想小窗①（v02）：直接用 a1_c003 盒子特寫貼圖（sets/square_a1/boxclose，含右上角的灰線頭），放大到小窗寬 80%、輕微褪色 | a2_c003 | 程式：build_a2_art.py `mem_box_v2`（`python3 build_a2_art.py v02`） | 衍生自使用者 ChatGPT 方案生成圖＋程式繪製 | 無文字；灰線頭清楚 | v02 |
| assets/final/sets/a2_window/sil-ale-hand_v02.png | 剪影（透明；636×310） | a2_window | 阿樂叔叔伸手接盒子的手（v02）：張開的手掌、五指分開、捲起的袖口；指尖在圖上 (25, 202) | a2_c013 | 程式：build_a2_art.py `sil_ale_hand_v2`（多邊形＋圓頭膠囊，4 倍超取樣） | 程式繪製（本專案） | 不是塊狀或爪子；在指尖碰到盒子前小窗就收起 | v02 |
| （程式）app/src/sets/a2_shop.ts | 程式景 | a2_shop | G4 燈籠店＋L1 短線（腕線頂點透明度）、竹篾、手部近景小台（阿樂叔叔分件手臂＋白紙芯外框圖、程式燈籠紙四態與紙團、同款紙繩與紙環）、求助站（a2_helpdesk/layout.json 建在 x＝40） | a2_c001、a2_c004–a2_c012 | 程式 | 本專案 | a2_c004 與 workshop_g4 逐像素相同（7 格比對差 0） | — |
| （程式）app/src/sets/a2_window.ts | 程式景 | a2_window | 加開著的店門暖光門口（孩子身後投影亮度 ≥ 0.50）、接盒子剪影手 v02 的位置 | a2_c013 | 程式 | 本專案 | — | — |
| assets/final/sets/a2_shop/insert-ale-forearm-{r,l}_v01.png、insert-ale-hand-{r,l}_v01.png 與各自的 -outline_v01.png | 分件（透明；母版 2 倍：前臂 360×590／296×608、手 270×342／238×294） | a2_shop 手部近景 | 修正第 2 輪：阿樂母版 forearm（v05）／hand（v04）分件放大 2 倍處理版——全劇共用紙纖維紋理（對比 1.6 倍）、邊緣往內 6 px 漸暗 10%（紙片厚度）、2 px 深色紙邊；白紙芯外框加紙纖維與 1.5 px 淡灰外緣。形狀不改 | a2_c008（開頭手部近景） | 程式加工（review/G5/a2/scripts/build_fix2_a2_art.py）；來源為本專案母版分件 | 本專案自製 | 驗收「手部近景平塗、像橡膠」（b1r2_regress a2 一般問題 5）；紙環同時移到腕背橫紋上（a2_shop.ts buildArm wb） | v01 |
| assets/final/sets/a2_helpdesk/layout.json（修改） | 景設定 | 求助站 | 修正第 2 輪：地面 #d9c3a0→#e8d7b8、後排騎樓自發光 0.3→0.5、帳篷與木箱自發光 0.2：求助站切回店內時全畫面亮度 0.48→0.52（相差 < 10%，原 0.41→0.52） | a2_c012 | 設定檔（修改前備份 review/G5/a2/scripts/a2_helpdesk_layout_fix1_base.json） | — | 主線更正裁定「切場亮度漸變」；不加第二次切黑（第 1 輪導演 6） | — |
| assets/final/sets/a2_shop/insert-ale-hand-{r,l}_v02.png | 分件（透明；母版 2 倍：270×342／238×294） | a2_shop 手部近景 | G6 精修（取代 v01；前臂與外框沿用 v01）：手的上緣切口（疊在前臂上的接縫）原本 2 列深色墨線＋深色紙邊 → 3 px 米白紙邊（紙片疊層的切口）；指縫、指節沿內部線條加柔和陰影（約 4 px、最深 −20%）、線條補深；手心裡的淺色接合舌片改成陰影中的膚色；其餘同 v01（紙纖維、6 px 厚度、外緣 2 px 深色紙邊） | a2_c008（開頭手部近景） | 程式加工（review/G5/a0/scripts/build_polish_art.py hands）；來源為本專案母版分件 chr-ale_hand-{r,l}_v04 | 本專案自製 | b1r3_failed a2 一般問題 3「右手腕分件接縫線、手指簡化」 | v02 |
