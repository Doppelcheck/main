import type {
  ClientCommand,
  ContentRequest,
  LogEntry,
  ServerEvent,
} from "@/types";
import { browserApi } from "@/lib/browser-api";

/** Long-lived port name between side panel and background. */
export const PANEL_PORT = "doppelcheck-panel";

/**
 * Tagged one-shot message: any extension surface (options page, etc.)
 * can fire one of these and the background relays them as
 * `{ kind: "log", entry }` `ServerEvent`s to every connected side
 * panel. Single source of truth for the debug log; we don't need a
 * second log surface in the options page.
 */
export interface RelayLogMessage {
  __doppelcheck: "log";
  entry: LogEntry;
}

export function isRelayLogMessage(m: unknown): m is RelayLogMessage {
  return (
    !!m &&
    typeof m === "object" &&
    (m as { __doppelcheck?: unknown }).__doppelcheck === "log"
  );
}

/** Send a single log entry into the relay. Resolves whether or not a
 *  side panel is currently listening — fire-and-forget. */
export function relayLogEntry(entry: LogEntry): void {
  const msg: RelayLogMessage = { __doppelcheck: "log", entry };
  try {
    void browserApi.runtime.sendMessage(msg);
  } catch {
    // No background available (during extension reload, etc.) — drop.
  }
}

export function connectPanel(): chrome.runtime.Port {
  return browserApi.runtime.connect({ name: PANEL_PORT });
}

/** Side panel → background. Silently no-ops if the port has been closed. */
export function sendCommand(port: chrome.runtime.Port, cmd: ClientCommand) {
  try {
    port.postMessage(cmd);
  } catch {
    // The port can disconnect at any moment (panel closed, tab navigated,
    // service worker restarted). Eat the throw so it doesn't surface as
    // "Uncaught Error: Attempting to use a disconnected port object".
  }
}

/** Background → side panel. Same swallow-the-throw policy. */
export function safePost(port: chrome.runtime.Port, event: ServerEvent) {
  try {
    port.postMessage(event);
  } catch {
    /* port closed */
  }
}

export function onServerEvent(
  port: chrome.runtime.Port,
  cb: (e: ServerEvent) => void,
) {
  port.onMessage.addListener(cb as (msg: unknown) => void);
}

/** Background → content script one-shot request. */
export async function sendToContent<T>(
  tabId: number,
  req: ContentRequest,
): Promise<T> {
  return browserApi.tabs.sendMessage(tabId, req) as Promise<T>;
}
