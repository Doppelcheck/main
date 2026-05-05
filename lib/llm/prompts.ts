/**
 * Centralised prompt definitions and the JSON schemas used by tiers
 * that support grammar-constrained generation (Chrome built-in's
 * `responseConstraint`, Ollama's `format`). The schemas are *also*
 * reflected in the prompt text so the network providers that don't
 * honour structured-output fields (Anthropic, plus older OpenAI-compat
 * endpoints) still produce matching JSON via prompt engineering alone.
 *
 * Without grammar constraints, Gemini Nano in particular frequently
 * wraps JSON in prose, emits Markdown bullets, or starts with "Here
 * are the claims:" — the schema is the only reliable way to get
 * parseable output from small models.
 */

import type { ExtractedPage } from "@/types";

const ARTICLE_LIMIT = 16_000;

export const CLAIMS_SCHEMA = {
  type: "array",
  minItems: 1,
  items: {
    type: "object",
    additionalProperties: false,
    properties: {
      text: { type: "string" },
      rationale: { type: "string" },
      quote: { type: "string" },
    },
    required: ["text", "quote"],
  },
} as const satisfies Record<string, unknown>;

/**
 * The order of properties matters: with `responseConstraint`, the model
 * fills them in the order declared. Putting `source_says` before
 * `alignment` forces the model to articulate the source's actual claim
 * *before* labelling — a small chain-of-thought that markedly improves
 * label/explanation consistency on Gemini Nano.
 */
export const COMPARISON_SCHEMA = {
  type: "object",
  additionalProperties: false,
  properties: {
    source_says: { type: "string" },
    alignment: { type: "string", enum: ["agrees", "disagrees", "unrelated"] },
    evidence: { type: "string" },
    explanation: { type: "string" },
  },
  required: ["source_says", "alignment", "evidence", "explanation"],
} as const satisfies Record<string, unknown>;

export const QUERY_SCHEMA = {
  type: "object",
  additionalProperties: false,
  properties: { query: { type: "string" } },
  required: ["query"],
} as const satisfies Record<string, unknown>;

export function claimExtractionPrompt(page: ExtractedPage, n: number) {
  const body = page.text.slice(0, ARTICLE_LIMIT);
  const lang = page.language || "the article's language";
  return {
    system:
      "You are an analyst who isolates the verifiable factual claims in an article — not opinions, not background framing, not author commentary.",
    user: `Article title: ${page.title}
Source: ${page.url}
${page.author ? `Author: ${page.author}\n` : ""}${page.published ? `Published: ${page.published}\n` : ""}Article language: ${lang}
---
${body}
---

List the ${n} most significant **falsifiable factual claims** in this article. A claim is good if a reader could plausibly verify it against an independent source. Skip vague generalities and value judgments.

For each claim produce three fields:
- "text": one paraphrased sentence stating the claim, in ${lang}.
- "rationale": one short sentence in ${lang} on why the claim is load-bearing for the article.
- "quote": a *verbatim* passage of 5–25 words from the article above that contains this claim. The quote MUST appear character-for-character in the article body — do not paraphrase, translate, or shorten with "…". This is used to highlight the claim on the page.

Reply ONLY with a JSON array of these objects. No prose, no code fences.`,
  };
}

export function searchQueryPrompt(claim: string, lang: string | undefined) {
  return {
    system:
      "Turn a factual claim into a concise web search query. Reply with JSON only.",
    user: `Claim: ${claim}
${lang ? `Article language: ${lang}\n` : ""}
Produce a 4–8 word web search query that would surface independent reporting on this claim. Include named entities and dates if present. No operators like site: or quotes.

Reply ONLY with JSON of this shape: {"query":"<your query>"}
No prose. No code fences.`,
  };
}

export function comparisonPrompt(
  claim: string,
  sourceUrl: string,
  sourceTitle: string,
  sourceText: string,
  language: string | undefined,
) {
  const trimmed = sourceText.slice(0, 12_000);
  const lang = language || "the language of the claim";
  return {
    system:
      "You decide whether one external source agrees with, contradicts, or is unrelated to a single factual claim. Be precise: the alignment label and explanation MUST agree with each other.",
    user: `Claim:
"${claim}"

External source (${sourceTitle} — ${sourceUrl}):
---
${trimmed}
---

Process:
1. First identify what the source actually asserts about the same fact (the topic of the claim). If it doesn't address it at all, that's "unrelated".
2. Then judge alignment:
   - "agrees": the source asserts substantially the same fact as the claim.
   - "disagrees": the source asserts a fact that materially contradicts the claim.
   - "unrelated": the source does not address this fact, even if it discusses the same topic.

Reply ONLY with this JSON. Fields MUST be filled in this order:
{
  "source_says": "<one sentence in ${lang}: what the source asserts about this same fact, or 'does not address it'>",
  "alignment": "agrees" | "disagrees" | "unrelated",
  "evidence": "<verbatim 1–2 sentence quote from the source above; empty string if unrelated>",
  "explanation": "<one neutral sentence in ${lang} explaining the alignment; MUST be consistent with the label above>"
}

Output language for source_says and explanation: ${lang}. No prose. No code fences.`,
  };
}
