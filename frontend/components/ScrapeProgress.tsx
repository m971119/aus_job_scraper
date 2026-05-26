interface Props {
  status: string;
  phase: string;
  currentPage: number;
  jobsScraped: number;
  jobsCompared: number;
  onCancel: () => void;
  countdown: number;
}

export default function ScrapeProgress({
  status,
  phase,
  currentPage,
  jobsScraped,
  jobsCompared,
  onCancel,
  countdown,
}: Props) {
  if (status === "idle") return null;

  const isRunning = status === "running";

  const lines: string[] = [];

  if (status === "done") {
    lines.push("Scrape complete");
    if (jobsScraped > 0) lines.push(`${jobsScraped} jobs scraped from seek`);
    if (jobsCompared > 0) lines.push(`${jobsCompared} jobs compared`);
  } else if (status === "cancelled") {
    lines.push("Scrape cancelled");
  } else if (status === "error") {
    lines.push("Scrape failed");
  } else {
    if (phase === "seeking") {
      lines.push(`Scraping page ${currentPage} on seek`);
      if (jobsScraped > 0) lines.push(`${jobsScraped} jobs found so far`);
    } else {
      lines.push(`${jobsScraped} jobs scraped from seek, comparing to local database`);
      lines.push(`${jobsCompared} jobs compared`);
    }
  }

  return (
    <div className="mt-3 space-y-1">
      <div className="flex items-start justify-between">
        <div className="space-y-0.5">
          {lines.map((line, i) => (
            <p key={i} className="text-sm text-[#888888]">
              {line}
              {i === 0 && isRunning && countdown > 0 && (
                <span className="ml-2 text-xs">— next update in {countdown}s</span>
              )}
            </p>
          ))}
        </div>
        {isRunning && (
          <button
            onClick={onCancel}
            className="text-xs text-[#753991] hover:underline ml-4 mt-0.5 shrink-0"
          >
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}
