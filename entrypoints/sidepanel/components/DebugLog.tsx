import { useEffect, useRef, useState } from "react";
import type { ExtractedPage, LogEntry } from "@/types";

interface Props {
  logs: LogEntry[];
  /** Current page metadata, used as a header in copied / downloaded logs. */
  page?: ExtractedPage;
  open: boolean;
  onToggle: () => void;
  /** Wipe the log entries from state. */
  onClear: () => void;
}

export function DebugLog({ logs, page, open, onToggle, onClear }: Props) {
  const scrollerRef = useRef<HTMLDivElement>(null);
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle");

  // Auto-scroll the log to the bottom whenever it grows while open.
  useEffect(() => {
    if (!open) return;
    const el = scrollerRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [logs, open]);

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(formatLog(logs, page));
      setCopyState("copied");
    } catch {
      // Some browsers / contexts deny clipboard writes without an
      // explicit gesture chain — fall back is "select the log yourself"
      // (the panel is select-text, see below).
      setCopyState("failed");
    }
    window.setTimeout(() => setCopyState("idle"), 1500);
  };

  const onDownload = () => {
    const blob = new Blob([formatLog(logs, page)], {
      type: "text/plain;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${browserSlug()}_doppelcheck-${stamp()}.log`;
    a.click();
    // Defer revoke so the browser actually fetches the blob first.
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  return (
    <section className="border-t border-ink/10 bg-paper/95 dark:border-paper/15 dark:bg-ink/95">
      <header className="flex items-center gap-2 px-3 py-1.5 text-xs">
        <button
          type="button"
          onClick={onToggle}
          className="flex flex-1 items-center gap-2 text-left font-medium text-ink/70 hover:text-ink dark:text-paper/70 dark:hover:text-paper"
        >
          <span aria-hidden>{open ? "▾" : "▸"}</span>
          <span>Debug log</span>
          <span className="text-ink/45 dark:text-paper/55">
            ({logs.length} {logs.length === 1 ? "entry" : "entries"})
          </span>
        </button>
        {open && (
          <div className="flex items-center gap-1">
            <ToolBtn
              title="Copy log to clipboard"
              onClick={onCopy}
              disabled={logs.length === 0}
            >
              {copyState === "copied"
                ? "✓ Copied"
                : copyState === "failed"
                  ? "Copy failed"
                  : "Copy"}
            </ToolBtn>
            <ToolBtn
              title="Download log as text file"
              onClick={onDownload}
              disabled={logs.length === 0}
            >
              Download
            </ToolBtn>
            <ToolBtn
              title="Clear log entries"
              onClick={onClear}
              disabled={logs.length === 0}
            >
              Clear
            </ToolBtn>
          </div>
        )}
      </header>
      {open && (
        <div
          ref={scrollerRef}
          // `select-text` makes the log directly selectable with the
          // mouse / keyboard for ad-hoc copying. The Copy/Download
          // buttons above are for the common case.
          className="max-h-56 select-text overflow-y-auto border-t border-ink/10 bg-ink/[0.03] px-3 py-2 font-mono text-[11px] leading-snug dark:border-paper/15 dark:bg-paper/[0.04]"
        >
          {logs.length === 0 ? (
            <p className="text-ink/50 dark:text-paper/55">No log entries yet.</p>
          ) : (
            logs.map((log, i) => (
              <div key={i} className="flex gap-2">
                <span className="shrink-0 tabular-nums text-ink/45 dark:text-paper/45">
                  {fmtTime(log.at)}
                </span>
                <span
                  className={
                    "shrink-0 " +
                    (log.level === "error"
                      ? "text-disagree"
                      : log.level === "warn"
                        ? "text-amber-600 dark:text-amber-400"
                        : "text-ink/55 dark:text-paper/55")
                  }
                >
                  {log.phase}
                </span>
                <span className="break-words">
                  {log.claimId ? (
                    <span className="mr-1 text-ink/40 dark:text-paper/40">
                      [{log.claimId}]
                    </span>
                  ) : null}
                  {log.message}
                </span>
              </div>
            ))
          )}
        </div>
      )}
    </section>
  );
}

function ToolBtn({
  children,
  ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      {...rest}
      className="rounded-sm border border-ink/15 bg-paper/80 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-ink/70 transition hover:bg-ink/5 disabled:opacity-40 disabled:hover:bg-paper/80 dark:border-paper/20 dark:bg-paper/10 dark:text-paper/70 dark:hover:bg-paper/20 dark:disabled:hover:bg-paper/10"
    />
  );
}

function fmtTime(at: number): string {
  const d = new Date(at);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}.${String(d.getMilliseconds()).padStart(3, "0")}`;
}

function stamp(): string {
  return new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
}

/** Short browser identifier used as a filename prefix so logs from
 *  different browsers don't get interleaved or overwritten when the
 *  user keeps both side-by-side. UA sniffing is fine here — we only
 *  need a tag for filenames, not feature detection. */
function browserSlug(): string {
  const ua = navigator.userAgent;
  if (/Firefox\//.test(ua)) return "firefox";
  if (/Edg\//.test(ua)) return "edge";
  if (/OPR\//.test(ua)) return "opera";
  if (/Chrome\//.test(ua)) return "chrome";
  if (/Safari\//.test(ua)) return "safari";
  return "browser";
}

/** Plain-text rendering of the log with a small context header. Pasteable
 *  into a bug report; openable in any editor. */
function formatLog(logs: LogEntry[], page?: ExtractedPage): string {
  const out: string[] = [];
  out.push(`DoppelCheck debug log — ${new Date().toISOString()}`);
  out.push(`User-agent: ${navigator.userAgent}`);
  if (page) {
    out.push(`Page:       ${page.title}`);
    out.push(`URL:        ${page.url}`);
    if (page.language) out.push(`Language:   ${page.language}`);
    out.push(`Word count: ${page.wordCount}`);
  }
  out.push("");
  for (const log of logs) {
    const ts = new Date(log.at).toISOString().slice(11, 23); // HH:MM:SS.mmm
    const lvl = log.level.toUpperCase().padEnd(5);
    const phase = log.phase.padEnd(18);
    const claim = log.claimId ? ` [${log.claimId}]` : "";
    out.push(`${ts} ${lvl} ${phase}${claim} ${log.message}`);
  }
  out.push("");
  return out.join("\n");
}
