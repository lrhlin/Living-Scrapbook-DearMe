---
name: scrapbook-template-design
description: Design or update Dear Me scrapbook page styles, their selection previews, and SVG rendering. Use when changing one of the six scrapbook templates or adding another style.
---

# Dear Me scrapbook template design

Design each entry as a composed keepsake page, not a row of image tiles. Treat the sticker artwork as a focal point and plan the writing, image scale, shape, and whitespace together.

## Shared rules

- Work within the existing 900 × 1200 SVG page and 72 px content margins.
- Keep titles, dates, writing, captions, and page numbers legible at normal preview size.
- Choose the size, aspect ratio, frame, and position of each image deliberately; do not default to equal square tiles.
- Balance a clear writing area with image area. A single focal image may sit off-center, including near the right third of the page.
- Use masks intentionally: diamonds, ovals, arches, circles, postcards, and instant-film frames.
- Use one clear decorative motif per style. Leave open space around writing and stickers.
- Repeat the same composition, frame, type treatment, colors, and motif across every page of a multi-page entry.
- Keep decorations in the page header, outer frame, sticker cards, or footer; never place them over the user's text or artwork.
- Make selector previews show the style's actual frame, alignment, colors, and signature motif.

## Style specifications

### Minimal — quiet editorial

Warm white paper, forest-ink headings, hairline rules, generous whitespace, and a left-aligned title. Let a single image anchor the right third of the page; when there are two, balance one rounded editorial frame with a smaller diamond crop. Use typography and spacing as decoration.

### Botanical — pressed garden journal

Soft ivory and sage paper, leafy corner sprigs, green-gray text, and pale botanical mats. Use a vertical oval focal image offset to the right third; when there are two images, pair a smaller oval with a diamond crop. Keep foliage sparse and outside the writing column.

### Celebration — keepsake party page

Cream paper with restrained coral, marigold, and sage accents. Use a short bunting motif near the header, a centered headline, and an asymmetric collage: a tall arch crop paired with a smaller tilted diamond. Keep the page cheerful without covering content.

### Travel — postcard journal

Pale blue-gray paper, a perforated or dashed border, postcard heading, small stamp, and a simple route motif. Give one image a wide landscape postcard frame; for a second image, use a small circular stamp-like crop. Keep the title clear of the stamp.

### Cozy — warm note page

Cream and blush paper, a softly rounded frame, gentle heart or stitched details, and warm brown text. Arrange images as an asymmetric pair of tilted Polaroid cards with room for captions. Keep the page calm and tactile rather than crowded.

### Vintage — archive keepsake

Warm parchment, sepia ink, a fine double frame, centered serif heading, and one small seal or archival mark. Use oval cameo crops with a double outline; pair two images symmetrically when available. Suggest age through paper and ornament, without noisy distress textures.

## Implementation

Keep the six selector previews consistent with the rendered designs. Define composition recipes in the sticker placement helper and masks/frames in the SVG sticker renderer. Keep rendering vector-based so exported SVG and PNG pages match. Unknown or legacy entries use Minimal.
