import { sendCommand } from "./commands.js";
import { els } from "./dom.js";
import { applyDisplayEnv, updateSetupValidation } from "./layout.js";
import { buildPalette, refreshPalette } from "./setup-editor.js";
import { loadAllSprites } from "./sprites.js";
import { requestRender, setConnectionState, setPanelMode } from "./ui.js";
import { appState } from "./state.js";

export function startTrainingFromDraft() {
  const { layoutDraft } = appState;
  if (!layoutDraft.start || !layoutDraft.bank) {
    updateSetupValidation("Place an agent and bank on the grid before training.");
    return;
  }
  if (!appState.socket || appState.socket.readyState !== WebSocket.OPEN) {
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
      await loadAllSprites();
      buildPalette();
      setPanelMode("setup");
      updateSetupValidation();
      requestRender();
    } else if (msg.type === "error") {
      els.startTrainingBtn.disabled = false;
      els.startTrainingBtn.textContent = "Start Training";
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
