import contextlib
import copy
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from compare_branch_metrics import main
from comparison_core import (
    COORDINATE_CONVENTION,
    PROJECTED_COORDINATE_DELTA_CONVENTION,
    ComparisonError,
    compare_reports,
)
from optimization_core import CALIBRATION_PARAMETERS, OPTIMIZATION_CONTRACT


HASHES = {
    "job": "1" * 64,
    "persisted": "2" * 64,
    "live": "3" * 64,
    "common": "4" * 64,
    "post_gcp": "5" * 64,
    "post_p1": "6" * 64,
    "configuration": "7" * 64,
    "preflight": "8" * 64,
    "optimization": "9" * 64,
}
ROLES = {
    "E1": "GCP",
    "C2": "CHECK_POINT",
    "E3": "GCP",
    "E4": "GCP",
    "C5": "CHECK_POINT",
    "E6": "GCP",
}


def reprojection(value, count=2):
    return {"count": count, "mean_px": value, "rms_px": value, "maximum_px": value}


def empty_reprojection():
    return {"count": 0, "mean_px": None, "rms_px": None, "maximum_px": None}


def residual_summary(count, value):
    return {
        "count": count,
        "bias_m": {"x": value, "y": value + 1.0, "z": value + 2.0},
        "rmse_m": {
            "x": abs(value) + 3.0,
            "y": abs(value) + 4.0,
            "z": abs(value) + 5.0,
            "xy": abs(value) + 6.0,
            "3d": abs(value) + 7.0,
        },
    }


def reprojection_from_errors(errors):
    return {
        "count": len(errors),
        "mean_px": sum(errors) / len(errors),
        "rms_px": math.sqrt(sum(value * value for value in errors) / len(errors)),
        "maximum_px": max(errors),
    }


def residual_summary_from_rows(rows):
    count = len(rows)
    return {
        "count": count,
        "bias_m": {
            axis: sum(row["residual_m"][axis] for row in rows) / count
            for axis in ("x", "y", "z")
        },
        "rmse_m": {
            "x": math.sqrt(sum(row["residual_m"]["x"] ** 2 for row in rows) / count),
            "y": math.sqrt(sum(row["residual_m"]["y"] ** 2 for row in rows) / count),
            "z": math.sqrt(sum(row["residual_m"]["z"] ** 2 for row in rows) / count),
            "xy": math.sqrt(sum(
                row["residual_m"]["x"] ** 2 + row["residual_m"]["y"] ** 2
                for row in rows
            ) / count),
            "3d": math.sqrt(sum(
                row["residual_m"]["x"] ** 2
                + row["residual_m"]["y"] ** 2
                + row["residual_m"]["z"] ** 2
                for row in rows
            ) / count),
        },
    }


def calibration_snapshot(f_value):
    parameters = {name: 0.0 for name in CALIBRATION_PARAMETERS}
    parameters["f"] = f_value
    return [{
        "sensor_key": "10",
        "sensor": "P1",
        "type": "Frame",
        "width": 8192,
        "height": 5460,
        "parameters": parameters,
    }]


def calibration_variation(before, after):
    rows = []
    changed = []
    for name in CALIBRATION_PARAMETERS:
        old = before[0]["parameters"][name]
        new = after[0]["parameters"][name]
        delta = new - old
        if abs(delta) > 1e-12:
            changed.append(name)
        fixed = name in {"b1", "b2", "k4", "p3", "p4"}
        rows.append({
            "sensor_key": "10",
            "sensor": "P1",
            "parameter": name,
            "before": old,
            "after": new,
            "delta": delta,
            "authorized_to_vary": not fixed,
            "fixed_tolerance": 1e-12 if fixed else None,
            "within_fixed_tolerance": True if fixed else None,
        })
    return {
        "rows": rows,
        "inferred_changed_parameters": changed,
        "api_effective_parameter_set_available": False,
        "issues": [],
    }


