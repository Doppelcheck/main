/**
 * Brave Search API client. https://brave.com/search/api/
 * Pricing: $5/1k queries, ~1k free credits/month for new users. Lowest
 * latency in the AIMultiple agentic-search benchmark.
 */

import type { SearchHit } from "@/types";

const ENDPOINT = "https://api.search.brave.com/res/v1/web/search";

interface BraveResponse {
  web?: {
    results?: {
      url: string;
      title: string;
      description: string;
      meta_url?: { hostname?: string };
    }[];
  };
}

export interface BraveSearchOpts {
  apiKey: string;
  query: string;
  count?: number;
  /** Restrict to a specific domain via `site:` prefix. */
  site?: string;
  /** UI/page-level locale, e.g. "de" or "en". Affects ranking. */
  language?: string;
}

export async function braveSearch({
  apiKey,
  query,
  count = 5,
  site,
  language,
}: BraveSearchOpts): Promise<SearchHit[]> {
  const q = site ? `site:${site} ${query}` : query;
  const url = new URL(ENDPOINT);
  url.searchParams.set("q", q);
  url.searchParams.set("count", String(Math.min(20, Math.max(1, count))));
  if (language) url.searchParams.set("search_lang", language);

  const res = await fetch(url, {
    headers: {
      accept: "application/json",
      "x-subscription-token": apiKey,
    },
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Brave Search ${res.status}: ${detail.slice(0, 200)}`);
  }
  const data = (await res.json()) as BraveResponse;
  const results = data.web?.results ?? [];
  return results.map((r) => {
    const domain = r.meta_url?.hostname ?? safeHost(r.url);
    return {
      url: r.url,
      title: stripHtml(r.title),
      snippet: stripHtml(r.description),
      domain,
      customDomain: !!site,
    } satisfies SearchHit;
  });
}

function safeHost(u: string): string {
  try {
    return new URL(u).hostname;
  } catch {
    return "";
  }
}

function stripHtml(s: string): string {
  return s.replace(/<[^>]+>/g, "").trim();
}
