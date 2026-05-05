/**
 * Shared bus that funnels every diagnostic in the extension into one
 * place: the side panel's debug log.
 *
 * Why this exists as a separate module: log entries originate in
 * many contexts (background SW / Firefox background page, options
 * page, side panel itself, content scripts). The side panel listens
 * via a long-lived port. Naïve `runtime.sendMessage` works *across*
 * contexts but does **not** deliver to the sender's own context. So
 * we keep the live panel-port set here and let same-context callers
 * broadcast directly, while cross-context callers fall back to
 * `runtime.sendMessage`. `routeLogEntry` is the one entry point
 * everyone uses; it does the right thing in both cases.
 */

import type { LogEntry, ServerEvent } from "@/types";
import { browserApi } from "@/lib/browser-api";
import {
  isRelayLogMessage,
  relayLogEntry,
  safePost,
} from "./index";

/** Live PANEL_PORT connections — broadcast targets. */
const panelPorts = new Set<chrome.runtime.Port>();

/**
 * Dedupe table for noisy log floods — when one upstream failure
 * cascades into many identical rejections, letting all of those
 * through fills the side panel within a second and buries the
 * actually-useful first error.
 *
 * Strategy: if the same message has been broadcast within the past
 * `DEDUPE_WINDOW_MS`, drop subsequent copies silently. The first
 * occurrence always goes through with full fidelity.
 */
const DEDUPE_WINDOW_MS = 3_000;
const recent = new Map<string, number>();

/**
 * Ring buffer for entries that arrive before any panel has
 * connected. Flushed to every newly-connecting panel and then
 * discarded. Capped so a long idle period can't grow it unbounded.
 * Entries older than `BACKLOG_MAX_AGE_MS` are dropped on flush —
 * a stale log from yesterday's attempt would only confuse the user.
 */
const BACKLOG_LIMIT = 200;
const BACKLOG_MAX_AGE_MS = 60_000;
const backlog: { event: ServerEvent; at: number }[] = [];

export function addPanelPort(port: chrome.runtime.Port): void {
  panelPorts.add(port);
  port.onDisconnect.addListener(() => panelPorts.delete(port));
  // Flush pre-mount backlog to this freshly-connected panel.
  flushBacklogTo((e) => safePost(port, e));
}

/**
 * Broadcast a log entry to every connected side panel. Same-context
 * delivery only; if no panels are connected here, the entry goes to
 * the backlog and is flushed when one connects.
 *
 * **Does not** reach panels connected to a *different* context — for
 * that, `routeLogEntry` also fires `relayLogEntry` so the background
 * SW (Chrome) picks it up via `runtime.onMessage` and re-broadcasts.
 */
export function broadcastLog(entry: LogEntry): void {
  if (isRecentDuplicate(entry)) return;
  const event: ServerEvent = { kind: "log", entry };
  if (panelPorts.size === 0) {
    recordBacklog(event);
  } else {
    for (const port of panelPorts) safePost(port, event);
  }
  // Mirror to the host-context console too — useful when a
  // side panel isn't open and the user is poking at devtools.
  const tag = `[doppelcheck:${entry.phase}]`;
  if (entry.level === "error") console.error(tag, entry.message);
  else if (entry.level === "warn") console.warn(tag, entry.message);
  else console.log(tag, entry.message);
}

function isRecentDuplicate(entry: LogEntry): boolean {
  const now = Date.now();
  // Garbage-collect stale entries while we're in here. Keeps the
  // map bounded without scheduling a separate timer.
  for (const [key, at] of recent) {
    if (now - at > DEDUPE_WINDOW_MS) recent.delete(key);
  }
  // Key includes phase + level so a "warn" and an "error" with the
  // same text don't collapse into each other.
  const key = `${entry.phase}|${entry.level}|${entry.message}`;
  const last = recent.get(key);
  if (last !== undefined && now - last < DEDUPE_WINDOW_MS) return true;
  recent.set(key, now);
  return false;
}

/**
 * The single entry point for sending a log entry to the side panel
 * from anywhere. Routes it to:
 *
 *   - panels connected to **this** context (direct broadcast)
 *   - panels connected to **any other** context (via the
 *     `runtime.sendMessage` relay → background → broadcast there)
 *
 * Either or both may noop in a given context; that's fine. The user
 * gets a single, deduplicated entry on the side panel either way.
 */
export function routeLogEntry(entry: LogEntry): void {
  broadcastLog(entry);
  relayLogEntry(entry);
}

/**
 * Install the cross-context relay listener. Call this **once per
 * context** that owns panel ports (background SW on Chrome, the
 * background page on Firefox MV2). Other contexts shouldn't bother:
 * `runtime.sendMessage` doesn't deliver to the sender.
 */
export function installRelayListener(): void {
  browserApi.runtime.onMessage.addListener((msg) => {
    if (!isRelayLogMessage(msg)) return;
    broadcastLog(msg.entry);
  });
}

function recordBacklog(event: ServerEvent): void {
  backlog.push({ event, at: Date.now() });
  if (backlog.length > BACKLOG_LIMIT) backlog.shift();
}

function flushBacklogTo(send: (e: ServerEvent) => void): void {
  const cutoff = Date.now() - BACKLOG_MAX_AGE_MS;
  for (const { event, at } of backlog) {
    if (at >= cutoff) send(event);
  }
  backlog.length = 0;
}
