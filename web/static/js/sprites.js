import { SPRITE_FILES } from "./constants.js";
import { appState } from "./state.js";

function loadImage(src) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => resolve(null);
    img.src = src;
  });
}

export async function loadAllSprites() {
  for (const [key, src] of Object.entries(SPRITE_FILES)) {
    appState.sprites[key] = await loadImage(src);
  }
  for (const file of appState.config?.buildingFiles || []) {
    appState.buildingSprites[file] = await loadImage(`/assets/elems/${file}`);
  }
  appState.bankSprite = await loadImage("/assets/elems/bank.png");
}
