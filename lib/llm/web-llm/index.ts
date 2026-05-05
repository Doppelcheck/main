/**
 * `LLM` adapter that runs an MLC web-llm engine — same interface as
 * Anthropic / OpenAI / Ollama, so the existing `LLMPipeline` reuses
 * its prompts and JSON streaming machinery without knowing or caring
 * which backend is underneath.
 *
 * The engine itself lives in exactly one persistent + WebGPU-capable
 * context per browser:
 *
 *   - **Chrome MV3**: an offscreen document. Created on demand by
 *     the proxy's `ensureHost()`. The MV3 service worker has no
 *     `navigator.gpu` and can't run the engine itself.
 *   - **Firefox MV2**: the (persistent) background page, which has
 *     `navigator.gpu` *and* survives tab churn / side-panel close.
 *
 * Routing rule:
 *
 *   - If we're calling from inside the host context (Firefox bg
 *     page on the analyze flow), call `generateInline` directly —
 *     Firefox doesn't deliver `runtime.connect()` self-loopbacks
 *     to the same context's `onConnect` listener, so the proxy
 *     would disconnect immediately.
 *   - Otherwise (options page, side panel, MV3 SW, content scripts)
 *     go through the proxy → host port.
 *
 * MLC is WebGPU-only — no WASM fallback. If WebGPU is unavailable,
 * `complete()` / `stream()` reject with a message pointing the user
 * at the network tier or at enabling WebGPU.
 */

import type { LLM } from "@/lib/llm";
import { isEngineHost } from "./host";
import { generateOffscreen } from "./offscreen-runner";

interface RunOpts {
  modelId: string;
  system: string;
  user: string;
  schema?: Record<string, unknown>;
  onDelta?: (text: string) => void;
  onProgress?: (progress: number, message?: string) => void;
}

/**
 * Pick the right runner based on whether THIS context is the engine
 * host. Resolved lazily so the dynamic import of the inline runner
 * (which pulls in MLC) only happens in contexts that actually need
 * to load it.
 */
async function runOnce(opts: RunOpts): Promise<void> {
  if (isEngineHost()) {
    const { generateInline } = await import("./engine-runner");
    await generateInline(opts);
    return;
  }
  await generateOffscreen(opts);
}

export interface WebLLMCfg {
  modelId: string;
}

export function makeWebLLMLLM(cfg: WebLLMCfg): LLM {
  return {
    tag: "web-llm",
    async complete(input, opts) {
      let acc = "";
      await runOnce({
        modelId: cfg.modelId,
        system: input.system,
        user: input.user,
        schema: opts?.schema,
        onDelta: (t) => {
          acc += t;
        },
        onProgress: opts?.onDownload,
      });
      return acc;
    },
    async *stream(input, opts) {
      // Bridge the push-based delta callback into a pull-based async
      // iterator. Tokens that arrive before the consumer iterates are
      // buffered; the iterator awaits a Promise that's resolved by
      // each new token (or by completion).
      const buffer: string[] = [];
      let done = false;
      let error: Error | undefined;
      let wake: () => void = () => undefined;
      let waiter: Promise<void> = new Promise((r) => (wake = r));

      const push = (t: string) => {
        buffer.push(t);
        const w = wake;
        waiter = new Promise((r) => (wake = r));
        w();
      };

      const promise = runOnce({
        modelId: cfg.modelId,
        system: input.system,
        user: input.user,
        schema: opts?.schema,
        onDelta: push,
        onProgress: opts?.onDownload,
      })
        .catch((err: Error) => {
          error = err;
        })
        .finally(() => {
          done = true;
          wake();
        });

      while (true) {
        while (buffer.length > 0) yield buffer.shift()!;
        if (done) break;
        await waiter;
      }
      await promise; // surface late rejections
      if (error) throw error;
    },
  };
}

