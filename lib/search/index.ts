import type { SearchHit, Settings } from "@/types";
import { braveSearch } from "./brave";

export { braveSearch } from "./brave";
export { factCheckLookup } from "./factcheck";

/**
 * Run a general search plus one site-restricted search per custom URL,
 * dedupe by hostname+path, drop the source page itself.
 */
export async function searchAll(
  query: string,
  pageUrl: string,
  settings: Settings,
  language?: string,
): Promise<SearchHit[]> {
  if (!settings.braveApiKey) {
    throw new Error(
      "Brave Search API key is not configured. Open the options page.",
    );
  }
  const seen = new Set<string>();
  try {
    seen.add(canonical(pageUrl));
  } catch {
    /* ignore */
  }

  const general = braveSearch({
    apiKey: settings.braveApiKey,
    query,
    count: 5,
    language,
  }).catch(() => [] as SearchHit[]);

  const siteSpecific = settings.customUrls.map((u) => {
    let domain: string;
    try {
      domain = new URL(u).hostname;
    } catch {
      return Promise.resolve([] as SearchHit[]);
    }
    return braveSearch({
      apiKey: settings.braveApiKey,
      query,
      count: 3,
      site: domain,
      language,
    }).catch(() => [] as SearchHit[]);
  });

  const all = (await Promise.all([general, ...siteSpecific])).flat();
  const out: SearchHit[] = [];
  for (const hit of all) {
    const key = canonical(hit.url);
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(hit);
  }
  return out;
}

function canonical(u: string): string {
  try {
    const url = new URL(u);
    return `${url.hostname}${url.pathname}`.replace(/\/+$/, "");
  } catch {
    return u;
  }
}
