/**
 * Google Gemini API client.
 *
 *   POST {endpoint}/v1beta/models/{model}:streamGenerateContent?alt=sse&key={key}
 *
 * Response is SSE with `data: {json}\n\n` chunks. Each chunk has a
 * `candidates[0].content.parts[].text` delta. We yield those.
 *
 * For structured output we set `responseMimeType: "application/json"`,
 * supported on Gemini 1.5 and later. The prompt fixes the JSON shape;
 * we don't pass a schema (top-level arrays + Gemini's strict schema
 * mode have the same incompatibility OpenAI does).
 */

import type { PromptInput } from "./index";
import { readSSEDeltas } from "./sse";

const ENDPOINT = "https://generativelanguage.googleapis.com";

interface GenerateBody {
  contents: { role: "user"; parts: { text: string }[] }[];
  systemInstruction?: { parts: { text: string }[] };
  generationConfig?: {
    temperature?: number;
    responseMimeType?: string;
    responseSchema?: Record<string, unknown>;
  };
}

export interface GooglePromptOpts {
  schema?: Record<string, unknown>;
  temperature?: number;
}

export async function promptGoogle(
  apiKey: string,
  model: string,
  input: PromptInput,
  streaming: false,
  opts?: GooglePromptOpts,
): Promise<string>;
export async function promptGoogle(
  apiKey: string,
  model: string,
  input: PromptInput,
  streaming: true,
  opts?: GooglePromptOpts,
): Promise<AsyncIterable<string>>;
export async function promptGoogle(
  apiKey: string,
  model: string,
  input: PromptInput,
  streaming: boolean,
  opts: GooglePromptOpts = {},
): Promise<string | AsyncIterable<string>> {
  const body: GenerateBody = {
    contents: [{ role: "user", parts: [{ text: input.user }] }],
    systemInstruction: { parts: [{ text: input.system }] },
    generationConfig: {
      temperature: opts.temperature ?? 0.3,
      ...(opts.schema ? { responseMimeType: "application/json" } : {}),
    },
  };

  const path = streaming
    ? `${ENDPOINT}/v1beta/models/${encodeURIComponent(model)}:streamGenerateContent?alt=sse&key=${encodeURIComponent(apiKey)}`
    : `${ENDPOINT}/v1beta/models/${encodeURIComponent(model)}:generateContent?key=${encodeURIComponent(apiKey)}`;

  const res = await fetch(path, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Google ${res.status}: ${detail.slice(0, 200)}`);
  }

  if (!streaming) {
    const json = (await res.json()) as GeminiResponse;
    return collectText(json);
  }
  if (!res.body) throw new Error("Google streaming response has no body");
  return readSSEDeltas<GeminiResponse>(res.body, (e) => collectText(e) || undefined);
}

interface GeminiResponse {
  candidates?: { content?: { parts?: { text?: string }[] } }[];
}

function collectText(json: GeminiResponse): string {
  return (json.candidates?.[0]?.content?.parts ?? [])
    .map((p) => p.text ?? "")
    .join("");
}
