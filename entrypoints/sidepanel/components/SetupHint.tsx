import type { Settings } from "@/types";

export function SetupHint({
  settings,
  onOpen,
}: {
  settings: Settings;
  onOpen: () => void;
}) {
  const missing: string[] = [];
  if (!settings.braveApiKey) missing.push("Brave Search API key");
  for (const m of llmConfigMissing(settings)) missing.push(m);

  return (
    <div className="mb-3 rounded-md border border-accent/40 bg-accent/10 p-3 text-sm">
      <p className="font-medium">Finish setup to enable verification.</p>
      <p className="mt-1 text-ink/70 dark:text-paper/70">
        Missing: {missing.join(", ")}.
      </p>
      <button
        type="button"
        onClick={onOpen}
        className="mt-2 rounded-md bg-accent px-3 py-1 text-xs font-medium text-white"
      >
        Open settings
      </button>
    </div>
  );
}

function llmConfigMissing(s: Settings): string[] {
  if (s.tier !== "network") return [];
  switch (s.networkProvider) {
    case "anthropic":
      return s.anthropic.apiKey ? [] : ["Anthropic API key"];
    case "openai":
      return s.openai.apiKey ? [] : ["OpenAI API key"];
    case "google":
      return s.google.apiKey ? [] : ["Google API key"];
    case "ollama":
      return s.ollama.baseUrl ? [] : ["Ollama base URL"];
    case "openai-compatible": {
      const out: string[] = [];
      if (!s.openaiCompatible.baseUrl) out.push("OpenAI-compatible base URL");
      if (!s.openaiCompatible.model) out.push("model name");
      return out;
    }
  }
}
