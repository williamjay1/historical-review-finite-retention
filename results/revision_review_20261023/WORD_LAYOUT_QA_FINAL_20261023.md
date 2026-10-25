# Final Word layout and native-artifact QA

Date: 23 October 2026. Artifact inspected: `manuscript/ESWA_Manuscript.docx`, `manuscript/ESWA_Supplementary.docx`, and `manuscript/ESWA_Cover_Letter.pdf`. Final PDFs were exported with Microsoft Word and inspected as page images at 110 dpi.

The tables in this DOCX use fixed Word column grids and three-line table borders. LibreOffice headless misreads the fixed grid in this particular Word file and stacks table cells. That renderer is therefore not used for the final layout verdict. Microsoft Word renders the same tables at full text width, as verified on pages 7, 8, 9, 10, and 15.

## Page map

| Page | Content | Layout verdict |
|---:|---|---|
| 1 | Title, abstract, keywords, start of Introduction | No overlap or clipping; abstract fits one page |
| 2 to 6 | Introduction, Related work, Materials and methods | Continuous text; headings kept with following text |
| 7 | End of 4.1 and Table 1 | Table 1 full width; 6 columns readable; no cell overflow |
| 8 | 4.2 and Table 2 | Table 2 full width; 5 columns readable; caption kept with table |
| 9 | Figure 1 and Table 3 | Figure 1 at 183 mm; no text overlap; Table 3 full width |
| 10 | 4.4 and Table 4 | Table 4 full width; 6 columns readable |
| 11 | Figure 2 and 4.4 continuation | Figure 2 at 183 mm; labels and legend clear; no clipping |
| 12 to 14 | Discussion, Conclusion, Data and AI statement | No overlap; Data statement and start of AI statement fit on page 14 |
| 15 | End of AI statement, start of References | No overlap; first 15 references complete |
| 16 | References | Remaining 5 numbered entries complete; no truncation |

## Supplementary

| Page | Content | Layout verdict |
|---:|---|---|
| 1 to 4 | S1 to S3, Tables S1 and S2 | Tables full width; equations clear; no clipping |
| 5 | S4, Tables S3 and S4 | Both tables full width; 5 columns readable |
| 6 | S4 continuation, Table S5, S5 | Table S5 full width; no overlap |
| 7 | S5 end, S6, References | Three numbered references complete |

## Counts

- Main manuscript: 16 pages, 4 native tables, 2 figures, 35 native OMML equations.
- Supplementary: 7 pages, 5 native tables, 17 native OMML equations.
- Cover letter: 1 page PDF.
- Figure files: PDF and SVG vector versions plus native 1200 dpi PNG.
- Table artwork: PDF, SVG, and native 1200 dpi PNG previews.
- No text was found overlapping another text object, a data line, or a table border in the inspected Word PDF pages.
- Figure 1b was regenerated only to change the legend label from `Full-if-fits` to `Full if fits`; plotted values and source data are unchanged.
