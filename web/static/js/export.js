/** Export and import of training run JSON snapshots. */

import { applyHyperparameterDefaults } from "./hyperparams.js";
import { syncLayoutDraftFromEnv, updateSetupValidation } from "./layout.js";
import { refreshPalette } from "./setup-editor.js";
import { requestRender, setPanelMode } from "./ui.js";
import { appState } from "./state.js";

export function downloadRunExport(data) {
  const stamp = data.exported_at?.slice(0, 19).replace(/[:T]/g, "-") ?? "run";
  const filename = `qlearning-run-${stamp}.json`;
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function requestRunExport(sendCommand) {
  return sendCommand({ type: "export" });
}

/** @param {unknown} data */
export function validateRunExport(data, gridCols = 12, gridRows = 9) {
  if (!data || typeof data !== "object") {
    return { ok: false, message: "Invalid JSON — expected an object." };
  }
  const run = /** @type {Record<string, unknown>} */ (data);
  if (run.version !== 1) {
    return { ok: false, message: "Unsupported export version (expected version 1)." };
  }
  const cols = Number(run.grid_cols ?? gridCols);
  const rows = Number(run.grid_rows ?? gridRows);
  if (cols !== gridCols || rows !== gridRows) {
    return {
      ok: false,
      message: `Grid size must be ${gridCols}×${gridRows} (file has ${cols}×${rows}).`,
    };
  }
  const layout = run.layout;
  if (!layout || typeof layout !== "object") {
    return { ok: false, message: "Missing layout object." };
  }
  const layoutObj = /** @type {Record<string, unknown>} */ (layout);
  if (!Array.isArray(layoutObj.start) || !Array.isArray(layoutObj.bank)) {
    return { ok: false, message: "Layout must include start and bank coordinates." };
  }
  const config = run.config;
  if (!config || typeof config !== "object") {
    return { ok: false, message: "Missing config object." };
  }
  return { ok: true, message: "" };
}

/**
 * @param {File} file
 * @returns {Promise<Record<string, unknown>>}
 */
export function readRunExportFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const data = JSON.parse(String(reader.result));
        resolve(data);
      } catch {
        reject(new Error("Could not parse JSON file."));
      }
    };
    reader.onerror = () => reject(new Error("Could not read file."));
    reader.readAsText(file);
  });
}

/** @param {ReturnType<typeof import("./dom.js")["els"]>} elsRef */
export function bindRunImport(elsRef, sendCommand) {
  elsRef.importRunInput.addEventListener("change", async (event) => {
    const input = /** @type {HTMLInputElement} */ (event.target);
    const file = input.files?.[0];
    input.value = "";
    if (!file) return;

    if (!appState.socket || appState.socket.readyState !== WebSocket.OPEN) {
      updateSetupValidation("Not connected to the server — wait for the connection indicator.");
      return;
    }

    try {
      const data = await readRunExportFile(file);
      const gridCols = appState.config?.gridCols ?? 12;
      const gridRows = appState.config?.gridRows ?? 9;
      const check = validateRunExport(data, gridCols, gridRows);
      if (!check.ok) {
        updateSetupValidation(check.message);
        return;
      }
      const sent = sendCommand({ type: "import_run", run: data });
      if (!sent) {
        updateSetupValidation("Not connected to the server — wait for the connection indicator.");
      }
    } catch (err) {
      updateSetupValidation(err instanceof Error ? err.message : "Could not import file.");
    }
  });
}

/** Apply layout-only import payload from the server (setup mode). */
export function applyImportedSetup(data) {
  if (data.train_config) {
    applyHyperparameterDefaults(data.train_config);
  }
  if (data.layout) {
    syncLayoutDraftFromEnv(data.layout);
  }
  setPanelMode("setup");
  refreshPalette();
  updateSetupValidation("Imported layout — press Start Training to run again.");
  requestRender();
}

export function promptRunImport(elsRef) {
  elsRef.importRunInput.click();
}
