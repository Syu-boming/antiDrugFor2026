// 反毒剪紙劇場：學校筆電硬體探針。單檔、離線，file:// 與 Electron 都能執行。
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { WebGPURenderer } from 'three/webgpu';

const VERSION = 'probe-v01 (2026-10-20)';
const $ = (id) => document.getElementById(id);
const results = { version: VERSION, started: new Date().toISOString(), env: {}, gpu: {}, bench: [], thermal: [], keys: [], audio: [], notes: [] };
const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* 私密模式等情況 */ } },
};

// ---------- 環境資訊 ----------
async function collectEnv() {
  const e = results.env;
  e.userAgent = navigator.userAgent;
  e.protocol = location.protocol;
  e.electron = /Electron/.test(navigator.userAgent);
  e.screen = { w: screen.width, h: screen.height, availW: screen.availWidth, availH: screen.availHeight, dpr: devicePixelRatio, colorDepth: screen.colorDepth };
  e.window = { w: innerWidth, h: innerHeight };
  e.cores = navigator.hardwareConcurrency || null;
  e.memoryGB = navigator.deviceMemory || null;
  e.windowManagementAPI = 'getScreenDetails' in window;
  e.keyboardLockAPI = !!(navigator.keyboard && navigator.keyboard.lock);
  try {
    if (navigator.getBattery) { const b = await navigator.getBattery(); e.battery = { charging: b.charging, level: Math.round(b.level * 100) }; }
  } catch { /* 不支援 */ }
  if (window.probeHost) {
    try { e.electronInfo = await window.probeHost.info(); } catch (err) { e.electronInfo = String(err); }
  }
  const f5 = store.get('probe_f5');
  if (f5 && Date.now() - Number(f5) < 15000) {
    results.notes.push('偵測到：上次按 F5 後頁面重新整理了（F5 無法攔截）。');
    e.f5Reloaded = true;
  }
  store.set('probe_f5', '');

  // WebGL2
  const c = document.createElement('canvas');
  const gl = c.getContext('webgl2');
  if (!gl) { results.gpu.webgl2 = false; }
  else {
    const dbg = gl.getExtension('WEBGL_debug_renderer_info');
    results.gpu.webgl2 = true;
    results.gpu.renderer = dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
    results.gpu.vendor = dbg ? gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL) : gl.getParameter(gl.VENDOR);
    results.gpu.maxTexture = gl.getParameter(gl.MAX_TEXTURE_SIZE);
    results.gpu.maxSamples = gl.getParameter(gl.MAX_SAMPLES);
    const r = String(results.gpu.renderer);
    results.gpu.software = /SwiftShader|Basic Render|llvmpipe|Software/i.test(r);
  }
  // WebGPU
  results.gpu.webgpu = false;
  if (navigator.gpu) {
    try {
      const ad = await navigator.gpu.requestAdapter({ powerPreference: 'high-performance' });
      if (ad) {
        results.gpu.webgpu = true;
        const info = ad.info || (ad.requestAdapterInfo ? await ad.requestAdapterInfo() : {});
        results.gpu.webgpuAdapter = { vendor: info.vendor, architecture: info.architecture, device: info.device, description: info.description, fallback: !!ad.isFallbackAdapter, maxTexture2D: ad.limits.maxTextureDimension2D };
      }
    } catch (err) { results.gpu.webgpuError = String(err); }
  }
  renderSummary();
}

