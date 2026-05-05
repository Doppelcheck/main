/**
 * Chrome built-in AI wrappers — Prompt API + Language Detector.
 *
 * Both APIs ship in Chrome 138+ stable for extensions. Two non-obvious
 * constraints learned the hard way:
 *
 * 1. The Prompt API requires both `expectedInputs.languages` and
 *    `expectedOutputs.languages`, and as of Chrome 138-ish only accepts
 *    `["en"]`, `["es"]`, `["ja"]` (or combinations thereof). German and
 *    other languages return "The requested language options are not
 *    supported." We always declare `["en"]` regardless of the article's
 *    actual language: the expected-languages field is a *safety
 *    attestation*, not a capability gate. The model still accepts and
 *    produces other languages at runtime — the prompt asks for the
 *    article's language explicitly and Gemini Nano follows.
 *
 * 2. On first use, Gemini Nano needs to download (multi-GB). The
 *    `monitor` callback exposes progress so the UI can show it instead
 *    of looking like the extension hung.
 *
 * The Summarizer API is also part of the platform, but we don't use it
 * — our pipeline never asks for a generic article summary.
 */

import type { PromptInput } from "./index";

/** Languages the Prompt API will accept in `expectedInputs`/`expectedOutputs`. */
const ATTESTABLE = ["en"] as const;

export interface ChromePromptOpts {
  /**
   * Reports model-download progress (0..1). The `message` parameter is
   * present for symmetry with `CallOpts.onDownload` — Chrome's Prompt
   * API doesn't expose a per-file message of its own, so callers see
   * `undefined` here.
   */
  onDownload?: (progress: number, message?: string) => void;
  /**
   * JSON schema for structured generation. Gemini Nano is small and
   * frequently wraps JSON in prose or emits Markdown lists when only
   * prompted; passing a schema as `responseConstraint` constrains the
   * output to valid JSON matching it. Strongly recommended for any
   * prompt that expects JSON.
   */
  schema?: Record<string, unknown>;
}

export async function promptChromeBuiltin(
  input: PromptInput,
  streaming: false,
  opts?: ChromePromptOpts,
): Promise<string>;
export async function promptChromeBuiltin(
  input: PromptInput,
  streaming: true,
  opts?: ChromePromptOpts,
): Promise<AsyncIterable<string>>;
export async function promptChromeBuiltin(
  input: PromptInput,
  streaming: boolean,
  opts: ChromePromptOpts = {},
): Promise<string | AsyncIterable<string>> {
  const session = await LanguageModel.create({
    initialPrompts: [{ role: "system", content: input.system }],
    expectedInputs: [{ type: "text", languages: [...ATTESTABLE] }],
    expectedOutputs: [{ type: "text", languages: [...ATTESTABLE] }],
    // Low-but-nonzero temperature: our prompts are essentially
    // classification tasks where we want consistency. `topK` and
    // `temperature` must be specified together; omitting one and setting
    // the other is a runtime error.
    topK: 3,
    temperature: 0.3,
    monitor: opts.onDownload
      ? (m) => {
          m.addEventListener("downloadprogress", (e) => {
            const ev = e as Event & { loaded?: number };
            if (typeof ev.loaded === "number") opts.onDownload!(ev.loaded);
          });
        }
      : undefined,
  });

  const promptOpts = opts.schema ? { responseConstraint: opts.schema } : undefined;

  if (!streaming) {
    try {
      return await session.prompt(input.user, promptOpts);
    } finally {
      session.destroy?.();
    }
  }

  const stream = session.promptStreaming(input.user, promptOpts);
  return (async function* () {
    try {
      for await (const chunk of stream) yield chunk;
    } finally {
      session.destroy?.();
    }
  })();
}

export async function detectLanguageChromeBuiltin(
  text: string,
): Promise<string | undefined> {
  if (typeof LanguageDetector === "undefined") return undefined;
  const detector = await LanguageDetector.create();
  try {
    const results = await detector.detect(text.slice(0, 1000));
    const top = results[0];
    if (!top || (top.confidence ?? 0) < 0.5) return undefined;
    return top.detectedLanguage;
  } finally {
    detector.destroy?.();
  }
}
