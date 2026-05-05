# DoppelCheck — Modern Reimagining

A reset of the project, keeping the **purpose** intact and rebuilding everything else around what browsers can natively do in 2026.

## What the project is actually trying to do

Strip away the implementation, and DoppelCheck does five things:

1. Take whatever the user is looking at in the browser.
2. Pull the substantive claims out of it.
3. Find independent sources that talk about the same claims.
4. Compare what the sources say to what the page says.
5. Show the user the divergence, in-place.

That's it. Everything else — the Python server, Ollama, Docker, the bookmarklet, Playwright, spaCy, stanza, sentence-transformers, the trafilatura pipeline, the proxy hack — is *plumbing for the same five steps*. In 2020 the plumbing was unavoidable. In 2026 the browser can do most of it natively.

## Why the current architecture has aged badly

| Pain point | Root cause |
|---|---|
| Two-step install (Docker + bookmarklet drag) | No single distribution channel for "code that runs on a page." |
| `/proxy` route exists | Bookmarklet JS gets blocked by Content Security Policy on hardened sites. There's no fix at the bookmarklet layer. |
| ~10 GB Docker image, GPU profiles, NVIDIA toolkit setup | Ollama needed because there was no in-browser LLM. |
| `torch==2.1.2`, `numpy<2.0`, `transformers==4.41.0` pinned forever | The ML stack carries five frameworks (torch, transformers, spaCy, stanza, sentence-transformers) for tasks the browser now does in one API call. |
| Stanza + spaCy + custom German pipeline | Language detection and tokenization didn't exist as web APIs. They do now. |
| `trafilatura` + custom chunker + entity extractor | Article extraction had no good JS implementation. It does now. |
| Three swappable chunkers (`embedding_clustering`, `tfidf_mmr`, `graph_textrank`) and two retrievers committed side-by-side | The team was hedging because none of the embedding-based approaches were obviously right — but running embeddings locally was expensive enough that they kept all three. |
| Bookmarklet UI re-injects on every click, loses state | No persistent UI surface from a bookmarklet. |
| Privacy depends on running Ollama locally | The only way to keep page content out of the cloud was to bring an LLM down. |

The **single architectural decision** that drives all of these is: *use a bookmarklet so you don't need to ship an extension*. That decision is no longer correct. Browser extensions are a one-click install from a store, work across every desktop browser, and have access to all the APIs the bookmarklet is fighting against.

## The gold-standard stack

### Distribution: Manifest V3 browser extension

Replaces: bookmarklet, `/proxy` route, the entire installation README section.

