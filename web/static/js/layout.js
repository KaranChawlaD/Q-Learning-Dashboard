import { els } from "./dom.js";
import { appState } from "./state.js";

/** Ensure layout draft buildings are always a list (handles stale session shapes). */
export function normalizeBuildingsDraft() {
  const { layoutDraft } = appState;
  if (!Array.isArray(layoutDraft.buildings)) {
    const legacy = layoutDraft.buildings;
    layoutDraft.buildings = legacy && typeof legacy === "object"
      ? Object.entries(legacy)
          .filter(([, pos]) => Array.isArray(pos) && pos.length >= 2)
          .map(([file, pos], index) => ({
            id: `building-legacy-${index}`,
            file,
            col: pos[0],
            row: pos[1],
          }))
      : [];
  }
  return layoutDraft.buildings;
}

export function draftEnvSnapshot() {
  const { layoutDraft } = appState;
  const buildings = normalizeBuildingsDraft().map((b) => ({
    file: b.file,
    col: b.col,
    row: b.row,
  }));
  return {
    start: layoutDraft.start,
    bank: layoutDraft.bank,
    obstacles: buildings.map((b) => [b.col, b.row]),
    buildings,
  };
}

export function applyDisplayEnv(env) {
  if (!env) {
    appState.displayEnv = draftEnvSnapshot();
    return;
  }
  appState.displayEnv = {
    start: env.start,
    bank: env.bank,
    obstacles: env.obstacles || [],
    buildings: env.buildings || [],
  };
}

export function pieceAtCell(col, row) {
  const { layoutDraft } = appState;
  if (layoutDraft.start && layoutDraft.start[0] === col && layoutDraft.start[1] === row) {
    return { kind: "agent" };
  }
  if (layoutDraft.bank && layoutDraft.bank[0] === col && layoutDraft.bank[1] === row) {
    return { kind: "bank" };
  }
  const building = normalizeBuildingsDraft().find((b) => b.col === col && b.row === row);
  if (building) {
    return { kind: "building", file: building.file, id: building.id };
  }
  return null;
}

export function clearCell(col, row) {
  const { layoutDraft } = appState;
  if (layoutDraft.start && layoutDraft.start[0] === col && layoutDraft.start[1] === row) {
    layoutDraft.start = null;
  }
  if (layoutDraft.bank && layoutDraft.bank[0] === col && layoutDraft.bank[1] === row) {
    layoutDraft.bank = null;
  }
  layoutDraft.buildings = normalizeBuildingsDraft().filter((b) => b.col !== col || b.row !== row);
}

export function updateSetupValidation(message) {
  const hasAgent = appState.layoutDraft.start !== null;
  const hasBank = appState.layoutDraft.bank !== null;
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
