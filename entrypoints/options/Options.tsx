import { useEffect, useMemo, useRef, useState } from "react";
import { getSettings, setSettings } from "@/lib/storage";
import {
  DEFAULT_SETTINGS,
  type AnthropicConfig,
  type GoogleConfig,
  type NetworkProvider,
  type OllamaConfig,
  type OpenAIConfig,
  type OpenAICompatibleConfig,
  type Settings,
  type Tier,
} from "@/types";
import { probeOllama } from "@/lib/llm/ollama";
import { probeOpenAI } from "@/lib/llm/openai";
import { probeLocalModel } from "@/lib/llm/web-llm/probe";
import { relayLogEntry } from "@/lib/messaging";
import { getCurrentWindowId, openSidePanel } from "@/lib/browser-api";

export function Options() {
  const [s, setS] = useState<Settings | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  /** Skip the auto-save effect on the very first run (right after we
   *  load existing settings). Without this gate we'd immediately re-
   *  write whatever we just read. */
  const initialised = useRef(false);
  /** Hide the "Saved" indicator until the user has actually changed
   *  something. */
  const userTouched = useRef(false);

  useEffect(() => {
    getSettings()
      .then(setS)
      .catch((err: Error) =>
        setLoadError(`Couldn't load settings: ${err.message}`),
      );
  }, []);

  // Debounced auto-save. Fires 400 ms after the last change.
  useEffect(() => {
    if (!s) return;
    if (!initialised.current) {
      initialised.current = true;
      return;
    }
    const timer = window.setTimeout(() => {
      setSettings(s)
        .then(() => {
          if (!userTouched.current) return;
          setSaved(true);
          window.setTimeout(() => setSaved(false), 1500);
        })
        .catch(() => undefined);
    }, 400);
    return () => clearTimeout(timer);
  }, [s]);

  const update = <K extends keyof Settings>(key: K, value: Settings[K]) => {
    if (!s) return;
    userTouched.current = true;
    setS({ ...s, [key]: value });
  };

  const onReset = async () => {
    userTouched.current = true;
    const next = await setSettings(DEFAULT_SETTINGS);
    setS(next);
    setSaved(true);
    window.setTimeout(() => setSaved(false), 1500);
  };

  if (loadError) {
    return (
      <div className="min-h-screen bg-paper p-8 text-ink dark:bg-ink dark:text-paper">
        <div className="mx-auto max-w-2xl rounded-md border border-disagree/30 bg-disagree/10 p-4 text-sm">
          <p className="font-semibold">Settings failed to load.</p>
          <p className="mt-1">{loadError}</p>
        </div>
      </div>
    );
  }
  if (!s) return <div className="p-8 text-ink dark:text-paper">Loading…</div>;

  return (
    <div className="min-h-screen bg-paper px-6 py-10 text-ink dark:bg-ink dark:text-paper">
      <div className="mx-auto max-w-2xl">
        <header className="mb-8">
          <h1 className="text-2xl font-semibold tracking-tight">DoppelCheck — Settings</h1>
          <p className="mt-1 text-sm text-ink/60 dark:text-paper/60">
            Everything is stored locally with <code>chrome.storage.sync</code>.
            API keys are never sent anywhere except the API they belong to.
          </p>
        </header>

        <Section
          title="Language model"
          help="Three options. Pick where you want analysis to run."
        >
          <TierPicker
            value={s.tier}
            onChange={(tier) => update("tier", tier)}
          />

          {s.tier === "browser-native" && <BrowserNativePanel />}

          {s.tier === "local-bundle" && (
            <LocalBundlePanel
              modelId={s.localBundleModel}
              onModelChange={(v) => update("localBundleModel", v)}
            />
          )}

          {s.tier === "network" && (
            <NetworkPanel
              provider={s.networkProvider}
              onProviderChange={(p) => update("networkProvider", p)}
              anthropic={s.anthropic}
              onAnthropicChange={(v) => update("anthropic", v)}
              openai={s.openai}
              onOpenAIChange={(v) => update("openai", v)}
              google={s.google}
              onGoogleChange={(v) => update("google", v)}
              ollama={s.ollama}
              onOllamaChange={(v) => update("ollama", v)}
              openaiCompatible={s.openaiCompatible}
              onOpenAICompatChange={(v) => update("openaiCompatible", v)}
            />
          )}
        </Section>

        <Section
          title="Search"
          help="Brave Search powers source discovery. Independent index, low latency, $5/1k with ~1k free monthly credits."
        >
          <Field label="Brave Search API key">
            <input
              className="input"
              type="password"
              autoComplete="off"
              placeholder="BSA…"
              value={s.braveApiKey}
              onChange={(e) => update("braveApiKey", e.target.value)}
            />
          </Field>
          <p className="mt-1 text-xs">
            <a
              className="text-accent hover:underline"
              href="https://api-dashboard.search.brave.com/app/keys"
              target="_blank"
              rel="noreferrer"
            >
              Get a Brave Search API key →
            </a>
          </p>
        </Section>

        <Section
          title="Fact-check lookup (optional)"
          help="Queries the Google Fact Check Tools database before searching the open web. Surfaces existing fact-checks from publishers like Snopes, Correctiv, dpa-Faktencheck."
        >
          <Field label="Google Fact Check API key">
            <input
              className="input"
              type="password"
              autoComplete="off"
              placeholder="AIza…"
              value={s.factCheckApiKey}
              onChange={(e) => update("factCheckApiKey", e.target.value)}
            />
          </Field>
          <p className="mt-1 text-xs">
            <a
              className="text-accent hover:underline"
              href="https://developers.google.com/fact-check/tools/api"
              target="_blank"
              rel="noreferrer"
            >
              Enable the Fact Check Tools API in Google Cloud →
            </a>
          </p>
        </Section>

        <Section
          title="Trusted sources"
          help="Each domain is searched in addition to the general web — useful for prioritising publications you already trust."
        >
          <CustomUrlList
            urls={s.customUrls}
            onChange={(urls) => update("customUrls", urls)}
          />
        </Section>

        <Section title="Behaviour">
          <Field label="Maximum claims per page">
            <input
              className="input w-24"
              type="number"
              min={1}
              max={10}
              value={s.maxClaims}
              onChange={(e) =>
                update("maxClaims", Math.max(1, Math.min(10, +e.target.value)))
              }
            />
          </Field>
          <Field label="UI language">
            <select
              className="select"
              value={s.uiLanguage}
              onChange={(e) =>
                update("uiLanguage", e.target.value as Settings["uiLanguage"])
              }
            >
              <option value="auto">Auto (follow page)</option>
              <option value="en">English</option>
              <option value="de">Deutsch</option>
            </select>
          </Field>
          <label className="mt-2 flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={s.autoVerify}
              onChange={(e) => update("autoVerify", e.target.checked)}
            />
            <span>
              Auto-verify each claim after extraction
              <span className="ml-1 text-xs text-ink/55 dark:text-paper/55">
                — when on, every claim is fact-checked, searched, and
                compared without you clicking <em>Verify</em>.
              </span>
            </span>
          </label>
          <label className="mt-2 flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={s.showDebugLogs}
              onChange={(e) => update("showDebugLogs", e.target.checked)}
            />
            <span>
              Show the debug log panel in the side panel
              <span className="ml-1 text-xs text-ink/55 dark:text-paper/55">
                — useful when verification feels slow and you want to see
                exactly what's happening at each step.
              </span>
            </span>
          </label>
        </Section>

        <div className="mt-8 flex items-center gap-3 text-sm">
          <span className="text-ink/55 dark:text-paper/55">
            Changes save automatically.
          </span>
          <span
            className={
              "transition-opacity " +
              (saved ? "opacity-100 text-agree" : "opacity-0")
            }
            aria-live="polite"
          >
            ✓ Saved
          </span>
          <span className="flex-1" />
          <button
            type="button"
            onClick={onReset}
            className="rounded-md border border-ink/15 px-3 py-1.5 text-xs text-ink hover:bg-ink/5 dark:border-paper/20 dark:text-paper dark:hover:bg-paper/10"
          >
            Reset to defaults
          </button>
        </div>
      </div>
      <style>{`
        .input, .select {
          width: 100%;
          background: rgba(255,255,255,0.65);
          border: 1px solid rgba(14,17,22,0.15);
          border-radius: 6px;
          padding: 0.5rem 0.75rem;
          font: inherit;
          color: inherit;
        }
        @media (prefers-color-scheme: dark) {
          .input, .select {
            background: rgba(250,250,247,0.05);
            border-color: rgba(250,250,247,0.18);
          }
        }
        .input:focus, .select:focus {
          outline: 2px solid #1a4d8c;
          outline-offset: 1px;
        }
      `}</style>
    </div>
  );
}

