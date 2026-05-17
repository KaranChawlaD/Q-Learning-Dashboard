import { els } from "./dom.js";
import { applyDisplayEnv, updateSetupValidation } from "./layout.js";
import { renderModelTests } from "./model-tests.js";
import { requestRender, setUpdateUi } from "./render-loop.js";
import { sendCommand } from "./commands.js";
import { appState } from "./state.js";

export function setStatus(text, klass) {
  els.statusText.textContent = text;
  els.status.classList.remove("is-training", "is-paused", "is-done", "is-setup");
  els.status.classList.add(klass);
}

export function setPanelMode(mode) {
  appState.uiMode = mode;
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

export function updateUi(trainingState) {
  if (trainingState.mode === "setup") {
    setPanelMode("setup");
    updateSetupValidation();
    return;
  }

  setPanelMode("training");
  applyDisplayEnv(trainingState.env);
  setupSpeedButtons(trainingState.speedLevels);
  els.speedText.textContent = `${trainingState.speed} steps / frame`;
  els.metricEp.textContent = `${trainingState.ep} / ${trainingState.totalEps}`;
  els.metricEps.textContent = trainingState.eps.toFixed(3);
  els.metricLast.textContent = trainingState.lastLen ? `${trainingState.lastLen} steps` : "— steps";
  els.metricAvg.textContent = trainingState.avg100 ? trainingState.avg100.toFixed(1) : "—";
  els.legendMin.textContent = `${trainingState.vmin >= 0 ? "+" : ""}${trainingState.vmin.toFixed(1)}`;
  els.legendMax.textContent = `${trainingState.vmax >= 0 ? "+" : ""}${trainingState.vmax.toFixed(1)}`;

    if (trainingState.finished) {
    setStatus("DONE", "is-done");
    els.subtitle.textContent = `Trained ${trainingState.totalEps} episodes · agent at ${trainingState.agent.col}, ${trainingState.agent.row}`;
    els.toggleLabel.textContent = "Restart training (Space)";
    renderModelTests(trainingState.modelTests);
  } else {
    els.testsCard.classList.add("hidden");
    els.testsCard.setAttribute("aria-hidden", "true");
    appState.renderedTestsKey = null;
    if (trainingState.paused) {
      setStatus("PAUSED", "is-paused");
      els.toggleLabel.textContent = "Resume training";
    } else {
      setStatus("TRAINING", "is-training");
      els.toggleLabel.textContent = "Pause training";
    }
  }

  const env = appState.displayEnv;
  const optimum =
    env?.start && env?.bank
      ? Math.abs(env.bank[0] - env.start[0]) + Math.abs(env.bank[1] - env.start[1]) + 6
      : 25;

  if (trainingState.lengths.length >= 100 && trainingState.avg100 < optimum) {
    els.chartSubtitle.classList.add("is-converged");
    els.chartSubtitle.textContent = `Lower is better · Converged near optimum (${trainingState.avg100.toFixed(1)} steps)`;
  } else {
    els.chartSubtitle.classList.remove("is-converged");
    els.chartSubtitle.textContent = "Lower is better";
  }

  for (const btn of els.speedButtons.querySelectorAll("button")) {
    btn.classList.toggle("active", Number(btn.dataset.idx) === trainingState.speedIdx);
  }
}

setUpdateUi(updateUi);

export function setConnectionState(connectionState) {
  els.connection.classList.remove("is-connected", "is-disconnected");
  if (connectionState === "connected") {
    els.connection.classList.add("is-connected");
    els.connection.querySelector(".label").textContent = "Connected";
  } else if (connectionState === "disconnected") {
    els.connection.classList.add("is-disconnected");
    els.connection.querySelector(".label").textContent = "Reconnecting…";
  } else {
    els.connection.querySelector(".label").textContent = "Connecting…";
  }
}

export { requestRender };
