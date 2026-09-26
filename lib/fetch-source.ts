/**
 * Fetch a candidate source URL from the service worker and return plain text.
 *
 * MV3 service workers don't have DOMParser, so for v1 we use a cheap regex
 * strip rather than running Defuddle here. The LLM is doing the actual
 * comparison, so a slightly noisier text input is acceptable. Upgrade path:
 * add an offscreen document running Defuddle for byte-perfect extraction.
 */

const MAX_BYTES = 400_000;
const MAX_TEXT = 14_000;

export async function fetchSourceText(
  url: string,
): Promise<{ title: string; text: string } | undefined> {
  let res: Response;
  try {
    res = await fetch(url, {
      headers: {
        accept:
          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      },
      redirect: "follow",
    });
  } catch {
    return undefined;
  }
  if (!res.ok) return undefined;
  const ctype = res.headers.get("content-type") ?? "";
  if (!ctype.includes("html") && !ctype.includes("text")) return undefined;

  const reader = res.body?.getReader();
  if (!reader) return undefined;
  const decoder = new TextDecoder("utf-8", { fatal: false });
  let html = "";
  let bytes = 0;
  while (bytes < MAX_BYTES) {
    const { value, done } = await reader.read();
    if (done) break;
    bytes += value.byteLength;
    html += decoder.decode(value, { stream: true });
  }
  reader.cancel().catch(() => undefined);
  html += decoder.decode();

  return {
    title: extractTitle(html) ?? new URL(url).hostname,
    text: stripHtml(html).slice(0, MAX_TEXT),
  };
}

function extractTitle(html: string): string | undefined {
  const m = /<title[^>]*>([\s\S]*?)<\/title>/i.exec(html);
  return m?.[1]?.replace(/\s+/g, " ").trim();
}

export function stripHtml(html: string): string {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<noscript[\s\S]*?<\/noscript>/gi, " ")
    .replace(/<header[\s\S]*?<\/header>/gi, " ")
    .replace(/<nav[\s\S]*?<\/nav>/gi, " ")
    .replace(/<footer[\s\S]*?<\/footer>/gi, " ")
    .replace(/<aside[\s\S]*?<\/aside>/gi, " ")
    .replace(/<form[\s\S]*?<\/form>/gi, " ")
    .replace(/<svg[\s\S]*?<\/svg>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&quot;/gi, '"')
    .replace(/&#(\d+);/g, (_m, n) => String.fromCodePoint(Number(n)))
    .replace(/&#x([\da-f]+);/gi, (_m, n) => String.fromCodePoint(parseInt(n, 16)))
    // `&amp;` decodes LAST, after every other entity form. Decoding it first made
    // this chain decode twice: `&amp;lt;script&amp;gt;` became `&lt;script&gt;`
    // and then `<script>` — markup reappearing *after* every tag-stripping pass
    // had already run, straight into the comparison prompt.
    .replace(/&amp;/gi, "&")
    .replace(/\s+/g, " ")
    .trim();
}
