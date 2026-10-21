"""G4 修正第 2 輪（美術，問題 1、5、9）：兩眼同閉的中性閉眼／半閉換片。

問題：第 1 輪的眼睛遮罩把「碰到髮絲或臉緣的整條睫毛」判成保護線，結果遠側（畫面左側、較小）那隻眼
沒有被填補、也畫不上眼皮線 → 眨眼時一眼閉一眼睜（看起來像眨單眼），或只剩淡化殘影。

這一版的做法（只重做 eyes_half、eyes_closed；嘴巴換片、睜眼原圖不變）：
- 每隻眼用手量的眼睛橢圓（eye_ellipses）外擴 2 px 當填補範圍，橢圓內一律重填成皮膚（不再判保護線）。
- 橢圓外的深色連通區：伸出去的部分很小（≤ 90 px、距橢圓 ≤ 7 px，例如睫毛尾端）就一起填掉；
  伸出去很大（髮絲、眼鏡框、臉緣線）就只保護橢圓外那段，不填不蓋。
- 兩眼都用同一個畫法畫線：閉眼＝近乎平直、略往下彎的中性閉眼線（closed_curve 0.05，不是向上拱的笑眼），
  半閉＝上半眼改皮膚＋眼皮線、下半眼保留原圖。兩隻眼在同一張換片裡，所以換片一切換就是兩眼同時閉、同時開。
- 每張換片自動檢查：兩隻眼各自「原本的眼白／眼珠像素還看得到的比例」與「新眼皮線的深色像素數」，
  寫進 review/G4/art/blink_check_r2.json；任一隻眼殘留 > 3% 或線 < 40 px 就報錯停下。

輸出（新版本號，不覆寫舊檔；打包 id 不變，tools/pack.mjs 自動取最新版）：
  assets/final/face/xiaoqing/chr-xiaoqing_eyes_half_v02.png、chr-xiaoqing_eyes_closed_v03.png（reach 姿勢）
  assets/final/face/xiaoqing/chr-xiaoqing_<watch|palm|worried>-eyes_half_v02.png、-eyes_closed_v02.png
  assets/final/face/xiaoyu/chr-xiaoyu_eyes_half_v02.png、chr-xiaoyu_eyes_closed_v03.png
  assets/final/face/xiaoqing/face-<姿勢>_v02.json、face_v04.json（原生格式，內容同 v03，只更新 change_log）
  assets/final/face/xiaoyu/face_v03.json
  review/G4/art/face_sheet_xq_v06.png（小晴三新姿勢）、face_sheet_v06.png（小晴 reach、小宇）、
  review/G4/art/blink_zoom_r2.png（每張換片的兩眼放大＋舞台尺寸）、blink_check_r2.json
用法：/opt/anaconda3/bin/python3 review/G4/art/scripts/build_faces_r2.py
"""
import json
import math
import sys
import zlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_faces as BF  # noqa: E402

ROOT = BF.ROOT
FIN = ROOT / "assets/final"
ART = ROOT / "review/G4/art"
CLOSED_CURVE = 0.05     # > 0：往下彎（中性閉眼）；0.05＝近乎平直
CLOSED_V = 0.55         # 閉眼線在眼高的位置（0＝上緣、1＝下緣）
HALF_V = 0.50
MARGIN = 2.0            # 橢圓外擴（px），蓋住抗鋸齒邊
SMALL_OUT = 90          # 橢圓外的深色伸出部分 ≤ 此像素數＝睫毛尾端，一起填
NEAR_OUT = 7            # 且距離橢圓 ≤ 此 px


def ellipse_mask(shape, e, grow=0.0):
    H, W = shape
    ex, ey, ea, eb, th = e
    yy, xx = np.mgrid[:H, :W]
    t = math.radians(th)
    dx, dy = xx - ex, yy - ey
    u = dx * math.cos(t) + dy * math.sin(t)
    v = -dx * math.sin(t) + dy * math.cos(t)
    return (u / (ea + grow)) ** 2 + (v / (eb + grow)) ** 2 <= 1


