/**
 * Page extraction lives in the *content script* (where it has DOM access).
 * Replaces: trafilatura + html2text + lxml + the multi-pass cleaning logic
 * in the legacy server/services/extractor.py.
 *
 * Defuddle's heuristics work well for the article body itself, but on news
 * sites with related-article rails, "Mehr zum Thema" sections, and
 * cross-promotion teaser blocks, it tends to slurp those into the output —
 * which then leaks into LLM claim extraction (the model picks up "claims"
 * that are actually about unrelated stories on the same page).
 *
 * The fix here is to do *DOM scoping* before Defuddle ever sees the page:
 *   1. Find the canonical main-article container using strong semantic
 *      signals (schema.org Article markup, single <article>, <main>).
 *   2. Clone the document and rebuild its body to contain only that
 *      subtree.
 *   3. Strip aside/nav/footer/related-content patterns from the clone.
 *   4. Then run Defuddle on the cleaned clone.
 *
 * Defuddle's constructor only accepts a `Document`, hence the clone +
 * body-rebuild dance rather than passing a subtree directly.
 */

import Defuddle from "defuddle";
import type { ExtractedPage } from "@/types";

export interface ExtractDebug {
  strategy:
    | "schema.org-Article"
    | "single-article-tag"
    | "best-article-tag"
    | "main-tag"
    | "role-main"
    | "whole-document";
  noiseRemoved: number;
}

const NOISE_SELECTORS = [
  // Structural
  "nav",
  "aside",
  "footer",
  'header[role="banner"]',
  '[role="navigation"]',
  '[role="complementary"]',
  '[role="search"]',
  // Common related/teaser patterns (case-insensitive class/id contains)
  '[class*="related" i]',
  '[class*="teaser" i]',
  '[class*="more-from" i]',
  '[class*="recommend" i]',
  '[class*="trending" i]',
  '[class*="newsletter" i]',
  '[class*="subscribe" i]',
  '[class*="paywall" i]',
  '[class*="comments" i]',
  '[class*="social" i]',
  '[class*="share" i]',
  '[id*="related" i]',
  '[id*="recommend" i]',
  '[id*="comments" i]',
  '[aria-label*="related" i]',
  '[aria-label*="more" i]',
  // Cookie banners and overlays
  '[class*="cookie" i]',
  '[class*="consent" i]',
  '[class*="banner" i]:not([role])',
];

export function extractFromDocument(doc: Document = document): {
  page: ExtractedPage;
  debug: ExtractDebug;
} {
  const url = doc.location?.href ?? "";
  const { scoped, strategy, noiseRemoved } = scopeToArticle(doc);

  const result = new Defuddle(scoped, {
    markdown: true,
    url,
    removeExactSelectors: true,
    removePartialSelectors: true,
  }).parse();

  const markdown = (result.content ?? "").trim();
  const text = markdownToPlainText(markdown);

  return {
    page: {
      url,
      title: result.title ?? doc.title ?? "",
      author: result.author || undefined,
      published: result.published || undefined,
      language: doc.documentElement.lang || undefined,
      wordCount: text ? text.split(/\s+/).filter(Boolean).length : 0,
      markdown,
      text,
    },
    debug: { strategy, noiseRemoved },
  };
}

/**
 * Returns a Document that contains only the page's main article body,
 * with related-article / teaser / nav / cookie patterns stripped.
 */
function scopeToArticle(doc: Document): {
  scoped: Document;
  strategy: ExtractDebug["strategy"];
  noiseRemoved: number;
} {
  const { container, strategy } = findMainContainer(doc);
  // Clone the entire document to keep `<head>` (Defuddle reads metadata
  // and schema.org JSON-LD from there).
  const clone = doc.cloneNode(true) as Document;

  if (container && strategy !== "whole-document") {
    // Find the corresponding element in the clone using its element path.
    // Cloning preserves structure, so the path resolves identically.
    const cloned = mirrorElement(doc, container, clone);
    if (cloned && clone.body) {
      clone.body.replaceChildren(cloned);
    }
  }

  const noiseRemoved = stripNoise(clone);
  return { scoped: clone, strategy, noiseRemoved };
}

