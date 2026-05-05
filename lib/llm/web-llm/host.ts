/**
 * Engine-host runtime port handler.
 *
 * Registers the `RUNNER_PORT` listener and runs the MLC engine in
 * the calling context. This must only be called from a context that
 * has both `navigator.gpu` (WebGPU) **and** is persistent — otherwise
 * an in-flight model load can be torn down by the browser. Concretely:
 *
 *   - **Chrome MV3 offscreen document** (`entrypoints/offscreen/main.ts`)
 *   - **Firefox MV2 background page** (`entrypoints/background.ts`,
 *     guarded by a `navigator.gpu` check so the Chromium SW path skips it)
 *
 * Other contexts (options page, side panel, content scripts, MV3 SW)
 * connect to this port via the proxy in `proxy.ts` and never run the
 * engine themselves. That keeps engine state in the one context that
 * survives tab churn / side-panel close / SW idle.
 */

import type { LogLevel } from "@/types";
import { routeLogEntry } from "@/lib/messaging/panel-bus";
import { generateInline } from "./engine-runner";
import {
  RUNNER_PORT,
  type RunnerEvent,
  type RunnerRequest,
} from "./protocol";

let installed = false;

/**
 * True if this context has been marked as the engine host (i.e.
 * `installEngineHostHandler()` ran here). Callers that want to talk
 * to the engine should check this and call `generateInline` directly
 * when true — the proxy's runtime port doesn't deliver self-connects
 * on Firefox MV2 (background → background), so the self-loopback
 * disconnects immediately.
 */
export function isEngineHost(): boolean {
  return installed;
}

export function installEngineHostHandler(): void {
  if (installed) return;
  installed = true;

  // Funnel all host-context diagnostics into the side-panel debug
  // log. MLC's WebGPU backend logs progress + warnings via console
  // (e.g. "Falling back to maxComputeInvocationsPerWorkgroup", "Device
  // was lost"), and Chrome/Firefox surface uncaught WebGPU errors
  // and unhandled promise rejections separately. Without this hook,
  // the user has to open three different devtools to see what went
  // wrong; with it, everything lands in one place.
  installHostDiagnosticsHook();

  chrome.runtime.onConnect.addListener((port) => {
    if (port.name !== RUNNER_PORT) return;

    // One AbortController per in-flight generation so the host can
    // cancel mid-stream when the proxy sends an "abort" message.
    const inflight = new Map<string, AbortController>();

    const send = (event: RunnerEvent) => {
      try {
        port.postMessage(event);
      } catch {
        // Port closed underneath us — drop silently.
      }
    };

    port.onMessage.addListener((req: RunnerRequest) => {
      switch (req.kind) {
        case "generate":
          void handleGenerate(req, inflight, send);
          return;
        case "abort": {
          const ctl = inflight.get(req.id);
          ctl?.abort();
          inflight.delete(req.id);
          return;
        }
      }
    });

    port.onDisconnect.addListener(() => {
      for (const ctl of inflight.values()) ctl.abort();
      inflight.clear();
    });
  });
}

async function handleGenerate(
  req: Extract<RunnerRequest, { kind: "generate" }>,
  inflight: Map<string, AbortController>,
  send: (e: RunnerEvent) => void,
): Promise<void> {
  const ctl = new AbortController();
  inflight.set(req.id, ctl);
  try {
    await generateInline({
      modelId: req.modelId,
      system: req.system,
      user: req.user,
      maxNewTokens: req.maxNewTokens,
      schema: req.schema,
      signal: ctl.signal,
      onProgress: (progress, message) =>
        send({ kind: "progress", id: req.id, progress, message }),
      onDelta: (text) => send({ kind: "delta", id: req.id, text }),
    });
    if (!ctl.signal.aborted) send({ kind: "done", id: req.id });
  } catch (err) {
    const e = err as Error;
    const stack = typeof e?.stack === "string" ? e.stack : undefined;
    const message = e?.message ?? String(err);
    // Side panel: full stack, so the user has line numbers without
    // opening offscreen / background-page devtools.
    routeLogEntry({
      at: Date.now(),
      level: "error",
      phase: "error",
      message: stack ? `Engine error: ${message}\n${stack}` : `Engine error: ${message}`,
    });
    // Proxy (probe / pipeline) — they need the message string for
    // their own catch handlers to bubble it up to the LLM call site.
    send({
      kind: "error",
      id: req.id,
      message: stack ? `${message}\n${stack}` : message,
    });
  } finally {
    inflight.delete(req.id);
  }
}

/**
 * Hook console.warn/error and global error / unhandledrejection
 * listeners in the host context so MLC's internal logs and any
 * stray WebGPU errors are mirrored into the side-panel debug log.
 *
 * The original console methods stay intact — devtools still shows
 * everything; we only *also* relay it. Lines we emit ourselves
 * (prefix `[doppelcheck:`) are skipped to avoid feedback loops with
 * the broadcaster's mirror-to-console path.
 */
function installHostDiagnosticsHook(): void {
  if (typeof console === "undefined") return;

  const origWarn = console.warn.bind(console);
  const origError = console.error.bind(console);
  const isOurOwnTag = (parts: unknown[]) =>
    typeof parts[0] === "string" && parts[0].startsWith("[doppelcheck:");
  const stringify = (parts: unknown[]) =>
    parts
      .map((p) =>
        typeof p === "string"
          ? p
          : p instanceof Error
          ? p.stack ?? p.message
          : (() => {
              try {
                return JSON.stringify(p);
              } catch {
                return String(p);
              }
            })(),
      )
      .join(" ");

  console.warn = (...parts: unknown[]) => {
    origWarn(...parts);
    if (isOurOwnTag(parts)) return;
    relay("warn", stringify(parts));
  };
  console.error = (...parts: unknown[]) => {
    origError(...parts);
    if (isOurOwnTag(parts)) return;
    relay("error", stringify(parts));
  };

  // Uncaught synchronous errors. WebGPU validation errors are
  // sometimes emitted here.
  if (typeof self !== "undefined" && typeof self.addEventListener === "function") {
    self.addEventListener("error", (event: Event) => {
      const e = event as ErrorEvent;
      const msg = e.message ?? "uncaught error";
      const stack = e.error?.stack ? `\n${e.error.stack}` : "";
      relay("error", `Uncaught: ${msg}${stack}`);
    });
    self.addEventListener("unhandledrejection", (event: Event) => {
      const e = event as PromiseRejectionEvent;
      const reason = e.reason;
      const msg =
        reason instanceof Error
          ? reason.stack ?? reason.message
          : typeof reason === "string"
          ? reason
          : (() => {
              try {
                return JSON.stringify(reason);
              } catch {
                return String(reason);
              }
            })();
      relay("error", `Unhandled rejection: ${msg}`);
    });
  }
}

function relay(level: LogLevel, message: string): void {
  routeLogEntry({
    at: Date.now(),
    level,
    phase: "error",
    message,
  });
}
