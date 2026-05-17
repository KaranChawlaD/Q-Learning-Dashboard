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

const PALETTE_ITEMS = [
  { id: "agent", label: "Agent", sprite: "down", kind: "agent" },
  { id: "bank", label: "Bank", sprite: "bank", kind: "bank" },
  { id: "building_1", label: "Building 1", sprite: "building_1.png", kind: "building" },
  { id: "building_2", label: "Building 2", sprite: "building_2.png", kind: "building" },
  { id: "building_3", label: "Building 3", sprite: "building_3.png", kind: "building" },
];

const els = {
  status: document.getElementById("status-pill"),
  statusText: document.getElementById("status-text"),
  speedText: document.getElementById("speed-text"),
  subtitle: document.getElementById("subtitle"),
  connection: document.getElementById("connection"),
  gridTitle: document.getElementById("grid-title"),
  gridSubtitle: document.getElementById("grid-subtitle"),
  heatmapLegend: document.getElementById("heatmap-legend"),
  setupCard: document.getElementById("setup-card"),
  setupValidation: document.getElementById("setup-validation"),
  startTrainingBtn: document.getElementById("start-training-btn"),
  palette: document.getElementById("palette"),
  metricsCard: document.getElementById("metrics-card"),
  controlsCard: document.getElementById("controls-card"),
  chartCard: document.getElementById("chart-card"),
  metricEp: document.getElementById("metric-ep"),
  metricEps: document.getElementById("metric-eps"),
  metricLast: document.getElementById("metric-last"),
  metricAvg: document.getElementById("metric-avg"),
  legendMin: document.getElementById("legend-min"),
  legendMax: document.getElementById("legend-max"),
  toggleLabel: document.getElementById("toggle-label"),
  speedButtons: document.getElementById("speed-buttons"),
  chartSubtitle: document.getElementById("chart-subtitle"),
  testsCard: document.getElementById("tests-card"),
  testsSubtitle: document.getElementById("tests-subtitle"),
  testsSummary: document.getElementById("tests-summary"),
  testsList: document.getElementById("tests-list"),
  gridCanvas: document.getElementById("grid-canvas"),
  chartCanvas: document.getElementById("chart-canvas"),
  dragGhost: document.getElementById("drag-ghost"),
};

const sprites = {};
const buildingSprites = {};
let bankSprite = null;

let socket = null;
let config = null;
let displayEnv = null;
let lastState = null;
let pendingFrame = false;
let renderedTestsKey = null;
let uiMode = "setup";

const layoutDraft = {
  start: null,
  bank: null,
  buildings: {},
};

let dragState = null;

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

function cellKey(col, row) {
  return `${col},${row}`;
}

function loadImage(src) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => resolve(null);
    img.src = src;
  });
}

