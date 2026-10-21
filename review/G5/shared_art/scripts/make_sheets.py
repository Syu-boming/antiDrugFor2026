"""G5 共用美術：接觸表、逐檔投影模擬、檢查總表。

輸出（review/G5/shared_art/）：
  contact_characters.png   全部新角色與新姿勢（同角色同一列；依 show_characters.json 的縮放排成舞台比例，紅線＝地面、藍線＝長椅座面 0.92）
  contact_props_sets.png   道具、邀請者、校門口與廣場景片
  contact_faces.jpg        退路臉部（小晴、小宇新姿勢）＋正式換片（四位新角色）放大
  projsim/<檔名>_sheet.jpg 逐檔投影模擬四聯圖（原圖／投影 v2／灰階／綠色弱）——tools/projsim.py
  checks_summary.json      每張圖的自動檢查（霧邊、白邊、裁切、色差、平光、兩眼同閉、投影 v2 主色亮度）
用法：/opt/anaconda3/bin/python3 review/G5/shared_art/scripts/make_sheets.py
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g5lib as L  # noqa: E402

ROOT = L.ROOT
OUT = ROOT / "review/G5/shared_art"
PY = "/opt/anaconda3/bin/python3"


def label(d, xy, text, size=22, fill=(30, 30, 30)):
    d.text(xy, text, fill=fill, font=L.font(size))


def contact_characters():
    show = json.loads((ROOT / "assets/final/rig/show_characters.json").read_text())
    rep = json.loads((OUT / "scale_report.json").read_text())
    PPU = 230
    rows = []
    from stage_preview import char_img
    for cid in ("xiaoqing", "xiaoyu", "pinan", "lin", "chen", "ye"):
        poses = [p for p in show["characters"][cid]["poses"] if p == "stand" or f"{cid}:{p}" in rep]
        tiles = []
        for p in poses:
            im, feet, s = char_img(cid, p)
            sc = s * PPU
            t = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.LANCZOS)
            tiles.append((p, t, feet[1] * sc, feet[0] * sc))
        top = max(f for _, _, f, _ in tiles)
        Hh = int(top + 70)
        Wd = sum(t.width for _, t, _, _ in tiles) + 30 * len(tiles) + 30
        c = Image.new("RGB", (Wd, Hh), (226, 222, 212))
        d = ImageDraw.Draw(c)
        x = 20
        ground = Hh - 40
        for p, t, fy, fx in tiles:
            c.paste(t, (x, int(ground - fy)), t)
            label(d, (x, ground + 6), f"{cid}:{p}", 20)
            x += t.width + 30
        d.line([(0, ground), (Wd, ground)], fill=(220, 40, 40), width=2)
        d.line([(0, ground - int(0.92 * PPU)), (Wd, ground - int(0.92 * PPU))], fill=(40, 90, 220), width=1)
        rows.append(c)
    Wd = max(r.width for r in rows)
    sheet = Image.new("RGB", (Wd, sum(r.height for r in rows) + 60), (226, 222, 212))
    d = ImageDraw.Draw(sheet)
    label(d, (20, 14), "G5 共用美術：角色與姿勢（舞台比例：show_characters.json 的縮放；紅線地面、藍線長椅座面 0.92）", 26)
    y = 60
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height
    sheet.save(OUT / "contact_characters.png")


def contact_props_sets():
    items = [("chr-inviter_hand-box", "assets/final/chr-inviter_hand-box_v01.png"), ("prop-sticker-box", "assets/final/props/prop-sticker-box_v01.png"),
             ("prop-truck", "assets/final/props/prop-truck_v01.png"), ("prop-bench", "assets/final/props/prop-bench_v01.png"),
             ("prop-truck-wheel", "assets/final/props/prop-truck-wheel_v01.png")]
    sets = sorted((ROOT / "assets/final/sets/gate").glob("*.png")) + sorted((ROOT / "assets/final/sets/square").glob("*.png"))
    items += [(p.stem.rsplit("_v", 1)[0], str(p.relative_to(ROOT))) for p in sets]
    th = 260
    tiles = []
    for name, f in items:
        im = Image.open(ROOT / f).convert("RGBA")
        sc = min(th / im.height, 520 / im.width)
        tiles.append((name, im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.LANCZOS)))
    cols, Wd = 4, 4 * 560 + 40
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (Wd, rows * (th + 50) + 70), (150, 150, 160))
    d = ImageDraw.Draw(sheet)
    label(d, (20, 16), "G5 共用美術：邀請者、道具、校門口（程式繪製退路版）與廣場分層景（灰底＝透明處）", 26, (255, 255, 255))
    for i, (name, t) in enumerate(tiles):
        x, y = 20 + (i % cols) * 560, 70 + (i // cols) * (th + 50)
        sheet.paste(t, (x, y), t)
        label(d, (x, y + th + 8), name, 20, (255, 255, 255))
    sheet.save(OUT / "contact_props_sets.png")


def contact_faces():
    fs = sorted((OUT / "faces").glob("xiaoqing_*.png")) + sorted((OUT / "faces").glob("xiaoyu_*.png")) + sorted((OUT / "faces_pieces").glob("*.png"))
    ims = [Image.open(f) for f in fs]
    Wd = 1800
    ims = [i.resize((Wd, int(i.height * Wd / i.width))) for i in ims]
    sheet = Image.new("RGB", (Wd, sum(i.height + 8 for i in ims) + 60), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    label(d, (20, 14), "臉部：小晴、小宇新姿勢＝退路換片模擬（face.ts drawFallback）；品安、林老師、陳伯伯、葉護理師＝正式換片（遮罩不蓋頭髮與臉緣）", 24, (255, 255, 255))
    y = 60
    for i in ims:
        sheet.paste(i, (0, y))
        y += i.height + 8
    sheet.save(OUT / "contact_faces.jpg", optimize=True)


def projsim_all(files):
    dst = OUT / "projsim"
    dst.mkdir(exist_ok=True)
    tmp = OUT / "_tmp/projsim"
    tmp.mkdir(parents=True, exist_ok=True)
    for f in files:
        subprocess.run([PY, str(ROOT / "tools/projsim.py"), str(ROOT / f), str(tmp)], check=True, capture_output=True)
        stem = Path(f).stem
        sh = tmp / f"{stem}_sheet.png"
        if sh.exists():
            im = Image.open(sh)
            im = im.convert("RGB")
            if im.width > 1400:
                im = im.resize((1400, int(im.height * 1400 / im.width)))
            im.save(dst / f"{stem}_sheet.jpg", quality=88)
    shutil.rmtree(tmp, ignore_errors=True)


def summary(files):
    imp = json.loads((OUT / "import.json").read_text())
    props = json.loads((OUT / "import_props.json").read_text())
    blink = json.loads((OUT / "blink_check.json").read_text())
    pieces = json.loads((OUT / "blink_check_pieces.json").read_text())
    from measure_faces import POSE_NAME
    sys.path.insert(0, str(ROOT / "tools"))
    from projsim import projector
    out = {}
    for rid, rec in imp.items():
        if rid.startswith("_") or "final" not in rec:
            continue
        key = f"{rec['character']}:{POSE_NAME[rec['part']]}"
        c = rec["checks"]
        a = np.array(Image.open(ROOT / rec["final"]).convert("RGBA"))
        pj = projector(a[..., :3].astype(np.float32))
        m = a[..., 3] >= 128
        new = rec["character"] in ("pinan", "lin", "chen", "ye")
        bc = pieces.get(key) if new else blink.get(key)
        out[rec["final"]] = {
            "key": key, "raw": rec["raw"], "generated": rec["generated"], "draws": 1,
            "fog_px": c["fog_px"], "white_border_px": c["white_border_px"], "white_border_ok": c["white_border_ok"],
            "outer_dark_line": c.get("outer_dark_line"), "dark_line_inside_border": c["dark_line_inside_border"],
            "raw_margins": c["raw_margins"], "crop_ok_feet_not_cut": c["crop_ok"], "lr_L_median_diff_flat_light": c.get("lr_L_median_diff"),
            "garments": rec["garments"], "recolor": rec.get("recolor"),
            "blink_both_closed_ok": bool(bc and bc["both_closed_ok"]), "blink_half_ok": bool(bc and bc["half"]["ok"]),
            "blink_method": "正式換片（face/<角色>/face_v01.json）" if new else "退路換片模擬（fallbackFaces）",
            "proj_v2_figure_median_lum": round(float(np.median(L.lab_of(np.clip(pj, 0, 255).astype(np.uint8))[..., 0][m])) / 100, 3),
        }
    for k, v in props.items():
        if k == "prop_inviter_v01":
            for part in ("hand", "box"):
                r = v[part]
                out[r["final"]] = {"raw": v["raw"], "generated": v["generated"], "draws": 1, "fog_px": r["checks"]["fog_px"],
                                   "white_border_px": r["checks"]["white_border_px"], "white_border_ok": r["checks"]["white_border_ok"],
                                   "raw_margins": r["checks"]["raw_margins"], "crop_ok": r["checks"]["crop_ok"],
                                   "note": r.get("note", "")}
    g = json.loads((OUT / "sets/gate_import.json").read_text())
    for k, v in g.items():
        a = np.array(Image.open(ROOT / v["file"]).convert("RGBA"))
        out[v["file"]] = {"draws": 0, "method": "程式繪製（paperdraw.py；image_gen 額度用完的退路）", **{kk: vv for kk, vv in L.checks(a).items() if kk in ("fog_px", "white_border_px", "lr_L_median_diff")}}
    s = json.loads((OUT / "sets/square_import.json").read_text())
    for k, v in s.items():
        out[v["file"]] = {"draws": 0, "method": "由 G2 拼版切件（不重抽）", "source": v["source"], **v.get("checks", {})}
    (OUT / "checks_summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    bad = [k for k, v in out.items() if v.get("blink_both_closed_ok") is False or v.get("fog_px", 0) > 50 or v.get("crop_ok_feet_not_cut") is False]
    print("檢查不通過：", bad)


def main():
    contact_characters()
    contact_props_sets()
    contact_faces()
    imp = json.loads((OUT / "import.json").read_text())
    files = [v["final"] for k, v in imp.items() if not k.startswith("_") and "final" in v]
    files += ["assets/final/chr-inviter_hand-box_v01.png", "assets/final/props/prop-sticker-box_v01.png", "assets/final/props/prop-truck_v01.png",
              "assets/final/props/prop-bench_v01.png"]
    files += [str(p.relative_to(ROOT)) for p in sorted((ROOT / "assets/final/sets").glob("*/*.png"))]
    files += ["review/G5/shared_art/contact_characters.png"]
    projsim_all(files)
    summary(files)


if __name__ == "__main__":
    main()
