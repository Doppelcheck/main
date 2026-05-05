import { useEffect, useState } from "react";
import type { Phase } from "@/types";

interface Props {
  phase: Phase;
  message?: string;
  progress?: number;
  busy: boolean;
}

const PHASE_LABEL: Record<Phase, string> = {
  idle: "",
  extracting: "Reading the page",
  "detect-language": "Detecting language",
  "model-download": "Downloading model",
  "model-test": "Testing model",
  "claim-extraction": "Extracting claims",
  "fact-check": "Checking fact-check databases",
  "query-generation": "Generating search query",
  search: "Searching the web",
  fetch: "Fetching sources",
  compare: "Comparing claim against source",
  highlight: "Highlighting on page",
  done: "Done",
  error: "Error",
};

export function StatusBar({ phase, message, progress, busy }: Props) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!busy) {
      setElapsed(0);
      return;
    }
    const start = Date.now();
    setElapsed(0);
    const id = window.setInterval(() => {
      setElapsed(Math.floor((Date.now() - start) / 1000));
    }, 250);
    return () => clearInterval(id);
  }, [busy, phase]);

  if (!busy && phase !== "error") return null;

  const label = PHASE_LABEL[phase] || "Working";
  const detail = message && message !== label ? message : undefined;

  return (
    <div className="border-b border-ink/10 bg-accent/[0.06] px-4 py-2 text-xs dark:border-paper/15 dark:bg-accent/15">
      <div className="flex items-center gap-2">
        {busy ? <Spinner /> : phase === "error" ? <ErrorDot /> : null}
        <span className="font-medium">{label}</span>
        {detail && (
          <span className="truncate text-ink/60 dark:text-paper/60" title={detail}>
            — {detail}
          </span>
        )}
        {busy && (
          <span className="ml-auto tabular-nums text-ink/55 dark:text-paper/55">
            {elapsed}s
          </span>
        )}
      </div>
      {typeof progress === "number" && progress >= 0 && progress <= 1 && (
        <div className="mt-1.5 h-1 w-full overflow-hidden rounded bg-ink/10 dark:bg-paper/15">
          <div
            className="h-full bg-accent transition-[width] duration-200"
            style={{ width: `${Math.round(progress * 100)}%` }}
          />
        </div>
      )}
    </div>
  );
}

function Spinner() {
  return (
    <svg
      className="h-3.5 w-3.5 animate-spin text-accent"
      viewBox="0 0 24 24"
      fill="none"
    >
      <circle
        cx="12"
        cy="12"
        r="9"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeOpacity="0.25"
      />
      <path
        d="M21 12a9 9 0 0 0-9-9"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

function ErrorDot() {
  return <span className="h-2 w-2 rounded-full bg-disagree" />;
}
