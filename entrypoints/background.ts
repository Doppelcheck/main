import { defineBackground } from "wxt/sandbox";
import type {
  Claim,
  ClientCommand,
  ContentRequest,
  ExtractedPage,
  HighlightType,
  LogEntry,
  LogLevel,
  Phase,
  ServerEvent,
  Settings,
  Verdict,
} from "@/types";
import { PANEL_PORT, ensureContentScript, safePost, sendToContent } from "@/lib/messaging";
import {
  addPanelPort,
  installRelayListener,
} from "@/lib/messaging/panel-bus";
import { browserApi } from "@/lib/browser-api";
import { getSettings } from "@/lib/storage";
import { getPipeline, type Pipeline, type PipelineCallOpts } from "@/lib/pipeline";
import { searchAll, factCheckLookup } from "@/lib/search";
import { fetchSourceText } from "@/lib/fetch-source";

export default defineBackground({
  type: "module",
  main() {
    // Toolbar-icon → side-panel/sidebar toggle.
    //
    // Chrome (MV3): the Side Panel API has a built-in "open when the
    // action is clicked" mode. Set it once and the browser handles the
    // rest.
    //
    // Firefox (MV2): there's no such mode. We listen on the action's
    // onClicked event ourselves and call `sidebarAction.toggle()`. The
    // action API is named `browserAction` in MV2; we try both names so
    // this code is the same on Chromium and Gecko.
    if (chrome.sidePanel?.setPanelBehavior) {
      chrome.sidePanel
        .setPanelBehavior({ openPanelOnActionClick: true })
        .catch(() => undefined);
    } else {
      const ff = browserApi as typeof chrome & {
        browserAction?: { onClicked?: chrome.events.Event<() => void> };
        sidebarAction?: { toggle?: () => void };
      };
      const onClicked =
        ff.browserAction?.onClicked ?? ff.action?.onClicked;
      onClicked?.addListener(() => {
        ff.sidebarAction?.toggle?.();
      });
    }

    chrome.runtime.onConnect.addListener((port) => {
      if (port.name !== PANEL_PORT) return;
      addPanelPort(port);
      const send = (e: ServerEvent) => safePost(port, e);
      port.onMessage.addListener((cmd: ClientCommand) => {
        handleCommand(cmd, send).catch((err: Error) => {
          send({ kind: "error", message: err.message });
          send({
            kind: "log",
            entry: makeLog("error", "error", err.message),
          });
        });
      });
    });

    // Relay log entries that arrive via `runtime.sendMessage` from
    // *other* extension contexts (options page, side panel, content
    // scripts). Same-context callers call `routeLogEntry` directly;
    // runtime.sendMessage doesn't deliver to the sender.
    installRelayListener();
  },
});

function makeLog(
  level: LogLevel,
  phase: Phase,
  message: string,
  extra: Partial<LogEntry> = {},
): LogEntry {
  return { at: Date.now(), level, phase, message, ...extra };
}

type Logger = (
  phase: Phase,
  message: string,
  extra?: { level?: LogLevel; progress?: number; claimId?: string },
) => void;

function makeLogger(send: (e: ServerEvent) => void): Logger {
  return (phase, message, extra = {}) => {
    const entry = makeLog(extra.level ?? "info", phase, message, {
      progress: extra.progress,
      claimId: extra.claimId,
    });
    send({ kind: "log", entry });
    const tag = `[doppelcheck:${phase}]`;
    if (entry.level === "error") console.error(tag, message);
    else if (entry.level === "warn") console.warn(tag, message);
    else console.log(tag, message);
  };
}

/** Convert a per-call Logger into the Pipeline-internal shape. */
function pipelineLog(log: Logger, claimId?: string): PipelineCallOpts["log"] {
  return (level, phase, message) => log(phase, message, { level, claimId });
}

async function handleCommand(
  cmd: ClientCommand,
  send: (e: ServerEvent) => void,
) {
  switch (cmd.kind) {
    case "analyze":
      return analyze(cmd.tabId, send);
    case "verify":
      return verify(cmd.tabId, cmd.claim, cmd.pageUrl, send);
    case "highlight-claim":
      await sendToTab(cmd.tabId, {
        kind: "highlight",
        ranges: [{ text: cmd.claimText, type: "claim" }],
      });
      return;
    case "clear-highlights":
      await sendToTab(cmd.tabId, { kind: "clear-highlights" });
      return;
  }
}

