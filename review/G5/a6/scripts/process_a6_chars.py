"""第六幕代理：Codex 原檔 → 角色立牌（照 review/G5/shared_art/scripts/process_chars.py 的流程）＋鏡像姿勢。

用法：/opt/anaconda3/bin/python3 review/G5/a6/scripts/process_a6_chars.py
- 原檔 review/G5/a6/raw/*.png（不改）
- 謝幕鞠躬兩張拼版（孩子、大人各三人）：依透明連通區切開 → assets/generated/chr-<角色>_pose-bow_v01.png（原像素、只裁切）
  → assets/final/chr-<角色>_pose-bow_v01.png（alpha<24→0、≥250→255、去雜點、裁透明邊＋16 px、顏色外擴）
- 阿琴阿姨站姿 → assets/generated/chr-aqin_master_v01.png → assets/final/chr-aqin_master_v01.png
- 鏡像姿勢（程式，PIL 左右翻轉）：品安 stand／walk_straps、小宇 standwatch → assets/final/chr-*_pose-*-m_v01.png
- 鞠躬的虛擬頭頂（headTop）：讓鞠躬圖的頭寬和站姿母版在舞台上同大小（引擎把腳底到 headTop 拉成角色身高）
- 輸出紀錄 review/G5/a6/chars_import.json（裁切、腳底、主色 ΔE、自動檢查、headTop）
"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "review/G5/shared_art/scripts"))
import g5lib as L  # noqa: E402

RAW = ROOT / "review/G5/a6/raw"
GEN = ROOT / "assets/generated"
FIN = ROOT / "assets/final"
OUT = ROOT / "review/G5/a6"
CFG = json.loads((FIN / "rig/show_characters.json").read_text())

SHEETS = {
    "bow_kids_v01": ["xiaoqing", "xiaoyu", "pinan"],
    "bow_adults_v01": ["chen", "lin", "ye"],
}
RECOLOR = {
    "xiaoqing": [("湖水綠吊帶褲", (160, 205), 0.25, 0.10, (0.0, 1.0), 37.0)],
    "xiaoyu": [("橘紅外套", (345, 22), 0.55, 0.25, (0.15, 0.78), 39.0)],
}
MASTER = {
    "xiaoqing": "chr-xiaoqing_master_v04.png", "xiaoyu": "chr-xiaoyu_master_v04.png", "pinan": "chr-pinan_master_v01.png",
    "chen": "chr-chen_master_v01.png", "lin": "chr-lin_master_v01.png", "ye": "chr-ye_master_v01.png",
}
GARMENTS = {
    "xiaoqing": [("湖水綠吊帶褲", (160, 205), 0.25, 0.10, 1.0, (0.3, 1.0)), ("芥末黃上衣", (35, 55), 0.5, 0.5, 1.0, (0.1, 0.5))],
    "xiaoyu": [("橘紅外套", (345, 22), 0.55, 0.25, 0.95, (0.15, 0.7)), ("卡其短褲", (25, 45), 0.2, 0.4, 0.85, (0.45, 0.8))],
    "pinan": [("茄紫上衣", (280, 345), 0.15, 0.12, 0.7, (0.15, 0.7)), ("橄欖綠書包", (55, 95), 0.2, 0.15, 0.7, (0.1, 0.7))],
    "lin": [("酒紅毛衣", (330, 15), 0.3, 0.15, 0.8, (0.12, 0.7))],
    "chen": [("黃綠背心", (55, 95), 0.4, 0.4, 1.0, (0.15, 0.7)), ("淺灰制服", (0, 360), 0.0, 0.55, 0.9, (0.12, 0.45))],
    "ye": [("鼠尾草綠護理服", (70, 160), 0.08, 0.35, 0.85, (0.15, 0.6))],
}


def finish(a):
    a, removed = L.clean_alpha(a)
    crop, off = L.crop_pad(a, 16)
    return crop, off, removed


def feet_and_top(a):
    al = a[..., 3] >= 128
    rows = np.nonzero(al.any(1))[0]
    bottom = int(rows.max())
    low = al[bottom - 40:bottom + 1].any(0)
    lx = np.nonzero(low)[0]
    return [round(float((lx.min() + lx.max()) / 2), 1), bottom - 4], int(rows.min())


def head_width(a, frac=(0.0, 0.2), pos="top"):
    """頭（含頭髮）寬：不透明範圍最上面 frac 高度內，每列寬度的第 90 百分位。"""
    al = a[..., 3] >= 128
    rows = np.nonzero(al.any(1))[0]
    top, bot = rows.min(), rows.max()
    H = bot - top
    ws = []
    for y in range(int(top + frac[0] * H), int(top + frac[1] * H)):
        xs = np.nonzero(al[y])[0]
        if len(xs):
            ws.append(xs.max() - xs.min())
    return float(np.percentile(ws, 90))


def auto_top(a):
    """引擎 standee.ts 的頭頂偵測（高度 12–22% 欄位加權中心 ±6% 寬的最高點）。"""
    al = a[..., 3] >= 128
    ys, xs = np.nonzero(al)
    y0, y1 = ys.min(), ys.max()
    H = y1 - y0
    band = al[int(y0 + 0.12 * H):int(y0 + 0.22 * H)]
    by, bx = np.nonzero(band)
    hx = bx.mean() if len(bx) else al.shape[1] / 2
    half = round(al.shape[1] * 0.06)
    best = 1e9
    for x in range(max(0, int(hx - half)), min(al.shape[1], int(hx + half))):
        col = np.nonzero(al[:, x])[0]
        if len(col):
            best = min(best, col.min())
    return int(best)


def main():
    rec = {}
    # ---------------- 鞠躬拼版
    for sheet, cids in SHEETS.items():
        raw = np.array(Image.open(RAW / f"{sheet}.png").convert("RGBA"))
        a, _ = L.clean_alpha(raw)
        lab, n = ndimage.label(a[..., 3] > 0)
        sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
        big = 1 + np.argsort(sizes)[::-1][:len(cids)]
        comps = sorted(big, key=lambda k: np.nonzero(lab == k)[1].mean())
        for cid, k in zip(cids, comps):
            ys, xs = np.nonzero(lab == k)
            x0, x1 = max(0, xs.min() - 24), min(raw.shape[1], xs.max() + 25)
            y0, y1 = max(0, ys.min() - 24), min(raw.shape[0], ys.max() + 25)
            # 原像素裁切（其他人物的像素清掉）→ generated
            sub = raw[y0:y1, x0:x1].copy()
            others = (lab[y0:y1, x0:x1] > 0) & (lab[y0:y1, x0:x1] != k)
            grow = ndimage.binary_dilation(others, iterations=6)
            sub[grow & ~(lab[y0:y1, x0:x1] == k), 3] = 0
            gen = GEN / f"chr-{cid}_pose-bow_v01.png"
            recol = None
            if cid in RECOLOR:   # 兒童主色調回 v04 色票（同 process_chars.py：L* 差 > 1 時 tools/recolor_garment.recolor）
                sys.path.insert(0, str(ROOT / "tools"))
                import recolor_garment as RG
                tmp = GEN / f"_tmp_bow_{cid}.png"
                Image.fromarray(sub, "RGBA").save(tmp)
                recol = [list(r) for r in RG.recolor(tmp.name, gen.name, RECOLOR[cid])]
                tmp.unlink()
                sub = np.array(Image.open(gen).convert("RGBA"))
            else:
                Image.fromarray(sub, "RGBA").save(gen, optimize=True)
            crop, off, removed = finish(sub)
            fin = FIN / f"chr-{cid}_pose-bow_v01.png"
            Image.fromarray(crop, "RGBA").save(fin, optimize=True)
            m = np.array(Image.open(FIN / MASTER[cid]).convert("RGBA"))
            feet_m, _ = feet_and_top(m)
            top_m = auto_top(m)
            h_cfg = CFG["characters"][cid]["height"]
            s_m = h_cfg / (feet_m[1] - top_m)        # 母版：世界單位／像素
            hw_m, hw_b = head_width(m, (0.0, 0.17)), head_width(crop, (0.0, 0.2))
            s_b = s_m * hw_m / hw_b
            feet_b, top_b = feet_and_top(crop)
            head_top = round(feet_b[1] - (feet_b[1] - top_b) / 0.86, 1)   # 鞠躬可見高度＝站姿身高 × 0.86（頭寬對齊會讓身體太小，見 bow_scale_check_*.png）
            r = {"raw": str((RAW / f"{sheet}.png").relative_to(ROOT)), "generated": str(gen.relative_to(ROOT)), "final": str(fin.relative_to(ROOT)),
                 "sheet_box": [int(x0), int(y0), int(x1), int(y1)], "size": [int(crop.shape[1]), int(crop.shape[0])], "stray_px_removed": removed,
                 "feet": feet_b, "bbox_top": top_b, "headTop_virtual": head_top, "head_width_px": {"master": round(hw_m, 1), "bow": round(hw_b, 1)},
                 "recolor": recol, "bow_visible_height_ratio": round((feet_b[1] - top_b) / (feet_b[1] - head_top), 3), "checks": L.checks(crop)}
            gs = {}
            for g in GARMENTS.get(cid, []):
                st = L.garment_stats(crop, g[1], g[2], g[3], g[4], g[5])
                sm = L.garment_stats(m, g[1], g[2], g[3], g[4], g[5])
                if st and sm:
                    st["dE_vs_master"] = L.delta_e(st["lab"], sm["lab"])
                gs[g[0]] = st
            r["garments"] = gs
            rec[f"{cid}:bow"] = r
            print(cid, "bow", r["size"], "headTop", head_top, "可見高比", r["bow_visible_height_ratio"], "白邊", r["checks"]["white_border_px"], "霧", r["checks"]["fog_px"],
                  {kk: (vv and vv.get("dE_vs_master")) for kk, vv in gs.items()})
    # ---------------- 阿琴阿姨
    raw = np.array(Image.open(RAW / "chr_aqin_stand_v01.png").convert("RGBA"))
    gen = GEN / "chr-aqin_master_v01.png"
    shutil.copyfile(RAW / "chr_aqin_stand_v01.png", gen)
    crop, off, removed = finish(raw)
    fin = FIN / "chr-aqin_master_v01.png"
    Image.fromarray(crop, "RGBA").save(fin, optimize=True)
    feet, top = feet_and_top(crop)
    rec["aqin:stand"] = {"raw": "review/G5/a6/raw/chr_aqin_stand_v01.png", "generated": str(gen.relative_to(ROOT)), "final": str(fin.relative_to(ROOT)),
                         "offset_from_source": list(off), "size": [int(crop.shape[1]), int(crop.shape[0])], "stray_px_removed": removed,
                         "feet": feet, "alpha_ref": L.alpha_ref(crop), "checks": L.checks(crop, raw)}
    print("aqin", rec["aqin:stand"]["size"], "白邊", rec["aqin:stand"]["checks"]["white_border_px"], "霧", rec["aqin:stand"]["checks"]["fog_px"], "裁切", rec["aqin:stand"]["checks"].get("raw_touches_edge"))
    # ---------------- 鏡像姿勢（程式）
    for src, dst in [("chr-pinan_master_v01.png", "chr-pinan_pose-stand-m_v01.png"),
                     ("chr-pinan_pose-walk-straps_v01.png", "chr-pinan_pose-walk-straps-m_v01.png"),
                     ("chr-xiaoyu_pose-standwatch_v01.png", "chr-xiaoyu_pose-standwatch-m_v01.png")]:
        im = Image.open(FIN / src).convert("RGBA")
        ImageOps.mirror(im).save(FIN / dst, optimize=True)
        rec[dst] = {"from": f"assets/final/{src}", "op": "PIL ImageOps.mirror", "size": list(im.size)}
    (OUT / "chars_import.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
