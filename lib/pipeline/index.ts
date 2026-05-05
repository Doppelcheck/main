/**
 * High-level pipeline interface — what the background actually needs from
 * "the LLM" to drive the verify flow.
 *
 * Two tiers, both of which resolve to a generative LLM and the single
 * `LLMPipeline` implementation:
 *
 *   - **browser-native** → Chrome built-in AI (Gemini Nano)
 *   - **network**        → Anthropic / OpenAI / Google / Ollama / OpenAI-compat
 */

import type { Alignment, Claim, ExtractedPage, LogLevel, Phase, Settings } from "@/types";
import { LLMPipeline } from "./llm-pipeline";
import { getLLM } from "@/lib/llm";

export interface PipelineCallOpts {
  /** 0..1 progress for long-running model downloads. */
  onDownload?: (progress: number, message?: string) => void;
  /** Pipeline-internal log forwarding; mirrors to the side panel + console. */
  log?: (level: LogLevel, phase: Phase, message: string) => void;
}

export interface ComparisonResult {
  alignment: Alignment;
  evidence: string;
  explanation: string;
  /** Optional intermediate "what the source says" — generative tiers emit it. */
  sourceSays?: string;
}

export interface Pipeline {
  /** UI-friendly identifier for status bar / debug log. */
  readonly tag: string;

  extractClaims(
    page: ExtractedPage,
    n: number,
    opts?: PipelineCallOpts,
  ): AsyncIterable<Claim>;

  generateQuery(
    claim: string,
    language: string | undefined,
    opts?: PipelineCallOpts,
  ): Promise<string>;

  compareToSource(
    claim: string,
    source: { url: string; title: string; text: string },
    language: string | undefined,
    opts?: PipelineCallOpts,
  ): Promise<ComparisonResult>;

  detectLanguage?(text: string): Promise<string | undefined>;
}

export async function getPipeline(settings: Settings): Promise<Pipeline> {
  const llm = await getLLM(settings);
  return new LLMPipeline(llm);
}
