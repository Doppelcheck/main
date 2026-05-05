import type { ExtractedPage } from "@/types";

export function PageMeta({ page }: { page: ExtractedPage }) {
  let host = "";
  try {
    host = new URL(page.url).hostname;
  } catch {
    /* ignore */
  }
  return (
    <section className="rounded-md border border-ink/10 bg-paper/60 p-3 text-sm dark:border-paper/15 dark:bg-paper/5">
      <p className="line-clamp-2 font-medium leading-snug">{page.title || host}</p>
      <p className="mt-1 text-xs text-ink/55 dark:text-paper/55">
        {host}
        {page.author ? ` · ${page.author}` : ""}
        {page.published ? ` · ${page.published}` : ""}
        {page.language ? ` · ${page.language}` : ""}
        {" · "}
        {page.wordCount.toLocaleString()} words
      </p>
    </section>
  );
}
