# G3 補充驗收：授權證據（主線整理，2026-10-21 08:05）

回應兩位驗收代理提出的嚴重問題「素材授權不明」（review/G3/el/qa/）。

## 1. ElevenLabs（Starter 付費方案）

- **帳號是付費方案**：使用者 2026-10-21 06:30 升級成 Starter。升級前，聲線庫聲線全部回 402「Free users cannot use library voices via the API」（audio/vo/elevenlabs_usage.jsonl，03:19）。升級後，同一把金鑰呼叫 Juin 回 200（06:3x），library 代理呼叫 253 次全部成功，其中 17 個 `free_users_allowed=false` 的聲線也都成功（review/G3/el/library/INDEX.md）。
- **官方條款**（ElevenLabs 說明中心〈Can I publish the content I generate on the platform?〉，2026-10-21 查閱）：
  - 原文：「All paid plans include a commercial license, provided you're not using Beta Services.」
  - 付費期間產生的內容「can be used commercially and indefinitely, subject to the Service-Specific Terms」。
  - 免費方案沒有商用授權，公開時必須在標題標註 elevenlabs.io。
  - 來源：https://elevenlabs.io/docs/help-center/legal/can-i-publish-the-content-i-generate-on-the-platform/llms.txt
- **聲線庫聲線**（ElevenLabs〈ElevenLabs Voices: A comprehensive guide〉，2026-10-21 查閱）：
  - 原文：「All voices in the Voice Library come with a free commercial use license.」
  - 來源：https://elevenlabs.io/elevenlabs-voices-a-comprehensive-guide
- **不是 Beta 服務**：官方模型頁把 eleven_v3 和 eleven_multilingual_v2 都寫成「previous generation」模型，沒有 alpha、beta 或 preview 標示。
  - 來源：https://elevenlabs.io/docs/overview/models
- **使用範圍**：本案是學校課堂、非營利；商用授權涵蓋的範圍更大。

## 2. edge-tts（維持 edge 的 8 個角色）

- **授權狀態已知**：edge-tts 是社群開發的非官方工具，呼叫 Edge 的線上朗讀服務；微軟沒有明確授權這種用途。這是已知、已記錄的風險，不是來源不明的素材。
- **核准過的規劃書寫明這條路**：`反毒剪紙劇場_課程與製作規劃_v1.3.md` 第 213–226 行：
  - 「Azure Speech 金鑰：正式授權的配音，聲線和 edge-tts 相同。」
  - 「都沒有時：用 edge-tts 製作，並記錄授權風險。」
  - 配音列：「有 Azure 金鑰就用 Azure，否則用 edge-tts（非官方，條款沒有明確授權，已記錄；同樣的聲線，之後可一鍵改用 Azure 重新合成）」。
  - v1.3 是使用者核准的版本。
- **已記錄**：ASSETS.md 與 REVIEW.md 記錄了 edge-tts 的風險，以及接受暫用的決定（第 1 輪聲音修正第 13 項）。
- **可以完全移除的退路**：使用者提供 Azure Speech 金鑰（F0 免費層每月 50 萬字元）後，執行 `tools/vo_build.py --service azure` 就能用同名聲線重新合成，句長幾乎不變。主線會在報告中建議使用者申請。

## 3. 主線對 4 個分歧角色與 1 個候選衝突的裁決

規則：兩位意見分歧時，只有在至少一位驗收代理認為 ElevenLabs 的可量測分數「嚴格高於」edge，而且另一位反對的理由已經不成立時，才改用 ElevenLabs。

