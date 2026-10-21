# 阿樂叔叔分件紙偶 v04：給引擎代理

來源：`assets/parts/ale_v03`（直接從正式母版 `chr-ale_master_v02.png` 切出的部件）。這一版只做三件事：修接縫、清理困惑頭、裁掉多餘的透明邊。部件的尺寸和比例沒有改動，所以站姿疊回去仍然和母版逐像素相同。產生這些檔案的腳本是 `review/G4/art/scripts/build_ale_rig.py`。

## 1. 檔案

| 檔案 | 用途 |
|---|---|
| `chr-ale_<部件>_v04.png` ×12 | 部件圖。每張裁到外框再留 16 px 透明邊，透明處做了顏色外擴。部件名稱的底線在檔名裡改成連字號，例如 `upper_arm_r` 的檔名是 `chr-ale_upper-arm-r_v04.png`，打包後的 id 是 `rig/chr-ale_upper-arm-r`（tools/pack.mjs 以相對 assets/final 的路徑當 id）。 |
| `chr-ale_head-worried_v04.png` | 困惑頭，a2 整段都用這顆。它和 `head` 共用同一個頸部樞紐（母版座標 530,330）。 |
| `chr-ale_<部件>-outline_v04.png` ×13 | 描邊底圖：白色紙芯邊 11 px，外側再加 1.6 px 深色細線。尺寸和對應部件完全相同，套用同一個變換即可。 |
| `ale_rig.json`（JSON id `rig/ale_rig`） | 每個部件的尺寸、`origin_master`（部件圖左上角在母版上的座標）、`pivot_local`（樞紐在部件圖上的位置）、`parent`、`joint_in_parent_local`（樞紐在父部件圖上的位置）、層序，以及接縫修正的紀錄。 |
| `ale_attach.json`（JSON id `rig/ale_attach`） | 操偶線的扣點：`wrist_back`、`elbow_out`、`knee_front`。a2 只用這三點。另一側的三點也附上，給後段六條線都扣上時用。 |
| `../face/ale/face.json` | 臉部換片（嘴 5 片、眼 3 片），座標相對 `chr-ale_head-worried_v04.png`。 |
| `../g4_manifest.json` 的 `a2_ale_key_poses` | a2 的六個關鍵姿勢，已換算好 three.js 的弧度。 |

## 2. 座標與角度

- 部件圖的像素座標以左上角為原點，y 向下。母版畫布是 1024×1656，站姿身高約 1610 px。
- 世界尺度的建議值是母版 1 px = 0.002857 單位，所以站姿高 4.6 單位，在中景 1080p 下約 640 px，和 G2 v04 合成的比例相同。身體中線（母版 x=510）放在世界 x=-2.2，腳底（母版 y=1631）放在 y=0。
- 角度一律是**相對父部件**的旋轉，單位是度，正值代表畫面上順時針。three.js 的 y 軸向上、逆時針為正，請用 `rad = -deg·π/180` 換算；manifest 裡的 `rad_threejs` 已經算好。
- `root` 寫成 `(dx_px, dy_px, deg, "hip_mid")`，作用在軀幹上，所有子部件跟著移動。`dy_px` 為正代表往下（坐下），換成世界座標是 `-dy_px × 0.002857`。`hip_mid` 在母版 (510, 1000)，也就是軀幹圖上的 (243, 749)。
- 換成 `RigSpec`（`rig.ts`）時，設 `u = 0.002857`：
  - 部件 `rect = [-pivot_local.x·u, -(size.y - pivot_local.y)·u, size.x·u, size.y·u]`。這樣樞紐就是原點，並且已經把 y 翻轉成向上。
  - 子部件 `at = [(joint_in_parent_local.x - 父.pivot_local.x)·u, -(joint_in_parent_local.y - 父.pivot_local.y)·u]`。
  - 軀幹沒有關節，就用 `hip_mid` (243, 749) 當樞紐。

## 3. 層序與描邊

由後往前：`shin_l, thigh_l, shin_r, thigh_r, upper_arm_l, head, upper_arm_r, torso, forearm_l, hand_l, forearm_r, hand_r`。

1. 先畫這個角色所有部件的 `-outline` 圖，renderOrder 用角色基準 +0，而且要比所有部件都小。
2. 再依上面的順序畫部件。

這樣一來，白邊只會出現在擺好姿勢後的整體外輪廓上，部件之間保留深色細接縫，不會冒出一圈圈白邊。請不要再用 `cutPaperMaterial` 幫每個部件各自加白邊。