/* ─── Tier picker (cards) ───────────────────────────────────────── */

const ALL_TIER_CARDS: { id: Tier; title: string; subtitle: string }[] = [
  {
    id: "browser-native",
    title: "Browser built-in",
    subtitle:
      "Use the browser's own on-device AI. Free, private, no setup beyond enabling it.",
  },
  {
    id: "local-bundle",
    title: "In-browser bundle",
    subtitle:
      "Run a small LLM in the browser via transformers.js. Configurable model, no daemon, no API key.",
  },
  {
    id: "network",
    title: "Network",
    subtitle:
      "Talk to any HTTP-reachable LLM: Anthropic, OpenAI, Google, Ollama, or any OpenAI-compatible endpoint.",
  },
];

/**
 * Hide the `browser-native` card when the browser doesn't ship a
 * compatible chat-style on-device LLM. We use feature detection
 * (`typeof LanguageModel`) rather than UA sniffing so this stays
 * correct on future Chromium variants that may add or drop the
 * Prompt API independently.
 */
function TierPicker({
  value,
  onChange,
}: {
  value: Tier;
  onChange: (t: Tier) => void;
}) {
  const browserNativeAvailable = typeof LanguageModel !== "undefined";
  const cards = ALL_TIER_CARDS.filter(
    (c) => c.id !== "browser-native" || browserNativeAvailable,
  );
  // Auto-migrate: if the saved tier is `browser-native` but the API
  // isn't here, nudge the user onto `local-bundle` so they don't
  // sit on a tier that will only ever error.
  useEffect(() => {
    if (value === "browser-native" && !browserNativeAvailable) {
      onChange("local-bundle");
    }
  }, [value, browserNativeAvailable, onChange]);

  const cols = cards.length === 3 ? "sm:grid-cols-3" : "sm:grid-cols-2";
  return (
    <div className={`grid grid-cols-1 gap-2 ${cols}`}>
      {cards.map((c) => {
        const active = value === c.id;
        return (
          <button
            type="button"
            key={c.id}
            onClick={() => onChange(c.id)}
            className={
              "rounded-md border p-3 text-left transition " +
              (active
                ? "border-accent bg-accent/10"
                : "border-ink/15 hover:border-ink/30 dark:border-paper/15 dark:hover:border-paper/30")
            }
          >
            <p className="font-medium">{c.title}</p>
            <p className="mt-1 text-xs text-ink/60 dark:text-paper/60">
              {c.subtitle}
            </p>
          </button>
        );
      })}
    </div>
  );
}