// ---------- 程式產生的紙材貼圖（不需外部圖檔） ----------
function rand(seed) { let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }
function paperTexture(color, seed, shape) {
  const S = 1024, cv = document.createElement('canvas'); cv.width = cv.height = S;
  const g = cv.getContext('2d'), r = rand(seed);
  g.fillStyle = color; g.beginPath();
  if (shape === 'hills') {
    g.moveTo(0, S); for (let x = 0; x <= S; x += 16) g.lineTo(x, S * 0.45 + Math.sin(x / 140 + seed) * 70 + r() * 10); g.lineTo(S, S);
  } else if (shape === 'houses') {
    g.moveTo(0, S); let x = 0; while (x < S) { const w = 110 + r() * 80, h = 260 + r() * 260; g.lineTo(x, S - h); g.lineTo(x + w / 2, S - h - 70); g.lineTo(x + w, S - h); x += w + 8; } g.lineTo(S, S);
  } else if (shape === 'tree') {
    g.arc(S / 2, S * 0.36, S * 0.3, 0, Math.PI * 2); g.rect(S * 0.46, S * 0.5, S * 0.08, S * 0.5);
  } else if (shape === 'figure') {
    g.arc(S / 2, S * 0.2, S * 0.12, 0, Math.PI * 2); g.rect(S * 0.37, S * 0.32, S * 0.26, S * 0.4); g.rect(S * 0.38, S * 0.7, S * 0.09, S * 0.3); g.rect(S * 0.53, S * 0.7, S * 0.09, S * 0.3);
  } else { g.rect(0, 0, S, S); }
  g.fill();
  // 手撕毛邊與紙纖維
  g.globalCompositeOperation = 'source-atop';
  for (let i = 0; i < 1800; i++) { g.strokeStyle = `rgba(255,255,255,${0.05 + r() * 0.12})`; g.lineWidth = 0.6 + r(); g.beginPath(); const x = r() * S, y = r() * S; g.moveTo(x, y); g.quadraticCurveTo(x + r() * 18 - 9, y + r() * 18 - 9, x + r() * 30 - 15, y + r() * 30 - 15); g.stroke(); }
  g.globalCompositeOperation = 'destination-out';
  for (let i = 0; i < 500; i++) { g.fillStyle = `rgba(0,0,0,${r() * 0.5})`; g.beginPath(); g.arc(r() * S, r() * S, r() * 2.2, 0, Math.PI * 2); g.fill(); }
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
  return t;
}

