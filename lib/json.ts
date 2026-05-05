/**
 * LLMs occasionally wrap JSON in code fences, prefix it with prose, or
 * truncate mid-stream. This module is the single place that copes with that.
 *
 * One-off thing worth knowing: Qwen 3 instruct models emit a
 * `<think>… reasoning …</think>` block before the actual answer
 * (built-in chain-of-thought). We strip those before extracting JSON
 * so the existing tolerant scanner doesn't trip on `{` characters
 * inside the model's reasoning text.
 */

/** Drop any `<think>…</think>` chain-of-thought blocks. */
function stripThinking(text: string): string {
  return text.replace(/<think>[\s\S]*?<\/think>/gi, "").trim();
}

/** Pull the first balanced JSON value out of an LLM's reply. */
export function extractJSON(text: string): string | undefined {
  const cleaned = stripThinking(text);
  const fenced = /```(?:json)?\s*([\s\S]*?)```/.exec(cleaned);
  const body = fenced?.[1] ?? cleaned;
  // Find first { or [ and walk forward tracking balance.
  for (let i = 0; i < body.length; i++) {
    const ch = body[i];
    if (ch !== "{" && ch !== "[") continue;
    const close = ch === "{" ? "}" : "]";
    let depth = 0;
    let inStr = false;
    let esc = false;
    for (let j = i; j < body.length; j++) {
      const c = body[j]!;
      if (inStr) {
        if (esc) esc = false;
        else if (c === "\\") esc = true;
        else if (c === '"') inStr = false;
        continue;
      }
      if (c === '"') inStr = true;
      else if (c === ch) depth++;
      else if (c === close) {
        depth--;
        if (depth === 0) return body.slice(i, j + 1);
      }
    }
    return undefined;
  }
  return undefined;
}

export function parseJSON<T>(text: string): T | undefined {
  const blob = extractJSON(text);
  if (!blob) return undefined;
  try {
    return JSON.parse(blob) as T;
  } catch {
    return undefined;
  }
}

/**
 * Streamed-JSON-array reader: consumes a growing string and yields each
 * complete top-level array element as it arrives. Lets us stream claims
 * to the UI as the LLM produces them, instead of waiting for the whole
 * response. Handles malformed prefixes and trailing prose gracefully.
 */
export function* readArrayElements(buffer: string): Iterable<string> {
  // Same `<think>` pre-strip as `extractJSON` — without it, a `{`
  // appearing in Qwen's reasoning text would be picked up as the
  // start of an array element.
  const cleaned = stripThinking(buffer);
  const start = cleaned.indexOf("[");
  if (start === -1) return;
  // Re-bind to the cleaned string for the rest of the scan.
  buffer = cleaned;
  let depth = 0;
  let inStr = false;
  let esc = false;
  let elemStart = -1;
  for (let i = start; i < buffer.length; i++) {
    const c = buffer[i]!;
    if (inStr) {
      if (esc) esc = false;
      else if (c === "\\") esc = true;
      else if (c === '"') inStr = false;
      continue;
    }
    if (c === '"') {
      inStr = true;
      if (depth === 1 && elemStart === -1) elemStart = i;
      continue;
    }
    if (c === "{" || c === "[") {
      depth++;
      if (depth === 2 && elemStart === -1) elemStart = i - 1;
      continue;
    }
    if (c === "}" || c === "]") {
      depth--;
      if (depth === 1 && elemStart !== -1) {
        yield buffer.slice(elemStart, i + 1).trim();
        elemStart = -1;
      }
      if (depth === 0) return;
    }
  }
}
