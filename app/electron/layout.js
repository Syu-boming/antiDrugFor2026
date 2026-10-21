// 依顯示器決定開幾個視窗、各放哪個螢幕（v1.2 第 19.4 節；純函式，tools/console-test.mjs 有單元測試）。
//   延伸顯示（兩個不同的畫面）→ 雙視窗：控制台放筆電內建螢幕（找不到就放主螢幕），舞台放另一個（優先外接）。
//   同步顯示（只回報一個畫面，或兩個畫面範圍完全相同）、只有一個螢幕、只投影到第二畫面 → 單一舞台視窗。
// displays：[{ id, bounds:{x,y,width,height}, internal }]（Electron screen.getAllDisplays() 的子集）

function sameBounds(a, b) {
  return a.bounds.x === b.bounds.x && a.bounds.y === b.bounds.y && a.bounds.width === b.bounds.width && a.bounds.height === b.bounds.height;
}

function chooseLayout(displays, primaryId, opts = {}) {
  if (!displays || !displays.length) return { mode: 'single', reason: 'no-display', stage: primaryId };
  const primary = displays.find((d) => d.id === primaryId) || displays[0];
  if (opts.single) return { mode: 'single', reason: 'forced', stage: primary.id };
  if (opts.dualTest) return { mode: 'dual-test', reason: 'test', stage: primary.id, console: primary.id };
  const consoleD = displays.find((d) => d.internal) || primary;
  const others = displays.filter((d) => d.id !== consoleD.id && !sameBounds(d, consoleD));
  if (!others.length) return { mode: 'single', reason: displays.length > 1 ? 'mirror' : 'one-display', stage: consoleD.id };
  const wanted = opts.stageDisplay != null ? others.find((d) => d.id === opts.stageDisplay) : null;
  const stage = wanted || others.find((d) => !d.internal) || others[0];
  return { mode: 'dual', reason: 'extended', stage: stage.id, console: consoleD.id };
}

module.exports = { chooseLayout, sameBounds };