def eye_regions(a, cfg):
    """回傳 [每眼 (fill, core, ell)]、protect（橢圓外要保護的深色線）"""
    H, W = a.shape[:2]
    L = BF.lum(a[..., :3].astype(np.float32))
    eb = cfg["eyes_box"]
    protect_all = (L < 125) & (a[..., 3] > 128)
    skin0, _ = BF.skin_stats(a, eb, protect_all)
    dist = np.abs(a[..., :3].astype(np.float32) - skin0).sum(-1)
    darkish = ((L < 135) | (dist > 110)) & (a[..., 3] > 128)
    out, prot = [], np.zeros((H, W), bool)
    for e in cfg["eye_ellipses"]:
        ell = ellipse_mask((H, W), e)
        ellm = ellipse_mask((H, W), e, MARGIN)
        near = ellipse_mask((H, W), e, MARGIN + 20)
        fill = ellm.copy()
        lab, n = ndimage.label(darkish & near)
        dt = ndimage.distance_transform_edt(~ellm)
        for k in range(1, n + 1):
            comp = lab == k
            if not (comp & ellm).any():
                continue
            outside = comp & ~ellm
            if not outside.any():
                continue
            # 伸到 near 範圍邊界的連通區＝髮絲／眼鏡框／臉緣（還會繼續往外延伸）
            touches_edge = (comp & ~ellipse_mask((H, W), e, MARGIN + 18)).any()
            if outside.sum() <= SMALL_OUT and dt[outside].max() <= NEAR_OUT and not touches_edge:
                fill |= ndimage.binary_dilation(outside, iterations=1) & near
            else:
                prot |= outside
        # 橢圓外的淺色非膚色小碎片（眼白外緣、高光點、被切到一半的雙眼皮摺線）：碰到填補區且很小就一起填掉，
        # 免得閉眼後留下白點或半截摺線
        light = (dist > 30) & (L >= 135) & (a[..., 3] > 128) & near & ~fill
        lab2, n2 = ndimage.label(light)
        fill_d = ndimage.binary_dilation(fill, iterations=4)
        edge = ~ellipse_mask((H, W), e, MARGIN + 18)
        for k in range(1, n2 + 1):
            comp = lab2 == k
            small_touch = (comp & fill_d).any() and comp.sum() <= 150
            tiny_near = comp.sum() <= 60      # 摺線被切成幾段時的小碎段
            if (small_touch or tiny_near) and not (comp & edge).any():
                fill |= ndimage.binary_dilation(comp, iterations=1) & near & ~(darkish & ~fill)
        core = ndimage.binary_fill_holes(ell & (dist > 40) & (a[..., 3] > 128))
        out.append((fill, core, ell))
    fill_all = out[0][0] | out[1][0]
    prot &= ~fill_all
    # 眼睛框內其他深色線（眉毛、髮絲、眼鏡框）一律保護
    prot |= darkish & ~fill_all
    return out, prot, L, dist


def lid_geom(core, c, tilt):
    ys, xs = np.nonzero(core)
    Rinv = BF.rot(-tilt)
    uv = Rinv @ np.stack([xs - c[0], ys - c[1]]).astype(float)
    u0, u1 = np.percentile(uv[0], 2), np.percentile(uv[0], 98)
    v0, v1 = np.percentile(uv[1], 2), np.percentile(uv[1], 98)
    return (u0 + u1) / 2, (u1 - u0) / 2, v0, (v1 - v0), uv, ys, xs


