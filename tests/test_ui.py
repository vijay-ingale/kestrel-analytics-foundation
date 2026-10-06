"""Exercise real Streamlit controls against an already-built integration database."""
import os
from pathlib import Path
import pytest

URL = os.environ.get("KESTREL_TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(not URL, reason="Requires built integration database")


def test_ui_views_and_query_execution(monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("DATABASE_URL",URL)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app/main.py")).run(timeout=60)
    assert not app.exception
    assert app.dataframe
    app.get("button_group")[0].set_value(["Operations"]).run(timeout=60)
    assert not app.exception
    metric = next(widget for widget in app.selectbox if widget.label == "Metric")
    app.get("button_group")[0].set_value(["Operations"])
    metric.set_value("cycles").run(timeout=60)
    assert not app.exception and app.dataframe
    trip_metric = next(widget for widget in app.selectbox if widget.label == "Metric")
    app.get("button_group")[0].set_value(["Operations"])
    trip_metric.set_value("trips").run(timeout=60)
    assert not app.exception and app.warning
    app.get("button_group")[0].set_value(["Data Quality"]).run(timeout=60)
    assert not app.exception and app.dataframe
    app.get("button_group")[0].set_value(["Questions & Trace"]).run(timeout=60)
    app.get("button_group")[0].set_value(["Questions & Trace"])
    next(button for button in app.button if button.label == "Run query").click().run(timeout=60)
    assert not app.exception and app.dataframe
    app.get("button_group")[0].set_value(["Reconciliation"]).run(timeout=60)
    assert not app.exception and app.dataframe
    app.get("button_group")[0].set_value(["Catalogue"]).run(timeout=60)
    assert not app.exception and len(app.expander) == 14
