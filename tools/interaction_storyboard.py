"""互動點靜態示意（G2 第 3 輪，兒童劇場導演意見 13）：一題（Q1）從出題到點燈的五個停點。

用法：/opt/anaconda3/bin/python3 tools/interaction_storyboard.py [--dir review/G2]
讀 quizcard_q1_{question,reveal,lamp}_v03.png（tools/quizcard_sample.mjs），輸出 interaction_storyboard_v03.png。
依據：v1.2 §7（每題約 75 秒的節奏、先全班作答再點一位、不離座）、§16.3（題卡靜止無倒數、揭答紙印章不畫紅叉）、
script/八題_v03.md Q1（題卡文字、輪區 A、揭答與「若不少人選了 1 或 3」的統一說法）；CLAUDE.md 第 7、11 條（不羞辱、不用攝影機與手勢辨識）。
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT = ("/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc", 10)


def font(px):
    try:
        return ImageFont.truetype(FONT[0], px, index=FONT[1])
    except OSError:
        return ImageFont.load_default()


def hand(d, x, y, n, s=1.0, col=(90, 70, 52)):
    """伸出 n 根手指的簡圖（與題卡手指圖示同一造型）。"""
    for i in range(4):
        up = i < n
        fx = x + (9 + i * 8) * s
        if up:
            d.rounded_rectangle([fx, y + 3 * s, fx + 6.6 * s, y + 28 * s], radius=3 * s, fill=col)
        else:
            d.rounded_rectangle([fx, y + 19 * s, fx + 6.6 * s, y + 29 * s], radius=3 * s, fill=col)
    d.rounded_rectangle([x + 7 * s, y + 22 * s, x + 41 * s, y + 48 * s], radius=10 * s, fill=col)


def classroom(w, h, card):
    img = Image.new("RGB", (w, h), (242, 236, 224))
    d = ImageDraw.Draw(img)
    # 銀幕（題卡靜止）
    sw = int(w * 0.46)
    sh = int(sw * 9 / 16)
    sx = (w - sw) // 2
    img.paste(card.resize((sw, sh), Image.LANCZOS), (sx, 18))
    d.rectangle([sx - 3, 15, sx + sw + 3, 18 + sh + 3], outline=(40, 40, 40), width=3)
    d.text((sx, 22 + sh), "銀幕：題卡靜止，沒有倒數、沒有滴答聲", font=font(17), fill=(60, 50, 40))
    # 老師（簡報筆）
    tx, ty = sx + sw + 40, 60 + sh // 2
    d.ellipse([tx, ty, tx + 34, ty + 34], fill=(70, 90, 140))
    d.rounded_rectangle([tx - 6, ty + 36, tx + 40, ty + 100], radius=10, fill=(70, 90, 140))
    d.text((tx - 30, ty + 106), "老師（簡報筆）", font=font(16), fill=(40, 40, 40))
    # 四區座位
    zy = 60 + sh + 40
    zw = (w - 100) // 4
    zones = "ABCD"
    for i, z in enumerate(zones):
        x0 = 40 + i * (zw + 7)
        hl = z == "A"
        d.rounded_rectangle([x0, zy, x0 + zw, h - 20], radius=14, fill=(255, 248, 230) if hl else (232, 226, 214),
                            outline=(36, 67, 140) if hl else (150, 140, 128), width=5 if hl else 2)
        d.text((x0 + 10, zy + 6), f"{z} 區" + ("（本題輪到）" if hl else ""), font=font(17), fill=(36, 67, 140) if hl else (90, 80, 70))
        k = 0
        for r in range(2):
            for c in range(4):
                n = [2, 2, 1, 2, 3, 2, 2, 1][(k + i * 3) % 8]
                hand(d, x0 + 10 + c * (zw - 16) / 4, zy + 36 + r * 42, n, 0.62)
                k += 1
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(ROOT / "review/G2"))
    a = ap.parse_args()
    d0 = Path(a.dir)
    q = Image.open(d0 / "quizcard_q1_question_v03.png").convert("RGB")
    rv = Image.open(d0 / "quizcard_q1_reveal_v03.png").convert("RGB")
    lp = Image.open(d0 / "quizcard_q1_lamp_v03.png").convert("RGB")
    pw, ph = 720, 405
    panels = [
        ("① 出題（約 12 秒）", q, ["折折收摺音效＝收聲訊號 → 舞台燈轉暗、題卡送上；字幕條收起。", "老師或旁白念題與三個選項（旁白念「一，」「二，」「三，」）。"]),
        ("② 想一想（約 8 秒）", q, ["題卡完全靜止：沒有倒數動畫、沒有滴答聲、沒有自動前進。", "老師：「想一想……3、2、1，一起比！」"]),
        ("③ 全班比手勢（約 10 秒）＋點一位（約 20 秒）", classroom(pw, ph, q), ["全班同時比 1、2、3 根手指，不離座、不搶答。", "老師點本題輪到的 A 區一位同學說理由；程式不用攝影機、不辨識手勢。"]),
        ("④ 揭答（約 15 秒，老師按簡報筆才揭答）", rv, ["正解蓋紙印章＋勾號＋外框，其他選項變淡；不畫紅叉、不用紅綠配對。", "「若不少人選了 1 或 3」只對全班統一說，不點名、不追問是誰選的。"]),
        ("⑤ 點燈（約 10 秒）", lp, ["台口上方第 1 盞紙燈約 1.5 秒漸亮、不閃爍（只看完成，不看答對率）。", "發獎與下一段劇情同時進行。"]),
    ]
    cols = 3
    rows = 2
    W = cols * (pw + 24) + 24
    H = rows * (ph + 140) + 80
    sheet = Image.new("RGB", (W, H), (36, 36, 38))
    d = ImageDraw.Draw(sheet)
    d.text((24, 16), "互動點靜態示意：Q1 一題的五個停點（每題約 75 秒；全程由老師用簡報筆逐步推進）", font=font(26), fill=(240, 240, 240))
    for i, (title, im, cap) in enumerate(panels):
        r, c = divmod(i, cols)
        x, y = 24 + c * (pw + 24), 70 + r * (ph + 140)
        sheet.paste(im.resize((pw, ph), Image.LANCZOS) if im.size != (pw, ph) else im, (x, y + 34))
        d.text((x, y + 2), title, font=font(21), fill=(255, 220, 120))
        for k, line in enumerate(cap):
            d.text((x, y + 34 + ph + 8 + k * 26), line, font=font(17), fill=(225, 225, 225))
    # 第 6 格：時間軸
    x, y = 24 + 2 * (pw + 24), 70 + (ph + 140)
    d.rectangle([x, y + 34, x + pw, y + 34 + ph], fill=(48, 46, 44))
    segs = [("讀題", 12), ("想", 8), ("比手勢", 10), ("點一位", 20), ("揭答", 15), ("點燈", 10)]
    tot = sum(s for _, s in segs)
    xx = x + 20
    colors = [(120, 150, 200), (150, 170, 120), (200, 170, 100), (200, 140, 110), (150, 120, 180), (230, 190, 90)]
    for (nm, s), col in zip(segs, colors):
        w = (pw - 40) * s / tot
        d.rectangle([xx, y + 120, xx + w - 3, y + 180], fill=col)
        d.text((xx + 4, y + 186), f"{nm}\n{s} 秒", font=font(16), fill=(230, 230, 230))
        xx += w
    d.text((x + 20, y + 60), "每題約 75 秒（v1.2 §7）；實際常拉長到約 90 秒，", font=font(18), fill=(240, 240, 240))
    d.text((x + 20, y + 86), "所以發獎和下一段劇情同時進行。", font=font(18), fill=(240, 240, 240))
    d.text((x + 20, y + 260), "其他互動點：找找看 1／2／3（a1_c003、a2_c001、a4_c013，", font=font(17), fill=(220, 220, 220))
    d.text((x + 20, y + 286), "不計獎、舉手指認；畫面不加箭頭、光圈或提示音）。", font=font(17), fill=(220, 220, 220))
    d.text((x + 20, y + 330), "答錯不羞辱、不說「害人出事」；不詢問家庭經驗。", font=font(17), fill=(220, 220, 220))
    sheet.save(d0 / "interaction_storyboard_v03.png")
    print(d0 / "interaction_storyboard_v03.png")


if __name__ == "__main__":
    main()
