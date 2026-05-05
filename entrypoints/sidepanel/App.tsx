import { useEffect, useReducer, useRef, useState } from "react";
import { connectPanel, onServerEvent, sendCommand } from "@/lib/messaging";
import { getSettings, watchSettings } from "@/lib/storage";
import type { Settings } from "@/types";
import { initialState, reducer } from "./state";
import { Header } from "./components/Header";
import { ClaimCard } from "./components/ClaimCard";
import { PageMeta } from "./components/PageMeta";
import { ErrorBanner } from "./components/ErrorBanner";
import { SetupHint } from "./components/SetupHint";
import { EmptyState } from "./components/EmptyState";
import { StatusBar } from "./components/StatusBar";
import { DebugLog } from "./components/DebugLog";

export function App() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [activeTabId, setActiveTabId] = useState<number | null>(null);
  /**
   * Tab the *current* analysis is bound to. Verify/highlight commands
   * always target this — the user may have switched to a source tab,
   * but the article they care about lives in the analyzed tab.
   */
  const [analyzedTabId, setAnalyzedTabId] = useState<number | null>(null);
  const [debugOpen, setDebugOpen] = useState(false);
  const portRef = useRef<chrome.runtime.Port | null>(null);

  useEffect(() => {
    getSettings().then(setSettings);
    return watchSettings(setSettings);
  }, []);

  useEffect(() => {
    chrome.tabs.query({ active: true, lastFocusedWindow: true }, (tabs) => {
      const t = tabs[0];
      if (t?.id != null) setActiveTabId(t.id);
    });
    const onActivated = (info: chrome.tabs.TabActiveInfo) => {
      // Track the new active tab for the *next* Analyze click. Don't
      // reset analysis state — the user may be opening a source link in
      // a new tab and expects the panel to keep showing the original
      // article's analysis. (Reset is explicit: clicking Analyze again.)
      setActiveTabId(info.tabId);
    };
    chrome.tabs.onActivated.addListener(onActivated);
    return () => chrome.tabs.onActivated.removeListener(onActivated);
  }, []);

  useEffect(() => {
    const port = connectPanel();
    portRef.current = port;
    onServerEvent(port, (event) => dispatch({ type: "server", event }));
    const onDisconnect = () => {
      // The service worker can be torn down by the browser at any moment.
      // Drop the port reference so subsequent sends don't blow up.
      if (portRef.current === port) portRef.current = null;
    };
    port.onDisconnect.addListener(onDisconnect);
    return () => {
      port.onDisconnect.removeListener(onDisconnect);
      try {
        port.disconnect();
      } catch {
        /* already closed */
      }
      if (portRef.current === port) portRef.current = null;
    };
  }, []);

  const ensurePort = (): chrome.runtime.Port | null => {
    if (portRef.current) return portRef.current;
    const port = connectPanel();
    portRef.current = port;
    onServerEvent(port, (event) => dispatch({ type: "server", event }));
    port.onDisconnect.addListener(() => {
      if (portRef.current === port) portRef.current = null;
    });
    return port;
  };

  const analyze = () => {
    if (activeTabId == null) return;
    const port = ensurePort();
    if (!port) return;
    setAnalyzedTabId(activeTabId);
    dispatch({ type: "analyze-start" });
    sendCommand(port, { kind: "analyze", tabId: activeTabId });
  };

  /** Tab to target for verify/highlight: the analyzed one if we know it,
   *  falling back to the active one (e.g. immediately after a panel reload). */
  const targetTabId = analyzedTabId ?? activeTabId;

  const verify = (claimId: string) => {
    const c = state.claims[claimId];
    if (!c || targetTabId == null || !state.page) return;
    const port = ensurePort();
    if (!port) return;
    dispatch({ type: "verify-start", claimId });
    sendCommand(port, {
      kind: "verify",
      tabId: targetTabId,
      claim: c.claim,
      pageUrl: state.page.url,
    });
  };

  const highlight = (claimText: string) => {
    if (targetTabId == null) return;
    const port = ensurePort();
    if (!port) return;
    sendCommand(port, { kind: "highlight-claim", tabId: targetTabId, claimText });
  };

  const clearHighlights = () => {
    if (targetTabId == null) return;
    const port = ensurePort();
    if (!port) return;
    sendCommand(port, { kind: "clear-highlights", tabId: targetTabId });
  };

  const openOptions = () => chrome.runtime.openOptionsPage();

  const setupOk = isSetupOK(settings);
  const busy =
    state.pagePhase === "extracting" ||
    state.pagePhase === "claims" ||
    Object.values(state.claims).some((c) => c.phase === "verifying");
  const debugVisible = !!settings?.showDebugLogs;

  return (
    <div className="flex h-full flex-col bg-paper text-ink dark:bg-ink dark:text-paper">
      <Header
        onAnalyze={analyze}
        onOpenOptions={openOptions}
        onClearHighlights={clearHighlights}
        canAnalyze={activeTabId != null && setupOk}
        busy={busy}
      />

      <StatusBar
        phase={state.currentPhase}
        message={state.currentStatus}
        progress={state.currentProgress}
        busy={busy}
      />

      <main className="flex-1 overflow-y-auto px-4 py-3">
        {!setupOk && settings && <SetupHint settings={settings} onOpen={openOptions} />}

        {state.pageError && <ErrorBanner message={state.pageError} />}

        {state.page && <PageMeta page={state.page} />}

        {state.claimOrder.length === 0 && state.pagePhase === "idle" && setupOk && (
          <EmptyState />
        )}

        <ul className="mt-4 space-y-3">
          {state.claimOrder.map((id, i) => {
            const c = state.claims[id];
            if (!c) return null;
            return (
              <ClaimCard
                key={id}
                index={i + 1}
                claim={c}
                onVerify={() => verify(id)}
                onHighlight={() => highlight(c.claim.text)}
              />
            );
          })}
        </ul>
      </main>

      {debugVisible && (
        <DebugLog
          logs={state.logs}
          page={state.page}
          open={debugOpen}
          onToggle={() => setDebugOpen((o) => !o)}
          onClear={() => dispatch({ type: "clear-logs" })}
        />
      )}
    </div>
  );
}

function isSetupOK(s: Settings | null): boolean {
  if (!s) return true; // not loaded yet; don't show the hint until we know
  if (!s.braveApiKey) return false;
  if (s.tier !== "network") return true;
  switch (s.networkProvider) {
    case "anthropic":
      return !!s.anthropic.apiKey;
    case "openai":
      return !!s.openai.apiKey;
    case "google":
      return !!s.google.apiKey;
    case "ollama":
      return !!s.ollama.baseUrl;
    case "openai-compatible":
      return !!s.openaiCompatible.baseUrl && !!s.openaiCompatible.model;
  }
}
