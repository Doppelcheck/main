/**
 * `stripHtml` is the service worker's only sanitiser for third-party pages fetched
 * during claim verification, and its output goes straight into the comparison prompt
 * as "the source text" and back to the user as verbatim evidence. Both properties
 * pinned here were broken:
 *
 *   - entity decoding ran `&amp;` FIRST, so a double-encoded sequence was decoded
 *     twice and markup reappeared after every tag-stripping pass had finished —
 *     `&amp;lt;script&amp;gt;` came out as the literal string `<script>`;
 *   - numeric entities used `String.fromCharCode`, which truncates anything above
 *     U+FFFF, so `&#128512;` decoded to U+F600 (a Private Use Area glyph) instead
 *     of the emoji.
 */

import { describe, expect, it } from "vitest";
import { stripHtml } from "@/lib/fetch-source";

describe("stripHtml entity decoding", () => {
  it("does not resurrect markup from a double-encoded sequence", () => {
    // The regression: decoding `&amp;` before `&lt;`/`&gt;` turns this into `<script>`,
    // smuggling tag-looking text past the tag stripper and into the LLM prompt.
    expect(stripHtml("&amp;lt;script&amp;gt;")).toBe("&lt;script&gt;");
  });

  it("decodes a singly-encoded entity exactly once", () => {
    expect(stripHtml("<p>a &lt;b&gt; c</p>")).toBe("a <b> c");
  });

  it("decodes an ampersand entity to a bare ampersand", () => {
    expect(stripHtml("<p>Tom &amp; Jerry</p>")).toBe("Tom & Jerry");
  });

  it("keeps an astral-plane decimal entity intact", () => {
    // String.fromCharCode(128512) silently yields U+F600; fromCodePoint is required.
    expect(stripHtml("&#128512;")).toBe("\u{1F600}");
  });

  it("keeps an astral-plane hex entity intact", () => {
    expect(stripHtml("&#x1F600;")).toBe("\u{1F600}");
  });

  it("still decodes basic-plane numeric entities", () => {
    expect(stripHtml("&#65;&#x42;")).toBe("AB");
  });

  it("removes script bodies rather than exposing their text", () => {
    expect(stripHtml("<p>before</p><script>alert('x')</script><p>after</p>")).toBe(
      "before after",
    );
  });

  it("collapses whitespace left behind by stripped tags", () => {
    expect(stripHtml("<div>\n  a\n\n  b\n</div>")).toBe("a b");
  });
});
