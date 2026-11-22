# 📖 Living Scrapbook · Dear Me

> *Little moments, beautifully remembered — and intelligently connected.*

An AI-powered personal scrapbook that doesn't just store your memories — it discovers the hidden threads between them, learns your aesthetic, transforms real-world objects into handcrafted materials, and grows alongside your life story.

---

## ✨ What Makes This Different

Most journaling apps are static. You write, you save, you scroll back someday. Living Scrapbook is different: it treats your memories as a living, breathing graph — where today's coffee shop photo might secretly belong to the same story as a friend you met three months ago.

---

## 🧠 Core Features

### 1. Memory Graph — AI Discovers the Connections You've Forgotten

> *Your memories are connected. We help you see how.*

Ordinary journals are one page per day. But life isn't linear — it's layered.

Living Scrapbook builds a continuously growing **Memory Graph** that links your entries across time by:

- **Location** — the same coffee shop appearing months apart
- **People** — the same friend appearing in different contexts
- **Themes** — a repeated feeling, activity, or intention
- **Text & tags** — keywords and emotions that echo across entries

**Example nudge from the AI:**
> *"The café photo you took today and the friend gathering you recorded two months ago share the same location. Would you like to group them into a themed scrapbook?"*

This transforms the scrapbook from a recording tool into a **tool for self-discovery** — surfacing the recurring chapters of your life that you might never have noticed yourself.

---

### 2. Aesthetic Learning — AI Learns *Your* Style, Not Just Your Prompts

> *Stop describing what you like. Just create, and we'll remember.*

Generic AI image tools generate layouts from prompts. The problem: they don't know *you*.

Living Scrapbook includes a **Personal Visual System** with a feedback loop:

| User Behavior | What the AI Learns |
|---|---|
| Consistently deletes large stickers | Prefers minimalism and negative space |
| Repositions photos into irregular arrangements | Likes a collage/scrapbook aesthetic |
| Repeatedly picks low-saturation palettes | Prefers muted, vintage tones |
| Rearranges text into smaller blocks | Values visual breathing room over density |

Every edit you make is a signal. Over time, the system builds a **structured style profile** — not by training a model, but through style parameters, edit history, and explicit feedback. Future layout suggestions will feel like they were made *for you*, because they were.

---

### 3. Real Objects → Scrapbook Materials — The Wow Moment

> *Upload a photo. Walk away with handcrafted stickers.*

This is the feature designed to create immediate delight.

**How it works:**

1. User uploads an ordinary photo — a café table, a train ticket, a bouquet of flowers
2. AI identifies individual objects within the photo (coffee cup, receipt, candle, pastry)
3. Each object is extracted and transformed into an **editable scrapbook element**:
   - Watercolor stickers
   - Collage cutouts
   - Line-art illustrations
   - Vintage-style ephemera

**What makes this powerful:** these aren't flat image exports. Each element is **independently draggable, scalable, and reusable** across multiple pages.

**Natural language editing:**
> *"Turn the coffee cup into a watercolor sticker, put the receipt in the bottom-left corner, and make everything feel like a vintage journal."*

The AI modifies only the elements you describe, leaving the rest of your layout untouched. This upgrades the experience from "AI image generation" to a **design tool that understands objects and creative intent**.

---

### 4. A Scrapbook That Grows With You — Living Chapters

> *Traditional journals are finished the moment you close them. Yours isn't.*

Living Scrapbook introduces the concept of **Living Chapters** — long-form stories that the AI assembles automatically from related entries over time.

**Example:**

| Date | Entry |
|---|---|
| January | *"This year I want to learn guitar."* |
| March | Records the first song practiced through |
| June | Uploads photos from a first-ever live performance |

The AI recognizes these entries as part of the same long-running story. It automatically generates a chapter page titled something like **"From First Chord to First Stage"** — a cohesive narrative scrapbook page built from entries spread across months.

Living Chapters can:
- **Reorganize past entries** from a new angle as the story develops
- **Surface connections** between entries that weren't obvious at the time
- **Grow retroactively** — adding depth to old memories as new ones are created

Your scrapbook doesn't just grow by adding new pages. It deepens.

---

## 🗺️ System Architecture (Planned)

```
┌─────────────────────────────────────────────────────┐
│                   User Interface                    │
│         (Scrapbook Editor · Memory Feed)            │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│                  AI Layer                           │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ Memory Graph │  │ Style Learner│  │  Object   │ │
│  │  Engine      │  │  (Aesthetic  │  │ Extractor │ │
│  │              │  │   Profile)   │  │           │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │          Living Chapter Generator            │  │
│  └──────────────────────────────────────────────┘  │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│                  Data Layer                         │
│    Entries · Photos · Tags · Edit History ·         │
│    Style Parameters · Memory Graph Nodes            │
└─────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack (Planned)

| Layer | Technology |
|---|---|
| Frontend | React / Next.js |
| Drag & drop editor | Fabric.js or Konva.js |
| AI vision (object extraction) | GPT-4o Vision / Google Vision API |
| Image style transfer | Stable Diffusion / DALL·E |
| Memory Graph | Graph database (Neo4j or similar) |
| Style learning | Structured style parameter store + edit history |
| Backend | Node.js / Python FastAPI |
| Storage | Cloud object storage (S3-compatible) |

---

## 🚀 Getting Started

> ⚙️ **Project is in early design stage.** Code and setup instructions will be added here as development progresses.

```bash
# Clone the repository
git clone https://github.com/lrhlin/Living-Scrapbook-DearMe.git
cd Living-Scrapbook-DearMe

# More setup steps coming soon...
```

---

## 🗓️ Roadmap

- [ ] **v0.1** — Core editor: drag-and-drop photo layout, basic tagging
- [ ] **v0.2** — Object extraction: upload photo → generate individual stickers
- [ ] **v0.3** — Style learning: track edit history, build aesthetic profile
- [ ] **v0.4** — Memory Graph: auto-link entries by location, people, theme
- [ ] **v0.5** — Living Chapters: auto-generate long-form story pages
- [ ] **v1.0** — Full product: all systems integrated, natural language editing

---

## 💡 Design Philosophy

> *A journal should know you as well as an old friend does.*

We believe:
- Memory is not linear — it's a web
- Personal taste cannot be captured in a single prompt — it's built through lived choices
- The most meaningful creative tools are the ones that learn alongside you
- A scrapbook's value should grow over time, not be fixed on the day it's written

---

## 🤝 Contributing

This project is in its earliest stage. Ideas, feedback, and contributions are very welcome.

Feel free to open an [Issue](https://github.com/lrhlin/Living-Scrapbook-DearMe/issues) to share thoughts on the concept or suggest features.

---

## 📄 License

MIT License — see [`LICENSE`](LICENSE) for details.

---

*Made with memory, intention, and a little bit of AI magic. 🫧*