def build_eyes(name, cfg, prefix, ver, out_dir):
    """只做 eyes_half／eyes_closed。回傳 {piece: rec}, 檢查數據"""
    a = np.array(Image.open(cfg["head"]).convert("RGBA"))
    H, W = a.shape[:2]
    tilt = cfg["tilt"]
    eb = cfg["eyes_box"]
    regions, prot, L, dist = eye_regions(a, cfg)
    fill_all = regions[0][0] | regions[1][0]
    protect_all = (L < 125) & (a[..., 3] > 128)
    skin_e, skin_m = BF.skin_stats(a, eb, fill_all | protect_all)
    skin_full = np.zeros((H, W), bool)
    skin_full[eb[1]:eb[3], eb[0]:eb[2]] = skin_m
    # 每隻眼分開填：邊界上的保護線用「這隻眼周圍 3–8 px 的皮膚平均色」代替（不用整框中位數），填出來的膚色才不會偏暗一塊
    clean = a.copy()
    for fill, core, ell in regions:
        ring = ndimage.binary_dilation(fill, iterations=8) & ~ndimage.binary_dilation(fill, iterations=2) & (L > 150) & (dist < 40) & (a[..., 3] > 200)
        local = a[ring][:, :3].astype(np.float32).mean(0) if ring.sum() > 30 else skin_e
        clean = BF.harmonic_fill(clean, fill, local, protect_all & ~fill, iters=900)
    clean = BF.paper_grain(clean, fill_all, skin_full & ~fill_all, seed=7 + zlib.crc32((name + prefix).encode()) % 100)
    core_all = regions[0][1] | regions[1][1]
    lash_px = a[core_all & (L < 60)]
    lash = np.median(lash_px[:, :3], 0) if len(lash_px) else np.array([30, 22, 20])
    lash_c = tuple(int(x) for x in lash) + (255,)
    rec = {"groups": {}, "pieces": {}}
    pieces = {}
    eyes_c = [(e[0], e[1]) for e in cfg["eye_ellipses"]]
    for var in ("eyes_half", "eyes_closed"):
        cv = BF.Canvas(eb)
        keep_lower = np.zeros((H, W), bool)
        for c, (fill, core, ell) in zip(eyes_c, regions):
            uc, hw_, v0, hh, uv, ys, xs = lid_geom(core, c, tilt)
            if var == "eyes_half":
                vm = v0 + HALF_V * hh
                vlid = vm + 0.10 * hh * np.clip(1 - ((uv[0] - uc) / hw_) ** 2, 0, 1)
                lower = uv[1] > vlid + 0.6
                kl = np.zeros((H, W), bool)
                kl[ys[lower], xs[lower]] = True
                keep_lower |= kl & ell
                u = np.linspace(uc - hw_ * 1.0, uc + hw_ * 1.0, 48)
                v = vm + 0.10 * hh * np.clip(1 - ((u - uc) / hw_) ** 2, 0, 1)
                X, Y = BF.to_img(c, tilt, u, v)
                cv.stroke(X, Y, cfg["lid_lw"], lash_c, taper=False)
            else:
                u = np.linspace(uc - hw_ * 0.92, uc + hw_ * 0.92, 48)
                vm = v0 + CLOSED_V * hh
                v = vm + CLOSED_CURVE * hh * np.clip(1 - ((u - uc) / (hw_ * 0.92)) ** 2, 0, 1) ** 0.8
                X, Y = BF.to_img(c, tilt, u, v)
                cv.stroke(X, Y, cfg["lid_lw"], lash_c, taper=True)
        img = clean.copy()
        if var == "eyes_half":
            img[keep_lower] = a[keep_lower]
        pieces[var] = (img, cv.result())
    old_ver, old_write = BF.PIECE_VER, BF.WRITE
    old_prefix = BF.PREFIX
    BF.PIECE_VER = {"eyes_half": ver["eyes_half"], "eyes_closed": ver["eyes_closed"]}
    BF.WRITE = {"eyes_half", "eyes_closed"}
    BF.PREFIX = prefix
    BF.write_group(name, "eyes", eb, a, clean, fill_all, prot, pieces, out_dir, rec)
    BF.PIECE_VER, BF.WRITE, BF.PREFIX = old_ver, old_write, old_prefix
    # ---- 檢查：每隻眼的殘留與線
    checks = {}
    x0, y0, x1, y1 = eb
    for var in ("eyes_half", "eyes_closed"):
        pc = np.array(Image.open(ROOT / rec["pieces"][var]["file"]).convert("RGBA")).astype(np.float32)
        comp = a.copy().astype(np.float32)
        al = pc[..., 3:4] / 255
        comp[y0:y1, x0:x1, :3] = comp[y0:y1, x0:x1, :3] * (1 - al) + pc[..., :3] * al
        Lc = BF.lum(comp[..., :3])
        dc = np.abs(comp[..., :3] - skin_e).sum(-1)
        per = []
        for i, (fill, core, ell) in enumerate(regions):
            # 原本的眼白、眼珠（core）中，換片後仍「明顯不是皮膚」且不是新線的比例
            line_m = np.zeros((H, W), bool)
            drawn = pieces[var][1][..., 3] > 20
            line_m[y0:y1, x0:x1] = ndimage.binary_dilation(drawn, iterations=2)
            # 半閉時下半眼是刻意保留的，只算上半
            if var == "eyes_half":
                c = eyes_c[i]
                uc, hw_, v0, hh, uv, ys, xs = lid_geom(core, c, tilt)
                upper = np.zeros((H, W), bool)
                sel = uv[1] < v0 + HALF_V * hh - 1
                upper[ys[sel], xs[sel]] = True
                region = upper & ~line_m
            else:
                region = core & ~line_m
            remain = region & ((dc > 60) | (Lc < 150))
            ratio = float(remain.sum() / max(region.sum(), 1))
            line_px = int((ell & line_m & (Lc < 110)).sum())
            per.append({"eye": "左（畫面左）" if i == 0 else "右（畫面右）", "core_px": int(core.sum()),
                        "checked_px": int(region.sum()), "remain_px": int(remain.sum()), "remain_ratio": round(ratio, 4),
                        "lid_line_dark_px": line_px})
            if ratio > 0.03 or line_px < 40:
                raise SystemExit(f"{name}{prefix} {var} 第 {i} 隻眼沒閉好：殘留 {ratio:.3f}、線 {line_px} px")
        checks[var] = per
    return rec, checks, a


