import pandas as pd
from glitchstudy.evaluation import score


def test_exact_line_matching():
    oracle = pd.DataFrame([{"PATH": "a.rb", "LINE": 2, "CATEGORY": "admin-by-default"}])
    predictions = pd.DataFrame([{"PATH": "a.rb", "LINE": 3, "ERROR": "admin-by-default"}])
    metrics, _ = score(oracle, predictions, "chef")
    row = metrics[metrics.category == "admin-by-default"].iloc[0]
    assert (row.tp, row.fp, row.fn) == (0, 1, 1)


def test_published_relaxed_matching_and_strict_sensitivity():
    oracle = pd.DataFrame([{"PATH": "a.rb", "LINE": 2, "CATEGORY": "no-integrity-check"}])
    predictions = pd.DataFrame([{"PATH": "a.rb", "LINE": 3, "ERROR": "no-integrity-check"}])
    loose, _ = score(oracle, predictions, "chef")
    strict, _ = score(oracle, predictions, "chef", strict=True)
    assert loose[loose.category == "no-integrity-check"].iloc[0].tp == 1
    assert strict[strict.category == "no-integrity-check"].iloc[0].tp == 0


def test_each_prediction_consumed_once():
    oracle = pd.DataFrame([{"PATH": "a.rb", "LINE": 2, "CATEGORY": "admin-by-default"},
                           {"PATH": "a.rb", "LINE": 3, "CATEGORY": "admin-by-default"}])
    predictions = pd.DataFrame([{"PATH": "a.rb", "LINE": 2, "ERROR": "admin-by-default"}])
    metrics, _ = score(oracle, predictions, "chef")
    row = metrics[metrics.category == "admin-by-default"].iloc[0]
    assert (row.tp, row.fp, row.fn) == (1, 0, 1)


def test_no_smell_as_separate_file_level_class():
    oracle = pd.DataFrame([{"PATH": "a.rb", "LINE": 0, "CATEGORY": "none"},
                           {"PATH": "b.rb", "LINE": 2, "CATEGORY": "admin-by-default"}])
    predictions = pd.DataFrame(columns=["PATH", "LINE", "ERROR"])
    metrics, _ = score(oracle, predictions, "chef")
    row = metrics[metrics.category == "none"].iloc[0]
    assert (row.tp, row.fp, row.fn) == (1, 1, 0)
