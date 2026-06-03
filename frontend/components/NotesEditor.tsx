"use client";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Underline from "@tiptap/extension-underline";
import Link from "@tiptap/extension-link";
import DOMPurify from "dompurify";
import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Props {
  jobId: number;
  initialNotes: string | null;
}

function ToolbarBtn({
  onClick,
  active,
  children,
}: {
  onClick: () => void;
  active?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onMouseDown={(e) => {
        e.preventDefault();
        onClick();
      }}
      className={`px-2 py-0.5 text-xs border rounded transition-colors ${
        active
          ? "border-primary bg-primary/10 text-primary"
          : "border-gray-200 bg-white text-gray-600 hover:border-primary hover:text-primary"
      }`}
    >
      {children}
    </button>
  );
}

export default function NotesEditor({ jobId, initialNotes }: Props) {
  const [editing, setEditing] = useState(false);
  const [html, setHtml] = useState<string | null>(initialNotes);
  const [linkOpen, setLinkOpen] = useState(false);
  const [linkUrl, setLinkUrl] = useState("");

  const editor = useEditor({
    extensions: [
      StarterKit,
      Underline,
      Link.configure({ openOnClick: false }),
    ],
    content: html ?? "",
    editorProps: {
      attributes: {
        class:
          "notes-content outline-none min-h-[80px] px-3 py-2.5 text-sm leading-relaxed",
      },
    },
    onBlur: async ({ editor }) => {
      const content = editor.isEmpty ? null : editor.getHTML();
      setHtml(content);
      setEditing(false);
      try {
        const res = await fetch(`${API}/api/jobs/${jobId}/notes`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ notes: content }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
      } catch (err) {
        console.error("Failed to save notes:", err);
      }
    },
  });

  const handleEdit = () => {
    editor?.commands.setContent(html ?? "");
    setEditing(true);
    setTimeout(() => editor?.commands.focus(), 0);
  };

  const openLinkInput = () => {
    const existing = editor?.getAttributes("link").href ?? "";
    setLinkUrl(existing);
    setLinkOpen(true);
  };

  const applyLink = () => {
    if (!editor) return;
    if (linkUrl.trim()) editor.chain().focus().setLink({ href: linkUrl.trim() }).run();
    else editor.chain().focus().unsetLink().run();
    setLinkOpen(false);
    setLinkUrl("");
  };

  const cancelLink = () => {
    setLinkOpen(false);
    setLinkUrl("");
    editor?.commands.focus();
  };

  return (
    <div className="mt-6 pt-5 border-t border-gray-100">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-sm font-semibold text-navy">Notes</h2>
        {editing ? (
          <span className="text-xs text-muted italic">Saves on close</span>
        ) : (
          <button
            onClick={handleEdit}
            className="text-xs text-muted hover:text-primary border border-gray-200 hover:border-primary px-2 py-0.5 rounded transition-colors"
          >
            Edit
          </button>
        )}
      </div>

      {editing ? (
        <div className="border border-primary rounded-lg overflow-hidden ring-2 ring-primary/20">
          <div className="flex flex-wrap gap-1 px-2 py-1.5 bg-gray-50 border-b border-gray-200">
            <ToolbarBtn
              onClick={() => editor?.chain().focus().toggleBold().run()}
              active={editor?.isActive("bold")}
            >
              <strong>B</strong>
            </ToolbarBtn>
            <ToolbarBtn
              onClick={() => editor?.chain().focus().toggleItalic().run()}
              active={editor?.isActive("italic")}
            >
              <em>I</em>
            </ToolbarBtn>
            <ToolbarBtn
              onClick={() => editor?.chain().focus().toggleUnderline().run()}
              active={editor?.isActive("underline")}
            >
              <span className="underline">U</span>
            </ToolbarBtn>
            <div className="w-px bg-gray-200 mx-0.5" />
            <ToolbarBtn
              onClick={() => editor?.chain().focus().toggleBulletList().run()}
              active={editor?.isActive("bulletList")}
            >
              • List
            </ToolbarBtn>
            <ToolbarBtn
              onClick={() => editor?.chain().focus().toggleOrderedList().run()}
              active={editor?.isActive("orderedList")}
            >
              1. List
            </ToolbarBtn>
            {linkOpen ? (
              <div
                className="flex items-center gap-1"
                onMouseDown={(e) => e.preventDefault()}
              >
                <input
                  type="url"
                  value={linkUrl}
                  onChange={(e) => setLinkUrl(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") { e.preventDefault(); applyLink(); }
                    if (e.key === "Escape") { e.preventDefault(); cancelLink(); }
                  }}
                  placeholder="https://..."
                  autoFocus
                  className="text-xs border border-gray-300 rounded px-2 py-0.5 w-40 focus:outline-none focus:border-primary"
                />
                <button
                  type="button"
                  onMouseDown={(e) => { e.preventDefault(); applyLink(); }}
                  className="text-xs border border-primary rounded px-2 py-0.5 bg-primary/10 text-primary"
                >
                  OK
                </button>
                <button
                  type="button"
                  onMouseDown={(e) => { e.preventDefault(); cancelLink(); }}
                  className="text-xs border border-gray-200 rounded px-2 py-0.5 text-gray-500"
                >
                  X
                </button>
              </div>
            ) : (
              <ToolbarBtn onClick={openLinkInput} active={editor?.isActive("link")}>
                Link
              </ToolbarBtn>
            )}
          </div>
          <EditorContent editor={editor} />
        </div>
      ) : (
        <div
          onClick={handleEdit}
          className="cursor-pointer px-3 py-2.5 border border-gray-200 rounded-lg bg-gray-50 min-h-[60px] hover:border-primary/40 transition-colors"
        >
          {html ? (
            <div
              className="notes-content text-sm leading-relaxed"
              dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(html) }}
            />
          ) : (
            <p className="text-muted text-sm italic">No notes yet.</p>
          )}
        </div>
      )}
    </div>
  );
}