async function analyze(tabId: number, send: (e: ServerEvent) => void) {
  const log = makeLogger(send);
  const settings = await getSettings();

  log("extracting", "Reading the page");
  // Make sure the content script is reachable before talking to it.
  // The most common failure here is an "orphaned" tab — one that was
  // already open before the extension was installed/reloaded — whose
  // manifest content script never got the chance to register. Other
  // cases (chrome://, Web Store, …) yield a clean user-facing error.
  try {
    await ensureContentScript(tabId);
  } catch (err) {
    const msg = (err as Error).message;
    log("error", msg, { level: "error" });
    send({ kind: "error", message: msg });
    return;
  }
  const extractRes = await sendToTab<
    | {
        ok: true;
        page: ExtractedPage;
        debug?: { strategy: string; noiseRemoved: number };
      }
    | { ok: false; error: string }
  >(tabId, { kind: "extract" });
  if (!extractRes.ok) {
    log("error", `Extraction failed: ${extractRes.error}`, { level: "error" });
    send({ kind: "error", message: `Extraction failed: ${extractRes.error}` });
    return;
  }
  const page = extractRes.page;
  if (extractRes.debug) {
    log(
      "extracting",
      `Scoped to ${extractRes.debug.strategy}, stripped ${extractRes.debug.noiseRemoved} noise element${extractRes.debug.noiseRemoved === 1 ? "" : "s"}`,
    );
  }
  log("extracting", `Extracted ${page.wordCount.toLocaleString()} words`);
  if (!page.text || page.wordCount < 80) {
    const msg = "This page doesn't seem to have enough article-like content to analyze.";
    log("error", msg, { level: "error" });
    send({ kind: "error", message: msg });
    return;
  }
  send({ kind: "page-extracted", page });

  const pipe = await getPipeline(settings);
  log("extracting", `Using ${tierLabel(settings)} (${pipe.tag})`);

  if (!page.language && pipe.detectLanguage) {
    log("detect-language", "Detecting article language");
    try {
      const lang = await pipe.detectLanguage(page.text);
      if (lang) {
        page.language = lang;
        log("detect-language", `Article language: ${lang}`);
      }
    } catch (err) {
      log("detect-language", `Language detection skipped: ${(err as Error).message}`, {
        level: "warn",
      });
    }
  }

  const callOpts: PipelineCallOpts = {
    onDownload: (p, message) => {
      // Per-chunk numeric progress drives the UI bar but doesn't go
      // to the debug log — it would otherwise emit one INFO line per
      // network chunk (hundreds per file). Only the runner's status
      // transitions ("Downloading X", "Downloaded X", "Model ready")
      // come through with a `message`, and those *do* belong in the
      // log. Same policy as `probe.ts` for the Test button.
      if (message) log("model-download", message, { progress: p });
    },
    log: pipelineLog(log),
  };

  send({ kind: "claims-start" });
  log("claim-extraction", `Asking the pipeline for up to ${settings.maxClaims} claims`);

  const claims: Claim[] = [];
  try {
    for await (const claim of pipe.extractClaims(page, settings.maxClaims, callOpts)) {
      claims.push(claim);
      log("claim-extraction", `Claim ${claims.length}: ${truncate(claim.text, 80)}`);
      send({ kind: "claim", claim });
    }
  } catch (err) {
    const msg = (err as Error).message;
    log("claim-extraction", `Claim extraction failed: ${msg}`, { level: "error" });
    send({ kind: "error", message: `Claim extraction failed: ${msg}` });
  }

  log(
    "claim-extraction",
    claims.length > 0
      ? `Claim extraction complete (${claims.length} claim${claims.length === 1 ? "" : "s"})`
      : "Claim extraction returned 0 claims",
    { level: claims.length > 0 ? "info" : "warn" },
  );
  send({ kind: "claims-done" });

  if (settings.autoVerify && claims.length > 0) {
    log("done", `Auto-verifying ${claims.length} claim${claims.length === 1 ? "" : "s"}`);
    for (const claim of claims) {
      await verify(tabId, claim, page.url, send).catch((err: Error) => {
        log("error", `Verify ${claim.id}: ${err.message}`, {
          level: "warn",
          claimId: claim.id,
        });
        send({ kind: "error", message: err.message, claimId: claim.id });
        send({ kind: "verify-done", claimId: claim.id });
      });
    }
    log("done", "All claims verified");
  }
}