/* ─── Browser-native: Chrome built-in AI status ──────────────────── */

function BrowserNativePanel() {
  const [chromeStatus, setChromeStatus] = useState<string>("checking…");

  useEffect(() => {
    (async () => {
      if (typeof LanguageModel === "undefined") {
        setChromeStatus("not available in this browser");
        return;
      }
      try {
        setChromeStatus(humanize(await LanguageModel.availability()));
      } catch {
        setChromeStatus("not available");
      }
    })();
  }, []);

  return (
    <div className="rounded-sm border border-ink/10 bg-paper/60 p-3 text-xs leading-relaxed dark:border-paper/15 dark:bg-paper/[0.04]">
      <p className="font-semibold">Chrome Built-in AI</p>
      <p className="mt-1 text-ink/70 dark:text-paper/70">
        Status on this browser: <strong>{chromeStatus}</strong>.
      </p>
      <p className="mt-1 text-ink/55 dark:text-paper/55">
        Requires Chrome 138+ on a supported OS. Uses Gemini Nano on-device
        via the Prompt API. The model downloads on first use. Firefox has
        no built-in chat-style LLM — pick <em>In-browser bundle</em> or{" "}
        <em>Network</em> there.
      </p>
    </div>
  );
}

/* ─── In-browser bundle: transformers.js with chosen model ───────── */

/**
 * Curated MLC web-llm prebuilt models. Inclusion rule:
 *
 *   **Drop a model only when it's been proven broken on both
 *   browsers.** Untested or browser-specific candidates stay so
 *   users can verify them with the Test button.
 *
 * Status annotations in the labels reflect what we've actually
 * observed in this project's testing — update them when a Test
 * verifies or refutes a row.
 *
 * Already disproved-on-both-and-removed:
 *   - `gemma3-1b-it-q4f16_1-MLC` — only q4f16 variant exists; OOM
 *     on Firefox WebGPU (Linux), `index_kernel` shader rejection
 *     on Chrome 147. No path forward without a different build.
 *
 * The two key axes:
 *
 *   - **q4f16_1**: smaller / faster, but needs WebGPU `shader-f16`.
 *     Some Chrome 147 builds on Linux don't enable that even with
 *     `--enable-unsafe-webgpu` — driver/adapter-dependent.
 *   - **q4f32_1**: larger weights (because activations are fp32),
 *     but no `shader-f16` requirement. The fallback for Chromes
 *     where f16 isn't available.
 */
