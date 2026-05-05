/**
 * Google Fact Check Tools API. Free with API key.
 * https://developers.google.com/fact-check/tools/api
 *
 * Surfaces existing fact-checks tagged with schema.org/ClaimReview from
 * publishers like Snopes, PolitiFact, Correctiv, dpa-Faktencheck, etc.
 *
 * This is the *cheap* answer to "is this claim already known false?" —
 * we hit it before the expensive search-and-compare loop.
 */

import type { FactCheckHit } from "@/types";

const ENDPOINT = "https://factchecktools.googleapis.com/v1alpha1/claims:search";

interface FactCheckResponse {
  claims?: {
    text?: string;
    claimant?: string;
    claimDate?: string;
    claimReview?: {
      publisher?: { name?: string; site?: string };
      url?: string;
      title?: string;
      reviewDate?: string;
      textualRating?: string;
      languageCode?: string;
    }[];
  }[];
}

export async function factCheckLookup(
  apiKey: string,
  query: string,
  language?: string,
): Promise<FactCheckHit[]> {
  const url = new URL(ENDPOINT);
  url.searchParams.set("query", query);
  url.searchParams.set("key", apiKey);
  if (language) url.searchParams.set("languageCode", language);
  url.searchParams.set("pageSize", "5");

  const res = await fetch(url);
  if (!res.ok) {
    if (res.status === 403 || res.status === 400) return [];
    throw new Error(`Fact Check API ${res.status}`);
  }
  const data = (await res.json()) as FactCheckResponse;
  const out: FactCheckHit[] = [];
  for (const claim of data.claims ?? []) {
    for (const review of claim.claimReview ?? []) {
      if (!review.url || !review.publisher?.name) continue;
      out.push({
        publisher: review.publisher.name,
        publisherSite: review.publisher.site,
        url: review.url,
        reviewDate: review.reviewDate,
        rating: review.textualRating ?? "—",
        claimText: claim.text ?? query,
        language: review.languageCode,
      });
    }
  }
  return out;
}