def marker_row(label, offset):
    role = ROLES[label]
    projections = [
        {"camera": "IMG_001.JPG", "dx_px": 1.0 + offset, "dy_px": 0.0,
         "error_px": 1.0 + offset, "pinned": True},
        {"camera": "IMG_002.JPG", "dx_px": 0.0, "dy_px": 2.0 + offset,
         "error_px": 2.0 + offset, "pinned": True},
    ]
    return {
        "label": label,
        "role": role,
        "reference_enabled": role == "GCP",
        "reference_xyz_m": [100.0, 200.0, 650.0],
        "estimated_xyz_m": [100.1 + offset, 200.1 + offset, 650.1 + offset],
        "projected_coordinate_delta_m": {
            "easting": 0.1 + offset,
            "northing": 0.2 + offset,
            "height": 0.3 + offset,
        },
        "residual_m": {
            "x": 0.1 + offset,
            "y": 0.2 + offset,
            "z": 0.3 + offset,
            "xy": math.hypot(0.1 + offset, 0.2 + offset),
            "3d": math.sqrt((0.1 + offset) ** 2 + (0.2 + offset) ** 2 + (0.3 + offset) ** 2),
        },
        "projection_count": 2,
        "reprojection": {
            "summary": {
                "count": 2,
                "mean_px": 1.5 + offset,
                "rms_px": math.sqrt(((1.0 + offset) ** 2 + (2.0 + offset) ** 2) / 2),
                "maximum_px": 2.0 + offset,
            },
            "individual": projections,
        },
    }


def report(branch, offset):
    markers = [marker_row(label, offset) for label in ROLES]
    before = calibration_snapshot(100.0)
    after = calibration_snapshot(101.0 + offset)
    tie_per_camera = [
        {"camera": "IMG_001.JPG", "valid_projection_count": 10,
         "reprojection": reprojection(0.5 + offset, count=10)},
        {"camera": "IMG_002.JPG", "valid_projection_count": 10,
         "reprojection": reprojection(0.6 + offset, count=10)},
    ]
    marker_errors = [
        projection["error_px"]
        for marker in markers
        for projection in marker["reprojection"]["individual"]
    ]
    role_rows = {
        role: [marker for marker in markers if marker["role"] == role]
        for role in ("GCP", "CHECK_POINT")
    }
    role_errors = {
        role: [
            projection["error_px"]
            for marker in rows
            for projection in marker["reprojection"]["individual"]
        ]
        for role, rows in role_rows.items()
    }
    tie_count = sum(row["valid_projection_count"] for row in tie_per_camera)
    tie_mean = sum(
        row["reprojection"]["mean_px"] * row["valid_projection_count"]
        for row in tie_per_camera
    ) / tie_count
    tie_rms = math.sqrt(sum(
        row["reprojection"]["rms_px"] ** 2 * row["valid_projection_count"]
        for row in tie_per_camera
    ) / tie_count)
    return {
        "adapter_version": "0.9.0",
        "timestamp_utc": "2026-09-19T12:00:00+00:00",
        "status": "METRICS_EXPORTED",
        "issues": [],
        "selection_performed": False,
        "run_id": "fixed_model_v1",
        "branch": branch,
        "chunk": "RGB",
        "project": "C:/private/project.psx",
        "metashape_version": "2.3.1",
        "python_version": "3.11.9",
        "platform": "synthetic-test",
        "campaign_id": "2025",
        "flight_date": "2025-04-29",
        "jobxml_sha256": HASHES["job"],
        "source_master_persisted_transform_sha256": HASHES["persisted"],
        "source_master_live_transform_sha256": HASHES["live"],
        "source_master_common_12sig_transform_sha256": HASHES["common"],
        "postoptimization_transform_sha256": HASHES["post_gcp" if branch == "GCP_ONLY" else "post_p1"],
        "preflight_report": {"path": "C:/private/preflight.json", "sha256": HASHES["preflight"]},
        "optimization_report": {"path": "C:/private/optimization.json", "sha256": HASHES["optimization"]},
        "configuration": {"path": "C:/private/global.json", "sha256": HASHES["configuration"]},
        "optimization_parameters": dict(OPTIMIZATION_CONTRACT),
        "task_recorded_parameters": dict(OPTIMIZATION_CONTRACT),
        "effective_parameter_set": {
            "api_available": False,
            "value": None,
            "note": "Metashape API does not expose the effective set.",
        },
        "additional_corrections": {
            "requested": False,
            "full_posthoc_coefficient_api_available": False,
            "verified_absent_with_observable_api": True,
            "task_retained_fit_corrections_false": True,
            "sensor_photo_parameters_empty_before": True,
            "sensor_photo_parameters_empty_after": True,
            "note": "Observable surfaces checked.",
        },
        "counts": {
            "cameras": 2,
            "aligned_cameras": 2,
            "markers": 6,
            "marker_projections": 12,
            "valid_tie_points": 10,
            "valid_tie_point_projections": 20,
        },
        "markers": {
            "coordinate_convention": COORDINATE_CONVENTION,
            "projected_coordinate_delta_convention": PROJECTED_COORDINATE_DELTA_CONVENTION,
            "individual": markers,
            "summary_by_role": {
                role: residual_summary_from_rows(rows) for role, rows in role_rows.items()
            },
            "check_points": {
                label: copy.deepcopy(next(row for row in markers if row["label"] == label))
                for label in ("C2", "C5")
            },
            "marker_reprojection_all": reprojection_from_errors(marker_errors),
            "marker_reprojection_by_role": {
                role: reprojection_from_errors(errors) for role, errors in role_errors.items()
            },
        },
        "tie_points": {
            "valid_tie_point_count": 10,
            "valid_track_count_with_projection": 10,
            "raw_track_count": 12,
            "valid_projection_count": 20,
            "aligned_camera_count": 2,
            "reprojection": {
                "count": tie_count,
                "mean_px": tie_mean,
                "rms_px": tie_rms,
                "maximum_px": max(row["reprojection"]["maximum_px"] for row in tie_per_camera),
            },
            "per_camera": tie_per_camera,
        },
        "calibration_before": before,
        "calibration_after": after,
        "calibration_variation": calibration_variation(before, after),
        "next_action": "Independent geomatic review; this exporter does not select a branch.",
    }


