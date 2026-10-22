"""G5 修正第 1 輪（主線裁定 5、b1_art a2 一般問題 5）：字幕說話者小頭像補齊。

沿用 G4 的 review/G4/art/scripts/make_speaker_icons.py 同款徽章（淡色圓盤＋白紙芯邊＋外側深色細線、128×128 透明），
輸出 assets/final/ui/ui-speaker_<說話者 id>_v01.png（id 與 app/src/ui/characters.ts 相同）：
  nurse（葉護理師）／guard（陳伯伯）／teacher（林老師）／pinan（品安）：從正式母版 chr-<角色>_master_v01.png 裁頭肩（不重新生成、不變臉）
  zhezhe（折折）：從折折程式畫面（review/G5/zhezhe/look.png 第一格「工作台上（平靜）」）裁頭部
  inviter（邀請者）：中性手掌圖示（程式畫，灰紙色、沒有臉、沒有膚色或飾品標記）
旁白（已有燈籠徽章）、執勤人員（只有聲音）維持現狀。圖裡沒有文字；名牌文字仍由程式排字。
檢查圖：review/G5/engine/art/speaker_icons_fix1.png（原寸 2×、實際顯示約 54 px 放在字幕框深底上、投影 v2）。
用法：/opt/anaconda3/bin/python3 review/G5/engine/scripts/make_speaker_icons_fix1.py
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import projsim  # noqa: E402

spec = importlib.util.spec_from_file_location("g4icons", ROOT / "review/G4/art/scripts/make_speaker_icons.py")
g4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g4)
S, SS = g4.S, g4.SS
FIN = ROOT / "assets/final"
OUT = FIN / "ui"
ART = ROOT / "review/G5/engine/art"

DISC = {"nurse": (212, 230, 222), "guard": (232, 232, 206), "teacher": (240, 222, 222), "pinan": (228, 220, 240),
        "zhezhe": (246, 232, 210), "inviter": (222, 222, 218)}
# 裁切框（母版像素：x0, y0, 邊長）：頭頂留一點、下巴下方露一點衣領，和 G4 小晴、小宇同樣的比例
SRC = {
    "nurse": (FIN / "chr-ye_master_v01.png", (100, 6, 330)),
    "guard": (FIN / "chr-chen_master_v01.png", (140, 4, 330)),
    "teacher": (FIN / "chr-lin_master_v01.png", (40, 8, 340)),
    "pinan": (FIN / "chr-pinan_master_v01.png", (45, 0, 440)),
}
ZHEZHE = (ROOT / "review/G5/zhezhe/look.png", (175, 170, 300))


def zhezhe_crop():
    im = Image.open(ZHEZHE[0]).convert("RGBA")
    x0, y0, side = ZHEZHE[1]
    return np.array(im.crop((x0, y0, x0 + side, y0 + side)).resize((S, S), Image.LANCZOS))


def palm():
    """中性手掌：灰紙色剪紙手掌（掌心朝前、五指張開），深棕細邊；沒有膚色、飾品、刺青"""
    s = S * SS
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    line = (88, 74, 62, 255)
    paper = (226, 220, 210, 255)
    sleeve = (150, 150, 146, 255)
    cx = s * 0.5
    # 袖口（灰色素面）
    def shape(fill, grow):
        g = grow
        d.rounded_rectangle([cx - s * 0.20 - g, s * 0.74 - g, cx + s * 0.20 + g, s * 0.98 + g], radius=SS * 6, fill=fill if fill != "sleeve" else sleeve)
    # 手掌＋手指（每段先畫深色外框再畫紙色）
    fingers = [(-0.135, 0.20, 0.30), (-0.045, 0.14, 0.36), (0.045, 0.15, 0.35), (0.13, 0.22, 0.29)]
    for pass_ in (0, 1):
        g = SS * 3 if pass_ == 0 else 0
        col = line if pass_ == 0 else paper
        d.rounded_rectangle([cx - s * 0.18 - g, s * 0.44 - g, cx + s * 0.18 + g, s * 0.78 + g], radius=s * 0.09 + g, fill=col)
        for dx, top, _h in fingers:
            x = cx + dx * s
            d.rounded_rectangle([x - s * 0.04 - g, s * top - g, x + s * 0.04 + g, s * 0.56 + g], radius=s * 0.04 + g, fill=col)
        # 拇指：從掌心左下斜向左上（圓頭粗線）
        w = s * 0.08 + 2 * g
        p0, p1 = (cx - s * 0.13, s * 0.68), (cx - s * 0.27, s * 0.47)
        d.line([p0, p1], fill=col, width=int(w))
        for (px, py) in (p0, p1):
            d.ellipse([px - w / 2, py - w / 2, px + w / 2, py + w / 2], fill=col)
        if pass_ == 1:  # 掌心再補一次紙色，蓋住拇指外框和掌心交界
            d.rounded_rectangle([cx - s * 0.18, s * 0.44, cx + s * 0.18, s * 0.78], radius=s * 0.09, fill=col)
    # 袖口最後畫（蓋住手腕）
    d.rounded_rectangle([cx - s * 0.22 - SS * 3, s * 0.76 - SS * 3, cx + s * 0.22 + SS * 3, s * 1.0], radius=SS * 6, fill=line)
    d.rounded_rectangle([cx - s * 0.22, s * 0.76, cx + s * 0.22, s * 1.0], radius=SS * 5, fill=sleeve)
    # （不畫掌紋：任何弧線都可能被看成臉）
    arr = np.array(im).astype(np.float32)
    n = ndimage.gaussian_filter(np.random.default_rng(11).standard_normal((s, s)), 1.5)
    m = arr[..., 3] > 0
    arr[m, :3] += (n / (n.std() + 1e-6))[m][:, None] * 3
    return np.array(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).resize((S, S), Image.LANCZOS))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ART.mkdir(parents=True, exist_ok=True)
    icons = {}
    for k, (p, box) in SRC.items():
        icons[k] = g4.badge_frame(g4.portrait(p, box), DISC[k])
    icons["zhezhe"] = g4.badge_frame(zhezhe_crop(), DISC["zhezhe"])
    icons["inviter"] = g4.badge_frame(palm(), DISC["inviter"])
    for k, arr in icons.items():
        Image.fromarray(arr, "RGBA").save(OUT / f"ui-speaker_{k}_v01.png", optimize=True)
    names = {"nurse": "葉護理師", "guard": "陳伯伯", "teacher": "林老師", "pinan": "品安", "zhezhe": "折折", "inviter": "邀請者",
             "ale": "阿樂叔叔", "xiaoqing": "小晴", "xiaoyu": "小宇", "narrator": "旁白"}
    allk = ["narrator", "ale", "xiaoqing", "xiaoyu", "zhezhe", "pinan", "nurse", "teacher", "guard", "inviter"]
    font = ImageFont.truetype(projsim.FONT[0], 18)
    font2 = ImageFont.truetype(projsim.FONT[0], 22)
    cols = 5
    sheet = Image.new("RGB", (cols * 290 + 40, 2 * 500 + 50), (44, 42, 40))
    d = ImageDraw.Draw(sheet)
    d.text((20, 10), "字幕說話者小頭像（G5 修正第 1 輪補齊）：上＝原寸 2×；中＝實際顯示 54 px 放在字幕框深底上；下＝同列投影 v2（前四個是 G4 既有）", font=font, fill=(240, 240, 240))
    for i, k in enumerate(allk):
        im = Image.open(OUT / f"ui-speaker_{k}_v01.png").convert("RGBA")
        x = 20 + (i % cols) * 290
        y0 = 44 + (i // cols) * 500
        big = Image.new("RGBA", (256, 256), (44, 42, 40, 255)); big.alpha_composite(im.resize((256, 256), Image.LANCZOS))
        sheet.paste(big.convert("RGB"), (x, y0))
        strip = Image.new("RGBA", (270, 80), (50, 45, 40, 255))
        strip.alpha_composite(im.resize((54, 54), Image.LANCZOS), (10, 6))
        ImageDraw.Draw(strip).text((74, 22), names[k], font=font2, fill=(245, 240, 230))
        sheet.paste(strip.convert("RGB"), (x, y0 + 270))
        sheet.paste(Image.fromarray(projsim.projector(np.array(strip.convert("RGB")))), (x, y0 + 360))
    sheet.save(ART / "speaker_icons_fix1.png")
    print("saved", [f"ui-speaker_{k}_v01.png" for k in icons], "→", ART / "speaker_icons_fix1.png")


if __name__ == "__main__":
    main()
