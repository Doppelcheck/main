/**
 * OpenAI Chat Completions client. Also covers any OpenAI-compatible
 * endpoint (OpenRouter, LM Studio, Groq, Together, vLLM, llama.cpp
 * server, Ollama via /v1, …) by pointing `baseUrl` at it.
 *
 * For structured output we use `response_format: { type: "json_object" }`,
 * which is the de-facto-standard JSON mode supported by virtually all
 * OpenAI-compatible servers. Strict JSON-schema mode is stricter but
 * incompatible with our top-level array schemas (CLAIMS_SCHEMA), so we
 * stick with json_object and rely on the prompt to fix the shape.
 */

import type { PromptInput } from "./index";
import { readSSEDeltas } from "./sse";

interface ChatBody {
  model: string;
  messages: { role: "system" | "user" | "assistant"; content: string }[];
  stream?: boolean;
  response_format?: { type: "json_object" } | { type: "text" };
  temperature?: number;
}

export interface OpenAIPromptOpts {
  schema?: Record<string, unknown>;
  temperature?: number;
}

export async function promptOpenAI(
  baseUrl: string,
  apiKey: string,
  model: string,
  input: PromptInput,
  streaming: false,
  opts?: OpenAIPromptOpts,
): Promise<string>;
export async function promptOpenAI(
  baseUrl: string,
  apiKey: string,
  model: string,
  input: PromptInput,
  streaming: true,
  opts?: OpenAIPromptOpts,
): Promise<AsyncIterable<string>>;
export async function promptOpenAI(
  baseUrl: string,
  apiKey: string,
  model: string,
  input: PromptInput,
  streaming: boolean,
  opts: OpenAIPromptOpts = {},
): Promise<string | AsyncIterable<string>> {
  const body: ChatBody = {
    model,
    messages: [
      { role: "system", content: input.system },
      { role: "user", content: input.user },
    ],
    stream: streaming,
    temperature: opts.temperature ?? 0.3,
    ...(opts.schema ? { response_format: { type: "json_object" } } : {}),
  };

  const url = `${baseUrl.replace(/\/+$/, "")}/chat/completions`;
  const headers: Record<string, string> = {
    "content-type": "application/json",
  };
  if (apiKey) headers["authorization"] = `Bearer ${apiKey}`;

  const res = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`OpenAI ${res.status}: ${detail.slice(0, 200)}`);
  }

  if (!streaming) {
    const json = (await res.json()) as {
      choices?: { message?: { content?: string } }[];
    };
    return json.choices?.[0]?.message?.content ?? "";
  }
  if (!res.body) throw new Error("OpenAI streaming response has no body");
  return readSSEDeltas<OpenAIEvent>(
    res.body,
    (e) => e.choices?.[0]?.delta?.content,
  );
}

interface OpenAIEvent {
  choices?: { delta?: { content?: string } }[];
}

/**
 * Probe an OpenAI-compatible endpoint by asking for a tiny completion.
 * Used by the options page's "Test connection" button. Returns either
 * the list of available models (if `/models` is supported) or just an
 * "ok" with no model list.
 */
export async function probeOpenAI(
  baseUrl: string,
  apiKey: string,
): Promise<
  | { ok: true; models: string[] }
  | { ok: false; reason: string; detail: string }
> {
  const url = `${baseUrl.replace(/\/+$/, "")}/models`;
  const headers: Record<string, string> = { accept: "application/json" };
  if (apiKey) headers["authorization"] = `Bearer ${apiKey}`;
  try {
    const res = await fetch(url, { method: "GET", headers });
    if (!res.ok) {
      return {
        ok: false,
        reason: "http",
        detail: `${res.status} ${res.statusText}`,
      };
    }
    const json = (await res.json()) as {
      data?: { id?: string }[];
    };
    return {
      ok: true,
      models: (json.data ?? [])
        .map((m) => m.id)
        .filter((m): m is string => typeof m === "string"),
    };
  } catch (err) {
    const msg = (err as Error).message;
    if (/network|fetch|cors/i.test(msg)) {
      return { ok: false, reason: "cors", detail: msg };
    }
    return { ok: false, reason: "unreachable", detail: msg };
  }
}
