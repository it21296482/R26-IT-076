# R26-IT-076 academic information website

This is a self-contained HTML and CSS website for the research project **AI-Powered Stock Market Insight Generator for the Colombo Stock Exchange**.

It documents all four individual research contributions, project milestones, produced documents, presentations, team members, supervision, and contact details. It is intentionally separate from the MERN product dashboard. No database, model service, or API credentials are needed to run this academic website.

## Research coverage and sources

- Component 1 / IT21296482: market modelling, expected-price deviation, volume-adjusted anomaly scores, calibration, and archived validation evidence. Existing content is preserved.
- Component 2 / IT21471162: financial-report understanding and prompt evaluation. Existing content is preserved.
- Component 3 / IT22065308: hybrid financial-news sentiment classification, methodology, evaluation equations, and the reported 60-headline comparison. Added from `academic-website (2).zip`.
- Component 4 / IT22547088: explainable risk classification with stock features, gold, oil, and VIX; methodology, archived findings, and limitations. Added from `academic-website-Ruchiini.zip`, including its supplied thesis PDF.

Component 3's package did not include an individual thesis PDF, so its available research proposal is linked and labelled as a proposal. Reported member evaluation figures have not been independently rerun for this website. Component 4's standalone prototype stack is distinguished from the integrated application. Upcoming assessment milestones remain labelled upcoming; website completion does not imply that all research evaluations are complete.

## Run locally

Live archive: https://r26-it-076-research.netlify.app/

Component 2's update adds the ten-prompt comparison, weighted evaluation formula,
selected prompt, technology summary, and downloadable methodology and evidence.
The reported benchmark limitations remain visible. Its styles are in
`benchmark.css`. Netlify is updated by manual static-site upload, not by an
automatic GitHub deployment.

Open `index.html` directly in a browser, or serve this directory with any static web server. No build tools or JavaScript runtime are required. An optional local preview command is:

```bash
python3 -m http.server 4173
```

Then open `http://127.0.0.1:4173`.

## Included source

- `index.html` - website structure and research content
- `styles.css` - responsive visual design
- `static-controls.css` - CSS-only component selection, milestones, responsive menu, and motion
- `component-additions.css` - scoped styling for the added research sections and accessible responsive tabs
- `assets/documents/` - thesis drafts and editable PP1 and PP2 presentation artefacts
- `architecture.html` and `architecture.css` - themed system architecture and design rationale

## HTML and CSS only

Component and milestone selection use native radio inputs and CSS. The mobile menu uses a native checkbox. Research expanders use HTML details/summary. Use the browser Find command to search documents. Motion and the progressive scroll indicator use CSS, with reduced-motion support and a static fallback. No JavaScript files, scripts, event handlers, framework, or backend are used by this website. Downloadable Python, JSON, CSV and Markdown files are retained as research evidence, not website code.
