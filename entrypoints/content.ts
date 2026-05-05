import { defineContentScript } from "wxt/sandbox";
import type { ContentRequest } from "@/types";
import { extractFromDocument } from "@/lib/extract";
import { clearHighlights, highlightRanges } from "@/lib/extract/highlight";

export default defineContentScript({
  matches: ["<all_urls>"],
  runAt: "document_idle",
  main() {
    chrome.runtime.onMessage.addListener((msg: ContentRequest, _sender, sendResponse) => {
      switch (msg.kind) {
        case "extract": {
          try {
            const { page, debug } = extractFromDocument();
            sendResponse({ ok: true, page, debug });
          } catch (err) {
            sendResponse({ ok: false, error: (err as Error).message });
          }
          return true;
        }
        case "highlight": {
          const result = highlightRanges(msg.ranges);
          sendResponse({ ok: result.applied > 0, ...result });
          return true;
        }
        case "clear-highlights": {
          clearHighlights();
          sendResponse({ ok: true });
          return true;
        }
      }
      return false;
    });
  },
});
