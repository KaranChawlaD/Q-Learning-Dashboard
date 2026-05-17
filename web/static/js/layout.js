import { els } from "./dom.js";
import { appState } from "./state.js";

export function draftEnvSnapshot() {
  const obstacles = Object.entries(appState.layoutDraft.buildings)
    .filter(([, pos]) => pos)
    .map(([file, pos]) => ({ file, col: pos[0], row: pos[1] }));
  return {
    start: appState.layoutDraft.start,
    bank: appState.layoutDraft.bank,
    obstacles: obstacles.map((b) => [b.col, b.row]),
    buildings: obstacles,
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
  for (const [file, pos] of Object.entries(layoutDraft.buildings)) {
    if (pos && pos[0] === col && pos[1] === row) {
      return { kind: "building", file };
    }
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
  for (const file of Object.keys(layoutDraft.buildings)) {
    const pos = layoutDraft.buildings[file];
    if (pos && pos[0] === col && pos[1] === row) {
      delete layoutDraft.buildings[file];
    }
  }
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
