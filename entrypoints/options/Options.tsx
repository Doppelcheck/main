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
} from "@/types";
import { probeOllama } from "@/lib/llm/ollama";
import { probeOpenAI } from "@/lib/llm/openai";

/**
 * UI-only top-level choice. Storage keeps two flat fields (`tier` and
 * `networkProvider`); the picker collapses them into a single 3-way
 * card row so the user doesn't have to click "Network" and *then*
 * "Cloud" / "Local server" — the two clicks are the same decision.
 *
 *   - "browser-native" → tier="browser-native"
 *   - "cloud"          → tier="network", networkProvider ∈ CLOUD_PROVIDERS
 *   - "local"          → tier="network", networkProvider ∈ LOCAL_PROVIDERS
 */
type TierChoice = "browser-native" | "cloud" | "local";

const CLOUD_PROVIDERS: NetworkProvider[] = ["anthropic", "openai", "google"];

function tierChoiceOf(s: Settings): TierChoice {
  if (s.tier === "browser-native") return "browser-native";
  return CLOUD_PROVIDERS.includes(s.networkProvider) ? "cloud" : "local";
}

/**
 * Compute the `(tier, networkProvider)` pair for a chosen card.
 * Preserves the user's per-group provider when they toggle within
 * "cloud" or "local"; only resets to a sensible default when they
 * switch *across* groups.
 */
