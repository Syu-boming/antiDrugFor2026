"""G4 修正第 1 輪（美術，問題 33；v1.2 第 15.3 節「字幕前加角色名牌與小頭像」）：字幕說話者小頭像。

輸出 assets/final/ui/ui-speaker_<說話者 id>_v01.png（128×128 透明，畫面上約 52–56 px 顯示；id 與 app/src/ui/characters.ts 相同）：
  narrator（旁白）：未點亮的和紙燈籠剪紙徽章（程式畫，沒有任何文字）
  ale／xiaoqing／xiaoyu：從正式母版裁頭肩（不重新生成，不變臉），放進淡色圓盤
每個徽章：淡色圓盤＋白色紙芯邊＋外側深色細線（和角色立牌同一套剪紙描邊）。圖裡沒有文字；名牌文字仍由程式排字。
檢查圖：review/G4/art/speaker_icons_v01.png（原寸 2×、實際顯示尺寸 54 px、放在字幕框深底上、投影 v2）。
是否採用由主線決定（共用字幕樣式，G4 凍結前）。
用法：/opt/anaconda3/bin/python3 review/G4/art/scripts/make_speaker_icons.py
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import projsim  # noqa: E402

FIN = ROOT / "assets/final"
OUT = FIN / "ui"
ART = ROOT / "review/G4/art"
S = 128
SS = 4
RIM = (58, 44, 34)
WHITE = (252, 246, 234)
DISC = {"narrator": (243, 234, 214), "ale": (214, 224, 236), "xiaoqing": (210, 234, 228), "xiaoyu": (246, 222, 210)}


def badge_frame(content_rgba, disc_rgb):
    """content_rgba：S×S 的圖（透明處露出圓盤）。回傳加上圓盤、白紙芯邊、深色細線的徽章。"""
    s = S * SS
    yy, xx = np.mgrid[:s, :s].astype(np.float32)
    r = np.hypot(xx - (s - 1) / 2, yy - (s - 1) / 2) / (s / 2)
    R_IN, R_WHITE, R_OUT = 0.84, 0.95, 0.995
    big = np.array(Image.fromarray(content_rgba).resize((s, s), Image.LANCZOS)).astype(np.float32)
    base = np.zeros((s, s, 4), np.float32)
    base[..., :3] = disc_rgb
    # 圓盤紙紋
    n = ndimage.gaussian_filter(np.random.default_rng(5).standard_normal((s, s)), 2.0)
    base[..., :3] += (n / (n.std() + 1e-6))[..., None] * 3
    a = big[..., 3:4] / 255
    base[..., :3] = base[..., :3] * (1 - a) + big[..., :3] * a
    inner = r < R_IN
    ring_w = (r >= R_IN) & (r < R_WHITE)
    ring_d = (r >= R_WHITE) & (r < R_OUT)
    # 內圈與白紙芯之間的細深線
    seam = (r >= R_IN - 0.012) & (r < R_IN + 0.005)
    out = np.zeros((s, s, 4), np.float32)
    out[inner, :3] = base[inner, :3]
    out[ring_w, :3] = WHITE
    out[ring_d, :3] = RIM
    out[seam, :3] = RIM
    out[r < R_OUT, 3] = 255
    small = out.reshape(S, SS, S, SS, 4).mean(axis=(1, 3))
    al = small[..., 3] > 0
    _, (iy, ix) = ndimage.distance_transform_edt(~al, return_indices=True)
    small[~al, :3] = small[iy[~al], ix[~al], :3]
    return np.clip(small, 0, 255).astype(np.uint8)


def portrait(path, box):
    """從透明母版裁一個正方形（box＝x0, y0, 邊長），縮到 S×S。"""
    im = Image.open(path).convert("RGBA")
    x0, y0, side = box
    return np.array(im.crop((x0, y0, x0 + side, y0 + side)).resize((S, S), Image.LANCZOS))


def lantern():
    """未點亮的和紙燈籠（剪紙風、平光、無字）"""
    s = S * SS
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = s / 2, s * 0.54
    w, h = s * 0.50, s * 0.50
    line = (110, 78, 52, 255)
    # 掛繩與提環
    d.line([(cx, s * 0.08), (cx, cy - h / 2 - s * 0.05)], fill=line, width=int(SS * 3))
    d.ellipse([cx - s * 0.035, s * 0.06, cx + s * 0.035, s * 0.13], outline=line, width=int(SS * 3))
    # 燈籠身：米色和紙橢圓
    body = [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]
    d.ellipse([body[0] - SS * 3, body[1] - SS * 3, body[2] + SS * 3, body[3] + SS * 3], fill=line)
    d.ellipse(body, fill=(246, 232, 204, 255))
    # 竹骨：橫向弧線（剪紙的細線）
    for k in (-0.30, -0.12, 0.06, 0.24):
        yk = cy + k * h
        half = (w / 2) * np.sqrt(max(0.0, 1 - (2 * k) ** 2))
        d.arc([cx - half, yk - h * 0.05, cx + half, yk + h * 0.05], 0, 180, fill=(196, 160, 112, 255), width=int(SS * 2.2))
    # 縱向淡摺痕
    for k in (-0.22, 0.0, 0.22):
        d.arc([cx + k * w - w * 0.08, body[1], cx + k * w + w * 0.08, body[3]], 270 if k < 0 else 90, 90 if k < 0 else 270,
              fill=(222, 200, 160, 255), width=int(SS * 1.5)) if k != 0 else d.line([(cx, body[1] + SS * 6), (cx, body[3] - SS * 6)], fill=(222, 200, 160, 255), width=int(SS * 1.5))
    # 上下木蓋
    cap_w, cap_h = w * 0.46, h * 0.13
    for yc in (body[1] - cap_h * 0.35, body[3] - cap_h * 0.65):
        d.rounded_rectangle([cx - cap_w / 2 - SS * 3, yc - SS * 3, cx + cap_w / 2 + SS * 3, yc + cap_h + SS * 3], radius=SS * 6, fill=line)
        d.rounded_rectangle([cx - cap_w / 2, yc, cx + cap_w / 2, yc + cap_h], radius=SS * 5, fill=(150, 98, 62, 255))
    # 下方短流蘇（芥末黃紙條）
    for dx in (-0.05, 0.0, 0.05):
        x = cx + dx * s
        d.line([(x, body[3] + cap_h * 0.4), (x, body[3] + s * 0.12)], fill=(214, 168, 64, 255), width=int(SS * 3))
    arr = np.array(im).astype(np.float32)
    n = ndimage.gaussian_filter(np.random.default_rng(9).standard_normal((s, s)), 1.5)
    m = arr[..., 3] > 0
    arr[m, :3] += (n / (n.std() + 1e-6))[m][:, None] * 3
    small = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).resize((S, S), Image.LANCZOS)
    return np.array(small)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    src = {
        "ale": (FIN / "rig/chr-ale_head_v04.png", (14, 14, 262)),
        "xiaoqing": (FIN / "chr-xiaoqing_master_v04.png", (40, 6, 420)),
        "xiaoyu": (FIN / "chr-xiaoyu_master_v04.png", (40, 0, 420)),
    }
    icons = {"narrator": badge_frame(lantern(), DISC["narrator"])}
    for k, (p, box) in src.items():
        icons[k] = badge_frame(portrait(p, box), DISC[k])
    for k, arr in icons.items():
        Image.fromarray(arr, "RGBA").save(OUT / f"ui-speaker_{k}_v01.png", optimize=True)
    # 檢查圖
    font = ImageFont.truetype(projsim.FONT[0], 18)
    sheet = Image.new("RGB", (4 * 290 + 40, 520), (44, 42, 40))
    d = ImageDraw.Draw(sheet)
    d.text((20, 10), "字幕說話者小頭像 v01：上＝原寸 2×；中＝實際顯示 54 px 放在字幕框深底上；下＝同列投影 v2", font=font, fill=(240, 240, 240))
    names = {"narrator": "旁白", "ale": "阿樂叔叔", "xiaoqing": "小晴", "xiaoyu": "小宇"}
    for i, (k, arr) in enumerate(icons.items()):
        x = 20 + i * 290
        im = Image.fromarray(arr)
        big = Image.new("RGBA", (256, 256), (44, 42, 40, 255)); big.alpha_composite(im.resize((256, 256), Image.LANCZOS))
        sheet.paste(big.convert("RGB"), (x, 44))
        strip = Image.new("RGBA", (270, 80), (50, 45, 40, 255))
        strip.alpha_composite(im.resize((54, 54), Image.LANCZOS), (10, 6))
        ds = ImageDraw.Draw(strip)
        ds.text((74, 22), names[k], font=ImageFont.truetype(projsim.FONT[0], 22), fill=(245, 240, 230))
        sheet.paste(strip.convert("RGB"), (x, 320))
        pj = Image.fromarray(projsim.projector(np.array(strip.convert("RGB"))))
        sheet.paste(pj, (x, 410))
    sheet.save(ART / "speaker_icons_v01.png")
    print("saved", [f"ui-speaker_{k}_v01.png" for k in icons])


if __name__ == "__main__":
    main()
