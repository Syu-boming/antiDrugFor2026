"""G4 美術：assets/final/g4_manifest.json（每個素材的 id、檔案、層、建議舞台座標與縮放、錨點）。
座標照 app/src/stage/layers.ts：x 向右、y 向上、z 朝觀眾；地面 y=0；中景相機下 z=0 平面 1 單位 ≈ 139 px@1080p。
數值來自 layout_test.py 的試排（review/G4/art/contrast_g4.json）與各處理腳本的紀錄。
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(Path(__file__).parent))
import ale_a2_poses as A  # noqa: E402

ART = ROOT / "review/G4/art"
FIN = ROOT / "assets/final"
lay = json.loads((ART / "contrast_g4.json").read_text())
pl = lay["placement"]
sp = json.loads((ART / "set_process.json").read_text())
wall = json.loads((ART / "wall_extend.json").read_text())
kc = json.loads((ART / "kids_crop.json").read_text())
kh = json.loads((ART / "kid_heads.json").read_text())
rig = json.loads((FIN / "rig/ale_rig.json").read_text())
A.apply_ik()


def pid(f):
    s = Path(f).stem
    return s.rsplit("_v", 1)[0] if "_v" in s else s


assets = []


def add(**k):
    assets.append(k)


# ---- 遠景
add(id="bg-workshop-back", file="assets/final/bg-workshop-back_v02.jpg", layer="遠", engine_layer="backdrop", z=-5.0,
    size_px=wall["size"], world_size=[22.0, round(22.0 * wall["size"][1] / wall["size"][0], 3)],
    anchor={"px": [wall["size"][0] / 2, wall["size"][1]], "meaning": "下緣中點＝地板線", "world": [0.0, 0.0, -5.0]},
    units_per_px=round(22.0 / wall["size"][0], 6),
    notes="騎樓下燈籠工作室後牆（淺暖米色灰泥＋淺木柱、上方層架放未點亮的紙燈籠與竹篾）。蓋滿中景與大全景。右側門洞（世界 x≈6.9–7.9）是孩子 a2_c012 往右跑出去的方向。"
          "柱子已提亮 40%，角色軀幹高度一帶投影 v2 亮度中位 0.59。不透明 JPG，色彩空間 sRGB。",
    cues=["a2_c001", "a2_c002", "a2_c004", "a2_c008", "a2_c012"])
add(id="bg-workshop-floor", file="assets/final/bg-workshop-floor_v01.jpg", layer="遠", engine_layer="backdrop（地板平面）", z=None,
    size_px=[1024, 512], world_size=[8.0, 4.0], anchor={"px": [0, 0], "meaning": "四方連續貼圖", "world": None}, units_per_px=round(8 / 1024, 6),
    notes="取代 sets.ts 的程式地板（#b98d62 偏暗）。y=0 地板平面，RepeatWrapping；1 單位＝128 px（木板寬約 0.5 單位，沿 x 方向）。淺暖色讓孩子的腳與鞋分得開。",
    cues=["a2_c001", "a2_c002", "a2_c004"])
# ---- 中景
L = pl["lanterns"]
add(id="bg-workshop-lanterns", file="assets/final/bg-workshop-lanterns_v01.png", layer="中", engine_layer="mid", z=L["z"],
    size_px=sp["bg-workshop-lanterns"]["final_size"], world_size=[L["world_w"], round(L["world_w"] * 414 / 1536, 3)],
    anchor={"px": [0, 0], "meaning": "左上角", "world": [L["left_top"][0], L["left_top"][1], L["z"]]},
    units_per_px=round(L["world_w"] / 1536, 6),
    notes="竹竿上掛 5 盞未點亮的紙燈籠（透明 PNG）。建議只放在畫面右半（孩子上方）、竹竿在中景畫面上緣下方約 0.3 單位，讓阿樂上方留白給落下的操偶線；燈籠繩很短、竹竿一定要在畫面內，避免被看成操偶線。可選層：大全景時可往左移。",
    cues=["a2_c001", "a2_c002", "a2_c004"])
# ---- 前景
T = pl["table"]
st = sp["bg-workshop-table"]
add(id="bg-workshop-table", file="assets/final/bg-workshop-table_v02.png", layer="前景", engine_layer="actors 層內、阿樂前面（不是 fore 層）", z=T["z"],
    size_px=st["final_size"], world_size=[T["world_w"], round(st["final_size"][1] * T["units_per_px"], 3)],
    anchor={"px": [st["table_body_x_px"][1], st["table_top_y_px"]], "meaning": "桌面上緣右端（阿樂左手扶的位置）",
            "world": [T["right_end_x"], T["top_surface_y"], T["z"]]},
    units_per_px=T["units_per_px"],
    notes="燈籠師傅工作台（厚卡紙，看得到桌面切口的紙層；桌上竹篾、燈籠紙、小剪刀、未糊紙的燈籠骨架；右三分之一桌面淨空給手扶）。"
          "放在阿樂前面 z≈0.3（同一層、不要放 fore z=2.4，否則推鏡、搖鏡時視差會讓『手扶桌面』對不上）。桌面高＝阿樂母版 y=830（世界 y≈2.29）、右端＝母版 x=705。"
          "坐姿時桌子擋住阿樂的右腿與臀部，左腿從桌子右端露出（膝前紙環看得到）。",
    cues=["a2_c001", "a2_c002", "a2_c004", "a2_c008"])
Wg = pl["wings"]
add(id="bg-workshop-wing", file="assets/final/bg-workshop-wing_v01.png", layer="前景", engine_layer="fore", z=Wg["z"],
    size_px=sp["bg-workshop-wing"]["final_size"], world_size=[Wg["world_w"], Wg["world_h"]],
    anchor={"px": [0, sp["bg-workshop-wing"]["final_size"][1]], "meaning": "左下角", "world": [Wg["left"][0], 0.0, Wg["z"]]},
    units_per_px=round(Wg["world_h"] / 1536, 6), mirror_copy={"flip_x": True, "anchor_meaning": "右下角", "world": [Wg["right_mirrored"][0] + Wg["world_w"], 0.0, Wg["z"]]},
    notes="側翼前景：一束竹子＋腳邊紙屑（透明 PNG）。左邊原圖、右邊水平鏡射一份。只佔畫面左右邊緣，不擋說話者的臉；紙屑在字幕區但不擋字幕底板中央。",
    cues=["a2_c001", "a2_c002", "a2_c004"])
# ---- 台口／介面貼圖
add(id="tex-curtain-paper", file="assets/final/tex-curtain-paper_v01.png", layer="台口", engine_layer="curtain", z=4.0,
    size_px=[512, 1024], world_size=None, anchor={"px": [0, 0], "meaning": "左右四方連續貼圖（RepeatWrapping S）", "world": None}, units_per_px=None,
    notes="摺層紙布幕貼圖（酒紅和紙、直向纖維、下緣深色滾邊＋芥末黃紙條）。不烘焙光影，摺層明暗由 curtain.ts 的幾何與燈光產生。無字。",
    cues=["片頭", "片尾"])
add(id="tex-titlecard-paper", file="assets/final/tex-titlecard-paper_v01.png", layer="介面", engine_layer="overlay（署名卡）", z=None,
    size_px=[1600, 900], world_size=None, anchor={"px": [800, 450], "meaning": "中心", "world": None}, units_per_px=None,
    notes="署名卡底紙（奶油色厚卡紙＋細框＋四角幾何剪紙花）。圖裡沒有任何字：「許博明老師製作」一定由劇場程式用字型排在中央。片頭、片尾用同一張。",
    cues=["片頭", "片尾"])
# ---- 孩子
for name, zh, cue_pose in (("xiaoqing", "小晴", "a2_c002 伸手提醒（指向叔叔手腕的線）"), ("xiaoyu", "小宇", "a2_c002 擔心後退半步")):
    P = pl[name]
    f = [k for k in kc if k.startswith(f"chr-{name}_pose")][0]
    h = kh[name]
    add(id=pid(f), file=f"assets/final/{f}", layer="角色", engine_layer="actors", z=P["z"],
        size_px=kc[f]["size"], world_size=[round(kc[f]["size"][0] * P["units_per_px"], 3), round(kc[f]["size"][1] * P["units_per_px"], 3)],
        anchor={"px": P["feet_anchor_px"], "meaning": "腳底中點（最低 40 列的左右範圍中點）", "world": [P["feet_world_x"], 0.0, P["z"]]},
        units_per_px=P["units_per_px"], height_units=P["height_units"],
        split_layers={"body": {"id": pid(h["body_file"]), "file": h["body_file"], "same_frame_as_full": True},
                      "head": {"id": pid(h["head_file"]), "file": h["head_file"], "offset_px": h["head_offset_px"], "pivot_px_head": h["pivot_px_head"],
                               "pivot_px_full": h["pivot_px_full"], "turn_range_deg": h["turn_range_deg"]}},
        face=f"assets/final/face/{name}/face.json",
        notes=f"{zh}：{cue_pose}。整張圖或『身體＋頭』兩層擇一（兩層 0° 疊回與原圖只差 ≤12 px 邊緣）。呼吸：身體層以腳底為錨點 scaleY 1.000–1.008、週期 3–4 秒；轉頭：頭層繞 pivot ±2.5° 以內；眨眼與對嘴見 face.json。",
        cues=["a2_c002", "a2_c004"])
for name, zh in (("xiaoqing", "小晴"), ("xiaoyu", "小宇")):
    f = f"chr-{name}_master_v04.png"
    up = pl[name]["height_units"] / kc[f"chr-{name}_pose-reach-worried_v04.png" if name == "xiaoqing" else f"chr-{name}_pose-stepback-surprised_v04.png"]["height_px"]
    up = round(pl[name]["height_units"] * (1.0) / kc[f]["height_px"], 6)
    add(id=pid(f), file=f"assets/final/{f}", layer="角色", engine_layer="actors", z=pl[name]["z"],
        size_px=kc[f]["size"], world_size=[round(kc[f]["size"][0] * up, 3), round(kc[f]["size"][1] * up, 3)],
        anchor={"px": kc[f]["feet_bottom_px"], "meaning": "腳底中點", "world": [pl[name]["feet_world_x"], 0.0, pl[name]["z"]]},
        units_per_px=up, height_units=pl[name]["height_units"],
        notes=f"{zh}站姿／中性（v04 母版）。G4 代表鏡頭不一定用到；需要站姿時用，臉部換片目前只做在姿勢圖頭上（母版是微笑臉，換片待 G5）。",
        cues=["a2_c001（可選）"])
# ---- 阿樂
att = json.loads((FIN / "rig/ale_attach.json").read_text())["points"]
_r = A.R.Rig()
U, AX = pl["ale"]["master_px_to_units"], pl["ale"]["body_center_x"]
poses = {}
for n, p in A.POSES.items():
    q = {k: v for k, v in p.items() if k != "root"}
    dx, dy, th, pv = p["root"]
    poses[n] = {"deg_screen_cw": q, "root": {"dx_px": dx, "dy_px": dy, "deg_screen_cw": th, "pivot": pv},
                "rad_threejs": {k: round(-v * math.pi / 180, 4) for k, v in q.items()}}
    M = _r.world(p)
    wp = {}
    for key in ("wrist_back", "elbow_out", "knee_front"):
        mp = A.R.apply(M[att[key]["part"]], att[key]["master_px"])
        wp[key] = [round(AX + (float(mp[0]) - 510) * U, 3), round((1631 - float(mp[1])) * U, 3), 0.0]
    hp = A.R.apply(M["head"], A.R.PIV["neck"])
    wp["neck"] = [round(AX + (float(hp[0]) - 510) * U, 3), round((1631 - float(hp[1])) * U, 3), 0.0]
    poses[n]["attach_world"] = wp
add(id="rig/ale_rig", file="assets/final/rig/ale_rig.json", layer="角色", engine_layer="actors", z=0.0,
    size_px=rig["master_canvas"], world_size=None,
    anchor={"px": [510, 1631], "meaning": "母版座標：身體中線、腳底（地板）", "world": [pl["ale"]["body_center_x"], 0.0, 0.0]},
    units_per_px=pl["ale"]["master_px_to_units"], height_units=pl["ale"]["standing_height_units"],
    parts={k: {"id": v["image_id"], "file": "assets/final/rig/" + v["file"], "outline_id": v["outline_image_id"]} for k, v in rig["parts"].items()},
    attach="assets/final/rig/ale_attach.json", face="assets/final/face/ale/face.json", readme="assets/final/rig/README.md",
    notes="阿樂叔叔分件紙偶 v04（ale_v03 接縫修正＋乾淨困惑頭）。a2 用困惑頭 head_worried；白色紙芯邊用各部件的 -outline 圖在所有部件後面畫一次（整體外輪廓）。站姿身高 4.6 單位＝中景 640 px，與 G2 v04 合成相同比例。",
    cues=["a2_c001", "a2_c002", "a2_c004"])

manifest = {
    "format": "antidrug-g4-art/1", "version": "v01", "date": "2026-10-21",
    "coords": "世界座標照 app/src/stage/layers.ts：x 向右、y 向上、z 朝觀眾；地面 y=0。world＝錨點的建議世界座標 [x, y, z]；units_per_px＝圖上 1 px 的世界長度。"
              "數值來自 review/G4/art/a2_layout_test.png 的 Python 試排（相機＝CAMERA_PRESETS.medium，1920×1080）。圖片像素座標 y 向下。",
    "pack_ids": "tools/pack.mjs：圖像 id＝相對 assets/final 的路徑去掉副檔名與 _vNN（例 bg-workshop-back、rig/chr-ale_torso、face/ale/chr-ale_mouth_open）；"
                "素材 JSON id 同理（rig/ale_rig、rig/ale_attach、face/xiaoqing/face、face/xiaoyu/face、face/ale/face、g4_manifest）。本檔 assets[].id 就是打包 id。",
    "layers": {"遠": "backdrop z=-5（後牆）＋地板平面", "中": "mid z=-0.9（懸掛燈籠）", "角色": "actors z=0（阿樂 0、小晴 +0.4、小宇 -0.35）",
               "前景": "工作台 z=+0.3（阿樂前面）；側翼 fore z=2.4", "台口": "curtain z=4.0", "介面": "正交疊層"},
    "draw_order_actors": ["chr-xiaoyu（z -0.35）", "rig/ale_rig（outline 全部 → 部件依 layers_back_to_front）", "bg-workshop-table（z 0.3）", "chr-xiaoqing（z 0.4）", "操偶線（strings.order 390；紙環畫在部件上面）"],
    "safe_area": {"subtitle_band": "畫面下 20%（y ≥ 864 @1080）", "safe_frame_90": [96, 54, 1824, 1026],
                  "faces_px_in_test": lay["figure_extent_px"], "note": "試排中三人的臉都在 y 300–620 之間，沒有進入字幕區。"},
    "contrast_proj_v2": {k: {"bg_torso_band_median_lum": v["bg_torso_band_median_lum"], "bg_torso_band_p10_lum": v["bg_torso_band_p10_lum"],
                             "costumes": v["costumes"]} for k, v in lay["contrast"].items()},
    "string_check": {"pixels_of_strings_on_kids": lay["string_pixels_on_kids"], "note": "腕、肘的線近乎垂直往上（偏畫面左）、膝的線往右上斜出，三條都不經過孩子、不經過阿樂的頭頸。"},
    "a2_ale_key_poses": poses,
    "camera_hints": "a2_c001 慢推到手腕近景：看 a2_ale_key_poses.sit.attach_world.wrist_back；a2_c004 沿線移動：hold 姿勢的 wrist_back → elbow_out → knee_front → 再往上（線往上延伸出畫面）。",
    "a2_c002_timing_hint": [
        {"t": "0.0–2.0 s", "pose": "sit", "note": "坐姿（承接 a2_c001），降彩開始"},
        {"t": "2.0–7.0 s", "pose": "sit", "note": "三條線依序落下扣上（腕背 → 肘外 → 膝前），每條間隔約 1.2 s，紙繩輕沙沙聲"},
        {"t": "7.0–9.0 s", "pose": "sit → wave", "note": "想揮手：手先抬起（意圖），阿樂台詞 a2_c002_01 開始"},
        {"t": "9.0–10.5 s", "pose": "wave → pulled", "note": "線先繃緊、手再被拉向畫面左（受力）"},
        {"t": "11.5–13.5 s", "pose": "pulled → halfstand", "note": "想站起來"},
        {"t": "13.5–14.5 s", "pose": "halfstand → kneetug", "note": "膝蓋被線一扯：左腳離地、身體往後晃"},
        {"t": "14.5–16.0 s", "pose": "kneetug → hold", "note": "左手趕快扶住桌面；小晴 a2_c002_02「叔叔，小心！」"},
        {"t": "16.0 s～", "pose": "hold", "note": "停格（呼吸與眨眼照常，線只做很小的擺盪）"},
    ],
    "assets": assets,
}
(FIN / "g4_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
print(len(assets), "assets")
