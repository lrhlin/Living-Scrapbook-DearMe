"use client";

import { useState } from "react";
import EntryPanel from "@/components/EntryPanel";
import MemoryGraphPanel from "@/components/MemoryGraphPanel";
import AestheticPanel from "@/components/AestheticPanel";
import ExtractPanel from "@/components/ExtractPanel";
import ChaptersPanel from "@/components/ChaptersPanel";

const TABS = [
  { id: "entries",  label: "📝 Journal" },
  { id: "graph",    label: "🕸 Memory Graph" },
  { id: "style",    label: "🎨 My Style" },
  { id: "extract",  label: "✂️ Extract Materials" },
  { id: "chapters", label: "📖 Living Chapters" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function HomePage() {
  const [tab, setTab] = useState<TabId>("entries");

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Header */}
      <header className="mb-8 text-center">
        <h1 className="text-3xl font-semibold tracking-tight text-stone-800">
          Living Scrapbook
        </h1>
        <p className="mt-1 text-stone-500 text-sm">Dear Me · little moments, beautifully remembered</p>
      </header>

      {/* Tab bar */}
      <nav className="flex gap-1 flex-wrap mb-8 border-b border-stone-200 pb-2">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-3 py-1.5 rounded-t text-sm font-medium transition-colors ${
              tab === t.id
                ? "bg-white border border-b-white border-stone-200 text-stone-800 -mb-px"
                : "text-stone-500 hover:text-stone-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {/* Panels */}
      <main>
        {tab === "entries"  && <EntryPanel />}
        {tab === "graph"    && <MemoryGraphPanel />}
        {tab === "style"    && <AestheticPanel />}
        {tab === "extract"  && <ExtractPanel />}
        {tab === "chapters" && <ChaptersPanel />}
      </main>
    </div>
  );
}
