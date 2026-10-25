# Table artwork QA

The final source contains four main tables and five supplementary tables. All
nine are rendered independently at exactly 183 mm PDF/SVG canvas width, with
height determined by their source rows and necessary header wrapping. Table
titles/captions are outside the artwork in `table_captions.md`. No manuscript
source was changed by the artwork generator.

The 150-dpi previews for Tables 1–4 and S1–S5 were actually opened and inspected
at their native resolution. Table 3 was re-inspected after the denominator was
kept with its slash on the second header line; Table S2 was also re-inspected
after that final generator run. No text overlap, text/rule intersection,
clipping, cramped header or missing cell was observed. The retained design is
white, three horizontal black rules, one header band, Arial 7 pt with bold
headers, left-aligned row labels and right-aligned numerical columns. There
are no vertical rules, body shading or decorative elements.

Deterministic checks separately establish:

- All 285 editable SVG cells preserve the exact source strings after whitespace
  normalization; wrapping changes no word, punctuation or numerical value.
- Every text bounding box remains inside its allocated cell. Pairwise text
  boxes do not overlap, and no text bounding box meets a horizontal rule.
- All nine PDFs contain embedded TrueType fonts, one page, and zero image
  objects. Their page width is exactly the 183 mm target.
- Every high-resolution PNG records 1,200 dpi; every preview records 150 dpi.
  Integer raster dimensions differ from the nominal physical size by less than
  one pixel. No interpolation is used to manufacture resolution.
- Source hashes before and after generation agree. Per-table geometry and
  embedded-font receipts accompany the files.

The actual cell strings, rather than visual transcription of small numbers,
are the authority for numerical fidelity. SVG text remains editable; the Word
manuscript can independently retain its native editable tables.