async function loadAllSprites() {
  for (const [key, src] of Object.entries(SPRITE_FILES)) {
    sprites[key] = await loadImage(src);
  }
  for (const file of config?.buildingFiles || []) {
    buildingSprites[file] = await loadImage(`/assets/elems/${file}`);
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

function canvasCellFromEvent(event, canvas, cols, rows) {
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  const col = Math.floor(x / TILE_SIZE);
  const row = Math.floor(y / TILE_SIZE);
  if (col < 0 || row < 0 || col >= cols || row >= rows) return null;
  return [col, row];
}

function draftEnvSnapshot() {
  const obstacles = Object.entries(layoutDraft.buildings)
    .filter(([, pos]) => pos)
    .map(([file, pos]) => ({ file, col: pos[0], row: pos[1] }));
  return {
    start: layoutDraft.start,
    bank: layoutDraft.bank,
    obstacles: obstacles.map((b) => [b.col, b.row]),
    buildings: obstacles,
  };
}

function applyDisplayEnv(env) {
  if (!env) {
    displayEnv = draftEnvSnapshot();
    return;
  }
  displayEnv = {
    start: env.start,
    bank: env.bank,
    obstacles: env.obstacles || [],
    buildings: env.buildings || [],
  };
}

function pieceAtCell(col, row) {
  if (layoutDraft.start && layoutDraft.start[0] === col && layoutDraft.start[1] === row) {
    return { kind: "agent" };
  }
  if (layoutDraft.bank && layoutDraft.bank[0] === col && layoutDraft.bank[1] === row) {
    return { kind: "bank" };
  }
  for (const [file, pos] of Object.entries(layoutDraft.buildings)) {
    if (pos && pos[0] === col && pos[1] === row) {
      return { kind: "building", file };
    }
  }
  return null;
}

function clearCell(col, row) {
  if (layoutDraft.start && layoutDraft.start[0] === col && layoutDraft.start[1] === row) {
    layoutDraft.start = null;
  }
  if (layoutDraft.bank && layoutDraft.bank[0] === col && layoutDraft.bank[1] === row) {
    layoutDraft.bank = null;
  }
  for (const file of Object.keys(layoutDraft.buildings)) {
    const pos = layoutDraft.buildings[file];
    if (pos && pos[0] === col && pos[1] === row) {
      delete layoutDraft.buildings[file];
    }
  }
}

function placePiece(kind, file, col, row) {
  clearCell(col, row);
  if (kind === "agent") {
    if (layoutDraft.start) clearCell(layoutDraft.start[0], layoutDraft.start[1]);
    layoutDraft.start = [col, row];
  } else if (kind === "bank") {
    if (layoutDraft.bank) clearCell(layoutDraft.bank[0], layoutDraft.bank[1]);
    layoutDraft.bank = [col, row];
  } else if (kind === "building" && file) {
    const old = layoutDraft.buildings[file];
    if (old) clearCell(old[0], old[1]);
    layoutDraft.buildings[file] = [col, row];
  }
  updateSetupValidation();
  refreshPalette();
  scheduleRender();
}

function removePiece(kind, file) {
  if (kind === "agent") layoutDraft.start = null;
  else if (kind === "bank") layoutDraft.bank = null;
  else if (kind === "building" && file) delete layoutDraft.buildings[file];
  updateSetupValidation();
  refreshPalette();
  scheduleRender();
}

function updateSetupValidation(message) {
  const hasAgent = layoutDraft.start !== null;
  const hasBank = layoutDraft.bank !== null;
  const ready = hasAgent && hasBank;

  if (message) {
    els.setupValidation.textContent = message;
    els.setupValidation.classList.toggle("is-error", !ready);
    els.setupValidation.classList.toggle("is-ready", ready);
  } else if (!hasAgent && !hasBank) {
    els.setupValidation.textContent = "Place an agent and bank on the grid to begin.";
    els.setupValidation.classList.remove("is-error", "is-ready");
  } else if (!hasAgent) {
    els.setupValidation.textContent = "Add an agent (start position) to the grid.";
    els.setupValidation.classList.add("is-error");
    els.setupValidation.classList.remove("is-ready");
  } else if (!hasBank) {
    els.setupValidation.textContent = "Add a bank (goal) to the grid.";
    els.setupValidation.classList.add("is-error");
    els.setupValidation.classList.remove("is-ready");
  } else {
    els.setupValidation.textContent = "Ready — press Start Training when your layout looks good.";
    els.setupValidation.classList.remove("is-error");
    els.setupValidation.classList.add("is-ready");
  }

  els.startTrainingBtn.disabled = !ready;
}

function drawEnvTiles(ctx, env, cols, rows, options = {}) {
  const { heatmap = false, state = null } = options;
  const obstacleSet = new Set((env.obstacles || []).map((o) => cellKey(o[0], o[1])));
  const bankKey = env.bank ? cellKey(env.bank[0], env.bank[1]) : null;
  const span = heatmap && state ? state.vmax - state.vmin || 1 : 1;

  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) {
      const tx = col * TILE_SIZE + TILE_GAP / 2;
      const ty = row * TILE_SIZE + TILE_GAP / 2;
      const tw = TILE_SIZE - TILE_GAP;
      const th = TILE_SIZE - TILE_GAP;
      const key = cellKey(col, row);

      if (obstacleSet.has(key)) {
        ctx.fillStyle = "#1c2131";
      } else if (bankKey && key === bankKey) {
        ctx.fillStyle = heatmap ? "#34d399" : "#1f3d34";
      } else if (heatmap && state) {
        const idx = row * cols + col;
        const v = state.v[idx];
        const t = (v - state.vmin) / span;
        ctx.fillStyle = rgb(plasma(t));
      } else {
        ctx.fillStyle = "#1a2032";
      }
      roundedRect(ctx, tx, ty, tw, th, TILE_RADIUS);
      ctx.fill();
    }
  }
}

