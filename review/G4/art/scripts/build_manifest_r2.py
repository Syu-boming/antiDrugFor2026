"""G4 修正第 2 輪（美術）：更新 assets/final/g4_manifest.json（就地更新；git 有紀錄）。

- version v05 → v06；新增 round2_art 區塊
- assets[] 的 tex-string-ring 改指 v02（米白紙環）
- string_render：紙環說明、預覽圖、量測檔
用法：/opt/anaconda3/bin/python3 review/G4/art/scripts/build_manifest_r2.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
MAN = ROOT / "assets/final/g4_manifest.json"


def main():
    m = json.loads(MAN.read_text())
    m["version"] = "v06"
    m["date"] = "2026-10-21"
    for a in m["assets"]:
        if a["id"] == "tex-string-ring":
            a["file"] = "assets/final/tex-string-ring_v02.png"
            a["notes"] = ("紙環貼圖 v02（G4 修正第 2 輪）：米白紙環（紙面 sRGB≈(251,242,222)、色相約 41°、彩度約 12%，整片同色、沒有放射漸層或高光）"
                          "＋細纖維紙紋＋左下紙帶接口細線；外緣、內緣暖深棕描邊；整個環往右下偏移 (5,6) px 的暖棕厚紙側邊當單側陰影"
                          "（alphaTest 0.5，所以用不透明色）。外半徑 0.88、孔半徑 0.42（貼圖半寬為 1）。正方形平面、直徑 0.103 世界單位、正對鏡頭、不隨肢體旋轉"
                          "（陰影方向因此固定在右下）。v01 灰環保留不刪。")
    sr = m["string_render"]
    sr["ring"] = ("tex-string-ring v02：米白紙環＋紙紋＋右下單側厚紙陰影；環身亮度在 light 1.0 時 luma≈242、light 0.92 時仍 ≥220。"
                  "strings.ts 的 ringMat.color.setScalar(light) 會把貼圖乘暗，light 低於 0.91 時環身會低於 220。")
    prev = sr.get("preview", [])
    for p in ("review/G4/art/ring_crops_v02_preview.png",):
        if p not in prev:
            prev.append(p)
    sr["preview"] = prev
    sr["ring_stats"] = "review/G4/art/ring_tex_v02.json（貼圖紙面、v01 擷取環身、v02 示意環身的亮度與色相）；引擎重擷取後跑 make_ring_tex_v02.py --measure <擷取資料夾>"
    m["round2_art"] = {
        "date": "2026-10-21",
        "items": {
            "1/5/9 兩眼同閉": ("小晴 reach＝face/xiaoqing/chr-xiaoqing_eyes_half v02、eyes_closed v03；小晴 watch／palm／worried＝chr-xiaoqing_<姿勢>-eyes_half v02、"
                              "eyes_closed v02；小宇＝chr-xiaoyu_eyes_half v02、eyes_closed v03。兩隻眼都換成同款線（閉眼＝近乎平直、略往下彎的中性閉眼線；"
                              "半閉＝上半眼改眼皮），同一張換片蓋兩眼，所以一換片就是兩眼同時閉、同時開。圖像 id 不含版本號，打包自動換用，"
                              "face JSON 的 shapes 不必改。檢查：review/G4/art/blink_check_r2.json、face_sheet_xq_v06.png、face_sheet_v06.png、blink_zoom_r2.png"),
            "face JSON": "face/xiaoqing/face＝face_v04.json（原生 FaceConfig，perPose 內容與 v03 相同，只更新版本與紀錄）；face/xiaoyu/face＝face_v03.json；face-<姿勢>_v02.json（只登記檔名）",
            "8 紙環": "tex-string-ring v02（見 assets[] 與 string_render.ring）",
        },
        "engine_notes": [
            "眨眼與翻面錯開（問題 10）、線的下垂弧（問題 6）、站起與扶桌（問題 7）、a2_c004 小動作（問題 12）是引擎的部分，素材沒有變更。",
            "引擎重擷取 g4_playback.mp4 與 ring_crops.png 後，才能做問題 8、9 的正式驗證（本輪美術只附示意與素材層級的量測）。",
            "strings.ts 的退路紙環 ringTexture()（素材缺圖時）仍是灰環；正式包有 v02 素材不會用到，若要一致可改成米白（#FBF2DE 紙面、#4A3426 描邊）。",
        ],
    }
    MAN.write_text(json.dumps(m, ensure_ascii=False, indent=1))
    print("manifest", m["version"], [a["file"] for a in m["assets"] if a["id"] == "tex-string-ring"])


if __name__ == "__main__":
    main()
