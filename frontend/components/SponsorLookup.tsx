"use client";
import { useState, useEffect, useRef, useMemo } from "react";
import Fuse from "fuse.js";

interface Props {
  companyName: string;
  sponsors: string[];
}

export default function SponsorLookup({ companyName, sponsors }: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleOpen = () => {
    setQuery(companyName);
    setOpen(true);
  };

  const fuse = useMemo(
    () => new Fuse(sponsors, { threshold: 0.4, includeScore: true }),
    [sponsors]
  );

  const results = useMemo(
    () => (query ? fuse.search(query).slice(0, 8) : []),
    [fuse, query]
  );

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={handleOpen}
        className="text-xs text-muted hover:text-primary border border-gray-200 hover:border-primary px-2 py-0.5 rounded transition-colors"
      >
        Sponsor?
      </button>

      {open && (
        <div className="absolute z-20 left-0 mt-1 w-72 bg-white border border-gray-200 rounded-lg shadow-lg p-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full px-3 py-1.5 text-sm border border-gray-200 rounded focus:outline-none focus:ring-2 focus:ring-primary"
            placeholder="Search sponsor list..."
            autoFocus
          />
          <div className="mt-2 max-h-48 overflow-y-auto space-y-0.5">
            {query && results.length === 0 && (
              <p className="text-xs text-muted py-2 text-center">No matches found</p>
            )}
            {results.map(({ item, score }) => (
              <div
                key={item}
                className="flex items-center justify-between px-2 py-1.5 rounded hover:bg-gray-50 text-sm"
              >
                <span className="text-gray-700 truncate mr-2">{item}</span>
                <span
                  className={`shrink-0 text-xs font-medium px-1.5 py-0.5 rounded ${
                    (score ?? 1) < 0.2
                      ? "bg-green-100 text-green-700"
                      : (score ?? 1) < 0.4
                      ? "bg-yellow-100 text-yellow-700"
                      : "bg-gray-100 text-gray-500"
                  }`}
                >
                  {(score ?? 1) < 0.2 ? "Strong" : (score ?? 1) < 0.4 ? "Likely" : "Weak"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