function drawSpritesOnGrid(ctx, env, agentOverride) {
  for (const b of env.buildings || []) {
    const img = buildingSprites[b.file];
    if (img) {
      ctx.drawImage(img, b.col * TILE_SIZE, b.row * TILE_SIZE, TILE_SIZE, TILE_SIZE);
    }
  }
  if (env.bank && bankSprite) {
    ctx.drawImage(
      bankSprite,
      env.bank[0] * TILE_SIZE,
      env.bank[1] * TILE_SIZE,
      TILE_SIZE,
      TILE_SIZE,
    );
  }
  const agent = agentOverride || (env.start ? { col: env.start[0], row: env.start[1], facing: "down" } : null);
  if (agent) {
    const ax = agent.col * TILE_SIZE;
    const ay = agent.row * TILE_SIZE;
    ctx.strokeStyle = "#38bdf8";
    ctx.lineWidth = 2;
    roundedRect(ctx, ax + 1, ay + 1, TILE_SIZE - 2, TILE_SIZE - 2, TILE_RADIUS);
    ctx.stroke();
    const sprite = sprites[agent.facing || "down"];
    if (sprite) {
      ctx.drawImage(sprite, ax, ay, TILE_SIZE, TILE_SIZE);
    }
  }
}

function drawSetupGrid() {
  if (!config) return;
  const cols = config.gridCols;
  const rows = config.gridRows;
  const w = cols * TILE_SIZE;
  const h = rows * TILE_SIZE;
  const ctx = setupCanvas(els.gridCanvas, w, h);
  ctx.clearRect(0, 0, w, h);

  const env = draftEnvSnapshot();
  applyDisplayEnv(null);
  drawEnvTiles(ctx, env, cols, rows);
  drawSpritesOnGrid(ctx, env);

  if (dragState && dragState.hoverCell) {
    const [col, row] = dragState.hoverCell;
    ctx.strokeStyle = "rgba(56, 189, 248, 0.85)";
    ctx.lineWidth = 2;
    ctx.setLineDash([4, 3]);
    roundedRect(ctx, col * TILE_SIZE + 2, row * TILE_SIZE + 2, TILE_SIZE - 4, TILE_SIZE - 4, TILE_RADIUS);
    ctx.stroke();
    ctx.setLineDash([]);
  }
}

function drawTrainingGrid(state) {
  if (!config || !displayEnv) return;
  const cols = config.gridCols;
  const rows = config.gridRows;
  const w = cols * TILE_SIZE;
  const h = rows * TILE_SIZE;
  const ctx = setupCanvas(els.gridCanvas, w, h);
  ctx.clearRect(0, 0, w, h);

  const obstacleSet = new Set((displayEnv.obstacles || []).map((o) => cellKey(o[0], o[1])));
  const bankKey = displayEnv.bank ? cellKey(displayEnv.bank[0], displayEnv.bank[1]) : null;
  const span = state.vmax - state.vmin || 1;

  drawEnvTiles(ctx, displayEnv, cols, rows, { heatmap: true, state });

  ctx.fillStyle = "rgba(245, 247, 255, 0.82)";
  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) {
      const key = cellKey(col, row);
      if (obstacleSet.has(key) || (bankKey && key === bankKey)) continue;
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

  drawSpritesOnGrid(ctx, displayEnv, state.agent);
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
  els.status.classList.remove("is-training", "is-paused", "is-done", "is-setup");
  els.status.classList.add(klass);
}

