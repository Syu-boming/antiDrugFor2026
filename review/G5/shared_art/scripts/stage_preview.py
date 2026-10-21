"""G5 共用美術：舞台尺寸預覽（Python 針孔相機近似引擎鏡位；不是引擎擷取，只看比例、層次、明度）。

- 相機：app/src/stage/layers.ts 的 CAMERA_PRESETS（垂直視角 20°），1920×1080。
- 景片：layout.draft.json 的 pieces／props（垂直平面、面向觀眾，依 z 由遠到近畫）；地面：floor 圖投影到 y=0 平面。
- 角色：assets/final/rig/show_characters.json 的設定（腳底對齊、height／headTop 換算縮放）；阿樂叔叔用母版圖代替分件紙偶。
- 平光、無陰影（引擎另有燈光與柔影）；輸出原圖＋投影模擬 v2，並量兒童身後背景（隱藏角色重畫）的投影 v2 亮度。
輸出：review/G5/shared_art/sets/<景>_preview_<鏡位>.png、_proj.png、_preview.json
用法：/opt/anaconda3/bin/python3 review/G5/shared_art/scripts/stage_preview.py
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g5lib as L  # noqa: E402

ROOT = L.ROOT
sys.path.insert(0, str(ROOT / "tools"))
from projsim import projector  # noqa: E402

OUT = ROOT / "review/G5/shared_art/sets"
W, H = 1920, 1080
CAMS = {
    "medium": {"pos": [0.3, 3.3, 22], "target": [0.3, 2.75, 0], "fov": 20},
    "wide": {"pos": [0, 4.5, 31], "target": [0, 4.3, 0], "fov": 20},
    "mid_low": {"pos": [0.6, 1.6, 17.5], "target": [0.6, 1.4, 0], "fov": 20},
}
SHOW = json.loads((ROOT / "assets/final/rig/show_characters.json").read_text())


class Cam:
    def __init__(self, c):
        self.pos = np.array(c["pos"], float)
        f = np.array(c["target"], float) - self.pos
        self.f = f / np.linalg.norm(f)
        r = np.cross(self.f, [0, 1, 0])
        self.r = r / np.linalg.norm(r)
        self.u = np.cross(self.r, self.f)
        self.k = (H / 2) / math.tan(math.radians(c["fov"] / 2))

    def proj(self, p):
        d = np.array(p, float) - self.pos
        zc = d @ self.f
        return W / 2 + (d @ self.r) / zc * self.k, H / 2 - (d @ self.u) / zc * self.k, zc


def paste_plane(canvas, img, cam, x, y, z, w, h):
    if y < 0:   # 地面以下的部分被地板擋住（引擎有深度測試）
        keep = (y + h) / h
        if keep <= 0:
            return
        img = img.crop((0, 0, img.width, max(1, int(round(img.height * keep)))))
        h, y = y + h, 0.0
    x0, y0, _ = cam.proj([x - w / 2, y + h, z])
    x1, y1, _ = cam.proj([x + w / 2, y, z])
    pw, ph = int(round(x1 - x0)), int(round(y1 - y0))
    if pw < 2 or ph < 2 or x1 < 0 or x0 > W or y1 < 0 or y0 > H:
        return
    t = img.resize((pw, ph), Image.LANCZOS)
    canvas.alpha_composite(t, (int(round(x0)), int(round(y0)))) if 0 <= x0 and 0 <= y0 and x0 + pw <= W and y0 + ph <= H else _paste_clip(canvas, t, int(round(x0)), int(round(y0)))


def _paste_clip(canvas, t, x, y):
    big = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    big.paste(t, (x, y), t)
    canvas.alpha_composite(big)


def floor_layer(canvas, cam, floor_img, extent, color):
    xs, zs = extent if extent else ((0, 1), (0, 1))  # (x0,x1),(z0,z1)
    yy, xx = np.mgrid[:H, :W]
    dirs = (cam.f[None, None, :] + ((xx - W / 2) / cam.k)[..., None] * cam.r[None, None, :] - ((yy - H / 2) / cam.k)[..., None] * cam.u[None, None, :])
    t = -cam.pos[1] / np.where(np.abs(dirs[..., 1]) < 1e-6, -1e-6, dirs[..., 1])
    hit = t > 0
    px = cam.pos[0] + t * dirs[..., 0]
    pz = cam.pos[2] + t * dirs[..., 2]
    out = np.zeros((H, W, 4), np.uint8)
    out[hit] = list(color) + [255]
    if floor_img is not None:
        fa = np.array(floor_img.convert("RGBA"))
        fh, fw = fa.shape[:2]
        u = (px - xs[0]) / (xs[1] - xs[0]) * fw
        v = (pz - zs[0]) / (zs[1] - zs[0]) * fh
        ok = hit & (u >= 0) & (u < fw) & (v >= 0) & (v < fh)
        out[ok] = fa[v[ok].astype(int), u[ok].astype(int)]
    canvas.alpha_composite(Image.fromarray(out, "RGBA"))


def char_img(cid, pose):
    cfg = SHOW["characters"][cid]
    pc = cfg["poses"][pose]
    iid = pc["image"]
    f = next((FIN for FIN in sorted((ROOT / "assets/final").glob(iid + "_v*.png"))), None)
    im = Image.open(f).convert("RGBA")
    a = np.array(im)
    m = a[..., 3] >= 128
    ys, xs = np.nonzero(m)
    bot = ys.max() + 1
    low = m[bot - 40:bot].any(0)
    lx = np.nonzero(low)[0]
    feet = pc.get("feet", [(lx.min() + lx.max()) / 2, bot - 4])
    if "headTop" in pc:
        top = pc["headTop"]
    else:
        sys.path.insert(0, str(HERE))
        from build_show_characters import engine_top
        top = engine_top(a)
    s = cfg["height"] / (feet[1] - top)
    return im, feet, s


def ale_img():
    im = Image.open(ROOT / "assets/generated/chr-ale_master_v02.png").convert("RGBA")
    a = np.array(im)
    m = a[..., 3] >= 128
    ys, xs = np.nonzero(m)
    return im, [510, 1631], 3.55 / (1631 - ys.min())


def place_char(canvas, cam, im, feet, s, x, z, flip=False):
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
        feet = [im.width - feet[0], feet[1]]
    w, h = im.width * s, im.height * s
    cx = x + (im.width / 2 - feet[0]) * s
    yb = (feet[1] - im.height) * s
    paste_plane(canvas, im, cam, cx, yb, z, w, h)
    # 頭部範圍（量背景用）：上 35%
    x0, y0, _ = cam.proj([cx - w / 2, yb + h, z])
    x1, y1, _ = cam.proj([cx + w / 2, yb, z])
    return [x0, y0, x1, y1]


def resolve(iid, setname):
    """圖像 id → assets/final 檔案（同 tools/pack.mjs：去版本號；短名＝sets/<景名>/短名）。"""
    for cand in ([iid] if "/" in iid else []) + [f"sets/{setname}/{iid}", iid]:
        fs = sorted((ROOT / "assets/final").glob(cand + "_v*.png"))
        if fs:
            return str(fs[-1].relative_to(ROOT))
    raise FileNotFoundError(iid)


def from_official(lay, setname):
    """layout.json（antidrug-set/1）→ 預覽用的 pieces／floor。"""
    pieces = []
    w = lay["wall"]
    f = resolve(w["image"], setname)
    im = Image.open(ROOT / f)
    pieces.append({"file": f, "x": 0, "y": w.get("y", 0), "z": w.get("z", -3.6), "width": w["width"], "height": w["width"] * im.height / im.width, "layer": "backdrop"})
    for L in lay["layers"]:
        f = resolve(L["image"], setname)
        im = Image.open(ROOT / f)
        wd = L.get("width") or L["height"] * im.width / im.height
        pieces.append({"file": f, "x": L["x"], "y": L.get("y", 0), "z": L["z"], "width": wd, "height": wd * im.height / im.width, "layer": L.get("layer", "mid")})
    fl = lay.get("floor", {})
    floor = {"color": fl.get("color", "#d9c3a0")}
    if fl.get("image"):
        floor = {"file": resolve(fl["image"], setname), "world_width": fl.get("width", 32), "world_depth": fl.get("depth", 12),
                 "center": [0, 0, fl.get("z", 8.4) - fl.get("depth", 12) / 2]}
    return {"pieces": pieces, "floor": floor}


def render(layout, cast, cam_name, with_cast=True):
    cam = Cam(CAMS[cam_name])
    cv = Image.new("RGBA", (W, H), (200, 196, 188, 255))
    fl = layout.get("floor", {})
    if fl.get("file"):
        floor_layer(cv, cam, Image.open(ROOT / fl["file"]), ((-fl["world_width"] / 2, fl["world_width"] / 2),
                                                            (fl["center"][2] - fl["world_depth"] / 2, fl["center"][2] + fl["world_depth"] / 2)), (217, 195, 160))
    else:
        floor_layer(cv, cam, None, None, tuple(int(layout["floor"]["color"][i:i + 2], 16) for i in (1, 3, 5)))
    items = [(p["z"], "piece", p) for p in layout["pieces"]] + [(p["z"], "piece", p) for p in layout.get("props", [])]
    if with_cast:
        items += [(c["z"], "char", c) for c in cast]
    boxes = {}
    for z, kind, p in sorted(items, key=lambda t: t[0]):
        if kind == "piece":
            img = Image.open(ROOT / p["file"]).convert("RGBA")
            paste_plane(cv, img, cam, p["x"], p["y"], p["z"], p["width"], p["height"])
        else:
            im, feet, s = ale_img() if p["id"] == "ale" else char_img(p["id"], p["pose"])
            boxes[p["id"]] = place_char(cv, cam, im, feet, s, p["x"], p["z"], p.get("flip", False))
    return cv.convert("RGB"), boxes


def lum(rgb):
    a = rgb.astype(np.float32) / 255
    a = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    return a @ np.array([0.2126, 0.7152, 0.0722])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    scenes = {
        "gate": {
            "layout": from_official(json.loads((ROOT / "assets/final/sets/gate/layout.json").read_text()), "gate"),
            "cast": [{"id": "ale", "x": -4.9, "z": 0.3}, {"id": "chen", "pose": "stand", "x": -1.9, "z": 0.25},
                     {"id": "xiaoqing", "pose": "stand", "x": 2.7, "z": 0.35}, {"id": "xiaoyu", "pose": "dial", "x": 3.6, "z": 0.1},
                     {"id": "lin", "pose": "stand", "x": 4.6, "z": 0.3}],
            "kids": ["xiaoqing", "xiaoyu"],
            "cams": ["medium", "wide", "mid_low"],
        },
        "square": {
            "layout": from_official(json.loads((ROOT / "assets/final/sets/square/layout.json").read_text()), "square"),
            "cast": [{"id": "pinan", "pose": "sit_lantern", "x": -2.4, "z": 0.2}, {"id": "xiaoqing", "pose": "stand", "x": 0.4, "z": 0.35},
                     {"id": "xiaoyu", "pose": "stand", "x": 1.5, "z": 0.1}, {"id": "ye", "pose": "stand", "x": 4.6, "z": 0.2}],
            "kids": ["pinan", "xiaoqing", "xiaoyu"],
            "cams": ["medium", "wide"],
        },
    }
    report = {}
    for name, sc in scenes.items():
        for cam in sc["cams"]:
            img, boxes = render(sc["layout"], sc["cast"], cam)
            bg, _ = render(sc["layout"], sc["cast"], cam, with_cast=False)
            img.save(OUT / f"{name}_preview_{cam}.png")
            pj = projector(np.array(img).astype(np.float32))
            Image.fromarray(np.clip(pj, 0, 255).astype(np.uint8)).save(OUT / f"{name}_preview_{cam}_proj.png")
            pbg = projector(np.array(bg).astype(np.float32))
            Lb = lum(np.clip(pbg, 0, 255))
            rec = {}
            for k in sc["kids"]:
                if k not in boxes:
                    continue
                x0, y0, x1, y1 = [int(round(v)) for v in boxes[k]]
                x0, x1 = max(0, x0), min(W, x1)
                y0, y1 = max(0, y0), min(H, y1)
                if x1 <= x0 or y1 <= y0:
                    continue
                reg = Lb[y0:y0 + int((y1 - y0) * 0.6), x0:x1]   # 頭與上半身高度的背景
                rec[k] = {"box_px": [x0, y0, x1, y1], "bg_proj_v2_median": round(float(np.median(reg)), 3), "bg_proj_v2_p10": round(float(np.percentile(reg, 10)), 3),
                          "height_px": y1 - y0, "ok_ge_0.50": bool(np.median(reg) >= 0.5)}
            report[f"{name}_{cam}"] = rec
            print(name, cam, rec)
    (OUT / "preview_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
