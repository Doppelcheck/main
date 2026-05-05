import { z } from "zod";

/**
 * Two top-level user-facing buckets:
 *
 *   - **browser-native** — uses the browser's own AI runtime
 *     (Chrome's Prompt API on Chromium). Fails clearly when not
 *     available; only Chromium currently ships a chat-style on-device
 *     LLM exposed to extensions.
 *
 *   - **network** — any LLM reachable over HTTP. Split into two
 *     conceptual subgroups in the UI (the storage shape is flat):
 *
 *       • Cloud APIs — Anthropic, OpenAI, Google Gemini.
 *       • Local server — Ollama (native API), or any OpenAI-compatible
 *         endpoint (LM Studio, llama.cpp server, vLLM, the companion
 *         `doppelcheck/gemma-server` zero-config Gemma 4 setup, …).
 */
type Tier = "browser-native" | "network";

export type NetworkProvider =
  | "anthropic"
  | "openai"
  | "google"
  | "ollama"
  | "openai-compatible";

const ProviderConfigSchemas = {
  anthropic: z.object({
    apiKey: z.string().default(""),
    model: z.string().default("claude-haiku-4-5-20251001"),
  }),
  openai: z.object({
    apiKey: z.string().default(""),
    model: z.string().default("gpt-4o-mini"),
  }),
  google: z.object({
    apiKey: z.string().default(""),
    model: z.string().default("gemini-2.5-flash"),
  }),
  ollama: z.object({
    baseUrl: z.string().default("http://localhost:11434"),
    model: z.string().default("llama3.2:3b"),
  }),
  /** Generic catch-all for any OpenAI-compatible chat-completions endpoint. */
  openaiCompatible: z.object({
    baseUrl: z.string().default(""),
    apiKey: z.string().default(""),
    model: z.string().default(""),
    /** Free-form label so the UI can remember which preset the user chose. */
    presetName: z.string().default(""),
  }),
};

export const SettingsSchema = z.object({
  tier: z.enum(["browser-native", "network"]).default("browser-native"),
  networkProvider: z
    .enum(["anthropic", "openai", "google", "ollama", "openai-compatible"])
    .default("anthropic"),

  anthropic: ProviderConfigSchemas.anthropic.default({}),
  openai: ProviderConfigSchemas.openai.default({}),
  google: ProviderConfigSchemas.google.default({}),
  ollama: ProviderConfigSchemas.ollama.default({}),
  openaiCompatible: ProviderConfigSchemas.openaiCompatible.default({}),

  braveApiKey: z.string().default(""),
  factCheckApiKey: z.string().default(""),
  customUrls: z.array(z.string().url()).default([]),
  maxClaims: z.number().int().min(1).max(10).default(5),
  uiLanguage: z.enum(["auto", "en", "de"]).default("auto"),
  showDebugLogs: z.boolean().default(false),
  autoVerify: z.boolean().default(true),
});
export type Settings = z.infer<typeof SettingsSchema>;
export type AnthropicConfig = Settings["anthropic"];
export type OpenAIConfig = Settings["openai"];
export type GoogleConfig = Settings["google"];
export type OllamaConfig = Settings["ollama"];
export type OpenAICompatibleConfig = Settings["openaiCompatible"];

export const DEFAULT_SETTINGS: Settings = SettingsSchema.parse({});

/**
 * Forward-migrate a possibly-old settings blob to the current shape.
 * Handles two historical layouts:
 *
 *   - Original flat shape: `llmTier` + `anthropicApiKey` / `ollamaBaseUrl`
 *     fields. Mapped to `tier` + `networkProvider` + nested per-provider
 *     configs.
 *   - Three-tier shape with `local-bundle` (transformers.js, then MLC
 *     web-llm). The in-browser tier was retired — old `local-bundle`
 *     users are moved to `network` + `anthropic` (with whatever key
 *     they had, or empty so the Options page surfaces the missing-key
 *     error normally).
 */
