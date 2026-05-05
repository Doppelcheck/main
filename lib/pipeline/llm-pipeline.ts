/**
 * Pipeline implementation backed by a generative LLM. Used for two
 * tiers:
 *
 *   - `browser-native` on Chromium → Chrome built-in AI (Gemini Nano)
 *   - `network` (any browser)      → Anthropic / OpenAI / Google /
 *                                    Ollama / OpenAI-compatible
 *
 * Holds the prompts + JSON-schema + tolerant-parser logic; the
 * background module just calls `extractClaims`, `generateQuery`, and
 * `compareToSource`.
 */

import type { Alignment, Claim, ExtractedPage } from "@/types";
import type { LLM } from "@/lib/llm";
import {
  CLAIMS_SCHEMA,
  COMPARISON_SCHEMA,
  QUERY_SCHEMA,
  claimExtractionPrompt,
  comparisonPrompt,
  searchQueryPrompt,
} from "@/lib/llm/prompts";
import { parseJSON, readArrayElements } from "@/lib/json";
import type { ComparisonResult, Pipeline, PipelineCallOpts } from "./index";

export class LLMPipeline implements Pipeline {
  readonly detectLanguage?: Pipeline["detectLanguage"];

  constructor(private readonly llm: LLM) {
    // Late-bind so `this.llm` is set first. TS class-field initializers
    // would otherwise complain about using `llm` before init.
    this.detectLanguage = llm.detectLanguage?.bind(llm);
  }

  get tag() {
    return this.llm.tag;
  }

  async *extractClaims(
    page: ExtractedPage,
    n: number,
    opts?: PipelineCallOpts,
  ): AsyncIterable<Claim> {
    const prompt = claimExtractionPrompt(page, n);
    const callOpts = { schema: CLAIMS_SCHEMA, onDownload: opts?.onDownload };
    let buffer = "";
    let lastReport = 0;
    const seen = new Set<string>();
    const emitted: Claim[] = [];

    const tryConsume = (
      obj: { text?: unknown; rationale?: unknown; quote?: unknown } | undefined,
    ): Claim | undefined => {
      if (emitted.length >= n) return undefined;
      if (!obj || typeof obj.text !== "string" || !obj.text.trim()) return undefined;
      const claim: Claim = {
        id: `c${emitted.length + 1}`,
        text: obj.text.trim(),
        rationale: typeof obj.rationale === "string" ? obj.rationale : undefined,
        quote: typeof obj.quote === "string" ? obj.quote.trim() : undefined,
      };
      emitted.push(claim);
      return claim;
    };

    try {
      for await (const delta of this.llm.stream(prompt, callOpts)) {
        buffer += delta;
        if (buffer.length - lastReport > 400) {
          lastReport = buffer.length;
          opts?.log?.(
            "info",
            "claim-extraction",
            `Receiving model output (${buffer.length.toLocaleString()} chars)`,
          );
        }
        for (const elem of readArrayElements(buffer)) {
          if (seen.has(elem)) continue;
          seen.add(elem);
          const claim = tryConsume(
            parseJSON<{ text?: unknown; rationale?: unknown; quote?: unknown }>(elem),
          );
          if (claim) yield claim;
          if (emitted.length >= n) return;
        }
      }
    } catch (err) {
      opts?.log?.(
        "warn",
        "claim-extraction",
        `Streaming failed (${(err as Error).message}); falling back to one-shot completion.`,
      );
      buffer = await this.llm.complete(prompt, callOpts);
    }

    // Closing-bracket pass: the streaming reader misses the last element
    // until the array terminator arrives.
    const arr = parseJSON<{ text?: unknown; rationale?: unknown; quote?: unknown }[]>(
      buffer,
    );
    if (Array.isArray(arr)) {
      const known = new Set(emitted.map((c) => c.text));
      for (const obj of arr) {
        const t = typeof obj?.text === "string" ? obj.text.trim() : undefined;
        if (!t || known.has(t)) continue;
        const claim = tryConsume(obj);
        if (claim) yield claim;
        if (emitted.length >= n) return;
      }
    }

    if (emitted.length === 0) {
      const preview = buffer.replace(/\s+/g, " ").trim().slice(0, 240);
      opts?.log?.(
        "warn",
        "claim-extraction",
        preview
          ? `No parseable claims. Raw model output (truncated): ${preview}…`
          : "No model output received.",
      );
    }
  }

  async generateQuery(
    claim: string,
    language: string | undefined,
    opts?: PipelineCallOpts,
  ): Promise<string> {
    const reply = await this.llm.complete(searchQueryPrompt(claim, language), {
      schema: QUERY_SCHEMA,
      onDownload: opts?.onDownload,
    });
    const parsed = parseJSON<{ query?: string }>(reply);
    return sanitizeQuery(parsed?.query ?? reply) || claim;
  }

  async compareToSource(
    claim: string,
    source: { url: string; title: string; text: string },
    language: string | undefined,
    opts?: PipelineCallOpts,
  ): Promise<ComparisonResult> {
    // Cap source text so the comparison prompt fits in a small-context
    // local model. SmolLM2-360M ships with `context_window_size: 4096`,
    // and the rest of the prompt (system message + claim + JSON
    // schema instructions) eats ~600 tokens. ~10 000 chars of source
    // text is roughly 2500–3500 tokens depending on language, leaving
    // headroom for the ~512-token reply. Larger remote models ignore
    // this cap effectively (they comfortably handle the full source).
    const SOURCE_CHAR_CAP = 10_000;
    const truncated =
      source.text.length > SOURCE_CHAR_CAP
        ? source.text.slice(0, SOURCE_CHAR_CAP) + "\n\n[…source truncated for context window]"
        : source.text;
    const reply = await this.llm.complete(
      comparisonPrompt(claim, source.url, source.title, truncated, language),
      { schema: COMPARISON_SCHEMA, onDownload: opts?.onDownload },
    );
    const parsed = parseJSON<{
      source_says?: string;
      alignment: string;
      evidence: string;
      explanation: string;
    }>(reply);
    if (!parsed) {
      const preview = reply.replace(/\s+/g, " ").trim().slice(0, 200);
      throw new Error(`unparseable model reply: ${preview}…`);
    }
    return {
      alignment: normalizeAlignment(parsed.alignment),
      evidence: (parsed.evidence ?? "").trim(),
      explanation: (parsed.explanation ?? "").trim(),
      sourceSays: parsed.source_says,
    };
  }

}

function normalizeAlignment(s: string | undefined): Alignment {
  const v = (s ?? "").toLowerCase().trim();
  if (v.startsWith("agree")) return "agrees";
  if (v.startsWith("disagree") || v.startsWith("contradict")) return "disagrees";
  return "unrelated";
}

function sanitizeQuery(reply: string): string {
  return reply
    .replace(/^["'`\s]+|["'`\s]+$/g, "")
    .split("\n")[0]!
    .replace(/^(query|search)\s*:\s*/i, "")
    .trim()
    .slice(0, 200);
}