function setPanelMode(mode) {
  uiMode = mode;
  const isSetup = mode === "setup";

  els.setupCard.classList.toggle("hidden", !isSetup);
  els.metricsCard.classList.toggle("hidden", isSetup);
  els.metricsCard.setAttribute("aria-hidden", isSetup ? "true" : "false");
  els.controlsCard.classList.toggle("hidden", isSetup);
  els.controlsCard.setAttribute("aria-hidden", isSetup ? "true" : "false");
  els.chartCard.classList.toggle("hidden", isSetup);
  els.chartCard.setAttribute("aria-hidden", isSetup ? "true" : "false");
  els.speedText.classList.toggle("hidden", isSetup);
  els.heatmapLegend.classList.toggle("hidden", isSetup);

  if (isSetup) {
    els.gridTitle.textContent = "Environment";
    els.gridSubtitle.textContent = "Drag pieces from the panel onto the grid";
    setStatus("SETUP", "is-setup");
    els.subtitle.textContent = "Design your gridworld, then train";
  } else {
    els.gridTitle.textContent = "Policy Heatmap";
    els.gridSubtitle.textContent = "max Q(s, a) per tile · arrows show greedy action";
  }
}

function formatTestDetails(details) {
  if (!details) return "";
  if (details.path) {
    return details.path.map((c) => `(${c[0]}, ${c[1]})`).join(" -> ");
  }
  return JSON.stringify(details, null, 2);
}

function renderModelTests(modelTests) {
  if (!modelTests) {
    els.testsCard.classList.add("hidden");
    els.testsCard.setAttribute("aria-hidden", "true");
    renderedTestsKey = null;
    return;
  }

  const key = JSON.stringify(modelTests.tests.map((t) => [t.id, t.passed, t.actual]));
  if (key === renderedTestsKey) {
    els.testsCard.classList.remove("hidden");
    els.testsCard.setAttribute("aria-hidden", "false");
    return;
  }
  renderedTestsKey = key;

  els.testsCard.classList.remove("hidden");
  els.testsCard.setAttribute("aria-hidden", "false");

  const { passed, total, allPassed } = modelTests;
  els.testsSummary.textContent = `${passed}/${total} passed`;
  els.testsSummary.classList.remove("is-pass", "is-fail");
  els.testsSummary.classList.add(allPassed ? "is-pass" : "is-fail");
  els.testsSubtitle.textContent = allPassed
    ? "All checks passed — greedy policy is ready"
    : "Some checks failed — expand a case to inspect expected vs actual";

  els.testsList.innerHTML = "";
  modelTests.tests.forEach((test, index) => {
    const item = document.createElement("article");
    item.className = `test-case ${test.passed ? "is-pass" : "is-fail"}`;
    item.setAttribute("role", "listitem");

    const head = document.createElement("button");
    head.type = "button";
    head.className = "test-case-head";
    head.setAttribute("aria-expanded", "false");
    head.innerHTML = `
      <svg class="test-case-chevron" viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <path d="M6 4l4 4-4 4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <span class="test-case-status ${test.passed ? "is-pass" : "is-fail"}" aria-hidden="true">
        ${test.passed ? "✓" : "✕"}
      </span>
      <span class="test-case-title">${test.name}</span>
      <span class="test-case-index">Case ${index + 1}</span>
    `;

    const body = document.createElement("div");
    body.className = "test-case-body";
    body.innerHTML = `
      <p class="test-case-desc">${test.description}</p>
      <div class="test-case-io">
        <div class="test-io-row">
          <span class="test-io-label">Expected</span>
          <p class="test-io-value">${test.expected}</p>
        </div>
        <div class="test-io-row">
          <span class="test-io-label">Actual</span>
          <p class="test-io-value ${test.passed ? "is-pass" : "is-fail"}">${test.actual}</p>
        </div>
        ${
          test.details
            ? `<div class="test-io-row">
          <span class="test-io-label">Details</span>
          <p class="test-io-value">${formatTestDetails(test.details)}</p>
        </div>`
            : ""
        }
      </div>
    `;

    head.addEventListener("click", () => {
      const open = item.classList.toggle("is-open");
      head.setAttribute("aria-expanded", open ? "true" : "false");
    });

    item.appendChild(head);
    item.appendChild(body);
    els.testsList.appendChild(item);
  });
}

