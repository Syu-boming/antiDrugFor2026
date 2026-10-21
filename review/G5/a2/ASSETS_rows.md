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
