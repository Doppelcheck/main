/**
 * CSS Custom Highlight API wrapper. Available in all major browsers since
 * 2024. Highlights ranges *without modifying the DOM* — replaces the
 * legacy bookmarklet's span-injection / style-restoration dance.
 *
 * Two non-obvious things:
 *
 * 1. The `::highlight(name)` selector must be defined in the *target
 *    document's* stylesheet — the extension's own CSS doesn't reach
 *    pages we content-script into. We inject a `<style>` tag the first
 *    time we apply highlights.
 *
 * 2. Lookup is fuzzy: we walk text nodes once into a flat string with
 *    offset metadata so we can match across element boundaries (text
 *    broken by inline `<a>`, `<em>`, etc). Exact match first, then a
 *    whitespace-collapsed match, then longest-common-prefix fallback.
 */

import type { HighlightType } from "@/types";

const REGISTRIES: Record<HighlightType, string> = {
  claim: "doppelcheck-claim",
  "evidence-agree": "doppelcheck-evidence-agree",
  "evidence-disagree": "doppelcheck-evidence-disagree",
};

const HIGHLIGHT_STYLE_ID = "doppelcheck-highlight-styles";
const HIGHLIGHT_CSS = `
::highlight(${REGISTRIES.claim}) {
  background-color: rgba(255, 213, 0, 0.42);
  color: inherit;
}
::highlight(${REGISTRIES["evidence-agree"]}) {
  background-color: rgba(31, 122, 58, 0.28);
}
::highlight(${REGISTRIES["evidence-disagree"]}) {
  background-color: rgba(179, 38, 30, 0.28);
}
`;

function ensureStylesheet() {
  if (document.getElementById(HIGHLIGHT_STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = HIGHLIGHT_STYLE_ID;
  style.textContent = HIGHLIGHT_CSS;
  // Append to <head> if it exists, otherwise <html>.
  (document.head ?? document.documentElement).appendChild(style);
}

const highlights = new Map<HighlightType, Highlight>();

function ensureHighlight(type: HighlightType): Highlight {
  let h = highlights.get(type);
  if (!h) {
    h = new Highlight();
    highlights.set(type, h);
    CSS.highlights?.set(REGISTRIES[type], h);
  }
  return h;
}

export function clearHighlights() {
  for (const [type, h] of highlights) {
    h.clear();
    CSS.highlights?.delete(REGISTRIES[type]);
  }
  highlights.clear();
}

export function highlightRanges(
  targets: { text: string; type: HighlightType }[],
): { applied: number; missed: number } {
  if (typeof CSS === "undefined" || !("highlights" in CSS)) {
    // Browsers without the Custom Highlight API: silently no-op.
    return { applied: 0, missed: targets.length };
  }
  ensureStylesheet();
  clearHighlights();
  let firstRange: Range | undefined;
  let applied = 0;
  let missed = 0;
  for (const target of targets) {
    const range = findRange(target.text);
    if (!range) {
      missed++;
      continue;
    }
    ensureHighlight(target.type).add(range);
    applied++;
    if (!firstRange) firstRange = range;
  }
  if (firstRange) {
    const node =
      firstRange.startContainer.nodeType === Node.ELEMENT_NODE
        ? (firstRange.startContainer as Element)
        : firstRange.startContainer.parentElement;
    node?.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  return { applied, missed };
}

function findRange(needle: string): Range | undefined {
  const target = needle.trim();
  if (target.length < 8) return undefined;
  // Walk text nodes, building a single concatenated string with offsets so
  // we can match across element boundaries (e.g. text broken by <a>).
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
    acceptNode(n) {
      if (!n.parentElement) return NodeFilter.FILTER_REJECT;
      const tag = n.parentElement.tagName;
      if (tag === "SCRIPT" || tag === "STYLE" || tag === "NOSCRIPT") {
        return NodeFilter.FILTER_REJECT;
      }
      return NodeFilter.FILTER_ACCEPT;
    },
  });

  let combined = "";
  const positions: { node: Text; start: number }[] = [];
  let n: Node | null;
  while ((n = walker.nextNode())) {
    const text = (n as Text).data;
    positions.push({ node: n as Text, start: combined.length });
    combined += text;
  }

  const idx = locate(combined, target);
  if (idx === -1) return undefined;

  const range = document.createRange();
  const startInfo = nodeAt(positions, idx);
  const endInfo = nodeAt(positions, idx + target.length);
  if (!startInfo || !endInfo) return undefined;
  range.setStart(startInfo.node, idx - startInfo.start);
  range.setEnd(endInfo.node, idx + target.length - endInfo.start);
  return range;
}

function nodeAt(
  positions: { node: Text; start: number }[],
  offset: number,
): { node: Text; start: number } | undefined {
  // Linear is fine — pages rarely have so many text nodes that this matters.
  let last: { node: Text; start: number } | undefined;
  for (const p of positions) {
    if (p.start > offset) break;
    last = p;
  }
  if (!last) return undefined;
  if (offset > last.start + last.node.data.length) return undefined;
  return last;
}

/**
 * Locate `needle` in `haystack`:
 *   1. exact substring
 *   2. whitespace-collapsed substring
 *   3. fuzzy: longest run of needle that appears verbatim
 */
function locate(haystack: string, needle: string): number {
  const direct = haystack.indexOf(needle);
  if (direct !== -1) return direct;

  const collapsed = haystack.replace(/\s+/g, " ");
  const collapsedNeedle = needle.replace(/\s+/g, " ");
  const altIdx = collapsed.indexOf(collapsedNeedle);
  if (altIdx !== -1) {
    // Map collapsed offset back to original. Approximate — good enough
    // to scroll into view; the highlight may be slightly off.
    return mapCollapsedToOriginal(haystack, altIdx);
  }

  // Last resort: shrink needle from the right until we find a match.
  for (let len = needle.length - 1; len >= 24; len -= 8) {
    const idx = haystack.indexOf(needle.slice(0, len));
    if (idx !== -1) return idx;
  }
  return -1;
}

function mapCollapsedToOriginal(original: string, collapsedIdx: number): number {
  let collapsed = 0;
  let prevSpace = false;
  for (let i = 0; i < original.length; i++) {
    if (collapsed === collapsedIdx) return i;
    const ch = original[i]!;
    const isSpace = /\s/.test(ch);
    if (isSpace) {
      if (!prevSpace) collapsed++;
      prevSpace = true;
    } else {
      collapsed++;
      prevSpace = false;
    }
  }
  return -1;
}
