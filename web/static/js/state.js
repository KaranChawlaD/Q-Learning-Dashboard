/** Mutable dashboard session state (WebSocket, layout draft, sprites). */

export const appState = {
  sprites: {},
  buildingSprites: {},
  bankSprite: null,
  socket: null,
  config: null,
  displayEnv: null,
  lastState: null,
  pendingFrame: false,
  renderedTestsKey: null,
  uiMode: "setup",
  layoutDraft: {
    start: null,
    bank: null,
    /** @type {{ id: string, file: string, col: number, row: number }[]} */
    buildings: [],
  },
  nextBuildingId: 0,
  dragState: null,
};
