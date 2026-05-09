"use strict";

const TILE_SIZE = 44;
const TILE_GAP = 3;
const TILE_RADIUS = 6;

const ACTION_DELTAS = [
  [0, -1],
  [0, 1],
  [-1, 0],
  [1, 0],
];

const PLASMA_STOPS = [
  [13, 8, 135],
  [84, 2, 163],
  [156, 23, 158],
  [218, 78, 119],
  [252, 159, 79],
  [240, 249, 33],
];

const SPRITE_FILES = {
  up: "/assets/sprites/business_man_1_back.png",
  down: "/assets/sprites/business_man_1_forward.png",
  left: "/assets/sprites/business_man_1_left.png",
  right: "/assets/sprites/business_man_1_right.png",
};

const els = {
  status: document.getElementById("status-pill"),
  statusText: document.getElementById("status-text"),
  speedText: document.getElementById("speed-text"),
  subtitle: document.getElementById("subtitle"),
  connection: document.getElementById("connection"),
  metricEp: document.getElementById("metric-ep"),
  metricEps: document.getElementById("metric-eps"),
  metricLast: document.getElementById("metric-last"),
  metricAvg: document.getElementById("metric-avg"),
  legendMin: document.getElementById("legend-min"),
  legendMax: document.getElementById("legend-max"),
  toggleLabel: document.getElementById("toggle-label"),
  speedButtons: document.getElementById("speed-buttons"),
  chartSubtitle: document.getElementById("chart-subtitle"),
  gridCanvas: document.getElementById("grid-canvas"),
  chartCanvas: document.getElementById("chart-canvas"),
};

const sprites = {};
const buildingSprites = {};
let bankSprite = null;

let socket = null;
let config = null;
let lastState = null;
let pendingFrame = false;

function lerp(a, b, t) {
  return [
    Math.round(a[0] + (b[0] - a[0]) * t),
    Math.round(a[1] + (b[1] - a[1]) * t),
    Math.round(a[2] + (b[2] - a[2]) * t),
  ];
}

function plasma(t) {
  if (!isFinite(t)) t = 0;
  t = Math.max(0, Math.min(1, t));
  const n = PLASMA_STOPS.length - 1;
  const seg = t * n;
  const i = Math.min(n - 1, Math.floor(seg));
  return lerp(PLASMA_STOPS[i], PLASMA_STOPS[i + 1], seg - i);
}

function rgb(c) {
  return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
}

function loadImage(src) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => resolve(null);
    img.src = src;
  });
}

async function loadAllSprites(buildings) {
  for (const [key, src] of Object.entries(SPRITE_FILES)) {
    sprites[key] = await loadImage(src);
  }
  for (const b of buildings) {
    buildingSprites[b.file] = await loadImage(`/assets/elems/${b.file}`);
  }
  bankSprite = await loadImage("/assets/elems/bank.png");
}

function setupCanvas(canvas, cssWidth, cssHeight) {
  const dpr = window.devicePixelRatio || 1;
  canvas.style.width = cssWidth + "px";
  canvas.style.height = cssHeight + "px";
  canvas.width = Math.round(cssWidth * dpr);
  canvas.height = Math.round(cssHeight * dpr);
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return ctx;
}

function roundedRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function drawGrid(state) {
  if (!config) return;
  const cols = config.gridCols;
  const rows = config.gridRows;
  const w = cols * TILE_SIZE;
  const h = rows * TILE_SIZE;
  const ctx = setupCanvas(els.gridCanvas, w, h);

  ctx.clearRect(0, 0, w, h);

  const obstacleSet = new Set(config.obstacles.map((o) => `${o[0]},${o[1]}`));
  const bankKey = `${config.bank[0]},${config.bank[1]}`;

  const span = state.vmax - state.vmin || 1;

  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) {
      const tx = col * TILE_SIZE + TILE_GAP / 2;
      const ty = row * TILE_SIZE + TILE_GAP / 2;
      const tw = TILE_SIZE - TILE_GAP;
      const th = TILE_SIZE - TILE_GAP;
      const key = `${col},${row}`;

      if (obstacleSet.has(key)) {
        ctx.fillStyle = "#1c2131";
      } else if (key === bankKey) {
        ctx.fillStyle = "#34d399";
      } else {
        const idx = row * cols + col;
        const v = state.v[idx];
        const t = (v - state.vmin) / span;
        ctx.fillStyle = rgb(plasma(t));
      }
      roundedRect(ctx, tx, ty, tw, th, TILE_RADIUS);
      ctx.fill();
    }
  }

  ctx.fillStyle = "rgba(245, 247, 255, 0.82)";
  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) {
      const key = `${col},${row}`;
      if (obstacleSet.has(key) || key === bankKey) continue;
      const idx = row * cols + col;
      const v = state.v[idx];
      if (v === 0) continue;
      const action = state.best[idx];
      const [dc, dr] = ACTION_DELTAS[action];
      const cx = col * TILE_SIZE + TILE_SIZE / 2;
      const cy = row * TILE_SIZE + TILE_SIZE / 2;
      const r = 7;
      ctx.beginPath();
      ctx.moveTo(cx + dc * r, cy + dr * r);
      ctx.lineTo(cx - dc * (r * 0.55) + -dr * (r * 0.7), cy - dr * (r * 0.55) + dc * (r * 0.7));
      ctx.lineTo(cx - dc * (r * 0.55) - -dr * (r * 0.7), cy - dr * (r * 0.55) - dc * (r * 0.7));
      ctx.closePath();
      ctx.fill();
    }
  }

  for (const b of config.buildings) {
    const img = buildingSprites[b.file];
    if (img) {
      ctx.drawImage(img, b.col * TILE_SIZE, b.row * TILE_SIZE, TILE_SIZE, TILE_SIZE);
    }
  }
  if (bankSprite) {
    ctx.drawImage(
      bankSprite,
      config.bank[0] * TILE_SIZE,
      config.bank[1] * TILE_SIZE,
      TILE_SIZE,
      TILE_SIZE,
    );
  }

  const ax = state.agent.col * TILE_SIZE;
  const ay = state.agent.row * TILE_SIZE;
  ctx.strokeStyle = "#38bdf8";
  ctx.lineWidth = 2;
  roundedRect(ctx, ax + 1, ay + 1, TILE_SIZE - 2, TILE_SIZE - 2, TILE_RADIUS);
  ctx.stroke();
  const sprite = sprites[state.agent.facing];
  if (sprite) {
    ctx.drawImage(sprite, ax, ay, TILE_SIZE, TILE_SIZE);
  }
}

function niceCeil(value, step) {
  return Math.ceil(value / step) * step;
}

