import type { ClaimState } from "../state";
import type { FactCheckHit, SearchHit, Verdict } from "@/types";

interface Props {
  index: number;
  claim: ClaimState;
  onVerify: () => void;
  onHighlight: () => void;
}

export function ClaimCard({ index, claim, onVerify, onHighlight }: Props) {
  const { claim: c, phase, factChecks, searchHits, verdicts, error } = claim;
  const verifying = phase === "verifying";

  return (
    <li className="rounded-md border border-ink/10 bg-paper/40 p-3 dark:border-paper/15 dark:bg-paper/5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wide text-ink/45 dark:text-paper/55">
            Claim {index}
          </p>
          <p
            className="mt-1 cursor-pointer leading-snug hover:underline"
            onClick={onHighlight}
            title="Highlight on page"
          >
            {c.text}
          </p>
          {c.rationale && (
            <p className="mt-1 text-xs italic text-ink/55 dark:text-paper/55">
              {c.rationale}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={onVerify}
          disabled={verifying}
          className="shrink-0 rounded-md border border-accent/40 bg-accent/10 px-2.5 py-1 text-xs font-medium text-accent transition hover:bg-accent/20 disabled:opacity-50 dark:text-paper"
        >
          {phase === "done" ? "Re-verify" : verifying ? "Verifying…" : "Verify"}
        </button>
      </div>

      {factChecks && factChecks.length > 0 && (
        <FactCheckList hits={factChecks} />
      )}

      {searchHits && (
        <SearchResults hits={searchHits} verdicts={verdicts} verifying={verifying} />
      )}

      {error && (
        <p className="mt-2 text-xs text-disagree">{error}</p>
      )}
    </li>
  );
}

function FactCheckList({ hits }: { hits: FactCheckHit[] }) {
  return (
    <div className="mt-3 rounded-sm border border-ink/10 bg-ink/[0.03] p-2 dark:border-paper/15 dark:bg-paper/[0.04]">
      <p className="text-xs font-semibold uppercase tracking-wide text-ink/55 dark:text-paper/60">
        Existing fact-checks
      </p>
      <ul className="mt-1 space-y-1">
        {hits.map((h) => (
          <li key={h.url} className="text-sm">
            <a
              href={h.url}
              target="_blank"
              rel="noreferrer"
              className="text-accent hover:underline"
            >
              {h.publisher}
            </a>
            : <span className="font-medium">{h.rating}</span>
            {h.reviewDate && (
              <span className="ml-1 text-xs text-ink/50 dark:text-paper/55">
                ({h.reviewDate.slice(0, 10)})
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function SearchResults({
  hits,
  verdicts,
  verifying,
}: {
  hits: SearchHit[];
  verdicts: Verdict[];
  verifying: boolean;
}) {
  const byUrl = new Map(verdicts.map((v) => [v.url, v]));
  return (
    <div className="mt-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-ink/55 dark:text-paper/60">
        Independent sources
      </p>
      {hits.length === 0 && (
        <p className="mt-1 text-xs text-ink/55 dark:text-paper/60">
          No matching sources.
        </p>
      )}
      <ul className="mt-1 space-y-2">
        {hits.map((h) => {
          const v = byUrl.get(h.url);
          return (
            <li key={h.url} className="text-sm">
              <div className="flex items-center gap-2">
                {v ? <AlignmentBadge alignment={v.alignment} /> : verifying ? <Pending /> : null}
                <a
                  href={h.url}
                  target="_blank"
                  rel="noreferrer"
                  className="truncate text-accent hover:underline"
                  title={h.url}
                >
                  {h.title || h.domain}
                </a>
                {h.customDomain && (
                  <span className="rounded-sm bg-ink/10 px-1 text-[10px] uppercase tracking-wide dark:bg-paper/15">
                    custom
                  </span>
                )}
              </div>
              <p className="ml-6 text-xs text-ink/60 dark:text-paper/60">{h.domain}</p>
              {v?.evidence && (
                <blockquote className="ml-6 mt-1 border-l-2 border-ink/15 pl-2 text-xs italic dark:border-paper/20">
                  {v.evidence}
                </blockquote>
              )}
              {v?.explanation && (
                <p className="ml-6 mt-1 text-xs text-ink/70 dark:text-paper/70">
                  {v.explanation}
                </p>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function AlignmentBadge({ alignment }: { alignment: Verdict["alignment"] }) {
  const styles: Record<Verdict["alignment"], string> = {
    agrees: "bg-agree/15 text-agree",
    disagrees: "bg-disagree/15 text-disagree",
    unrelated: "bg-unrelated/15 text-unrelated",
  };
  const labels: Record<Verdict["alignment"], string> = {
    agrees: "agrees",
    disagrees: "disagrees",
    unrelated: "unrelated",
  };
  return (
    <span
      className={`rounded-sm px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${styles[alignment]}`}
    >
      {labels[alignment]}
    </span>
  );
}

function Pending() {
  return (
    <span className="h-2 w-2 animate-pulse rounded-full bg-accent" aria-label="pending" />
  );
}
