# DoppelCheck

A critical-thinking sidekick for the open web. DoppelCheck reads the article you're on, isolates the most load-bearing factual claims, then — claim by claim — checks them against existing fact-check databases and independent sources, and shows where they agree, where they disagree, and what the disagreement actually says.

It's a browser extension. There is no server, no Docker, no Ollama, nothing to install on your machine beyond the extension itself. Page content stays on-device by default.

> **Note:** v1.0 is a complete rewrite of DoppelCheck on a modern stack. The original Python + FastAPI + Ollama + bookmarklet implementation is preserved in [`legacy/`](legacy/) and remains runnable. See [`REVISION.md`](REVISION.md) for the design rationale.

## Install

DoppelCheck targets Chromium browsers (Chrome, Edge, Brave, Arc, Opera) on Windows / macOS / Linux / ChromeOS, plus Firefox 128+.

### From source (until the Web Store listing is published)

```bash
git clone https://github.com/Doppelcheck/main doppelcheck
cd doppelcheck
npm install
npm run build           # produces .output/chrome-mv3/
# or:  npm run build:firefox  → .output/firefox-mv2/
```

Then in the browser:

- **Chrome / Edge / Brave**: open `chrome://extensions`, enable "Developer mode", click "Load unpacked", point at `.output/chrome-mv3/`.
- **Firefox**: open `about:debugging#/runtime/this-firefox`, "Load Temporary Add-on", point at `.output/firefox-mv2/manifest.json`.

The DoppelCheck icon now sits in the toolbar. Clicking it opens the side panel.

### Configure

Open the extension's options page (right-click the toolbar icon → "Options", or click the gear inside the side panel). At minimum you need:

1. **A Brave Search API key.** Free tier gives ~1k queries/month — enough for personal use. Get one at [api-dashboard.search.brave.com](https://api-dashboard.search.brave.com/app/keys).
2. **A language model.** Pick one of:
   - **Browser built-in (default).** Free, on-device, private. Uses Chrome's Gemini Nano via the Prompt API. Requires Chrome 138+ on a supported OS; the model downloads on first use and the options page shows status. Not available on Firefox.
   - **Cloud API.** Bring an API key for **Anthropic Claude** (best price/perf for this workload is `claude-haiku-4-5-20251001` at $1/$5 per million tokens), **OpenAI**, or **Google Gemini**. Streaming, schema-aware where the API supports it. Keys go directly to the provider — DoppelCheck never proxies them.
   - **Local server.** Point DoppelCheck at any HTTP-reachable LLM running on your own machine. Two protocols are supported: **Ollama** (native API with schema-constrained generation) and **OpenAI-compatible** (LM Studio, llama.cpp server, vLLM, …). The easiest path is the companion [doppelcheck/gemma-server](https://github.com/doppelcheck/gemma-server) — a one-shot installer that runs Gemma 4 locally and exposes it as an Ollama server on `localhost:11434`; the options page has a one-click "Use gemma-server" preset.

Optional but recommended:

3. **A Google Fact Check Tools API key.** Free. Surfaces existing fact-checks from publishers like Snopes, PolitiFact, Correctiv, dpa-Faktencheck *before* DoppelCheck spends LLM calls on the open web. Enable the API at [developers.google.com/fact-check/tools/api](https://developers.google.com/fact-check/tools/api).
4. **Trusted sources.** Add publication domains you already trust — Brave will run a site-restricted search against each of them in addition to the general web.

Settings sync across your browsers via `chrome.storage.sync`. Keys never leave your device except to the API they belong to.

## Use

1. Open the article you want to scrutinise.
2. Click the DoppelCheck icon. The side panel opens.
3. Click **Analyze page**. Within a few seconds the panel lists the strongest factual claims in the article, in the article's language.
4. Click **Verify** on any claim. DoppelCheck:
   - queries Google Fact Check Tools for an existing review of that claim,
   - generates a search query and runs it against Brave Search (general + your trusted domains),
   - fetches each candidate source and asks the LLM whether it agrees, disagrees, or is unrelated, with a verbatim evidence quote,
   - highlights the claim and the evidence directly on the page (using the CSS Custom Highlight API — no DOM mutation).
5. Click any quote to follow through to the source.

## What you give up vs. the legacy version

- **No fully offline default.** The legacy version ran a local Ollama LLM by default, which let it work air-gapped at the cost of a multi-gigabyte install. The default tier here uses Chrome's on-device Gemini Nano (provided by Google but running locally without network calls). If you specifically need *third-party-free* local inference, install the companion [`doppelcheck/gemma-server`](https://github.com/doppelcheck/gemma-server) and pick it from the **Local server** tier — same air-gapped guarantee as the legacy Ollama setup, with a one-shot installer instead of Docker.
- **Mobile is out of scope.** Chrome's built-in AI doesn't ship on Android/iOS yet; mobile would need a different host.

## What's improved

- One-click install instead of Docker + bookmarklet drag.
- ~500 KB total extension size vs. ~10 GB Docker image.
- Persistent UI in the browser's side panel — no more sidebar getting re-injected on every click.
- No CSP `/proxy` workaround — content scripts have access by default.
- Single TypeScript codebase, cross-browser, fully typed.
- Direct Google Fact Check Tools integration: catches already-fact-checked claims for free before any LLM call.
- Streaming claim extraction — claims appear in the panel as the model produces them.

## Project layout

```
.
├── entrypoints/              extension surfaces
│   ├── background.ts         service worker — orchestrates extract/verify
│   ├── content.ts            content script — Defuddle + CSS Highlights
│   ├── sidepanel/            React UI shown in the browser side panel
│   └── options/              React UI for the settings page
├── lib/                      domain logic, all browser-side
│   ├── llm/                  tiered LLM router (chrome-builtin, anthropic, openai, google, ollama, openai-compatible)
│   ├── search/               Brave Search + Google Fact Check clients
│   ├── extract/              Defuddle wrapper + CSS Custom Highlight API
│   ├── messaging/            typed port-based comms (panel ↔ background)
│   ├── storage.ts            chrome.storage.sync wrapper for Settings
│   ├── fetch-source.ts       service-worker side fetch + cheap HTML strip
│   └── json.ts               LLM-output JSON tolerant parser + array streamer
├── components/               (room for shared React components)
├── assets/globals.css        Tailwind + CSS Custom Highlight API styles
├── public/                   static assets copied to the extension root
├── wxt.config.ts             WXT build config (Chrome MV3 + Firefox MV2)
└── legacy/                   the previous Python + bookmarklet implementation
```

## Develop

```bash
npm run dev              # WXT dev server, auto-reloads on save (Chrome)
npm run dev:firefox      # same, Firefox profile
npm run compile          # tsc --noEmit
npm run zip              # produce a .zip ready for the Chrome Web Store
```

## License

MIT for the code. IBM Plex fonts (used in the UI styling) are SIL Open Font License 1.1.

## Acknowledgements

DoppelCheck began as a project by Mark Wernsdorfer with funding from WPK-Innovationsfonds and Media Lab Bayern, aimed at promoting critical evaluation of online information.
