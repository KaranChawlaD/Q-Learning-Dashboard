import { PLASMA_STOPS } from "./constants.js";

export function lerp(a, b, t) {
  return [
    Math.round(a[0] + (b[0] - a[0]) * t),
    Math.round(a[1] + (b[1] - a[1]) * t),
    Math.round(a[2] + (b[2] - a[2]) * t),
  ];
}

export function plasma(t) {
  if (!isFinite(t)) t = 0;
  t = Math.max(0, Math.min(1, t));
  const n = PLASMA_STOPS.length - 1;
  const seg = t * n;
  const i = Math.min(n - 1, Math.floor(seg));
  return lerp(PLASMA_STOPS[i], PLASMA_STOPS[i + 1], seg - i);
}

export function rgb(c) {
  return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
}
