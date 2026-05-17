/** Grid rendering and palette configuration. */

export const TILE_SIZE = 44;
export const TILE_GAP = 3;
export const TILE_RADIUS = 6;

export const ACTION_DELTAS = [
  [0, -1],
  [0, 1],
  [-1, 0],
  [1, 0],
];

export const PLASMA_STOPS = [
  [13, 8, 135],
  [84, 2, 163],
  [156, 23, 158],
  [218, 78, 119],
  [252, 159, 79],
  [240, 249, 33],
];

export const SPRITE_FILES = {
  up: "/assets/sprites/business_man_1_back.png",
  down: "/assets/sprites/business_man_1_forward.png",
  left: "/assets/sprites/business_man_1_left.png",
  right: "/assets/sprites/business_man_1_right.png",
};

export const PALETTE_ITEMS = [
  { id: "agent", label: "Agent", sprite: "down", kind: "agent" },
  { id: "bank", label: "Bank", sprite: "bank", kind: "bank" },
  { id: "building_1", label: "Building 1", sprite: "building_1.png", kind: "building" },
  { id: "building_2", label: "Building 2", sprite: "building_2.png", kind: "building" },
  { id: "building_3", label: "Building 3", sprite: "building_3.png", kind: "building" },
];
