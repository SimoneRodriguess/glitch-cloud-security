"""Development-first, hash-frozen evaluation. Test labels never enter the rule."""
import argparse
from datetime import datetime, timezone
import json

import pandas as pd

from . import ROOT, ARTIFACT
from .baseline import analyze_file, digest
from .command_rule import CommandAwareVisitor, NaiveCommandVisitor
from .evaluation import load_oracle, score

VISITORS = {"command_aware": CommandAwareVisitor, "naive_substring": NaiveCommandVisitor}


def freeze():
    out = ROOT / "results"
    files = [ROOT / "glitchstudy/command_rule.py", ROOT / "glitchstudy/extension.py", out / "split_manifest.csv", ARTIFACT / "GLITCH/configs/improved.ini"]
    hashes = {str(path.relative_to(ROOT)): digest(path) for path in files}
    target = out / "rule_freeze.json"
    if target.exists():
        recorded = json.loads(target.read_text())
        if recorded["hashes"] != hashes:
            raise ValueError("Frozen rule or protocol changed; do not silently reuse the holdout")
        return recorded
    if not (out / "extension_development_metrics.csv").exists():
        raise ValueError("Run development evaluation before freezing")
    record = {"utc_time": datetime.now(timezone.utc).isoformat(), "hashes": hashes,
              "target_smell": "admin-by-default", "reason": "Literal database users missed in command-valued/opaque IR nodes; identified in paper and development errors.",
              "protocol": "File-disjoint heldout evaluation, frozen rule and naive ablation; no threshold training or test-error tuning.",
              "development_files": 120, "test_files": 121, "unit_tests_at_freeze": 35,
              "limitation": "Internal file-level holdout, not project-independent or externally annotated new data."}
    target.write_text(json.dumps(record, indent=2))
    return record


def verify_frozen():
    record = json.loads((ROOT / "results/rule_freeze.json").read_text())
    assert all(digest(ROOT / name) == value for name, value in record["hashes"].items()), "Frozen source changed"


def run(phase):
    out = ROOT / "results"
    if phase == "test":
        verify_frozen()
    splits = pd.read_csv(out / "split_manifest.csv")
    metrics, strict_metrics, statuses = [], [], []
    for tech in ["ansible", "chef", "puppet"]:
        selected = splits[(splits.tech == tech) & (splits.split == phase)]
        files = set(selected.file)
        oracle = load_oracle(tech)
        oracle = oracle[oracle.PATH.isin(files)]
        baseline = pd.read_csv(out / f"native_{tech}_improved.csv")
        baseline = baseline[baseline.PATH.isin(files)]
        folder = ARTIFACT / "RESULTS" / tech / "oracle-dataset"
        if tech == "chef": folder /= "recipes"
        variants = {"baseline": baseline}
        for method, visitor in VISITORS.items():
            print(f"{phase}/{tech}/{method}: {len(files)} files", flush=True)
            predictions = []
            for name in sorted(files):
                source = folder / name
                assert digest(source) == selected[selected.file == name].iloc[0].source_sha256
                rows, status = analyze_file(source, tech, ARTIFACT / "GLITCH/configs/improved.ini", visitor)
                predictions.extend(rows)
                statuses.append({"phase": phase, "tech": tech, "method": method, **status})
            variants[method] = pd.DataFrame(predictions, columns=["PATH", "LINE", "ERROR", "CODE", "TEXT"])
            variants[method].to_csv(out / f"{phase}_{tech}_{method}.csv", index=False)
        for method, predictions in variants.items():
            summary, errors = score(oracle, predictions, tech)
            summary["tech"], summary["method"], summary["phase"] = tech, method, phase
            metrics.append(summary)
            strict, _ = score(oracle, predictions, tech, strict=True)
            strict["tech"], strict["method"], strict["phase"] = tech, method, phase
            strict_metrics.append(strict)
            pd.DataFrame(errors).to_csv(out / f"{phase}_errors_{tech}_{method}.csv", index=False)
    pd.concat(metrics, ignore_index=True).to_csv(out / f"extension_{phase}_metrics.csv", index=False)
    pd.concat(strict_metrics, ignore_index=True).to_csv(out / f"strict_extension_{phase}_metrics.csv", index=False)
    (out / f"extension_{phase}_status.json").write_text(json.dumps(statuses, indent=2))
    result = pd.concat(metrics, ignore_index=True)
    print(result[result.category == "admin-by-default"].to_string(index=False), flush=True)
    if phase == "test":
        verify_frozen()
        full = []
        for tech in ["ansible", "chef", "puppet"]:
            oracle = load_oracle(tech)
            for method in ["baseline", *VISITORS]:
                predictions = pd.read_csv(out / f"native_{tech}_improved.csv") if method == "baseline" else pd.concat([pd.read_csv(out / f"{p}_{tech}_{method}.csv") for p in ["development", "test"]], ignore_index=True)
                predictions.to_csv(out / f"full_{tech}_{method}.csv", index=False)
                summary, _ = score(oracle, predictions, tech)
                summary["tech"], summary["method"], summary["phase"] = tech, method, "full_oracle_descriptive"
                full.append(summary)
        pd.concat(full, ignore_index=True).to_csv(out / "extension_full_metrics.csv", index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["development", "freeze", "test"])
    phase = parser.parse_args().phase
    if phase == "freeze": print(json.dumps(freeze(), indent=2))
    else: run(phase)
