# Dear Me · Next.js interface

This interface provides journal entry forms, memory connections, style preferences, Bob sticker generation and living chapters. It connects to the FastAPI backend through `src/lib/api.ts` and manages client state in `src/lib/store.ts`.

For the scrapbook composer, page viewer and sticker library, run `./start-local.sh` from the repository root and open **http://127.0.0.1:8000**.

## Run this interface

Start the backend with `./start-backend.sh` from the repository root. In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**. Configure your Bob key using the instructions in the [project README](../README.md).

## Source layout

- `src/app/`: application page, layout and shared styles.
- `src/components/`: journal, graph, style, sticker and chapter panels.
- `src/lib/api.ts`: backend requests and response types.
- `src/lib/store.ts`: client state and panel actions.

## Checks

```bash
npm run lint
npm run build
```