## 4. 舌片弧線修正（G2 帶進 G4 的問題 3）

- **肩**：上臂放在軀幹後層，所以肩部的圓舌片永遠藏在軀幹的肩球後面。這次把軀幹右肩球、左肩球裡的深色弧線，包括母版原有的手臂輪廓線和舌片邊線，都改成鄰近的袖子顏色：右肩 1426 px，左肩 1137 px。現在手臂舉起（wave）或被拉向旁邊（pulled）時，肩膀看起來是連續的袖子，不會露出一圈圓紙。
- **膝**：左右大腿下端圓舌片的深色邊線改成鄰近的褲子顏色（各約 900 px）。膝蓋彎起來時看起來是膝頭，不是一片圓紙。
- **肘、腕**：前臂捲起的袖口本來就蓋住手肘舌片，這兩處不用改。
- **髖**：a2 全程被工作台擋住。
- 對照圖：`review/G4/art/ale_a2_poses_before.png`（原部件）和 `ale_a2_poses_fixed.png`（v04）。每個姿勢都附右肩、右肘、左膝、左肩的特寫。

## 5. 困惑頭清理

沿用 `tools/rig_ale_v03.make_worried_head` 的對位（上 70% 輪廓 IoU 0.97），另外做了幾項清理：

- 生成圖頸部殘留的圓弧線和陰影線改成膚色，共 440 px。
- 頭內的白色殘點清掉，共 226 px。
- 零碎小塊移除，共 71 px。

臉、膚色、髮型都沒有改動。

## 6. a2 姿勢（數值在 `g4_manifest.json` 的 `a2_ale_key_poses`）

| 姿勢 | 用在哪裡 | 要點 |
|---|---|---|
| `sit` | a2_c001 結尾、a2_c002 開頭 | 坐在高凳上（root dy +80）。右手靠在**身體左外側**的桌面上，這樣腕、肘的線往上走都在身體外面，不會橫過胸前或頭頸。左腿從桌子右端露出，膝前紙環看得到。 |
| `wave` | 「我想揮手」 | 右手先抬起，表現意圖。 |
| `pulled` | 線繃緊 | 右手被拉向畫面左邊（危險方位），手腕下垂。 |
| `halfstand` | 想站起來 | 臀部抬高，身體前傾 4°。 |
| `kneetug` | 膝蓋被扯 | 左膝被提起，腳底離地約 160 px，身體往後晃 5°。左手伸向桌面。 |
| `hold` | 停格 | 左手掌心朝下壓在桌面右端（手腕在母版 598,806）。左膝在桌子右邊，紙環看得到。 |

- 用 `ale_a2_poses.py` 檢查過：每個姿勢著地的腳離地板都在 ±8 px 以內，`kneetug` 的左腳是刻意離地。
- 右腿被桌子擋住，角度只是讓腳不穿過地板。
- 左手扶桌由兩節 IK 算出，手肘朝外。如果手肘收進身體，前臂會像從胸口長出來，所以不採用。
- 工作台的位置固定在：桌面上緣 = 母版 y=830（世界 y≈2.29）、右端 = 母版 x=705（世界 x≈-1.64）、z≈0.3（阿樂前面一點）。**不要把桌子放到 fore 層（z=2.4）**，否則推鏡、搖鏡時的視差會讓手扶的位置對不上。

## 7. 操偶線扣點（`ale_attach.json`）

- `wrist_back`：右前臂靠手腕處，從外側緣往內 9 px（`forearm_r` 局部 69,210）。a2_c001 的 L1 細線也扣在這裡。
- `elbow_out`：右上臂靠手肘處，從外側緣往內 10 px（`upper_arm_r` 局部 39,279）。**不扣手肘內側。**
- `knee_front`：左大腿下端膝頭中央（`thigh_l` 局部 87.5,330）。
- 每一點都附 `from_pivot_px`（相對樞紐），可以直接換成 `AnchorSpec.local`：`[dx·u, -dy·u]`。
- 線往上延伸出畫面。腕、肘的線近乎垂直、略偏畫面左；膝的線往右上斜出（`perform.ts` 的 STRING_LEAN 2.6 可以沿用）。在試排（`review/G4/art/a2_layout_test.png`）裡，三條線都沒有經過孩子，也沒有經過阿樂的頭頸。

## 8. 還沒有的東西（照實寫）

