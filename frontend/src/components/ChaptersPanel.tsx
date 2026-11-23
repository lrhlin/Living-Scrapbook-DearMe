"use client";

import { useState } from "react";
import { useStore } from "@/lib/store";

export default function ChaptersPanel() {
  const { chapters, loadChapters, entries } = useStore();
  const [loading, setLoading] = useState(false);

  const titleMap: Record<string, string> = {};
  for (const e of entries) titleMap[e.id] = e.title;

  async function handleGenerate() {
    setLoading(true);
    try {
      await loadChapters();
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      <section className="bg-white rounded-xl border border-stone-200 p-6">
        <h2 className="text-lg font-semibold mb-1">Living Chapters</h2>
        <p className="text-stone-400 text-sm mb-4">
          The AI reads your entries and assembles the long-running stories hidden inside them.
          Each chapter is a narrative arc that spans days, months, or years.
        </p>
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="px-5 py-2 bg-stone-800 text-white rounded-lg text-sm font-medium hover:bg-stone-700 disabled:opacity-50 transition-colors"
        >
          {loading ? "Generating chapters…" : "✨ Generate My Chapters"}
        </button>
      </section>

      {chapters.length === 0 && !loading && (
        <p className="text-stone-400 text-sm text-center py-8">
          Add memories with a shared location, person or tag, then generate your first chapter.
        </p>
      )}

      {chapters.map((chapter) => (
        <article key={chapter.id} className="bg-white rounded-xl border border-stone-200 overflow-hidden">
          {/* Chapter header */}
          <div className="bg-stone-800 text-white px-6 py-4">
            <p className="text-xs text-stone-400 uppercase tracking-widest mb-0.5">
              {chapter.theme}
            </p>
            <h3 className="text-xl font-semibold">{chapter.title}</h3>
          </div>

          {/* Narrative */}
          <div className="px-6 py-5 border-b border-stone-100">
            <p className="text-stone-600 text-sm leading-relaxed italic">"{chapter.narrative}"</p>
          </div>

          {/* Entry timeline */}
          <div className="px-6 py-5">
            <h4 className="text-xs uppercase tracking-widest text-stone-400 mb-4">Entries in this chapter</h4>
            <ol className="relative border-l border-stone-200 space-y-6 ml-2">
              {chapter.entries.map((ce) => (
                <li key={ce.entry_id} className="ml-4">
                  <div className="absolute -left-1.5 mt-1.5 w-3 h-3 rounded-full bg-stone-300 border-2 border-white" />
                  <time className="text-xs text-stone-400">{ce.date}</time>
                  <h5 className="font-semibold text-stone-800 text-sm mt-0.5">{ce.title}</h5>
                  {ce.summary && (
                    <p className="text-stone-500 text-xs mt-0.5">{ce.summary}</p>
                  )}
                </li>
              ))}
            </ol>
          </div>
        </article>
      ))}
    </div>
  );
}