def main():
    crop = json.loads((ART / "kids_crop.json").read_text())
    jobs = []
    for n in ("xiaoqing", "xiaoyu"):
        cfg = BF.shift_cfg(BF.CHARS[n], crop[BF.CHARS[n]["head"].name]["offset_from_source"])
        jobs.append((n, "reach" if n == "xiaoqing" else "stepback", cfg, "", {"eyes_half": "v02", "eyes_closed": "v03"}))
    xq = json.loads((ART / "xq_v05_face_cfg.json").read_text())
    for k, c in xq.items():
        cfg = dict(c)
        cfg["head"] = FIN / f"chr-xiaoqing_pose-{k}_v05.png"
        cfg["eyes"] = [tuple(e) for e in cfg["eyes"]]
        cfg["eyes_box"] = tuple(cfg["eyes_box"])
        jobs.append(("xiaoqing", k, cfg, f"{k}-", {"eyes_half": "v02", "eyes_closed": "v02"}))
    report, sheets = {}, {}
    for name, pose, cfg, prefix, ver in jobs:
        out_dir = BF.FACE_DIR / name
        rec, checks, head = build_eyes(name, cfg, prefix, ver, out_dir)
        report[f"{name}-{pose}"] = checks
        sheets[f"{name}-{pose}"] = (name, pose, cfg, prefix, rec, head)
        print(name, pose, {v: [(e["remain_ratio"], e["lid_line_dark_px"]) for e in checks[v]] for v in checks})
    write_jsons(sheets)
    (ART / "blink_check_r2.json").write_text(json.dumps({
        "rule": "每張 eyes_half／eyes_closed 換片疊回頭部圖後，兩隻眼分別檢查：remain_ratio＝原本眼白／眼珠像素在換片後仍看得到的比例"
                "（半閉只算上半眼，下半眼是刻意保留）；lid_line_dark_px＝橢圓內新眼皮線的深色像素數。門檻：每隻眼 remain_ratio ≤ 0.03 且線 ≥ 40 px。",
        "closed_style": f"中性閉眼線：近乎平直、略往下彎（closed_curve {CLOSED_CURVE}），不是向上拱的笑眼",
        "results": report}, ensure_ascii=False, indent=1))
    make_sheets(sheets)


