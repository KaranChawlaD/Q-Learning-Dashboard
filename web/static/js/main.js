/** Dashboard entry point — wires DOM events and opens the WebSocket. */

import { els } from "./dom.js";
import {
  bindSetupEditor,
  onGridContextMenu,
  onGridPointerDown,
} from "./setup-editor.js";
import { requestRender } from "./ui.js";
import { sendCommand } from "./commands.js";
import { connect, startTrainingFromDraft } from "./websocket.js";
import { appState } from "./state.js";

function bindControls() {
  document.querySelectorAll("[data-cmd]").forEach((btn) => {
    btn.addEventListener("click", () => {
      sendCommand({ type: btn.dataset.cmd });
    });
  });

  els.startTrainingBtn.addEventListener("click", startTrainingFromDraft);
  els.gridCanvas.addEventListener("pointerdown", onGridPointerDown);
  els.gridCanvas.addEventListener("contextmenu", onGridContextMenu);

  window.addEventListener("keydown", (event) => {
    if (event.target.matches("input, textarea, button")) return;
    if (appState.uiMode !== "training") return;
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
      sendCommand({ type: "speed", idx: Math.min(5, (appState.lastState?.speedIdx ?? 1) + 1) });
    } else if (event.key === "ArrowLeft" || event.key === "-") {
      sendCommand({ type: "speed", idx: Math.max(0, (appState.lastState?.speedIdx ?? 1) - 1) });
    }
  });

  window.addEventListener("resize", requestRender);
}

bindSetupEditor();
bindControls();
connect();
