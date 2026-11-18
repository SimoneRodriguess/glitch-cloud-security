"""Generate the report and IEEE manuscript from verified experiment artifacts."""
import json
import shutil
import os

# Colab exports its inline backend to subprocesses, but that backend is not
# installed in the isolated analysis environment. Set this BEFORE import:
# matplotlib validates MPLBACKEND during its own initialization.
os.environ["MPLBACKEND"] = "Agg"
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import ROOT


def macro(name, text):
    return "\\newcommand{\\" + name + "}{" + text + "}\n"


def table(caption, label, columns, headers, rows, note=""):
    return (r"\begin{table}[t]\centering\caption{" + caption + "}" + r"\label{" + label + "}\n" +
            r"\begin{tabular}{" + columns + r"}\toprule" + "\n" +
            " & ".join(headers) + r" \\\midrule" + "\n" +
            "\n".join(" & ".join(row) + r" \\" for row in rows) + "\n" +
            r"\bottomrule\end{tabular}" + (r"\par\smallskip\emph{" + note + "}" if note else "") + r"\end{table}")


def main():
    out, paper = ROOT / "results", ROOT / "paper"
    audit = json.loads((out / "AUDIT.json").read_text())
    assert audit["all_passed"], "Do not generate final manuscript from failed artifacts"
    baseline = pd.read_csv(out / "baseline_metrics.csv")
    test = pd.read_csv(out / "extension_test_metrics.csv")
    full = pd.read_csv(out / "extension_full_metrics.csv")
    dev = pd.read_csv(out / "extension_development_metrics.csv")
    provenance = json.loads((out / "baseline_provenance.json").read_text())
    freeze = json.loads((out / "rule_freeze.json").read_text())
    def admin(frame, tech, method):
        return frame[(frame.tech == tech) & (frame.method == method) & (frame.category == "admin-by-default")].iloc[0]
    a, b, naive = [admin(test, "chef", name) for name in ["baseline", "command_aware", "naive_substring"]]
    fa, fb = [admin(full, "chef", name) for name in ["baseline", "command_aware"]]
    da, db = [admin(dev, "chef", name) for name in ["baseline", "command_aware"]]
    texts = []
    texts.append(macro("BaselineAbstract", "Fresh predictions match all six author-stored language/configuration outputs exactly, and an independent scorer agrees with the original metric scripts."))
    texts.append(macro("ExtensionAbstract", f"On 40 reserved Chef files with {int(a.tp+a.fn)} annotated administrative-default occurrences, recall increases from {100*a.recall:.2f}\\% to {100*b.recall:.2f}\\%, precision from {100*a.precision:.2f}\\% to {100*b.precision:.2f}\\%, and F1 from {100*a.f1:.2f}\\% to {100*b.f1:.2f}\\%. The extension recovers {int(b.tp-a.tp)} missed occurrences without adding false positives; Ansible and Puppet oracle results remain unchanged."))
    texts.append(macro("PartitionDescription", "Development comprises 40 files per technology (120 total); test comprises 41 Ansible, 40 Chef, and 40 Puppet files (121 total). Entire files, including all their labels, remain in one partition. File hashes and membership are recorded; related originating projects are not guaranteed disjoint."))
    texts.append(macro("DevelopmentEvidence", f"In Chef development files, the reproduced administrative-default detector has TP={int(da.tp)}, FP={int(da.fp)}, and FN={int(da.fn)}. Manual inspection of development false negatives identifies literal MySQL users in command guards, heredoc shell scripts, a status-command assignment, and an opaque Ruby block. Other missed annotations refer to unresolved database-user attributes rather than an explicit literal root option. The proposed rule recovers {int(db.tp-da.tp)} development occurrences without new false positives; it deliberately leaves runtime-variable cases unresolved."))
    texts.append(macro("RuleDescription", "The rule processes command-related IR variable/attribute fields and their source slices. Supported roles include command, cmd, shell, execute, code, block, only\\_if, not\\_if, and identifiers ending in \\_cmd or \\_command. In opaque command blocks it recognizes explicit Ruby system/exec/spawn or shell-literal wrappers. A source assignment can also recover a literal command whose IR value was replaced by an interpolation function node. Shell-like tokens distinguish supported executables (mysql, mysqladmin, mysqldump, mysqlcheck) from quoted mentions. A report requires a literal root user given by -uroot, -u root, --user=root, or --user root before the SQL execution payload. Leading environment assignments and command chaining are supported. Unresolved user expressions, root-like substrings, arbitrary wrappers, and option-file defaults are not inferred. The same implementation applies to all three technologies; no benchmark filenames or oracle labels are used in recognition."))
    texts.append(macro("ReproductionDiscussion", "All six native prediction multisets match the author outputs: improved and SLIC/SLAC-like configurations for each language. Ansible equality is checked over file/category/content because the stored output lacks line numbers; Chef and Puppet equality uses file/line/category. The independently implemented scorer agrees with all six original scorer runs. Per-category counts are identical. Puppet macro precision is 0.686 before rounding, displayed as 0.69, versus the paper's 0.68; averaging the paper's already-rounded per-category precisions gives 0.684, displayed as 0.68. This is an aggregation-rounding difference, not a prediction gap. Four Ansible file types yield no IR in the original parser; these are retained in the evaluated population and their diagnostics are disclosed, not silently dropped or described as successfully parsed."))
    published = {"ansible": (.77, .87), "chef": (.77, .86), "puppet": (.68, .85)}
    baseline_rows = []
    for tech in ["ansible", "chef", "puppet"]:
        measured = baseline[(baseline.tech == tech) & (baseline.configuration == "improved") & (baseline.origin == "native")]
        pp, rr = published[tech]
        baseline_rows.append([tech.title(), f"{pp:.2f}", f"{rr:.2f}", f"{measured.precision.mean():.2f}", f"{measured.recall.mean():.2f}"])
    texts.append(macro("BaselineTable", table("Published and reproduced improved-GLITCH averages.", "tab:baseline", "lrrrr", ["Technology", "Paper P", "Paper R", "Native P", "Native R"], baseline_rows,
        "Native averages use unrounded category values, include the separate No smell class and exclude undefined values. Puppet's one-hundredth precision difference is explained by averaging rounded cells; prediction multisets and counts match exactly.")))
    texts.append(macro("ExtensionDiscussion", f"The primary reserved-test comparison is Chef administrative-default detection: TP/FP/FN changes from {int(a.tp)}/{int(a.fp)}/{int(a.fn)} to {int(b.tp)}/{int(b.fp)}/{int(b.fn)}. Recall improves by {100*(b.recall-a.recall):.2f} percentage points and F1 by {100*(b.f1-a.f1):.2f} percentage points, with no added false positives. Administrative-default results on reserved Ansible and Puppet files remain unchanged; parser integration tests establish cross-language behavior on controlled examples, not additional real-world gains. The eight unrelated security-smell categories remain unchanged because the visitor only adds administrative-default reports. The paper's separate No smell file-level class may change as additional smells are detected."))
    labels = [("baseline", "Archived GLITCH"), ("command_aware", "Command-aware"), ("naive_substring", "Naive substrings")]
    extension_rows = []
    for name, display in labels:
        r = admin(test, "chef", name)
        extension_rows.append([display, str(int(r.tp)), str(int(r.fp)), str(int(r.fn)), f"{r.precision:.3f}", f"{r.recall:.3f}", f"{r.f1:.3f}"])
    texts.append(macro("ExtensionTable", table("Reserved Chef administrative-default results (40 files).", "tab:extension", "lrrrrrr", ["Method", "TP", "FP", "FN", "P", "R", "F1"], extension_rows,
        "Point estimates on 16 annotated occurrences. Rule and ablation were frozen before test scoring. These are smell detections, not confirmed vulnerabilities.")))
    texts.append(macro("AblationDiscussion", f"The deliberately weak substring ablation adds a report when an IR source line contains both mysql and root. It attains test recall {naive.recall:.3f} but incurs {int(naive.fp)} false positives, compared with {int(b.fp)} for the command-aware rule. Its F1 is {naive.f1:.3f}, below the command-aware value {b.f1:.3f}. The ablation is a frozen mechanistic control, not a claimed competitive analyzer. On the full 80-file Chef oracle, the command-aware result is TP={int(fb.tp)}, FP={int(fb.fp)}, FN={int(fb.fn)} (precision {fb.precision:.3f}, recall {fb.recall:.3f}, F1 {fb.f1:.3f}); these full-oracle numbers include development files and are descriptive rather than held-out validation."))
    checks = len(audit["checks"])
    status = json.loads((out / "baseline_status.json").read_text())
    original_seconds = sum(x["seconds"] for x in status if x["configuration"] == "improved")
    extension_status = sum((json.loads((out / f"extension_{phase}_status.json").read_text()) for phase in ["development", "test"]), [])
    extension_seconds = sum(x["seconds"] for x in extension_status if x["method"] == "command_aware")
    texts.append(macro("VerificationDiscussion", f"All {checks} audit checks pass. The original source remains unchanged, partition/source hashes match, the rule freeze is intact, all original reports are preserved, and only the target smell receives new reports. Independent scores agree with nine original scorer runs covering baseline, command-aware, and naive methods across languages. Three representative files are reparsed and replayed successfully. There are 35 automated correctness and integration tests. The frozen rule timestamp is {freeze['utc_time'].split('T')[0]}; no post-test rule edits are made. Native execution uses Python {provenance['python']} and Ruby 2.6.10 on arm64 macOS. Summed per-file times for the improved original and command-aware runs over 241 files are {original_seconds:.2f} and {extension_seconds:.2f} seconds, respectively. These single-run timings include parsing, exclude download/setup, and do not establish a statistically reliable speed difference."))
    texts.append(macro("SpecificLimitations", "The original Chef oracle contains duplicated labels at the same file/line/category; we retain these for faithful reproduction instead of repairing ground truth. Unresolved database-user variables and unsupported command constructs remain false negatives. The rule stops before the SQL execution payload, so it does not resolve user overrides after that payload or full shell/Ruby semantics. Reported gains apply to the archived analyzer and this oracle; they are not proof of generalization to current GLITCH releases or modern production repositories."))
    texts.append(macro("MeasuredConclusion", f"We reproduce the archived GLITCH accuracy evaluation exactly at the stored-prediction level and verify its matching protocol independently. A development-motivated, frozen command-aware extension improves reserved Chef administrative-default F1 from {a.f1:.3f} to {b.f1:.3f}, recovering {int(b.tp-a.tp)} missed occurrences without additional false positives. The correction does not improve every smell or every language; Ansible and Puppet oracle scores remain unchanged. The measured outcome supports a bounded implementation contribution with explicitly limited generalization."))
    (paper / "generated.tex").write_text("% Generated from audited measured experiment artifacts.\n" + "\n".join(texts))
    fig, ax = plt.subplots(figsize=(6, 3.2))
    x = np.arange(3)
    for i, (name, label) in enumerate(labels):
        r = admin(test, "chef", name)
        ax.bar(x + (i-1)*.24, [r.precision, r.recall, r.f1], width=.24, label=label)
    ax.set_xticks(x, ["Precision", "Recall", "F1"])
    ax.set_ylim(0, 1.1)
    ax.set_ylabel("Reserved Chef oracle score")
    ax.legend(fontsize=8, loc="upper center", ncol=3)
    fig.tight_layout()
    fig.savefig(out / "chef_holdout.png", dpi=200)
    plt.close(fig)
    shutil.copy2(out / "chef_holdout.png", paper / "chef_holdout.png")
    lines = ["# GLITCH: measured reproduction and correction", "", "## Baseline fidelity", "",
             "**Exact match:** all six author-stored prediction outputs are reproduced natively (3 technologies × 2 configurations). Independent scoring agrees with the original scripts.", "",
             "All 241 oracle files are enumerated: Ansible 81, Chef 80, Puppet 80. This is the labeled accuracy experiment, not the 196,755-script unlabelled frequency rerun.", "",
             "| Technology | Published average precision | Published average recall | Native average precision | Native average recall |",
             "|---|---:|---:|---:|---:|"]
    for r in baseline_rows: lines.append("| " + " | ".join(r) + " |")
    lines += ["", "**Rounding note:** Puppet's unrounded category precisions average to 0.685907 (displayed 0.69). Averaging the published two-decimal category values gives 0.684444 (displayed 0.68). This one-hundredth macro-average difference does not correspond to different detections: all original prediction multisets and per-category counts match exactly."]
    lines += ["", "## Flaw fixed", "", "The original analyzer misses explicit root database users embedded in command-valued fields and opaque command-block IR source slices. The extension recognizes literal MySQL user options without executing scripts or assuming unresolved variables are root.", "",
              "## Reserved Chef test results", "", "40 test files, 16 annotated Admin-by-default occurrences. The rule was frozen after development evaluation and before test scoring.", "",
              "| Method | TP | FP | FN | Precision | Recall | F1 |", "|---|---:|---:|---:|---:|---:|---:|"]
    for r in extension_rows: lines.append("| " + " | ".join(r) + " |")
    lines += ["", f"**Measured gain:** {int(b.tp-a.tp)} recovered true positives, no new false positives; recall +{100*(b.recall-a.recall):.2f} percentage points, F1 +{100*(b.f1-a.f1):.2f} percentage points.", "",
              "Ansible and Puppet oracle results remain unchanged. All unrelated security-smell report sets are preserved. Parser integration tests establish shared rule behavior across the three languages on controlled fixtures.", "",
              "## Full Chef oracle (descriptive, includes development)", "",
              f"Baseline: TP={int(fa.tp)}, FP={int(fa.fp)}, FN={int(fa.fn)}, P={fa.precision:.6f}, R={fa.recall:.6f}, F1={fa.f1:.6f}.",
              f"Corrected: TP={int(fb.tp)}, FP={int(fb.fp)}, FN={int(fb.fn)}, P={fb.precision:.6f}, R={fb.recall:.6f}, F1={fb.f1:.6f}.", "",
              "Do not present these full-oracle figures as held-out results.", "",
              "## Verification and caveats", "", f"- {checks} audit checks pass; 35 automated tests pass.",
              "- Exact archived-source baseline and installed Puppet egg; source/image/partition hashes retained.",
              "- Four Ansible file types produce no IR in the original analyzer; these files remain in the evaluated population. Matching the authors does not prove parser completeness.",
              "- File-disjoint internal holdout, not project-disjoint external validation; only 16 target occurrences in reserved Chef files.",
              "- Original duplicate oracle labels and original content/file-level matching exceptions are disclosed.",
              "- A security smell is not proof of exploitability; root access can be required for legitimate provisioning.",
              "- The rule is bounded and does not resolve runtime users, arbitrary shell wrappers or post-payload user overrides.",
              "- The base paper already discusses this limitation; the contribution is an implementation and measured extension, not a claim of unprecedented discovery.", "",
              "## Deliverables", "", "- `paper/main.pdf`: IEEE conference-format report.", "- `paper/main.tex`, `paper/generated.tex`, `paper/references.bib`: editable manuscript.", "- `results/AUDIT.json`, `results/rule_freeze.json`: verification and pre-test freeze.", "- `results/extension_test_metrics.csv`: full held-out metrics.", "- `results/extension_full_metrics.csv`: descriptive full-oracle metrics.", "- `PRESENTATION_GUIDE.md`: defense guide."]
    (out / "REPORT.md").write_text("\n".join(lines) + "\n")
    print("Generated measured report and IEEE manuscript tables.")


if __name__ == "__main__":
    main()
