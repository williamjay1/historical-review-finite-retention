# Elsevier CAS LaTeX build

Date: 26 October 2026. Class: `cas-dc.cls` version 2.4 from `els-cas-templates.zip`
(Editeur Elsevier CAS bundle). Engine: pdfLaTeX (MiKTeX), three passes.

## Files

- `ESWA_Manuscript_cas.tex`: manuscript source in the CAS double-column template.
- `ESWA_Manuscript_cas.pdf`: compiled PDF, 12 content pages plus a one-page
  Highlights sheet produced by the class.
- `cas-dc.cls`, `cas-common.sty`, `cas-model2-names.bst`: unchanged template files.
- `figs/figure1_storage_task.pdf`, `figs/figure2_online_age.pdf`: vector figures
  used by the `figure*` environments.

## Structure

The manuscript uses the template front matter: `\title`, author, `\cormark`,
`\ead`, `\credit`, `\affiliation`, `\cortext`, `abstract`, `highlights`,
`keywords`, `\maketitle`, numbered `\section` and `\subsection`, four `table*`
environments with booktabs rules, two `figure*` environments, equation
environments, `thebibliography` with 20 numbered entries in first-appearance
order, `\printcredits`, and two `\section*` declarations (data and code
availability, generative AI use) immediately before the references.

## Compilation

```text
pdflatex ESWA_Manuscript_cas.tex
pdflatex ESWA_Manuscript_cas.tex
pdflatex ESWA_Manuscript_cas.tex
```

No undefined citations or references remain after the third pass.

## Checks

- Page count: 12 content pages; PDF reports 13 pages including the highlights page.
- All 20 references rendered and numbered [1] to [20] in first-appearance order.
- Tables 1 to 4 render at full width on pages 6, 6, 7 and 8 with no text overflow.
- Figures 1 and 2 render at full width on pages 7 and 9; no label overlap.
- Remaining overfull boxes after typesetting: one 5.6 pt overfull box in the
  conclusion paragraph; no other overfull box in the body.
- Author block: name, e-mail, affiliation and CReDiT roles are taken from the
  author profile; add any additional co-authors before submission.

## Scope

The body text, numbers, tables, figures, data statement, AI declaration and
references match the Word manuscript. The LaTeX source is a typeset version of
the same content, not a separate version with different results.
