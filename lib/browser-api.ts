/**
 * Cross-browser WebExtension API namespace.
 *
 * Browser story:
 * - **Chrome MV3**: `chrome.*` returns Promises natively. `browser` is undefined.
 * - **Firefox MV2**: `chrome.*` exists but is **callback-only** — calling
 *   `await chrome.storage.sync.get(K)` resolves to `undefined`. The
 *   Promise-returning surface is on the `browser.*` namespace instead.
 * - **Firefox MV3**: both work, but `browser.*` is still the canonical one.
 *
 * Always import this and use `browserApi.*` for any call you intend to
 * `await`. Event-listener registration (`onMessage.addListener` etc.)
 * works on either namespace, but routing those through here too keeps
 * the codebase consistent.
 */

export const browserApi: typeof chrome =
  (globalThis as { browser?: typeof chrome }).browser ?? chrome;

/**
 * Open the extension's side panel / sidebar from a user-gesture handler.
 *
 * **Must be called synchronously from inside a click handler.** Both
 * `chrome.sidePanel.open()` (Chromium 116+) and
 * `browser.sidebarAction.open()` (Firefox MV2) require an unconsumed
 * user-gesture. `await`-ing anything else first reliably loses it,
 * which is why this function takes a pre-fetched `windowId` instead of
 * querying it on the spot.
 *
 * Quietly noops if the API isn't available; callers shouldn't depend
 * on the panel actually being open afterwards (it might already be).
 */
export function openSidePanel(windowId?: number): void {
  // Chromium MV3
  const sp = (chrome as typeof chrome & {
    sidePanel?: {
      open?: (opts: { windowId: number }) => Promise<void>;
    };
  }).sidePanel;
  if (sp?.open) {
    if (typeof windowId === "number") {
      sp.open({ windowId }).catch(() => undefined);
    }
    return;
  }

  // Firefox MV2 — sidebarAction.open() doesn't need a window id.
  const ff = browserApi as typeof chrome & {
    sidebarAction?: { open?: () => Promise<void> };
  };
  if (ff.sidebarAction?.open) {
    ff.sidebarAction.open().catch(() => undefined);
  }
}

/**
 * Best-effort current-window-id lookup. Cache the result and pass it
 * to `openSidePanel()` from the click handler.
 */
export async function getCurrentWindowId(): Promise<number | undefined> {
  try {
    const w = await chrome.windows.getCurrent();
    return typeof w.id === "number" ? w.id : undefined;
  } catch {
    return undefined;
  }
}