function drawChart(state) {
  const canvas = els.chartCanvas;
  const cssWidth = canvas.parentElement.clientWidth - 20;
  const cssHeight = canvas.parentElement.clientHeight - 20;
  const ctx = setupCanvas(canvas, cssWidth, cssHeight);

  ctx.clearRect(0, 0, cssWidth, cssHeight);

  const padL = 48;
  const padR = 16;
  const padT = 14;
  const padB = 32;
  const plotX = padL;
  const plotY = padT;
  const plotW = cssWidth - padL - padR;
  const plotH = cssHeight - padT - padB;

  ctx.fillStyle = "rgba(11, 15, 26, 0.55)";
  ctx.fillRect(plotX, plotY, plotW, plotH);

  ctx.font = "11px JetBrains Mono, Consolas, monospace";
  ctx.fillStyle = "#64748b";
  ctx.textBaseline = "middle";

  const lengths = state.lengths || [];
  const totalEps = state.totalEps || 5000;
  const xMax = Math.max(totalEps, lengths.length);
  const rawMax = lengths.length ? Math.max(...lengths) : 50;
  const yMax = Math.max(50, niceCeil(rawMax, 25));

  ctx.strokeStyle = "rgba(148, 163, 184, 0.12)";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const frac = i / 4;
    const y = plotY + plotH - frac * plotH;
    if (i > 0 && i < 4) {
      ctx.beginPath();
      ctx.moveTo(plotX, y);
      ctx.lineTo(plotX + plotW, y);
      ctx.stroke();
    }
    ctx.textAlign = "right";
    ctx.fillText(String(Math.round(yMax * frac)), plotX - 8, y);
  }

  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  for (let i = 0; i <= 4; i++) {
    const frac = i / 4;
    const x = plotX + frac * plotW;
    const val = Math.round(xMax * frac);
    const txt = val >= 1000 ? `${(val / 1000).toFixed(val % 1000 ? 1 : 0)}k` : String(val);
    ctx.fillText(txt, x, plotY + plotH + 8);
  }

  if (lengths.length >= 2) {
    const denom = Math.max(1, xMax - 1);
    ctx.strokeStyle = "rgba(56, 189, 248, 0.75)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let i = 0; i < lengths.length; i++) {
      const x = plotX + (i / denom) * plotW;
      const y = plotY + plotH - (lengths[i] / yMax) * plotH;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }

  const window = 50;
  if (lengths.length >= window) {
    const denom = Math.max(1, xMax - 1);
    let sum = 0;
    for (let i = 0; i < window; i++) sum += lengths[i];
    ctx.strokeStyle = "#fbbf24";
    ctx.lineWidth = 2;
    ctx.beginPath();
    let avg = sum / window;
    let xi = window - 1;
    let x = plotX + (xi / denom) * plotW;
    let y = plotY + plotH - (avg / yMax) * plotH;
    ctx.moveTo(x, y);
    for (let i = window; i < lengths.length; i++) {
      sum += lengths[i] - lengths[i - window];
      avg = sum / window;
      xi = i;
      x = plotX + (xi / denom) * plotW;
      y = plotY + plotH - (avg / yMax) * plotH;
      ctx.lineTo(x, y);
    }
    ctx.stroke();
  }

  if (lengths.length >= 1 && lengths.length < totalEps) {
    const denom = Math.max(1, xMax - 1);
    const nx = plotX + ((lengths.length - 1) / denom) * plotW;
    ctx.strokeStyle = "rgba(148, 163, 184, 0.35)";
    ctx.setLineDash([3, 4]);
    ctx.beginPath();
    ctx.moveTo(nx, plotY);
    ctx.lineTo(nx, plotY + plotH);
    ctx.stroke();
    ctx.setLineDash([]);
  }
}

function setStatus(text, klass) {
  els.statusText.textContent = text;
  els.status.classList.remove("is-training", "is-paused", "is-done");
  els.status.classList.add(klass);
}

function updateUi(state) {
  setupSpeedButtons(state.speedLevels);
  els.speedText.textContent = `${state.speed} steps / frame`;
  els.metricEp.textContent = `${state.ep} / ${state.totalEps}`;
  els.metricEps.textContent = state.eps.toFixed(3);
  els.metricLast.textContent = state.lastLen ? `${state.lastLen} steps` : "— steps";
  els.metricAvg.textContent = state.avg100 ? state.avg100.toFixed(1) : "—";
  els.legendMin.textContent = `${state.vmin >= 0 ? "+" : ""}${state.vmin.toFixed(1)}`;
  els.legendMax.textContent = `${state.vmax >= 0 ? "+" : ""}${state.vmax.toFixed(1)}`;

  if (state.finished) {
    setStatus("DONE", "is-done");
    els.subtitle.textContent = `Trained ${state.totalEps} episodes · agent at ${state.agent.col}, ${state.agent.row}`;
    els.toggleLabel.textContent = "Restart to train again";
  } else if (state.paused) {
    setStatus("PAUSED", "is-paused");
    els.toggleLabel.textContent = "Resume training";
  } else {
    setStatus("TRAINING", "is-training");
    els.toggleLabel.textContent = "Pause training";
  }

  if (state.lengths.length >= 100 && state.avg100 < 25) {
    els.chartSubtitle.classList.add("is-converged");
    els.chartSubtitle.textContent = `Lower is better · Converged near optimum (${state.avg100.toFixed(1)} steps)`;
  } else {
    els.chartSubtitle.classList.remove("is-converged");
    els.chartSubtitle.textContent = "Lower is better";
  }

  for (const btn of els.speedButtons.querySelectorAll("button")) {
    btn.classList.toggle("active", Number(btn.dataset.idx) === state.speedIdx);
  }
}

