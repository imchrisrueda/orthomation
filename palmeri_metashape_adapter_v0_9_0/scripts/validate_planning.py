"""Validate offline planning drafts, writing only a redacted JSON report to stdout."""

import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

from planning_core import BOUNDARIES, PlanningError, load_planning, validate_planning


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    result = {"structural_status": "FAIL", "structure_valid": False, **BOUNDARIES}
    if len(args) > 1 or (args and args[0].startswith("-")):
        result["error"] = "usage_expected_optional_draft_json"
        code = 2
    else:
        base = Path(__file__).resolve().parents[1] / "planning"
        paths = [Path(args[0])] if args else [base / "_template_flight_contract.json", base / "evaluation_protocol.json"]
        try:
            reports = [validate_planning(load_planning(path)) for path in paths]
            result = {"structural_status": "PASS", "structure_valid": True, "drafts": reports, **BOUNDARIES}
            code = 0
        except PlanningError as exc:
            result["error"] = str(exc)
            code = 1
    print(json.dumps(result, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
