/**
 * Proxy that forwards generation requests to whichever extension
 * context hosts the MLC web-llm engine.
 *
 *   - **Chrome MV3**: the host is an offscreen document. Created
 *     lazily here on first use; once up, it stays up for the
 *     lifetime of the service worker.
 *   - **Firefox MV2**: the host is the (always-on) background page.
 *     `ensureHost()` is a no-op there.
 *
 * The same `RUNNER_PORT` protocol works in both browsers — only the
 * setup step differs.
 */

import { browserApi } from "@/lib/browser-api";
import {
  RUNNER_PORT,
  type RunnerEvent,
  type RunnerRequest,
} from "./protocol";

const OFFSCREEN_PATH = "offscreen.html";
const OFFSCREEN_REASON = "WORKERS";

let portPromise: Promise<chrome.runtime.Port> | null = null;
let nextId = 0;

/** Listeners keyed by request id. */
const listeners = new Map<string, (e: RunnerEvent) => void>();

interface ChromeOffscreen {
  createDocument(opts: {
    url: string;
    reasons: string[];
    justification: string;
  }): Promise<void>;
  hasDocument?: () => Promise<boolean>;
}

async function ensureHost(): Promise<void> {
  // Chrome MV3: spin up the offscreen document on demand. Firefox
  // MV2 has no `chrome.offscreen` API — its background page already
  // hosts the engine, so there's nothing to set up.
  const off = (chrome as unknown as { offscreen?: ChromeOffscreen }).offscreen;
  if (!off) return;
  if (await off.hasDocument?.()) return;
  await off.createDocument({
    url: browserApi.runtime.getURL(OFFSCREEN_PATH),
    reasons: [OFFSCREEN_REASON as never],
    justification:
      "MLC web-llm requires WebGPU and a real page context, which the MV3 service worker doesn't provide.",
  });
}

async function getPort(): Promise<chrome.runtime.Port> {
  if (portPromise) {
    try {
      const port = await portPromise;
      void port.name;
      return port;
    } catch {
      portPromise = null;
    }
  }
  portPromise = (async () => {
    await ensureHost();
    const port = browserApi.runtime.connect({ name: RUNNER_PORT });
    port.onMessage.addListener((msg: unknown) => {
      const event = msg as RunnerEvent;
      const cb = listeners.get(event.id);
      if (cb) cb(event);
    });
    port.onDisconnect.addListener(() => {
      portPromise = null;
      for (const cb of listeners.values()) {
        cb({
          kind: "error",
          id: "*",
          message: "offscreen document disconnected",
        });
      }
      listeners.clear();
    });
    return port;
  })();
  return portPromise;
}

export interface OffscreenGenerateOpts {
  modelId: string;
  system: string;
  user: string;
  maxNewTokens?: number;
  schema?: Record<string, unknown>;
  onDelta?: (text: string) => void;
  onProgress?: (progress: number, message?: string) => void;
  signal?: AbortSignal;
}

export async function generateOffscreen(
  opts: OffscreenGenerateOpts,
): Promise<void> {
  const port = await getPort();
  const id = `g${++nextId}`;

  await new Promise<void>((resolve, reject) => {
    const onMessage = (event: RunnerEvent) => {
      if (event.id !== id && event.id !== "*") return;
      switch (event.kind) {
        case "progress":
          if (typeof event.progress === "number")
            opts.onProgress?.(event.progress, event.message);
          else if (event.message) opts.onProgress?.(0, event.message);
          return;
        case "delta":
          opts.onDelta?.(event.text);
          return;
        case "done":
          listeners.delete(id);
          resolve();
          return;
        case "error":
          listeners.delete(id);
          reject(new Error(event.message));
          return;
      }
    };
    listeners.set(id, onMessage);

    const onAbort = () => {
      try {
        port.postMessage({ kind: "abort", id } satisfies RunnerRequest);
      } catch {
        /* port may already be closed */
      }
      listeners.delete(id);
      reject(new DOMException("aborted", "AbortError"));
    };
    if (opts.signal) {
      if (opts.signal.aborted) {
        onAbort();
        return;
      }
      opts.signal.addEventListener("abort", onAbort, { once: true });
    }

    try {
      port.postMessage({
        kind: "generate",
        id,
        modelId: opts.modelId,
        system: opts.system,
        user: opts.user,
        maxNewTokens: opts.maxNewTokens,
        schema: opts.schema,
      } satisfies RunnerRequest);
    } catch (err) {
      listeners.delete(id);
      reject(err);
    }
  });
}

export function offscreenAvailable(): boolean {
  return !!(chrome as unknown as { offscreen?: unknown }).offscreen;
}