def piece_rec(rec, var):
    p = dict(rec["pieces"][var])
    return p


def write_jsons(sheets):
    log = ("v02／v04（G4 修正第 2 輪）：eyes_half、eyes_closed 兩眼都換成同款線（閉眼＝中性閉眼線、半閉＝上半眼改眼皮），"
           "修正第 1 輪遠側眼沒閉（眨單眼）與淡化殘影；嘴巴換片與睜眼原圖不變。檢查：review/G4/art/blink_check_r2.json")
    # 小晴三新姿勢：素材代理格式 face-<姿勢>_v02.json
    for key, (name, pose, cfg, prefix, rec, head) in sheets.items():
        if name == "xiaoqing" and pose in ("watch", "palm", "worried"):
            fd = BF.FACE_DIR / "xiaoqing"
            face = json.loads((fd / f"face-{pose}_v01.json").read_text())
            for var in ("eyes_half", "eyes_closed"):
                face["pieces"][var] = piece_rec(rec, var)
            face["version"] = "v02"
            face["change_log"] = log
            (fd / f"face-{pose}_v02.json").write_text(json.dumps(face, ensure_ascii=False, indent=1))
    # 小宇：face_v03.json（素材代理格式，頭層座標）
    name, pose, cfg, prefix, rec, head = sheets["xiaoyu-stepback"]
    fd = BF.FACE_DIR / "xiaoyu"
    face = json.loads((fd / "face_v02.json").read_text())
    kh = json.loads((ART / "kid_heads.json").read_text())["xiaoyu"]
    ox, oy = kh["head_offset_px"]
    for var in ("eyes_half", "eyes_closed"):
        p = piece_rec(rec, var)
        p["anchor_px_pose_image"] = list(p["anchor_px"])
        p["anchor_px"] = [p["anchor_px"][0] - ox, p["anchor_px"][1] - oy]
        face["pieces"][var] = p
    face["version"] = "v03"
    face["change_log"] = log
    (fd / "face_v03.json").write_text(json.dumps(face, ensure_ascii=False, indent=1))
    # 小晴 reach 的檔案紀錄另寫一份（素材代理格式，id face/xiaoqing/face-reach；引擎不讀，只是登記換片檔名）
    name, pose, cfg, prefix, rec, head = sheets["xiaoqing-reach"]
    fd = BF.FACE_DIR / "xiaoqing"
    v2 = json.loads((fd / "face_v02.json").read_text())
    kh = json.loads((ART / "kid_heads.json").read_text())["xiaoqing"]
    ox, oy = kh["head_offset_px"]
    for var in ("eyes_half", "eyes_closed"):
        p = piece_rec(rec, var)
        p["anchor_px_pose_image"] = list(p["anchor_px"])
        p["anchor_px"] = [p["anchor_px"][0] - ox, p["anchor_px"][1] - oy]
        v2["pieces"][var] = p
    # 小晴原生合併版 face_v04.json：換片 id 不含版本號，內容同 v03；只更新版本與紀錄
    v3 = json.loads((fd / "face_v03.json").read_text())
    v3["version"] = "v04"
    v3["change_log"] = log + "。各姿勢眼睛換片檔：reach＝chr-xiaoqing_eyes_half_v02／eyes_closed_v03；watch／palm／worried＝chr-xiaoqing_<姿勢>-eyes_half_v02／eyes_closed_v02（見 face-<姿勢>_v02.json）。"
    v3["format_note"] = v3["format_note"].replace("face-<姿勢>_v01.json", "face-<姿勢>_v02.json")
    v3["reach_pieces"] = {k: {"file": v["file"], "image_id": v["image_id"]} for k, v in v2["pieces"].items()}
    (fd / "face_v04.json").write_text(json.dumps(v3, ensure_ascii=False, indent=1))


