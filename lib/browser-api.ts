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
