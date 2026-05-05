/**
 * Anthropic Messages API client over fetch. We avoid the @anthropic-ai/sdk
 * package to keep the extension bundle small — the API surface we need is
 * a single POST with optional SSE streaming.
 *
 * Note: this runs in a Manifest V3 service worker, so `fetch` is available
 * but not `XMLHttpRequest`. The SDK's `dangerouslyAllowBrowser` mode would
 * also work — fetch is just lighter.
 */

import type { PromptInput } from "./index";
import { readSSEDeltas } from "./sse";

const ENDPOINT = "https://api.anthropic.com/v1/messages";
const ANTHROPIC_VERSION = "2023-06-01";

interface MessagesBody {
  model: string;
  max_tokens: number;
  system?: string;
  messages: { role: "user" | "assistant"; content: string }[];
  stream?: boolean;
}

export async function promptAnthropic(
  apiKey: string,
  model: string,
  input: PromptInput,
  streaming: false,
): Promise<string>;
export async function promptAnthropic(
  apiKey: string,
  model: string,
  input: PromptInput,
  streaming: true,
): Promise<AsyncIterable<string>>;
export async function promptAnthropic(
  apiKey: string,
  model: string,
  input: PromptInput,
  streaming: boolean,
): Promise<string | AsyncIterable<string>> {
  const body: MessagesBody = {
    model,
    max_tokens: 1024,
    system: input.system,
    messages: [{ role: "user", content: input.user }],
    stream: streaming,
  };
  const res = await fetch(ENDPOINT, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": ANTHROPIC_VERSION,
      "anthropic-dangerous-direct-browser-access": "true",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Anthropic API ${res.status}: ${detail.slice(0, 300)}`);
  }
  if (!streaming) {
    const json = (await res.json()) as {
      content: { type: string; text?: string }[];
    };
    return json.content
      .filter((c) => c.type === "text" && typeof c.text === "string")
      .map((c) => c.text!)
      .join("");
  }
  if (!res.body) throw new Error("Anthropic streaming response has no body");
  return readSSEDeltas<AnthropicEvent>(res.body, (e) =>
    e.type === "content_block_delta" && e.delta?.type === "text_delta"
      ? e.delta.text
      : undefined,
  );
}

interface AnthropicEvent {
  type?: string;
  delta?: { type?: string; text?: string };
}