def make_sheets(sheets):
    f = ImageFont.truetype(BF.FONT, 22, index=10)
    fs = ImageFont.truetype(BF.FONT, 16, index=10)

    def tile(head, rec, var, cfg, K=3, mouth=None):
        im = Image.fromarray(head.copy(), "RGBA")
        if var != "eyes_open":
            p = rec["pieces"][var]
            pc = Image.open(ROOT / p["file"]).convert("RGBA")
            im.alpha_composite(pc, tuple(p["anchor_px"]))
        bg = Image.new("RGBA", im.size, (214, 206, 190, 255))
        bg.alpha_composite(im)
        x0, y0, x1, y1 = cfg["eyes_box"]
        big = bg.crop((x0 - 8, y0 - 8, x1 + 8, y1 + 8))
        big = big.resize((big.width * K, big.height * K), Image.LANCZOS)
        s = cfg["stage_scale"]
        hx0, hy0, hx1, hy1 = x0 - 120, y0 - 150, x1 + 120, y1 + 200
        st = bg.crop((hx0, hy0, hx1, hy1))
        st = st.resize((int(st.width * s), int(st.height * s)), Image.LANCZOS)
        st = st.resize((st.width * 2, st.height * 2), Image.NEAREST)
        return big.convert("RGB"), st.convert("RGB")

    def sheet(keys, path, title):
        rows = []
        for k in keys:
            name, pose, cfg, prefix, rec, head = sheets[k]
            tiles = [(v, *tile(head, rec, v, cfg)) for v in ("eyes_open", "eyes_half", "eyes_closed")]
            rows.append((k, tiles))
        Wt = 40 + max(sum(b.width + 16 for _, b, _ in t) + sum(s.width + 12 for _, _, s in t) for _, t in rows)
        Ht = 70 + sum(40 + max(max(b.height, s.height) for _, b, s in t) + 30 for _, t in rows)
        S = Image.new("RGB", (Wt, Ht), (46, 44, 42))
        d = ImageDraw.Draw(S)
        d.text((20, 16), title, font=f, fill=(240, 240, 240))
        y = 64
        for k, t in rows:
            d.text((20, y), f"{k}　左三格＝眼睛放大 ×3（睜眼原圖｜半閉｜閉眼），右三格＝舞台尺寸（×stage_scale 再放大 2 倍）", font=fs, fill=(240, 210, 120))
            y += 26
            x = 20
            for v, b, s in t:
                S.paste(b, (x, y))
                tw = d.textlength(v, font=fs)
                d.rectangle([x, y, x + tw + 10, y + 22], fill=(240, 236, 226))
                d.text((x + 5, y + 2), v, font=fs, fill=(20, 20, 20))
                x += b.width + 16
            for v, b, s in t:
                S.paste(s, (x, y))
                x += s.width + 12
            y += max(max(b.height, s.height) for _, b, s in t) + 30
        S.save(path)

    sheet(["xiaoqing-watch", "xiaoqing-palm", "xiaoqing-worried"], ART / "face_sheet_xq_v06.png",
          "G4 修正第 2 輪：小晴 watch／palm／worried 的眼睛換片——半閉、閉眼都是兩眼同步（中性閉眼線，不是笑眼、不是單眼）")
    sheet(["xiaoqing-reach", "xiaoyu-stepback"], ART / "face_sheet_v06.png",
          "G4 修正第 2 輪：小晴 reach、小宇的眼睛換片——兩眼都是閉眼線（不再有淡化殘影）")
    # 全部合在一張（給驗收快速看）
    sheet(list(sheets), ART / "blink_zoom_r2.png", "G4 修正第 2 輪：所有孩子眼睛換片（睜｜半閉｜閉），兩眼同步")


if __name__ == "__main__":
    main()
