/**
 * In-process MLC web-llm runner. Runs in whatever context imports
 * it — Firefox MV2 background page or the Chrome MV3 offscreen
 * document. Both have WebGPU available; the MV3 service worker does
 * not, which is why Chrome routes through `offscreen-runner` instead.
 *
 * Engines are cached per `modelId`. Switching model in settings forces
 * a fresh load on the next call; the previous engine is `unload()`-ed
 * so its WebGPU buffers are released.
 */

import type {
  ChatCompletionMessageParam,
  ChatCompletionRequestStreaming,
  InitProgressReport,
  MLCEngineInterface,
  ResponseFormat,
} from "@mlc-ai/web-llm";

interface CachedEngine {
  modelId: string;
  engine: MLCEngineInterface;
}

let cached: CachedEngine | null = null;

export interface InlineGenerateOpts {
  modelId: string;
  system: string;
  user: string;
  maxNewTokens?: number;
  /**
   * Optional JSON schema. When present, the engine's grammar sampler
   * masks tokens that would break the schema, so the streamed output
   * is guaranteed to parse as a JSON document matching it.
   */
  schema?: Record<string, unknown>;
  /** Streamed token-text callback (called once per generated chunk). */
  onDelta?: (text: string) => void;
  /** Init progress (0..1). Covers model download + WebGPU warmup. */
  onProgress?: (progress: number, message?: string) => void;
  signal?: AbortSignal;
}

/**
 * Run one generation. Resolves once the model has emitted all tokens;
 * deltas are streamed via `onDelta`.
 *
 * The first call for a given `modelId` triggers download + WebGPU
 * compile; subsequent calls reuse the warm engine.
 */
export async function generateInline(opts: InlineGenerateOpts): Promise<void> {
  const engine = await getEngine(opts.modelId, opts.onProgress);

  const messages: ChatCompletionMessageParam[] = [
    { role: "system", content: opts.system },
    { role: "user", content: opts.user },
  ];

  // Build the OpenAI-compatible request. JSON-schema-constrained
  // generation is enabled by `response_format.type: "json_object"` +
  // `schema: <stringified JSON schema>` — XGrammar masks invalid
  // tokens at sampling time, so the streamed output never produces
  // malformed JSON.
  const responseFormat: ResponseFormat | undefined = opts.schema
    ? { type: "json_object", schema: JSON.stringify(opts.schema) }
    : undefined;

  const request: ChatCompletionRequestStreaming = {
    stream: true,
    messages,
    max_tokens: opts.maxNewTokens ?? 512,
    // Low temperature: our prompts are essentially classification +
    // structured-output tasks where consistency matters more than
    // creativity. Same rationale as the Chrome built-in path.
    temperature: 0.3,
    // Anti-degeneracy controls. SmolLM2-360M and other small models
    // routinely fall into token-loop collapse on long-tail prompts
    // (e.g. claim extraction in German), repeating the same word
    // hundreds of times until `max_tokens` is hit. `frequency_penalty`
    // makes already-emitted tokens less likely on each subsequent
    // step, `top_p` (nucleus sampling) bounds the candidate pool to
    // the high-probability mass — both directly attack repetition
    // collapse without changing the output for well-behaved models.
    frequency_penalty: 0.5,
    top_p: 0.9,
    ...(responseFormat ? { response_format: responseFormat } : {}),
  };

  const completion = await engine.chat.completions.create(request);

  for await (const chunk of completion) {
    if (opts.signal?.aborted) {
      // MLC has its own interrupt; we also stop iterating.
      try {
        await engine.interruptGenerate();
      } catch {
        /* ignore */
      }
      return;
    }
    const delta = chunk.choices[0]?.delta?.content;
    if (delta && opts.onDelta) opts.onDelta(delta);
  }
}

/**
 * Lazy load + cache the MLC engine for `modelId`. Loads
 * `@mlc-ai/web-llm` only when first needed so the import isn't paid
 * by surfaces that never use it (options page, side panel UI shell).
 */
async function getEngine(
  modelId: string,
  onProgress?: (p: number, message?: string) => void,
): Promise<MLCEngineInterface> {
  if (cached && cached.modelId === modelId) return cached.engine;

  // Switching models — release the previous engine's GPU buffers
  // before allocating new ones. The unload is best-effort; if it
  // throws (engine in a bad state) we discard the reference anyway.
  if (cached) {
    try {
      await cached.engine.unload();
    } catch {
      /* ignore */
    }
    cached = null;
  }

  // Forward init progress (download + compile + warmup) to the
  // caller's onProgress. MLC reports `progress` in 0..1 and a
  // human-readable `text` like "Loading model from cache[42/142]".
  const initProgressCallback = (report: InitProgressReport) => {
    if (!onProgress) return;
    onProgress(typeof report.progress === "number" ? report.progress : 0, report.text);
  };

  // Dynamic import: keeps the ~14MB MLC bundle out of contexts that
  // never actually generate (e.g. side panel UI, options form). The
  // first generate() call here pays the import; subsequent ones hit
  // the module cache.
  const { MLCEngine } = await import("@mlc-ai/web-llm");
  const engine = new MLCEngine({ initProgressCallback });
  try {
    await engine.reload(modelId);
  } catch (err) {
    const message = (err as Error)?.message ?? "";
    // Some MLC ModelRecords (e.g. `gemma3-1b-it-q4f16_1-MLC` in
    // 0.2.83) ship *both* `context_window_size` and
    // `sliding_window_size` populated, and the engine refuses that
    // combination with `WindowSizeConfigurationError`. The error
    // message itself tells us to override one to -1 — disabling the
    // sliding window keeps the full context, which is what our
    // short claim/source prompts need anyway.
    if (/WindowSizeConfigurationError|sliding_window_size|context_window_size/i.test(message)) {
      await engine.reload(modelId, { sliding_window_size: -1 });
    } else {
      // Map "Object has already been disposed" / device-lost
      // failures into a clear OOM message. Firefox WebGPU on Linux
      // tears the GPU device down with `GPUDeviceLostInfo` when
      // model weights overflow VRAM during chunk upload, and every
      // downstream TVM handle then throws "disposed" — which by
      // itself doesn't hint at the real cause. Surface the actual
      // problem so the user knows to pick a smaller model.
      if (
        /already been disposed|Device was lost|Device destroyed|Not enough memory|out of memory/i.test(
          message,
        )
      ) {
        throw new Error(
          `${message}\n\nLikely cause: the WebGPU device ran out of memory loading this model. Try a smaller one (SmolLM2-360M is the safest starting point).`,
        );
      }
      throw err;
    }
  }
  cached = { modelId, engine };
  return engine;
}

/** Tag describing the active engine — currently just the modelId. */
export function activeBackendTag(): string | undefined {
  return cached?.modelId;
}
