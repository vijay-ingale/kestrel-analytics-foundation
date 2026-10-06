from decimal import Decimal
import pytest
from pipeline.contracts import inspect_schema, normalize, parse, temperature_c


def pos(**changes):
    return dict(txn_id="T1", txn_line_no=1, outlet_code="O1", sku_code="S1", channel="MT", event_ts="2025-01-01T20:00:00Z", qty=2, unit_price=10, **changes)


def test_alias_conflict_is_not_silently_resolved():
    _, errors, _, _ = normalize("pos_transactions", pos(quantity_units=3))
    assert "ALIAS_CONFLICT:quantity" in errors


def test_equal_numeric_aliases_are_accepted():
    row, errors, _, _ = normalize("pos_transactions", pos(quantity_units="2.0"))
    assert not errors and row["quantity"] == Decimal(2)


def test_missing_quantity_is_not_zero():
    source = pos()
    source["qty"] = None
    row, _, warnings, _ = normalize("pos_transactions", source)
    assert row["quantity"] is None and "MISSING:quantity" in warnings


def test_schema_version_is_checked_against_partition():
    _, missing, extras = inspect_schema("pos_transactions", list(pos()) + ["new_field"], "2025-10-02")
    assert "quantity_units" in missing and extras == ["new_field"]


def test_conversion_preserves_missing_measurement():
    assert temperature_c(None, "C", "THERMLOG") is None
    assert temperature_c(50, None, "COLDEYE") == Decimal(10)
    assert temperature_c(50, "K", "COLDEYE") is None


def test_conflicting_unit_metadata_is_rejected():
    _, errors, _, _ = normalize("reefer_telemetry", {"temp_f": 50, "temp_unit": "C"})
    assert "UNIT_METADATA_CONFLICT" in errors


@pytest.mark.parametrize("value", ["1,234", "NaN", "infinity", "USD 10"])
def test_ambiguous_and_nonfinite_numbers_are_rejected(value):
    with pytest.raises(ValueError):
        parse(value, "numeric")


def test_timestamp_conventions_are_explicit():
    with pytest.raises(ValueError):
        parse("2025-01-01 10:00:00", "timestamptz")
    assert parse("2025-01-01 10:00:00", "timestamp").tzinfo is None
