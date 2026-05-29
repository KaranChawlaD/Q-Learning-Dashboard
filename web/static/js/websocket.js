import { sendCommand } from "./commands.js";
import { els } from "./dom.js";
import {
  applyHyperparameterDefaults,
  bindHyperparameterLab,
  readHyperparameterPayload,
  setHyperparameterError,
} from "./hyperparams.js";
import { applyDisplayEnv, normalizeBuildingsDraft, updateSetupValidation } from "./layout.js";
import { buildPalette, refreshPalette } from "./setup-editor.js";
import { loadAllSprites } from "./sprites.js";
import { requestRender, setConnectionState, setPanelMode } from "./ui.js";
import { appState } from "./state.js";

function resetStartTrainingButton() {
  els.startTrainingBtn.disabled = false;
  els.startTrainingBtn.textContent = "Start Training";
}

export function startTrainingFromDraft() {
  try {
    const { layoutDraft } = appState;
    if (!layoutDraft.start || !layoutDraft.bank) {
      updateSetupValidation("Place an agent and bank on the grid before training.");
      return;
    }
    if (!appState.socket || appState.socket.readyState !== WebSocket.OPEN) {
      updateSetupValidation("Not connected to the server — wait for the connection indicator.");
      return;
    }
    const buildingPlacements = normalizeBuildingsDraft().map((b) => ({
      file: b.file,
      col: b.col,
      row: b.row,
    }));
    const hp = readHyperparameterPayload();
    if (!hp.ok) {
      const message = hp.message || "Invalid hyperparameters.";
      setHyperparameterError(message);
      updateSetupValidation(message);
      return;
    }
    els.startTrainingBtn.disabled = true;
    els.startTrainingBtn.textContent = "Starting…";
    const sent = sendCommand({
      type: "start_training",
      start: layoutDraft.start,
      bank: layoutDraft.bank,
      obstacles: buildingPlacements.map((b) => [b.col, b.row]),
      building_placements: buildingPlacements,
      train_config: hp.payload,
    });
    if (!sent) {
      resetStartTrainingButton();
      updateSetupValidation("Not connected to the server — wait for the connection indicator.");
    }
  } catch (err) {
    console.error("[start_training]", err);
    resetStartTrainingButton();
    updateSetupValidation("Could not start training — refresh the page and try again.");
  }
}

export function connect() {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const url = `${proto}//${location.host}/ws`;
  setConnectionState("connecting");
  appState.socket = new WebSocket(url);
  appState.socket.addEventListener("open", () => setConnectionState("connected"));
  appState.socket.addEventListener("close", () => {
    setConnectionState("disconnected");
    setTimeout(connect, 1000);
  });
  appState.socket.addEventListener("message", async (event) => {
    let msg;
    try {
      msg = JSON.parse(event.data);
    } catch {
      return;
    }
    if (msg.type === "init") {
      appState.config = msg.config;
      normalizeBuildingsDraft();
      await loadAllSprites();
      buildPalette();
      bindHyperparameterLab();
      applyHyperparameterDefaults(msg.config.trainConfig);
      setPanelMode("setup");
      updateSetupValidation();
      requestRender();
    } else if (msg.type === "error") {
      resetStartTrainingButton();
      updateSetupValidation(msg.message || "Could not start training.");
    } else if (msg.type === "state") {
      appState.lastState = msg.data;
      if (appState.lastState.mode === "setup") {
        setPanelMode("setup");
        els.startTrainingBtn.textContent = "Start Training";
        refreshPalette();
        updateSetupValidation();
        requestRender();
      } else if (appState.config) {
        setPanelMode("training");
        applyDisplayEnv(appState.lastState.env);
        requestRender();
      }
    }
  });
}
