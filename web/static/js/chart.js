import { setupCanvas, niceCeil } from "./canvas.js";
import { els } from "./dom.js";

export function drawChart(trainingState) {
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

  const lengths = trainingState.lengths || [];
  const totalEps = trainingState.totalEps || 5000;
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
