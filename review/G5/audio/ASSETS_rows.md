# G5 配樂與音效｜ASSETS.md 待合併列（主線合併）

放在 ASSETS.md「配樂與音效」表下面（同欄位）。重建：`caffeinate -i tools/.venv/bin/python tools/music/build_all.py`；量測：review/G5/audio/metrics.json；對點：review/G5/audio/CUES.md；圖：review/G5/audio/waveforms_music.png、waveforms_sfx.png。聽感全部未驗證。

| 檔名 | 類型 | 角色／場景 | 部件 | 使用 cue | 來源 | 授權 | 檢視結果 | 版本 |
|---|---|---|---|---|---|---|---|---|
| audio/music/music_zhezhe_v02.wav | 配樂（無縫循環 16.0 s） | 折折 | M2 折折動機（短句 0–4 s＋循環底） | a0_c002、a0_c004、a3_c001、a7_c001 | 自製（程式作曲）＋FluidR3_GM 音色庫（MIT）；tools/music/compose.py | 原創；音色庫 MIT（audio/LICENSES/FluidR3_GM_copyright.txt） | -24.0 LUFS、-6.6 dBTP；100 ms 最大跳升 5.7 dB；接縫樣本差 42 LSB；聽感未驗證 | v02（G5 正式版；v01 主線佔位保留） |
| audio/music/music_shiny_v02.wav | 配樂（無縫循環 15.0 s） | 閃亮盒子 | M3 閃亮動機（音樂盒圓舞曲、增三和弦；最低音 C4、高通 200 Hz） | a1_c002–a1_c003、a2_c003、a2_c013、a3_c001 | 自製（程式作曲）＋FluidR3_GM 音色庫（MIT）；tools/music/compose.py | 原創；音色庫 MIT（audio/LICENSES/FluidR3_GM_copyright.txt） | -24.0 LUFS、-11.1 dBTP；100 ms 最大跳升 3.5 dB；接縫樣本差 125 LSB；聽感未驗證 | v02（G5 正式版；v01 主線佔位保留） |
| audio/music/music_road_v02.wav | 配樂（無縫循環 20.0 s） | 紙上的路 | M5（木塊 3+3+2，不是時鐘滴答、不像警報） | a4_c002、a4_c003、a4_c008 | 自製（程式作曲）＋FluidR3_GM 音色庫（MIT）；tools/music/compose.py | 原創；音色庫 MIT（audio/LICENSES/FluidR3_GM_copyright.txt） | -24.0 LUFS、-10.6 dBTP；100 ms 最大跳升 3.0 dB；接縫樣本差 42 LSB；聽感未驗證 | v02（G5 正式版；v01 主線佔位保留） |
| audio/music/music_road_hold_v01.wav | 配樂（無縫循環 16.0 s） | 背光剪影 | M5 長音（加做、可選） | a4_c004 | 自製（程式作曲）＋FluidR3_GM 音色庫（MIT）；tools/music/compose.py | 原創；音色庫 MIT（audio/LICENSES/FluidR3_GM_copyright.txt） | -24.0 LUFS、-13.4 dBTP；100 ms 最大跳升 0.8 dB；接縫樣本差 149 LSB；聽感未驗證 | v01（G5 正式版；加做） |
| audio/music/music_courage_v02.wav | 配樂（無縫循環 30.0 s） | 拒絕、找大人 | M6 勇氣動機（M1 上行變奏） | a1_c004、a2_c012、a3_c002、a3_c004、a4_c012、a5_c005–a5_c007、a6_c006、a7_c002 | 自製（程式作曲）＋FluidR3_GM 音色庫（MIT）；tools/music/compose.py | 原創；音色庫 MIT（audio/LICENSES/FluidR3_GM_copyright.txt） | -24.0 LUFS、-10.6 dBTP；100 ms 最大跳升 5.8 dB；接縫樣本差 26 LSB；聽感未驗證 | v02（G5 正式版；v01 主線佔位保留） |
| audio/music/music_recovery_v02.wav | 配樂（無縫循環 24.0 s＝四季一輪） | 醫院走廊、四季 | M7 復原動機（M1 慢版鋼琴＋弦） | a5_c008、a6_c008、a6_c009 | 自製（程式作曲）＋FluidR3_GM 音色庫（MIT）；tools/music/compose.py | 原創；音色庫 MIT（audio/LICENSES/FluidR3_GM_copyright.txt） | -24.0 LUFS、-11.0 dBTP；100 ms 最大跳升 2.0 dB；接縫樣本差 180 LSB；聽感未驗證 | v02（G5 正式版；v01 主線佔位保留） |
| audio/music/music_town_night_v02.wav | 配樂（無縫循環 30.0 s） | 燈節夜晚廣場 | M1 夜晚版 | a6_c001、a6_c002 | 自製（程式作曲）＋FluidR3_GM 音色庫（MIT）；tools/music/compose.py | 原創；音色庫 MIT（audio/LICENSES/FluidR3_GM_copyright.txt） | -24.0 LUFS、-12.0 dBTP；100 ms 最大跳升 1.9 dB；接縫樣本差 17 LSB；聽感未驗證 | v02（G5 正式版；v01 主線佔位保留） |
| audio/music/music_bows_v02.wav | 配樂（一次播完 18.0 s） | 謝幕 | M1 謝幕版（7 組鞠躬對小節頭 1／3／…／13 s，15.0 s 最後和弦） | a8_c001 | 自製（程式作曲）＋FluidR3_GM 音色庫（MIT）；tools/music/compose.py | 原創；音色庫 MIT（audio/LICENSES/FluidR3_GM_copyright.txt） | -20.0 LUFS、-7.6 dBTP；100 ms 最大跳升 4.2 dB；檔尾 10 ms 峰值 -90.3 dBFS；聽感未驗證 | v02（G5 正式版；v01 主線佔位保留） |
| audio/sfx/sfx_windchime_v01.wav | 音效（4.2 s，單聲道） | 燈籠店門 | S6 風鈴 | a0_c004 | 自製（程式合成）；tools/music/sfx.py | 原創 | 最大瞬間 -24.0 LUFS、峰值 -14.9 dBFS、-14.9 dBTP；起音 97.6 ms；聽感未驗證 | v01（G5 原地覆寫紙張摩擦佔位） |
| audio/sfx/sfx_bamboo_drop_v01.wav | 音效（1.0 s，單聲道） | 窗內剪影 | S7 竹篾輕落地 | a1_c008 | 自製（程式合成）；tools/music/sfx.py | 原創 | 最大瞬間 -28.0 LUFS、峰值 -12.0 dBFS、-12.0 dBTP；起音 6.0 ms；聽感未驗證 | v01（G5 原地覆寫紙張摩擦佔位） |
| audio/sfx/sfx_wind_v01.wav | 音效（30.0 s，單聲道） | 廣場、校門口 | S8 風聲（無縫循環 30.0 s，3.0 s 一陣風） | a1_c008、a5_c001、a5_c005 | 自製（程式合成）；tools/music/sfx.py | 原創 | 整合 -30.0 LUFS、峰值 -14.0 dBFS、-14.0 dBTP；接縫樣本差 12 LSB；聽感未驗證 | v01（G5 原地覆寫紙張摩擦佔位） |
| audio/sfx/sfx_school_bell_v01.wav | 音效（7.0 s，單聲道） | 教室 | S9 下課鐘（柔；西敏寺鐘聲前兩句，公有領域旋律） | a3_c008 | 自製（程式合成）；tools/music/sfx.py | 原創 | 最大瞬間 -24.0 LUFS、峰值 -14.1 dBFS、-14.1 dBTP；起音 605.3 ms；聽感未驗證 | v01（G5 原地覆寫紙張摩擦佔位） |
| audio/sfx/sfx_gate_ambience_v01.wav | 音效（40.0 s，單聲道） | 校門口 | S10 校門口環境聲（無縫循環 40.0 s；人聲只有母音、聽不出字） | a3_c003、a4_c001、a4_c008 | 自製（程式合成）；tools/music/sfx.py | 原創 | 整合 -36.0 LUFS、峰值 -19.6 dBFS、-19.6 dBTP；接縫樣本差 4 LSB；聽感未驗證 | v01（G5 原地覆寫紙張摩擦佔位） |
| audio/sfx/sfx_watch_dial_v01.wav | 音效（2.2 s，單聲道） | 校門口 | S11 兒童手錶撥號音（輕；不是 DTMF） | a5_c005／a5_c006 | 自製（程式合成）；tools/music/sfx.py | 原創 | 最大瞬間 -28.0 LUFS、峰值 -18.2 dBFS、-18.2 dBTP；起音 6.2 ms；聽感未驗證 | v01（G5 原地覆寫紙張摩擦佔位） |
| audio/sfx/sfx_phone_bed_v01.wav | 音效（40.0 s，單聲道） | 119 通話 | S12 電話音色底音（無縫循環 40.0 s；沒有電信撥號／回鈴音） | a5_c006 | 自製（程式合成）；tools/music/sfx.py | 原創 | 整合 -38.0 LUFS、峰值 -24.5 dBFS、-24.5 dBTP；接縫樣本差 7 LSB；聽感未驗證 | v01（G5 原地覆寫紙張摩擦佔位） |
| audio/sfx/sfx_ambulance_engine_v01.wav | 音效（16.0 s，單聲道） | 校門口 | S13 救護車引擎聲（無警笛、喇叭、煞車尖響） | a5_c007 | 自製（程式合成）；tools/music/sfx.py | 原創 | 最大瞬間 -24.0 LUFS、峰值 -16.2 dBFS、-16.2 dBTP；起音 5369.9 ms；聽感未驗證 | v01（G5 原地覆寫紙張摩擦佔位） |
| audio/sfx/sfx_plane_whoosh_v01.wav | 音效（1.6 s，單聲道） | 騎樓、校門口 | S14 紙飛機咻聲（輕） | a3_c001、a4_c002 | 自製（程式合成）；tools/music/sfx.py | 原創 | 最大瞬間 -26.0 LUFS、峰值 -15.5 dBFS、-15.5 dBTP；起音 387.0 ms；聽感未驗證 | v01（G5 原地覆寫紙張摩擦佔位） |
| audio/sfx/sfx_crowd_far_v01.wav | 音效（40.0 s，單聲道） | 廣場 | S15 廣場人聲遠景（無縫循環 40.0 s；聽不出字） | a1_c001、a6_c001 | 自製（程式合成）；tools/music/sfx.py | 原創 | 整合 -34.0 LUFS、峰值 -18.4 dBFS、-18.4 dBTP；接縫樣本差 12 LSB；聽感未驗證 | v01（G5 原地覆寫紙張摩擦佔位） |
| audio/sfx/sfx_footsteps_v01.wav | 音效（4.0 s，單聲道） | 通用 | S16 紙偶腳步（8 步、每步 0.5 s） | 走路往右的 cue | 自製（程式合成）；tools/music/sfx.py | 原創 | 最大瞬間 -31.0 LUFS、峰值 -12.0 dBFS、-12.0 dBTP；起音 7.0 ms；聽感未驗證 | v01（G5 原地覆寫紙張摩擦佔位） |

另：`audio/sfx/_placeholders.txt` 已清空（11 個音效與 music_town_night 都有正式檔）。