| 角色 | 配音導演 | 兒童劇場導演 | 裁決 | 理由 |
|---|---|---|---|---|
| 旁白 | edge（EL 11／edge 14） | EL Door v3（14／14 打平） | **edge** | 最佳候選把「電子煙」念錯，兩個轉寫模型都一樣；必要旁白一句尾疑似截斷；v3 每次合成都不同。旁白負責兩句必要旁白，沒有一位認為 EL 嚴格較好。 |
| 林老師 | EL Door v3（15／13） | edge（反對理由：Door 已經給旁白） | **ElevenLabs Door v3** | 旁白保留 edge，反對理由不成立。edge 版兩個轉寫模型都把「小宇」念成「小玉」，而且林老師和邀請者、旁白都用同一個底聲。 |
| 小晴 | edge（11／12） | EL Tiffy（12／12 打平） | **edge** | 沒有一位認為 EL 嚴格較好。Tiffy v3 只測了 2 句；同一聲線用 v2 念「紙燈節」被轉成「只等街」；和折折的音高差從 0.95 半音縮小到 0.64 半音。 |
| 陳伯伯 | edge（12／15） | EL Neil v3（14／14 打平） | **edge** | 沒有一位認為 EL 嚴格較好。 |
| 執勤人員 | EL Angel v3（12／11） | EL Ling v3（13／12） | **ElevenLabs Angel v3** | 兩位都選 EL。Ling v3 把 a5_c006_05「做得很好」的「做」念錯，兩個模型都轉成「瘦／繡」。Angel v3 的兩句都正確，和小宇的音高差 3.9 半音（Ling 只有 0.4 半音）。工作流按總分自動選了 Ling，但兩位的總分出自不同評分者，不能直接相加比較，所以由主線改判。 |
| 葉護理師 | EL Devon v3 | EL Devon v3 | **ElevenLabs Devon v3** | 兩位一致。 |

其餘 5 個角色（折折、小宇、阿樂叔叔、品安、邀請者）兩位都選 edge。

## 4. 採用 ElevenLabs v3 的條件（正式算檔時強制）

1. **逐句自動檢查，不過就重算**：兩個轉寫模型都不能出現非同音差異；句尾最後 60 ms 不能有聲（v3 句尾截斷的問題，見 qa/配音導演/tail_voicing.json）；語速和停頓要在角色目標內。
2. **重算上限**：每句最多重算 6 次。仍不過的話，整個角色退回 edge，不在同一角色內混用兩種引擎。
3. **停頓**：多句台詞用分段合成並插入停頓，做法同必要旁白一，例如葉護理師「不是喔。你們找大人…」。
4. **執勤人員**：沿用 edge 版的電話音色處理。
5. **資產紀錄**：ASSETS.md 逐檔記錄 voice_id、模型、seed、request_id 與計費。

## 5. 獨立重驗結果與主線最終裁決（2026-10-21 08:05）

使用者 2026-10-21 08:0x 已向 ElevenLabs 申請教育用途豁免（18 歲條款），等待回覆。

### 重驗代理的判定

重驗代理（新代理）逐字核對了證據檔的三段引文，都相符。條款原文存在 scratchpad/el_terms/。判定：

- **(a) ElevenLabs：嚴重問題成立。**
  - ElevenLabs 禁止用途政策（https://elevenlabs.io/use-policy，2026-10-09 更新）「Use by and for Minors」一節：「Apps, products, or experiences directed at individuals under 18 are prohibited unless we have assessed and approved them in writing.」
  - 本劇是給 8–10 歲兒童看的，專案沒有這份書面核准。
  - 這條和商用授權無關，第 1 節的商用引文解決不了。
  - 主線已用 WebFetch 自行核對原文。政策沒有教育用途的例外，也沒寫申請核准的管道。
- **(b) edge-tts：嚴重問題不成立。** 已知、已核准（v1.3）、已記錄的風險。附帶三個條件：
  1. ASSETS.md 補註：依 v1.3 第 0、6 節，v1.2 第 20.2 節「不放進正式交付包」不再適用。
  2. 只用於離線演出與彩排，不另外散布音檔；總報告要列出這項風險，並建議改用 Azure 重建。
  3. REVIEW.md 寫明童聲維持 edge 的理由：ElevenLabs 聲線設計擋掉兒童描述、聲線庫沒有童聲、加上上述政策限制。