const LOCAL_MODEL_OPTIONS: { id: string; label: string; size: string; lang: string }[] = [
  {
    id: "SmolLM2-360M-Instruct-q4f16_1-MLC",
    label: "SmolLM2 360M (✓ Firefox; ✗ Chrome — needs shader-f16)",
    size: "~360 MB",
    lang: "English-leaning",
  },
  {
    id: "SmolLM2-360M-Instruct-q4f32_1-MLC",
    label: "SmolLM2 360M fp32 (untested; Chrome candidate without shader-f16)",
    size: "~480 MB",
    lang: "English-leaning",
  },
  {
    id: "SmolLM2-135M-Instruct-q0f32-MLC",
    label: "SmolLM2 135M fp32 (untested; smallest, tightest VRAM)",
    size: "~270 MB",
    lang: "English-leaning",
  },
  {
    id: "Qwen3-0.6B-q4f32_1-MLC",
    label: "Qwen 3 0.6B fp32 (untested; multilingual, Chrome candidate)",
    size: "~700 MB",
    lang: "100+ languages",
  },
  {
    id: "Phi-4-mini-instruct-q4f32_1-MLC",
    label: "Phi-4 mini fp32 (untested; best quality, ~3 GB VRAM)",
    size: "~3 GB",
    lang: "English-leaning",
  },
];

function LocalBundlePanel({
  modelId,
  onModelChange,
}: {
  modelId: string;
  onModelChange: (v: string) => void;
}) {
  const isCustom = !LOCAL_MODEL_OPTIONS.some((o) => o.id === modelId);
  const selected = LOCAL_MODEL_OPTIONS.find((o) => o.id === modelId);

  // Test-state lives per (modelId, device). Changing either clears the
  // cached result. We don't persist this — the test is meant as a
  // pre-flight check before clicking Analyze, not a long-lived
  // certification.
  type TestState =
    | { kind: "idle" }
    | {
        kind: "running";
        progress: number;
        message?: string;
        abort: AbortController;
      }
    | {
        kind: "ok";
        sample: string;
        durationMs: number;
        backend?: string;
      }
    | { kind: "failed"; error: string };
  const [test, setTest] = useState<TestState>({ kind: "idle" });
  const lastKey = useRef(modelId);
  if (lastKey.current !== modelId && test.kind !== "running") {
    // user switched model → reset the verdict.
    lastKey.current = modelId;
    if (test.kind !== "idle") setTest({ kind: "idle" });
  }

  // Pre-fetch the current window id so the click handler can call
  // `chrome.sidePanel.open({ windowId })` synchronously — the API
  // discards calls made after an `await` because the user gesture is
  // already consumed.
  const windowIdRef = useRef<number | undefined>(undefined);
  useEffect(() => {
    getCurrentWindowId().then((id) => {
      windowIdRef.current = id;
    });
  }, []);

  const onTest = async () => {
    if (test.kind === "running") return;
    if (!modelId.trim()) return;
    // SYNCHRONOUS inside the click gesture — must not be preceded by
    // `await`. The probe's log events flow through the runtime relay
    // → background → connected panel ports, so the panel needs to be
    // the receiver. The background buffers any entries that arrive
    // before the panel finishes mounting and flushes them on connect.
    openSidePanel(windowIdRef.current);
    const abort = new AbortController();
    setTest({ kind: "running", progress: 0, message: "Starting…", abort });
    const result = await probeLocalModel({
      modelId,
      signal: abort.signal,
      onProgress: (progress, message) =>
        setTest((s) =>
          s.kind === "running" ? { ...s, progress, message } : s,
        ),
      // Detailed runtime events go to the side panel's debug log
      // through the runtime relay. The options page itself shows
      // only the concise verdict below.
      onLog: (level, phase, message) =>
        relayLogEntry({ at: Date.now(), level, phase, message }),
    });
    if (result.ok) {
      setTest({
        kind: "ok",
        sample: result.sample,
        durationMs: result.durationMs,
        backend: result.backend,
      });
    } else {
      setTest({ kind: "failed", error: result.error });
    }
  };

  const onCancel = () => {
    if (test.kind === "running") {
      test.abort.abort();
      setTest({ kind: "idle" });
    }
  };

  return (
    <div className="space-y-3">
      <Field label="Model">
        <select
          className="select"
          value={isCustom ? "__custom__" : modelId}
          onChange={(e) => {
            const v = e.target.value;
            if (v === "__custom__") return;
            onModelChange(v);
          }}
        >
          {LOCAL_MODEL_OPTIONS.map((o) => (
            <option key={o.id} value={o.id}>
              {o.label} — {o.size}, {o.lang}
            </option>
          ))}
          <option value="__custom__">Custom…</option>
        </select>
        {selected && (
          <p className="mt-1 text-xs text-ink/55 dark:text-paper/55">
            <code>{selected.id}</code>
          </p>
        )}
      </Field>
      <Field label="Custom MLC model id (must be a key in `prebuiltAppConfig.model_list`)">
        <input
          className="input"
          value={modelId}
          onChange={(e) => onModelChange(e.target.value)}
          placeholder="Phi-4-mini-instruct-q4f16_1-MLC"
          spellCheck={false}
        />
      </Field>

      <ModelTestRow
        state={test}
        onTest={onTest}
        onCancel={onCancel}
        modelIdEmpty={!modelId.trim()}
      />

      <div className="rounded-sm border border-ink/10 bg-ink/[0.03] p-3 text-xs leading-relaxed dark:border-paper/15 dark:bg-paper/[0.04]">
        <p className="font-semibold text-ink dark:text-paper">How this runs</p>
        <ul className="mt-1 list-disc space-y-1 pl-5 text-ink/75 dark:text-paper/70">
          <li>
            Runs MLC web-llm with WebGPU. Output is constrained by a JSON
            schema at the sampler level (XGrammar) — claim extraction and
            verdict comparison can't return malformed JSON.
          </li>
          <li>
            <strong>Chrome</strong> hosts the engine in an offscreen
            document; MV3 service workers can't use WebGPU.
            <strong className="ml-1">Firefox</strong> runs it directly in
            the background page (WebGPU is available from Firefox 141+;
            set <code>dom.webgpu.enabled = true</code> in{" "}
            <code>about:config</code> if needed on Linux).
          </li>
          <li>
            First analysis downloads the model + WebGPU compile artifacts
            (sizes above). Cached in IndexedDB forever after that.
          </li>
          <li>
            Test the model here before clicking Analyze — Firefox WebGPU
            in particular sometimes rejects shaders for specific ops, and
            you'd rather find out at Test time than mid-analysis.
          </li>
        </ul>
      </div>
    </div>
  );
}

