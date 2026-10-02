"""Strict offline draft validation; never grants execution or reads referenced evidence."""

import datetime
import json
from pathlib import Path
import re

from optimization_core import OPTIMIZATION_CONTRACT, EXECUTION_PHASES


class PlanningError(ValueError):
    """Fixed error codes only: no caller-supplied values in diagnostics."""


def _fail(code):
    raise PlanningError(code)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail("duplicate_json_key")
        result[key] = value
    return result


def _integer(text):
    if len(text.lstrip("-")) > 16:
        _fail("integer_out_of_range")
    return int(text)


def load_planning(path):
    """Read only the explicitly selected draft JSON, not its evidence references."""
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_pairs,
                           parse_int=_integer,
                           parse_float=lambda text: _fail("numeric_type_not_supported"),
                           parse_constant=lambda text: _fail("nonfinite_json"))
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        if isinstance(exc, PlanningError):
            raise
        raise PlanningError("draft_unreadable_or_invalid") from exc
    return value


def _object(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        _fail("draft_fields_invalid")


def _exact(value, expected):
    """Recursive comparison preserves JSON types (True is never the integer 1)."""
    if type(value) is not type(expected):
        _fail("draft_policy_invalid")
    if type(expected) is dict:
        _object(value, expected)
        for key in expected:
            _exact(value[key], expected[key])
    elif type(expected) is list:
        if len(value) != len(expected):
            _fail("draft_policy_invalid")
        for actual, wanted in zip(value, expected):
            _exact(actual, wanted)
    elif value != expected:
        _fail("draft_policy_invalid")


def _text(value):
    return type(value) is str and 0 < len(value) <= 512 and bool(value.strip()) and all(ord(c) >= 32 for c in value)


PROPOSED_REFERENCE = {
    "source": "project_policy", "acceptance": "NOT_GRANTED", "status": "PROPOSED",
    "camera_crs": "EPSG::4326", "marker_crs": "EPSG::25830", "chunk_crs": "EPSG::25830",
    "camera_height": "h_ellipsoidal", "marker_height": "h_ellipsoidal",
    "marker_coordinate_units": "metre", "camera_horizontal_units": "degree",
    "height_units": "metre",
    "roles": {"E1": "GCP", "E3": "GCP", "E4": "GCP", "E6": "GCP", "C2": "CHECK_POINT", "C5": "CHECK_POINT"},
}
EVIDENCE_NAMES = (
    "jobxml", "image_inventory", "human_image_acceptance", "human_exclusions",
    "common_master", "configuration", "marking_and_projections", "sensors_and_initial_calibration",
    "branch_parameters_and_constraints", "datum", "coordinate_epoch",
)
BOUNDARIES = {"execution_authorized": False, "products_authorized": False,
              "geomatic_acceptance": "NOT_GRANTED"}


def default_contract():
    return {
        "schema_version": "planning-1", "artifact_type": "flight_contract", "review_status": "DRAFT",
        "identity": {"campaign_id": None, "flight_date": None, "run_id": None, "version": None,
                     "metashape_version": None},
        "boundaries": dict(BOUNDARIES), "proposed_reference": json.loads(json.dumps(PROPOSED_REFERENCE)),
        "reference_metadata": {"datum": None, "ellipsoidal_height_reference": None, "coordinate_epoch": None,
                               "acceptance": "NOT_GRANTED"},
        "optimization_contract": dict(OPTIMIZATION_CONTRACT),
        "evidence": {name: {"sha256": None, "documentary_source": None} for name in EVIDENCE_NAMES},
        "expected_counts": {"cameras": None, "transform_components": None},
        "phases": {phase: {"status": "REVIEW_REQUIRED", "documentary_source": None} for phase in EXECUTION_PHASES},
    }


def default_protocol():
    return {
        "schema_version": "planning-1", "artifact_type": "evaluation_protocol", "review_status": "DRAFT",
        "boundaries": dict(BOUNDARIES), "proposal_status": "HUMAN_ACCEPTANCE_REQUIRED_FACTS_9_OPEN",
        "geometry_stage": {
            "gate": "BEFORE_PRODUCTS", "selection": "HUMAN_ONLY_NO_RANKING_OR_THRESHOLDS",
            "existing_metric_sources": ["metrics.marker_summary_by_role", "metrics.check_points",
                                        "metrics.marker_reprojection_all", "metrics.marker_reprojection_by_role",
                                        "metrics.tie_points", "metrics.calibration_by_sensor_key"],
            "check_points": ["C2", "C5"], "gcp_interpretation": "INTERNAL_ADJUSTMENT_SEPARATE_FROM_CP",
            "cp_reporting": {"individual_residuals": True, "bias_axes": ["x", "y", "z"],
                             "rmse_axes": ["x", "y", "z", "xy", "3d"]},
            "comparability": list(EVIDENCE_NAMES[:9]),
            "reprojection_interpretation": "PIXEL_CONSISTENCY_NOT_EXTERNAL_ACCURACY",
            "calibration_interpretation": "DIAGNOSTIC_CHANGE_NOT_PROOF_OF_OVERFITTING",
        },
        "product_stage": {
            "gate": "AFTER_RECORDED_HUMAN_GEOMETRIC_SELECTION_AND_PRODUCT_AUTHORIZATION",
            "metrics_to_specify": ["density", "completeness", "noise", "GSD", "DSM_DTM", "resolution",
                                   "NoData", "seamlines", "radiometry", "coverage", "3D"],
            "algorithms_or_thresholds_defined": False,
        },
        "conventions": {
            "residual_sign": "estimated-reference", "residual_frame": "COMPARATOR_LOCAL_FRAME_AT_ESTIMATED_POSITION",
            "residual_units": "metre", "reprojection_units": "pixel",
            "calibration_units": "native_per_parameter",
            "crs_25830_deltas": "SEPARATE_DIAGNOSTIC_NOT_FOR_RMSE",
            "branch_delta": "GCP_P1-GCP_ONLY", "adjustment_height": "h_ellipsoidal",
            "orthometric_height": "H_ONLY_BY_EXPLICIT_VALIDATED_POSTERIOR_TRANSFORMATION",
        },
        "uncertainty": {
            "two_cp": "EXPLORATORY_NOT_ROBUST_CHARACTERIZATION", "spatial_extrapolation": False,
            "confidence_intervals_from_two_cp": False, "statistical_thresholds_defined": False,
        },
    }


def _report(kind, missing):
    return {"artifact_type": kind, "structural_status": "PASS", "structure_valid": True,
            "evidence_complete": not missing, "missing_evidence": missing,
            "review_status": "REVIEW_REQUIRED", "operational_status": "NOT_EXECUTABLE",
            "evidence_verified": False,
            "evidence_completeness_meaning": "DECLARED_FIELDS_ONLY_NOT_ACCEPTANCE_OR_COMPARABILITY", **BOUNDARIES}


def validate_contract(value):
    template = default_contract()
    _object(value, template)
    if type(value["review_status"]) is not str or value["review_status"] not in {"DRAFT", "REVIEW_REQUIRED", "REJECTED"}:
        _fail("review_status_invalid")
    for key in ("schema_version", "artifact_type", "boundaries", "proposed_reference", "optimization_contract"):
        _exact(value[key], template[key])
    missing = []
    _object(value["identity"], template["identity"])
    for key, item in value["identity"].items():
        if item is None:
            missing.append("identity." + key)
        elif not _text(item):
            _fail("identity_invalid")
        elif key == "metashape_version" and not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", item):
            _fail("metashape_version_invalid")
        elif key == "flight_date":
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", item):
                _fail("flight_date_invalid")
            try:
                datetime.date.fromisoformat(item)
            except ValueError:
                _fail("flight_date_invalid")
    _object(value["evidence"], EVIDENCE_NAMES)
    for name in EVIDENCE_NAMES:
        record = value["evidence"][name]
        _object(record, ("sha256", "documentary_source"))
        for key, item in record.items():
            if item is None:
                missing.append("evidence." + name + "." + key)
            elif key == "sha256":
                if type(item) is not str or not re.fullmatch(r"[0-9a-fA-F]{64}", item):
                    _fail("evidence_hash_invalid")
            elif not _text(item):
                _fail("evidence_source_invalid")
    _object(value["expected_counts"], template["expected_counts"])
    for key, item in value["expected_counts"].items():
        if item is None:
            missing.append("expected_counts." + key)
        elif type(item) is not int or not 0 < item <= 10**12:
            _fail("expected_count_invalid")
    metadata = value["reference_metadata"]
    _object(metadata, template["reference_metadata"])
    _exact(metadata["acceptance"], "NOT_GRANTED")
    for key in ("datum", "ellipsoidal_height_reference", "coordinate_epoch"):
        item = metadata[key]
        if item is None:
            missing.append("reference_metadata." + key)
        elif not _text(item):
            _fail("reference_metadata_invalid")
        else:
            if key == "coordinate_epoch" and not re.fullmatch(r"[0-9]{4}(?:\.[0-9]{1,8})?", item):
                _fail("coordinate_epoch_format_invalid")
            source_name = "coordinate_epoch" if key == "coordinate_epoch" else "datum"
            if value["evidence"][source_name]["documentary_source"] is None:
                _fail("reference_metadata_source_missing")
    _object(value["phases"], EXECUTION_PHASES)
    for phase in EXECUTION_PHASES:
        record = value["phases"][phase]
        _object(record, ("status", "documentary_source"))
        if type(record["status"]) is not str or record["status"] not in {"REVIEW_REQUIRED", "BLOCKED"}:
            _fail("phase_status_invalid")
        if record["documentary_source"] is None:
            missing.append("phases." + phase + ".documentary_source")
        elif not _text(record["documentary_source"]):
            _fail("phase_source_invalid")
    report = _report("flight_contract", missing)
    report["source_review_status"] = value["review_status"]
    return report


def validate_protocol(value):
    _exact(value, default_protocol())
    report = _report("evaluation_protocol", ["human_protocol_acceptance"])
    report["source_review_status"] = value["review_status"]
    return report


def validate_planning(value):
    if type(value) is not dict:
        _fail("draft_not_object")
    kind = value.get("artifact_type")
    if kind == "flight_contract":
        return validate_contract(value)
    if kind == "evaluation_protocol":
        return validate_protocol(value)
    if kind == "common_campaign":
        from common_campaign_core import validate_common_campaign
        return validate_common_campaign(value)
    _fail("artifact_type_invalid")
