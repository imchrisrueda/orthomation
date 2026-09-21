"""Strict offline comparison of two reviewed post-optimization metric reports."""

from __future__ import annotations

import json
from hashlib import sha256
import math
from pathlib import Path
import re

from optimization_core import CALIBRATION_PARAMETERS, OPTIMIZATION_CONTRACT


BRANCHES = ("GCP_ONLY", "GCP_P1")
MARKER_ROLES = {
    "E1": "GCP",
    "C2": "CHECK_POINT",
    "E3": "GCP",
    "E4": "GCP",
    "C5": "CHECK_POINT",
    "E6": "GCP",
}
CHECK_POINTS = ("C2", "C5")
ROLE_COUNTS = {"GCP": 4, "CHECK_POINT": 2}
HASH_RE = re.compile(r"[0-9a-f]{64}")
FIXED_PARAMETERS = {"b1", "b2", "k4", "p3", "p4"}
ALLOWED_PARAMETERS = set(CALIBRATION_PARAMETERS) - FIXED_PARAMETERS
FIXED_TOLERANCE = 1e-12
NUMERIC_REL_TOLERANCE = 1e-12
NUMERIC_ABS_TOLERANCE = 1e-12
COORDINATE_CONVENTION = (
    "estimated minus reference, transformed to the local Cartesian frame at the estimated "
    "marker position following Agisoft save_estimated_reference.py; x/y/z are local-frame "
    "components in metres"
)
PROJECTED_COORDINATE_DELTA_CONVENTION = (
    "estimated minus reference directly in marker CRS (EPSG:25830 easting/northing and "
    "ellipsoidal height), exported separately and not used for RMSE"
)
TOP_LEVEL_KEYS = {
    "adapter_version", "timestamp_utc", "status", "issues", "selection_performed", "run_id",
    "branch", "chunk", "project", "metashape_version", "python_version", "platform",
    "campaign_id", "flight_date", "jobxml_sha256",
    "source_master_persisted_transform_sha256", "source_master_live_transform_sha256",
    "source_master_common_12sig_transform_sha256", "postoptimization_transform_sha256",
    "preflight_report", "optimization_report", "configuration", "optimization_parameters",
    "task_recorded_parameters", "effective_parameter_set", "additional_corrections", "counts",
    "markers", "tie_points", "calibration_before", "calibration_after",
    "calibration_variation", "next_action",
}


