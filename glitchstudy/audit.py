"""Audit provenance, frozen holdout, original scoring, and model replay."""
import json
from collections import Counter
import subprocess
import sys
import pandas as pd

from . import ROOT, ARTIFACT
from .baseline import analyze_file, digest
from .command_rule import CommandAwareVisitor
from .evaluation import load_oracle, score
from .extension import verify_frozen


def key(frame):
    return set((r.PATH, int(r.LINE), r.ERROR) for r in frame.itertuples())


def main():
    out = ROOT / "results"
    baseline = json.loads((out / "baseline_provenance.json").read_text())
    freeze = json.loads((out / "rule_freeze.json").read_text())
    source = json.loads((ROOT / "data/artifact-provenance.json").read_text())
    checks = {}
    checks["official_artifact_md5_verified"] = source["md5_verified"]
    checks["all_six_native_prediction_sets_match_authors"] = all(r["exact_prediction_set_match"] for r in baseline["native_vs_author_predictions"])
    multiset_checks = []
    for tech in ["ansible", "chef", "puppet"]:
        for configuration in ["improved", "legacy"]:
            fresh = pd.read_csv(out / f"native_{tech}_{configuration}.csv")
            cached = pd.read_csv(out / f"authors_{tech}_{configuration}.csv")
            columns = ["PATH", "ERROR", "TEXT"] if tech == "ansible" else ["PATH", "LINE", "ERROR"]
            multiset_checks.append(Counter(map(tuple, fresh[columns].to_numpy())) == Counter(map(tuple, cached[columns].to_numpy())))
    checks["all_six_prediction_multisets_and_counts_match"] = all(multiset_checks)
    checks["six_baseline_official_scorers_agree"] = all(r["independent_scorer_matches_official"] for r in baseline["official_scorer_checks"])
    checks["baseline_source_unchanged"] = all(digest(ARTIFACT / "GLITCH" / name) == value for name, value in baseline["source_code_sha256"].items())
    verify_frozen()
    checks["rule_and_protocol_frozen"] = True
    splits = pd.read_csv(out / "split_manifest.csv")
    checks["complete_241_file_population"] = len(splits) == 241 and not splits.duplicated(["tech", "file"]).any()
    checks["file_disjoint_holdout"] = set(map(tuple, splits[splits.split == "development"][["tech", "file"]].to_numpy())).isdisjoint(set(map(tuple, splits[splits.split == "test"][["tech", "file"]].to_numpy())))
    checks["split_manifest_unchanged"] = digest(out / "split_manifest.csv") == baseline["split_manifest_sha256"]
    checks["all_source_file_hashes_match"] = all(digest(ARTIFACT / "RESULTS" / r.tech / "oracle-dataset" / ("recipes" if r.tech == "chef" else "") / r.file) == r.source_sha256 for r in splits.itertuples())
    metric = pd.read_csv(out / "extension_full_metrics.csv")
    integrity = []
    official = []
    for tech in ["ansible", "chef", "puppet"]:
        oracle = load_oracle(tech)
        original = pd.read_csv(out / f"full_{tech}_baseline.csv")
        corrected = pd.read_csv(out / f"full_{tech}_command_aware.csv")
        a, b = key(original), key(corrected)
        integrity.append({"tech": tech, "original_reports_preserved": a <= b,
                          "new_reports_only_target_smell": all(x[2] == "admin-by-default" for x in b - a),
                          "additional_report_count": len(b - a)})
        for method in ["baseline", "command_aware", "naive_substring"]:
            predictions = pd.read_csv(out / f"full_{tech}_{method}.csv")
            fresh, _ = score(oracle, predictions, tech)
            saved = metric[(metric.tech == tech) & (metric.method == method)]
            assert all((fresh[column].to_numpy() == saved[column].to_numpy()).all() for column in ["tp", "fp", "fn"])
            script_folder = ARTIFACT / "RESULTS" / tech / "oracle-dataset-analysis"
            input_path = out / f"official_extension_input_{tech}_{method}.csv"
            if tech == "ansible":
                input_path.write_text("\n".join(f"{r.PATH},{r.ERROR},{r.TEXT}" for r in predictions.itertuples()) + "\n")
            else:
                predictions[["PATH", "LINE", "ERROR"]].to_csv(input_path, index=False)
            result = subprocess.run([sys.executable, str(script_folder / "calculate-metrics.py"), str(input_path.resolve())], cwd=script_folder, capture_output=True, text=True, check=True)
            (out / f"official_extension_score_{tech}_{method}.txt").write_text(result.stdout)
            p_values, r_values, current = {}, {}, None
            for line in result.stdout.splitlines():
                if line == "PRECISION": current = p_values
                elif line == "RECALL": current = r_values
                elif current is not None:
                    name, _, value = line.rpartition(" ")
                    try: current[name] = float(value)
                    except ValueError: pass
            agrees = all((pd.isna(r.precision) or abs(r.precision - p_values[r.category]) < 1e-12) and (pd.isna(r.recall) or abs(r.recall - r_values[r.category]) < 1e-12) for _, r in fresh.iterrows())
            official.append({"tech": tech, "method": method, "agrees": agrees})
    checks["full_metrics_recomputed"] = True
    checks["original_detections_preserved"] = all(x["original_reports_preserved"] for x in integrity)
    checks["only_admin_category_added"] = all(x["new_reports_only_target_smell"] for x in integrity)
    checks["nine_extension_original_scorers_agree"] = all(x["agrees"] for x in official)
    # Reparse and replay a fixed hash-selected file in each technology.
    replays = []
    for tech in ["ansible", "chef", "puppet"]:
        file = sorted(splits[(splits.tech == tech) & (splits.split == "test")].file)[0]
        path = ARTIFACT / "RESULTS" / tech / "oracle-dataset" / ("recipes" if tech == "chef" else "") / file
        rows, _ = analyze_file(path, tech, ARTIFACT / "GLITCH/configs/improved.ini", CommandAwareVisitor)
        fresh = pd.DataFrame(rows, columns=["PATH", "LINE", "ERROR", "CODE", "TEXT"])
        saved = pd.read_csv(out / f"test_{tech}_command_aware.csv")
        replays.append({"tech": tech, "file": file, "matches": key(fresh) == key(saved[saved.PATH == file])})
    checks["three_native_file_replays_match"] = all(x["matches"] for x in replays)
    status = json.loads((out / "baseline_status.json").read_text())
    unsupported = sorted(set((x["tech"], x["file"]) for x in status if not x["parsed"]))
    oracle_anomalies = []
    for tech in ["ansible", "chef", "puppet"]:
        oracle = load_oracle(tech)
        duplicates = oracle[oracle.duplicated(["PATH", "LINE", "CATEGORY"], keep=False)]
        if len(duplicates):
            oracle_anomalies.append({"tech": tech, "duplicate_label_rows": duplicates.to_dict("records")})
    result = {"all_passed": all(checks.values()), "checks": checks,
              "preservation": integrity, "official_extension_scores": official, "replays": replays,
              "original_unsupported_file_types": unsupported, "oracle_duplicate_labels": oracle_anomalies,
              "frozen_rule_utc_time": freeze["utc_time"],
              "caveat": "Internal consistency and exact baseline reproduction are not external validation or exploitability evidence."}
    (out / "AUDIT.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    if not result["all_passed"]:
        raise AssertionError("Audit failed")


if __name__ == "__main__":
    main()
