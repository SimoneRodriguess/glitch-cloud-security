# Project defense guide

## Your central claim

“We reproduced the archived GLITCH accuracy evaluation exactly and extended its IR visitor to detect literal administrative MySQL users embedded in commands. We designed the rule using development errors and froze it before evaluating reserved files. On 40 reserved Chef scripts, F1 improved from 58.33% to 78.57%, recovering four missed occurrences without additional false positives.”

Keep that scope: **one smell, an archived 2022 analyzer, and a small labeled holdout**. Do not claim to detect every cloud vulnerability or to reproduce the complete large-corpus frequency experiment.

## Numbers to memorize

### Baseline reproduction

All six stored outputs match: Ansible, Chef and Puppet × improved and legacy configuration. The complete accuracy oracle has **241 files**. Original improved Chef Admin-by-default counts are **TP=15, FP=1, FN=22** (precision 93.75%, recall 40.54%, F1 56.60%).

Puppet's macro precision is a rounding subtlety: averaging unrounded category scores gives 0.685907→0.69; averaging the paper's rounded category scores gives 0.684444→0.68. Prediction multisets and category counts are identical. Do not hide this arithmetic difference or call it a detector-performance gap.

### Primary reserved Chef test

| | Original | Corrected |
|---|---:|---:|
| Files | 40 | 40 |
| Annotated occurrences | 16 | 16 |
| TP | 7 | 11 |
| FP | 1 | 1 |
| FN | 9 | 5 |
| Precision | 87.50% | 91.67% |
| Recall | 43.75% | 68.75% |
| F1 | 58.33% | 78.57% |

Recall improves **25 percentage points**; F1 improves **20.24 percentage points**. These are percentage-point differences, not relative-percent improvements.

### Full Chef oracle (not independent holdout)

The corrected full-oracle counts are **TP=27, FP=1, FN=10**, precision 96.43%, recall 72.97%, F1 83.08%. This includes development data; do not mix it with the primary test table.

## What the flaw is

The original Admin-by-default detector asks whether a variable/attribute name resembles a user field and its literal value contains an administrative name. It misses something like:

```ruby
execute "dbcheck" do
  command "mysql -uroot -e SELECT"
end
```

The key is `command`, not `user`, even though the command explicitly uses `root`. Other code contains a dynamic password but a literal root user: interpolation elsewhere does not make that user dynamic. Some Ruby command blocks survive as opaque IR source slices, so the extension uses their retained source locations too.

The rule recognizes MySQL-family executables and literal `-uroot`, `-u root`, `--user=root`, or `--user root` options before the SQL payload. It does not run commands or resolve runtime variables. Quoted mentions such as `echo 'mysql -uroot'` are not treated as database execution.

## What you need to understand

I cannot infer your existing knowledge from generated project files. Make sure you can explain:

1. **IaC:** declarative/procedural scripts that configure infrastructure; Ansible YAML, Chef Ruby, Puppet DSL.
2. **AST/IR:** the parser turns syntax into structured nodes; the IR lets one detector process several languages.
3. **Visitor:** traversal that applies rules to variables, attributes, conditions and atomic units.
4. **Lexical analysis:** tokenization recognizes command/options without executing the string. This is bounded, not full shell interpretation.
5. **Precision:** TP/(TP+FP). **Recall:** TP/(TP+FN). **F1:** 2TP/(2TP+FP+FN).
6. **Ground truth:** author annotations, not “whatever our detector reports.” A smell is not a proven exploit.
7. **Reproduction versus extension:** reproduce the whole original oracle first; design on development files; freeze; then score reserved test files.
8. **Matching protocol:** original Ansible uses line-content matching; Chef/Puppet mostly use exact lines with limited exceptions. Admin-by-default in Chef uses exact lines.

## Common examiner questions

**Why this paper instead of the previous one?** Original code, installed parser, configurations, oracle files, annotations and stored predictions are available. We matched the actual outputs instead of guessing missing preprocessing.

**Is it cloud security?** IaC controls cloud-server and service configuration; hard-coded users and administrative command execution relate to least privilege. This is configuration-security static analysis, not network intrusion detection.

**What did you invent?** A bounded command-aware extension of the archived IR visitor, with source recovery for opaque command slices and measured held-out evidence. GLITCH, parsing, shell tokenization and least privilege are not inventions here. The paper already discusses this limitation.

**Did you tune against the test set?** The split was frozen before individual error inspection. The rule was designed from development errors and synthetic boundary tests, then hashed before reserved-test evaluation. The freeze is in `results/rule_freeze.json`.

**Why not a simple regex?** The naive mysql/root substring ablation has ten false positives on the reserved Chef files versus one for the corrected analyzer, because mentions and unresolved values can contain those strings without a literal root command.

**Is the result statistically generalizable?** Not established. The reserved Chef files contain only 16 target occurrences, and related source projects may appear in both partitions. We claim a measured internal holdout improvement, not production-cloud validation.

**Why are some misses left?** The rule does not infer users from runtime variables, arbitrary wrappers, option files or full shell/Ruby semantics. Original duplicated oracle labels are retained for faithful reproduction.

**Can root be legitimate?** Yes. The smell is a review signal about privileges, not proof of exploitation or a reason to automatically remove required provisioning privileges.

## Suggested 8–10 minute presentation

1. Cloud IaC security problem and ASE 2022 base paper.
2. Original GLITCH architecture: three parsers → common IR → security visitor.
3. Verified artifacts, source commit and exact baseline reproduction.
4. Development failure example: command-embedded root user.
5. New rule, negative examples and unchanged original detectors.
6. File-disjoint split and pre-test source freeze.
7. Primary reserved Chef table and naive-ablation chart.
8. Audit/tests, scope limits and future project-disjoint validation.

## Live demo

```bash
cd glitch-cloud-security
.venv/bin/python -m pytest -q
.venv/bin/python -m glitchstudy.audit
```

Show `results/REPORT.md`, `results/rule_freeze.json`, `results/chef_holdout.png` and the code in `glitchstudy/command_rule.py`. Dataset download is not needed for these demos because selected verified artifacts are already present. Rerunning the same holdout is not a newly independent validation experiment.

Replace manuscript author details, personally review the implementation and results, and follow your institution's AI-assistance disclosure policy before submission.
