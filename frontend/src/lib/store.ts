/**
 * Global Zustand store — single source of truth for all feature state.
 */
"use client";

import { create } from "zustand";
import {
  api,
  type ConnectionSuggestion,
  type Entry,
  type EntryCreate,
  type ExtractionResult,
  type LivingChapter,
  type MemoryGraph,
  type StyleProfile,
  type EditAction,
} from "@/lib/api";

interface AppState {
  // Entries
  entries: Entry[];
  loadEntries: () => Promise<void>;
  createEntry: (payload: EntryCreate) => Promise<Entry>;
  deleteEntry: (id: string) => Promise<void>;

  // Memory Graph
  memoryGraph: MemoryGraph | null;
  suggestions: ConnectionSuggestion[];
  loadMemoryGraph: () => Promise<void>;

  // Style
  styleProfile: StyleProfile | null;
  styleHint: string;
  loadStyleProfile: () => Promise<void>;
  submitStyleFeedback: (entryId: string, actions: EditAction[]) => Promise<void>;

  // Extraction
  extractionResult: ExtractionResult | null;
  extracting: boolean;
  extractObjects: (file: File, style: string) => Promise<void>;

  // Chapters
  chapters: LivingChapter[];
  loadChapters: () => Promise<void>;
}

export const useStore = create<AppState>((set, get) => ({
  // ── Entries ──────────────────────────────────────
  entries: [],
  async loadEntries() {
    const entries = await api.entries.list();
    set({ entries });
  },
  async createEntry(payload) {
    const entry = await api.entries.create(payload);
    set((s) => ({ entries: [entry, ...s.entries] }));
    return entry;
  },
  async deleteEntry(id) {
    await api.entries.delete(id);
    set((s) => ({ entries: s.entries.filter((e) => e.id !== id) }));
  },

  // ── Memory Graph ─────────────────────────────────
  memoryGraph: null,
  suggestions: [],
  async loadMemoryGraph() {
    const [graph, suggestions] = await Promise.all([
      api.memoryGraph.get(),
      api.memoryGraph.suggestions(),
    ]);
    set({ memoryGraph: graph, suggestions });
  },

  // ── Style ────────────────────────────────────────
  styleProfile: null,
  styleHint: "",
  async loadStyleProfile() {
    const [profile, { hint }] = await Promise.all([
      api.style.profile(),
      api.style.hint(),
    ]);
    set({ styleProfile: profile, styleHint: hint });
  },
  async submitStyleFeedback(entryId, actions) {
    const profile = await api.style.feedback(entryId, actions);
    const { hint } = await api.style.hint();
    set({ styleProfile: profile, styleHint: hint });
  },

  // ── Extraction ───────────────────────────────────
  extractionResult: null,
  extracting: false,
  async extractObjects(file, style) {
    set({ extracting: true, extractionResult: null });
    try {
      const result = await api.extract.fromImage(file, style);
      set({ extractionResult: result });
    } finally {
      set({ extracting: false });
    }
  },

  // ── Chapters ─────────────────────────────────────
  chapters: [],
  async loadChapters() {
    const chapters = await api.chapters.list();
    set({ chapters });
  },
}));
