interface Props {
  onAnalyze: () => void;
  onOpenOptions: () => void;
  onClearHighlights: () => void;
  canAnalyze: boolean;
  busy: boolean;
}

export function Header({
  onAnalyze,
  onOpenOptions,
  onClearHighlights,
  canAnalyze,
  busy,
}: Props) {
  return (
    <header className="flex items-center justify-between border-b border-ink/10 bg-paper px-4 py-3 dark:border-paper/15 dark:bg-ink">
      <div className="flex items-center gap-2">
        <Logo />
        <h1 className="text-lg font-semibold tracking-tight">DoppelCheck</h1>
      </div>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onAnalyze}
          disabled={!canAnalyze || busy}
          className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white transition hover:bg-accent/90 disabled:opacity-40"
        >
          {busy ? "Working…" : "Analyze page"}
        </button>
        <button
          type="button"
          onClick={onClearHighlights}
          title="Clear in-page highlights"
          className="rounded-md p-1.5 text-ink/60 hover:bg-ink/5 dark:text-paper/60 dark:hover:bg-paper/10"
        >
          <BrushIcon />
        </button>
        <button
          type="button"
          onClick={onOpenOptions}
          title="Settings"
          className="rounded-md p-1.5 text-ink/60 hover:bg-ink/5 dark:text-paper/60 dark:hover:bg-paper/10"
        >
          <CogIcon />
        </button>
      </div>
    </header>
  );
}

function Logo() {
  return (
    <span
      aria-hidden
      className="grid h-7 w-7 place-items-center rounded-md bg-accent font-mono text-[11px] font-bold text-white"
    >
      DC
    </span>
  );
}

function CogIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}

function BrushIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M9.06 11.9 8 21l-3-3 3-3 .57-2.74a3 3 0 0 1 .85-1.61l9.16-9.17a1.5 1.5 0 0 1 2.12 2.12l-9.17 9.17a3 3 0 0 1-1.61.85L9.06 11.9z" />
    </svg>
  );
}
