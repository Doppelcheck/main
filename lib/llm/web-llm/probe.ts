/**
 * Smoke-test an MLC web-llm model in the browser.
 *
 * Two reporting channels:
 *
 *   - `onProgress(progress, message?)` — purely visual. Numeric values
 *     drive a progress bar; messages describe the current init phase.
 *   - `onLog(level, phase, message)` — coarse log entries suitable for
 *     the side panel's debug log. The options page forwards these
 *     through the runtime relay so they appear alongside analyze
 *     events. Per-percent download chatter is filtered out.
 */

import type { LogLevel, Phase } from "@/types";
import { generateOffscreen } from "./offscreen-runner";

export interface ProbeResult {
  ok: true;
  sample: string;
  durationMs: number;
  /** The MLC model id that loaded. */
  backend?: string;
}

export interface ProbeFailure {
  ok: false;
  error: string;
  durationMs: number;
}

export interface ProbeOpts {
  modelId: string;
  /** Numeric progress + status messages for the UI. */
  onProgress?: (progress: number, message?: string) => void;
  /** Routed to the side panel's debug log via the runtime relay. */
  onLog?: (level: LogLevel, phase: Phase, message: string) => void;
  signal?: AbortSignal;
}

export async function probeLocalModel(
  opts: ProbeOpts,
): Promise<ProbeResult | ProbeFailure> {
  const t0 = performance.now();
  const log = (level: LogLevel, message: string) =>
    opts.onLog?.(level, "model-test", message);

  log("info", `Test starting: ${opts.modelId}`);

  // Dedupe progress messages so the debug log doesn't fill with one
  // entry per percent. MLC's `report.text` only changes a few times
  // during a load — when it does, that's an interesting transition.
  let lastMessage: string | undefined;
  let acc = "";
  try {
    // Always proxy to the engine host (offscreen doc on Chrome,
    // background page on Firefox). The host has WebGPU and lives
    // longer than this options-page tab — running the engine inline
    // here meant Firefox could discard the tab mid-load, leaving the
    // engine "Object has already been disposed".
    await generateOffscreen({
      modelId: opts.modelId,
      system: "You answer in one short word, no explanation.",
      user: "Say hi.",
      maxNewTokens: 16,
      signal: opts.signal,
      onProgress: (progress, message) => {
        opts.onProgress?.(progress, message);
        if (message && message !== lastMessage) {
          lastMessage = message;
          const level: LogLevel = /failed|fatal|abort|error/i.test(message)
            ? "warn"
            : "info";
          log(level, message);
        }
      },
      onDelta: (t) => {
        acc += t;
      },
    });
    const sample = acc.trim();
    if (!sample) {
      log("error", "Model loaded but produced no output");
      return {
        ok: false,
        error: "model loaded but produced no output",
        durationMs: Math.round(performance.now() - t0),
      };
    }
    // The engine itself is in another context (offscreen doc on
    // Chrome, background page on Firefox); we can't call
    // `activeBackendTag()` across contexts, but the model id we
    // asked for IS the active backend if the call succeeded.
    const backend = opts.modelId;
    const durationMs = Math.round(performance.now() - t0);
    log(
      "info",
      `Test ok: model=${backend ?? "?"} duration=${(durationMs / 1000).toFixed(1)}s sample=${sample.slice(0, 60)}`,
    );
    return {
      ok: true,
      sample: sample.slice(0, 80),
      durationMs,
      backend,
    };
  } catch (err) {
    const error = (err as Error).message ?? String(err);
    log("error", `Test failed: ${error}`);
    return {
      ok: false,
      error,
      durationMs: Math.round(performance.now() - t0),
    };
  }
}
