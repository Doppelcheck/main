export function EmptyState() {
  return (
    <div className="mt-6 rounded-md border border-dashed border-ink/15 p-4 text-sm text-ink/60 dark:border-paper/20 dark:text-paper/60">
      <p className="font-medium text-ink dark:text-paper">Ready when you are.</p>
      <p className="mt-1">
        Open an article you'd like to scrutinise and click <strong>Analyze page</strong>.
        DoppelCheck will pull out the strongest factual claims, then — claim by
        claim — check fact-check databases and independent sources for support
        or contradictions.
      </p>
    </div>
  );
}
