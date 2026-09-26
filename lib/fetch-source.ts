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

export function extractTitle(html: string): string | undefined {
  const m = /<title[^>]*>([\s\S]*?)<\/title>/i.exec(html);
  if (!m?.[1]) return undefined;
  // The title is returned in the same object as the fully decoded body text and is
  // shown as the source's name, so it goes through the SAME decoder — it used to
  // collapse whitespace only, putting raw `&amp;` in the UI beside decoded prose.
  return decodeEntities(m[1]).replace(/\s+/g, " ").trim() || undefined;
}

/**
 * Decode the HTML entity forms these fetched pages actually use.
 *
 * ORDER IS LOAD-BEARING: `&amp;` is decoded LAST, after every other form. Decoding
 * it first made the chain decode twice — `&amp;lt;script&amp;gt;` became
 * `&lt;script&gt;` and then `<script>`, markup reappearing *after* every
 * tag-stripping pass had already run, straight into the comparison prompt.
 *
 * `String.fromCodePoint`, never `fromCharCode`: the latter truncates above U+FFFF,
 * so `&#128512;` decoded to U+F600 (a Private Use Area glyph) instead of the emoji,
 * silently corrupting text presented to the user as a verbatim quote.
 *
 * One function, because two copies of this chain drifted apart once already.
 */
function decodeEntities(text: string): string {
  return text
    .replace(/&nbsp;/gi, " ")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&quot;/gi, '"')
    .replace(/&#(\d+);/g, (_m, n) => String.fromCodePoint(Number(n)))
    .replace(/&#x([\da-f]+);/gi, (_m, n) => String.fromCodePoint(parseInt(n, 16)))
    .replace(/&amp;/gi, "&");
}

export function stripHtml(html: string): string {
  return decodeEntities(
    html
      .replace(/<script[\s\S]*?<\/script>/gi, " ")
      .replace(/<style[\s\S]*?<\/style>/gi, " ")
      .replace(/<noscript[\s\S]*?<\/noscript>/gi, " ")
      .replace(/<header[\s\S]*?<\/header>/gi, " ")
      .replace(/<nav[\s\S]*?<\/nav>/gi, " ")
      .replace(/<footer[\s\S]*?<\/footer>/gi, " ")
      .replace(/<aside[\s\S]*?<\/aside>/gi, " ")
      .replace(/<form[\s\S]*?<\/form>/gi, " ")
      .replace(/<svg[\s\S]*?<\/svg>/gi, " ")
      .replace(/<[^>]+>/g, " "),
  )
    .replace(/\s+/g, " ")
    .trim();
}