function ModelTestRow({
  state,
  onTest,
  onCancel,
  modelIdEmpty,
}: {
  state:
    | { kind: "idle" }
    | {
        kind: "running";
        progress: number;
        message?: string;
        abort: AbortController;
      }
    | {
        kind: "ok";
        sample: string;
        durationMs: number;
        backend?: string;
      }
    | { kind: "failed"; error: string };
  onTest: () => void;
  onCancel: () => void;
  modelIdEmpty: boolean;
}) {
  // Only show the "WebGPU unavailable" hint when the error is
  // genuinely about adapter availability — not just any error that
  // happens to mention "WebGPU" in passing. The OOM error rewrite,
  // for instance, includes "WebGPU device ran out of memory", and
  // we mustn't nudge the user to enable a feature that's already on.
  const looksLikeNoAdapter =
    state.kind === "failed" &&
    /requestAdapter|GPU adapter|no available backend/i.test(state.error) &&
    !/disposed|out of memory|Device was lost|Device destroyed/i.test(state.error);
  const failureHint = looksLikeNoAdapter
    ? "WebGPU isn't available in this browser. Pick Network or Browser-built-in in Settings, or enable WebGPU."
    : null;
  return (
    <div>
      <div className="flex items-center gap-2">
        {state.kind === "running" ? (
          <button
            type="button"
            onClick={onCancel}
            className="rounded-md border border-disagree/40 bg-disagree/10 px-3 py-1 text-sm text-disagree"
          >
            Cancel
          </button>
        ) : (
          <button
            type="button"
            onClick={onTest}
            disabled={modelIdEmpty}
            className="rounded-md border border-accent/40 bg-accent/10 px-3 py-1 text-sm text-accent disabled:opacity-40 dark:text-paper"
          >
            Test model
          </button>
        )}
        <span className="text-xs text-ink/55 dark:text-paper/55">
          Loads the model in this page (with progress) and runs a tiny
          prompt.
        </span>
      </div>
      {state.kind === "running" && (
        <div className="mt-2 space-y-1 text-xs">
          <div className="flex items-center gap-2">
            <Spinner />
            <span className="text-ink/70 dark:text-paper/70">
              {state.message ?? "Loading…"}
            </span>
          </div>
          <div className="h-1 w-full overflow-hidden rounded bg-ink/10 dark:bg-paper/15">
            <div
              className="h-full bg-accent transition-[width] duration-200"
              style={{ width: `${Math.round(state.progress * 100)}%` }}
            />
          </div>
        </div>
      )}
      {state.kind === "ok" && (
        <p className="mt-2 text-xs text-agree">
          ✓ Loaded on{" "}
          <code className="rounded-sm bg-agree/10 px-1">
            {state.backend ?? "unknown"}
          </code>{" "}
          in {(state.durationMs / 1000).toFixed(1)}s. Sample output:{" "}
          <code className="rounded-sm bg-agree/10 px-1">{state.sample}</code>
        </p>
      )}
      {state.kind === "failed" && (
        <>
          <p className="mt-2 break-words text-xs text-disagree">
            ✗ {state.error}
          </p>
          {failureHint && (
            <p className="mt-1 text-xs text-ink/70 dark:text-paper/70">
              ↳ {failureHint}
            </p>
          )}
        </>
      )}
      <p className="mt-1 text-[11px] text-ink/45 dark:text-paper/45">
        Detailed transcript appears in the side panel's debug log
        (the panel auto-opens when you click <em>Test model</em>; enable{" "}
        <em>Show debug log</em> in <em>Behaviour</em> below if you don't
        see it).
      </p>
    </div>
  );
}

