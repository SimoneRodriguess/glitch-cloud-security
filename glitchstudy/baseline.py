"""Re-run original analyses on all 241 oracle scripts, preserving raw output."""
import contextlib
import hashlib
import importlib.metadata
import io
import json
import platform
import re
import subprocess
import sys
import time

import pandas as pd
from glitch.analysis.security import SecurityVisitor
from glitch.parsers.cmof import AnsibleParser, ChefParser, PuppetParser
from glitch.repr.inter import UnitBlockType
from glitch.tech import Tech

from . import ROOT, ARTIFACT
from .evaluation import ERROR_CODES, load_oracle, score

PARSERS = {"ansible": AnsibleParser, "chef": ChefParser, "puppet": PuppetParser}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze_file(path, tech, config, visitor_class=SecurityVisitor):
    parser = PARSERS[tech]()
    visitor = visitor_class(Tech(tech))
    visitor.config(str(config))
    captured = io.StringIO()
    start = time.perf_counter()
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        block = parser.parse(str(path), UnitBlockType.unknown, False)
        errors = sorted(set(visitor.check(block) or []), key=lambda e: (e.path, e.line, e.code)) if block is not None else []
    rows = [{"PATH": path.name, "LINE": error.line, "ERROR": ERROR_CODES[error.code], "CODE": error.code,
             "TEXT": re.sub(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----.*?-----END (?:RSA |OPENSSH |EC )?PRIVATE KEY-----",
                            "[PRIVATE KEY REDACTED]", error.repr.strip(), flags=re.DOTALL)} for error in errors]
    return rows, {"file": path.name, "seconds": time.perf_counter() - start, "parsed": block is not None, "diagnostics": captured.getvalue()}


