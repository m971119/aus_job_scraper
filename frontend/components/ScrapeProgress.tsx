interface Props {
  status: string;
  currentPage: number;
  totalPages: number;
  onCancel: () => void;
  countdown: number;
}

export default function ScrapeProgress({ status, currentPage, totalPages, onCancel, countdown }: Props) {
  if (status === "idle") return null;

  const isRunning = status === "running";
  const detecting = isRunning && totalPages === 0;
  const pct = totalPages > 0 ? Math.round((currentPage / totalPages) * 100) : 0;

  let label: string;
  if (detecting) {
    label = `Scraping page ${currentPage}...`;
  } else if (isRunning) {
    label = `Scraping... page ${currentPage} of ${totalPages}`;
  } else if (status === "done") {
    label = "Scrape complete";
  } else if (status === "cancelled") {
    label = "Scrape cancelled";
  } else {
    label = "Scrape failed";
  }

  return (
    <div className="mt-3 space-y-2">
      <div className="flex items-center justify-between text-sm text-[#888888]">
        <span>
          {label}
          {isRunning && countdown > 0 && (
            <span className="ml-2 text-xs text-[#888888]">— next update in {countdown}s</span>
          )}
        </span>
        {isRunning && (
          <button
            onClick={onCancel}
            className="text-xs text-[#753991] hover:underline"
          >
            Cancel
          </button>
        )}
      </div>

      {!detecting && (isRunning || status === "done") && (
        <div className="h-1.5 w-full rounded-full bg-gray-200 overflow-hidden">
          <div
            className="h-full rounded-full bg-[#209dd7] transition-all duration-300"
            style={{ width: `${status === "done" ? 100 : pct}%` }}
          />
        </div>
      )}
    </div>
  );
}
