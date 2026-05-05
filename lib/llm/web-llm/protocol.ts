/**
 * Wire protocol between the background service worker / Firefox
 * background page and the offscreen document that hosts the MLC
 * web-llm engine.
 *
 * Each `Generate` request is identified by a UUID-ish string. The
 * runner streams back zero or more `Progress` events (model download
 * + warmup), zero or more `Delta` events (each new token text), and
 * exactly one terminating event: `Done` or `Error`.
 */

export interface GenerateRequest {
  kind: "generate";
  id: string;
  modelId: string;
  system: string;
  user: string;
  /** Hard token cap. Defaults applied by the runner. */
  maxNewTokens?: number;
  /**
   * Optional JSON schema that constrains the model's response. When
   * present, MLC's XGrammar mask sampler enforces it at the token
   * level — the output is guaranteed to be a JSON document matching
   * the schema. Pass the schema as an object; the runner serialises
   * it for `response_format.schema`.
   */
  schema?: Record<string, unknown>;
}

export interface AbortRequest {
  kind: "abort";
  id: string;
}

export type RunnerRequest = GenerateRequest | AbortRequest;

export interface ProgressEvent {
  kind: "progress";
  id: string;
  /** 0..1 download/init progress when known. */
  progress?: number;
  /** Free-form status text (file name, warmup phase, …). */
  message?: string;
}

export interface DeltaEvent {
  kind: "delta";
  id: string;
  /** New token text since the previous delta. */
  text: string;
}

export interface DoneEvent {
  kind: "done";
  id: string;
}

export interface ErrorEvent {
  kind: "error";
  id: string;
  message: string;
}

export type RunnerEvent = ProgressEvent | DeltaEvent | DoneEvent | ErrorEvent;

/** Port name for the long-lived background ↔ offscreen channel. */
export const RUNNER_PORT = "doppelcheck-runner";