class CompareBranchMetricsTests(unittest.TestCase):
    def setUp(self):
        self.gcp = report("GCP_ONLY", 0.0)
        self.p1 = report("GCP_P1", 0.25)
        self.input_hashes = ["a" * 64, "b" * 64]
        self.paths = [ROOT / "tests" / ".test_metrics_a.json", ROOT / "tests" / ".test_metrics_b.json"]

    def tearDown(self):
        for path in self.paths:
            path.unlink(missing_ok=True)

    def assert_fail(self, left=None, right=None):
        with self.assertRaises(ComparisonError):
            compare_reports(
                self.gcp if left is None else left,
                self.p1 if right is None else right,
                input_hashes=self.input_hashes,
            )

    def test_success_is_order_independent_and_delta_sign_is_p1_minus_gcp(self):
        forward = compare_reports(self.gcp, self.p1, input_hashes=self.input_hashes)
        reverse = compare_reports(self.p1, self.gcp, input_hashes=list(reversed(self.input_hashes)))
        self.assertEqual(forward, reverse)
        self.assertEqual(forward["status"], "OBJECTIVE_COMPARISON_READY")
        self.assertFalse(forward["selection_performed"])
        self.assertTrue(forward["human_decision_required"])
        self.assertFalse(forward["products_authorized"])
        delta = forward["metrics"]["check_points"]["C2"]["delta_GCP_P1_minus_GCP_ONLY"]
        self.assertAlmostEqual(delta["residual_m"]["x"], 0.25)
        calibration_delta = forward["metrics"]["calibration_by_sensor_key"]["10"]["parameters"]["f"]["after"]
        self.assertAlmostEqual(calibration_delta["delta_GCP_P1_minus_GCP_ONLY"], 0.25)
        self.assertEqual(
            forward["provenance"]["input_report_sha256_by_branch"],
            {"GCP_ONLY": "a" * 64, "GCP_P1": "b" * 64},
        )

    def test_duplicate_or_invalid_branches_fail(self):
        self.assert_fail(self.gcp, copy.deepcopy(self.gcp))
        invalid = copy.deepcopy(self.p1)
        invalid["branch"] = "OTHER"
        self.assert_fail(self.gcp, invalid)

    def test_invalid_status_issues_and_selection_fail(self):
        for key, value in (("status", "FAIL"), ("issues", ["problem"]), ("selection_performed", True)):
            with self.subTest(key=key):
                invalid = copy.deepcopy(self.p1)
                invalid[key] = value
                self.assert_fail(self.gcp, invalid)

    def test_provenance_version_configuration_master_and_contract_mismatches_fail(self):
        mutations = [
            ("run_id", "other"),
            ("jobxml_sha256", "a" * 64),
            ("source_master_live_transform_sha256", "b" * 64),
            ("metashape_version", "2.4.0"),
        ]
        for key, value in mutations:
            with self.subTest(key=key):
                invalid = copy.deepcopy(self.p1)
                invalid[key] = value
                self.assert_fail(self.gcp, invalid)
        invalid = copy.deepcopy(self.p1)
        invalid["configuration"]["sha256"] = "c" * 64
        self.assert_fail(self.gcp, invalid)
        invalid = copy.deepcopy(self.p1)
        invalid["optimization_parameters"]["adaptive_fitting"] = True
        self.assert_fail(self.gcp, invalid)
        invalid = copy.deepcopy(self.p1)
        invalid["effective_parameter_set"]["api_available"] = True
        self.assert_fail(self.gcp, invalid)
        invalid = copy.deepcopy(self.p1)
        invalid["additional_corrections"]["verified_absent_with_observable_api"] = False
        self.assert_fail(self.gcp, invalid)

    def test_marker_roles_enabled_missing_duplicates_and_projection_cameras_fail(self):
        mutations = []
        wrong_role = copy.deepcopy(self.p1)
        wrong_role["markers"]["individual"][0]["role"] = "CHECK_POINT"
        mutations.append(wrong_role)
        wrong_enabled = copy.deepcopy(self.p1)
        wrong_enabled["markers"]["individual"][0]["reference_enabled"] = False
        mutations.append(wrong_enabled)
        missing = copy.deepcopy(self.p1)
        missing["markers"]["individual"].pop()
        mutations.append(missing)
        duplicated = copy.deepcopy(self.p1)
        duplicated["markers"]["individual"][-1]["label"] = "E1"
        mutations.append(duplicated)
        camera = copy.deepcopy(self.p1)
        camera["markers"]["individual"][0]["reprojection"]["individual"][0]["camera"] = "OTHER.JPG"
        mutations.append(camera)
        projection = copy.deepcopy(self.p1)
        projection["markers"]["individual"][0]["projection_count"] = 3
        mutations.append(projection)
        for index, invalid in enumerate(mutations):
            with self.subTest(index=index):
                self.assert_fail(self.gcp, invalid)

    def test_missing_or_duplicate_tie_camera_and_calibration_sensor_fail(self):
        invalid = copy.deepcopy(self.p1)
        invalid["tie_points"]["per_camera"].pop()
        self.assert_fail(self.gcp, invalid)
        invalid = copy.deepcopy(self.p1)
        invalid["tie_points"]["per_camera"][1]["camera"] = "IMG_001.JPG"
        self.assert_fail(self.gcp, invalid)
        invalid = copy.deepcopy(self.p1)
        invalid["calibration_after"].append(copy.deepcopy(invalid["calibration_after"][0]))
        self.assert_fail(self.gcp, invalid)
        invalid = copy.deepcopy(self.p1)
        invalid["calibration_after"][0]["sensor_key"] = "11"
        self.assert_fail(self.gcp, invalid)

    def test_nan_inf_null_numeric_string_and_bad_sha_fail(self):
        invalid_values = (float("nan"), float("inf"), None, "1.0")
        for value in invalid_values:
            with self.subTest(value=value):
                invalid = copy.deepcopy(self.p1)
                invalid["markers"]["summary_by_role"]["GCP"]["rmse_m"]["x"] = value
                self.assert_fail(self.gcp, invalid)
        invalid = copy.deepcopy(self.p1)
        invalid["jobxml_sha256"] = "not-a-sha"
        self.assert_fail(self.gcp, invalid)
        invalid = copy.deepcopy(self.p1)
        invalid["counts"]["cameras"] = True
        self.assert_fail(self.gcp, invalid)

    def test_calibration_before_and_fixed_parameters_fail_closed(self):
        invalid = copy.deepcopy(self.p1)
        invalid["calibration_before"][0]["parameters"]["f"] = 99.0
        self.assert_fail(self.gcp, invalid)
        invalid = copy.deepcopy(self.p1)
        invalid["calibration_after"][0]["parameters"]["b1"] = 1e-6
        row = next(row for row in invalid["calibration_variation"]["rows"] if row["parameter"] == "b1")
        row.update(after=1e-6, delta=1e-6, within_fixed_tolerance=False)
        self.assert_fail(self.gcp, invalid)

    def test_exact_coordinate_conventions_are_required(self):
        invalid = copy.deepcopy(self.p1)
        invalid["markers"]["coordinate_convention"] = "UNKNOWN_ORTHOMETRIC"
        self.assert_fail(self.gcp, invalid)
        invalid = copy.deepcopy(self.p1)
        invalid["markers"]["projected_coordinate_delta_convention"] = "UNKNOWN_VERTICAL"
        self.assert_fail(self.gcp, invalid)

    def test_incoherent_derived_summaries_fail(self):
        mutations = []
        residual = copy.deepcopy(self.p1)
        residual["markers"]["individual"][0]["residual_m"]["3d"] += 1.0
        mutations.append(residual)
        role_rmse = copy.deepcopy(self.p1)
        role_rmse["markers"]["summary_by_role"]["GCP"]["rmse_m"]["3d"] += 1.0
        mutations.append(role_rmse)
        marker_summary = copy.deepcopy(self.p1)
        marker_summary["markers"]["individual"][0]["reprojection"]["summary"]["rms_px"] += 1.0
        mutations.append(marker_summary)
        global_reprojection = copy.deepcopy(self.p1)
        global_reprojection["markers"]["marker_reprojection_all"]["mean_px"] += 1.0
        mutations.append(global_reprojection)
        role_reprojection = copy.deepcopy(self.p1)
        role_reprojection["markers"]["marker_reprojection_by_role"]["GCP"]["maximum_px"] += 1.0
        mutations.append(role_reprojection)
        tie_reprojection = copy.deepcopy(self.p1)
        tie_reprojection["tie_points"]["reprojection"]["rms_px"] += 1.0
        mutations.append(tie_reprojection)
        tie_count = copy.deepcopy(self.p1)
        tie_count["tie_points"]["reprojection"]["count"] = 999
        mutations.append(tie_count)
        for index, invalid in enumerate(mutations):
            with self.subTest(index=index):
                self.assert_fail(self.gcp, invalid)

    def test_zero_marker_projections_are_valid_and_do_not_divide_by_zero(self):
        reports = [copy.deepcopy(self.gcp), copy.deepcopy(self.p1)]
        for value in reports:
            for marker in value["markers"]["individual"]:
                marker["projection_count"] = 0
                marker["reprojection"] = {"summary": empty_reprojection(), "individual": []}
            value["markers"]["check_points"] = {
                label: copy.deepcopy(next(
                    marker for marker in value["markers"]["individual"] if marker["label"] == label
                ))
                for label in ("C2", "C5")
            }
            value["markers"]["marker_reprojection_all"] = empty_reprojection()
            value["markers"]["marker_reprojection_by_role"] = {
                "GCP": empty_reprojection(),
                "CHECK_POINT": empty_reprojection(),
            }
            value["counts"]["marker_projections"] = 0
        result = compare_reports(*reports, input_hashes=self.input_hashes)
        self.assertEqual(result["status"], "OBJECTIVE_COMPARISON_READY")
        self.assertEqual(result["metrics"]["marker_reprojection_all"]["GCP_ONLY"]["count"], 0)
        self.assertIsNone(
            result["metrics"]["marker_reprojection_all"]
            ["delta_GCP_P1_minus_GCP_ONLY"]["rms_px"]
        )

    def test_zero_tie_projections_are_valid_and_consistent(self):
        reports = [copy.deepcopy(self.gcp), copy.deepcopy(self.p1)]
        for value in reports:
            value["tie_points"]["valid_projection_count"] = 0
            value["tie_points"]["reprojection"] = empty_reprojection()
            for camera in value["tie_points"]["per_camera"]:
                camera["valid_projection_count"] = 0
                camera["reprojection"] = empty_reprojection()
            value["counts"]["valid_tie_point_projections"] = 0
        result = compare_reports(*reports, input_hashes=self.input_hashes)
        self.assertEqual(result["status"], "OBJECTIVE_COMPARISON_READY")
        self.assertIsNone(
            result["metrics"]["tie_points"]
            ["delta_GCP_P1_minus_GCP_ONLY"]["reprojection"]["maximum_px"]
        )

    def test_unknown_keys_fail_in_critical_objects(self):
        paths = (
            (),
            ("configuration",),
            ("markers",),
            ("markers", "individual", 0),
            ("markers", "individual", 0, "reprojection", "individual", 0),
            ("markers", "summary_by_role", "GCP"),
            ("tie_points",),
            ("tie_points", "per_camera", 0),
            ("calibration_before", 0),
            ("calibration_variation",),
            ("calibration_variation", "rows", 0),
        )
        for path in paths:
            with self.subTest(path=path):
                invalid = copy.deepcopy(self.p1)
                target = invalid
                for part in path:
                    target = target[part]
                target["unknown_field"] = "unexpected"
                self.assert_fail(self.gcp, invalid)

    def test_raw_track_count_null_is_valid_only_when_equal(self):
        left = copy.deepcopy(self.gcp)
        right = copy.deepcopy(self.p1)
        left["tie_points"]["raw_track_count"] = None
        right["tie_points"]["raw_track_count"] = None
        result = compare_reports(left, right, input_hashes=self.input_hashes)
        tie_metrics = result["metrics"]["tie_points"]
        self.assertIsNone(tie_metrics["GCP_ONLY"]["raw_track_count"])
        self.assertIsNone(tie_metrics["GCP_P1"]["raw_track_count"])
        self.assertIsNone(tie_metrics["delta_GCP_P1_minus_GCP_ONLY"]["raw_track_count"])

        right["tie_points"]["raw_track_count"] = 12
        self.assert_fail(left, right)

    def test_input_hashes_are_mandatory_and_strict(self):
        with self.assertRaises(ComparisonError):
            compare_reports(self.gcp, self.p1)
        with self.assertRaises(ComparisonError):
            compare_reports(self.gcp, self.p1, input_hashes=["bad", "b" * 64])

    def test_output_has_no_paths_or_decision_language(self):
        result = compare_reports(self.gcp, self.p1, input_hashes=self.input_hashes)
        encoded = json.dumps(result, ensure_ascii=False, sort_keys=True).lower()
        for forbidden in (
            "c:/private", "\\private", "winner", "preferred", "better", "worse",
            "mejor", "peor", "recomendada", "score", "rank",
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertNotIn("postoptimization_transform_sha256", encoded)
        self.assertEqual(
            result["limitations"],
            [
                "ELLIPSOIDAL_HEIGHT_ONLY",
                "NO_INDEPENDENT_CRS_VALIDATION",
                "NO_PRODUCTS",
                "TWO_CHECK_POINTS_EXPLORATORY",
                "GNSS_AND_P1_RESTRICTIONS_NOT_REVALIDATED",
                "NO_PHOTO_SET_FINGERPRINT",
                "NO_PRODUCTS_STATE_INHERITED_NOT_REDEMONSTRATED",
            ],
        )

    def test_cli_success_and_redacted_failure(self):
        for path, value in zip(self.paths, (self.p1, self.gcp)):
            path.write_text(json.dumps(value), encoding="utf-8")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main([str(self.paths[0]), str(self.paths[1])])
        self.assertEqual(code, 0)
        success = json.loads(stdout.getvalue())
        self.assertEqual(success["status"], "OBJECTIVE_COMPARISON_READY")
        self.assertEqual(
            success["provenance"]["input_report_sha256_by_branch"],
            {
                "GCP_ONLY": hashlib.sha256(self.paths[1].read_bytes()).hexdigest(),
                "GCP_P1": hashlib.sha256(self.paths[0].read_bytes()).hexdigest(),
            },
        )
        self.assertNotIn(str(self.paths[0]), stdout.getvalue())

        self.paths[0].write_text('{"value": NaN}', encoding="utf-8")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main([str(self.paths[0]), str(self.paths[1])])
        failure = json.loads(stdout.getvalue())
        self.assertEqual(code, 1)
        self.assertEqual(failure["status"], "FAIL")
        self.assertNotIn(str(self.paths[0]), stdout.getvalue())
        self.assertNotIn("metrics", failure)

        self.paths[0].write_text('{"status":"FAIL","status":"METRICS_EXPORTED"}', encoding="utf-8")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main([str(self.paths[0]), str(self.paths[1])])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(stdout.getvalue())["errors"], ["duplicate_json_key"])


if __name__ == "__main__":
    unittest.main()