function updateUi(state) {
  if (state.mode === "setup") {
    setPanelMode("setup");
    updateSetupValidation();
    return;
  }

  setPanelMode("training");
  applyDisplayEnv(state.env);
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
    renderModelTests(state.modelTests);
  } else {
    els.testsCard.classList.add("hidden");
    els.testsCard.setAttribute("aria-hidden", "true");
    renderedTestsKey = null;
    if (state.paused) {
      setStatus("PAUSED", "is-paused");
      els.toggleLabel.textContent = "Resume training";
    } else {
      setStatus("TRAINING", "is-training");
      els.toggleLabel.textContent = "Pause training";
    }
  }

  const optimum = displayEnv?.start && displayEnv?.bank
    ? Math.abs(displayEnv.bank[0] - displayEnv.start[0]) +
      Math.abs(displayEnv.bank[1] - displayEnv.start[1]) +
      6
    : 25;

  if (state.lengths.length >= 100 && state.avg100 < optimum) {
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
    const mode = lastState?.mode || uiMode;
    if (mode === "setup") {
      drawSetupGrid();
    } else if (lastState) {
      drawTrainingGrid(lastState);
      drawChart(lastState);
      updateUi(lastState);
    }
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

function startTrainingFromDraft() {
  if (!layoutDraft.start || !layoutDraft.bank) {
    updateSetupValidation("Place an agent and bank on the grid before training.");
    return;
  }
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    updateSetupValidation("Not connected to the server — wait for the connection indicator.");
    return;
  }
  const obstacles = Object.values(layoutDraft.buildings).filter(Boolean);
  els.startTrainingBtn.disabled = true;
  els.startTrainingBtn.textContent = "Starting…";
  sendCommand({
    type: "start_training",
    start: layoutDraft.start,
    bank: layoutDraft.bank,
    obstacles,
  });
}

function paletteThumbHtml(item) {
  if (item.kind === "agent") {
    return `<img src="${SPRITE_FILES.down}" alt="" draggable="false" />`;
  }
  if (item.kind === "bank") {
    return `<img src="/assets/elems/bank.png" alt="" draggable="false" />`;
  }
  return `<img src="/assets/elems/${item.sprite}" alt="" draggable="false" />`;
}

function visiblePaletteItems() {
  return PALETTE_ITEMS.filter((item) => {
    if (item.kind === "agent") return layoutDraft.start === null;
    if (item.kind === "bank") return layoutDraft.bank === null;
    return true;
  });
}

function refreshPalette() {
  els.palette.innerHTML = "";
  for (const item of visiblePaletteItems()) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "palette-item";
    chip.dataset.kind = item.kind;
    chip.dataset.file = item.sprite || "";
    chip.setAttribute("role", "listitem");
    chip.innerHTML = `
      <span class="palette-thumb">${paletteThumbHtml(item)}</span>
      <span class="palette-label">${item.label}</span>
    `;
    chip.addEventListener("pointerdown", (event) => beginDrag(event, item));
    els.palette.appendChild(chip);
  }
}

function buildPalette() {
  refreshPalette();
}

function beginDrag(event, item) {
  if (event.button !== 0) return;
  event.preventDefault();
  dragState = {
    kind: item.kind,
    file: item.kind === "building" ? item.sprite : null,
    fromGrid: false,
    hoverCell: null,
  };
  showDragGhost(item, event.clientX, event.clientY);
  chipActive(event.currentTarget);
}

function chipActive(el) {
  for (const chip of els.palette.querySelectorAll(".palette-item")) {
    chip.classList.toggle("is-active", chip === el);
  }
}

