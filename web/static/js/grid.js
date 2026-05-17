import {
  ACTION_DELTAS,
  TILE_GAP,
  TILE_RADIUS,
  TILE_SIZE,
} from "./constants.js";
import { cellKey, roundedRect, setupCanvas } from "./canvas.js";
import { plasma, rgb } from "./color.js";
import { els } from "./dom.js";
import { applyDisplayEnv, draftEnvSnapshot } from "./layout.js";
import { appState } from "./state.js";

function drawEnvTiles(ctx, env, cols, rows, options = {}) {
  const { heatmap = false, heatmapState = null } = options;
  const obstacleSet = new Set((env.obstacles || []).map((o) => cellKey(o[0], o[1])));
  const bankKey = env.bank ? cellKey(env.bank[0], env.bank[1]) : null;
  const span = heatmap && heatmapState ? heatmapState.vmax - heatmapState.vmin || 1 : 1;

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
      } else if (heatmap && heatmapState) {
        const idx = row * cols + col;
        const v = heatmapState.v[idx];
        const t = (v - heatmapState.vmin) / span;
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
  const { sprites, buildingSprites, bankSprite } = appState;
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
  const agent =
    agentOverride ||
    (env.start ? { col: env.start[0], row: env.start[1], facing: "down" } : null);
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

export function drawSetupGrid() {
  const { config, dragState } = appState;
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

  if (dragState?.hoverCell) {
    const [col, row] = dragState.hoverCell;
    ctx.strokeStyle = "rgba(56, 189, 248, 0.85)";
    ctx.lineWidth = 2;
    ctx.setLineDash([4, 3]);
    roundedRect(ctx, col * TILE_SIZE + 2, row * TILE_SIZE + 2, TILE_SIZE - 4, TILE_SIZE - 4, TILE_RADIUS);
    ctx.stroke();
    ctx.setLineDash([]);
  }
}

export function drawTrainingGrid(trainingState) {
  const { config, displayEnv } = appState;
  if (!config || !displayEnv) return;
  const cols = config.gridCols;
  const rows = config.gridRows;
  const w = cols * TILE_SIZE;
  const h = rows * TILE_SIZE;
  const ctx = setupCanvas(els.gridCanvas, w, h);
  ctx.clearRect(0, 0, w, h);

  const obstacleSet = new Set((displayEnv.obstacles || []).map((o) => cellKey(o[0], o[1])));
  const bankKey = displayEnv.bank ? cellKey(displayEnv.bank[0], displayEnv.bank[1]) : null;

  drawEnvTiles(ctx, displayEnv, cols, rows, { heatmap: true, heatmapState: trainingState });

  ctx.fillStyle = "rgba(245, 247, 255, 0.82)";
  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) {
      const key = cellKey(col, row);
      if (obstacleSet.has(key) || (bankKey && key === bankKey)) continue;
      const idx = row * cols + col;
      const v = trainingState.v[idx];
      if (v === 0) continue;
      const action = trainingState.best[idx];
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

  drawSpritesOnGrid(ctx, displayEnv, trainingState.agent);
}
