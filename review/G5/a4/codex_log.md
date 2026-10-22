# 第四幕 Codex 生圖紀錄

## G5 修正第 1 輪（2026-10-21）
- 生成 0 張（額度上限 2 張，沒有用）。驗收指出的美術問題都用程式繪製解決，和第四幕 v01 道具同一套 paperdraw 紙紋畫法：
  - 找找看 3 的竹編貓頭骨架（兩耳＋頭框；一小角版＝帆布鼓起只露左耳尖）：assets/final/sets/gate/set-gate_a4-truck_v01.png、set-gate_a4-truck-tip_v01.png
  - 遠景家長牽孩子（淺紙色背影小紙人）：set-gate_a4-walkers-{a,b}_v02.png
  - 背光剪影（手剪紙輪廓＋紙纖維毛邊）：assets/final/sets/a4_roadmap/set-a4map_sil-car_v02.png、set-a4map_sil-walker_v02.png
  - 腳本：review/G5/a4/scripts/build_a4_art_fix1.py

## G5 修正第 2 輪（2026-10-22，第四幕＋驗收包工具）
- 生成 0 張（上限 2 張，沒有用）。這一輪只改排戲（淡入淡出、鏡頭曝光、鏡位斜角）與景的程式動作（gate.ts：lift 提亮、gateOpen 折疊門收起、zzpatch 地板補片），沒有新圖。

## G6 精修（2026-10-22，第四幕＋共用小修）
- 生成 0 張（上限 2 張，沒有用）。這一輪只改排戲（a4_c002 轉場、a4_c001 窗景燈與 a4_deep）、鏡位（a4_map）、景的程式動作（gate.ts setTrack haze／hazeStreet；a4_roadmap.ts 原點地圖補片、小車起點），沒有新圖。