function showDragGhost(item, x, y) {
  els.dragGhost.classList.remove("hidden");
  els.dragGhost.innerHTML = paletteThumbHtml(item);
  moveDragGhost(x, y);
}

function moveDragGhost(x, y) {
  els.dragGhost.style.left = `${x}px`;
  els.dragGhost.style.top = `${y}px`;
}

function hideDragGhost() {
  els.dragGhost.classList.add("hidden");
  els.dragGhost.innerHTML = "";
  for (const chip of els.palette.querySelectorAll(".palette-item")) {
    chip.classList.remove("is-active");
  }
}

function onPointerMove(event) {
  if (!dragState) return;
  moveDragGhost(event.clientX, event.clientY);
  if (!config) return;
  const cell = canvasCellFromEvent(event, els.gridCanvas, config.gridCols, config.gridRows);
  dragState.hoverCell = cell;
  scheduleRender();
}

function onPointerUp(event) {
  if (!dragState) return;
  const cell = canvasCellFromEvent(event, els.gridCanvas, config.gridCols, config.gridRows);
  if (cell && uiMode === "setup") {
    if (event.altKey && dragState.fromGrid) {
      removePiece(dragState.kind, dragState.file);
    } else {
      placePiece(dragState.kind, dragState.file, cell[0], cell[1]);
    }
  }
  dragState = null;
  hideDragGhost();
  scheduleRender();
}

function onGridPointerDown(event) {
  if (uiMode !== "setup" || event.button !== 0) return;
  const cell = canvasCellFromEvent(event, els.gridCanvas, config.gridCols, config.gridRows);
  if (!cell) return;
  const piece = pieceAtCell(cell[0], cell[1]);
  if (!piece) return;
  event.preventDefault();
  dragState = {
    kind: piece.kind,
    file: piece.file || null,
    fromGrid: true,
    hoverCell: cell,
  };
  const item = PALETTE_ITEMS.find(
    (p) =>
      (p.kind === piece.kind && p.kind !== "building") ||
      (p.kind === "building" && p.sprite === piece.file),
  );
  if (item) showDragGhost(item, event.clientX, event.clientY);
  clearCell(cell[0], cell[1]);
  refreshPalette();
  updateSetupValidation();
  scheduleRender();
}

function onGridContextMenu(event) {
  if (uiMode !== "setup") return;
  event.preventDefault();
  const cell = canvasCellFromEvent(event, els.gridCanvas, config.gridCols, config.gridRows);
  if (!cell) return;
  clearCell(cell[0], cell[1]);
  refreshPalette();
  updateSetupValidation();
  scheduleRender();
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
      await loadAllSprites();
      buildPalette();
      setPanelMode("setup");
      updateSetupValidation();
      scheduleRender();
    } else if (msg.type === "error") {
      els.startTrainingBtn.disabled = false;
      els.startTrainingBtn.textContent = "Start Training";
      updateSetupValidation(msg.message || "Could not start training.");
    } else if (msg.type === "state") {
      lastState = msg.data;
      if (lastState.mode === "setup") {
        setPanelMode("setup");
        els.startTrainingBtn.textContent = "Start Training";
        refreshPalette();
        updateSetupValidation();
        scheduleRender();
      } else if (config) {
        setPanelMode("training");
        applyDisplayEnv(lastState.env);
        scheduleRender();
      }
    }
  });
}

function bindControls() {
  document.querySelectorAll("[data-cmd]").forEach((btn) => {
    btn.addEventListener("click", () => {
      sendCommand({ type: btn.dataset.cmd });
    });
  });

  els.startTrainingBtn.addEventListener("click", startTrainingFromDraft);

  els.gridCanvas.addEventListener("pointerdown", onGridPointerDown);
  els.gridCanvas.addEventListener("contextmenu", onGridContextMenu);
  window.addEventListener("pointermove", onPointerMove);
  window.addEventListener("pointerup", onPointerUp);
  window.addEventListener("pointercancel", onPointerUp);

  window.addEventListener("keydown", (event) => {
    if (event.target.matches("input, textarea, button")) return;
    if (uiMode !== "training") return;
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
