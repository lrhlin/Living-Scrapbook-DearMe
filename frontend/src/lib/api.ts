const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ── Types ───────────────────────────────────────────────────────────────────

export interface Entry {
  id: string;
  title: string;
  text: string;
  location: string;
  people: string[];
  tags: string[];
  image_urls: string[];
  created_at: string;
  updated_at: string;
}

export interface EntryCreate {
  title: string;
  text?: string;
  location?: string;
  people?: string[];
  tags?: string[];
  image_urls?: string[];
}

export interface MemoryNode {
  entry_id: string;
  title: string;
  location: string;
  people: string[];
  tags: string[];
  created_at: string;
}

export interface MemoryEdge {
  source: string;
  target: string;
  reason: string;
  weight: number;
}

export interface MemoryGraph {
  nodes: MemoryNode[];
  edges: MemoryEdge[];
}

export interface ConnectionSuggestion {
  entry_a: string;
  entry_b: string;
  reason: string;
  suggested_theme: string;
}

export interface StyleProfile {
  user_id: string;
  prefer_minimalism: number;
  prefer_collage: number;
  prefer_muted_colors: number;
  prefer_negative_space: number;
  color_palette: string[];
  edit_count: number;
}

export interface EditAction {
  action_type: string;
  element_type: string;
  detail: Record<string, unknown>;
}

export interface ExtractedObject {
  id: string;
  label: string;
  style: string;
  image_url: string;
  description: string;
}

export interface ExtractionResult {
  source_image_url: string;
  objects: ExtractedObject[];
}

export interface ChapterEntry {
  entry_id: string;
  title: string;
  date: string;
  summary: string;
}

export interface LivingChapter {
  id: string;
  title: string;
  narrative: string;
  entries: ChapterEntry[];
  theme: string;
  created_at: string;
}

// ── API calls ────────────────────────────────────────────────────────────────

export const api = {
  // Entries
  entries: {
    list: () => request<Entry[]>("/entries/"),
    create: (body: EntryCreate) =>
      request<Entry>("/entries/", { method: "POST", body: JSON.stringify(body) }),
    delete: (id: string) =>
      fetch(`${BASE}/entries/${id}`, { method: "DELETE" }),
  },

  // Memory Graph
  memoryGraph: {
    get: () => request<MemoryGraph>("/memory-graph/"),
    suggestions: () => request<ConnectionSuggestion[]>("/memory-graph/suggestions"),
  },

  // Aesthetic / Style
  style: {
    profile: () => request<StyleProfile>("/style/profile"),
    hint: () => request<{ hint: string }>("/style/profile/hint"),
    feedback: (entry_id: string, actions: EditAction[]) =>
      request<StyleProfile>("/style/feedback", {
        method: "POST",
        body: JSON.stringify({ entry_id, actions }),
      }),
    reset: () => fetch(`${BASE}/style/profile`, { method: "DELETE" }).then((r) => r.json()),
  },

  // Object Extraction
  extract: {
    fromImage: async (file: File, style = "watercolor"): Promise<ExtractionResult> => {
      const form = new FormData();
      form.append("file", file);
      form.append("style", style);
      const res = await fetch(`${BASE}/extract/`, { method: "POST", body: form });
      if (!res.ok) throw new Error(`Extract error ${res.status}`);
      return res.json();
    },
  },

  // Living Chapters
  chapters: {
    list: () => request<LivingChapter[]>("/chapters/"),
  },
};
