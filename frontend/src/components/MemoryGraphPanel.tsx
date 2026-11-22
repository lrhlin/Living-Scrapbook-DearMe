"use client";

import { useEffect } from "react";
import { useStore } from "@/lib/store";

export default function MemoryGraphPanel() {
  const { memoryGraph, suggestions, entries, loadMemoryGraph, loadEntries } = useStore();

  useEffect(() => {
    loadEntries().then(() => loadMemoryGraph());
  }, [loadEntries, loadMemoryGraph]);

  // Build entry id → title lookup
  const titleMap: Record<string, string> = {};
  for (const e of entries) titleMap[e.id] = e.title;

  return (
    <div className="space-y-8">
      {/* Graph overview */}
      <section className="bg-white rounded-xl border border-stone-200 p-6">
        <h2 className="text-lg font-semibold mb-1">Memory Graph</h2>
        <p className="text-stone-400 text-sm mb-4">
          Your entries are linked by shared locations, people, and themes.
        </p>
        {!memoryGraph || memoryGraph.nodes.length === 0 ? (
          <p className="text-stone-400 text-sm">
            Add at least 2 entries that share a location, person, or tag to see connections.
          </p>
        ) : (
          <div className="space-y-4">
            <div className="flex gap-6 text-sm text-stone-500">
              <span>
                <span className="font-semibold text-stone-800">{memoryGraph.nodes.length}</span> memories
              </span>
              <span>
                <span className="font-semibold text-stone-800">{memoryGraph.edges.length}</span> connections
              </span>
            </div>

            {/* Edge list */}
            <ul className="space-y-2">
              {memoryGraph.edges.map((edge, i) => (
                <li key={i} className="flex items-start gap-3 p-3 bg-stone-50 rounded-lg text-sm">
                  <span className="text-stone-400 mt-0.5">🔗</span>
                  <div>
                    <span className="font-medium text-stone-800">
                      {titleMap[edge.source] ?? edge.source}
                    </span>
                    <span className="text-stone-400 mx-1.5">↔</span>
                    <span className="font-medium text-stone-800">
                      {titleMap[edge.target] ?? edge.target}
                    </span>
                    <p className="text-stone-400 text-xs mt-0.5">{edge.reason}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {/* AI Suggestions */}
      <section className="bg-white rounded-xl border border-stone-200 p-6">
        <h2 className="text-lg font-semibold mb-1">✨ Suggested Themes</h2>
        <p className="text-stone-400 text-sm mb-4">
          Connections you might have forgotten — group them into a themed scrapbook.
        </p>
        {suggestions.length === 0 ? (
          <p className="text-stone-400 text-sm">No suggestions yet. Add more entries with shared details.</p>
        ) : (
          <ul className="space-y-3">
            {suggestions.map((s, i) => (
              <li key={i} className="p-4 border border-amber-100 bg-amber-50 rounded-xl">
                <p className="font-medium text-stone-800 text-sm">
                  💡 {s.suggested_theme}
                </p>
                <p className="text-stone-500 text-xs mt-1">
                  <span className="font-medium">{titleMap[s.entry_a] ?? s.entry_a}</span>
                  {" and "}
                  <span className="font-medium">{titleMap[s.entry_b] ?? s.entry_b}</span>
                  {" share: "}
                  {s.reason}
                </p>
              </li>
            ))}
          </ul>
        )}
        <button
          onClick={() => loadMemoryGraph()}
          className="mt-4 px-4 py-2 text-sm border border-stone-200 rounded-lg text-stone-600 hover:bg-stone-50 transition-colors"
        >
          Refresh
        </button>
      </section>
    </div>
  );
}
