# G5 修正第 1 輪｜共用元件代理｜ASSETS.md 待合併列（主線合併）

| 檔名 | 類型 | 角色／場景 | 部件 | 使用 cue | 來源 | 授權 | 檢視結果 | 版本 |
|---|---|---|---|---|---|---|---|---|
| assets/final/ui/ui-speaker_{zhezhe,pinan,nurse,teacher,guard,inviter}_v01.png | 字幕說話者小頭像（128×128 透明圓形徽章） | 折折、品安、葉護理師、林老師、陳伯伯、邀請者 | 折折＝從折折程式畫面（review/G5/zhezhe/look.png）裁頭部；品安、葉護理師、林老師、陳伯伯＝從正式母版 chr-*_master_v01.png 裁頭肩；邀請者＝中性灰紙手掌（程式畫，沒有臉、膚色、飾品） | 全劇字幕（v1.2 第 15.3 節；b1_art a2 一般問題 5） | review/G5/engine/scripts/make_speaker_icons_fix1.py（沿用 G4 make_speaker_icons.py 的徽章） | 原創（程式產生）／使用者 ChatGPT 方案生成（母版裁切） | 圖中無字；字幕框深底上與投影 v2 都清楚（review/G5/engine/art/speaker_icons_fix1.png） | v01 |
| app/src/stage/lamps.ts（程式繪製，沒有圖檔） | 台口八盞燈（剪紙紙燈＋木條＋柔和光暈） | 全劇台口 | 未亮灰白紙色＋深棕細邊；亮＝暖黃＋加法光暈 | 全劇（quiz 鏡位看得到） | 程式繪製（canvas） | 原創 | quiz 鏡位 1080p y≈13–90 px、寬約畫面 60%；只隨 world.lamps 單向漸變 | — |
