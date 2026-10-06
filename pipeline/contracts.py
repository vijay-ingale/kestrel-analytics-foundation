"""Explicit mappings: never infer business meaning from similar column names."""
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = json.loads((ROOT / "contracts/feeds.json").read_text())


def empty(value):
    return value is None or (isinstance(value, str) and not value.strip()) or (
        isinstance(value, float) and math.isnan(value)
    )


def parse(value, kind):
    if empty(value):
        return None
    if kind == "text":
        return str(value).strip()
    if kind in ("numeric", "bigint"):
        number = Decimal(str(value))
        if not number.is_finite():
            raise ValueError("nonfinite number")
        if kind == "bigint":
            if number != number.to_integral_value() or not -(2**63) <= number < 2**63:
                raise ValueError("invalid bigint")
            return int(number)
        return number
    if kind == "date":
        return date.fromisoformat(str(value))
    stamp = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if kind == "timestamptz" and stamp.tzinfo is None:
        raise ValueError("timezone required")
    if kind == "timestamp" and stamp.tzinfo is not None:
        raise ValueError("WMS timestamp must be site-local")
    return stamp


def inspect_schema(feed, names, partition_date):
    contract = CONTRACTS[feed]
    names = set(names)
    missing = set(contract["required"]) - names
    for target, aliases in contract.get("aliases", {}).items():
        if not names.intersection(aliases):
            missing.add(target)
    version = "v1"
    if feed == "pos_transactions":
        selected = contract["versions"][0 if partition_date < "2025-10-01" else 1]
        version = selected["name"]
        if selected["quantity_column"] not in names:
            missing.add(selected["quantity_column"])
    known = set(contract["fields"]) | {contract["partition"]}
    for aliases in contract.get("aliases", {}).values():
        known.update(aliases)
    return version, sorted(missing), sorted(names - known)


def normalize(feed, row):
    contract = CONTRACTS[feed]
    mapped = {}
    errors, warnings = [], []
    aliases = contract.get("aliases", {})
    for field, kind in contract["fields"].items():
        values = [(name, row[name]) for name in aliases.get(field, [field]) if name in row and not empty(row[name])]
        try:
            parsed = [parse(value, kind) for _, value in values]
            if parsed and any(value != parsed[0] for value in parsed[1:]):
                errors.append(f"ALIAS_CONFLICT:{field}")
            mapped[field] = parsed[0] if parsed else None
        except (ValueError, TypeError, InvalidOperation, OverflowError):
            mapped[field] = None
            errors.append(f"INVALID_TYPE:{field}")
        if mapped[field] is None:
            (errors if field in contract["required"] else warnings).append(f"MISSING:{field}")
        elif field in contract.get("enums", {}) and mapped[field] not in contract["enums"][field]:
            errors.append(f"UNKNOWN_VALUE:{field}")
        bounds = contract.get("ranges", {}).get(field)
        if bounds and mapped[field] is not None and not bounds[0] <= mapped[field] <= bounds[1]:
            errors.append(f"OUT_OF_RANGE:{field}")
        if field in contract.get("nonnegative", []) and mapped[field] is not None and mapped[field] < 0:
            warnings.append(f"NEGATIVE_REVIEW:{field}")
    if feed == "reefer_telemetry":
        named_units = [unit for name, unit in (("temp_c", "C"), ("temp_f", "F")) if not empty(row.get(name))]
        if len(named_units) > 1 or (named_units and mapped["temp_unit"] and named_units[0] != mapped["temp_unit"]):
            errors.append("UNIT_METADATA_CONFLICT")
        if named_units and not mapped["temp_unit"]:
            mapped["temp_unit"] = named_units[0]
            warnings.append("UNIT_FROM_COLUMN")
    payload = json.dumps(row, sort_keys=True, default=str, separators=(",", ":"))
    return mapped, sorted(set(errors)), sorted(set(warnings)), hashlib.sha256(payload.encode()).hexdigest()


def temperature_c(value, unit, vendor):
    resolved = unit or CONTRACTS["reefer_telemetry"]["vendor_units"].get(vendor)
    if value is None or resolved not in ("C", "F"):
        return None
    number = Decimal(str(value))
    return (number - 32) * Decimal(5) / Decimal(9) if resolved == "F" else number
