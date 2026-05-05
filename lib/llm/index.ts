import type { Settings } from "@/types";
import {
  promptChromeBuiltin,
  detectLanguageChromeBuiltin,
  type ChromePromptOpts,
} from "./chrome-ai";
import { promptAnthropic } from "./anthropic";
import { promptOpenAI } from "./openai";
import { promptGoogle } from "./google";
import { promptOllama } from "./ollama";
import { makeWebLLMLLM } from "./web-llm";

export interface PromptInput {
  system: string;
  user: string;
}

export interface CallOpts {
  /**
   * Progress callback for long-running model downloads. Called with
   * `progress` in 0..1 and an optional human-readable status message.
   * Currently only the Chrome built-in path emits this (Gemini Nano
   * is downloaded on first use); other tiers ignore the callback.
   */
  onDownload?: (progress: number, message?: string) => void;
  /**
   * JSON schema constraining the model's response. Honoured by tiers
   * that support grammar-constrained generation:
   *
   *   - Chrome built-in AI → passed as `responseConstraint`
   *   - MLC web-llm        → passed as `response_format.schema`
   *                          (XGrammar masks invalid tokens at sampling
   *                          time, so output is guaranteed to parse)
   *   - Ollama native API  → passed as `format`
   *
   * The remaining network providers (Anthropic / OpenAI / Google /
   * OpenAI-compatible) ignore the schema; we rely on prompt engineering
   * to fix the JSON shape, augmented by `response_format: json_object`
   * (OpenAI / OpenAI-compat) or `responseMimeType: application/json`
   * (Google) where supported.
   */
  schema?: Record<string, unknown>;
}

/**
 * Public LLM identity used by logging / UI labels. Mirrors the user-
 * facing tier + provider choice.
 */
export type LLMTag =
  | "chrome-builtin"
  | "web-llm"
  | "anthropic"
  | "openai"
  | "google"
  | "ollama"
  | "openai-compatible";

export interface LLM {
  complete(input: PromptInput, opts?: CallOpts): Promise<string>;
  /**
   * Streamed completion. Yields **delta** chunks (the new tokens since
   * the previous chunk), NOT the cumulative text-so-far. Consumers
   * accumulate themselves.
   */
  stream(input: PromptInput, opts?: CallOpts): AsyncIterable<string>;
  /**
   * Best-effort BCP-47 language detection. Implemented by the Chrome
   * built-in tier (via `LanguageDetector`); other tiers omit it and
   * the caller falls back to article metadata.
   */
  detectLanguage?(text: string): Promise<string | undefined>;
  readonly tag: LLMTag;
}

/**
 * Build an LLM client appropriate for the user's settings. All three
 * tiers go through here now: `browser-native` (Chrome built-in AI),
 * `local-bundle` (MLC web-llm in-browser), and `network` (any of the
 * remote providers).
 */
export async function getLLM(settings: Settings): Promise<LLM> {
  switch (settings.tier) {
    case "browser-native": {
      // Chrome's Prompt API on Chromium browsers. Firefox has no
      // built-in chat/instruction model — we surface a clear error
      // there so the user picks a different tier.
      if (await chromeBuiltinAvailable()) return makeChromeLLM();
      throw new Error(
        "Browser built-in AI isn't available on this browser. Switch the tier in Settings to In-browser bundle or Network.",
      );
    }
    case "local-bundle":
      return makeWebLLMLLM({
        modelId: settings.localBundleModel,
      });
    case "network":
      return makeNetworkLLM(settings);
  }
}

export function makeNetworkLLM(settings: Settings): LLM {
  switch (settings.networkProvider) {
    case "anthropic":
      return makeAnthropicLLM(settings);
    case "openai":
      return makeOpenAILLM(settings, "openai");
    case "openai-compatible":
      return makeOpenAILLM(settings, "openai-compatible");
    case "google":
      return makeGoogleLLM(settings);
    case "ollama":
      return makeOllamaLLM(settings);
  }
}

function makeChromeLLM(): LLM {
  return {
    tag: "chrome-builtin",
    complete: (input, opts) => promptChromeBuiltin(input, false, toChrome(opts)),
    async *stream(input, opts) {
      const it = await promptChromeBuiltin(input, true, toChrome(opts));
      yield* it;
    },
    detectLanguage: detectLanguageChromeBuiltin,
  };
}

function makeAnthropicLLM(settings: Settings): LLM {
  const cfg = settings.anthropic;
  if (!cfg.apiKey) {
    throw new Error("Anthropic API key not configured. Open the options page.");
  }
  return {
    tag: "anthropic",
    complete: (input) => promptAnthropic(cfg.apiKey, cfg.model, input, false),
    async *stream(input) {
      const it = await promptAnthropic(cfg.apiKey, cfg.model, input, true);
      yield* it;
    },
  };
}

function makeOpenAILLM(
  settings: Settings,
  variant: "openai" | "openai-compatible",
): LLM {
  let baseUrl: string;
  let apiKey: string;
  let model: string;
  if (variant === "openai") {
    baseUrl = "https://api.openai.com/v1";
    apiKey = settings.openai.apiKey;
    model = settings.openai.model;
    if (!apiKey) {
      throw new Error("OpenAI API key not configured. Open the options page.");
    }
  } else {
    baseUrl = settings.openaiCompatible.baseUrl;
    apiKey = settings.openaiCompatible.apiKey;
    model = settings.openaiCompatible.model;
    if (!baseUrl) {
      throw new Error(
        "OpenAI-compatible base URL not configured. Open the options page.",
      );
    }
  }
  if (!model) {
    throw new Error("Model name not configured for the network provider.");
  }
  return {
    tag: variant,
    complete: (input, opts) =>
      promptOpenAI(baseUrl, apiKey, model, input, false, { schema: opts?.schema }),
    async *stream(input, opts) {
      const it = await promptOpenAI(baseUrl, apiKey, model, input, true, {
        schema: opts?.schema,
      });
      yield* it;
    },
  };
}

function makeGoogleLLM(settings: Settings): LLM {
  const cfg = settings.google;
  if (!cfg.apiKey) {
    throw new Error("Google API key not configured. Open the options page.");
  }
  return {
    tag: "google",
    complete: (input, opts) =>
      promptGoogle(cfg.apiKey, cfg.model, input, false, { schema: opts?.schema }),
    async *stream(input, opts) {
      const it = await promptGoogle(cfg.apiKey, cfg.model, input, true, {
        schema: opts?.schema,
      });
      yield* it;
    },
  };
}

function makeOllamaLLM(settings: Settings): LLM {
  const cfg = settings.ollama;
  if (!cfg.baseUrl) {
    throw new Error("Ollama base URL not configured. Open the options page.");
  }
  return {
    tag: "ollama",
    complete: (input, opts) =>
      promptOllama(cfg.baseUrl, cfg.model, input, false, { schema: opts?.schema }),
    async *stream(input, opts) {
      const it = await promptOllama(cfg.baseUrl, cfg.model, input, true, {
        schema: opts?.schema,
      });
      yield* it;
    },
  };
}

function toChrome(opts: CallOpts | undefined): ChromePromptOpts | undefined {
  if (!opts) return undefined;
  return { onDownload: opts.onDownload, schema: opts.schema };
}

async function chromeBuiltinAvailable(): Promise<boolean> {
  try {
    if (typeof LanguageModel === "undefined") return false;
    const status = await LanguageModel.availability();
    return status === "available" || status === "downloadable" || status === "downloading";
  } catch {
    return false;
  }
}