def main():
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    metrics, strict_metrics, statuses, splits, checks, native_cached_diffs = [], [], [], [], [], []
    source = ARTIFACT / "GLITCH"
    for tech in PARSERS:
        oracle = load_oracle(tech)
        files = sorted(set(oracle.PATH))
        folder = ARTIFACT / "RESULTS" / tech / "oracle-dataset"
        if tech == "chef":
            folder = folder / "recipes"
        assert all((folder / name).exists() for name in files)
        # Freeze a deterministic, file-disjoint development/test partition BEFORE
        # inspecting individual errors or implementing any extension.
        ordered = sorted(files, key=lambda name: hashlib.sha256(("glitch-dev-v1/" + tech + "/" + name).encode()).hexdigest())
        dev = set(ordered[:len(ordered) // 2])
        splits.extend({"tech": tech, "file": name, "split": "development" if name in dev else "test", "source_sha256": digest(folder / name)} for name in files)
        configurations = [("improved", "improved.ini"), ("legacy", "SLIC_puppet.ini" if tech == "puppet" else "SLAC_" + tech + ".ini")]
        for version, config_name in configurations:
            records = []
            print(f"Running {tech}/{version}: {len(files)} oracle files", flush=True)
            for name in files:
                rows, status = analyze_file(folder / name, tech, source / "configs" / config_name)
                records.extend(rows)
                statuses.append({"tech": tech, "configuration": version, **status})
            predictions = pd.DataFrame(records, columns=["PATH", "LINE", "ERROR", "CODE", "TEXT"])
            predictions.to_csv(out / f"native_{tech}_{version}.csv", index=False)
            prefix = "GLITCH-" if version == "improved" else ("GLITCH-SLIC-" if tech == "puppet" else "GLITCH-SLAC-")
            cached_path = ARTIFACT / "RESULTS" / tech / "oracle-dataset-analysis" / f"{prefix}{tech}-oracle.csv"
            if tech == "ansible":
                lines = [line.split(",", 2) for line in cached_path.read_text().splitlines()]
                cached = pd.DataFrame(lines, columns=["PATH", "ERROR", "TEXT"])
                cached["LINE"] = -1  # Original output has content, not line numbers.
            else:
                cached = pd.read_csv(cached_path)
            cached.to_csv(out / f"authors_{tech}_{version}.csv", index=False)
            for origin, frame in [("native", predictions), ("authors_cached", cached)]:
                summary, errors = score(oracle, frame, tech)
                summary["tech"], summary["configuration"], summary["origin"] = tech, version, origin
                metrics.append(summary)
                if not (origin == "authors_cached" and tech == "ansible"):
                    strict, _ = score(oracle, frame, tech, strict=True)
                    strict["tech"], strict["configuration"], strict["origin"] = tech, version, origin
                    strict_metrics.append(strict)
                if origin == "native" and version == "improved":
                    # Only DEVELOPMENT file errors are exposed for rule design.
                    pd.DataFrame([e for e in errors if e["PATH"] in dev]).to_csv(out / f"development_errors_{tech}.csv", index=False)
            # Compare against the unmodified official scorer by executing only
            # its metric script, never the oracle infrastructure scripts.
            script = cached_path.parent / "calculate-metrics.py"
            scorer_input = out / f"native_{tech}_{version}.csv"
            if tech == "ansible":
                scorer_input = out / f"official_input_{tech}_{version}.txt"
                scorer_input.write_text("\n".join(f"{r.PATH},{r.ERROR},{r.TEXT}" for r in predictions.itertuples()) + "\n")
            result = subprocess.run([sys.executable, str(script), str(scorer_input.resolve())], cwd=script.parent, capture_output=True, text=True, check=True)
            (out / f"official_scorer_{tech}_{version}.txt").write_text(result.stdout)
            p_values, r_values = {}, {}
            current = None
            for line in result.stdout.splitlines():
                if line == "PRECISION": current = p_values
                elif line == "RECALL": current = r_values
                elif current is not None:
                    key, _, value = line.rpartition(" ")
                    try: current[key] = float(value)
                    except ValueError: pass
            expected, _ = score(oracle, predictions, tech)
            valid = all((pd.isna(row.precision) or abs(row.precision - p_values[row.category]) < 1e-12) and (pd.isna(row.recall) or abs(row.recall - r_values[row.category]) < 1e-12) for _, row in expected.iterrows())
            checks.append({"tech": tech, "configuration": version, "independent_scorer_matches_official": valid})
            key = (lambda frame: set((r.PATH, r.ERROR, r.TEXT) for r in frame.itertuples())) if tech == "ansible" else (lambda frame: set((r.PATH, int(r.LINE), r.ERROR) for r in frame.itertuples()))
            a, b = key(predictions), key(cached)
            native_cached_diffs.append({"tech": tech, "configuration": version, "native_only": sorted(a - b), "authors_only": sorted(b - a), "exact_prediction_set_match": a == b})
    pd.concat(metrics, ignore_index=True).to_csv(out / "baseline_metrics.csv", index=False)
    pd.concat(strict_metrics, ignore_index=True).to_csv(out / "strict_baseline_metrics.csv", index=False)
    pd.DataFrame(splits).to_csv(out / "split_manifest.csv", index=False)
    (out / "baseline_status.json").write_text(json.dumps(statuses, indent=2))
    report = {"official_scorer_checks": checks, "native_vs_author_predictions": native_cached_diffs,
              "source_commit": json.loads((ROOT / "data/source-revision.json").read_text())["source_commit"],
              "python": platform.python_version(), "platform": platform.platform(),
              "ruby": subprocess.run(["ruby", "--version"], capture_output=True, text=True, check=True).stdout.strip(),
              "packages": {name: importlib.metadata.version(name) for name in ["ruamel.yaml", "ply", "pandas", "numpy"]},
              "files_by_technology": {tech: len(load_oracle(tech).PATH.unique()) for tech in PARSERS},
              "split_manifest_sha256": digest(out / "split_manifest.csv"),
              "source_code_sha256": {str(p.relative_to(source)): digest(p) for p in sorted(source.rglob("*.py")) if ".git" not in p.parts},
              "scope": "All 241 manually annotated oracle scripts; full 196755-script frequency rerun not performed.",
              "execution": "Individual files parsed with original parsers/visitors, explicit unknown block type; no IaC execution."}
    (out / "baseline_provenance.json").write_text(json.dumps(report, indent=2))
    assert all(c["independent_scorer_matches_official"] for c in checks)
    print(json.dumps({"files": report["files_by_technology"], "scorers": checks, "exact_matches": [(d["tech"], d["configuration"], d["exact_prediction_set_match"]) for d in native_cached_diffs]}, indent=2))


if __name__ == "__main__":
    main()
