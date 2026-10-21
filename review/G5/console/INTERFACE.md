# 簡報筆映射與教師控制台：介面說明（G5 共用元件，2026-10-21）

依據：v1.2 第 19.2、19.4、21 節；v1.3 第 6 節（Electron 可攜版雙視窗為打包首選）。測試：`node tools/console-test.mjs`（含全劇 show 與 Electron，見 `console_test.json`）。

## 1. 檔案

| 檔案 | 內容 |
|---|---|
| `app/src/engine/input.ts` | 按鍵映射（舞台、控制台、按鍵測試頁共用）。原 API 不變；新增 `effectiveKeymap()`、`resolveAction()`、`keyLabel()`、`ACTION_LABEL`、本機加設 `loadKeymapOverrides()`／`saveKeymapOverrides()`（localStorage `antidrug-theater-keymap`，F5／Esc 固定攔截不能改）。`new InputController(onAction)` 不給映射時跟著本機加設，其他視窗改了映射會由 storage 事件即時更新。 |
| `app/src/ui/console-protocol.ts` | 訊息格式、傳輸（Electron IPC → BroadcastChannel → storage 事件）、顯示用純函式（下一步預告、輪區、查核點落差、壓縮建議） |
| `app/src/ui/console-link.ts` → `dist/console-link.js` | 舞台端連結：讀 `window.__engine`（與 G5 引擎的 `window.__engineShow`）、送狀態快照、執行控制台的操作。壓縮級別與查核點到達時間用引擎的；授課時鐘（開幕 00:30 起跳、老師 ±30 秒）存在這裡。狀態來源唯一＝舞台視窗。不畫任何東西在舞台上；`?capture=1` 時不啟動；另每 100 ms 比對 devicePixelRatio，變了就送 resize（main.ts 的 matchMedia 在「只改縮放、視窗大小不變」時不會觸發）。 |
| `app/src/ui/console.ts`、`console.css`、`app/console.html` → `dist/console.html` | 教師控制台（筆電端深色大字） |
| `app/src/ui/console-keytest.ts`、`app/keytest.html` → `dist/keytest.html` | 簡報筆按鍵測試頁（控制台也有同一個面板） |
| `app/console.build.mjs` | 產生上述檔案，並由 `dist/index.html` 產生 `dist/stage.html`（只多一行 `<script src="console-link.js">`，畫面完全相同） |
| `app/electron/main.js`、`preload.js`、`layout.js`、`package.json` | Electron 外殼：延伸顯示 → 舞台全螢幕在投影、控制台在筆電；同步顯示／一個畫面 → 單一舞台視窗；IPC 轉送；允許自動播放；舞台不因失焦降速；擋外部請求；拒絕攝影機麥克風；防止螢幕休眠 |
| `app/electron/pack.mjs` | 組 `resources/app`（＋有 Windows zip 時組可攜版資料夾 `AntidrugTheater/`，執行檔 `AntidrugTheater.exe`）。輸出預設 `app/electron/out/` |
| `tools/console-test.mjs` | Playwright 測試（瀏覽器雙視窗、單一視窗退路、縮放、按鍵測試、Electron） |

## 2. 三種開法

1. **Electron（首選）**：開發時 `<electron> app/electron [--cues=show] [--single] [--windowed] [--query=q=B&lead=200]`；可攜版雙擊 `AntidrugTheater.exe`。cue 集預設依序找 `show`、`g4`、`demo`。控制台按「下一步」在準備畫面＝遠端「準備播放」（可出聲，不必到投影畫面點滑鼠）。
2. **瀏覽器雙視窗（方案 B／E）**：開 `dist/console.html?cues=show`，按「開啟舞台視窗」（有視窗管理權限時自動放到另一個螢幕，否則請拖過去），**在投影畫面上按一次「準備播放」**（瀏覽器規定聲音要在舞台視窗啟用；控制台會提示）。也可以自己另開 `dist/stage.html?cues=show&nofs=1`，控制台自動連上。
3. **單一舞台視窗（退路）**：`dist/index.html` 或 `stage.html`。控制台偵測到同步顯示（`screen.isExtended=false`）時 5 秒後自動改走這條；舞台已開著時只提醒、不開第二個舞台。

## 3. 控制台用到的 cue 欄位（各幕代理與整合代理請填）

