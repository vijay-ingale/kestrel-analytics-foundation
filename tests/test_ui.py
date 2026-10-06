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
    app.session_state["view"] = "Operations"
    app.run(timeout=60)
    assert not app.exception
    metric = next(widget for widget in app.selectbox if widget.label == "Metric")
    metric.set_value("trips").run(timeout=60)
    assert not app.exception and app.warning
    app.session_state["view"] = "Data Quality"
    app.run(timeout=60)
    assert not app.exception and app.dataframe
    app.session_state["view"] = "Questions & Trace"
    app.run(timeout=60)
    next(button for button in app.button if button.label == "Run query").click().run(timeout=60)
    assert not app.exception and app.dataframe
    app.session_state["view"] = "Reconciliation"
    app.run(timeout=60)
    assert not app.exception and app.dataframe
    app.session_state["view"] = "Catalogue"
    app.run(timeout=60)
    assert not app.exception and len(app.expander) == 14
