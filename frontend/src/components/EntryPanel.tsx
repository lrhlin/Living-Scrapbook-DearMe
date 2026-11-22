"use client";

import { useEffect, useState } from "react";
import { useStore } from "@/lib/store";
import type { EntryCreate } from "@/lib/api";

export default function EntryPanel() {
  const { entries, loadEntries, createEntry, deleteEntry } = useStore();
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState<EntryCreate>({
    title: "",
    text: "",
    location: "",
    people: [],
    tags: [],
  });
  const [peopleInput, setPeopleInput] = useState("");
  const [tagsInput, setTagsInput] = useState("");

  useEffect(() => {
    loadEntries();
  }, [loadEntries]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await createEntry({
        ...form,
        people: peopleInput.split(",").map((s) => s.trim()).filter(Boolean),
        tags: tagsInput.split(",").map((s) => s.trim()).filter(Boolean),
      });
      setForm({ title: "", text: "", location: "", people: [], tags: [] });
      setPeopleInput("");
      setTagsInput("");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      {/* New entry form */}
      <section className="bg-white rounded-xl border border-stone-200 p-6">
        <h2 className="text-lg font-semibold mb-4">New Entry</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <input
            required
            placeholder="Title"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            className="w-full px-3 py-2 rounded-lg border border-stone-200 text-sm focus:outline-none focus:ring-2 focus:ring-stone-300"
          />
          <textarea
            placeholder="What happened today…"
            rows={4}
            value={form.text}
            onChange={(e) => setForm({ ...form, text: e.target.value })}
            className="w-full px-3 py-2 rounded-lg border border-stone-200 text-sm focus:outline-none focus:ring-2 focus:ring-stone-300 resize-none"
          />
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <input
              placeholder="Location"
              value={form.location}
              onChange={(e) => setForm({ ...form, location: e.target.value })}
              className="px-3 py-2 rounded-lg border border-stone-200 text-sm focus:outline-none focus:ring-2 focus:ring-stone-300"
            />
            <input
              placeholder="People (comma separated)"
              value={peopleInput}
              onChange={(e) => setPeopleInput(e.target.value)}
              className="px-3 py-2 rounded-lg border border-stone-200 text-sm focus:outline-none focus:ring-2 focus:ring-stone-300"
            />
            <input
              placeholder="Tags (comma separated)"
              value={tagsInput}
              onChange={(e) => setTagsInput(e.target.value)}
              className="px-3 py-2 rounded-lg border border-stone-200 text-sm focus:outline-none focus:ring-2 focus:ring-stone-300"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="px-5 py-2 bg-stone-800 text-white rounded-lg text-sm font-medium hover:bg-stone-700 disabled:opacity-50 transition-colors"
          >
            {loading ? "Saving…" : "Add Entry"}
          </button>
        </form>
      </section>

      {/* Entry list */}
      <section>
        <h2 className="text-lg font-semibold mb-3">All Entries ({entries.length})</h2>
        {entries.length === 0 && (
          <p className="text-stone-400 text-sm">No entries yet. Add your first memory above.</p>
        )}
        <ul className="space-y-3">
          {entries.map((entry) => (
            <li key={entry.id} className="bg-white rounded-xl border border-stone-200 p-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="font-semibold text-stone-800">{entry.title}</h3>
                  <p className="text-stone-500 text-xs mt-0.5">
                    {new Date(entry.created_at).toLocaleDateString()}
                    {entry.location && ` · 📍 ${entry.location}`}
                  </p>
                  {entry.text && (
                    <p className="text-stone-600 text-sm mt-2 line-clamp-2">{entry.text}</p>
                  )}
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {entry.people.map((p) => (
                      <span key={p} className="px-2 py-0.5 bg-stone-100 text-stone-600 rounded-full text-xs">
                        👤 {p}
                      </span>
                    ))}
                    {entry.tags.map((t) => (
                      <span key={t} className="px-2 py-0.5 bg-amber-50 text-amber-700 rounded-full text-xs">
                        # {t}
                      </span>
                    ))}
                  </div>
                </div>
                <button
                  onClick={() => deleteEntry(entry.id)}
                  className="text-stone-300 hover:text-red-400 transition-colors text-lg flex-shrink-0"
                  title="Delete entry"
                >
                  ×
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
