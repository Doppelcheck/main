import type {
  Claim,
  ExtractedPage,
  FactCheckHit,
  LogEntry,
  Phase,
  SearchHit,
  ServerEvent,
  Verdict,
} from "@/types";

export type ClaimPhase = "idle" | "verifying" | "done";

export interface ClaimState {
  claim: Claim;
  phase: ClaimPhase;
  factChecks?: FactCheckHit[];
  searchHits?: SearchHit[];
  verdicts: Verdict[];
  error?: string;
}

export interface AppState {
  page?: ExtractedPage;
  pagePhase: "idle" | "extracting" | "extracted" | "claims" | "ready" | "error";
  pageError?: string;
  /** Most recent server-reported phase, drives the status strip. */
  currentPhase: Phase;
  /** Last log line (used as the status text). */
  currentStatus?: string;
  /** Optional 0..1 progress (e.g. for model download). */
  currentProgress?: number;
  claims: Record<string, ClaimState>;
  claimOrder: string[];
  /** Recent log entries, capped — only kept if the user enables debug logs. */
  logs: LogEntry[];
}

const LOG_CAP = 200;

export const initialState: AppState = {
  pagePhase: "idle",
  currentPhase: "idle",
  claims: {},
  claimOrder: [],
  logs: [],
};

export type Action =
  | { type: "reset" }
  | { type: "analyze-start" }
  | { type: "verify-start"; claimId: string }
  | { type: "clear-logs" }
  | { type: "page-error"; message: string }
  | { type: "server"; event: ServerEvent };

export function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case "reset":
      return initialState;
    case "analyze-start":
      return {
        ...initialState,
        pagePhase: "extracting",
        currentPhase: "extracting",
        currentStatus: "Reading the page…",
      };
    case "verify-start":
      return startVerifying(state, action.claimId);
    case "clear-logs":
      return { ...state, logs: [] };
    case "page-error":
      return {
        ...state,
        pagePhase: "error",
        currentPhase: "error",
        pageError: action.message,
      };
    case "server":
      return applyServerEvent(state, action.event);
  }
}

function applyServerEvent(state: AppState, e: ServerEvent): AppState {
  switch (e.kind) {
    case "log": {
      const logs = [...state.logs, e.entry].slice(-LOG_CAP);
      const next: AppState = {
        ...state,
        logs,
        currentPhase: e.entry.phase,
        currentStatus: e.entry.message,
        currentProgress: e.entry.progress,
      };
      if (e.entry.level === "error") next.pageError = e.entry.message;
      return next;
    }
    case "page-extracted":
      return { ...state, page: e.page, pagePhase: "extracted" };
    case "claims-start":
      return {
        ...state,
        pagePhase: "claims",
        currentPhase: "claim-extraction",
        claims: {},
        claimOrder: [],
      };
    case "claim": {
      if (state.claims[e.claim.id]) return state;
      return {
        ...state,
        claims: {
          ...state.claims,
          [e.claim.id]: { claim: e.claim, phase: "idle", verdicts: [] },
        },
        claimOrder: [...state.claimOrder, e.claim.id],
      };
    }
    case "claims-done":
      return {
        ...state,
        pagePhase: "ready",
        currentPhase: "done",
        currentStatus: undefined,
        currentProgress: undefined,
      };
    case "fact-check":
      return mutateClaim(state, e.claimId, (c) => ({
        ...c,
        phase: "verifying",
        factChecks: e.hits,
      }));
    case "search-results":
      return mutateClaim(state, e.claimId, (c) => ({
        ...c,
        phase: "verifying",
        searchHits: e.hits,
      }));
    case "verdict":
      return mutateClaim(state, e.verdict.claimId, (c) => ({
        ...c,
        verdicts: [...c.verdicts, e.verdict],
      }));
    case "verify-done":
      return {
        ...mutateClaim(state, e.claimId, (c) => ({ ...c, phase: "done" })),
        currentPhase: "done",
        currentStatus: undefined,
        currentProgress: undefined,
      };
    case "error":
      if (e.claimId) {
        return mutateClaim(state, e.claimId, (c) => ({
          ...c,
          phase: "done",
          error: e.message,
        }));
      }
      return {
        ...state,
        pagePhase: "error",
        currentPhase: "error",
        pageError: e.message,
        currentStatus: e.message,
      };
  }
}

function mutateClaim(
  state: AppState,
  id: string,
  fn: (c: ClaimState) => ClaimState,
): AppState {
  const existing = state.claims[id];
  if (!existing) return state;
  return { ...state, claims: { ...state.claims, [id]: fn(existing) } };
}

export function startVerifying(state: AppState, id: string): AppState {
  return mutateClaim(state, id, (c) => ({
    ...c,
    phase: "verifying",
    verdicts: [],
    factChecks: undefined,
    searchHits: undefined,
    error: undefined,
  }));
}