- **手型換片**：目前只有母版的放鬆手（H1）。劇本的 H3（張開手揮手）和 H7（掌心朝下扶桌）還沒有做，a2 先用 H1 轉角度代替：`wave` 手掌朝上舉起，`hold` 手平放在桌面。要做的話，需要另外生成左右手各 2 片，比照母版畫布和比例。
- **坐姿腿**：不另外做一組。坐姿用大腿旋轉加桌子遮擋（角色表 1.3 寫的「坐姿腿」由此代替）。

## 9. v05 修正（G4 修正第 1 輪，2026-10-21，美術代理）

v04 檔案都保留；`tools/pack.mjs` 每個 id 取最新版本，所以下面這些檔案一放進來，打包就會自動換用，**圖像 id 不變**。

| 檔案 | 改了什麼 | 引擎要知道的事 |
|---|---|---|
| `chr-ale_forearm-{l,r}_v05.png`、`-outline_v05.png` | 移除切件時帶進來的襯衫碎片（左 403 px、右 1217 px）；沿外形補 3 px 深棕線稿（手腕圓舌片內不畫）；膚色區補紙纖維與外緣輕微暗邊。檢查圖 `review/G4/art/forearm_fix_v05.png` | 尺寸、樞紐、原點與 v04 完全相同，不用改程式 |
| `chr-ale_head-greet_v05.png`、`-outline_v05.png` | 新的替換頭 `head_greet`＝X2「想打招呼」：一般頭（微笑）的眉毛上抬 9 px、外端再抬 2 px。其餘像素不動。檢查圖 `review/G4/art/ale_head_greet_v05.png` | `ale_rig_v05.json` 的 `parts.head_greet`（命名規則和 `head_worried` 一樣，`partsFromRigJson` 會自動當成 head 的替換部件）。`perform.ts` 目前只在 head／head_worried 之間切換，要加一個表情（例如 `emotion: 'greet'` → 顯示 head_greet）。眼、嘴位置和 head 一樣，臉部換片直接用 `FALLBACK_FACES['ale:head']` |
| `ale_rig_v05.json` | 同 v04，只把前臂換成 v05 檔名，並加上 `head_greet` | JSON id 仍是 `rig/ale_rig` |
| `ale_attach_v05.json` | 扣點改成**整個紙環落在肢體剪影內**（離外形邊緣 ≥ 26.5 母版 px）：腕背 `forearm_r` (82,184)、肘外 `upper_arm_r` (54,265)、膝前 `thigh_l` (88,330)。六個 a2 姿勢都驗過（`review/G4/art/ale_attach_v05_check.json`、`ale_a2_poses_v05.png`） | JSON id 仍是 `rig/ale_attach`；`ring` 欄位寫了紙環與線的建議尺寸（見下） |

### 操偶線與紙環的畫法（問題 22、23、34）

- 線的貼圖：`assets/final/tex-string-rope_v01.png`（id `tex-string-rope`，64×256，不透明）。u 跨線寬（u=0 在畫面左、受光邊在左），v 沿線長、上下四方連續，一個週期等於 4 個線寬，和 `strings.ts` 現在的 `vRepeat = len / (width·4)` 相同。內容：兩側深灰邊（各 12/64）、左側淡色受光邊、淡灰紙繩身（平均 sRGB≈178）、斜向扭紋與紙纖維。請用 `RepeatWrapping`、mipmap、線性過濾，取代 `ropeTexture()` 的程式貼圖。
- 線寬：建議 `STRING_WIDTH = 0.043`（g4_mid 中景約 8.0 px、錨點近景約 10.5 px），落在規格的 6–10 px。現在的 0.066 在中景是 12.5 px。
- 紙環貼圖：`assets/final/tex-string-ring_v01.png`（id `tex-string-ring`，128×128，透明）。圓環：外側深灰細線、白色紙芯邊、淡灰紙環身、內側深灰細線，中間透明（看得到肢體）。請把 `ring` 改成**正方形**平面，直徑 `0.103` 世界單位（約 2.4 倍線寬，中景約 19 px），不隨肢體旋轉、不用 `ringWidth` 拉長。原本的矩形紙帶不再使用。
- 線的下端：停在紙環上緣（扣點往線的方向退 0.4 倍直徑），紙環畫在部件與線的上面。
- 預覽：`review/G4/art/string_preview_v01.png`（6／8／10.5 px 畫在後牆、皮膚、工作褲、白襯衫上，含投影 v2）、`review/G4/art/ale_a2_poses_v05.png`（六個姿勢的中景 1:1）。
- 明度（`review/G4/art/string_tex_v01.json`）：線身改成淡灰（規格 sRGB 170–200）之後，線身對淺牆的 ΔL* 約 18（投影 v2 約 13）、對阿樂皮膚約 3；可讀性改由兩側深灰邊提供（深灰邊對牆 ΔL* 64／投影 v2 44，對皮膚 50／32）。對工作褲（膝前線）的線身 ΔL* 由舊版約 10 提高到約 32（投影 v2 約 23）。`tools/capture_probe.py` 現在只取線中心像素、門檻 ΔL* ≥ 25，套在淡灰紙繩上會在牆與皮膚前判不通過；建議改成同時列出「線身」與「深灰邊」對背景的 ΔL*，取較大者判定（要主線決定，見 notes）。