async function verify(
  tabId: number,
  claim: Claim,
  pageUrl: string,
  send: (e: ServerEvent) => void,
) {
  const log = makeLogger(send);
  const settings = await getSettings();
  const pipe = await getPipeline(settings);
  const callOpts: PipelineCallOpts = {
    onDownload: (p, message) => {
      // See note in `analyze` — only emit log entries on status
      // transitions, not on every per-chunk numeric tick.
      if (message) log("model-download", message, { progress: p, claimId: claim.id });
    },
    log: pipelineLog(log, claim.id),
  };

  log("detect-language", "Detecting claim language", { claimId: claim.id });
  const lang = await safeDetectLang(pipe, claim.text);
  if (lang) {
    log("detect-language", `Claim language: ${lang}`, { claimId: claim.id });
  }

  // 1. Existing fact-checks (cheap, authoritative for known claims).
  if (settings.factCheckApiKey) {
    log("fact-check", "Querying Google Fact Check Tools", { claimId: claim.id });
    try {
      const hits = await factCheckLookup(
        settings.factCheckApiKey,
        claim.text,
        lang,
      );
      log("fact-check", `Fact-check API returned ${hits.length} hit(s)`, {
        claimId: claim.id,
      });
      send({ kind: "fact-check", claimId: claim.id, hits });
    } catch (err) {
      log("fact-check", `Fact Check API failed: ${(err as Error).message}`, {
        level: "warn",
        claimId: claim.id,
      });
      send({
        kind: "error",
        message: `Fact Check API: ${(err as Error).message}`,
        claimId: claim.id,
      });
    }
  } else {
    log("fact-check", "Fact Check API key not configured, skipping", {
      level: "warn",
      claimId: claim.id,
    });
  }

  // 2. Generate a search query, then run general + per-custom-domain searches.
  log("query-generation", "Generating search query", { claimId: claim.id });
  const query = await pipe.generateQuery(claim.text, lang, callOpts);
  log("query-generation", `Search query: "${query}"`, { claimId: claim.id });

  log("search", "Searching Brave (general + trusted domains)", { claimId: claim.id });
  const hits = await searchAll(query, pageUrl, settings, lang);
  log("search", `Search returned ${hits.length} unique source(s)`, {
    claimId: claim.id,
  });
  send({ kind: "search-results", claimId: claim.id, hits });

  // 3. Verdict per source — sequentially to keep cost bounded and the UI ordered.
  const evidenceForHighlight: { text: string; type: HighlightType }[] = [];
  for (const [i, hit] of hits.slice(0, 5).entries()) {
    log("fetch", `Fetching ${hit.domain} (${i + 1}/${Math.min(5, hits.length)})`, {
      claimId: claim.id,
    });
    try {
      const fetched = await fetchSourceText(hit.url);
      if (!fetched) {
        log("fetch", `Could not fetch ${hit.domain}`, {
          level: "warn",
          claimId: claim.id,
        });
        continue;
      }
      log(
        "compare",
        `Comparing claim against ${hit.domain} (${fetched.text.length.toLocaleString()} chars)`,
        { claimId: claim.id },
      );
      const result = await pipe.compareToSource(
        claim.text,
        { url: hit.url, title: fetched.title, text: fetched.text },
        lang,
        callOpts,
      );
      const verdict: Verdict = {
        claimId: claim.id,
        url: hit.url,
        alignment: result.alignment,
        evidence: result.evidence,
        explanation: result.explanation,
      };
      log("compare", `${hit.domain}: ${verdict.alignment}`, { claimId: claim.id });
      send({ kind: "verdict", verdict });
      if (verdict.alignment !== "unrelated" && verdict.evidence) {
        evidenceForHighlight.push({
          text: verdict.evidence,
          type:
            verdict.alignment === "agrees"
              ? "evidence-agree"
              : "evidence-disagree",
        });
      }
    } catch (err) {
      log(
        "compare",
        `${hit.domain}: ${(err as Error).message}`,
        { level: "warn", claimId: claim.id },
      );
      send({
        kind: "error",
        message: `${hit.domain}: ${(err as Error).message}`,
        claimId: claim.id,
      });
    }
  }

  // 4. Highlight the claim's verbatim quote on the original page.
  const claimRange = claim.quote || claim.text;
  if (claimRange) {
    log("highlight", "Applying in-page highlight", { claimId: claim.id });
    await sendToTab<{ ok: boolean; applied?: number; missed?: number }>(tabId, {
      kind: "highlight",
      ranges: [{ text: claimRange, type: "claim" }],
    })
      .then((res) => {
        if (res && res.applied === 0) {
          log(
            "highlight",
            `Could not locate claim quote on the page: "${truncate(claimRange, 80)}"`,
            { level: "warn", claimId: claim.id },
          );
        }
      })
      .catch(() => undefined);
  }

  log("done", "Verification complete", { claimId: claim.id });
  send({ kind: "verify-done", claimId: claim.id });
}

async function safeDetectLang(
  pipe: Pipeline,
  text: string,
): Promise<string | undefined> {
  if (!pipe.detectLanguage) return undefined;
  try {
    return await pipe.detectLanguage(text);
  } catch {
    return undefined;
  }
}

function tierLabel(s: Settings): string {
  switch (s.tier) {
    case "browser-native":
      return "browser built-in AI (Chrome Gemini Nano)";
    case "network":
      switch (s.networkProvider) {
        case "anthropic":
          return `network → Anthropic ${s.anthropic.model}`;
        case "openai":
          return `network → OpenAI ${s.openai.model}`;
        case "google":
          return `network → Google Gemini ${s.google.model}`;
        case "ollama":
          return `network → Ollama (${s.ollama.model} @ ${s.ollama.baseUrl})`;
        case "openai-compatible":
          return `network → ${s.openaiCompatible.presetName || "OpenAI-compatible"} (${s.openaiCompatible.model} @ ${s.openaiCompatible.baseUrl})`;
      }
  }
}

function truncate(s: string, n: number): string {
  if (s.length <= n) return s;
  return s.slice(0, n - 1).trimEnd() + "…";
}

/**
 * Background → content-script one-shot. Routes through the shared
 * `browser.*`-preferring helper in lib/messaging so it returns a real
 * Promise on Firefox MV2 (where `chrome.tabs.sendMessage` is callback-
 * only and `await`-ing it would silently resolve to `undefined`).
 */
function sendToTab<T = unknown>(
  tabId: number,
  req: ContentRequest,
): Promise<T> {
  return sendToContent<T>(tabId, req);
}

export type { Settings };
