"use client";

import { useRef, useState } from "react";
import { useStore } from "@/lib/store";

const STYLES = ["watercolor", "lineart", "collage", "vintage"] as const;
type Style = (typeof STYLES)[number];

export default function ExtractPanel() {
  const { extractObjects, extractionResult, extracting } = useStore();
  const [style, setStyle] = useState<Style>("watercolor");
  const [preview, setPreview] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setPreview(URL.createObjectURL(file));
  }

  async function handleExtract() {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    await extractObjects(file, style);
  }

  return (
    <div className="space-y-8">
      <section className="bg-white rounded-xl border border-stone-200 p-6">
        <h2 className="text-lg font-semibold mb-1">Extract Materials from Photo</h2>
        <p className="text-stone-400 text-sm mb-5">
          Upload a photo and the AI will identify objects and generate scrapbook stickers for each one.
        </p>

        {/* Upload area */}
        <div
          className="border-2 border-dashed border-stone-200 rounded-xl p-8 text-center cursor-pointer hover:border-stone-400 transition-colors"
          onClick={() => fileRef.current?.click()}
        >
          {preview ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={preview} alt="Preview" className="max-h-48 mx-auto rounded-lg object-contain" />
          ) : (
            <p className="text-stone-400 text-sm">Click to upload a photo (JPG, PNG, WebP)</p>
          )}
          <input
            ref={fileRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={handleFileChange}
          />
        </div>

        {/* Style selector */}
        <div className="mt-4 flex flex-wrap gap-2">
          {STYLES.map((s) => (
            <button
              key={s}
              onClick={() => setStyle(s)}
              className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                style === s
                  ? "bg-stone-800 text-white border-stone-800"
                  : "border-stone-200 text-stone-600 hover:bg-stone-50"
              }`}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>

        <button
          onClick={handleExtract}
          disabled={extracting || !fileRef.current?.files?.length}
          className="mt-4 px-5 py-2 bg-stone-800 text-white rounded-lg text-sm font-medium hover:bg-stone-700 disabled:opacity-50 transition-colors"
        >
          {extracting ? "Extracting objects…" : "✂️ Extract & Generate Stickers"}
        </button>
      </section>

      {/* Results */}
      {extractionResult && (
        <section className="bg-white rounded-xl border border-stone-200 p-6">
          <h2 className="text-lg font-semibold mb-4">
            Extracted Objects ({extractionResult.objects.length})
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            {extractionResult.objects.map((obj) => (
              <div key={obj.id} className="border border-stone-100 rounded-xl p-3 text-center">
                {obj.image_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={obj.image_url}
                    alt={obj.label}
                    className="w-full h-32 object-contain rounded-lg mb-2"
                  />
                ) : (
                  <div className="w-full h-32 bg-stone-50 rounded-lg mb-2 flex items-center justify-center text-stone-300 text-3xl">
                    🖼
                  </div>
                )}
                <p className="text-sm font-medium text-stone-700 capitalize">{obj.label}</p>
                <p className="text-xs text-stone-400">{obj.style}</p>
              </div>
            ))}
          </div>
          <p className="text-xs text-stone-400 mt-4">
            {!extractionResult.objects[0]?.image_url &&
              "Demo mode: set OPENAI_API_KEY in backend/.env to generate real sticker images."}
          </p>
        </section>
      )}
    </div>
  );
}
