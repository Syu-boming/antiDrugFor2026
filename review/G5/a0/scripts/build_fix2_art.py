"""G5 修正第 2 輪（第一幕）：燈籠店的窗嵌進店面牆（b1r2_regress a1 一般問題 2：窗戶像獨立立在廣場上的窗框）。程式繪製，不用 Codex 生圖。

輸出：
  assets/final/sets/square_a1/shopwall_v01.png   騎樓最右邊那一間的燈籠店門面（窗的後面）：紙瓦屋簷、米色灰泥牆（同騎樓柱子的色系、紙纖維）、
                                                  左右木柱、下緣木裙板、右邊店門（淺杏色門簾，沒有字）、門上一盞不亮的小紙燈籠。
                                                  牆是實心的（窗洞由前面的窗框、窗紙、剪影負責），遮住騎樓柱子的石座與台階。
  世界尺寸 3.75 × 3.85 單位（150 px／單位）：左下角在 x 3.35、y −0.07（square_a1.ts 的 SHOPWALL）。
規則：圖裡沒有任何文字、數字、標誌；不畫陰影與方向光；2 px 深色紙邊（finish edge_dark）。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "review/G5/shared_art/scripts"))
import paperdraw as P  # noqa: E402

OUT1 = ROOT / "assets/final/sets/square_a1"
PP = 150
X0, Y0, WU, HU = 3.35, -0.07, 3.75, 3.85


def px(xw, yw):
    return (xw - X0) * PP, (Y0 + HU - yw) * PP


def shopwall():
    W, H = int(WU * PP), int(HU * PP)
    s = P.Sheet(W, H)
    stucco = (234, 208, 170, 255)
    wood, wood2, wood3 = (150, 108, 72, 255), (170, 126, 86, 255), (128, 92, 62, 255)
    tile, tile2 = (166, 98, 72, 255), (142, 82, 62, 255)
    # 牆身（灰泥）
    _, yt = px(0, 3.36)
    s.rect(10, yt, W - 10, H - 2, stucco, line=2.0)
    # 左右木柱（試過左邊改淺色壁柱：鏡頭跟拍平移時窗框左緣附近的格子每秒變化 4 次，所以維持深色木柱）
    s.rect(4, yt, 26, H - 2, wood, line=2.0)
    s.rect(W - 26, yt, W - 4, H - 2, wood, line=2.0)
    # 下緣木裙板
    _, ys = px(0, 0.26)
    s.rect(10, ys, W - 10, H - 2, wood2, line=2.0)
    for xk in range(60, W - 30, 70):
        s.line([(xk, ys + 6), (xk, H - 8)], 1.4)
    # 店門（右邊）：木門框＋淺杏色門簾（沒有字）＋下半木門板
    dx0, _ = px(6.36, 0); dx1, _ = px(6.98, 0)
    _, dy0 = px(0, 2.05)
    s.rect(dx0 - 8, dy0 - 8, dx1 + 8, ys, wood3, line=2.0)
    s.rect(dx0, dy0, dx1, ys, (112, 84, 62, 255), line=1.6)
    _, dyc = px(0, 1.45)
    s.rect(dx0 + 4, dy0 + 4, dx1 - 4, dyc, (240, 198, 152, 255), line=1.6)
    s.line([((dx0 + dx1) / 2, dy0 + 4), ((dx0 + dx1) / 2, dyc)], 1.6)
    for yk in (dyc + 30, dyc + 75):
        s.line([(dx0 + 10, yk), (dx1 - 10, yk)], 1.2)
    # 門上一盞不亮的小紙燈籠（掛在屋簷下）
    for xw in (6.67,):
        lx, ly = px(xw, 2.62)
        s.line([(lx, px(0, 3.36)[1]), (lx, ly - 24)], 1.4)
        s.ellipse(lx - 15, ly - 22, lx + 15, ly + 20, (246, 222, 176, 255), line=1.4)
        s.rect(lx - 7, ly - 26, lx + 7, ly - 20, (90, 64, 44, 255), line=0)
        s.rect(lx - 7, ly + 18, lx + 7, ly + 24, (90, 64, 44, 255), line=0)
    # 紙瓦屋簷（下緣比牆寬一點的梯形，一排瓦片弧線）
    _, ye0 = px(0, 3.78)
    _, ye1 = px(0, 3.30)
    s.poly([(18, ye0), (W - 18, ye0), (W - 2, ye1), (2, ye1)], tile, line=2.0)
    s.rect(2, ye1 - 12, W - 2, ye1 + 2, tile2, line=1.6)
    for xk in range(24, W - 10, 34):
        s.line([(xk, ye0 + 6), (xk - 6, ye1 - 14)], 1.2, (110, 64, 48, 255))
    a = s.finish(edge_dark=0.08)
    return a, {"px_per_unit": PP, "origin_bottom_left_world": [X0, Y0], "size_units": [WU, HU]}


def main():
    meta = {}
    a, m = shopwall()
    P.save(a, OUT1 / "shopwall_v01.png")
    meta["shopwall_v01.png"] = m
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
