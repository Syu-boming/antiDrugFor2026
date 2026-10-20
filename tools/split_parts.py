"""分件紙偶套件拆件（v1.2 第 22.1 節第 4 步）：SciPy 連通區標記 → 獨立部件 PNG ＋接觸表。

用法：
  /opt/anaconda3/bin/python3 tools/split_parts.py [套件圖] [--out assets/parts/ale] [--sheet review/G2/kit_ale_parts_sheet.png]
  [--override 對照.json]  # 若自動命名錯誤，可給 {"元件編號": "部件名"} 人工覆寫
  --layout master_v03：G2 第 3 輪起不再拆生成的套件圖，改以正式母版 chr-ale_master_v02.png 直接切件
    （tools/master_cut.py；輸出 assets/parts/ale_v03/、review/G2/kit_ale_v03_parts_sheet.png、kit_ale_v03_cutmap.png）

命名規則（依位置與形狀）：
  - 先以 alpha 做連通區標記（8 連通），去掉小於畫面 0.05% 的碎屑。
  - 依「列」分組（質心 y 做一維分群成 3 列，對應生成提示的三列排法），列內依 x 由左到右排序，
    對照提示的排法：第 1 列 頭、軀幹、右上臂、左上臂；第 2 列 右前臂、左前臂、右手、左手；
    第 3 列 右大腿、左大腿、右小腿含鞋、左小腿含鞋。
  - 再用形狀檢查交叉驗證：軀幹面積最大；手面積最小且最接近方形；小腿含鞋的底部最寬（鞋）；
    位置與形狀不一致時以形狀為準並在接觸表標示「形狀校正」。
  - 左／右＝角色自身的左右（正面看時，角色的右側在畫面左側）。
輸出：<out>/<部件>.png（裁切留 8 px 透明邊、只保留該元件的像素）、<out>/parts.json（元件框、面積、質心、
      端點圓弧檢查），以及接觸表（上：原圖＋編號框；下：各部件與名稱）。
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
FONT = ("/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc", 10)
FONT_FALLBACK = ("/System/Library/Fonts/STHeiti Medium.ttc", 0)

LAYOUTS = {
    "v01": [  # 12 件、三列（review/G2/raw/kit_ale.png）
        ["head", "torso", "upper_arm_r", "upper_arm_l"],
        ["forearm_r", "forearm_l", "hand_r", "hand_l"],
        ["thigh_r", "thigh_l", "shin_r", "shin_l"],
    ],
    "v02": [  # 13 件、兩列：圍裙下襬獨立成件（review/G2/raw/kit_ale_v02.png）
        ["head", "torso", "apron_skirt", "upper_arm_r", "upper_arm_l"],
        ["forearm_r", "forearm_l", "hand_r", "hand_l", "thigh_r", "thigh_l", "shin_r", "shin_l"],
    ],
}
LAYOUT = LAYOUTS["v01"]
ZH = {"head": "頭（含頸部舌片）", "torso": "軀幹", "apron_skirt": "圍裙下襬", "upper_arm_r": "右上臂", "upper_arm_l": "左上臂",
      "forearm_r": "右前臂", "forearm_l": "左前臂", "hand_r": "右手", "hand_l": "左手",
      "thigh_r": "右大腿", "thigh_l": "左大腿", "shin_r": "右小腿含鞋", "shin_l": "左小腿含鞋"}
PAIRS = [("upper_arm_r", "upper_arm_l"), ("forearm_r", "forearm_l"), ("hand_r", "hand_l"),
         ("thigh_r", "thigh_l"), ("shin_r", "shin_l")]


def font(px):
    for p, i in (FONT, FONT_FALLBACK):
        try:
            return ImageFont.truetype(p, px, index=i)
        except OSError:
            pass
    return ImageFont.load_default()


def end_roundness(mask):
    """沿主軸量兩端：端點 3% 處寬度 ÷ 15% 處寬度。圓弧舌片約 0.3–0.75；平切端接近 1。"""
    ys, xs = np.nonzero(mask)
    pts = np.stack([xs, ys], 1).astype(np.float64)
    c = pts.mean(0)
    u, s, vt = np.linalg.svd(pts - c, full_matrices=False)
    axis = vt[0]
    if axis[1] < 0:
        axis = -axis  # 讓主軸朝下（第一端＝上端）
    perp = np.array([-axis[1], axis[0]])
    t = (pts - c) @ axis
    w = (pts - c) @ perp
    L = t.max() - t.min()
    res = []
    for sign, name in ((1, "top"), (-1, "bottom")):
        tt = (t - t.min()) / L if sign == 1 else (t.max() - t) / L

        def width(at, band=0.015):
            sel = np.abs(tt - at) < band
            return float(w[sel].max() - w[sel].min()) if sel.sum() > 3 else 0.0

        w3, w15 = width(0.03), width(0.15)
        r = w3 / w15 if w15 > 0 else None
        res.append(dict(end=name, w3=round(w3, 1), w15=round(w15, 1),
                        ratio=round(r, 2) if r else None, rounded=bool(r is not None and r < 0.8)))
    return dict(length_px=round(float(L), 1), ends=res)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kit", nargs="?", default=str(ROOT / "review/G2/raw/kit_ale.png"))
    ap.add_argument("--out", default=str(ROOT / "assets/parts/ale"))
    ap.add_argument("--sheet", default=str(ROOT / "review/G2/kit_ale_parts_sheet.png"))
    ap.add_argument("--override", default=None)
    ap.add_argument("--alpha-thr", type=int, default=40)
    ap.add_argument("--layout", default="v01", choices=sorted(LAYOUTS) + ["master_v03"])
    ap.add_argument("--alpha-floor", type=int, default=0, help="部件 PNG 中 alpha 低於此值的淡霧清成全透明")
    args = ap.parse_args()
    if args.layout == "master_v03":
        import master_cut
        m = master_cut.cut()
        print(json.dumps({k: dict(source_px=v["source_px"], synth_px=v["synth_px"]) for k, v in m["parts"].items()},
                         ensure_ascii=False))
        print("未分配像素：", m["unassigned_body_px"])
        return
    global LAYOUT
    LAYOUT = LAYOUTS[args.layout]
    n_expect = sum(len(r) for r in LAYOUT)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    im = Image.open(args.kit).convert("RGBA")
    arr = np.array(im)
    alpha = arr[..., 3]
    mask = ndimage.binary_fill_holes(alpha > args.alpha_thr)
    lab, n = ndimage.label(mask, structure=np.ones((3, 3)))
    areas = ndimage.sum(mask, lab, range(1, n + 1))
    min_area = mask.size * 0.0005
    keep = [i + 1 for i, a in enumerate(areas) if a >= min_area]
    dropped = [dict(label=i + 1, area=int(a)) for i, a in enumerate(areas) if a < min_area]
    comps = []
    for k in keep:
        m = lab == k
        ys, xs = np.nonzero(m)
        comps.append(dict(label=int(k), area=int(m.sum()), cx=float(xs.mean()), cy=float(ys.mean()),
                          box=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]))
    print(f"連通區 {n} 個，保留 {len(comps)} 個（碎屑 {len(dropped)} 個）")
    if len(comps) != n_expect:
        print(f"警告：部件數不是 {n_expect}，請檢查（可能有部件相連或斷開）")

    # ---- 依位置命名：以「上緣 y」分列（以最大間隙切分；兩列時大件與小件的質心差太多，改用上緣）----
    nrows = len(LAYOUT)
    cys = np.array([c["box"][1] if nrows == 2 else c["cy"] for c in comps], dtype=float)
    order = np.argsort(cys)
    gaps = np.diff(cys[order])
    cuts = sorted(np.argsort(-gaps)[:nrows - 1]) if len(comps) >= nrows else []
    rows, start = [], 0
    for ccut in cuts:
        rows.append(order[start:ccut + 1].tolist())
        start = ccut + 1
    rows.append(order[start:].tolist())
    names = {}
    for r, idxs in enumerate(rows):
        idxs = sorted(idxs, key=lambda i: comps[i]["cx"])
        for j, i in enumerate(idxs):
            if r < len(LAYOUT) and j < len(LAYOUT[r]):
                names[i] = LAYOUT[r][j]
            else:
                names[i] = f"extra_{r}_{j}"

    # ---- 形狀交叉驗證 ----
    notes = []
    for c in comps:
        x0, y0, x1, y1 = c["box"]
        c["w"], c["h"] = x1 - x0, y1 - y0
        c["fill"] = c["area"] / (c["w"] * c["h"])
        m = (lab[y0:y1, x0:x1] == c["label"])
        rw = m.sum(1)
        c["bottom_width_ratio"] = float(rw[int(len(rw) * 0.8):].max() / (rw[int(len(rw) * 0.3):int(len(rw) * 0.6)].mean() + 1e-6))
    by_area = sorted(range(len(comps)), key=lambda i: -comps[i]["area"])
    if comps and names.get(by_area[0]) != "torso":
        notes.append(f"形狀校正：面積最大的元件 #{comps[by_area[0]]['label']} 原判為 {names.get(by_area[0])}，改為 torso")
        old = names[by_area[0]]
        for i, nm in list(names.items()):
            if nm == "torso":
                names[i] = old
        names[by_area[0]] = "torso"
    smallest = sorted(range(len(comps)), key=lambda i: comps[i]["area"])[:2]
    for i in smallest:
        if not names[i].startswith("hand"):
            notes.append(f"提醒：最小的元件 #{comps[i]['label']} 判為 {names[i]}（預期為手），請目視確認")
    for i, c in enumerate(comps):
        if names[i].startswith("shin") and c["bottom_width_ratio"] < 1.15:
            notes.append(f"提醒：{names[i]} 底部沒有明顯變寬（鞋），請目視確認")

    if args.override:
        ov = json.loads(Path(args.override).read_text())
        for i, c in enumerate(comps):
            if str(c["label"]) in ov:
                notes.append(f"人工覆寫：#{c['label']} {names[i]} → {ov[str(c['label'])]}")
                names[i] = ov[str(c["label"])]

    # 成對部件：畫面左邊的是角色的右側
    for r_name, l_name in PAIRS:
        ir = [i for i, nm in names.items() if nm == r_name]
        il = [i for i, nm in names.items() if nm == l_name]
        if ir and il and comps[ir[0]]["cx"] > comps[il[0]]["cx"]:
            names[ir[0]], names[il[0]] = l_name, r_name

    # ---- 輸出部件 ----
    manifest = dict(source=str(Path(args.kit).relative_to(ROOT)) if str(args.kit).startswith(str(ROOT)) else str(args.kit),
                    size=list(im.size), alpha_threshold=args.alpha_thr, convention="左／右＝角色自身的左右",
                    dropped_specks=dropped, notes=notes, parts={})
    pad = 8
    crops = {}
    for i, c in enumerate(comps):
        nm = names[i]
        x0, y0, x1, y1 = c["box"]
        X0, Y0 = max(x0 - pad, 0), max(y0 - pad, 0)
        X1, Y1 = min(x1 + pad, im.width), min(y1 + pad, im.height)
        own = ndimage.binary_dilation(lab == c["label"], iterations=3)[Y0:Y1, X0:X1]
        piece = arr[Y0:Y1, X0:X1].copy()
        piece[..., 3] = np.where(own, piece[..., 3], 0)
        if args.alpha_floor:
            piece[..., 3] = np.where(piece[..., 3] < args.alpha_floor, 0, piece[..., 3])
        pim = Image.fromarray(piece, "RGBA")
        pim.save(out / f"{nm}.png")
        crops[nm] = pim
        manifest["parts"][nm] = dict(label=c["label"], zh=ZH.get(nm, nm), file=f"{nm}.png", box_in_kit=c["box"],
                                     size=[X1 - X0, Y1 - Y0], area_px=c["area"],
                                     centroid=[round(c["cx"], 1), round(c["cy"], 1)],
                                     joint_ends=end_roundness(lab[y0:y1, x0:x1] == c["label"]))
    (out / "parts.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))

    # ---- 接觸表 ----
    f_t, f_s = font(30), font(22)
    kit_w = 1500
    ks = kit_w / im.width
    kit_bg = Image.new("RGBA", im.size, (150, 150, 146, 255))
    kit_v = Image.alpha_composite(kit_bg, im).convert("RGB")
    dk = ImageDraw.Draw(kit_v)
    for i, c in enumerate(comps):
        dk.rectangle(c["box"], outline=(255, 40, 40), width=3)
        dk.text((c["box"][0] + 4, c["box"][1] + 2), f"#{c['label']} {names[i]}", font=font(26), fill=(255, 255, 0),
                stroke_width=2, stroke_fill=(0, 0, 0))
    kit_v = kit_v.resize((kit_w, round(im.height * ks)), Image.LANCZOS)
    cell_w, cell_h, cols = 370, 430, 4 if n_expect <= 12 else 5
    order_names = [nm for row in LAYOUT for nm in row] + [nm for nm in crops if nm not in sum(LAYOUT, [])]
    nrows = int(np.ceil(len(order_names) / cols))
    sheet = Image.new("RGB", (max(kit_w, cell_w * cols) + 40, 70 + kit_v.height + 30 + nrows * cell_h + 20), (46, 46, 48))
    d = ImageDraw.Draw(sheet)
    d.text((20, 18), f"阿樂叔叔分件接觸表：連通區 {len(comps)} 件（預期 {n_expect}）— 來源 {Path(args.kit).name}", font=f_t, fill=(240, 240, 240))
    sheet.paste(kit_v, (20, 70))
    y_base = 70 + kit_v.height + 30
    for k, nm in enumerate(order_names):
        if nm not in crops:
            continue
        pim = crops[nm]
        cx, cy = 20 + (k % cols) * cell_w, y_base + (k // cols) * cell_h
        d.rectangle([cx + 6, cy + 6, cx + cell_w - 6, cy + cell_h - 60], fill=(150, 150, 146))
        s = min((cell_w - 30) / pim.width, (cell_h - 90) / pim.height, 1.0)
        t = pim.resize((max(1, round(pim.width * s)), max(1, round(pim.height * s))), Image.LANCZOS)
        sheet.paste(t, (cx + (cell_w - t.width) // 2, cy + 12 + (cell_h - 78 - t.height) // 2), t)
        je = manifest["parts"][nm]["joint_ends"]["ends"]
        rr = "／".join("圓" if e["rounded"] else "平" for e in je) if nm not in ("head", "torso") else "—（多舌片，目視）"
        d.text((cx + 10, cy + cell_h - 52), f"{ZH.get(nm, nm)}  {nm}", font=f_s, fill=(240, 240, 240))
        d.text((cx + 10, cy + cell_h - 26), f"{pim.width}×{pim.height}px  兩端:{rr}", font=font(18), fill=(190, 190, 190))
    sheet.save(args.sheet)
    print(json.dumps({nm: dict(label=v["label"], size=v["size"], ends=[e["rounded"] for e in v["joint_ends"]["ends"]])
                      for nm, v in manifest["parts"].items()}, ensure_ascii=False))
    for nline in notes:
        print(nline)


if __name__ == "__main__":
    main()
