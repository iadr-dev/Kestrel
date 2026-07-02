# Social banner (Open Graph / Twitter card)

The code in `src/app/layout.tsx` references **`/banner/kestrel-banner.png`** as the
Open Graph and Twitter `summary_large_image`.

- **Current file:** `kestrel-banner.png` (1424 × 752, ~1.91:1 — OG-compliant)
- **Recommended size:** 1200 × 630 px (the OG standard) or any 1.91:1 ratio
- **Keep under ~1 MB** ideally so link-preview crawlers fetch it quickly (current ≈1.1 MB,
  acceptable; compress with e.g. `pngquant`/`squoosh` if you want it leaner).

If you rename or replace it, update `openGraph.images` / `twitter.images` (and the
`width`/`height`) in `src/app/layout.tsx`.

The Gemini generation prompt is in `prompt.md` in this folder.
