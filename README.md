# GLITCH ASE 2022: artifact-first reproduction and extension

[Open in Colab](https://colab.research.google.com/github/SimoneRodriguess/glitch-cloud-security/blob/main/COLAB.ipynb) · [Research paper](paper/main.pdf) · [Measured results](results/REPORT.md)

Base paper: N. Saavedra and J. F. Ferreira, **GLITCH: Automated Polyglot Security Smell Detection in Infrastructure as Code**, IEEE/ACM ASE 2022, DOI [10.1145/3551349.3556945](https://doi.org/10.1145/3551349.3556945).

This is a standalone personal research repository. It uses the original author artifact, not the current GLITCH implementation. No Ansible playbook, Chef recipe, or Puppet manifest is executed: only static parsing and smell analysis are performed. Ruby Ripper reads Chef source; it does not execute recipes.

## Verified artifacts

- Complete author replication image: Figshare **version 2**, [10.6084/m9.figshare.19726603.v2](https://doi.org/10.6084/m9.figshare.19726603.v2).
- Image size: **1,819,003,392 bytes**, published MD5 `d9de60550dc558ad227ab14ceef64654` verified locally.
- SHA-256: `db9455021b1664e4d9fae2a784d3f71d4320f070ed3f8fd60c03af7ab8496e31`.
- Embedded GLITCH source commit: `91831ed97abc1379d8c3db9dacb86b40d09508f9`.
- Embedded, installed Puppet dependency: **puppetparser 0.1.3** egg. The earlier source directory is removed by a Docker layer; we use the actual final installed egg, not a newer parser.
- Oracle scripts and majority-vote annotations are present for **Ansible 81, Chef 80, Puppet 80** scripts.
- Native GLITCH source is recovered from Docker layers, applying whiteouts and allowing only selected regular files. Arbitrary archive paths and symlinks are not extracted.
- Zenodo `10.5281/zenodo.6670081` archives GLITCH **v1.0.0 source**, not the entire replication package. It is **not** the measured baseline.
- `data/source-revision.json` preserves the archived tool revision without embedding another Git repository.

The artifact's old README SHA1 refers to a different image version; version-2 Figshare metadata is the checksum authority here.

## Local setup

```bash
git clone https://github.com/SimoneRodriguess/glitch-cloud-security.git
cd glitch-cloud-security
uv venv .venv --python 3.10
uv pip install --python .venv/bin/python -r requirements.txt
uv pip install --python .venv/bin/python --no-deps -e artifact/GLITCH
.venv/bin/python prepare_data.py
.venv/bin/python -u -m glitchstudy.baseline
.venv/bin/python -m pytest -q
.venv/bin/python -u -m glitchstudy.extension development
.venv/bin/python -m glitchstudy.extension freeze
.venv/bin/python -u -m glitchstudy.extension test
.venv/bin/python -m glitchstudy.audit
.venv/bin/python -m glitchstudy.report
```

Python 3.10, CPU, and Ruby with Ripper are sufficient. The native macOS Ruby 2.6.10 is used and recorded. `glitchstudy` automatically loads the original Puppet egg. No Docker daemon, amd64 emulation, GPU, or paid Colab runtime is required. Using a newer Ruby/Python can change parsing, so all predictions are compared with author-stored outputs rather than assuming equivalence.

The original tool, parser, annotations, and 240 of the 241 oracle scripts are included. One original Chef sample embeds an RSA private key: it is intentionally excluded from this public repository and ignored by Git. `prepare_data.py` restores the exact sample locally from the authors' checksum-verified 1.82 GB image if missing. Result text redacts private-key payloads without changing file/line/category detections or numerical scores. The original measured results and source checksums remain available. This repository is public for academic review.

On Ubuntu/Colab, install Ruby if absent: `apt-get update && apt-get install -y ruby`. Verify with `ruby -rripper -e 'puts "Ripper OK"'`. The report generator forces a non-interactive plotting backend for subprocess compatibility with Colab.

## Evaluation scope and protocol

1. Run **all 241 labeled oracle scripts**, not a selected easy subset, with both original improved and SLIC/SLAC-like configurations.
2. Parse each listed oracle file individually with the original parser and unknown block type. This guarantees enumerated-file coverage instead of assuming the old folder traversal visits flat Chef oracle files.
3. Preserve raw predictions. Verify an independent scorer against the original author's unmodified metric scripts.
4. Preserve the original technology-specific matching: Ansible matches source-line content; Chef allows file-level matching for weak crypto/integrity; Puppet allows file-level matching for weak crypto/IP binding. Also report native exact-line sensitivity separately.
5. Treat “No smell” as the paper's separate file-level class, not as an extra line-level smell. Hard-coded password/user subtype reports are not additional categories in the nine-smell scores, but still affect the original no-smell logic.
6. Fix a deterministic file-disjoint 50/50 development/test partition **before inspecting individual error cases and implementing the extension**. The full oracle remains a reproduction benchmark; extension generalization is judged on the reserved test files. This is not a preregistered external study, and files may be correlated by originating project.
7. Choose the extension from documented and observed baseline errors, not by optimizing against reserved test labels. Freeze the rule before scoring test outcomes. Report any regressions and unchanged smell categories.

This reproduces the paper's **accuracy evaluation**, not its full 196,755-script frequency experiment. The latter includes unlabelled data and the authors report about 1,400 minutes for Chef analysis alone; it is not necessary to establish oracle accuracy or measure a targeted correction. No full-corpus rerun is claimed.

## Artifacts

- Original paper: [arXiv v3](https://arxiv.org/abs/2205.14371v3). The authors' paper is linked rather than redistributed here; our report and its source are included.
- `data/artifact-provenance.json`, `data/extracted-manifest.json`: exact source and extracted-file hashes.
- `artifact/GLITCH/`: unmodified analysis source/configurations from the image.
- `artifact/RESULTS/*/oracle-dataset*/`: author data, annotations, and scoring scripts.
- `results/baseline_metrics.csv`: native and author-cached precision/recall/F1/counts.
- `results/strict_baseline_metrics.csv`: exact-line sensitivity where source line numbers are available.
- `results/native_*.csv`, `results/authors_*.csv`: independently measured and cached predictions, distinctly labeled.
- `results/official_scorer_*.txt`: original scorer output on the native run.
- `results/development_errors_*.csv`: only development-file errors exposed for rule design.
- `results/split_manifest.csv`: frozen partitions and source hashes.
- `results/baseline_provenance.json`: versions, parse coverage, scorer checks and prediction-set comparisons.

Original GLITCH and replication artifact are GPL-3.0+. Attribution and source licenses are retained. Any extension built upon the tool is supplied under compatible GPL-3.0+ terms. Replace author/affiliation placeholders and follow institutional AI-assistance disclosure requirements before submitting a research report.

## Completed results and submission artifacts

- `paper/main.pdf`: compiled IEEE conference-format report; official `IEEEtran` class, Times-compatible text/math, standard class margins and numeric IEEE references.
- `results/REPORT.md`: measured baseline fidelity and correction results.
- `glitchstudy/command_rule.py`: the frozen command-aware visitor and naive ablation.
- `results/extension_test_metrics.csv`: primary held-out results, separated from the full-oracle descriptive results.
- `results/rule_freeze.json`, `results/AUDIT.json`: pre-test rule freeze and independent checks.
- `PRESENTATION_GUIDE.md`: numerical results, concepts and defense questions.
- `COLAB.ipynb`: free-tier CPU workflow. Open the notebook using the link above; it downloads this public repository automatically, creates the Python environment and installs Ruby if needed. No manual ZIP upload or GPU is required.
- `REPOSITORY_MANIFEST.json`: checksums of source, artifacts and measured deliverables in this repository.

The complete baseline output matches the authors across all six technology/configuration combinations. The correction targets command-embedded administrative MySQL users, **not** entropy-based secret filtering. On 40 reserved Chef scripts, precision improves 87.50%→91.67%, recall 43.75%→68.75%, and F1 58.33%→78.57%, with four additional true positives and no new false positives. Ansible and Puppet scores remain unchanged.

These are bounded oracle results, not universal security or production-cloud guarantees. The paper already describes this limitation; describe the contribution as its implementation and measured correction. The frozen rule rejects silent post-test edits.

To rebuild the PDF using a standard TeX installation:

```bash
cd paper
latexmk -pdf main.tex
```

Otherwise upload `paper/main.tex`, `paper/generated.tex`, `paper/references.bib` and `paper/chef_holdout.png` to Overleaf, or use a standard local TeX installation. A venue-specific IEEE template or page limit may differ from this generic conference format.
