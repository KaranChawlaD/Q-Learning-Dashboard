import { PALETTE_ITEMS, SPRITE_FILES } from "./constants.js";
import { canvasCellFromEvent } from "./canvas.js";
import { els } from "./dom.js";
import {
  clearCell,
  pieceAtCell,
  updateSetupValidation,
} from "./layout.js";
import { requestRender } from "./render-loop.js";
import { appState } from "./state.js";

export function visiblePaletteItems() {
  return PALETTE_ITEMS.filter((item) => {
    if (item.kind === "agent") return appState.layoutDraft.start === null;
    if (item.kind === "bank") return appState.layoutDraft.bank === null;
    return true;
  });
}

function paletteThumbHtml(item) {
  if (item.kind === "agent") {
    return `<img src="${SPRITE_FILES.down}" alt="" draggable="false" />`;
  }
  if (item.kind === "bank") {
    return `<img src="/assets/elems/bank.png" alt="" draggable="false" />`;
  }
  return `<img src="/assets/elems/${item.sprite}" alt="" draggable="false" />`;
}

export function refreshPalette() {
  els.palette.innerHTML = "";
  for (const item of visiblePaletteItems()) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "palette-item";
    chip.dataset.kind = item.kind;
    chip.dataset.file = item.sprite || "";
    chip.setAttribute("role", "listitem");
    chip.innerHTML = `
      <span class="palette-thumb">${paletteThumbHtml(item)}</span>
      <span class="palette-label">${item.label}</span>
    `;
    chip.addEventListener("pointerdown", (event) => beginDrag(event, item));
    els.palette.appendChild(chip);
  }
}

export function buildPalette() {
  refreshPalette();
}

export function placePiece(kind, file, col, row) {
  clearCell(col, row);
  const { layoutDraft } = appState;
  if (kind === "agent") {
    if (layoutDraft.start) clearCell(layoutDraft.start[0], layoutDraft.start[1]);
    layoutDraft.start = [col, row];
  } else if (kind === "bank") {
    if (layoutDraft.bank) clearCell(layoutDraft.bank[0], layoutDraft.bank[1]);
    layoutDraft.bank = [col, row];
  } else if (kind === "building" && file) {
    const old = layoutDraft.buildings[file];
    if (old) clearCell(old[0], old[1]);
    layoutDraft.buildings[file] = [col, row];
  }
  updateSetupValidation();
  refreshPalette();
  requestRender();
}

export function removePiece(kind, file) {
  const { layoutDraft } = appState;
  if (kind === "agent") layoutDraft.start = null;
  else if (kind === "bank") layoutDraft.bank = null;
  else if (kind === "building" && file) delete layoutDraft.buildings[file];
  updateSetupValidation();
  refreshPalette();
  requestRender();
}

function chipActive(el) {
  for (const chip of els.palette.querySelectorAll(".palette-item")) {
    chip.classList.toggle("is-active", chip === el);
  }
}

function showDragGhost(item, x, y) {
  els.dragGhost.classList.remove("hidden");
  els.dragGhost.innerHTML = paletteThumbHtml(item);
  els.dragGhost.style.left = `${x}px`;
  els.dragGhost.style.top = `${y}px`;
}

function hideDragGhost() {
  els.dragGhost.classList.add("hidden");
  els.dragGhost.innerHTML = "";
  for (const chip of els.palette.querySelectorAll(".palette-item")) {
    chip.classList.remove("is-active");
  }
}

function beginDrag(event, item) {
  if (event.button !== 0) return;
  event.preventDefault();
  appState.dragState = {
    kind: item.kind,
    file: item.kind === "building" ? item.sprite : null,
    fromGrid: false,
    hoverCell: null,
  };
  showDragGhost(item, event.clientX, event.clientY);
  chipActive(event.currentTarget);
}

function onPointerMove(event) {
  if (!appState.dragState) return;
  els.dragGhost.style.left = `${event.clientX}px`;
  els.dragGhost.style.top = `${event.clientY}px`;
  if (!appState.config) return;
  const cell = canvasCellFromEvent(
    event,
    els.gridCanvas,
    appState.config.gridCols,
    appState.config.gridRows,
  );
  appState.dragState.hoverCell = cell;
  requestRender();
}

function onPointerUp(event) {
  if (!appState.dragState) return;
  const cell = canvasCellFromEvent(
    event,
    els.gridCanvas,
    appState.config?.gridCols ?? 0,
    appState.config?.gridRows ?? 0,
  );
  if (cell && appState.uiMode === "setup") {
    if (event.altKey && appState.dragState.fromGrid) {
      removePiece(appState.dragState.kind, appState.dragState.file);
    } else {
      placePiece(appState.dragState.kind, appState.dragState.file, cell[0], cell[1]);
    }
  }
  appState.dragState = null;
  hideDragGhost();
  requestRender();
}

export function onGridPointerDown(event) {
  if (appState.uiMode !== "setup" || event.button !== 0) return;
  const cell = canvasCellFromEvent(
    event,
    els.gridCanvas,
    appState.config.gridCols,
    appState.config.gridRows,
  );
  if (!cell) return;
  const piece = pieceAtCell(cell[0], cell[1]);
  if (!piece) return;
  event.preventDefault();
  appState.dragState = {
    kind: piece.kind,
    file: piece.file || null,
    fromGrid: true,
    hoverCell: cell,
  };
  const item = PALETTE_ITEMS.find(
    (p) =>
      (p.kind === piece.kind && p.kind !== "building") ||
      (p.kind === "building" && p.sprite === piece.file),
  );
  if (item) showDragGhost(item, event.clientX, event.clientY);
  clearCell(cell[0], cell[1]);
  refreshPalette();
  updateSetupValidation();
  requestRender();
}

export function onGridContextMenu(event) {
  if (appState.uiMode !== "setup") return;
  event.preventDefault();
  const cell = canvasCellFromEvent(
    event,
    els.gridCanvas,
    appState.config.gridCols,
    appState.config.gridRows,
  );
  if (!cell) return;
  clearCell(cell[0], cell[1]);
  refreshPalette();
  updateSetupValidation();
  requestRender();
}

export function bindSetupEditor() {
  window.addEventListener("pointermove", onPointerMove);
  window.addEventListener("pointerup", onPointerUp);
  window.addEventListener("pointercancel", onPointerUp);
}