- **One-click install** from Chrome Web Store, Firefox Add-ons, Edge Add-ons. No Docker, no `python main.py`, no bookmark drag.
- **Content scripts bypass page CSP** — the `/proxy` workaround disappears entirely.
- **Side Panel API** (`chrome.sidePanel`, Chrome 114+) gives a persistent UI that survives navigation, instead of re-injecting a sidebar `<div>` into the DOM on every click. Firefox uses `sidebar_action` (different API, same UX) — a thin compat shim handles both. ([Chrome Side Panel docs](https://developer.chrome.com/docs/extensions/reference/api/sidePanel), [Firefox sidebar_action](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/manifest.json/action))
- **`chrome.storage.sync`** for settings (custom URLs, model choice) — config syncs across the user's devices automatically. Replaces `content_analysis_config.json`.
- **No backend.** Nothing to host, nothing for the user to keep running. The "server" is the extension's service worker.

### Build & framework: WXT + React + TypeScript

Replaces: FastAPI app, Jinja templates, the dual `bookmarklet.html` / `bookmarklet_new.html` split.

- **[WXT](https://wxt.dev)** — Vite-powered, file-based routing, single codebase compiles to Chrome MV3, Firefox MV3, and Edge. ~400 KB output. Plasmo is in maintenance mode as of 2026; CRXJS is too thin for a project this size; WXT is the consensus winner.
- **React + TypeScript** for the side panel UI. Type safety matters more here than it did in `bookmarklet.js` (~80 KB of untyped JS).
- **Tailwind + shadcn/ui** for the UI. Replaces the hand-rolled CSS in `server/static/css/`.
- **Zod** for schema validation at the LLM/search-API boundary, mirroring the role pydantic plays in [server/models.py](server/models.py) today.

### Page extraction: Defuddle

Replaces: `trafilatura`, `markdown_to_plain_text`, the "extract complete sentences" helper, the multi-pass content cleaning logic.

- **[Defuddle](https://github.com/kepano/defuddle)** is the JS-native, MIT-licensed successor to Mozilla Readability. Built by the Obsidian Web Clipper team — already proven inside an extension at scale.
- Recovers from initial detection failures (Readability's biggest weakness — it's overly conservative and silently drops content).
- Outputs clean Markdown directly with normalized handling for code blocks, footnotes, and math. No second-pass cleanup needed.
- Has site-specific extractors for ChatGPT, Reddit, X, etc., for cases where generic heuristics fail.
- **Zero browser dependencies** — the core bundle is dependency-free in the browser, replacing the entire `trafilatura → lxml → html2text` chain.

### Language model: tiered, on-device first

Replaces: Ollama service, `tulu3`, all of `server/services/llm_ollama.py`, the model-pull-on-first-call logic, `check_ollama()`.

**Tier 1 — Chrome built-in AI APIs (default, free, private)**

Chrome 138+ ships several Gemini-Nano-backed APIs that run **fully on-device** with no API key, no network, no install. Critically, the **Prompt API for Extensions is stable** as of Chrome 138. ([Chrome Built-in AI](https://developer.chrome.com/docs/ai/built-in-apis))

| API | Status (Chrome 138+) | Replaces in current code |
|---|---|---|
| `LanguageModel` (Prompt API for Extensions) | **Stable** | The generic `prompt_ollama()` calls — claim extraction, query generation, comparison |
| `Summarizer` | **Stable** | `generate_summary()` in `llm_ollama.py` |
| `Translator` | **Stable** | The English/German bilingual handling |
| `LanguageDetector` | **Stable** | Stanza's only real job in the current code |
| `Writer` / `Rewriter` | Origin trial | Not used today, but useful for "rewrite this claim as a search query" |
| `Proofreader` | Origin trial | n/a |

This collapses **most of `server/services/`, all of `server/utils/nlp.py`, and the entire stanza/spaCy/Ollama dependency tree** into four browser API calls.

**Tier 2 — Cloud fallback for non-Chrome / older Chrome / users who want a stronger model**

User pastes their own API key into settings; nothing routes through us.

- **Anthropic Claude Haiku 4.5** (`claude-haiku-4-5-20251001`) is the right default: $1/$5 per MTok, 200K context, ~4–5× faster than Sonnet. Prompt caching brings the input side to $0.10/MTok, which matters when the same article body is reused across "extract claims," "rewrite to query," and "compare to source." ([Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing))
- Streaming is mandatory — the current bookmarklet shows claims one-by-one as the LLM produces them, and that UX needs to survive the rewrite.

**Tier 3 — Fully-offline fallback**

[transformers.js](https://github.com/huggingface/transformers.js) or [WebLLM](https://github.com/mlc-ai/web-llm) running a small instruct model (Llama 3.2 1B / Phi 3.5 mini / Qwen 2.5 1.5B) via WebGPU, in an offscreen document or web worker. WebLLM is faster (3–10× WASM); transformers.js is more flexible if embeddings are also needed in-browser.

This is the explicit replacement for "user must install Docker + Ollama + pull a 4 GB model." It's **opt-in**, not the default — most users get Tier 1 for free.

### Search: Brave Search API (primary), Tavily (LLM-optimized alternative)

Replaces: `googlesearch-python`, `google-api-python-client`, the Google Custom Search Engine setup, the per-domain manual fan-out in [server/routes.py:187](server/routes.py:187).

- **[Brave Search API](https://brave.com/search/api/)** — independent 30B-page index, lowest latency in the AIMultiple agentic-search benchmark (669 ms avg), best agent-search score. $5/1k queries with 1k free monthly credits for new users — generous enough for typical individual use without ever paying. Privacy-aligned (no tracking), which matches the project's stated values better than Google CSE does.
- **[Tavily](https://tavily.com)** as alternative when the calling code wants pre-ranked, citation-formatted snippets without post-processing. Free tier is 1,000 queries/month.
- **[Exa](https://exa.ai)** for the "find semantically similar content" case — useful when the user wants *related* coverage of a topic rather than literal keyword matches. Worth wiring in as a third option.
- Custom-domain restriction (`custom_urls`) becomes a per-engine `site:` filter rather than the current N-extra-API-calls fan-out — much cheaper and simpler.

### Direct fact-check lookup: Google Fact Check Tools API

**This is missing from the current implementation and is exactly the project's stated purpose.**

The [Fact Check Tools API](https://developers.google.com/fact-check/tools/api) lets you query a global database of `ClaimReview`-tagged articles by claim text. Before doing the full "find sources, compare, score alignment" pipeline, the extension should ask: *has anyone already fact-checked this exact claim?* If a Snopes / PolitiFact / Correctiv / dpa-Faktencheck entry exists, surface it directly. This is one HTTP call and gives users an immediate, authoritative answer for the easy cases. Free.

### Comparison & alignment: simpler than today

Replaces: `e5_semantic_retrieval.py`, `smith_waterman_retriever.py`, `embedding_clustering.py`, `tfidf_mmr.py`, `graph_textrank.py`, `calculate_semantic_alignment`, plus all the torch/sentence-transformers/scikit-learn dependencies that exist only to support them.

The current code carries **three chunk-selection algorithms and two retrieval algorithms** committed side-by-side because none was clearly right. Almost all of that complexity dissolves when:

- **Brave/Tavily already return relevance-ranked, snippet-sized results.** No local re-ranking needed for the 80% case.
- **The LLM is doing the comparison anyway.** Feeding it the original claim + the search-result snippet directly is cheaper than the current "fetch full page → extract → chunk → embed → retrieve top-k chunks → compare" pipeline, and produces a better answer because the LLM sees the full snippet in context.
- **For deep comparison** (when the user clicks "open this source"), `Defuddle` extracts the full article and the LLM compares against it directly. Needs no embeddings if context windows are 200K tokens.

If embeddings *are* needed (e.g., for very long sources), `Xenova/all-MiniLM-L6-v2` via transformers.js in a web worker handles it in-browser with no Python.

### Highlighting: native browser APIs

Replaces: the manual `<span>` injection + `originalElementStyles` tracking in `bookmarklet.js`.

The [CSS Custom Highlight API](https://developer.mozilla.org/en-US/docs/Web/API/CSS_Custom_Highlight_API) (`Highlight`, `CSS.highlights`) lets the extension highlight passages **without modifying the DOM**. This is the right primitive — it's what Firefox Reader View's annotations and Chrome's "find on page" use internally. Available across all major browsers as of 2024. The current code's "store original styles, inject spans, restore on close" dance disappears.

### Storage & caching

- `chrome.storage.sync` — user settings (custom URLs, preferred LLM tier, API keys for Tier 2). Auto-syncs across devices.
- `chrome.storage.session` — per-session state (current page's extracted claims).
- IndexedDB — claim-extraction cache keyed by URL hash, so re-clicking the bookmarklet on the same page is instant.

## What the user experience looks like

1. User installs the extension from Chrome Web Store. (One click.)
2. User browses normally. The extension icon sits in the toolbar.
3. On any page, user clicks the icon → the side panel opens persistently on the right.
4. The side panel shows: detected language, ~3–5 key claims (streamed as they arrive), and for each claim a "verify" button.
5. User clicks "verify" on a claim:
   - First: query Google Fact Check Tools API for an existing fact-check. If found, show it.
   - Then: Brave Search returns 5 candidate sources (general + custom-domain filtered).
   - For each, the LLM produces a one-sentence "agrees / disagrees / unrelated" verdict + the specific contradicting passage.
6. Clicking a passage scrolls + highlights it on the original page (CSS Custom Highlight API).
7. All of step 5 runs against Gemini Nano on-device by default. No network calls except to Brave and Fact Check.

## Concrete dependency reduction

| Current | Replacement | Net change |
|---|---|---|
| Docker + Ollama + GPU toolkit | — | removed |
| FastAPI, uvicorn, jinja2, aiohttp | WXT service worker | removed (Python stack) |
| trafilatura, lxml, lxml_html_clean, html2text, markdown-it-py, mdit-plain | Defuddle | 6 packages → 1 |
| spacy, stanza, RapidFuzz | Chrome `LanguageDetector` + `Translator` | 3 packages → 0 |
| torch, torchvision, transformers, sentence-transformers, accelerate, optree, networkx, scikit-learn | Chrome `LanguageModel` (or Tier 2/3 fallback) | 8 packages → 0 |
| ollama Python client | Chrome `LanguageModel` | removed |
| googlesearch-python, google-api-python-client | `fetch()` to Brave/Tavily | 2 packages → 0 |
| playwright | content script DOM access | removed |
| `bookmarklet.js` (~80 KB, untyped) | Typed React side panel | refactor |
| `/proxy` CSP workaround | content scripts have access by default | removed |

The reimplementation is roughly **one TypeScript codebase, ~500 KB of shipped extension, no server, no Docker, no Python, no GPU drivers**.

## What this *gives up*

Honest trade-offs, not glossed over:

- **Chrome-first by default.** Firefox/Safari users get Tier 2 (cloud LLM with their own API key) or Tier 3 (transformers.js). The on-device "free, private, zero-config" path is Chrome-only because Gemini Nano is. This is the right trade because Chromium-family browsers (Chrome + Edge + Brave + Arc + Opera) cover ~75% of desktop share.
- **Mobile is not solved.** Chrome Built-in AI doesn't ship on Android or iOS Chrome. Mobile probably wants a native app, not an extension. Out of scope for v1.
- **No more "fully air-gapped local LLM" by default.** Tier 1 runs on-device but is provided by Google. Users who specifically need *fully* third-party-free can opt into Tier 3 (transformers.js / WebLLM) — same guarantee as the current Ollama setup, without the install pain.
- **Lose pluggable algorithms.** The three chunkers and two retrievers committed today disappear in favor of "let the LLM do it." If a future use case actually needs custom retrieval, transformers.js makes it easy to add back — but in one place, not five.

## Recommended initial milestones

1. **Skeleton extension with side panel + Defuddle extraction.** No LLM yet. Click → see extracted markdown of the page in the panel. Validates the install-and-open path.
2. **Chrome Built-in AI: claim extraction.** Wire the `Summarizer` + `LanguageModel` APIs to produce the same 3–5-claim output the current backend produces. Compare quality against the `tulu3` baseline on a fixed set of 20 articles before committing to it as the default.
3. **Brave Search + Fact Check Tools.** Add the verification flow. Streaming results into the side panel.
4. **Tier 2 fallback (Anthropic API).** Settings page for the API key. Same prompts, different transport.
5. **CSS Custom Highlight API for in-page highlighting.** Replace the current span-injection approach.
6. **Cross-browser polish.** Firefox `sidebar_action` shim, edge-cases on sites with strict CSP, Edge Add-ons listing.
7. **Tier 3 (transformers.js / WebLLM) opt-in.** Last, because the smallest user segment.

## Sources

- [Chrome Built-in AI APIs](https://developer.chrome.com/docs/ai/built-in-apis)
- [Chrome Prompt API](https://developer.chrome.com/docs/ai/prompt-api)
- [Chrome Summarizer API](https://developer.chrome.com/docs/ai/summarizer-api)
- [chrome.sidePanel API reference](https://developer.chrome.com/docs/extensions/reference/api/sidePanel)
- [Firefox sidebar_action manifest key](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/manifest.json/action)
- [Firefox Manifest V3 migration guide](https://extensionworkshop.com/documentation/develop/manifest-v3-migration-guide/)
- [WXT — Next-gen Web Extension Framework](https://wxt.dev/)
- [WXT vs Plasmo vs CRXJS comparison (2026)](https://trybuildpilot.com/649-wxt-vs-plasmo-vs-crxjs-2026)
- [Defuddle on GitHub](https://github.com/kepano/defuddle)
- [Defuddle vs Readability writeup](https://biggo.com/news/202505240122_Defuddle_Web_Content_Extractor)
- [Mozilla Readability](https://github.com/mozilla/readability)
- [WebLLM](https://github.com/mlc-ai/web-llm)
- [transformers.js](https://github.com/huggingface/transformers.js)
- [WebGPU browser inference cost analysis (2026)](https://www.buildmvpfast.com/blog/webgpu-browser-ai-inference-cost-savings-2026)
- [Anthropic Claude API pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- [Claude Haiku 4.5 announcement](https://www.anthropic.com/news/claude-haiku-4-5)
- [Brave Search API](https://brave.com/search/api/)
- [Tavily Search API](https://tavily.com)
- [Exa neural search](https://exa.ai)
- [Agentic search benchmark of 8 APIs (2026)](https://aimultiple.com/agentic-search)
- [Google Fact Check Tools API](https://developers.google.com/fact-check/tools/api)
- [ClaimReview schema (schema.org)](https://schema.org/ClaimReview)
- [CSS Custom Highlight API](https://developer.mozilla.org/en-US/docs/Web/API/CSS_Custom_Highlight_API)