function findMainContainer(doc: Document): {
  container: Element | null;
  strategy: ExtractDebug["strategy"];
} {
  // 1. Explicit schema.org Article markup — the strongest signal a
  // publisher can give us.
  const schemaArticle = doc.querySelector(
    '[itemtype$="/NewsArticle"],[itemtype$="/Article"],[itemtype$="/BlogPosting"],[itemtype$="/ReportageNewsArticle"]',
  );
  if (schemaArticle && hasSubstantialText(schemaArticle)) {
    return { container: schemaArticle, strategy: "schema.org-Article" };
  }

  // 2. <article> elements.
  const articles = Array.from(doc.querySelectorAll("article")).filter(
    hasSubstantialText,
  );
  if (articles.length === 1) {
    return { container: articles[0]!, strategy: "single-article-tag" };
  }
  if (articles.length > 1) {
    // Multiple articles on a page = front-page-style layout. Pick the
    // densest one (most text relative to link count) as the focal article.
    return {
      container: articles.reduce((best, cur) =>
        contentScore(cur) > contentScore(best) ? cur : best,
      ),
      strategy: "best-article-tag",
    };
  }

  // 3. <main>
  const main = doc.querySelector("main");
  if (main && hasSubstantialText(main)) {
    return { container: main, strategy: "main-tag" };
  }

  // 4. role="main"
  const roleMain = doc.querySelector('[role="main"]');
  if (roleMain && hasSubstantialText(roleMain)) {
    return { container: roleMain, strategy: "role-main" };
  }

  return { container: null, strategy: "whole-document" };
}

function hasSubstantialText(el: Element): boolean {
  // Filter out skinny <article> tags used as teaser cards. A real
  // article body typically has at least a few hundred characters of text.
  return (el.textContent?.trim().length ?? 0) > 400;
}

/** Higher = more like an article body, less like a link list. */
function contentScore(el: Element): number {
  const text = el.textContent?.trim().length ?? 0;
  const links = el.querySelectorAll("a").length;
  // Each link costs ~50 text chars worth of penalty: link-rail blocks and
  // teaser lists have many short links, real article bodies have few.
  return text - links * 50;
}

/**
 * Given an element in `srcDoc`, return the corresponding element in the
 * cloned `dstDoc`. Walks parent chain to build a child-index path, then
 * follows it down the clone.
 */
function mirrorElement(
  srcDoc: Document,
  el: Element,
  dstDoc: Document,
): Element | null {
  const path: number[] = [];
  let cur: Node | null = el;
  while (cur && cur !== srcDoc) {
    const parent: ParentNode | null = cur.parentNode;
    if (!parent) return null;
    const idx = Array.prototype.indexOf.call(parent.childNodes, cur);
    if (idx < 0) return null;
    path.unshift(idx);
    cur = parent as Node;
  }
  let node: Node = dstDoc;
  for (const idx of path) {
    const child = node.childNodes[idx];
    if (!child) return null;
    node = child;
  }
  return node instanceof Element ? node : null;
}

function stripNoise(doc: Document): number {
  let removed = 0;
  for (const sel of NOISE_SELECTORS) {
    let nodes: NodeListOf<Element>;
    try {
      nodes = doc.body.querySelectorAll(sel);
    } catch {
      // Older Chromium versions may not support some attribute selectors.
      continue;
    }
    nodes.forEach((el) => {
      el.remove();
      removed++;
    });
  }
  return removed;
}

/**
 * Cheap markdown → plain text. Defuddle outputs Markdown, but on some
 * pages it leaves bare HTML tags inline (article wrappers, inline
 * `<span>`s for inline styling, etc.). We strip both Markdown and
 * leftover HTML so downstream — claim extraction, NLI, sentence
 * splitting — never sees `<article><p>` showing up as the start of a
 * "claim".
 *
 * Headings are dropped entirely (line + content), not merely de-marked.
 * They're not factual assertions and, because most lack terminal
 * punctuation, leaving them in the text fools `Intl.Segmenter` into
 * merging them with the next paragraph's first sentence.
 */
function markdownToPlainText(md: string): string {
  return md
    .replace(/```[\s\S]*?```/g, " ") // fenced code blocks
    .replace(/`[^`]*`/g, " ") // inline code
    .replace(/!\[[^\]]*]\([^)]*\)/g, " ") // images
    .replace(/\[([^\]]*)]\([^)]*\)/g, "$1") // links → label only
    .replace(/<!--[\s\S]*?-->/g, " ") // HTML comments
    .replace(/<[^>]+>/g, " ") // any remaining HTML tags
    .replace(/^#{1,6}\s+.*$/gm, "") // ATX headings: drop the whole line
    .replace(/^[-=]{3,}\s*$/gm, "") // setext heading underlines
    .replace(/^>\s+/gm, "") // blockquote markers
    .replace(/[*_~]/g, "") // emphasis markers
    .replace(/\s+\n/g, "\n")
    .replace(/\n{2,}/g, "\n\n")
    .replace(/[ \t]{2,}/g, " ")
    .trim();
}
