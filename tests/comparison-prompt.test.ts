import { describe, expect, it } from "vitest";
import { SOURCE_CHAR_CAP, comparisonPrompt } from "@/lib/llm/prompts";

/**
 * The source-length budget is ONE number. `compareToSource` applies
 * `SOURCE_CHAR_CAP` and appends a visible truncation marker; the prompt
 * builder must then pass that text through untouched.
 *
 * It did not always: `comparisonPrompt` carried its own `slice(0, 12_000)`
 * while the caller capped at 10_000, so the prompt's limit was unreachable
 * code that silently disagreed with the real one. Nothing failed — which is
 * exactly why it survived. These tests make the disagreement loud.
 */
describe("comparisonPrompt", () => {
  const build = (text: string) =>
    comparisonPrompt("a claim", "https://example.com/a", "A title", text, "English");

  // REGRESSION: a second slice reappearing inside comparisonPrompt would
  // truncate text the caller had already deliberately capped and marked.
  it("passes the source text through without truncating it again", () => {
    const text = "x".repeat(SOURCE_CHAR_CAP + 5_000);
    expect(build(text).user).toContain(text);
  });

  // REGRESSION: the caller's truncation marker is what tells the model the
  // source is incomplete. A second slice would cut the marker off the end.
  it("keeps the caller's truncation marker intact", () => {
    const marker = "[…source truncated for context window]";
    const text = "y".repeat(SOURCE_CHAR_CAP) + "\n\n" + marker;
    expect(build(text).user).toContain(marker);
  });

  it("includes the claim, the source url and the title", () => {
    const user = build("short source").user;
    expect(user).toContain("a claim");
    expect(user).toContain("https://example.com/a");
    expect(user).toContain("A title");
  });

  // REGRESSION: the three alignment labels in the prompt text must stay in
  // step with COMPARISON_SCHEMA's enum and with normalizeAlignment's output.
  it("names exactly the three alignment labels the schema allows", () => {
    const user = build("short source").user;
    expect(user).toContain('"agrees"');
    expect(user).toContain('"disagrees"');
    expect(user).toContain('"unrelated"');
  });
});
