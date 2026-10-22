# G5 修正第 1 輪｜短音效（佔位檔換正式）｜ASSETS.md 待合併列（主線合併）

放在 ASSETS.md「配樂與音效」表下面（同欄位）。原檔名原地覆寫 audio/sfx/_placeholders.txt 列的四個佔位檔（之前是 1.3 秒紙張摩擦的複本），做完已清空 _placeholders.txt。
重建：`caffeinate -i tools/.venv/bin/python tools/music/build_all.py --only sfx_gust,sfx_phone_noanswer,sfx_truck_arrive,sfx_crowd_short`；
量測：review/G5/audio/metrics.json（44 檔，其他 40 檔數值不變）；圖：review/G5/audio/waveforms_sfx.png。規格照 G3／G5：樣本峰值、最大瞬間響度個別上限（sfx.py SFX_LEVEL）、真峰值 ≤ −2 dBTP、起音 ≥ 5 ms、6 kHz 以上能量很低、沒有突發巨響。聽感全部未驗證（Claude 聽不到音訊）。

| 檔名 | 類型 | 角色／場景 | 部件 | 使用 cue | 來源 | 授權 | 檢視結果 | 版本 |
|---|---|---|---|---|---|---|---|---|
| audio/sfx/sfx_gust_v01.wav | 音效（2.6 s，單聲道） | 廣場、校門口 | S17 一陣風（1.0 s 最強、最後 0.6 s 退去；不呼嘯、低通 4.5 kHz） | 目前沒有 cue 使用（各幕可用） | 自製（程式合成）；tools/music/sfx.py | 原創 | 最大瞬間 -28.0 LUFS、峰值 -17.0 dBFS、-17.0 dBTP；起音 558.6 ms；100 ms 最大跳升 10.4 dB；聽感未驗證 | v01（G5 修正第 1 輪原地覆寫佔位） |
| audio/sfx/sfx_phone_noanswer_v01.wav | 音效（2.6 s，單聲道） | 求助站（葉護理師打電話） | S18 撥號沒人接（兩聲柔和鈴 520／650 Hz＋14 Hz 顫音，0.05／1.35 s 各 0.8 s；電話線音色；不用真實電信業者的回鈴音、撥號音、忙線音） | a2_c012 | 自製（程式合成）；tools/music/sfx.py | 原創 | 最大瞬間 -28.0 LUFS、峰值 -19.4 dBFS、-19.4 dBTP；起音 17.8 ms；100 ms 最大跳升 21.4 dB（從靜音到 -28 LUFS 的輕鈴）；聽感未驗證 | v01（G5 修正第 1 輪原地覆寫佔位） |
| audio/sfx/sfx_truck_arrive_v01.wav | 音效（5.0 s，單聲道） | 校門口（阿樂叔叔的小貨車） | S19 小貨車輕聲開近、停下、怠速（0–3.0 s 開近、3.0–3.6 s 停、3.6–5.0 s 怠速；不按喇叭、沒有煞車尖響） | a4_c001 | 自製（程式合成）；tools/music/sfx.py | 原創 | 最大瞬間 -27.0 LUFS、峰值 -17.1 dBFS、-17.1 dBTP；起音 1509.7 ms；100 ms 最大跳升 3.5 dB；聽感未驗證 | v01（G5 修正第 1 輪原地覆寫佔位） |
| audio/sfx/sfx_crowd_short_v01.wav | 音效（4.0 s，單聲道） | 廣場 | S20 廣場人聲短版（約 10 個聲音只有母音、低通 2.2 kHz、殘響推遠，聽不出任何字；0.6 s 淡入、最後 0.8 s 淡出） | a2_c012 | 自製（程式合成）；tools/music/sfx.py | 原創 | 最大瞬間 -30.0 LUFS、峰值 -18.8 dBFS、-18.8 dBTP；起音 645.4 ms；100 ms 最大跳升 5.3 dB；聽感未驗證 | v01（G5 修正第 1 輪原地覆寫佔位） |
