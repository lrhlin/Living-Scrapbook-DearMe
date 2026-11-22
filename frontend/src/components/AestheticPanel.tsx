"use client";

import { useEffect } from "react";
import { useStore } from "@/lib/store";
import type { EditAction } from "@/lib/api";

function Bar({ value, label }: { value: number; label: string }) {
  const pct = Math.round(value * 100);
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-stone-500">
        <span>{label}</span>
        <span>{pct}%</span>
      </div>
      <div className="h-2 bg-stone-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-stone-700 rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

// Demo actions users can fire to update the style profile
const DEMO_ACTIONS: { label: string; actions: EditAction[] }[] = [
  {
    label: "Delete a large sticker",
    actions: [{ action_type: "delete_sticker", element_type: "sticker", detail: {} }],
  },
  {
    label: "Move photo irregularly",
    actions: [{ action_type: "reposition_photo", element_type: "photo", detail: { irregular: true } }],
  },
  {
    label: "Pick muted color (#a89080)",
    actions: [{ action_type: "change_color", element_type: "background", detail: { saturation: 0.1, hex: "#a89080" } }],
  },
  {
    label: "Pick vivid color (#e63946)",
    actions: [{ action_type: "change_color", element_type: "background", detail: { saturation: 0.9, hex: "#e63946" } }],
  },
  {
    label: "Shrink a sticker",
    actions: [{ action_type: "resize", element_type: "sticker", detail: { scale: 0.5 } }],
  },
];

export default function AestheticPanel() {
  const { styleProfile, styleHint, loadStyleProfile, submitStyleFeedback } = useStore();

  useEffect(() => {
    loadStyleProfile();
  }, [loadStyleProfile]);

  async function handleDemoAction(actions: EditAction[]) {
    await submitStyleFeedback("demo", actions);
  }

  return (
    <div className="space-y-8">
      {/* Style profile bars */}
      <section className="bg-white rounded-xl border border-stone-200 p-6">
        <h2 className="text-lg font-semibold mb-1">Your Aesthetic Profile</h2>
        <p className="text-stone-400 text-sm mb-5">
          Built from your editing behaviour — every change you make teaches the AI your taste.
        </p>
        {styleProfile ? (
          <div className="space-y-4">
            <Bar value={styleProfile.prefer_minimalism}    label="Minimalism" />
            <Bar value={styleProfile.prefer_collage}       label="Collage feeling" />
            <Bar value={styleProfile.prefer_muted_colors}  label="Muted colours" />
            <Bar value={styleProfile.prefer_negative_space} label="Negative space" />

            <div className="mt-4 pt-4 border-t border-stone-100">
              <p className="text-xs text-stone-400 mb-1">Prompt hint for AI layout generation:</p>
              <p className="text-sm text-stone-600 italic">"{styleHint}"</p>
            </div>

            {styleProfile.color_palette.length > 0 && (
              <div className="mt-3">
                <p className="text-xs text-stone-400 mb-2">Your colour palette history:</p>
                <div className="flex gap-2 flex-wrap">
                  {styleProfile.color_palette.map((hex) => (
                    <div
                      key={hex}
                      title={hex}
                      className="w-7 h-7 rounded-full border border-stone-200"
                      style={{ backgroundColor: hex }}
                    />
                  ))}
                </div>
              </div>
            )}

            <p className="text-xs text-stone-400 mt-2">Total edits recorded: {styleProfile.edit_count}</p>
          </div>
        ) : (
          <p className="text-stone-400 text-sm">Loading…</p>
        )}
      </section>

      {/* Demo interaction */}
      <section className="bg-white rounded-xl border border-stone-200 p-6">
        <h2 className="text-lg font-semibold mb-1">Simulate Editing Actions</h2>
        <p className="text-stone-400 text-sm mb-4">
          Click actions below to see how the AI learns your style in real time.
        </p>
        <div className="flex flex-wrap gap-2">
          {DEMO_ACTIONS.map((d) => (
            <button
              key={d.label}
              onClick={() => handleDemoAction(d.actions)}
              className="px-3 py-1.5 text-sm border border-stone-200 rounded-lg text-stone-700 hover:bg-stone-50 transition-colors"
            >
              {d.label}
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
