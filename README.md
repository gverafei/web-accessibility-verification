# Automated Verification of Dynamic Web Pages Using Decision Language Models for Web Accessibility Remediation

This repository accompanies the **MethodsX** research article **Automated Verification of Dynamic Web Pages Using Decision Language Models for Web Accessibility Remediation**. It contains the implementation, case-level evidence, model and human decisions, analysis scripts and editable diagrams.

The study includes **534 cases**: 69 acquired, 257 patched and 208 regenerated interfaces from 70 source domains, with 1,068 human judgments.

## Quick start

```sh
git clone https://github.com/gverafei/web-accessibility-verification.git
cd web-accessibility-verification
python -m http.server 5088 --bind 127.0.0.1
```

Open <http://127.0.0.1:5088/supplementary/>. The catalogue links each case to its reference and target images, evaluated image groups, generating model, model outputs and human decisions.

## Folder organization

```text
web-accessibility-verification/
|-- README.md                     Usage and reproduction instructions
|-- requirements.txt              Python dependencies
|-- MANIFEST.sha256.json           File checksums
|-- analysis/                     CSV/JSON results and Python-generated plots
|-- contracts/
|   |-- protocol.json             Category contracts and typed questions
|   `-- requests/                 Executable request templates for both models
|-- diagrams/                     draw.io diagram sources and PNG exports
|-- scripts/                      Python implementation and analysis
|   |-- verify.py                 Verify files and reconstruct recorded decisions
|   |-- analyze.py                Recompute agreement, timing and cost statistics
|   |-- figures.py                Generate plots and plotted-data tables
|   |-- replicate.py              Validate requests or repeat model inference
|   |-- build_catalogue.py        Rebuild the evidence catalogue
|   |-- build_case_summary.py     Generate the visual case-summary PDF
|   |-- build_manifest.py         Generate the file-checksum manifest
|   `-- ...                       Supporting controller and plotting modules
|-- study/
|   |-- cases.json                Case identities, metadata and final judgments
|   |-- assets/                   Reference/target images and HTML
|   |-- decisions/                Per-case aggregation records
|   `-- exchanges/                Requests, responses, image bindings and timings
`-- supplementary/
    |-- index.html                Evidence catalogue
    |-- instrument.html           Human-review instrument
    |-- catalogue.css             Catalogue styles
    `-- cases/                    Case pages (001-534)
```

## View the evidence

- [Evidence catalogue](supplementary/index.html).
- [Case identities and decisions (CSV)](analysis/case-comparison.csv).
- [Agreement, timing and cost results (JSON)](analysis/comparison.json).
- [Human-review instrument](supplementary/instrument.html).
- [Plots and plotted data](analysis/).
- [Editable diagrams](diagrams/).

## Case identifiers

Case numbers **1-534** identify entries in the catalogue and CSV. The CSV's `review_id` field stores the corresponding original HR identifier. For example, `--cases 60` selects the regenerated interface for `https://www.linkedin.com/` (Case 60).

## Python environment

Use **Python 3.12 or later**. Run the following commands from the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows, activate with `.venv\Scripts\activate`.

## Reproduce the analysis

Verify file checksums, image bindings and recorded decisions:

```sh
python scripts/verify.py
```

Recompute statistics, tables and plots:

```sh
python scripts/analyze.py --output runtime/reproduced-analysis
python scripts/figures.py --output runtime/reproduced-analysis
```

Results are written to `runtime/reproduced-analysis/`. The corresponding published results are in `analysis/`. Plots are exported as PNG, with CSV files for the plotted data.

Rebuild the catalogue and visual case summaries:

```sh
python scripts/build_catalogue.py
python scripts/build_case_summary.py --output runtime/supplementary-cases.pdf
```

## Repeat model inference

Validate the saved request templates locally:

```sh
python scripts/replicate.py --cases 60 --route decisions
python scripts/replicate.py --all --route decisions
python scripts/replicate.py --all --route luna
```

To execute the requests, set `OPENROUTER_API_KEY` in the environment and specify a budget with `--max-usd`:

```sh
python scripts/replicate.py --cases 60 --route decisions --execute --max-usd 0.25
python scripts/replicate.py --cases 60 --route luna --execute --max-usd 0.25
```

Use `--all` in place of `--cases 60` to select the full cohort. The `decisions` route uses Luna Decisions; `luna` uses conventional Luna. New responses, inference durations and costs are written to `runtime/replication/`.