## 10. 修正第 2 輪（G4 修正第 2 輪，2026-10-21，美術代理）

舊檔都保留；圖像 id 不含版本號，`tools/pack.mjs` 自動取最新版本，**引擎程式與 face JSON 的 shapes 都不必改**。

| 檔案 | 改了什麼 | 引擎要知道的事 |
|---|---|---|
| `face/xiaoqing/chr-xiaoqing_eyes_half_v02.png`、`chr-xiaoqing_eyes_closed_v03.png`（reach）；`chr-xiaoqing_{watch,palm,worried}-eyes_half_v02.png`、`-eyes_closed_v02.png`；`face/xiaoyu/chr-xiaoyu_eyes_half_v02.png`、`chr-xiaoyu_eyes_closed_v03.png` | 第 1 輪的眼睛遮罩把碰到髮絲的整條睫毛判成保護線，畫面左側那隻眼沒有被填補、也沒畫上眼皮線，眨眼時一眼閉一眼睜（看起來像眨單眼）或只剩淡化殘影。這一版兩隻眼都整個重填成皮膚，再畫同款的線：閉眼＝近乎平直、略往下彎的中性閉眼線（不是笑眼）；半閉＝上半眼改眼皮、下半眼保留原圖。檢查：`review/G4/art/blink_check_r2.json`（每隻眼殘留 ≤0.3%、閉眼線 ≥103 px）、`face_sheet_xq_v06.png`、`face_sheet_v06.png`、`blink_zoom_r2.png` | 錨點、尺寸、圖像 id 與上一版完全相同。兩眼在同一張換片裡，所以一換片就是兩眼同時閉、同時開；**眨眼和翻面錯開 0.3 秒（問題 10）是引擎的事**，素材做不到 |
| `face/xiaoqing/face_v04.json`（id `face/xiaoqing/face`） | 原生 FaceConfig，`perPose`、`headLayer`、空槽與 v03 完全相同，只更新 `version`、`change_log`，另加 `reach_pieces`（登記 reach 的換片檔名，引擎不讀） | 不用改程式 |
| `face/xiaoyu/face_v03.json`、`face/xiaoqing/face-{watch,palm,worried}_v02.json` | 素材代理格式，只把 eyes_half／eyes_closed 的 `file`、`changed_px` 換成新版本 | 不用改程式 |
| `tex-string-ring_v02.png`（id `tex-string-ring`） | 灰色、像金屬墊圈的 v01 改成**米白紙環**：紙面 sRGB≈(251,242,222)（色相約 41°、彩度約 12%），整片同色、沒有放射漸層或高光；細纖維紙紋＋左下紙帶接口細線；外緣、內緣暖深棕描邊；整個環往右下偏移 (5,6) px 的暖棕厚紙側邊當單側陰影。外半徑 0.88、孔半徑 0.42（貼圖半寬為 1）。示意 `review/G4/art/ring_crops_v02_preview.png`、量測 `ring_tex_v02.json` | 貼圖格式（128×128 透明、alphaTest 0.5、正方形平面、直徑 0.103、正對鏡頭不旋轉）都不變。陰影畫在貼圖裡、方向固定右下，所以紙環**不要旋轉**。`ringMat.color.setScalar(light)` 在 light < 0.91 時會讓環身低於 sRGB 220。退路 `ringTexture()` 仍是灰環（正式包用不到） |

重擷取後量實際畫面的紙環：`/opt/anaconda3/bin/python3 review/G4/art/scripts/make_ring_tex_v02.py --measure review/G4/pack/capture` → `review/G4/pack/capture/ring_body_stats.json`（環身平均亮度、色相、彩度）。
