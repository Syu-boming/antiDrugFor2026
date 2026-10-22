"""G6 精修（第一批 a0、a1、a2）的程式美術。不用 Codex 生圖，只加工既有母版。

用法：/opt/anaconda3/bin/python3 review/G5/a0/scripts/build_polish_art.py [pinan|hands|rack|all]

pinan（a1_c004 品安偷偷回頭看柱子，b1r3_failed a1 一般問題 3）
  輸入：assets/final/chr-pinan_pose-sit-lantern_v01.png（顯示時 facing −1 ＋ sit_lantern_back＝這張原圖的方向：臉朝左、眼睛看左下的燈籠）
  做法（在顯示方向上做，最後左右翻轉存檔，和 sit_lantern_back 一樣用 facing −1 顯示）：
    - 眼珠（深褐虹膜＋瞳孔＋高光）往左上移，眼白補在下方，上眼線蓋在眼珠上面（不改眼眶形狀）
    - 頭部以下巴與脖子交界為支點順時針（臉那側往上）轉一點：y＜400 全轉、400–475 漸變到 0（脖子平順彎過去，沒有接縫），
      燈籠、手、身體不動
  輸出：assets/final/chr-pinan_pose-sit-lantern-look1_v01.png（中間格：眼珠移一半、頭轉 6°）
        assets/final/chr-pinan_pose-sit-lantern-look2_v01.png（停住的那格：眼珠移到左上、頭轉 12°）

hands（a2_c008 手部近景，b1r3_failed a2 一般問題 3：右手腕分件接縫線、手指簡化）
  輸入：assets/final/rig/chr-ale_hand-{r,l}_v04.png（母版分件；修正第 2 輪的 insert v01 也是從這兩張做的）
  輸出：assets/final/sets/a2_shop/insert-ale-hand-{r,l}_v02.png（2 倍解析度；前臂、外框沿用 v01）
  做法：
    - 手的上緣（接在前臂上的切口）原本是 2 列深色墨線＋外緣深色紙邊 → 改成 3 px 米白紙邊（紙片疊在前臂上的切口，和全劇剪紙的白紙芯同色），
      看不到深色接縫線
    - 指縫與指節：沿著手內部的深色線條加柔和陰影（約 4 px 擴散、最深 −20%），線條本身補深一點；手背中段微亮 4%
    - 手心裡的淺色紙片（母版的接合舌片）改成陰影中的膚色（像捧起的手心）
    - 其餘同修正第 2 輪：紙纖維紋理、邊緣往內 6 px 漸暗 10%、外緣 2 px 深色紙邊（上緣切口除外）

lamps（a0_c002 上半部空牆，b1r3_failed a0 一般問題 3）
  輸入：assets/final/bg-workshop-lanterns_v01.png（G2 燈籠店吊燈籠，同一套畫風）
  做法：裁中間三盞（桃、黃、綠）連同竹竿，左右翻轉（和店裡原本那排的順序不同），竹竿兩端加兩個小木托架（釘在牆上）；
        不投影子（景裡設定），只當牆上的景片
  輸出：assets/final/sets/workshop_a0/hanglamps_v01.png
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[4]
FINAL = ROOT / "assets/final"


# ───────────────────────────── 品安看柱子 ─────────────────────────────
EYES = [  # 顯示方向（＝原圖）的眼睛框與虹膜種子點、上眼線厚度
    {"box": (148, 306, 204, 364), "seed": (177, 342), "lash": 6},
    {"box": (246, 284, 320, 344), "seed": (276, 322), "lash": 7},
]


def _lum(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def shift_irises(a, dx, dy):
    """a：HxWx4 float（0–255）。每隻眼睛：虹膜層往 (dx, dy) 移，裁在眼白＋原虹膜範圍內；空出來的地方補眼白色。"""
    out = a.copy()
    for e in EYES:
        x0, y0, x1, y1 = e["box"]
        sub = a[y0:y1, x0:x1]
        L = _lum(sub)
        dark = L < 120
        sclera = (sub[..., 0] > 228) & (sub[..., 1] > 218) & (sub[..., 2] > 190)
        h, w = dark.shape
        # 上眼線：每一欄由上往下第一段深色的前 lash 個像素
        lash = np.zeros_like(dark)
        for x in range(w):
            col = np.where(dark[:, x])[0]
            if len(col):
                top = col[0]
                if top < h * 0.55:
                    lash[top:top + e["lash"], x] = dark[top:top + e["lash"], x]
        iris_dark = dark & ~lash
        lab, _ = ndimage.label(iris_dark)
        sx, sy = e["seed"][0] - x0, e["seed"][1] - y0
        k = lab[sy, sx]
        if k == 0:
            raise SystemExit(f"眼睛種子點不在虹膜上：{e}")
        iris = lab == k
        iris = ndimage.binary_fill_holes(iris)                      # 含高光點
        skin = (sub[..., 0] > 225) & (sub[..., 1] > 150) & (sub[..., 1] < 216) & (sub[..., 2] < 205)
        iris_aa = ndimage.binary_dilation(iris, iterations=1) & ~lash & ~skin   # 虹膜＋一圈反鋸齒（不含膚色、上眼線）
        opening = (ndimage.binary_fill_holes(sclera | iris_aa) & ~ndimage.binary_dilation(lash, iterations=1) & ~skin) | iris_aa
        # 眼白色：原圖眼白的中位數
        sc = np.median(sub[sclera][:, :3], axis=0)
        base = sub.copy()
        base[iris_aa, :3] = sc
        # 移動後的虹膜層
        layer = np.zeros_like(sub)
        m = np.zeros((h, w), bool)
        ys, xs = np.where(iris_aa)
        ty, tx = ys + dy, xs + dx
        ok = (ty >= 0) & (ty < h) & (tx >= 0) & (tx < w)
        layer[ty[ok], tx[ok]] = sub[ys[ok], xs[ok]]
        m[ty[ok], tx[ok]] = True
        m &= opening
        res = base.copy()
        res[m] = layer[m]
        out[y0:y1, x0:x1] = res
    return out


def bend_head(a, deg, pivot=(318.0, 440.0), y_full=400.0, y_zero=475.0):
    """輸出像素 (x, y) 的旋轉角＝deg × w(y)（y＜y_full 全轉，y_zero 以下 0，中間 smoothstep）；反向取樣（預乘 alpha，雙線性）。"""
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = np.clip((y_zero - yy) / (y_zero - y_full), 0, 1)
    wgt = u * u * (3 - 2 * u)
    th = np.deg2rad(deg) * wgt
    px, py = pivot
    dx, dy = xx - px, yy - py
    c, s = np.cos(-th), np.sin(-th)                                 # 反向旋轉
    sx = px + dx * c - dy * s
    sy = py + dx * s + dy * c
    pre = a.copy()
    pre[..., :3] *= pre[..., 3:4] / 255.0
    out = np.zeros_like(a)
    for ch in range(4):
        out[..., ch] = ndimage.map_coordinates(pre[..., ch], [sy, sx], order=1, mode="constant", cval=0.0)
    al = np.clip(out[..., 3:4], 1e-3, 255)
    out[..., :3] = np.where(out[..., 3:4] > 0.5, out[..., :3] * 255.0 / al, 0)
    return out


def pinan():
    src = Image.open(FINAL / "chr-pinan_pose-sit-lantern_v01.png").convert("RGBA")
    a = np.asarray(src).astype(np.float32)
    for name, (dx, dy, deg) in {"look1": (-1, -3, 6.0), "look2": (-3, -7, 12.0)}.items():
        b = shift_irises(a, dx, dy)
        b = bend_head(b, deg)
        b = np.clip(b, 0, 255).astype(np.uint8)
        im = ImageOps.mirror(Image.fromarray(b, "RGBA"))          # 和 sit_lantern_back 一樣：檔案＝顯示方向的鏡像，用 facing −1 顯示
        dst = FINAL / f"chr-pinan_pose-sit-lantern-{name}_v01.png"
        im.save(dst, optimize=True)
        print("wrote", dst.relative_to(ROOT), im.size)


# ───────────────────────────── 手部近景的手 ─────────────────────────────
INK = np.array([78, 62, 51], np.float32)
PAPER = np.array([246, 236, 220], np.float32)


def hand(side):
    sys.path.insert(0, str(ROOT / "review/G5/shared_art/scripts"))
    import paperdraw as P  # noqa: E402
    src = Image.open(FINAL / f"rig/chr-ale_hand-{side}_v04.png").convert("RGBA")
    a0 = np.asarray(src).astype(np.float32)
    m0 = a0[..., 3] > 128
    ys, xs = np.where(m0)
    top = ys.min()
    # 1 倍：上緣兩列深色墨線換成下面一列的膚色
    a0[top:top + 2, :, :3] = a0[top + 2:top + 3, :, :3]
    S = 2
    im = Image.fromarray(np.clip(a0, 0, 255).astype(np.uint8), "RGBA").resize((src.width * S, src.height * S), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32)
    h, w = a.shape[:2]
    m = a[..., 3] > 128
    din = ndimage.distance_transform_edt(m)
    rgb = a[..., :3]
    L = _lum(rgb)
    skinref = ndimage.median_filter(np.where(m, L, 0), size=15)
    # 手心淺色紙片 → 陰影中的膚色
    pale = m & (rgb[..., 2] / np.maximum(rgb[..., 0], 1) > 0.62) & (L > 170)
    pale = ndimage.binary_opening(pale, iterations=1)
    pale_soft = ndimage.gaussian_filter(pale.astype(np.float32), 1.2)
    shadow_skin = np.array([228, 152, 98], np.float32)
    rgb = rgb * (1 - pale_soft[..., None]) + shadow_skin * pale_soft[..., None]
    L = _lum(rgb)
    # 內部線條（指縫、指節）：比附近膚色暗 25% 以上、離外緣 3 px 以上
    lines = m & (din > 3) & (L < skinref * 0.75) & ~ndimage.binary_dilation(pale, iterations=3)
    lines = ndimage.binary_opening(lines, structure=np.ones((2, 2))) | lines & (L < skinref * 0.6)
    ao = ndimage.gaussian_filter(lines.astype(np.float32), 4.0)
    ao = np.clip(ao / max(ao.max(), 1e-6) * 1.6, 0, 1)
    shade = 1 - 0.20 * ao
    # 手背中段微亮（離外緣與線條都遠的地方）
    far = np.clip((din - 8) / 20, 0, 1) * (1 - ao)
    shade *= 1 + 0.04 * ndimage.gaussian_filter(far, 6)
    rgb = rgb * shade[..., None]
    rgb[lines] = rgb[lines] * 0.75 + INK * 0.25
    a[..., :3] = rgb
    # 紙纖維、厚度
    tex = 1.0 + (P.paper_tex(w, h) - 1.0) * 1.6
    a[..., :3] *= tex[..., None]
    k = np.clip(1 - din / 6.0, 0, 1) * 0.10
    a[..., :3] *= (1 - k[..., None])
    # 外緣：上緣切口（最上面 5 px 內）用 3 px 米白紙邊，其他地方 2 px 深色紙邊
    yy = np.arange(h)[:, None] * np.ones((1, w))
    cut = yy <= top * S + 5
    edge = m & (din <= 2.0) & ~cut
    a[edge, :3] = a[edge, :3] * 0.2 + INK * 0.8
    paper_band = m & cut & (yy <= top * S + 3)
    pt = PAPER[None, :] * tex[paper_band][:, None]
    a[paper_band, :3] = pt
    # 紙邊下緣一條很淡的影子（紙片厚度）
    sh = m & (yy > top * S + 3) & (yy <= top * S + 5)
    a[sh, :3] *= 0.88
    a = np.clip(a, 0, 255).astype(np.uint8)
    dst = FINAL / f"sets/a2_shop/insert-ale-hand-{side}_v02.png"
    P.save(a, dst)
    print("wrote", dst.relative_to(ROOT), a.shape[1], a.shape[0])


# ───────────────────────────── 牆上的一排吊燈籠（a0） ─────────────────────────────
def lamps():
    from PIL import ImageDraw
    src = Image.open(FINAL / "bg-workshop-lanterns_v01.png").convert("RGBA")
    crop = src.crop((400, 0, 1240, src.height))
    crop = ImageOps.mirror(crop)
    pad = 26
    W, H = crop.width + 2 * pad, crop.height + 30
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # 木托架（竹竿下方、釘在牆上的小木塊）：先畫，竹竿蓋在上面
    d = ImageDraw.Draw(out)
    wood, dark = (176, 128, 84, 255), (122, 86, 58, 255)
    for cx in (pad + 22, W - pad - 22):
        d.rounded_rectangle([cx - 13, 6, cx + 13, 62], 5, fill=wood, outline=dark, width=2)
        d.ellipse([cx - 4, 40, cx + 4, 48], fill=dark)                 # 木釘
    out.alpha_composite(crop, (pad, 0))
    bb = out.getbbox()
    out = out.crop((0, 0, W, min(H, bb[3] + 4)))                       # 底邊貼齊燈籠下緣（景片以底邊中央為原點）
    a = np.asarray(out).astype(np.float32)
    sys.path.insert(0, str(ROOT / "review/G5/shared_art/scripts"))
    import paperdraw as P  # noqa: E402
    dst = FINAL / "sets/workshop_a0/hanglamps_v01.png"
    P.save(np.clip(a, 0, 255).astype(np.uint8), dst)
    print("wrote", dst.relative_to(ROOT), out.width, out.height)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("pinan", "all"):
        pinan()
    if what in ("lamps", "all"):
        lamps()
    if what in ("hands", "all"):
        hand("r")
        hand("l")
