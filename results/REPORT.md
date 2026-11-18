# GLITCH: measured reproduction and correction

## Baseline fidelity

**Exact match:** all six author-stored prediction outputs are reproduced natively (3 technologies × 2 configurations). Independent scoring agrees with the original scripts.

All 241 oracle files are enumerated: Ansible 81, Chef 80, Puppet 80. This is the labeled accuracy experiment, not the 196,755-script unlabelled frequency rerun.

| Technology | Published average precision | Published average recall | Native average precision | Native average recall |
|---|---:|---:|---:|---:|
| Ansible | 0.77 | 0.87 | 0.77 | 0.87 |
| Chef | 0.77 | 0.86 | 0.77 | 0.86 |
| Puppet | 0.68 | 0.85 | 0.69 | 0.85 |

**Rounding note:** Puppet's unrounded category precisions average to 0.685907 (displayed 0.69). Averaging the published two-decimal category values gives 0.684444 (displayed 0.68). This one-hundredth macro-average difference does not correspond to different detections: all original prediction multisets and per-category counts match exactly.

## Flaw fixed

The original analyzer misses explicit root database users embedded in command-valued fields and opaque command-block IR source slices. The extension recognizes literal MySQL user options without executing scripts or assuming unresolved variables are root.

## Reserved Chef test results

40 test files, 16 annotated Admin-by-default occurrences. The rule was frozen after development evaluation and before test scoring.

| Method | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| Archived GLITCH | 7 | 1 | 9 | 0.875 | 0.438 | 0.583 |
| Command-aware | 11 | 1 | 5 | 0.917 | 0.688 | 0.786 |
| Naive substrings | 15 | 10 | 1 | 0.600 | 0.938 | 0.732 |

**Measured gain:** 4 recovered true positives, no new false positives; recall +25.00 percentage points, F1 +20.24 percentage points.

Ansible and Puppet oracle results remain unchanged. All unrelated security-smell report sets are preserved. Parser integration tests establish shared rule behavior across the three languages on controlled fixtures.

## Full Chef oracle (descriptive, includes development)

Baseline: TP=15, FP=1, FN=22, P=0.937500, R=0.405405, F1=0.566038.
Corrected: TP=27, FP=1, FN=10, P=0.964286, R=0.729730, F1=0.830769.

Do not present these full-oracle figures as held-out results.

## Verification and caveats

- 15 audit checks pass; 35 automated tests pass.
- Exact archived-source baseline and installed Puppet egg; source/image/partition hashes retained.
- Four Ansible file types produce no IR in the original analyzer; these files remain in the evaluated population. Matching the authors does not prove parser completeness.
- File-disjoint internal holdout, not project-disjoint external validation; only 16 target occurrences in reserved Chef files.
- Original duplicate oracle labels and original content/file-level matching exceptions are disclosed.
- A security smell is not proof of exploitability; root access can be required for legitimate provisioning.
- The rule is bounded and does not resolve runtime users, arbitrary shell wrappers or post-payload user overrides.
- The base paper already discusses this limitation; the contribution is an implementation and measured extension, not a claim of unprecedented discovery.

## Deliverables

- `paper/main.pdf`: IEEE conference-format report.
- `paper/main.tex`, `paper/generated.tex`, `paper/references.bib`: editable manuscript.
- `results/AUDIT.json`, `results/rule_freeze.json`: verification and pre-test freeze.
- `results/extension_test_metrics.csv`: full held-out metrics.
- `results/extension_full_metrics.csv`: descriptive full-oracle metrics.
- `PRESENTATION_GUIDE.md`: defense guide.
