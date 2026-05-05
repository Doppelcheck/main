/**
 * Ollama HTTP client. Talks to a locally-running Ollama instance — same
 * setup the legacy Python implementation used.
 *
 * Two things to know about Ollama from a browser:
 *
 * 1. **Origin allow-list.** Ollama checks the request `Origin` header
 *    server-side. Browser extensions send their own `chrome-extension://`
 *    or `moz-extension://` origin, which Ollama rejects by default. The
 *    user must run the daemon with:
 *
 *        OLLAMA_ORIGINS="chrome-extension://*,moz-extension://*" ollama serve
 *
 *    or the catch-all `OLLAMA_ORIGINS=*`. We surface that hint clearly
 *    in the options page; the error message here also points to it.
 *
 * 2. **Structured output.** Ollama since v0.5 accepts `format: <schema>`
 *    on the chat endpoint and does grammar-constrained generation. We
 *    pass the same schemas the Chrome built-in tier uses, so JSON
 *    parsing is reliable across the on-device and Ollama paths.
 */

import type { PromptInput } from "./index";

const CHAT_PATH = "/api/chat";
const TAGS_PATH = "/api/tags";

interface OllamaChatBody {
  model: string;
  messages: { role: "system" | "user" | "assistant"; content: string }[];
  stream: boolean;
  /** Either the literal string "json" (any JSON) or a JSON schema object. */
  format?: "json" | Record<string, unknown>;
  /** Per-call options, e.g. `temperature`. */
  options?: Record<string, unknown>;
}

export interface OllamaPromptOpts {
  schema?: Record<string, unknown>;
  /** Lower temperature = more deterministic output. */
  temperature?: number;
}

export async function promptOllama(
  baseUrl: string,
  model: string,
  input: PromptInput,
  streaming: false,
  opts?: OllamaPromptOpts,
): Promise<string>;
export async function promptOllama(
  baseUrl: string,
  model: string,
  input: PromptInput,
  streaming: true,
  opts?: OllamaPromptOpts,
): Promise<AsyncIterable<string>>;
export async function promptOllama(
  baseUrl: string,
  model: string,
  input: PromptInput,
  streaming: boolean,
  opts: OllamaPromptOpts = {},
): Promise<string | AsyncIterable<string>> {
  const body: OllamaChatBody = {
    model,
    messages: [
      { role: "system", content: input.system },
      { role: "user", content: input.user },
    ],
    stream: streaming,
    options: { temperature: opts.temperature ?? 0.3 },
  };
  if (opts.schema) body.format = opts.schema;

  const res = await fetchOllama(baseUrl, CHAT_PATH, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Ollama ${res.status}: ${detail.slice(0, 200)}`);
  }

  if (!streaming) {
    const json = (await res.json()) as { message?: { content?: string } };
    return json.message?.content ?? "";
  }
  if (!res.body) throw new Error("Ollama streaming response has no body");
  return parseNDJSON(res.body);
}

/** Yields delta `message.content` chunks from Ollama's NDJSON stream. */
async function* parseNDJSON(
  body: ReadableStream<Uint8Array>,
): AsyncIterable<string> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      const t = line.trim();
      if (!t) continue;
      try {
        const json = JSON.parse(t) as {
          message?: { content?: string };
          done?: boolean;
        };
        if (json.message?.content) yield json.message.content;
        if (json.done) return;
      } catch {
        // Skip malformed lines.
      }
    }
  }
  if (buffer.trim()) {
    try {
      const json = JSON.parse(buffer) as { message?: { content?: string } };
      if (json.message?.content) yield json.message.content;
    } catch {
      /* ignore */
    }
  }
}

/**
 * Probe the Ollama daemon. Returns the list of installed model tags on
 * success, or a structured error the options page can render.
 */
export async function probeOllama(
  baseUrl: string,
): Promise<
  | { ok: true; models: string[] }
  | { ok: false; reason: "unreachable" | "cors" | "http"; detail: string }
> {
  try {
    const res = await fetchOllama(baseUrl, TAGS_PATH, { method: "GET" });
    if (!res.ok) {
      return {
        ok: false,
        reason: "http",
        detail: `${res.status} ${res.statusText}`,
      };
    }
    const json = (await res.json()) as { models?: { name?: string }[] };
    const models = (json.models ?? [])
      .map((m) => m.name)
      .filter((n): n is string => typeof n === "string");
    return { ok: true, models };
  } catch (err) {
    const msg = (err as Error).message;
    // Browser CORS rejections produce TypeError "NetworkError…" / "Failed to fetch".
    // Without further detail the browser doesn't distinguish between
    // "daemon not running" and "daemon up but origin blocked", so we
    // signal "cors" and let the UI show the OLLAMA_ORIGINS hint.
    if (/network|fetch|cors/i.test(msg)) {
      return { ok: false, reason: "cors", detail: msg };
    }
    return { ok: false, reason: "unreachable", detail: msg };
  }
}

function fetchOllama(
  baseUrl: string,
  path: string,
  init: RequestInit,
): Promise<Response> {
  const url = `${baseUrl.replace(/\/+$/, "")}${path}`;
  return fetch(url, init);
}
