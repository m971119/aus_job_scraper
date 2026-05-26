"use client";
import { useEffect, useRef, useState } from "react";
import { Tag } from "@/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Props {
  jobId: number;
  initialTags: Tag[];
}

export default function TagManager({ jobId, initialTags }: Props) {
  const [tags, setTags] = useState<Tag[]>(initialTags);
  const [allTags, setAllTags] = useState<Tag[]>([]);
  const [input, setInput] = useState("");
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch(`${API}/api/tags`)
      .then((r) => r.json())
      .then(setAllTags);
  }, []);

  useEffect(() => {
    const onClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const appliedIds = new Set(tags.map((t) => t.id));

  const suggestions = allTags.filter(
    (t) =>
      !appliedIds.has(t.id) &&
      t.name.toLowerCase().includes(input.toLowerCase())
  );

  const canCreate =
    input.trim().length > 0 &&
    !allTags.some((t) => t.name.toLowerCase() === input.trim().toLowerCase());

  const applyTag = async (tag: Tag) => {
    await fetch(`${API}/api/jobs/${jobId}/tags/${tag.id}`, { method: "POST" });
    setTags((prev) => [...prev, tag]);
    setInput("");
    setOpen(false);
  };

  const createAndApply = async () => {
    const name = input.trim();
    if (!name) return;
    const res = await fetch(`${API}/api/tags`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (!res.ok) return;
    const newTag: Tag = await res.json();
    setAllTags((prev) => [...prev, newTag]);
    await applyTag(newTag);
  };

  const removeTag = async (tag: Tag) => {
    await fetch(`${API}/api/jobs/${jobId}/tags/${tag.id}`, { method: "DELETE" });
    setTags((prev) => prev.filter((t) => t.id !== tag.id));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      if (suggestions.length > 0 && !canCreate) {
        applyTag(suggestions[0]);
      } else if (canCreate) {
        createAndApply();
      }
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div className="mt-6 pt-5 border-t border-gray-100">
      <h2 className="text-sm font-semibold text-navy mb-3">Tags</h2>

      <div className="flex flex-wrap gap-2 mb-3">
        {tags.map((tag) => (
          <span
            key={tag.id}
            className="inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full bg-primary/10 text-primary border border-primary/20"
          >
            {tag.name}
            <button
              onClick={() => removeTag(tag)}
              className="ml-0.5 hover:text-red-500 transition-colors leading-none"
              aria-label={`Remove ${tag.name}`}
            >
              &times;
            </button>
          </span>
        ))}
      </div>

      <div ref={containerRef} className="relative inline-block">
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder="Add tag..."
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 w-48 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30"
        />

        {open && (suggestions.length > 0 || canCreate) && (
          <ul className="absolute z-10 mt-1 w-48 bg-white border border-gray-200 rounded-lg shadow-md text-sm overflow-hidden">
            {suggestions.map((tag) => (
              <li key={tag.id}>
                <button
                  className="w-full text-left px-3 py-2 hover:bg-gray-50 transition-colors"
                  onMouseDown={(e) => {
                    e.preventDefault();
                    applyTag(tag);
                  }}
                >
                  {tag.name}
                </button>
              </li>
            ))}
            {canCreate && (
              <li>
                <button
                  className="w-full text-left px-3 py-2 hover:bg-accent/10 text-accent font-medium transition-colors border-t border-gray-100"
                  onMouseDown={(e) => {
                    e.preventDefault();
                    createAndApply();
                  }}
                >
                  Create &ldquo;{input.trim()}&rdquo;
                </button>
              </li>
            )}
          </ul>
        )}
      </div>
    </div>
  );
}