export function migrateSettings(raw: unknown): unknown {
  if (typeof raw !== "object" || raw === null) return raw;
  const r = raw as Record<string, unknown>;

  // Drop the retired in-browser-bundle fields wherever they appear.
  delete r.localBundleModel;
  delete r.localBundleDevice;

  if (typeof r.tier === "string") {
    if (r.tier === "local-bundle") {
      r.tier = "network";
      if (typeof r.networkProvider !== "string") r.networkProvider = "anthropic";
    }
    return r;
  }

  const oldTier = typeof r.llmTier === "string" ? r.llmTier : undefined;
  let tier: Tier = "browser-native";
  let networkProvider: NetworkProvider = "anthropic";
  switch (oldTier) {
    case "chrome-builtin":
      tier = "browser-native";
      break;
    case "local":
      // Retired in-browser tier — move to network + anthropic.
      tier = "network";
      networkProvider = "anthropic";
      break;
    case "ollama":
      tier = "network";
      networkProvider = "ollama";
      break;
    case "anthropic":
      tier = "network";
      networkProvider = "anthropic";
      break;
  }

  const out: Record<string, unknown> = { ...r, tier, networkProvider };
  out.anthropic = {
    apiKey: typeof r.anthropicApiKey === "string" ? r.anthropicApiKey : "",
    model:
      typeof r.anthropicModel === "string"
        ? r.anthropicModel
        : "claude-haiku-4-5-20251001",
  };
  out.ollama = {
    baseUrl:
      typeof r.ollamaBaseUrl === "string" ? r.ollamaBaseUrl : "http://localhost:11434",
    model: typeof r.ollamaModel === "string" ? r.ollamaModel : "llama3.2:3b",
  };

  // Drop superseded flat fields so they don't keep living in storage.
  delete out.llmTier;
  delete out.anthropicApiKey;
  delete out.anthropicModel;
  delete out.ollamaBaseUrl;
  delete out.ollamaModel;
  return out;
}

export interface ExtractedPage {
  url: string;
  title: string;
  author?: string;
  published?: string;
  language?: string;
  wordCount: number;
  markdown: string;
  text: string;
}

export interface Claim {
  id: string;
  /** The factual claim, paraphrased clearly. May not appear verbatim on the page. */
  text: string;
  /** Why this claim is load-bearing for the article. */
  rationale?: string;
  /**
   * A verbatim sentence/passage from the article that contains this claim.
   * Used for in-page highlighting (since `text` is paraphrased and may not
   * match the page).
   */
  quote?: string;
}

export interface SearchHit {
  url: string;
  title: string;
  snippet: string;
  domain: string;
  customDomain: boolean;
}

export interface FactCheckHit {
  publisher: string;
  publisherSite?: string;
  url: string;
  reviewDate?: string;
  rating: string;
  claimText: string;
  language?: string;
}

export type Alignment = "agrees" | "disagrees" | "unrelated";

export interface Verdict {
  claimId: string;
  url: string;
  alignment: Alignment;
  evidence: string;
  explanation: string;
}

export type LogLevel = "info" | "warn" | "error";

export type Phase =
  | "idle"
  | "extracting"
  | "detect-language"
  | "model-download"
  | "model-test"
  | "claim-extraction"
  | "fact-check"
  | "query-generation"
  | "search"
  | "fetch"
  | "compare"
  | "highlight"
  | "done"
  | "error";

export interface LogEntry {
  /** Wall-clock ms (Date.now). */
  at: number;
  level: LogLevel;
  /** Coarse pipeline phase — drives the status bar. */
  phase: Phase;
  message: string;
  /** Progress in 0..1 for long-running steps (model download, etc.). */
  progress?: number;
  /** When the log line belongs to a specific claim's verify flow. */
  claimId?: string;
}

export type ServerEvent =
  | { kind: "log"; entry: LogEntry }
  | { kind: "page-extracted"; page: ExtractedPage }
  | { kind: "claims-start" }
  | { kind: "claim"; claim: Claim }
  | { kind: "claims-done" }
  | { kind: "fact-check"; claimId: string; hits: FactCheckHit[] }
  | { kind: "search-results"; claimId: string; hits: SearchHit[] }
  | { kind: "verdict"; verdict: Verdict }
  | { kind: "verify-done"; claimId: string }
  | { kind: "error"; message: string; claimId?: string };

export type ClientCommand =
  | { kind: "analyze"; tabId: number }
  | { kind: "verify"; tabId: number; claim: Claim; pageUrl: string }
  | { kind: "highlight-claim"; tabId: number; claimText: string }
  | { kind: "clear-highlights"; tabId: number };

export type ContentRequest =
  | { kind: "ping" }
  | { kind: "extract" }
  | { kind: "highlight"; ranges: { text: string; type: HighlightType }[] }
  | { kind: "clear-highlights" };

export type HighlightType = "claim" | "evidence-agree" | "evidence-disagree";
