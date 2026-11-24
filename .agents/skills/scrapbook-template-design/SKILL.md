---
name: scrapbook-template-design
description: Design or update Dear Me scrapbook page styles, their selection previews, and SVG rendering. Use when changing one of the six scrapbook templates or adding another style.
---

# Dear Me scrapbook template design

Design each entry as a printed keepsake page. Keep the writing readable, give stickers a clear place on the page, and make every style recognizable from both its preview card and its exported SVG.

## Shared rules

- Work within the existing 900 × 1200 SVG page and 72 px content margins.
- Keep title, date, text, sticker labels, and page numbers legible at normal preview size.
- Use one clear decorative motif per style. Leave open space around writing and stickers.
- Repeat the same frame, type treatment, colors, and motif across every page of a multi-page entry.
- Keep decorations in the page header, outer frame, sticker cards, or footer; never place them over the user's text or sticker artwork.
- Make the selector preview show the style's actual frame, colors, alignment, and signature motif.
- Keep the six styles distinct through composition and details, not palette alone.

## Style specifications

### Minimal — quiet editorial

Warm white paper, forest-ink headings, hairline rules, generous whitespace, left-aligned title, and clean square-cornered sticker areas. No ornamental flourishes. Use typography and spacing as the decoration.

### Botanical — pressed garden journal

Soft ivory and sage paper, leafy corner sprigs, a delicate organic frame, green-gray text, and pale botanical sticker mats. Keep foliage sparse and outside the writing column; avoid a dense floral wallpaper effect.

### Celebration — keepsake party page

Cream paper with restrained coral, marigold, and sage accents. Use a short bunting or confetti motif near the header, a centered headline, rounded sticker mats, and small celebratory marks. Keep the page cheerful without covering content.

### Travel — postcard journal

Pale blue-gray paper, a perforated or dashed border, postcard heading, small stamp, and a simple route or compass motif. Keep the title and date clear of the stamp; use cool slate text and sand-blue sticker mats.

### Cozy — warm note page

Cream and blush paper, softly rounded frame and sticker mats, gentle heart or stitched details, and warm brown text. Center the heading when space allows. Keep the page calm and tactile rather than crowded.

### Vintage — archive keepsake

Warm parchment, sepia ink, a fine double frame, centered serif heading, and one small seal or archival mark. Use muted ochre sticker mats and symmetrical details. Suggest age through paper and ornament, without noisy distress textures.

## Implementation

The style selection belongs in `backend/app/static/index.html` and `scrapbook.css`. Keep each selector preview consistent with its rendered design. Define palette and layout choices in `backend/app/services/scrapbook.py`; render decorations as SVG shapes so exports match the preview. Keep unknown or legacy entries on the Minimal style.
