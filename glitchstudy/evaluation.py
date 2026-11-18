"""Published matching protocol plus exact-line sensitivity, no hidden tuning."""
from collections import Counter
import pandas as pd

from . import ARTIFACT

ORACLE_CODES = {
    "Use of HTTP without SSL/TLS": "use of http", "Admin by default": "admin-by-default",
    "Suspicious comment": "suspicious comment", "Empty password": "empty-password",
    "Hard-coded secret": "hardcoded-secret", "Unrestricted IP Address": "improper ip address binding",
    "No integrity check": "no-integrity-check", "Missing Default in Case Statement": "missing default case statement",
    "Use of weak cryptography algorithms": "weak cryptography algorithms", "none": "none",
}
ERROR_CODES = {
    "sec_hard_secr": "hardcoded-secret", "sec_empty_pass": "empty-password", "sec_https": "use of http",
    "sec_invalid_bind": "improper ip address binding", "sec_no_int_check": "no-integrity-check",
    "sec_susp_comm": "suspicious comment", "sec_hard_user": "hardcoded-username",
    "sec_hard_pass": "hardcoded-password", "sec_def_admin": "admin-by-default",
    "sec_no_default_switch": "missing default case statement", "sec_weak_crypt": "weak cryptography algorithms",
}
CATEGORIES = list(dict.fromkeys(ORACLE_CODES.values()))
IGNORE = {"hardcoded-password", "hardcoded-username"}


def load_oracle(tech):
    folder = ARTIFACT / "RESULTS" / tech / "oracle-dataset-analysis"
    path = folder / ("oracle-dataset.csv" if tech == "puppet" else "oracle_dataset.csv")
    frame = pd.read_csv(path)
    frame["CATEGORY"] = frame.CATEGORY.map(ORACLE_CODES)
    if frame.CATEGORY.isna().any():
        raise ValueError("Unknown oracle category")
    frame["LINE"] = frame.LINE.astype(int)
    return frame


def score(oracle, predictions, tech, strict=False):
    # Match individual published labels, consuming one prediction per occurrence.
    # File-level exceptions follow the original technology-specific scorers.
    loose = set() if strict else ({"weak cryptography algorithms", "improper ip address binding"} if tech == "puppet" else {"weak cryptography algorithms", "no-integrity-check"})
    original = predictions.to_dict("records")
    unused = list(original)
    true = Counter()
    false_negative = Counter()
    mismatch = []
    for label in oracle.to_dict("records"):
        category, file, line = label["CATEGORY"], label["PATH"], int(label["LINE"])
        if category == "none":
            if not any(p["PATH"] == file for p in original):
                true["none"] += 1
            else:
                false_negative["none"] += 1
            continue
        def matches(p):
            if p["PATH"] != file or p["ERROR"] != category:
                return False
            if tech == "ansible" and not strict:
                source_line = (ARTIFACT / "RESULTS" / tech / "oracle-dataset" / file).read_text().splitlines()[line - 1]
                if category == "suspicious comment":
                    return source_line.strip() == p["TEXT"].strip()
                key, value = p["TEXT"].split(":", 1)
                return key.strip("\"'") in source_line and value.strip("\"'") in source_line
            return int(p["LINE"]) == line or category in loose
        found = next((i for i, p in enumerate(unused) if matches(p)), None)
        if found is not None:
            true[category] += 1
            del unused[found]
        else:
            false_negative[category] += 1
            mismatch.append({"type": "FN", "PATH": file, "LINE": line, "ERROR": category})
    false_positive = Counter(p["ERROR"] for p in unused)
    for file in set(oracle.PATH):
        if not any(p["PATH"] == file for p in original) and oracle[oracle.PATH == file].iloc[0].CATEGORY != "none":
            false_positive["none"] += 1
    mismatch.extend({"type": "FP", **p} for p in unused if p["ERROR"] not in IGNORE)
    rows = []
    for category in CATEGORIES:
        tp, fp, fn = true[category], false_positive[category], false_negative[category]
        rows.append({"category": category, "tp": tp, "fp": fp, "fn": fn,
                     "precision": tp / (tp + fp) if tp + fp else None,
                     "recall": tp / (tp + fn) if tp + fn else None,
                     "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None})
    return pd.DataFrame(rows), mismatch
