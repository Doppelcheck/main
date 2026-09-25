import { describe, expect, it } from "vitest";
import { normalizeAlignment } from "@/lib/pipeline/llm-pipeline";

/**
 * `compareToSource` maps a model's free-text alignment label onto the
 * three-value `Alignment` union. Only two of the six LLM tiers actually
 * enforce the schema enum: `chrome-builtin` (`responseConstraint`) and
 * `ollama` (`format`). The OpenAI-compatible tier sends
 * `response_format: {type:"json_object"}` — any JSON, no enum — and the
 * Google tier sends only `responseMimeType` (see lib/llm/index.ts:33,
 * which documents this explicitly). So an unconstrained model's phrasing
 * reaches this function verbatim, and a mapping error here is shown to
 * the user as a source verdict.
 *
 * The regression each test below guards against is named in its title.
 */
describe("normalizeAlignment", () => {
  it("maps the three schema-constrained labels to themselves", () => {
    expect(normalizeAlignment("agrees")).toBe("agrees");
    expect(normalizeAlignment("disagrees")).toBe("disagrees");
    expect(normalizeAlignment("unrelated")).toBe("unrelated");
  });

  it("is case- and whitespace-insensitive", () => {
    expect(normalizeAlignment("  AGREES ")).toBe("agrees");
    expect(normalizeAlignment("Disagrees")).toBe("disagrees");
  });

  it("reads 'contradicts' as disagreement", () => {
    expect(normalizeAlignment("contradicts")).toBe("disagrees");
  });

  // REGRESSION: a negated phrasing used to fall through the
  // startsWith("agree")/startsWith("disagree") prefix test and land on
  // "unrelated" — presenting a source that CONTRADICTS the claim to the
  // user as irrelevant to it. That is the worst possible mislabelling
  // for a fact-checking tool: the contradiction disappears silently.
  it("does not read a negated agreement as unrelated", () => {
    expect(normalizeAlignment("does not agree")).toBe("disagrees");
    expect(normalizeAlignment("not agree")).toBe("disagrees");
    expect(normalizeAlignment("doesn't agree")).toBe("disagrees");
    expect(normalizeAlignment("no agreement")).toBe("disagrees");
  });

  // REGRESSION: "unsupported" / "refutes" / "denies" are the other
  // phrasings an unconstrained model reaches for. They must not be read
  // as "unrelated" either.
  it("reads refutation vocabulary as disagreement", () => {
    expect(normalizeAlignment("refutes")).toBe("disagrees");
    expect(normalizeAlignment("refuted")).toBe("disagrees");
    expect(normalizeAlignment("contradicted")).toBe("disagrees");
  });

  // REGRESSION: the fallback must stay "unrelated" — an unrecognised or
  // missing label is exactly the case where the tool should claim
  // nothing, rather than guess a verdict.
  it("falls back to unrelated for an unrecognised or missing label", () => {
    expect(normalizeAlignment("banana")).toBe("unrelated");
    expect(normalizeAlignment("")).toBe("unrelated");
    expect(normalizeAlignment(undefined)).toBe("unrelated");
  });
});