function Spinner() {
  return (
    <svg
      className="h-3.5 w-3.5 animate-spin text-accent"
      viewBox="0 0 24 24"
      fill="none"
    >
      <circle
        cx="12"
        cy="12"
        r="9"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeOpacity="0.25"
      />
      <path
        d="M21 12a9 9 0 0 0-9-9"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

/* ─── Network: provider dropdown + per-provider panels ──────────── */

function NetworkPanel(props: {
  provider: NetworkProvider;
  onProviderChange: (p: NetworkProvider) => void;
  anthropic: AnthropicConfig;
  onAnthropicChange: (v: AnthropicConfig) => void;
  openai: OpenAIConfig;
  onOpenAIChange: (v: OpenAIConfig) => void;
  google: GoogleConfig;
  onGoogleChange: (v: GoogleConfig) => void;
  ollama: OllamaConfig;
  onOllamaChange: (v: OllamaConfig) => void;
  openaiCompatible: OpenAICompatibleConfig;
  onOpenAICompatChange: (v: OpenAICompatibleConfig) => void;
}) {
  return (
    <>
      <Field label="Provider">
        <select
          className="select"
          value={props.provider}
          onChange={(e) =>
            props.onProviderChange(e.target.value as NetworkProvider)
          }
        >
          <option value="anthropic">Anthropic Claude</option>
          <option value="openai">OpenAI</option>
          <option value="google">Google Gemini</option>
          <option value="ollama">Ollama (native API, schema-constrained)</option>
          <option value="openai-compatible">
            OpenAI-compatible (OpenRouter, LM Studio, Groq, Together, vLLM, …)
          </option>
        </select>
      </Field>
      {props.provider === "anthropic" && (
        <AnthropicForm value={props.anthropic} onChange={props.onAnthropicChange} />
      )}
      {props.provider === "openai" && (
        <OpenAIForm value={props.openai} onChange={props.onOpenAIChange} />
      )}
      {props.provider === "google" && (
        <GoogleForm value={props.google} onChange={props.onGoogleChange} />
      )}
      {props.provider === "ollama" && (
        <OllamaForm value={props.ollama} onChange={props.onOllamaChange} />
      )}
      {props.provider === "openai-compatible" && (
        <OpenAICompatForm
          value={props.openaiCompatible}
          onChange={props.onOpenAICompatChange}
        />
      )}
    </>
  );
}

function AnthropicForm({
  value,
  onChange,
}: {
  value: AnthropicConfig;
  onChange: (v: AnthropicConfig) => void;
}) {
  return (
    <>
      <Field label="API key">
        <input
          className="input"
          type="password"
          autoComplete="off"
          placeholder="sk-ant-…"
          value={value.apiKey}
          onChange={(e) => onChange({ ...value, apiKey: e.target.value })}
        />
        <ProviderLink
          href="https://console.anthropic.com/settings/keys"
          label="Get a key →"
        />
      </Field>
      <Field label="Model">
        <input
          className="input"
          value={value.model}
          onChange={(e) => onChange({ ...value, model: e.target.value })}
          placeholder="claude-haiku-4-5-20251001"
        />
      </Field>
    </>
  );
}

function OpenAIForm({
  value,
  onChange,
}: {
  value: OpenAIConfig;
  onChange: (v: OpenAIConfig) => void;
}) {
  return (
    <>
      <Field label="API key">
        <input
          className="input"
          type="password"
          autoComplete="off"
          placeholder="sk-…"
          value={value.apiKey}
          onChange={(e) => onChange({ ...value, apiKey: e.target.value })}
        />
        <ProviderLink
          href="https://platform.openai.com/api-keys"
          label="Get a key →"
        />
      </Field>
      <Field label="Model">
        <input
          className="input"
          value={value.model}
          onChange={(e) => onChange({ ...value, model: e.target.value })}
          placeholder="gpt-4o-mini"
        />
      </Field>
    </>
  );
}

function GoogleForm({
  value,
  onChange,
}: {
  value: GoogleConfig;
  onChange: (v: GoogleConfig) => void;
}) {
  return (
    <>
      <Field label="API key">
        <input
          className="input"
          type="password"
          autoComplete="off"
          placeholder="AIza…"
          value={value.apiKey}
          onChange={(e) => onChange({ ...value, apiKey: e.target.value })}
        />
        <ProviderLink
          href="https://aistudio.google.com/apikey"
          label="Get a key from AI Studio →"
        />
      </Field>
      <Field label="Model">
        <input
          className="input"
          value={value.model}
          onChange={(e) => onChange({ ...value, model: e.target.value })}
          placeholder="gemini-2.5-flash"
        />
      </Field>
    </>
  );
}

function OllamaForm({
  value,
  onChange,
}: {
  value: OllamaConfig;
  onChange: (v: OllamaConfig) => void;
}) {
  const [probing, setProbing] = useState(false);
  const [probeResult, setProbeResult] = useState<
    | { ok: true; models: string[] }
    | { ok: false; reason: string; detail: string }
    | null
  >(null);

  const test = async () => {
    setProbing(true);
    setProbeResult(null);
    try {
      setProbeResult(await probeOllama(value.baseUrl));
    } finally {
      setProbing(false);
    }
  };

  return (
    <>
      <Field label="Base URL">
        <input
          className="input"
          value={value.baseUrl}
          onChange={(e) => onChange({ ...value, baseUrl: e.target.value })}
          placeholder="http://localhost:11434"
        />
      </Field>
      <Field label="Model tag">
        <input
          className="input"
          value={value.model}
          onChange={(e) => onChange({ ...value, model: e.target.value })}
          placeholder="llama3.2:3b"
        />
        <p className="mt-1 text-xs text-ink/55 dark:text-paper/55">
          Any model tag from <code>ollama list</code>.
        </p>
      </Field>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={test}
          disabled={probing || !value.baseUrl}
          className="rounded-md border border-accent/40 bg-accent/10 px-3 py-1 text-sm text-accent disabled:opacity-40 dark:text-paper"
        >
          {probing ? "Testing…" : "Test connection"}
        </button>
        <ProbeBadge result={probeResult} />
      </div>
      <CorsHint kind="ollama" />
    </>
  );
}

function OpenAICompatForm({
  value,
  onChange,
}: {
  value: OpenAICompatibleConfig;
  onChange: (v: OpenAICompatibleConfig) => void;
}) {
  const [probing, setProbing] = useState(false);
  const [probeResult, setProbeResult] = useState<
    | { ok: true; models: string[] }
    | { ok: false; reason: string; detail: string }
    | null
  >(null);

  const presets: { label: string; baseUrl: string }[] = [
    { label: "Ollama (localhost)", baseUrl: "http://localhost:11434/v1" },
    { label: "LM Studio (localhost)", baseUrl: "http://localhost:1234/v1" },
    { label: "vLLM / llama.cpp (localhost)", baseUrl: "http://localhost:8000/v1" },
    { label: "OpenRouter", baseUrl: "https://openrouter.ai/api/v1" },
    { label: "Groq", baseUrl: "https://api.groq.com/openai/v1" },
    { label: "Together AI", baseUrl: "https://api.together.xyz/v1" },
    { label: "DeepInfra", baseUrl: "https://api.deepinfra.com/v1/openai" },
  ];

  const applyPreset = (label: string, baseUrl: string) =>
    onChange({ ...value, baseUrl, presetName: label });

  const test = async () => {
    setProbing(true);
    setProbeResult(null);
    try {
      setProbeResult(await probeOpenAI(value.baseUrl, value.apiKey));
    } finally {
      setProbing(false);
    }
  };

  return (
    <>
      <Field label="Quick presets">
        <div className="flex flex-wrap gap-1">
          {presets.map((p) => (
            <button
              type="button"
              key={p.label}
              onClick={() => applyPreset(p.label, p.baseUrl)}
              className={
                "rounded-sm border px-2 py-0.5 text-xs " +
                (value.presetName === p.label
                  ? "border-accent bg-accent/10 text-accent"
                  : "border-ink/15 hover:border-ink/30 dark:border-paper/20 dark:hover:border-paper/40")
              }
            >
              {p.label}
            </button>
          ))}
        </div>
      </Field>
      <Field label="Base URL">
        <input
          className="input"
          value={value.baseUrl}
          onChange={(e) =>
            onChange({ ...value, baseUrl: e.target.value, presetName: "" })
          }
          placeholder="https://api.example.com/v1"
        />
      </Field>
      <Field label="API key (leave blank for keyless local servers)">
        <input
          className="input"
          type="password"
          autoComplete="off"
          value={value.apiKey}
          onChange={(e) => onChange({ ...value, apiKey: e.target.value })}
        />
      </Field>
      <Field label="Model">
        <input
          className="input"
          value={value.model}
          onChange={(e) => onChange({ ...value, model: e.target.value })}
          placeholder="model-id"
        />
      </Field>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={test}
          disabled={probing || !value.baseUrl}
          className="rounded-md border border-accent/40 bg-accent/10 px-3 py-1 text-sm text-accent disabled:opacity-40 dark:text-paper"
        >
          {probing ? "Testing…" : "Test connection"}
        </button>
        <ProbeBadge result={probeResult} />
      </div>
      <CorsHint kind="openai-compatible" />
    </>
  );
}

function ProbeBadge({
  result,
}: {
  result:
    | { ok: true; models: string[] }
    | { ok: false; reason: string; detail: string }
    | null;
}) {
  if (!result) return null;
  if (result.ok) {
    const list = result.models.length
      ? `: ${result.models.slice(0, 4).join(", ")}${result.models.length > 4 ? "…" : ""}`
      : "";
    return (
      <span className="text-xs text-agree">
        ✓ Connected — {result.models.length} model
        {result.models.length === 1 ? "" : "s"} installed{list}
      </span>
    );
  }
  return (
    <span className="text-xs text-disagree">
      ✗{" "}
      {result.reason === "cors"
        ? "Reachability check failed — likely CORS / origin block."
        : `${result.reason}: ${result.detail.slice(0, 80)}`}
    </span>
  );
}

function CorsHint({ kind }: { kind: "ollama" | "openai-compatible" }) {
  if (kind === "ollama") {
    return (
      <div className="mt-2 rounded-sm border border-ink/10 bg-ink/[0.03] p-2 text-xs leading-relaxed dark:border-paper/15 dark:bg-paper/[0.04]">
        Ollama rejects browser-extension origins by default. Start the
        daemon with:
        <pre className="mt-1 overflow-x-auto rounded-sm bg-ink/10 p-2 dark:bg-paper/10">
{`OLLAMA_ORIGINS="chrome-extension://*,moz-extension://*" ollama serve

# or, for any origin:
OLLAMA_ORIGINS="*" ollama serve`}
        </pre>
      </div>
    );
  }
  return (
    <div className="mt-2 rounded-sm border border-ink/10 bg-ink/[0.03] p-2 text-xs leading-relaxed dark:border-paper/15 dark:bg-paper/[0.04]">
      Most cloud providers (OpenRouter, Groq, Together, …) accept
      browser-extension origins out of the box. Local servers (LM Studio,
      vLLM, llama.cpp) usually need a CORS allow-list — check their docs
      for an env var or flag.
    </div>
  );
}

function ProviderLink({ href, label }: { href: string; label: string }) {
  return (
    <p className="mt-1 text-xs">
      <a
        className="text-accent hover:underline"
        href={href}
        target="_blank"
        rel="noreferrer"
      >
        {label}
      </a>
    </p>
  );
}

/* ─── Reused layout / utility components ────────────────────────── */

function Section({
  title,
  help,
  children,
}: {
  title: string;
  help?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mb-8 rounded-md border border-ink/10 bg-paper/60 p-5 dark:border-paper/15 dark:bg-paper/[0.04]">
      <h2 className="text-base font-semibold">{title}</h2>
      {help && (
        <p className="mt-1 text-xs text-ink/60 dark:text-paper/55">{help}</p>
      )}
      <div className="mt-3 space-y-3">{children}</div>
    </section>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-ink/55 dark:text-paper/60">
        {label}
      </span>
      {children}
    </label>
  );
}

function CustomUrlList({
  urls,
  onChange,
}: {
  urls: string[];
  onChange: (urls: string[]) => void;
}) {
  const [draft, setDraft] = useState("");
  const valid = useMemo(() => {
    if (!draft) return false;
    try {
      const u = new URL(draft.startsWith("http") ? draft : `https://${draft}`);
      return !!u.hostname && u.hostname.includes(".");
    } catch {
      return false;
    }
  }, [draft]);

  const add = () => {
    const url = draft.startsWith("http") ? draft : `https://${draft}`;
    if (urls.includes(url)) return;
    onChange([...urls, url]);
    setDraft("");
  };

  return (
    <div>
      <ul className="space-y-1">
        {urls.map((u) => (
          <li
            key={u}
            className="flex items-center justify-between rounded-sm border border-ink/10 bg-paper/80 px-2 py-1 text-sm dark:border-paper/15 dark:bg-paper/[0.06]"
          >
            <span className="truncate">{u}</span>
            <button
              type="button"
              onClick={() => onChange(urls.filter((x) => x !== u))}
              className="ml-2 text-xs text-disagree hover:underline"
            >
              remove
            </button>
          </li>
        ))}
      </ul>
      <div className="mt-2 flex gap-2">
        <input
          className="input flex-1"
          placeholder="https://example.org"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && valid) add();
          }}
        />
        <button
          type="button"
          onClick={add}
          disabled={!valid}
          className="rounded-md bg-accent px-3 py-1 text-sm text-white disabled:opacity-40"
        >
          Add
        </button>
      </div>
    </div>
  );
}

function humanize(status: string): string {
  switch (status) {
    case "available":
      return "ready (on-device)";
    case "downloadable":
      return "available — model will download on first use";
    case "downloading":
      return "downloading model…";
    case "unavailable":
      return "unavailable on this device";
    default:
      return status;
  }
}
