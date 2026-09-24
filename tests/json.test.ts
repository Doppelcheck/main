import { describe, expect, it } from "vitest";
import { extractJSON, parseJSON, readArrayElements } from "@/lib/json";

describe("extractJSON", () => {
  it("returns a bare object unchanged", () => {
    expect(extractJSON('{"a":1}')).toBe('{"a":1}');
  });

  it("unwraps a ```json fenced block", () => {
    expect(extractJSON('Here you go:\n```json\n{"a":1}\n```\n')).toBe('{"a":1}');
  });

  it("unwraps an unlabelled fenced block", () => {
    expect(extractJSON('```\n[1,2]\n```')).toBe("[1,2]");
  });

  it("skips prose before and after the JSON", () => {
    expect(extractJSON('Sure! {"a":1} Hope that helps.')).toBe('{"a":1}');
  });

  it("keeps nested structures whole", () => {
    const blob = '{"a":{"b":[1,{"c":2}]}}';
    expect(extractJSON(`noise ${blob} noise`)).toBe(blob);
  });

  it("is not fooled by braces inside strings", () => {
    const blob = '{"a":"} not the end {"}';
    expect(extractJSON(blob)).toBe(blob);
  });

  it("is not fooled by an escaped quote inside a string", () => {
    const blob = '{"a":"say \\" }"}';
    expect(extractJSON(blob)).toBe(blob);
  });

  it("strips a Qwen <think> block before scanning", () => {
    const text = '<think>maybe {"wrong":1} is right</think>{"right":1}';
    expect(extractJSON(text)).toBe('{"right":1}');
  });

  it("strips a multi-line <think> block case-insensitively", () => {
    const text = '<THINK>\nline one {\nline two\n</THINK>\n{"ok":true}';
    expect(extractJSON(text)).toBe('{"ok":true}');
  });

  it("returns undefined when the value never closes", () => {
    expect(extractJSON('{"a":1')).toBeUndefined();
  });

  it("returns undefined when there is no JSON at all", () => {
    expect(extractJSON("I cannot help with that.")).toBeUndefined();
  });
});

describe("parseJSON", () => {
  it("parses an extracted object", () => {
    expect(parseJSON<{ a: number }>('```json\n{"a":1}\n```')).toEqual({ a: 1 });
  });

  it("returns undefined for a balanced but invalid blob", () => {
    // Balanced braces, so extractJSON yields it, but JSON.parse rejects it.
    expect(parseJSON("{a:1}")).toBeUndefined();
  });

  it("returns undefined when nothing was extracted", () => {
    expect(parseJSON("no json here")).toBeUndefined();
  });
});

describe("readArrayElements", () => {
  const collect = (s: string) => [...readArrayElements(s)];

  it("yields each complete object element", () => {
    expect(collect('[{"a":1},{"b":2}]')).toEqual(['{"a":1}', '{"b":2}']);
  });

  it("yields only the elements that have arrived so far", () => {
    expect(collect('[{"a":1},{"b":')).toEqual(['{"a":1}']);
  });

  it("yields nothing before the first element closes", () => {
    expect(collect('[{"a":')).toEqual([]);
  });

  it("yields nothing when no array has started", () => {
    expect(collect("thinking about it")).toEqual([]);
  });

  it("keeps a nested object inside an element whole", () => {
    expect(collect('[{"a":{"b":1}},{"c":2}]')).toEqual([
      '{"a":{"b":1}}',
      '{"c":2}',
    ]);
  });

  it("is not fooled by a bracket inside an element's string", () => {
    expect(collect('[{"a":"]["},{"b":2}]')).toEqual(['{"a":"]["}', '{"b":2}']);
  });

  it("stops at the end of the array and ignores trailing prose", () => {
    expect(collect('[{"a":1}] and that is all')).toEqual(['{"a":1}']);
  });

  it("ignores prose before the array", () => {
    expect(collect('Here are the claims: [{"a":1}]')).toEqual(['{"a":1}']);
  });

  it("strips a <think> block so its braces are not mistaken for elements", () => {
    const text = '<think>[{"draft":1}]</think>[{"final":1}]';
    expect(collect(text)).toEqual(['{"final":1}']);
  });
});
