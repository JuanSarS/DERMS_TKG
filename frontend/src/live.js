/** Canal WebSocket local, separado del JWT y del subprotocolo remoto. */
import { update } from "./state.js";

let liveSocket = null;

export function connectLive(runId, onEvent) {
  if (liveSocket) liveSocket.close();
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const url = `${protocol}://${location.host}/api/live/${encodeURIComponent(runId)}`;
  liveSocket = new WebSocket(url);
  liveSocket.onmessage = (message) => {
    const event = JSON.parse(message.data);
    if (event.type === "qsts_progress") update({ progress: event });
    onEvent?.(event);
  };
  liveSocket.onerror = () =>
    update({
      error: "El canal de progreso local está desconectado. Los datos confirmados permanecen.",
    });
  return liveSocket;
}
export function closeLive() {
  if (liveSocket) liveSocket.close();
  liveSocket = null;
}
