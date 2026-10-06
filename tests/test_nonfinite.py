import json
from pipeline.contracts import json_safe


def test_quarantine_payload_supports_nonfinite_source_values():
    safe = json_safe({"quantity":float("inf"),"reading":float("nan")})
    assert json.loads(json.dumps(safe,allow_nan=False)) == {"quantity":"inf","reading":"nan"}
