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

/**
 * Make sure the content script is alive in the given tab before the
 * background tries to talk to it. Fixes the canonical "Could not
 * establish connection. Receiving end does not exist." failure that
 * fires when:
 *
 *   - the tab pre-dates an extension reload (orphaned content world),
 *   - Chrome injected the manifest content script before the tab fully
 *     loaded and dropped it on the floor (rare but happens), or
 *   - the user clicks Analyze on a URL where content scripts can't run
 *     (chrome://, the Web Store, file:// without permission, etc.).
 *
 * Strategy: ping the content script. If it answers, return. If it
 * fails with the orphan-error pattern, re-inject `content-scripts/
 * content.js` via `chrome.scripting.executeScript` and ping again.
 * If injection itself rejects, classify the message and surface a
 * user-actionable error.
 */
export async function ensureContentScript(tabId: number): Promise<void> {
  if (await pingContentScript(tabId)) return;

  const scripting = (browserApi as typeof chrome).scripting;
  if (!scripting?.executeScript) {
    // No programmatic injection on this browser/permission set.
    // Best we can do is tell the user to reload the page.
    throw new Error(
      "This tab needs to be reloaded for DoppelCheck to read it. " +
        "Refresh the page (Ctrl+R / Cmd+R) and click Analyze again.",
    );
  }

  try {
    // WXT bundles `entrypoints/content.ts` to this path on both
    // `chrome-mv3` and `firefox-mv2` outputs; keep them in sync if
    // the entrypoint name changes.
    await scripting.executeScript({
      target: { tabId },
      files: ["content-scripts/content.js"],
    });
  } catch (err) {
    const msg = (err as Error).message ?? "";
    if (
      /Cannot access|chrome:\/\/|chrome-extension:|extensions gallery|webstore|restricted|Missing host permission/i.test(
        msg,
      )
    ) {
      throw new Error(
        "DoppelCheck can't read this page — the browser blocks extensions on " +
          "internal URLs (chrome://, the Chrome Web Store, etc.). Open a regular " +
          "article and try again.",
      );
    }
    throw new Error(
      `Couldn't load DoppelCheck's page reader into this tab: ${msg}. ` +
        "Try reloading the page and clicking Analyze again.",
    );
  }

  if (!(await pingContentScript(tabId))) {
    throw new Error(
      "DoppelCheck's page reader was injected but isn't responding. " +
        "Reload the page and try again.",
    );
  }
}

async function pingContentScript(tabId: number): Promise<boolean> {
  try {
    const reply = await sendToContent<{ ok?: boolean }>(tabId, { kind: "ping" });
    return reply?.ok === true;
  } catch (err) {
    const msg = (err as Error).message ?? "";
    if (/Receiving end does not exist|Could not establish connection/i.test(msg)) {
      return false;
    }
    // Anything else — permission, tab-gone, etc. — is not "missing
    // content script", so let the caller see the original failure.
    throw err;
  }
}
