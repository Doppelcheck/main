# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A browser extension (Manifest V3) that helps the user critically evaluate the article they're reading: extract factual claims, look for existing fact-checks, search independent sources, and surface contradictions inline.

> **Major rewrite:** The current code is a clean reimplementation. The previous Python + FastAPI + Ollama + bookmarklet codebase is preserved unchanged in [`legacy/`](legacy/) for reference and is still runnable from there. The reasoning behind the rewrite is in [`REVISION.md`](REVISION.md) — read it before proposing architectural changes.

## Commands

```bash
npm install              # postinstall runs `wxt prepare` to generate types
npm run dev              # Chrome dev profile with HMR
npm run dev:firefox      # Firefox dev profile
npm run build            # → .output/chrome-mv3/
npm run build:firefox    # → .output/firefox-mv2/
npm run compile          # tsc --noEmit (type-check only)
npm run zip              # zip a release build for the Chrome Web Store
```

There is no test suite or linter wired up — `tsc --noEmit` is the only static check. Both Chrome and Firefox builds must succeed for cross-browser claims to hold; CI should run both.

## Architecture

The extension splits along three runtime boundaries, each with very different capabilities:

### 1. Content script (`entrypoints/content.ts`)

Runs in the page's DOM. Sole owner of:

- **Page extraction** — wraps [Defuddle](https://github.com/kepano/defuddle) (`lib/extract/index.ts`). Defuddle replaces the legacy `trafilatura → lxml → html2text` chain. It outputs Markdown directly.
- **In-page highlighting** — uses the [CSS Custom Highlight API](https://developer.mozilla.org/en-US/docs/Web/API/CSS_Custom_Highlight_API) via `lib/extract/highlight.ts`. Highlights are *applied without modifying the DOM*; the legacy bookmarklet's "store original styles → inject spans → restore on close" dance is gone. The highlight selector falls back from exact match → whitespace-collapsed match → longest-prefix fuzzy match before giving up.

It exposes one message-handler that takes `{ kind: "extract" | "highlight" | "clear-highlights" }` and replies synchronously.

### 2. Background service worker (`entrypoints/background.ts`)

The orchestrator. Holds no persistent state — everything important lives in `chrome.storage.sync` (settings) or transient port-scoped variables.

Two flows, driven by commands from the side panel over a long-lived `chrome.runtime.Port`:

- **`analyze`** → `sendToTab(extract)` → LLM streamed claim extraction → emit `claim` events as each JSON element completes (see `lib/json.ts:readArrayElements`). The streaming JSON-array reader is what gives the side panel its progressive UI.
- **`verify`** → Google Fact Check lookup → LLM search-query generation → Brave Search (general + per-custom-domain fan-out) → for each hit: `fetchSourceText` → LLM comparison prompt → emit `verdict` event. Then highlights the claim + agree/disagree evidence on the original page in one final `sendToTab(highlight)` call.

MV3 service workers don't have `DOMParser`. `lib/fetch-source.ts` deliberately uses a regex strip rather than running Defuddle in the background — the LLM is doing the actual judgment work, so a slightly noisier text input is acceptable. **If extraction quality on candidate sources becomes the bottleneck, the upgrade path is an offscreen document that runs Defuddle.** Don't try to import Defuddle into the service worker; it needs `Document`.

### 3. Side panel + options pages (`entrypoints/sidepanel/`, `entrypoints/options/`)

React + TypeScript + Tailwind. The side panel uses the Chrome `chrome.sidePanel` API (Chrome 114+) and Firefox's `sidebar_action` (different API, same UX) — `wxt.config.ts` emits the right manifest fields per browser. Both wire through `chrome.action` to open on icon-click.

App state for the side panel is a single `useReducer` in `entrypoints/sidepanel/state.ts`. Server events from the background drive 90% of state transitions; the discriminated union `ServerEvent` in `types.ts` is the source of truth for what the UI can react to. **When you add a new background→panel signal, add it as a new variant on `ServerEvent`, not as a side channel.**

### LLM tiering (`lib/llm/`)

The router lives in `lib/llm/index.ts`. There are two implementations, both behind the same `LLM` interface:

| Tier | When | File |
|---|---|---|
| 1 — Chrome Built-in AI (Gemini Nano on-device) | Default. Probes `LanguageModel.availability()` at request time and falls back if unavailable. | `lib/llm/chrome-ai.ts` |
| 2 — Anthropic Claude (`claude-haiku-4-5-20251001` default) | Either explicitly selected, or auto-fallback when Tier 1 is unavailable and a key is present. Streaming uses Anthropic's SSE; we parse it directly from `fetch` rather than pulling in `@anthropic-ai/sdk`. | `lib/llm/anthropic.ts` |

Streaming returns *cumulative* strings, not deltas. This is intentional — the JSON-array streaming reader in `lib/json.ts` consumes a growing buffer, so each LLM tier just yields the running concatenation.

All prompts are centralised in `lib/llm/prompts.ts`. Reply-format constraints (always JSON, never prose, language follows the article) are enforced in the system message — change them in *one place*, never per-call.

## Cross-cutting conventions

- **Path alias:** WXT auto-generates `@/*` → project root. Don't add custom Vite aliases; they clash with WXT's. The legacy `src/` directory has been flattened (`lib/`, `components/`, `types.ts` all sit at the project root) so import paths match WXT's expectations.
- **Settings shape is owned by Zod** in `types.ts`. `lib/storage.ts` re-validates on read so a malformed `chrome.storage.sync` blob can't poison runtime.
- **Don't do "best-effort" parallel fetches in `verify`.** Sources are processed sequentially so the side panel renders verdicts in the same order Brave returned hits — users find this much more readable than racing results. Cost is bounded anyway (5 hits × ~one LLM call each).
- **MV3 service worker constraints:** no `XMLHttpRequest`, no `DOMParser`, no `localStorage`. Use `fetch`, regex string work, and `chrome.storage.*` respectively.
- **Cross-browser:** `chrome.sidePanel` is Chromium-only. The Firefox path goes via `sidebar_action`; the conditional in `wxt.config.ts` and the `globalThis.browser?.sidebarAction` shim in `background.ts` are the only two places that branch by browser. Add new branches there only — don't sprinkle `if (chrome.sidePanel)` checks throughout.

## Things to know about the build

- WXT 0.19, Vite 6 under the hood. Builds Chrome MV3 by default; Firefox build emits MV2 (Firefox MV3 sidebar APIs aren't a strict superset of Chromium's, so MV2 is currently the cleaner cross-browser target).
- Icons: `public/icon/{16,48,128}.png` are committed and referenced by the manifest. They're regenerated from `public/icon.svg` by a small Pillow script if you change the source — there's no automatic SVG→PNG step in the build.
- Public files in `public/` are copied verbatim into the extension. Don't put anything large there; it ships to every user.

## Legacy directory

`legacy/` contains the previous Python implementation — FastAPI server + Ollama LLM + Playwright fetch + bookmarklet. It's runnable on its own with `cd legacy && docker compose up`. Use it as a reference for prompt wording, search behaviour, or the original bookmarklet UI flow. **Do not import from it; it has no relationship to the current build pipeline.**
