import json
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from orthomation_core import (
    ValidationError,
    parse_jobxml,
    read_dji_xmp,
    significant_transform_rows,
    transform_fingerprint,
    transform_representation_equivalence,
    transform_rows_fingerprint,
)
from optimization_core import (
    CALIBRATION_PARAMETERS,
    OPTIMIZATION_CONTRACT,
    compare_calibrations,
    reprojection_statistics,
    require_approved_experiment,
    residual_statistics,
    validate_experiment_contract,
    validate_metashape_version,
    validate_optimization_contract,
)


class FakeCamera:
    def __init__(self, label, transform):
        self.label = label
        self.transform = transform


class FakeChunk:
    def __init__(self, cameras):
        self.cameras = cameras


class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.campaign = json.loads((ROOT / "campaigns" / "2025.json").read_text(encoding="utf-8"))
        cls.jobxml = ROOT / cls.campaign["default_jobxml"]

    def test_2025_jobxml_is_valid_and_ellipsoidal(self):
        result = parse_jobxml(
            self.jobxml,
            self.campaign["control_points"],
            self.campaign["jobxml_rules"],
        )
        self.assertEqual(result["geoid"], "EGM08IGN")
        self.assertEqual(len(result["points"]), 6)
        self.assertEqual(result["observation_years"], [2025])
        for point in result["points"].values():
            self.assertEqual(point["survey_method"], "NetworkFix")
            self.assertGreater(point["h_ellipsoid"], point["H_orthometric"])
            self.assertAlmostEqual(point["geoid_separation"], 51.2116, places=3)
            self.assertGreater(point["horizontal_precision"], 0)
            self.assertGreater(point["vertical_precision"], 0)

    def test_wrong_campaign_year_is_rejected(self):
        rules = dict(self.campaign["jobxml_rules"])
        rules["expected_survey_year"] = 2026
        with self.assertRaisesRegex(ValidationError, "observation years"):
            parse_jobxml(self.jobxml, self.campaign["control_points"], rules)

    def test_supplied_2026_jobxml_is_rejected(self):
        campaign = json.loads((ROOT / "campaigns" / "2026.json").read_text(encoding="utf-8"))
        with self.assertRaisesRegex(ValidationError, "observation years"):
            parse_jobxml(
                ROOT / campaign["default_jobxml"],
                campaign["control_points"],
                campaign["jobxml_rules"],
            )

    def test_dji_xmp_packet_reader(self):
        packet = b'''prefix<x:xmpmeta><rdf:RDF><rdf:Description
          drone-dji:GpsStatus="Normal"
          drone-dji:AltitudeType="RtkAlt"
          drone-dji:RtkFlag="50"
          drone-dji:SurveyingMode="1"
          drone-dji:GpsLatitude="40.1"
          drone-dji:GpsLongitude="-3.4"
          drone-dji:AbsoluteAltitude="601.2"
          drone-dji:RtkStdLon="0.02"
          drone-dji:RtkStdLat="0.03"
          drone-dji:RtkStdHgt="0.06"/></rdf:RDF></x:xmpmeta>suffix'''
        path = ROOT / "tests" / ".test_xmp_packet.jpg"
        try:
            path.write_bytes(packet)
            xmp = read_dji_xmp(path)
        finally:
            path.unlink(missing_ok=True)
        self.assertEqual(xmp["drone-dji:AltitudeType"], "RtkAlt")
        self.assertEqual(xmp["drone-dji:RtkFlag"], "50")

    def test_transform_fingerprint_accepts_flat_metashape_matrix_iteration(self):
        flat = FakeChunk([FakeCamera("camera", [1.0, 2.0, 3.0, 4.0])])
        nested = FakeChunk([FakeCamera("camera", [[1.0, 2.0], [3.0, 4.0]])])
        self.assertEqual(transform_fingerprint(flat), transform_fingerprint(nested))

    def test_transform_fingerprint_is_camera_order_independent(self):
        first = FakeCamera("A", None)
        second = FakeCamera("B", [1.0, 0.0, 0.0, 1.0])
        self.assertEqual(
            transform_fingerprint(FakeChunk([first, second])),
            transform_fingerprint(FakeChunk([second, first])),
        )

    def test_fixed_model_optimization_contract_is_exact(self):
        self.assertEqual(validate_optimization_contract(dict(OPTIMIZATION_CONTRACT)), OPTIMIZATION_CONTRACT)
        invalid = dict(OPTIMIZATION_CONTRACT)
        invalid["adaptive_fitting"] = True
        with self.assertRaisesRegex(RuntimeError, "fixed-model contract"):
            validate_optimization_contract(invalid)

    def test_global_config_changes_only_optimization_adaptive_fitting(self):
        config = json.loads((ROOT / "config" / "global.json").read_text(encoding="utf-8"))
        self.assertFalse(config["optimization"]["adaptive_fitting"])
        self.assertTrue(config["metashape"]["alignment_presets"]["MORPHOLOGY_MAX"]["adaptive_fitting"])
        self.assertTrue(config["metashape"]["alignment_presets"]["BASELINE_A0"]["adaptive_fitting"])
        self.assertEqual(config["optimization"], OPTIMIZATION_CONTRACT)

    def test_experiment_is_blocked_until_geomatic_approval(self):
        config = json.loads((ROOT / "config" / "global.json").read_text(encoding="utf-8"))
        config["optimization_experiments"]["fixed_model_v1"]["review_status"] = "REVIEW_REQUIRED"
        with self.assertRaisesRegex(RuntimeError, "geomatic review"):
            require_approved_experiment(config, "fixed_model_v1")

    def test_reviewed_tolerances_and_metashape_version_are_exact(self):
        config = json.loads((ROOT / "config" / "global.json").read_text(encoding="utf-8"))
        experiment = config["optimization_experiments"]["fixed_model_v1"]
        self.assertIs(validate_experiment_contract(experiment), experiment)
        self.assertEqual(validate_metashape_version("2.3.1", "2.3.1"), "2.3.1")
        invalid = dict(experiment)
        invalid["fixed_parameter_absolute_tolerance"] = dict(experiment["fixed_parameter_absolute_tolerance"])
        invalid["fixed_parameter_absolute_tolerance"]["b1"] = float("inf")
        with self.assertRaisesRegex(RuntimeError, "Tolerance b1"):
            validate_experiment_contract(invalid)
        with self.assertRaisesRegex(RuntimeError, "reviewed version"):
            validate_metashape_version("2.4.0", "2.3.1")

    def test_live_transform_contract_is_bound_to_reviewed_version(self):
        config = json.loads((ROOT / "config" / "global.json").read_text(encoding="utf-8"))
        experiment = config["optimization_experiments"]["fixed_model_v1"]
        self.assertEqual(experiment["reviewed_metashape_version"], "2.3.1")
        self.assertEqual(
            experiment["source_master_live_transform_sha256"],
            "e75f994cfff3a0a286ee7e3283b4ae2f202ce7869ee4e42c3b4caf0107831520",
        )
        invalid = dict(experiment)
        invalid["source_master_live_transform_sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "source_master_live_transform_sha256"):
            validate_experiment_contract(invalid)

    @staticmethod
    def transform_contract(persisted, live):
        digits = 12
        return {
            "source_master_transform_sha256": transform_rows_fingerprint(persisted),
            "source_master_live_transform_sha256": transform_rows_fingerprint(live),
            "source_master_common_12sig_transform_sha256": transform_rows_fingerprint(
                significant_transform_rows(persisted, digits)
            ),
            "source_master_equivalence_max_abs_delta": 1e-15,
            "transform_equivalence_significant_digits": digits,
            "transform_equivalence_allowed_difference_indices": [0, 1, 2, 4, 5, 6, 8, 9, 10],
            "expected_camera_count": len(persisted),
            "expected_transform_component_count": sum(len(values) for _, values in persisted),
        }

    @staticmethod
    def equivalent_transform_rows():
        base = [
            0.1234567890123456, 0.0, 0.0, 4.0,
            0.0, 1.0, 0.0, 5.0,
            0.0, 0.0, 1.0, 6.0,
            0.0, 0.0, 0.0, 1.0,
        ]
        live = list(base)
        live[0] += 1e-16
        return [("A", base)], [("A", live)]

    def test_transform_representation_equivalence_accepts_reviewed_roundoff(self):
        persisted, live = self.equivalent_transform_rows()
        result = transform_representation_equivalence(
            persisted, live, self.transform_contract(persisted, live)
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["different_indices"], [0])
        self.assertTrue(result["labels_exactly_equal"])

    def test_transform_representation_rejects_persisted_and_live_hashes(self):
        persisted, live = self.equivalent_transform_rows()
        contract = self.transform_contract(persisted, live)
        contract["source_master_transform_sha256"] = "0" * 64
        contract["source_master_live_transform_sha256"] = "1" * 64
        issues = transform_representation_equivalence(persisted, live, contract)["issues"]
        self.assertTrue(any("Persisted transform fingerprint" in issue for issue in issues))
        self.assertTrue(any("Live transform fingerprint" in issue for issue in issues))

    def test_transform_representation_rejects_camera_count_and_labels(self):
        persisted, live = self.equivalent_transform_rows()
        relabeled = [("B", live[0][1])]
        contract = self.transform_contract(persisted, relabeled)
        contract["expected_camera_count"] = 2
        issues = transform_representation_equivalence(persisted, relabeled, contract)["issues"]
        self.assertTrue(any("Transform cameras" in issue for issue in issues))
        self.assertTrue(any("camera labels differ" in issue for issue in issues))

    def test_transform_representation_rejects_component_count(self):
        persisted, live = self.equivalent_transform_rows()
        contract = self.transform_contract(persisted, live)
        contract["expected_transform_component_count"] += 1
        issues = transform_representation_equivalence(persisted, live, contract)["issues"]
        self.assertTrue(any("Transform components" in issue for issue in issues))

    def test_transform_representation_rejects_translation_and_homogeneous_row_differences(self):
        persisted, live = self.equivalent_transform_rows()
        for index in (3, 12):
            with self.subTest(index=index):
                changed = list(live[0][1])
                changed[index] += 1e-14
                changed_live = [("A", changed)]
                contract = self.transform_contract(persisted, changed_live)
                issues = transform_representation_equivalence(persisted, changed_live, contract)["issues"]
                self.assertTrue(any("outside reviewed rotation indices" in issue for issue in issues))

    def test_transform_representation_rejects_delta_above_reviewed_maximum(self):
        persisted, _ = self.equivalent_transform_rows()
        changed = list(persisted[0][1])
        changed[0] += 1e-10
        live = [("A", changed)]
        contract = self.transform_contract(persisted, live)
        issues = transform_representation_equivalence(persisted, live, contract)["issues"]
        self.assertTrue(any("reviewed maximum" in issue for issue in issues))

    def test_transform_representation_rejects_common_hash(self):
        persisted, live = self.equivalent_transform_rows()
        contract = self.transform_contract(persisted, live)
        contract["source_master_common_12sig_transform_sha256"] = "2" * 64
        issues = transform_representation_equivalence(persisted, live, contract)["issues"]
        self.assertTrue(any("significant-digit hash" in issue for issue in issues))

    def test_residual_statistics_use_component_rmse(self):
        result = residual_statistics([
            {"x": 3.0, "y": 4.0, "z": 0.0},
            {"x": -3.0, "y": 0.0, "z": 4.0},
        ])
        self.assertEqual(result["bias_m"], {"x": 0.0, "y": 2.0, "z": 2.0})
        self.assertAlmostEqual(result["rmse_m"]["x"], 3.0)
        self.assertAlmostEqual(result["rmse_m"]["xy"], math.sqrt(17.0))
        self.assertAlmostEqual(result["rmse_m"]["3d"], 5.0)

    def test_reprojection_statistics_report_rms_pixels(self):
        result = reprojection_statistics([3.0, 4.0])
        self.assertEqual(result["count"], 2)
        self.assertAlmostEqual(result["mean_px"], 3.5)
        self.assertAlmostEqual(result["rms_px"], math.sqrt(12.5))

    def test_calibration_comparison_rejects_fixed_parameter_change(self):
        parameters = {name: 0.0 for name in CALIBRATION_PARAMETERS}
        before = [{"sensor_key": "1", "sensor": "P1", "parameters": dict(parameters)}]
        changed = dict(parameters)
        changed["b1"] = 1e-6
        after = [{"sensor_key": "1", "sensor": "P1", "parameters": changed}]
        result = compare_calibrations(
            before,
            after,
            ["f", "cx", "cy", "k1", "k2", "k3", "p1", "p2"],
            ["b1", "b2", "k4"],
            ["p3", "p4"],
            {"b1": 1e-12, "b2": 1e-12, "k4": 1e-12, "p3": 1e-12, "p4": 1e-12},
            1e-12,
        )
        self.assertTrue(any("b1" in issue for issue in result["issues"]))

    def test_calibration_comparison_uses_stable_sensor_keys(self):
        parameters = {name: 0.0 for name in CALIBRATION_PARAMETERS}
        snapshots = [
            {"sensor_key": "10", "sensor": "P1", "parameters": dict(parameters)},
            {"sensor_key": "11", "sensor": "P1", "parameters": dict(parameters)},
        ]
        result = compare_calibrations(
            snapshots,
            snapshots,
            ["f", "cx", "cy", "k1", "k2", "k3", "p1", "p2"],
            ["b1", "b2", "k4"],
            ["p3", "p4"],
            {"b1": 1e-12, "b2": 1e-12, "k4": 1e-12, "p3": 1e-12, "p4": 1e-12},
            1e-12,
        )
        self.assertEqual(result["issues"], [])
        self.assertEqual(len(result["rows"]), 2 * len(CALIBRATION_PARAMETERS))

        duplicated = [dict(snapshots[0]), dict(snapshots[0])]
        result = compare_calibrations(
            duplicated,
            duplicated,
            ["f", "cx", "cy", "k1", "k2", "k3", "p1", "p2"],
            ["b1", "b2", "k4"],
            ["p3", "p4"],
            {"b1": 1e-12, "b2": 1e-12, "k4": 1e-12, "p3": 1e-12, "p4": 1e-12},
            1e-12,
        )
        self.assertTrue(any("duplicated" in issue for issue in result["issues"]))


if __name__ == "__main__":
    unittest.main()
