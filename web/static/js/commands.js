import { appState } from "./state.js";

export function sendCommand(msg) {
  if (appState.socket?.readyState === WebSocket.OPEN) {
    appState.socket.send(JSON.stringify(msg));
  }
}
