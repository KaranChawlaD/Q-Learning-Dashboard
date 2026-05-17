import { drawChart } from "./chart.js";
import { drawSetupGrid, drawTrainingGrid } from "./grid.js";
import { appState } from "./state.js";

let updateUiFn = null;

/** Register UI updater to avoid circular imports between render-loop and ui. */
export function setUpdateUi(fn) {
  updateUiFn = fn;
}

export function requestRender() {
  if (appState.pendingFrame) return;
  appState.pendingFrame = true;
  requestAnimationFrame(() => {
    appState.pendingFrame = false;
    const mode = appState.lastState?.mode || appState.uiMode;
    if (mode === "setup") {
      drawSetupGrid();
    } else if (appState.lastState) {
      drawTrainingGrid(appState.lastState);
      drawChart(appState.lastState);
      updateUiFn?.(appState.lastState);
    }
  });
}
