# Living Scrapbook · Dear Me

Little moments, beautifully remembered. Turn photos into illustrated stickers with OpenAI or IBM Bob, then combine them with your words in automatically arranged scrapbook pages.

## Try it locally

```bash
./start-local.sh
```

Open **http://127.0.0.1:8000**. The launcher installs Python dependencies in `backend/venv`, installs Bob Shell and the SVG renderer in `tools/node_modules`, and starts FastAPI.

Requirements: Node.js 24+ and Python 3.11–3.13. Set `DEARME_PYTHON=/path/to/python` to select Python or `DEARME_PORT=8001` to change the port. The launcher also detects a compatible bundled Codex Python.

Place your OpenAI API key as plain text in **oaikey.txt** at the repository root. For IBM Bob, place an Inference-scoped key in **bobkey.txt**. You can also set `OPENAI_API_KEY` and `BOB_API_KEY` in `backend/.env`. The server reads the selected provider's key; these credential files are covered by `.gitignore`.

On a new machine, run `tools/node_modules/.bin/bob chat` to review the Bob Shell license and complete setup.

## Create a scrapbook entry

1. Open **My scrapbook** and select stickers from your library or the supplied samples.
2. Add your words, a date and an optional title.
3. Click **Add**. The app wraps the text, arranges stickers in rows and continues onto additional pages as needed.

You can create entries with words, stickers or both. The composer supports up to 50 stickers and 20,000 characters per entry, with local page layout.

Choose Minimal, Botanical, Celebration, Travel, Cozy or Vintage for the page design. You can write your story yourself or use **Draft my story** to turn notes into editable text with Bob. Personal writing style uses 1–5 journal samples for that draft.

Saved entries appear under **Pages to come back to**. Open one to browse its pages, read the text, download a page as SVG or PNG, or download the complete entry as a ZIP. Each entry keeps its text, sticker snapshots and exports in `backend/uploads/scrapbook`.

Use **Use in scrapbook** in the Studio or sticker library to select a sticker for your next entry. The composer also includes sticker search and filters for your creations and samples.

## Choose your sticker maker

1. **Choose photos.** Upload up to three JPEG, PNG or WebP photos, or choose a supplied example.
2. **Pick a sticker maker.** **OpenAI · raster PNG** is the default. Switch to **IBM Bob · vector SVG + PNG** in the Studio's setting. Your browser remembers the choice.
3. **Make it yours.** Pick a subject and a style: paper cut, soft illustration or ink sketch.
4. **Create the artwork.** OpenAI edits the reference into a detailed transparent PNG with a white sticker border. Bob writes SVG artwork; local code adds its border and renders a PNG.
5. **Keep and reuse.** Download the sticker or select it for a scrapbook entry. Both formats work in all page styles. Photos, stickers and generation details are saved in `backend/uploads/studio`.

OpenAI uses **gpt-image-2.6-sunburst**, high quality, at **1024 × 1024** pixels. Request one to three variations per photo; usage is charged to your OpenAI API account. Bob can illustrate up to three subjects per photo, with a default task spending limit of **0.5 Bobcoins**. The app queues up to three photos and processes one at a time. Results show the model or provider, elapsed time and reported usage.

## How it is built

```text
Photo → OpenAI bordered PNG → sticker library
Photo → Bob SVG illustration → shape-based border → PNG → sticker library
Words + selected stickers → local page layout → saved scrapbook → SVG / PNG / ZIP
```

FastAPI serves the local HTML, CSS and JavaScript interface, handles background sticker jobs, and stores the library and scrapbook on disk. The selected provider creates stickers; Bob handles story drafts and chapter narratives. Scrapbook SVG exports embed raster stickers as PNG data and retain Bob stickers as vector shapes.

| Location | Responsibility |
| --- | --- |
| `backend/app/static/` | Scrapbook composer, page viewer, Studio and library |
| `backend/app/services/scrapbook.py` | Text wrapping, page layout, sticker snapshots and exports |
| `backend/app/services/bob_client.py` | Bob Shell requests, streamed responses and usage |
| `backend/app/services/object_extractor.py` | Illustration prompts and SVG/PNG workflow |
| `backend/app/services/openai_stickers.py` | Reference image edits and transparent PNG stickers |
| `backend/app/services/svg_stickers.py` | Vector validation and border generation |
| `backend/app/services/studio_jobs.py` | Generation queue and saved jobs |
| `tools/render-svg.cjs` | PNG rendering with resvg |
| `artifacts/bob-sticker-examples/` | Reference photos, Bob illustrations and source credits |

Explore the API at **http://127.0.0.1:8000/docs**. The webpage uses `/api/v1/scrapbook` for entries and stickers, and `/api/v1/studio` for generation jobs. `POST /api/v1/extract/` serves the original client.

The backend also offers journal entries, connections based on shared locations, people and tags, style preferences learned from editing actions, and living chapters that group related memories. Chapter summaries use Bob when configured and a local template otherwise. Journal entries and style preferences use server memory; the Studio and scrapbook use files. The original Next.js interface is in `frontend/`.

## Configuration

Copy `backend/.env.example` to `backend/.env` for overrides:

| Variable | Purpose |
| --- | --- |
| `STICKER_PROVIDER` | Initial Studio provider: openai (default) or bob |
| `OPENAI_API_KEY` | OpenAI key; defaults to reading oaikey.txt |
| `OPENAI_KEY_FILE` | OpenAI key-file path |
| `OPENAI_IMAGE_MODEL` | Image model; default gpt-image-2.6-sunburst |
| `OPENAI_IMAGE_QUALITY` | Image quality; default high |
| `OPENAI_TIMEOUT_SECONDS` | Image request timeout; default 300 seconds |
| `BOB_API_KEY` | Inference-scoped Bob key; defaults to reading bobkey.txt |
| `BOB_KEY_FILE` | Key-file path |
| `BOB_CLI_PATH` | Bob executable; defaults to the pinned local installation |
| `BOB_MAX_COST` | Per-generation Bobcoin limit; default 0.5 |
| `BOB_MAX_TURNS` | Agent turns per task; default 10 |
| `BOB_TIMEOUT_SECONDS` | Generation timeout; default 240 seconds |
| `UPLOAD_DIR` | Data directory; default backend/uploads |
| `MAX_UPLOAD_SIZE_MB` | Upload limit; default 20 MB, with a 25-megapixel image limit |

The demo runs as a single-user workspace at the loopback address `127.0.0.1`.

## Verification

```bash
PYTHONPATH=backend backend/venv/bin/python -m unittest discover -s backend/tests -v
node --check backend/app/static/studio.js
node --check backend/app/static/scrapbook.js
```

The suite checks provider response parsing, SVG validation and borders, photo uploads, the generation queue, PNG rendering, multi-page layout, saved entries and downloads. AI responses are supplied by test fixtures.

## Challenge context

Built for the AI Builders Challenge with IBM Bob, organized by BeMyApp. Bob provides SVG illustration and scrapbook writing; OpenAI provides the default raster sticker option. Codex was used for implementation and verification of the local Studio and scrapbook interface.
