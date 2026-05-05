/**
 * Shared Server-Sent Events parser used by every streaming network
 * provider that follows the `data: {json}\n\n` convention (Anthropic,
 * OpenAI, Google Gemini, plus any OpenAI-compatible endpoint).
 *
 * Ollama is the odd one out — it streams plain newline-delimited JSON
 * (NDJSON), not SSE. Its parser lives in `ollama.ts`.
 */

/**
 * Read an SSE response body and yield the delta strings extracted from
 * each event by `pickDelta`. Events whose data line is `[DONE]` end
 * the stream. Malformed JSON events are silently skipped.
 *
 * @param body The response body (must be present; caller checks).
 * @param pickDelta Provider-specific function that pulls the new text
 *   from one event's parsed JSON. Return `undefined` to skip an event
 *   that doesn't carry text (keep-alives, role announcements, etc).
 */
export async function* readSSEDeltas<T>(
  body: ReadableStream<Uint8Array>,
  pickDelta: (event: T) => string | undefined,
): AsyncIterable<string> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // SSE events are delimited by blank lines. Each event has one or
    // more `field: value` lines; we only care about `data:`.
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";
    for (const evt of events) {
      const dataLine = evt.split("\n").find((l) => l.startsWith("data:"));
      if (!dataLine) continue;
      const payload = dataLine.slice(5).trim();
      if (!payload) continue;
      if (payload === "[DONE]") return;
      let parsed: T;
      try {
        parsed = JSON.parse(payload) as T;
      } catch {
        continue; // malformed event — skip
      }
      const delta = pickDelta(parsed);
      if (typeof delta === "string" && delta.length > 0) yield delta;
    }
  }
}
