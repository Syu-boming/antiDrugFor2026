"""G5 共用美術：小鎮廣場分層景（G2 第 3 輪的 bg-square-*_v03 拼版 → 一件一檔）＋ layout.draft.json。

來源（assets/generated，Codex image_gen，G2 已登記）：sky、mountains、backrow、arcade、trees、planters（_v03）。
做法：每張拼版依連通區切成單件（去 alpha 雜點、裁透明邊＋8 px、顏色外擴）；天空整張（不透明）。
輸出：assets/final/sets/square/set-square_<件名>_v01.png、layout.draft.json；檢查 review/G5/shared_art/sets/square_*.png
用法：/opt/anaconda3/bin/python3 review/G5/shared_art/scripts/build_square.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g5lib as L  # noqa: E402

ROOT = L.ROOT
GEN = ROOT / "assets/generated"
DST = ROOT / "assets/final/sets/square"
OUT = ROOT / "review/G5/shared_art"

# 拼版 → 件名（依連通區由左到右、由上到下）
KITS = {
    "mountains": ["mountains"],
    "backrow": ["backrow"],
    "arcade": ["arcade"],
    "trees": ["tree-a", "tree-b"],
    "planters": ["planter-tall", "planter-mid", "planter-long"],
}


def cut(kit, names):
    a = np.array(Image.open(GEN / f"bg-square-{kit}_v03.png").convert("RGBA"))
    a, removed = L.clean_alpha(a, min_comp=1500)
    lab, n = ndimage.label(a[..., 3] > 0)
    objs = ndimage.find_objects(lab)
    sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
    idx = [i for i in range(n) if sizes[i] >= 1500]
    # 花台上的小花叢可能和花台分開：併到下方最近的大件
    big = sorted(idx, key=lambda i: -sizes[i])[:len(names)]
    small = [i for i in idx if i not in big]
    groups = {i: [i] for i in big}
    for s in small:
        sy, sx = objs[s]
        cx = (sx.start + sx.stop) / 2
        best = min(big, key=lambda b: abs((objs[b][1].start + objs[b][1].stop) / 2 - cx) + abs(objs[b][0].start - sy.stop) * 0.5)
        groups[best].append(s)
    order = sorted(big, key=lambda i: (objs[i][1].start, objs[i][0].start))
    recs = {}
    for name, b in zip(names, order):
        piece = a.copy()
        piece[~np.isin(lab, [g + 1 for g in groups[b]]), 3] = 0
        crop, off = L.crop_pad(piece, 8)
        f = DST / f"set-square_{name}_v01.png"
        Image.fromarray(crop, "RGBA").save(f, optimize=True)
        recs[name] = {"file": str(f.relative_to(ROOT)), "source": f"assets/generated/bg-square-{kit}_v03.png", "offset_in_source": list(off),
                      "size": [int(crop.shape[1]), int(crop.shape[0])], "parts_merged": len(groups[b]),
                      "checks": {k: v for k, v in L.checks(crop).items() if k in ("fog_px", "semi_alpha_px", "lr_L_median_diff")}}
    return recs


def main():
    DST.mkdir(parents=True, exist_ok=True)
    recs = {}
    sky = Image.open(GEN / "bg-square-sky_v03.png").convert("RGB")
    sky.save(DST / "set-square_sky_v01.png", optimize=True)
    recs["sky"] = {"file": "assets/final/sets/square/set-square_sky_v01.png", "source": "assets/generated/bg-square-sky_v03.png", "size": list(sky.size), "opaque": True}
    for kit, names in KITS.items():
        recs.update(cut(kit, names))

    def piece(name, layer, x, y, w, z, note=""):
        W, H = recs[name]["size"]
        return {"id": f"sets/square/set-square_{name}", "file": recs[name]["file"], "layer": layer, "x": x, "y": y, "z": z,
                "width": w, "height": round(w * H / W, 3), "anchor": "bottom-center", "note": note}

    layout = {
        "format": "antidrug-g5-set-layout-draft/1",
        "status": "草稿：引擎代理定 layout.json 正式格式後改寫（app/SHOW_INTERFACE.md）。",
        "set": "square",
        "coords": "世界座標同 app/src/stage/layers.ts：x 向右、y 向上（地面 0）、z 朝觀眾；x,y＝圖片底邊中點；width／height 世界單位（height 依圖片比例算好）。layer 只是建議的層名（backdrop z=-5、far -3.2、mid -0.9、actors 0、fore 2.4）。",
        "scale_ref": "阿樂叔叔站姿 3.55、小晴 2.5；舞台開口 15.6×8.8；g4_mid 鏡位在 z=0 看到約 10.3×5.8。",
        "lighting": "兒童站位身後是騎樓下層的淺米色門面；平光預覽投影 v2 中位亮度約 0.47–0.48（review/G5/shared_art/sets/preview_report.json），差一點到 D-G2-06 的 0.50：引擎請比照 G4 bg-workshop-back 給騎樓景片自發光（約 0.3）或柔光區。",
        "floor": {"color": "#d9c3a0", "note": "廣場地面：暖黃米色紙（G2 合成用的地面色），引擎用平塗紙紋或沿用 bg-workshop-floor 的做法另做；本關沒有新地面圖。"},
        "pieces": [
            piece("sky", "backdrop", 0, -0.5, 26, -5.0, "整張不透明背板"),
            piece("mountains", "far", 0, -1.6, 24, -4.2, "遠山：底邊在地面下，只在建築上緣後露出山脊"),
            piece("backrow", "far", 3.2, 0, 15.5, -3.2, "後排騎樓（五個拱門）"),
            piece("arcade", "mid", -1.0, 0, 12.5, -1.6, "前排紅磚騎樓：下層淺米色門面在角色身後"),
            piece("tree-a", "mid", -6.6, 0, 4.2, -0.8, "左側行道樹（危險方位那側，邀請者從柱子後伸手時也可遮擋）"),
            piece("tree-b", "mid", 6.4, 0, 4.2, -0.8, "右側行道樹"),
            piece("planter-long", "mid", 4.6, 0, 3.6, -0.5, "長花台（求助站／長椅旁）"),
            piece("planter-tall", "fore", -7.4, 0, 1.7, 2.4, "左前景花台（畫面邊緣框景，不擋表演區）"),
            piece("planter-mid", "fore", 7.5, 0, 1.6, 2.4, "右前景花台"),
        ],
        "props_suggested": {"bench": "props/prop-bench（座面世界高 0.92；a1_c001 品安 P-PA1 坐在上面綁燈籠）"},
        "made_by": "review/G5/shared_art/scripts/build_square.py",
    }
    (OUT / "sets/square_layout_source.json").write_text(json.dumps(layout, ensure_ascii=False, indent=1))
    (OUT / "sets").mkdir(exist_ok=True)
    (OUT / "sets/square_import.json").write_text(json.dumps(recs, ensure_ascii=False, indent=1))
    for k, v in recs.items():
        print(k, v["size"], v.get("parts_merged", ""))


if __name__ == "__main__":
    main()
