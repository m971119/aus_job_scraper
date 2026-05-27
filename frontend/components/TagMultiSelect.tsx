"use client";
import { useState, useRef, useEffect } from "react";
import { Tag } from "@/types";

interface Props {
  label: string;
  tags: Tag[];
  selected: string[];
  onChange: (updater: (prev: string[]) => string[]) => void;
}

export default function TagMultiSelect({ label, tags, selected, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const toggle = (name: string) => {
    onChange((prev) => prev.includes(name) ? prev.filter((s) => s !== name) : [...prev, name]);
  };

  const buttonLabel = selected.length === 0 ? label : `${label} (${selected.length})`;

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`w-full px-4 py-2 border rounded-lg text-sm text-left bg-white focus:outline-none focus:ring-2 focus:ring-primary transition-colors ${
          selected.length > 0 ? "border-primary text-primary" : "border-gray-200 text-gray-700"
        }`}
      >
        <span className="flex items-center justify-between">
          <span className="truncate">{buttonLabel}</span>
          <span className="ml-2 opacity-50 flex-shrink-0">▾</span>
        </span>
      </button>
      {open && tags.length > 0 && (
        <div className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
          {tags.map((t) => (
            <label
              key={t.id}
              className="flex items-center gap-2 px-3 py-2 hover:bg-gray-50 cursor-pointer text-sm text-gray-700"
            >
              <input
                type="checkbox"
                checked={selected.includes(t.name)}
                onChange={() => toggle(t.name)}
                className="accent-primary"
              />
              {t.name}
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
