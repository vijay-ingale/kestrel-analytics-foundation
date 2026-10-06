from datetime import date
import pytest
from pipeline.query import METRICS, parameters, query_sql


def test_every_supported_metric_has_one_select():
    for metric in METRICS.values():
        if metric["supported"]:
            assert query_sql(metric["id"])


def test_unsupported_questions_explain_missing_evidence():
    with pytest.raises(ValueError, match="trip"):
        query_sql("trips")


def test_reversed_dates_are_rejected():
    with pytest.raises(ValueError):
        parameters("2026-01-02","2026-01-01")


def test_default_as_of_is_explicit_end_plus_one():
    assert parameters("2026-04-01","2026-06-30")["as_of"] == date(2026,7,1)