function applyTierChoice(s: Settings, choice: TierChoice): Settings {
  if (choice === "browser-native") return { ...s, tier: "browser-native" };
  const inCloud = CLOUD_PROVIDERS.includes(s.networkProvider);
  if (choice === "cloud") {
    const provider = inCloud ? s.networkProvider : "anthropic";
    return { ...s, tier: "network", networkProvider: provider };
  }
  const provider = inCloud ? "ollama" : s.networkProvider;
  return { ...s, tier: "network", networkProvider: provider };
}

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

  const setTierChoice = (choice: TierChoice) => {
    if (!s) return;
    userTouched.current = true;
    setS(applyTierChoice(s, choice));
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

  const tierChoice = tierChoiceOf(s);

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
          help="Pick where you want analysis to run."
        >
          <TierPicker value={tierChoice} onChange={setTierChoice} />

          {tierChoice === "browser-native" && <BrowserNativePanel />}

          {tierChoice === "cloud" && (
            <CloudPanel
              provider={s.networkProvider}
              onProviderChange={(p) => update("networkProvider", p)}
              anthropic={s.anthropic}
              onAnthropicChange={(v) => update("anthropic", v)}
              openai={s.openai}
              onOpenAIChange={(v) => update("openai", v)}
              google={s.google}
              onGoogleChange={(v) => update("google", v)}
            />
          )}

          {tierChoice === "local" && (
            <LocalServerPanel
              provider={s.networkProvider}
              onProviderChange={(p) => update("networkProvider", p)}
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

const ALL_TIER_CARDS: { id: TierChoice; title: string; subtitle: string }[] = [
  {
    id: "browser-native",
    title: "Browser built-in",
    subtitle:
      "Use the browser's own on-device AI. Free, private, no setup beyond enabling it.",
  },
  {
    id: "cloud",
    title: "Cloud APIs",
    subtitle: "Anthropic, OpenAI, or Google. API key required.",
  },
  {
    id: "local",
    title: "Local server",
    subtitle: "Ollama or any OpenAI-compatible HTTP endpoint.",
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
  value: TierChoice;
  onChange: (t: TierChoice) => void;
}) {
  const browserNativeAvailable = typeof LanguageModel !== "undefined";
  const cards = ALL_TIER_CARDS.filter(
    (c) => c.id !== "browser-native" || browserNativeAvailable,
  );
  // Auto-migrate: if the saved tier is `browser-native` but the API
  // isn't here, nudge the user onto Cloud APIs so they don't sit on
  // a tier that will only ever error.
  useEffect(() => {
    if (value === "browser-native" && !browserNativeAvailable) {
      onChange("cloud");
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
        no built-in chat-style LLM — pick <em>Network</em> there.
      </p>
    </div>
  );
}

/* ─── Cloud APIs: provider dropdown + per-provider form ─────────── */

function CloudPanel(props: {
  provider: NetworkProvider;
  onProviderChange: (p: NetworkProvider) => void;
  anthropic: AnthropicConfig;
  onAnthropicChange: (v: AnthropicConfig) => void;
  openai: OpenAIConfig;
  onOpenAIChange: (v: OpenAIConfig) => void;
  google: GoogleConfig;
  onGoogleChange: (v: GoogleConfig) => void;
}) {
  return (
    <div className="space-y-3">
      <Field label="Cloud provider">
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
    </div>
  );
}

/* ─── Local server: provider dropdown + per-provider form ───────── */

function LocalServerPanel(props: {
  provider: NetworkProvider;
  onProviderChange: (p: NetworkProvider) => void;
  ollama: OllamaConfig;
  onOllamaChange: (v: OllamaConfig) => void;
  openaiCompatible: OpenAICompatibleConfig;
  onOpenAICompatChange: (v: OpenAICompatibleConfig) => void;
}) {
  // Preset for the companion gemma-server: it exposes Ollama on
  // localhost:11434 with `gemma4:e2b-it-q4_K_M` pre-installed (the
  // E2B-Instruct, q4_K_M-quantised Gemma 4 build that ships with the
  // installer). One click pre-fills the Ollama form below.
  const applyGemmaServer = () => {
    props.onProviderChange("ollama");
    props.onOllamaChange({
      baseUrl: "http://localhost:11434",
      model: "gemma4:e2b-it-q4_K_M",
    });
  };

  return (
    <div className="space-y-3">
      <div className="rounded-md border border-accent/30 bg-accent/[0.06] p-3 text-xs leading-relaxed">
        <p className="font-semibold text-ink dark:text-paper">
          Easiest local setup: <code>doppelcheck/gemma-server</code>
        </p>
        <p className="mt-1 text-ink/75 dark:text-paper/70">
          A zero-config installer that runs Gemma 4 locally and exposes
          it as an Ollama-compatible server on{" "}
          <code>localhost:11434</code>. Install it from{" "}
          <a
            className="text-accent hover:underline"
            href="https://github.com/doppelcheck/gemma-server"
            target="_blank"
            rel="noreferrer"
          >
            github.com/doppelcheck/gemma-server
          </a>
          , then click the button below to point DoppelCheck at it.
        </p>
        <button
          type="button"
          onClick={applyGemmaServer}
          className="mt-2 rounded-md border border-accent/40 bg-accent/10 px-3 py-1 text-sm text-accent dark:text-paper"
        >
          Use gemma-server (localhost:11434)
        </button>
      </div>

      <Field label="Local server type">
        <select
          className="select"
          value={props.provider}
          onChange={(e) =>
            props.onProviderChange(e.target.value as NetworkProvider)
          }
        >
          <option value="ollama">
            Ollama — native API, schema-constrained (also: gemma-server)
          </option>
          <option value="openai-compatible">
            OpenAI-compatible — LM Studio, llama.cpp server, vLLM, …
          </option>
        </select>
      </Field>
      {props.provider === "ollama" && (
        <OllamaForm value={props.ollama} onChange={props.onOllamaChange} />
      )}
      {props.provider === "openai-compatible" && (
        <OpenAICompatForm
          value={props.openaiCompatible}
          onChange={props.onOpenAICompatChange}
        />
      )}
    </div>
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
          placeholder="http://localhost:8000/v1"
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
      Local servers (LM Studio, vLLM, llama.cpp) usually need a CORS
      allow-list — check their docs for an env var or flag that
      whitelists <code>chrome-extension://</code> and{" "}
      <code>moz-extension://</code> origins.
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