class ComparisonError(ValueError):
    """A stable, redacted validation failure."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _fail(code):
    raise ComparisonError(code)


def _pairs_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail("duplicate_json_key")
        result[key] = value
    return result


def load_metrics_json(path):
    """Load strict JSON without exposing a local path in failures."""
    try:
        text = Path(path).read_text(encoding="utf-8")
        value = json.loads(
            text,
            object_pairs_hook=_pairs_object,
            parse_constant=lambda _value: _fail("non_finite_json_number"),
        )
    except ComparisonError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError):
        _fail("input_json_invalid")
    if type(value) is not dict:
        _fail("input_must_be_object")
    _reject_nonfinite(value)
    return value


def sha256_file(path):
    digest = sha256()
    try:
        with Path(path).open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError:
        _fail("input_json_invalid")
    return digest.hexdigest()


def _reject_nonfinite(value):
    if type(value) is float and not math.isfinite(value):
        _fail("non_finite_number")
    if type(value) is dict:
        for item in value.values():
            _reject_nonfinite(item)
    elif type(value) is list:
        for item in value:
            _reject_nonfinite(item)


def _strict_equal(left, right):
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(_strict_equal(left[key], right[key]) for key in left)
    if type(left) is list:
        return len(left) == len(right) and all(_strict_equal(a, b) for a, b in zip(left, right))
    return left == right


def _dict(value, code):
    if type(value) is not dict:
        _fail(code)
    return value


def _list(value, code):
    if type(value) is not list:
        _fail(code)
    return value


def _string(value, code):
    if type(value) is not str or not value:
        _fail(code)
    return value


def _bool(value, code):
    if type(value) is not bool:
        _fail(code)
    return value


def _integer(value, code, minimum=0):
    if type(value) is not int or value < minimum:
        _fail(code)
    return value


def _number(value, code, nonnegative=False):
    if type(value) not in (int, float) or not math.isfinite(value):
        _fail(code)
    if nonnegative and value < 0:
        _fail(code)
    return value


def _hash(value, code):
    if type(value) is not str or HASH_RE.fullmatch(value) is None:
        _fail(code)
    return value


def _exact_keys(value, keys, code):
    value = _dict(value, code)
    if set(value) != set(keys):
        _fail(code)
    return value


def _close(left, right):
    return math.isclose(
        float(left), float(right),
        rel_tol=NUMERIC_REL_TOLERANCE,
        abs_tol=NUMERIC_ABS_TOLERANCE,
    )


def _require_close(left, right, code):
    _number(left, code)
    _number(right, code)
    if not _close(left, right):
        _fail(code)


def _validate_optimization_contract(value, code):
    value = _exact_keys(value, OPTIMIZATION_CONTRACT, code)
    for key, expected in OPTIMIZATION_CONTRACT.items():
        if type(value[key]) is not bool or value[key] is not expected:
            _fail(code)


def _validate_reprojection(value, code):
    value = _exact_keys(value, ("count", "mean_px", "rms_px", "maximum_px"), code)
    count = _integer(value["count"], code)
    if count == 0:
        if any(value[key] is not None for key in ("mean_px", "rms_px", "maximum_px")):
            _fail(code)
    else:
        for key in ("mean_px", "rms_px", "maximum_px"):
            _number(value[key], code, nonnegative=True)
    return value


def _validate_residual_summary(value, expected_count, code):
    value = _exact_keys(value, ("count", "bias_m", "rmse_m"), code)
    if _integer(value["count"], code) != expected_count:
        _fail(code)
    bias = _exact_keys(value["bias_m"], ("x", "y", "z"), code)
    rmse = _exact_keys(value["rmse_m"], ("x", "y", "z", "xy", "3d"), code)
    for item in bias.values():
        _number(item, code)
    for item in rmse.values():
        _number(item, code, nonnegative=True)
    return value


def _validate_xyz(value, code):
    value = _list(value, code)
    if len(value) != 3:
        _fail(code)
    for item in value:
        _number(item, code)
    return value


def _validate_marker_row(row, code):
    row = _exact_keys(
        row,
        (
            "label", "role", "reference_enabled", "reference_xyz_m", "estimated_xyz_m",
            "projected_coordinate_delta_m", "residual_m", "projection_count", "reprojection",
        ),
        code,
    )
    label = _string(row.get("label"), code)
    if label not in MARKER_ROLES or row.get("role") != MARKER_ROLES[label]:
        _fail(code)
    expected_enabled = MARKER_ROLES[label] == "GCP"
    if _bool(row.get("reference_enabled"), code) is not expected_enabled:
        _fail(code)
    _validate_xyz(row.get("reference_xyz_m"), code)
    _validate_xyz(row.get("estimated_xyz_m"), code)
    projected = _exact_keys(
        row.get("projected_coordinate_delta_m"), ("easting", "northing", "height"), code
    )
    for item in projected.values():
        _number(item, code)
    residual = _exact_keys(row.get("residual_m"), ("x", "y", "z", "xy", "3d"), code)
    for key, item in residual.items():
        _number(item, code, nonnegative=key in ("xy", "3d"))
    _require_close(residual["xy"], math.hypot(residual["x"], residual["y"]), code)
    _require_close(
        residual["3d"],
        math.sqrt(residual["x"] ** 2 + residual["y"] ** 2 + residual["z"] ** 2),
        code,
    )
    projection_count = _integer(row.get("projection_count"), code)
    reprojection = _exact_keys(row.get("reprojection"), ("summary", "individual"), code)
    summary = _validate_reprojection(reprojection.get("summary"), code)
    individual = _list(reprojection.get("individual"), code)
    if len(individual) != projection_count or summary["count"] != projection_count:
        _fail(code)
    cameras = []
    errors = []
    for projection in individual:
        projection = _exact_keys(
            projection, ("camera", "dx_px", "dy_px", "error_px", "pinned"), code
        )
        camera = _string(projection.get("camera"), code)
        cameras.append(camera)
        dx = _number(projection.get("dx_px"), code)
        dy = _number(projection.get("dy_px"), code)
        error = _number(projection.get("error_px"), code, nonnegative=True)
        if not math.isclose(error, math.hypot(dx, dy), rel_tol=1e-12, abs_tol=1e-12):
            _fail(code)
        errors.append(error)
        if _bool(projection.get("pinned"), code) is not True:
            _fail(code)
    if len(cameras) != len(set(cameras)):
        _fail(code)
    if errors:
        _require_close(summary["mean_px"], sum(errors) / len(errors), code)
        _require_close(summary["rms_px"], math.sqrt(sum(item * item for item in errors) / len(errors)), code)
        _require_close(summary["maximum_px"], max(errors), code)
    return label, {"row": row, "cameras": sorted(cameras), "errors": errors}


def _validate_markers(value, code):
    value = _exact_keys(
        value,
        (
            "coordinate_convention", "projected_coordinate_delta_convention", "individual",
            "summary_by_role", "check_points", "marker_reprojection_all",
            "marker_reprojection_by_role",
        ),
        code,
    )
    if value["coordinate_convention"] != COORDINATE_CONVENTION:
        _fail(code)
    if value["projected_coordinate_delta_convention"] != PROJECTED_COORDINATE_DELTA_CONVENTION:
        _fail(code)
    rows = _list(value.get("individual"), code)
    by_label = {}
    for row in rows:
        label, validated = _validate_marker_row(row, code)
        if label in by_label:
            _fail(code)
        by_label[label] = validated
    if set(by_label) != set(MARKER_ROLES):
        _fail(code)
    summaries = _exact_keys(value.get("summary_by_role"), ROLE_COUNTS, code)
    reprojection_by_role = _exact_keys(value.get("marker_reprojection_by_role"), ROLE_COUNTS, code)
    for role, count in ROLE_COUNTS.items():
        summary = _validate_residual_summary(summaries[role], count, code)
        role_rows = [item["row"]["residual_m"] for item in by_label.values() if item["row"]["role"] == role]
        for axis in ("x", "y", "z"):
            _require_close(summary["bias_m"][axis], sum(row[axis] for row in role_rows) / count, code)
            _require_close(
                summary["rmse_m"][axis],
                math.sqrt(sum(row[axis] ** 2 for row in role_rows) / count),
                code,
            )
        _require_close(
            summary["rmse_m"]["xy"],
            math.sqrt(sum(row["x"] ** 2 + row["y"] ** 2 for row in role_rows) / count),
            code,
        )
        _require_close(
            summary["rmse_m"]["3d"],
            math.sqrt(sum(row["x"] ** 2 + row["y"] ** 2 + row["z"] ** 2 for row in role_rows) / count),
            code,
        )
        role_projection_count = sum(
            item["row"]["projection_count"]
            for item in by_label.values() if item["row"]["role"] == role
        )
        role_reprojection = _validate_reprojection(reprojection_by_role[role], code)
        if role_reprojection["count"] != role_projection_count:
            _fail(code)
        role_errors = [
            error for item in by_label.values() if item["row"]["role"] == role
            for error in item["errors"]
        ]
        if role_errors:
            _require_close(role_reprojection["mean_px"], sum(role_errors) / len(role_errors), code)
            _require_close(
                role_reprojection["rms_px"],
                math.sqrt(sum(item * item for item in role_errors) / len(role_errors)),
                code,
            )
            _require_close(role_reprojection["maximum_px"], max(role_errors), code)
    total_projection_count = sum(item["row"]["projection_count"] for item in by_label.values())
    all_reprojection = _validate_reprojection(value.get("marker_reprojection_all"), code)
    if all_reprojection["count"] != total_projection_count:
        _fail(code)
    all_errors = [error for item in by_label.values() for error in item["errors"]]
    if all_errors:
        _require_close(all_reprojection["mean_px"], sum(all_errors) / len(all_errors), code)
        _require_close(
            all_reprojection["rms_px"],
            math.sqrt(sum(item * item for item in all_errors) / len(all_errors)),
            code,
        )
        _require_close(all_reprojection["maximum_px"], max(all_errors), code)
    check_points = _exact_keys(value.get("check_points"), CHECK_POINTS, code)
    for label in CHECK_POINTS:
        if not _strict_equal(check_points[label], by_label[label]["row"]):
            _fail(code)
    return {"raw": value, "by_label": by_label}


def _validate_tie_points(value, code):
    value = _exact_keys(
        value,
        (
            "valid_tie_point_count", "valid_track_count_with_projection", "raw_track_count",
            "valid_projection_count", "aligned_camera_count", "reprojection", "per_camera",
        ),
        code,
    )
    for key in (
        "valid_tie_point_count", "valid_track_count_with_projection", "valid_projection_count",
        "aligned_camera_count",
    ):
        _integer(value.get(key), code)
    raw_track_count = value.get("raw_track_count")
    if raw_track_count is not None:
        _integer(raw_track_count, code)
    aggregate = _validate_reprojection(value.get("reprojection"), code)
    per_camera = _list(value.get("per_camera"), code)
    cameras = {}
    for row in per_camera:
        row = _exact_keys(row, ("camera", "valid_projection_count", "reprojection"), code)
        camera = _string(row.get("camera"), code)
        if camera in cameras:
            _fail(code)
        count = _integer(row.get("valid_projection_count"), code)
        summary = _validate_reprojection(row.get("reprojection"), code)
        if summary["count"] != count:
            _fail(code)
        cameras[camera] = row
    if len(cameras) != value["aligned_camera_count"]:
        _fail(code)
    if sum(row["valid_projection_count"] for row in cameras.values()) != value["valid_projection_count"]:
        _fail(code)
    total = value["valid_projection_count"]
    if aggregate["count"] != total:
        _fail(code)
    if total:
        weighted_mean = sum(
            row["reprojection"]["mean_px"] * row["valid_projection_count"]
            for row in cameras.values()
        ) / total
        weighted_rms = math.sqrt(sum(
            row["reprojection"]["rms_px"] ** 2 * row["valid_projection_count"]
            for row in cameras.values()
        ) / total)
        maximum = max(row["reprojection"]["maximum_px"] for row in cameras.values())
        _require_close(aggregate["mean_px"], weighted_mean, code)
        _require_close(aggregate["rms_px"], weighted_rms, code)
        _require_close(aggregate["maximum_px"], maximum, code)
    return {"raw": value, "cameras": cameras}


def _validate_calibration_snapshot(value, code):
    rows = _list(value, code)
    by_sensor = {}
    for row in rows:
        row = _exact_keys(
            row, ("sensor_key", "sensor", "type", "width", "height", "parameters"), code
        )
        key = _string(row.get("sensor_key"), code)
        if key in by_sensor:
            _fail(code)
        metadata = {
            "sensor": _string(row.get("sensor"), code),
            "type": _string(row.get("type"), code),
            "width": _integer(row.get("width"), code, minimum=1),
            "height": _integer(row.get("height"), code, minimum=1),
        }
        parameters = _exact_keys(row.get("parameters"), CALIBRATION_PARAMETERS, code)
        for item in parameters.values():
            _number(item, code)
        by_sensor[key] = {"metadata": metadata, "parameters": parameters}
    if not by_sensor:
        _fail(code)
    return by_sensor


def _validate_calibration_variation(value, before, after, code):
    value = _exact_keys(
        value,
        ("rows", "inferred_changed_parameters", "api_effective_parameter_set_available", "issues"),
        code,
    )
    if value.get("issues") != [] or type(value.get("issues")) is not list:
        _fail(code)
    if value.get("api_effective_parameter_set_available") is not False:
        _fail(code)
    changed = _list(value.get("inferred_changed_parameters"), code)
    if any(type(item) is not str or item not in CALIBRATION_PARAMETERS for item in changed):
        _fail(code)
    rows = _list(value.get("rows"), code)
    expected_pairs = {(sensor, name) for sensor in before for name in CALIBRATION_PARAMETERS}
    by_pair = {}
    for row in rows:
        row = _exact_keys(
            row,
            (
                "sensor_key", "sensor", "parameter", "before", "after", "delta",
                "authorized_to_vary", "fixed_tolerance", "within_fixed_tolerance",
            ),
            code,
        )
        sensor = _string(row.get("sensor_key"), code)
        name = _string(row.get("parameter"), code)
        pair = (sensor, name)
        if pair in by_pair or pair not in expected_pairs or sensor not in after:
            _fail(code)
        if row.get("sensor") != before[sensor]["metadata"]["sensor"]:
            _fail(code)
        old = _number(row.get("before"), code)
        new = _number(row.get("after"), code)
        delta = _number(row.get("delta"), code)
        if old != before[sensor]["parameters"][name] or new != after[sensor]["parameters"][name]:
            _fail(code)
        if delta != new - old:
            _fail(code)
        authorized = _bool(row.get("authorized_to_vary"), code)
        if authorized is not (name in ALLOWED_PARAMETERS):
            _fail(code)
        if name in FIXED_PARAMETERS:
            if _number(row.get("fixed_tolerance"), code, nonnegative=True) != FIXED_TOLERANCE:
                _fail(code)
            if _bool(row.get("within_fixed_tolerance"), code) is not True:
                _fail(code)
            if abs(delta) > FIXED_TOLERANCE:
                _fail(code)
        elif row.get("fixed_tolerance") is not None or row.get("within_fixed_tolerance") is not None:
            _fail(code)
        by_pair[pair] = row
    if set(by_pair) != expected_pairs:
        _fail(code)
    expected_changed = sorted({name for (_sensor, name), row in by_pair.items() if abs(row["delta"]) > 1e-12})
    if changed != expected_changed:
        _fail(code)
    return by_pair


def _validate_report(report):
    report = _exact_keys(report, TOP_LEVEL_KEYS, "report_invalid")
    _reject_nonfinite(report)
    if report.get("adapter_version") != "0.9.0":
        _fail("adapter_version_invalid")
    if report.get("metashape_version") != "2.3.1":
        _fail("metashape_version_invalid")
    if report.get("status") != "METRICS_EXPORTED":
        _fail("metrics_status_invalid")
    if type(report.get("issues")) is not list or report["issues"] != []:
        _fail("metrics_issues_present")
    if type(report.get("selection_performed")) is not bool or report["selection_performed"] is not False:
        _fail("selection_state_invalid")
    for key in ("run_id", "branch", "campaign_id", "flight_date"):
        _string(report.get(key), f"{key}_invalid")
    for key in (
        "timestamp_utc", "chunk", "project", "python_version", "platform", "next_action",
    ):
        _string(report.get(key), f"{key}_invalid")
    if report["branch"] not in BRANCHES:
        _fail("branch_invalid")
    for key in (
        "jobxml_sha256", "source_master_persisted_transform_sha256",
        "source_master_live_transform_sha256", "source_master_common_12sig_transform_sha256",
        "postoptimization_transform_sha256",
    ):
        _hash(report.get(key), f"{key}_invalid")
    for key in ("preflight_report", "optimization_report", "configuration"):
        container = _exact_keys(report.get(key), ("path", "sha256"), f"{key}_invalid")
        _string(container.get("path"), f"{key}_path_invalid")
        _hash(container.get("sha256"), f"{key}_sha256_invalid")
    _validate_optimization_contract(report.get("optimization_parameters"), "optimization_contract_invalid")
    _validate_optimization_contract(report.get("task_recorded_parameters"), "task_contract_invalid")
    effective = _exact_keys(
        report.get("effective_parameter_set"), ("api_available", "value", "note"),
        "effective_parameter_set_invalid",
    )
    if effective.get("api_available") is not False or effective.get("value") is not None:
        _fail("effective_parameter_set_invalid")
    _string(effective.get("note"), "effective_parameter_set_invalid")
    corrections = _exact_keys(
        report.get("additional_corrections"),
        (
            "requested", "full_posthoc_coefficient_api_available",
            "verified_absent_with_observable_api", "task_retained_fit_corrections_false",
            "sensor_photo_parameters_empty_before", "sensor_photo_parameters_empty_after", "note",
        ),
        "additional_corrections_invalid",
    )
    required_corrections = {
        "requested": False,
        "full_posthoc_coefficient_api_available": False,
        "verified_absent_with_observable_api": True,
        "task_retained_fit_corrections_false": True,
        "sensor_photo_parameters_empty_before": True,
        "sensor_photo_parameters_empty_after": True,
    }
    for key, expected in required_corrections.items():
        if type(corrections.get(key)) is not bool or corrections[key] is not expected:
            _fail("additional_corrections_invalid")
    _string(corrections.get("note"), "additional_corrections_invalid")
    counts = _exact_keys(
        report.get("counts"),
        ("cameras", "aligned_cameras", "markers", "marker_projections", "valid_tie_points", "valid_tie_point_projections"),
        "counts_invalid",
    )
    for item in counts.values():
        _integer(item, "counts_invalid")
    if counts["markers"] != len(MARKER_ROLES):
        _fail("counts_invalid")
    markers = _validate_markers(report.get("markers"), "markers_invalid")
    tie_points = _validate_tie_points(report.get("tie_points"), "tie_points_invalid")
    if tie_points["raw"]["aligned_camera_count"] != counts["aligned_cameras"]:
        _fail("counts_invalid")
    if tie_points["raw"]["valid_tie_point_count"] != counts["valid_tie_points"]:
        _fail("counts_invalid")
    if tie_points["raw"]["valid_projection_count"] != counts["valid_tie_point_projections"]:
        _fail("counts_invalid")
    if sum(item["row"]["projection_count"] for item in markers["by_label"].values()) != counts["marker_projections"]:
        _fail("counts_invalid")
    before = _validate_calibration_snapshot(report.get("calibration_before"), "calibration_before_invalid")
    after = _validate_calibration_snapshot(report.get("calibration_after"), "calibration_after_invalid")
    if set(before) != set(after):
        _fail("calibration_sensor_set_invalid")
    for sensor in before:
        if not _strict_equal(before[sensor]["metadata"], after[sensor]["metadata"]):
            _fail("calibration_sensor_metadata_invalid")
    variation = _validate_calibration_variation(
        report.get("calibration_variation"), before, after, "calibration_variation_invalid"
    )
    return {
        "raw": report,
        "counts": counts,
        "markers": markers,
        "tie_points": tie_points,
        "calibration_before": before,
        "calibration_after": after,
        "calibration_variation": variation,
    }


def _pair(left, right):
    if type(left) is dict and type(right) is dict and set(left) == set(right):
        delta = {key: _subtract(left[key], right[key]) for key in left}
    else:
        delta = _subtract(left, right)
    return {
        "GCP_ONLY": left,
        "GCP_P1": right,
        "delta_GCP_P1_minus_GCP_ONLY": delta,
    }


def _subtract(left, right):
    if left is None and right is None:
        return None
    if type(left) is dict and type(right) is dict and set(left) == set(right):
        return {key: _subtract(left[key], right[key]) for key in left}
    if type(left) not in (int, float) or type(right) not in (int, float):
        _fail("approved_metric_shape_invalid")
    return right - left


def _select_tie_metrics(value):
    return {
        key: value[key]
        for key in (
            "valid_tie_point_count", "valid_track_count_with_projection",
            "raw_track_count", "valid_projection_count", "aligned_camera_count", "reprojection",
        )
    }


def _select_check_point(row):
    return {
        "residual_m": row["residual_m"],
        "projected_coordinate_delta_m": row["projected_coordinate_delta_m"],
        "projection_count": row["projection_count"],
        "reprojection": row["reprojection"]["summary"],
    }


def compare_reports(first, second, input_hashes=None):
    """Return an allowlisted objective comparison or raise ComparisonError."""
    if type(input_hashes) not in (list, tuple) or len(input_hashes) != 2:
        _fail("input_report_hashes_missing")
    for value in input_hashes:
        _hash(value, "input_report_sha256_invalid")
    validated = [_validate_report(first), _validate_report(second)]
    by_branch = {}
    input_hash_by_branch = {}
    for report, input_hash in zip(validated, input_hashes):
        branch = report["raw"]["branch"]
        if branch in by_branch:
            _fail("duplicate_branch")
        by_branch[branch] = report
        input_hash_by_branch[branch] = input_hash
    if set(by_branch) != set(BRANCHES):
        _fail("branch_pair_invalid")
    gcp = by_branch["GCP_ONLY"]
    p1 = by_branch["GCP_P1"]

    equal_fields = (
        "run_id", "campaign_id", "flight_date", "jobxml_sha256",
        "source_master_persisted_transform_sha256", "source_master_live_transform_sha256",
        "source_master_common_12sig_transform_sha256", "optimization_parameters",
        "task_recorded_parameters", "effective_parameter_set", "additional_corrections",
    )
    for key in equal_fields:
        if not _strict_equal(gcp["raw"].get(key), p1["raw"].get(key)):
            _fail("cross_branch_provenance_mismatch")
    if gcp["raw"]["configuration"]["sha256"] != p1["raw"]["configuration"]["sha256"]:
        _fail("configuration_mismatch")
    if not _strict_equal(gcp["counts"], p1["counts"]):
        _fail("counts_mismatch")
    for label in MARKER_ROLES:
        left = gcp["markers"]["by_label"][label]
        right = p1["markers"]["by_label"][label]
        if left["row"]["role"] != right["row"]["role"]:
            _fail("marker_role_mismatch")
        if not _strict_equal(left["row"]["reference_xyz_m"], right["row"]["reference_xyz_m"]):
            _fail("marker_reference_mismatch")
        if left["row"]["projection_count"] != right["row"]["projection_count"]:
            _fail("marker_projection_count_mismatch")
        if left["cameras"] != right["cameras"]:
            _fail("marker_projection_camera_mismatch")
    if set(gcp["tie_points"]["cameras"]) != set(p1["tie_points"]["cameras"]):
        _fail("tie_point_camera_mismatch")
    for camera in gcp["tie_points"]["cameras"]:
        if gcp["tie_points"]["cameras"][camera]["valid_projection_count"] != p1["tie_points"]["cameras"][camera]["valid_projection_count"]:
            _fail("tie_point_projection_count_mismatch")
    for key in (
        "valid_tie_point_count", "valid_track_count_with_projection", "raw_track_count",
        "valid_projection_count", "aligned_camera_count",
    ):
        if gcp["tie_points"]["raw"][key] != p1["tie_points"]["raw"][key]:
            _fail("tie_point_count_mismatch")
    if not _strict_equal(gcp["calibration_before"], p1["calibration_before"]):
        _fail("calibration_before_mismatch")

    marker_summary = {
        role: _pair(
            gcp["markers"]["raw"]["summary_by_role"][role],
            p1["markers"]["raw"]["summary_by_role"][role],
        )
        for role in ROLE_COUNTS
    }
    marker_reprojection_by_role = {
        role: _pair(
            gcp["markers"]["raw"]["marker_reprojection_by_role"][role],
            p1["markers"]["raw"]["marker_reprojection_by_role"][role],
        )
        for role in ROLE_COUNTS
    }
    check_points = {
        label: _pair(
            _select_check_point(gcp["markers"]["by_label"][label]["row"]),
            _select_check_point(p1["markers"]["by_label"][label]["row"]),
        )
        for label in CHECK_POINTS
    }
    calibration = {}
    for sensor in sorted(gcp["calibration_before"]):
        calibration[sensor] = {
            "metadata": gcp["calibration_before"][sensor]["metadata"],
            "parameters": {},
        }
        for name in CALIBRATION_PARAMETERS:
            calibration[sensor]["parameters"][name] = {
                "before": _pair(
                    gcp["calibration_before"][sensor]["parameters"][name],
                    p1["calibration_before"][sensor]["parameters"][name],
                ),
                "after": _pair(
                    gcp["calibration_after"][sensor]["parameters"][name],
                    p1["calibration_after"][sensor]["parameters"][name],
                ),
                "variation": _pair(
                    gcp["calibration_variation"][(sensor, name)]["delta"],
                    p1["calibration_variation"][(sensor, name)]["delta"],
                ),
            }

    return {
        "schema_version": "orthomation.objective-branch-comparison/1",
        "status": "OBJECTIVE_COMPARISON_READY",
        "selection_performed": False,
        "human_decision_required": True,
        "geomatic_acceptance": "NOT_GRANTED",
        "products_authorized": False,
        "check_point_count": 2,
        "evidence_scope": "EXPLORATORY_TWO_CHECK_POINTS",
        "limitations": [
            "ELLIPSOIDAL_HEIGHT_ONLY",
            "NO_INDEPENDENT_CRS_VALIDATION",
            "NO_PRODUCTS",
            "TWO_CHECK_POINTS_EXPLORATORY",
            "GNSS_AND_P1_RESTRICTIONS_NOT_REVALIDATED",
            "NO_PHOTO_SET_FINGERPRINT",
            "NO_PRODUCTS_STATE_INHERITED_NOT_REDEMONSTRATED",
        ],
        "provenance": {
            **{
                key: gcp["raw"][key]
                for key in (
                    "adapter_version", "metashape_version", "run_id", "campaign_id", "flight_date",
                    "jobxml_sha256", "source_master_persisted_transform_sha256",
                    "source_master_live_transform_sha256",
                    "source_master_common_12sig_transform_sha256",
                )
            },
            "configuration_sha256": gcp["raw"]["configuration"]["sha256"],
            "input_report_sha256_by_branch": {
                branch: input_hash_by_branch[branch] for branch in BRANCHES
            },
        },
        "metrics": {
            "counts": _pair(gcp["counts"], p1["counts"]),
            "marker_summary_by_role": marker_summary,
            "marker_reprojection_all": _pair(
                gcp["markers"]["raw"]["marker_reprojection_all"],
                p1["markers"]["raw"]["marker_reprojection_all"],
            ),
            "marker_reprojection_by_role": marker_reprojection_by_role,
            "check_points": check_points,
            "tie_points": _pair(
                _select_tie_metrics(gcp["tie_points"]["raw"]),
                _select_tie_metrics(p1["tie_points"]["raw"]),
            ),
            "calibration_by_sensor_key": calibration,
        },
    }


def failure_report(code):
    return {
        "schema_version": "orthomation.objective-branch-comparison/1",
        "status": "FAIL",
        "selection_performed": False,
        "human_decision_required": True,
        "geomatic_acceptance": "NOT_GRANTED",
        "products_authorized": False,
        "errors": [str(code)],
    }