### 主線最終裁決

- **全部 11 個角色的正式配音維持 edge-tts**（依第 4 節第 2 條的退路）。
- 驗收選出的 Devon（葉護理師）、Door（林老師）、Angel（執勤人員）只寫進 casting.json 的 `alt.elevenlabs` 當備案，等驗收工作流結束後再寫入。
- 使用者若取得 ElevenLabs 書面核准，再用這 3 個備案重建，並依重驗代理列的條件逐檔記錄：核准信件、訂閱方案、voice_id、模型、seed、request_id、預告期。
- **本專案不再呼叫 ElevenLabs**。目前沒有任何正式檔案用到 ElevenLabs 的輸出（G4 計費 0）。
- (b) 的三個條件在 G3/G4 驗收工作流結束後寫進 ASSETS.md／REVIEW.md（那兩個檔案目前由修正代理使用中）。

## 6. 使用者指示（2026-10-21 08:1x）

- 使用者表示用 ElevenLabs 應該會比較好，並指示「先做再說」：人在外面，暫時無法轉交 ElevenLabs 的回覆。
- 主線執行方式：
  - 製作全劇 ElevenLabs 版（工作流 wf_42597e72-70b），逐句自動檢查、重算，再由驗收代理逐角色和 edge 版比較；ElevenLabs 版沒有客觀缺陷就採用。
  - edge 全劇版同時保留成可一鍵切換的備案。
  - G7 總報告列為待確認事項：「ElevenLabs 18 歲條款書面核准待補；未獲核准時，演出前改用 edge 版」。
  - 核准信件取得後，記進 ASSETS.md。

## 7. 全劇版進度與主線對第 4 節第 2 條的修訂（2026-10-21 12:45）

- 全劇版工作流（wf_42597e72-70b）的工具代理完成；兩組製作代理在 11:4x 撞到用量上限前已做出 193 句：通過 167、未通過 24、未完成 2，計費 6,386 點（audio/vo_el/ledger.json）。報告與驗收代理沒有跑到。
- **同一套自動檢查套在 edge 全劇基準上，edge 每個角色的未通過句都比 EL 多**（例如旁白 edge 轉寫不過 15 句、EL 4 句；小晴 edge 語速不過 16 句、EL 0 句；review/G3/el/full/edge/metrics.json 對 audio/vo_el/build_report_el.json）。
- 所以第 4 節第 2 條「同一角色有一句重算 6 次仍不過，整個角色退回 edge」改為：
  1. 逐句比較 EL 與 edge 在同一套檢查下的缺陷。EL 有、edge 沒有的缺陷，才算 EL 的客觀缺陷。
  2. 只有一個轉寫模型出現、另一個模型逐字正確的差異，記為「轉寫模型分歧」，不算客觀缺陷（G3 驗收對 edge 版也是這樣處理，見 REVIEW.md 第 1 輪）。
  3. 兩個模型都錯、念錯檢查詞或必要旁白、句尾截斷：一律要重算到通過。仍不過時由驗收代理決定該角色用 EL 或 edge，同一角色仍不混用兩種引擎。
- 主線第 2 輪重算 8 句（關鍵詞「喪屍煙彈」、句首字被吞、語速過快與 2 句未完成），逐句設定寫在 audio/vo_el/casting/*.json 的 lines.<編號>._note。

## 8. 使用者決定（2026-10-21 13:2x）
- 使用者聽完全劇後指示：「全部都改成ElevenLabs版本 不要用edge-tts」。記為 DECISIONS.md D-G3-07。
- 取代第 5 節「全部 11 個角色維持 edge-tts」與第 6 節的 edge 一鍵備案；edge 檔只封存、不打包。
- 兒童用途書面核准仍待 ElevenLabs 回覆；取得後把核准信件記進 ASSETS.md，G7 總報告照列。
