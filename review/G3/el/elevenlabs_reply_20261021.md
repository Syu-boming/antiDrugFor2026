# ElevenLabs 回覆：未滿 18 歲對象的使用（2026-10-21）

- 來源：使用者 2026-10-21 下午收到的電子郵件，使用者把內文貼給主線（以下為原文照錄）。原始郵件（含寄件地址、日期）由使用者保存；建議另存 PDF 或轉寄留底，並確認寄件人網域為 elevenlabs.io。
- 背景：ElevenLabs 禁止用途政策（https://elevenlabs.io/use-policy，2026-10-09）「Use by and for Minors」：給未滿 18 歲對象的產品須經 ElevenLabs 評估並書面核准。使用者 2026-10-21 上午以教育用途申請（review/G3/el/license_evidence.md 第 5 節）。

## 郵件原文

> Dear Syu Boming,
> I hope this email finds you well.
> I am writing to provide clarification regarding the compliance and guidelines for using ElevenLabs text-to-speech technology with children under the age of 18.
> Under ElevenLabs’ terms of service and safety guidelines, the use of AI voice technology for individuals under 18 years of age is permitted, provided that it strictly serves educational purposes and is conducted under proper supervision.
> To ensure full compliance, please keep the following key points in mind:
> Educational Purpose: The AI-generated voices and audio content must be used exclusively for teaching, learning, language practice, or school-related project activities.
> Consent & Supervision: When working with minors, proper institutional oversight and, where applicable, parental or guardian consent should be maintained in accordance with school policies and local privacy regulations.
> Safety & Ethics: Voice cloning of minors is subject to high privacy and safety protection standards. Pre-made, standard library voices or official educational accounts should be prioritized for student-facing projects.
> Please let me know if you need any further documentation, sample consent forms, or assistance in setting up the educational workflow.
> Best regards,

## 本專案對照（主線）

| 郵件條件 | 本專案做法 | 符合 |
|---|---|---|
| 只用於教學、學習或學校專題 | 國小三、四年級反毒課程，一節 40 分鐘校內演出；只用於離線演出與彩排，不另外散布音檔 | 是 |
| 適當的機構監督；依學校規定與當地隱私法規取得家長同意（如適用） | 教師全程操作；學生只觀看、比手勢作答，不錄學生聲音、不蒐集姓名或使用紀錄，程式不用攝影機與麥克風（CLAUDE.md 第 11 條）。課程規劃已安排課前知會學務處與輔導室（v1.2 第 8.4、9.1 節），建議一併說明配音使用 AI 聲線庫 | 是（依校規知會） |
| 未成年人聲音複製須高度保護；學生用專案優先用聲線庫標準聲線 | 11 個角色全部是 ElevenLabs 聲線庫聲線，沒有任何聲音複製（含未成年人） | 是 |

## 判讀
- 這是 ElevenLabs 對使用者申請的書面回覆，明確寫出「教育用途且有適當監督時允許用於未滿 18 歲對象」，本專案三項條件都符合，主線據此把「兒童用途書面核准」由「待回覆」改為「已取得書面確認」。
- 郵件是通則式說明，沒有點名本作品；如需更明確的紀錄，可回信請 ElevenLabs 確認本課堂劇場專案（選擇性，不影響目前判讀）。