// ---------- 代表場景（接近 A 級負載） ----------
function buildScene(o) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#2a2238');
  const camera = new THREE.PerspectiveCamera(20, 16 / 9, 1, 200);
  camera.position.set(0, 2, 38);
  scene.add(new THREE.AmbientLight('#ffe8cc', 0.55));
  const sun = new THREE.DirectionalLight('#fff2dc', 1.6);
  sun.position.set(-8, 12, 14);
  if (o.shadows) { sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048); sun.shadow.radius = 4; Object.assign(sun.shadow.camera, { left: -16, right: 16, top: 12, bottom: -12, near: 1, far: 60 }); }
  scene.add(sun);
  const colors = ['#e9dcc3', '#b9d3c5', '#e7b48f', '#9fbfa0', '#d9a6a0', '#c9b6d9'];
  const shapes = ['rect', 'hills', 'houses', 'hills', 'houses', 'hills'];
  const group = new THREE.Group(); scene.add(group);
  for (let i = 0; i < o.layers; i++) {
    const mat = new THREE.MeshStandardMaterial({ map: paperTexture(colors[i % 6], 11 + i, shapes[i % 6]), roughness: 0.95, alphaTest: 0.5, side: THREE.DoubleSide });
    const m = new THREE.Mesh(new THREE.PlaneGeometry(30, 17), mat);
    m.position.z = -i * 1.4 + 4; m.position.y = -0.5;
    m.castShadow = m.receiveShadow = o.shadows; group.add(m);
  }
  // 半透明和紙層（一般透明混合、不寫深度）
  const washi = new THREE.Mesh(new THREE.PlaneGeometry(30, 17), new THREE.MeshStandardMaterial({ map: paperTexture('#fff6e0', 77, 'rect'), transparent: true, opacity: 0.35, depthWrite: false }));
  washi.position.z = 5.5; washi.renderOrder = 10; group.add(washi);
  const figs = [];
  for (let i = 0; i < 4; i++) {
    const f = new THREE.Mesh(new THREE.PlaneGeometry(3, 3), new THREE.MeshStandardMaterial({ map: paperTexture(['#e5b23a', '#e05a3a', '#2f4f7a', '#6aa58e'][i], 200 + i, i === 3 ? 'tree' : 'figure'), alphaTest: 0.5, side: THREE.DoubleSide }));
    f.position.set(-6 + i * 4, -2.2, 3 + (i % 2) * 0.6); f.castShadow = f.receiveShadow = o.shadows; group.add(f); figs.push(f);
  }
  // 聚光燈光錐（加色混合）
  const cone = new THREE.Mesh(new THREE.ConeGeometry(4, 14, 48, 1, true), new THREE.MeshBasicMaterial({ color: '#ffe2a8', transparent: true, opacity: 0.12, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
  cone.position.set(2, 4, 4); cone.rotation.z = 0.35; cone.renderOrder = 11; scene.add(cone);
  let dust = null;
  if (o.particles) {
    const n = 3000, pos = new Float32Array(n * 3), r = rand(9);
    for (let i = 0; i < n; i++) { pos[i * 3] = r() * 24 - 12; pos[i * 3 + 1] = r() * 14 - 6; pos[i * 3 + 2] = r() * 10 - 2; }
    const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    dust = new THREE.Points(geo, new THREE.PointsMaterial({ color: '#fff4d6', size: 0.06, transparent: true, opacity: 0.6, depthWrite: false }));
    scene.add(dust);
  }
  const update = (t) => {
    camera.position.x = Math.sin(t * 0.25) * 3; camera.position.z = 36 + Math.sin(t * 0.17) * 2; camera.lookAt(0, 0, 0);
    figs.forEach((f, i) => { f.rotation.z = Math.sin(t * 1.3 + i) * 0.08; f.position.y = -2.2 + Math.abs(Math.sin(t * 2 + i)) * 0.15; });
    cone.rotation.z = 0.35 + Math.sin(t * 0.6) * 0.2;
    if (dust) dust.rotation.y = t * 0.02;
  };
  return { scene, camera, update };
}

const GradingShader = {
  uniforms: { tDiffuse: { value: null }, sat: { value: 1.08 }, lift: { value: 0.02 }, gain: { value: 1.03 } },
  vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
  fragmentShader: 'uniform sampler2D tDiffuse; uniform float sat, lift, gain; varying vec2 vUv; void main(){ vec4 c = texture2D(tDiffuse, vUv); float l = dot(c.rgb, vec3(0.2126,0.7152,0.0722)); c.rgb = mix(vec3(l), c.rgb, sat); c.rgb = c.rgb * gain + lift; gl_FragColor = c; }',
};

// ---------- 效能量測 ----------
const canvasHost = () => $('stage');
async function makeRenderer(o) {
  const host = canvasHost(); host.innerHTML = '';
  let renderer;
  if (o.kind === 'webgl') {
    renderer = new THREE.WebGLRenderer({ antialias: o.msaa && !o.post, powerPreference: 'high-performance' });
  } else {
    renderer = new WebGPURenderer({ antialias: o.msaa, forceWebGL: o.kind === 'webgpu-forcewebgl', powerPreference: 'high-performance' });
    await renderer.init();
  }
  renderer.toneMapping = THREE.NoToneMapping;
  renderer.shadowMap.enabled = !!o.shadows;
  if (renderer.shadowMap) renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  if (o.res === '1080p') { renderer.setPixelRatio(1); renderer.setSize(1920, 1080, false); }
  else { renderer.setPixelRatio(devicePixelRatio); renderer.setSize(innerWidth, innerHeight, false); }
  renderer.domElement.style.cssText = 'width:100%;height:100%;display:block;object-fit:contain;background:#000';
  host.appendChild(renderer.domElement);
  return renderer;
}

function stats(deltas) {
  if (!deltas.length) return null;
  const s = [...deltas].sort((a, b) => a - b), q = (p) => s[Math.min(s.length - 1, Math.floor(p * s.length))];
  return { frames: s.length, fpsMedian: Math.round(1000 / q(0.5) * 10) / 10, p50ms: +q(0.5).toFixed(2), p95ms: +q(0.95).toFixed(2), maxMs: +s[s.length - 1].toFixed(1), over100ms: s.filter((d) => d > 100).length };
}

async function runBench(o, seconds, onTick) {
  const label = o.label;
  let renderer, composer, sceneObj;
  try {
    renderer = await makeRenderer(o);
    sceneObj = buildScene(o);
    if (o.kind === 'webgl' && o.post) {
      const size = renderer.getDrawingBufferSize(new THREE.Vector2());
      const rt = new THREE.WebGLRenderTarget(size.x, size.y, { type: THREE.HalfFloatType, samples: o.msaa ? 4 : 0 });
      composer = new EffectComposer(renderer, rt);
      composer.addPass(new RenderPass(sceneObj.scene, sceneObj.camera));
      if (o.bloom) composer.addPass(new UnrealBloomPass(new THREE.Vector2(size.x / 2, size.y / 2), 0.45, 0.6, 0.85));
      if (o.grading) composer.addPass(new ShaderPass(GradingShader));
      composer.addPass(new OutputPass());
    }
    if (renderer.compileAsync) await renderer.compileAsync(sceneObj.scene, sceneObj.camera);
  } catch (err) {
    const rec = { label, error: String(err && err.message || err) };
    results.bench.push(rec); return rec;
  }
  const deltas = []; const t0 = performance.now(); let last = t0;
  await new Promise((resolve) => {
    const frame = (now) => {
      const t = (now - t0) / 1000;
      sceneObj.update(t);
      if (composer) composer.render(); else renderer.render(sceneObj.scene, sceneObj.camera);
      if (t > 2) deltas.push(now - last);
      last = now;
      if (onTick) onTick(t, seconds, deltas);
      if (t < seconds + 2) requestAnimationFrame(frame); else resolve();
    };
    requestAnimationFrame(frame);
  });
  const rec = { label, kind: o.kind, res: o.res, config: { msaa: o.msaa, shadows: o.shadows, bloom: !!o.bloom, grading: !!o.grading, particles: o.particles, layers: o.layers }, backend: renderer.backend ? (renderer.backend.isWebGPUBackend ? 'WebGPU' : 'WebGL2 (WebGPURenderer)') : 'WebGL2', size: renderer.getDrawingBufferSize ? renderer.getDrawingBufferSize(new THREE.Vector2()).toArray() : null, ...stats(deltas) };
  renderer.dispose && renderer.dispose();
  results.bench.push(rec); saveLocal();
  return rec;
}

const FULL = { msaa: true, shadows: true, bloom: true, grading: true, particles: true, layers: 6, post: true };
const BASE = { msaa: true, shadows: true, bloom: false, grading: false, particles: true, layers: 6, post: false };
function quickPlan() {
  const p = [
    { label: 'WebGL A 級全效果 1080p', kind: 'webgl', res: '1080p', ...FULL, secs: 15 },
    { label: 'WebGL 基本場景（無後製）1080p', kind: 'webgl', res: '1080p', ...BASE, secs: 10 },
    { label: 'A 級－陰影', kind: 'webgl', res: '1080p', ...FULL, shadows: false, secs: 8 },
    { label: 'A 級－泛光', kind: 'webgl', res: '1080p', ...FULL, bloom: false, secs: 8 },
    { label: 'A 級－粒子', kind: 'webgl', res: '1080p', ...FULL, particles: false, secs: 8 },
    { label: 'A 級－多重取樣', kind: 'webgl', res: '1080p', ...FULL, msaa: false, secs: 8 },
    { label: 'WebGL A 級全效果 原生解析度', kind: 'webgl', res: 'native', ...FULL, secs: 10 },
  ];
  if (results.gpu.webgpu) p.push({ label: 'WebGPU 基本場景 1080p', kind: 'webgpu', res: '1080p', ...BASE, secs: 10 });
  p.push({ label: 'WebGPURenderer 強制 WebGL2 基本場景 1080p', kind: 'webgpu-forcewebgl', res: '1080p', ...BASE, secs: 10 });
  return p;
}

async function runPlan(plan, title) {
  document.body.classList.add('running');
  for (let i = 0; i < plan.length; i++) {
    const o = plan[i];
    $('progress').textContent = `${title}：${i + 1}/${plan.length}　${o.label}`;
    await runBench(o, o.secs, (t, s) => { $('progress').textContent = `${title}：${i + 1}/${plan.length}　${o.label}　${Math.max(0, Math.ceil(s + 2 - t))} 秒`; });
  }
  canvasHost().innerHTML = '';
  document.body.classList.remove('running');
  $('progress').textContent = '';
  renderSummary(); show('summary');
}

async function thermal() {
  document.body.classList.add('running');
  const o = { label: '耐熱 10 分鐘（WebGL A 級 1080p）', kind: 'webgl', res: '1080p', ...FULL };
  results.thermal = [];
  for (let m = 1; m <= 10; m++) {
    $('progress').textContent = `耐熱測試：第 ${m}/10 分鐘`;
    const rec = await runBench({ ...o, label: `耐熱第 ${m} 分鐘` }, 58);
    results.bench.pop(); results.thermal.push({ minute: m, p95ms: rec.p95ms, fpsMedian: rec.fpsMedian, over100ms: rec.over100ms });
    saveLocal();
  }
  canvasHost().innerHTML = ''; document.body.classList.remove('running'); $('progress').textContent = '';
  renderSummary(); show('summary');
}

// ---------- 按鍵 ----------
const HANDLED = ['PageUp', 'PageDown', 'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', ' ', 'Enter', '.', 'b', 'B', 'F5', 'Tab'];
window.addEventListener('keydown', (ev) => {
  const rec = { key: ev.key, code: ev.code, repeat: ev.repeat, t: Math.round(performance.now()) };
  if (ev.key === 'F5') store.set('probe_f5', String(Date.now()));
  if (HANDLED.includes(ev.key)) ev.preventDefault();
  results.keys.push(rec); if (results.keys.length > 200) results.keys.shift();
  const log = $('keylog');
  if (log) log.innerHTML = results.keys.slice(-14).reverse().map((k) => `<div><b>${k.key === ' ' ? 'Space' : k.key}</b>　code=${k.code}${k.repeat ? '　（長按重複）' : ''}</div>`).join('');
  saveLocal();
});

// ---------- 聲音 ----------
let actx = null;
function ctx() { if (!actx) actx = new (window.AudioContext || window.webkitAudioContext)(); if (actx.state === 'suspended') actx.resume(); return actx; }
function tone(freq, dur, pan = 0, delay = 0) {
  const a = ctx(), o = a.createOscillator(), g = a.createGain(), p = a.createStereoPanner();
  o.frequency.value = freq; o.connect(g).connect(p).connect(a.destination); p.pan.value = pan;
  const t = a.currentTime + delay; g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(0.3, t + 0.02); g.gain.setValueAtTime(0.3, t + dur - 0.05); g.gain.linearRampToValueAtTime(0, t + dur);
  o.start(t); o.stop(t + dur + 0.05);
}
const audioTests = {
  left: () => { tone(660, 1.2, -1); results.audio.push('左聲道測試'); },
  right: () => { tone(660, 1.2, 1); results.audio.push('右聲道測試'); },
  both: () => { tone(1000, 1.5, 0); results.audio.push('雙聲道 1kHz'); },
  sweep: () => { [262, 330, 392, 523, 659, 784].forEach((f, i) => tone(f, 0.35, 0, i * 0.4)); results.audio.push('音階'); },
  swallow: () => { $('audiostatus').textContent = '8 秒後會響一聲短嗶，注意開頭有沒有被吃掉…'; tone(1000, 0.25, 0, 8); setTimeout(() => { $('audiostatus').textContent = '剛才的嗶聲完整嗎？（完整＝不會吞音）'; }, 8400); results.audio.push('靜音 8 秒後嗶聲（HDMI 吞音測試）'); },
};

// ---------- 投影圖卡 ----------
function drawCards() {
  const cv = $('cards'); const W = 1920, H = 1080; cv.width = W; cv.height = H;
  const g = cv.getContext('2d');
  g.fillStyle = '#000'; g.fillRect(0, 0, W, H);
  for (let i = 0; i <= 10; i++) { const v = Math.round(i * 25.5); g.fillStyle = `rgb(${v},${v},${v})`; g.fillRect(60 + i * 160, 40, 150, 120); g.fillStyle = i < 6 ? '#fff' : '#000'; g.font = 'bold 28px sans-serif'; g.fillText(`${i * 10}%`, 80 + i * 160, 110); }
  const sizes = [40, 48, 56, 64, 72, 84, 96];
  let y = 230;
  g.fillStyle = '#fff';
  sizes.forEach((s) => { g.font = `bold ${s}px "Microsoft JhengHei","PingFang TC","Noto Sans TC",sans-serif`; g.fillText(`${s}px　${s >= 84 ? '不碰、不試；先離開' : '不碰、不試；先離開，找大人。'}`, 60, y + s); y += s + 22; });
  const sw = [['#e5b23a', '1', '●'], ['#3a8fb7', '2', '▲'], ['#e05a3a', '3', '■']];
  sw.forEach(([c, n, sh], i) => { g.fillStyle = c; g.fillRect(1420, 230 + i * 170, 420, 140); g.fillStyle = '#fff'; g.font = 'bold 96px sans-serif'; g.fillText(`${n} ${sh}`, 1460, 335 + i * 170); });
  ['#efe6d2', '#9fbfa0', '#2a2238'].forEach((c, i) => { g.fillStyle = c; g.fillRect(1420 + i * 140, 760, 130, 260); g.strokeStyle = '#8a8a8a'; g.lineWidth = 8; g.beginPath(); g.moveTo(1485 + i * 140, 760); g.lineTo(1485 + i * 140, 1020); g.stroke(); });
  g.fillStyle = '#ddd'; g.font = '24px sans-serif'; g.fillText('灰色操偶線在三種背景上', 1420, 1050);
  g.lineWidth = 4;
  g.strokeStyle = '#00e0ff'; g.strokeRect(2, 2, W - 4, H - 4);
  g.strokeStyle = '#ffd400'; const w43 = H * 4 / 3; g.strokeRect((W - w43) / 2, 2, w43, H - 4);
  g.strokeStyle = '#ff5ad1'; const h1610 = W * 10 / 16; if (h1610 <= H) g.strokeRect(2, (H - h1610) / 2, W - 4, h1610);
  g.strokeStyle = '#7CFC00'; g.setLineDash([16, 12]); g.strokeRect(W * 0.05, H * 0.05, W * 0.9, H * 0.9); g.setLineDash([]);
  g.fillStyle = '#ccc'; g.font = '22px sans-serif'; g.fillText('藍框 16:9 全畫面｜黃框 4:3｜綠虛線 90% 安全框', 60, H - 20);
}

// ---------- 介面 ----------
function show(id) { document.querySelectorAll('.panel').forEach((p) => p.classList.toggle('on', p.id === id)); }
function saveLocal() { store.set('probe_results', JSON.stringify(results)); }
function fmtBench(b) { return b.error ? `${b.label}：失敗（${b.error}）` : `${b.label}：${b.fpsMedian} fps，第 95 百分位 ${b.p95ms} ms，最長 ${b.maxMs} ms，超過 100 ms ${b.over100ms} 次（${b.size ? b.size.join('×') : ''}，${b.backend}）`; }
function renderSummary() {
  const g = results.gpu, e = results.env;
  const lines = [
    `探針版本：${VERSION}`,
    `執行方式：${e.electron ? 'Electron 可攜版' : (e.protocol === 'file:' ? '瀏覽器開啟 file://' : e.protocol)}`,
    `瀏覽器：${(e.userAgent || '').replace(/.*(Edg\/[\d.]+|Chrome\/[\d.]+).*/, '$1')}${e.electronInfo && e.electronInfo.versions ? `（Electron ${e.electronInfo.versions.electron}）` : ''}`,
    `螢幕：${e.screen ? `${e.screen.w}×${e.screen.h}，縮放 ${Math.round(e.screen.dpr * 100)}%` : ''}${e.electronInfo && e.electronInfo.displays ? `；顯示器 ${e.electronInfo.displays.length} 台：${e.electronInfo.displays.map((d) => `${d.size.width}×${d.size.height}@${Math.round(d.scaleFactor * 100)}%`).join('、')}` : ''}`,
    `GPU：${g.renderer || '未知'}${g.software ? '　⚠ 軟體渲染（不通過）' : ''}`,
    `WebGL2：${g.webgl2 ? '可用' : '不可用'}；最大貼圖 ${g.maxTexture || '?'}；多重取樣 ${g.maxSamples || '?'}`,
    `WebGPU：${g.webgpu ? `可用（${[g.webgpuAdapter.vendor, g.webgpuAdapter.architecture, g.webgpuAdapter.description].filter(Boolean).join(' ')}${g.webgpuAdapter.fallback ? '，後備介面卡' : ''}）` : `不可用${g.webgpuError ? `（${g.webgpuError}）` : ''}`}`,
    `電源：${e.battery ? `${e.battery.charging ? '接電' : '用電池'}，電量 ${e.battery.level}%` : '未知'}`,
    `雙螢幕 API：${e.windowManagementAPI ? '有' : '無'}；Keyboard Lock：${e.keyboardLockAPI ? '有' : '無'}`,
    ...results.bench.map(fmtBench),
    ...(results.thermal.length ? [`耐熱 10 分鐘：每分鐘第 95 百分位 ${results.thermal.map((x) => x.p95ms).join(' / ')} ms`] : []),
    `按鍵紀錄：${[...new Set(results.keys.map((k) => `${k.key === ' ' ? 'Space' : k.key}(${k.code})`))].slice(-12).join('、') || '尚未測試'}`,
    ...results.notes,
  ];
  $('summarytext').innerHTML = lines.map((l) => `<div>${l}</div>`).join('');
}
function download() {
  results.finished = new Date().toISOString();
  const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' });
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `探針結果_${new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-')}.json`; a.click();
}

window.addEventListener('DOMContentLoaded', () => {
  const prev = store.get('probe_results');
  if (prev) { try { const p = JSON.parse(prev); results.bench = p.bench || []; results.thermal = p.thermal || []; results.keys = p.keys || []; } catch { /* 忽略 */ } }
  $('btn-full').onclick = () => { (document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen()).catch(() => {}); };
  $('btn-quick').onclick = () => runPlan(quickPlan(), '快速測試');
  $('btn-60').onclick = () => runPlan([{ label: '60 秒（WebGL A 級 1080p）', kind: 'webgl', res: '1080p', ...FULL, secs: 60 }], '60 秒測試');
  $('btn-thermal').onclick = thermal;
  $('btn-keys').onclick = () => show('keys');
  $('btn-audio').onclick = () => { ctx(); show('audio'); };
  $('btn-cards').onclick = () => { drawCards(); show('cardspanel'); };
  $('btn-summary').onclick = () => { renderSummary(); show('summary'); };
  $('btn-download').onclick = download;
  $('btn-reset').onclick = () => { results.bench = []; results.thermal = []; results.keys = []; saveLocal(); renderSummary(); };
  Object.entries(audioTests).forEach(([k, fn]) => { const b = $(`a-${k}`); if (b) b.onclick = fn; });
  collectEnv().then(() => show('summary'));
});