| 欄位 | 控制台怎麼用 |
|---|---|
| `title` | 「下一步：播放〈title〉」、跳到選單 |
| `teacherNote` | 講稿重點（目前段落，播放中與停住時都顯示）；下一段的提示顯示在「接下來」 |
| `quiz.answer`、`quiz.number`、`quiz.qid`、`options` | 本題正解與指定區（Q1–Q8 依 `number` 輪 A→B→C→D）；劇情等待時預告下一題。reveal、lamp 沒寫 `quiz` 時沿用前一個 quiz |
| `lamp` | 「下一步：點燈（第 N 盞）」 |
| `checkpoint {label, atMinute, escalate}` | 到達時間用引擎的紀錄（`__engineShow.checkpoints()`：離開該 cue 時，沒離開則播完時），換算成授課時鐘（從老師上台起算，開幕 00:30 起跳）顯示落差；引擎還沒開演（直接用跳到選單）或舊版引擎時由連結在播完時自己記。`escalate {behindSec, level}` 是壓縮建議門檻（沒寫才用內建表）。第一個 cue 與 `atMinute ≤ 0` 不計 |
| `compression` | 「本段：0／1／2 級」；控制台的「啟用 0／1／2 級」呼叫 `__engineShow.setCompression()`（播放中＝這段播完才套用，控制台顯示「已選 N 級」） |
| `shortVersion`；`getCues()` 的 `droppedLines`、`skipped`、`chapter` | 啟用 2 級時顯示本段短版；顯示本段略過的句子；跳到選單依章節分組、標示「目前略過」 |

全劇 cue 集（`cues/show/`）已填好查核點與 `escalate`（a2_c011 13 分／90 秒 1 級、a4_c011 23.45／120 秒 1 級、a6_c005 30.82／150 秒 2 級、a8_c003 34.55），控制台實測八題正解 2、3、1、1、3、2、3、2、指定區 ABCDABCD 正確。

## 4. 訊息（`console-protocol.ts` 的 `Msg`）

舞台 → 控制台：`state`（快照：引擎狀態子集、舞台焦點／顯示／縮放、授課時鐘、查核點紀錄、壓縮級別、最後按鍵；播放中每 250 ms、其他每 1 s、狀態轉換立即）、`cues`、`ack`（操作結果：advanced／ignored／paused／resumed／back／need-gesture…）、`key`。
控制台 → 舞台：`hello`、`cmd`（next／prev／pause／replay／start／goto）、`clock`（start／reset／adjust／restore）、`compression`。Electron 主程序 → 兩個視窗：`host`（layout、display-metrics）。

## 5. 需要主線配合（handoff）

1. `app/build.mjs` 結尾加：`const { buildConsole } = await import('./console.build.mjs'); await buildConsole({ dev });`（否則 `npm run build` 不會產生控制台與 `stage.html`）。`package.json` 可加 `"build:console": "node console.build.mjs"`、`"test:console": "node ../tools/console-test.mjs"`。
2. `.gitignore` 加 `app/electron/out/`。
3. （選擇）若要讓 `index.html` 本身也能接控制台，在 `<script src="app.js"></script>` 後加 `<script src="console-link.js"></script>`；`console.build.mjs` 會偵測到並讓 `stage.html` 與它相同。
4. 授課時鐘起點差 30 秒：時長估算 v03 的查核點以「老師上台」為 00:00、開幕約 00:30；引擎 `checkpointReport()` 從「片頭按下一步」起算，所以引擎的 `behindSec`／`suggestedCompression` 比表上少算 30 秒。控制台已自行加上 00:30（老師可 ±30 秒）並用 `escalate` 門檻重算建議；若教師選單或其他地方也要顯示引擎的建議級別，請主線決定是否在引擎加 30 秒起點（`CLOCK_START_OFFSET`）。
5. G6 打包：`node app/electron/pack.mjs` 組可攜版；操作卡請寫「延伸顯示（Win＋P）→ 雙擊 AntidrugTheater.exe → 在控制台按下一步＝準備播放」與單一視窗退路。

## 6. 已知限制（代理驗收查不了的）

- 作業系統焦點：無頭瀏覽器不能真的切焦點，測試是模擬 focus／blur 與 `document.hasFocus()`；實機請點一下投影畫面再點回控制台，看提示是否正確。
- 兩個實體螢幕的視窗位置、Windows 縮放比例不同時的重設：版面邏輯有單元測試、縮放用模擬驗證；學校筆電未驗證（彩排時看控制台「狀態 › 舞台畫面」的縮放值）。
- Electron 在本機用 macOS 41.3.0 驗證；可攜版用 Windows 44.9.1（探針同版），未在 Windows 實跑。
- 瀏覽器雙視窗要老師在投影畫面上按一次「準備播放」；Edge kiosk（InPrivate）每次都要重新允許視窗管理權限。