function setupSpeedButtons(levels) {
  if (els.speedButtons.childElementCount === levels.length) return;
  els.speedButtons.innerHTML = "";
  levels.forEach((value, idx) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.dataset.idx = String(idx);
    btn.textContent = value >= 1000 ? `${value / 1000}k` : String(value);
    btn.title = `${value} steps per frame  (key: ${idx + 1})`;
    btn.addEventListener("click", () => sendCommand({ type: "speed", idx }));
    els.speedButtons.appendChild(btn);
  });
}

function scheduleRender() {
  if (pendingFrame) return;
  pendingFrame = true;
  requestAnimationFrame(() => {
    pendingFrame = false;
    if (!lastState) return;
    drawGrid(lastState);
    drawChart(lastState);
    updateUi(lastState);
  });
}

function setConnectionState(state) {
  els.connection.classList.remove("is-connected", "is-disconnected");
  if (state === "connected") {
    els.connection.classList.add("is-connected");
    els.connection.querySelector(".label").textContent = "Connected";
  } else if (state === "disconnected") {
    els.connection.classList.add("is-disconnected");
    els.connection.querySelector(".label").textContent = "Reconnecting…";
  } else {
    els.connection.querySelector(".label").textContent = "Connecting…";
  }
}

function sendCommand(msg) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(msg));
  }
}

function connect() {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const url = `${proto}//${location.host}/ws`;
  setConnectionState("connecting");
  socket = new WebSocket(url);
  socket.addEventListener("open", () => setConnectionState("connected"));
  socket.addEventListener("close", () => {
    setConnectionState("disconnected");
    setTimeout(connect, 1000);
  });
  socket.addEventListener("message", async (event) => {
    let msg;
    try {
      msg = JSON.parse(event.data);
    } catch {
      return;
    }
    if (msg.type === "init") {
      config = msg.config;
      await loadAllSprites(config.buildings);
      if (lastState) scheduleRender();
    } else if (msg.type === "state") {
      lastState = msg.data;
      if (config) scheduleRender();
    }
  });
}

function bindControls() {
  document.querySelectorAll("[data-cmd]").forEach((btn) => {
    btn.addEventListener("click", () => {
      sendCommand({ type: btn.dataset.cmd });
    });
  });

  window.addEventListener("keydown", (event) => {
    if (event.target.matches("input, textarea")) return;
    if (event.code === "Space") {
      event.preventDefault();
      sendCommand({ type: "toggle" });
    } else if (event.key === "s" || event.key === "S") {
      sendCommand({ type: "save" });
    } else if (event.key === "r" || event.key === "R") {
      sendCommand({ type: "reset" });
    } else if (event.key >= "1" && event.key <= "6") {
      sendCommand({ type: "speed", idx: Number(event.key) - 1 });
    } else if (event.key === "ArrowRight" || event.key === "+") {
      sendCommand({ type: "speed", idx: Math.min(5, (lastState?.speedIdx ?? 1) + 1) });
    } else if (event.key === "ArrowLeft" || event.key === "-") {
      sendCommand({ type: "speed", idx: Math.max(0, (lastState?.speedIdx ?? 1) - 1) });
    }
  });

  window.addEventListener("resize", scheduleRender);
}

bindControls();
connect();
