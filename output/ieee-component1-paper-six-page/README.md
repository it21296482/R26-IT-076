# Six-Page Component 1 Research Paper

This is the condensed publication-format version of the Component 1 manuscript.
The nine-page manuscript and its original source package remain unchanged.

## Format and Contents

- Exactly six pages, including authors, abstract, figures, tables and references.
- Unmodified IEEEtran conference class, standard two-column body and margins.
- Standard 10-point body; no global font reduction, margin changes or page scaling.
- Six original figures, four tables and thirteen references retained.
- Last-page columns manually aligned; the final discussion paragraph is kept intact.
- Focus remains IT21296482's work, with other components credited as contributions.
- The abstract is self-contained, with technical abbreviations introduced in the body.

The source archive also includes the companion Markdown document,
`Component_1_Conclusion_Formulas_and_Improvements_IT21296482.md`. It contains a
plain-English conclusion, worked formulas, evidence limitations, comparison with
the two supplied presentation examples, and proposed residual-pattern experiments.
Proposed experiments are not presented as completed model improvements.

`main.tex` is the editable manuscript. Compile it with a normal LaTeX distribution,
Tectonic or Overleaf. `IEEEtran.cls` is the unmodified CTAN class. The six figures
are provided as vector PDFs with PNG review copies in `figures/`.

## Evidence and Reproduction

`build_figures.py` rebuilds figures and checks saved predictions against result
tables. It does not train new models or fetch new prices. `evidence_manifest.json`
records source fingerprints and evaluation scope. When run outside the repository,
set `RESEARCH_REPO` to the original checkout containing `research/component1/`.

```bash
RESEARCH_REPO=/absolute/path/to/R26-IT-076 python3 build_figures.py
tectonic main.tex
```

The archived anomaly labels use full-history quantiles. This retrospective leakage,
two-stock scope, limited positive-label counts, missing neural checkpoints and
unverified pre-target forecast registration remain disclosed. Later runtime upgrades
are not claimed as improvements to the archived metrics. Negative results and
baseline comparisons have not been removed to shorten the paper.

The six-page limit is the requested submission constraint, not a universal limit
for every IEEE publication. Authors should confirm the selected venue's specific
template, author order, review and PDF-validation requirements before submission.
