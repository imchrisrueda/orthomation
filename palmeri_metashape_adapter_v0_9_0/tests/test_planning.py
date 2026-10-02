"""Adversarial draft preparation checks using synthetic evidence only."""

import contextlib
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / "scripts"))
from planning_core import PlanningError, default_contract, load_planning, validate_planning
from validate_planning import main


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.contract = load_planning(PACKAGE / "planning" / "_template_flight_contract.json")
        self.protocol = load_planning(PACKAGE / "planning" / "evaluation_protocol.json")

    def no_permission(self, report):
        self.assertFalse(report["execution_authorized"])
        self.assertFalse(report["products_authorized"])
        self.assertEqual(report["geomatic_acceptance"], "NOT_GRANTED")

    def test_defaults_are_structurally_valid_incomplete_drafts(self):
        for draft in (self.contract, self.protocol):
            report = validate_planning(draft)
            self.assertEqual(report["structural_status"], "PASS")
            self.assertTrue(report["structure_valid"])
            self.assertFalse(report["evidence_complete"])
            self.assertTrue(report["missing_evidence"])
            self.no_permission(report)

    def test_concrete_fully_declared_contract_never_authorizes_or_authenticates(self):
        self.contract["identity"] = {"campaign_id": "SYNTHETIC", "run_id": "SYNTHETIC", "version": "1", "flight_date": "2026-10-02", "metashape_version": "2.3.1"}
        for record in self.contract["evidence"].values():
            record.update(sha256="a" * 64, documentary_source="synthetic nonexistent file")
        for record in self.contract["phases"].values():
            record["documentary_source"] = "synthetic human record pending verification"
        self.contract["expected_counts"] = {"cameras": 8, "transform_components": 128}
        self.contract["reference_metadata"].update(datum="synthetic datum", ellipsoidal_height_reference="synthetic ellipsoid", coordinate_epoch="2026.75")
        report = validate_planning(self.contract)
        self.assertTrue(report["evidence_complete"])
        self.assertFalse(report["evidence_verified"])
        self.assertEqual(report["review_status"], "REVIEW_REQUIRED")
        self.assertEqual(report["operational_status"], "NOT_EXECUTABLE")
        self.no_permission(report)

    def test_missing_and_extra_keys_at_every_contract_object_fail(self):
        paths = [(), ("identity",), ("reference_metadata",), ("boundaries",), ("proposed_reference",), ("proposed_reference", "roles"),
                 ("optimization_contract",), ("evidence",), ("evidence", "jobxml"), ("expected_counts",),
                 ("phases",), ("phases", "optimization")]
        for path in paths:
            for action in ("delete", "inject"):
                draft = copy.deepcopy(self.contract)
                node = draft
                for key in path:
                    node = node[key]
                if action == "delete":
                    del node[next(iter(node))]
                else:
                    node["execution_authorized_injected"] = True
                with self.subTest(path=path, action=action), self.assertRaises(PlanningError):
                    validate_planning(draft)

    def test_approval_injection_and_truthy_types_fail(self):
        for key in ("execution_authorized", "products_authorized", "geomatic_acceptance"):
            for value in (True, 1, "APPROVED"):
                draft = copy.deepcopy(self.contract)
                draft["boundaries"][key] = value
                with self.subTest(key=key, value=value), self.assertRaises(PlanningError):
                    validate_planning(draft)
        for target in ("review", "phase", "reference"):
            draft = copy.deepcopy(self.contract)
            if target == "review":
                draft["review_status"] = "APPROVED"
            elif target == "phase":
                draft["phases"]["optimization"]["status"] = "APPROVED"
            else:
                draft["proposed_reference"]["acceptance"] = "APPROVED"
            with self.assertRaises(PlanningError):
                validate_planning(draft)

    def test_counts_require_positive_bounded_int_not_bool(self):
        for value in (True, False, "43", 43.0, 0, -1, 10**13, [], {}):
            draft = copy.deepcopy(self.contract)
            draft["expected_counts"]["cameras"] = value
            with self.subTest(value=value), self.assertRaises(PlanningError):
                validate_planning(draft)

    def test_dates_and_identity_types(self):
        for value in (True, 20261002, "2026-02-29", "2026-1-01", "2026-13-01", " ", "secret\npath"):
            draft = copy.deepcopy(self.contract)
            draft["identity"]["flight_date"] = value
            with self.subTest(value=value), self.assertRaises(PlanningError):
                validate_planning(draft)
        self.contract["identity"]["flight_date"] = "2024-02-29"
        self.assertTrue(validate_planning(self.contract)["structure_valid"])

    def test_hash_and_documentary_source_types(self):
        for key, values in {"sha256": [True, 64, "a" * 63, "g" * 64, "secret/path"],
                            "documentary_source": [True, {}, "", "path\nsecret"]}.items():
            for value in values:
                draft = copy.deepcopy(self.contract)
                draft["evidence"]["jobxml"][key] = value
                with self.subTest(key=key, value=value), self.assertRaises(PlanningError):
                    validate_planning(draft)

    def test_policy_crs_roles_height_and_optimization_remain_fixed(self):
        for path, value in [(('proposed_reference', 'camera_crs'), 'EPSG::25830'),
                            (('proposed_reference', 'marker_height'), 'H_orthometric'),
                            (('proposed_reference', 'roles', 'C2'), 'GCP'),
                            (('optimization_contract', 'fit_b1'), True),
                            (('optimization_contract', 'fit_f'), 1)]:
            draft = copy.deepcopy(self.contract)
            node = draft
            for key in path[:-1]:
                node = node[key]
            node[path[-1]] = value
            with self.subTest(path=path), self.assertRaises(PlanningError):
                validate_planning(draft)

    def test_protocol_separation_uncertainty_conventions_cannot_be_weakened(self):
        mutations = [(('product_stage', 'gate'), 'BEFORE_PRODUCTS'),
                     (('uncertainty', 'confidence_intervals_from_two_cp'), True),
                     (('uncertainty', 'spatial_extrapolation'), True),
                     (('geometry_stage', 'cp_reporting', 'bias_axes'), ['x', 'y', 'z', 'xy']),
                     (('conventions', 'residual_sign'), 'reference-estimated'),
                     (('conventions', 'branch_delta'), 'GCP_ONLY-GCP_P1'),
                     (('conventions', 'adjustment_height'), 'H_orthometric')]
        for path, value in mutations:
            draft = copy.deepcopy(self.protocol)
            node = draft
            for key in path[:-1]:
                node = node[key]
            node[path[-1]] = value
            with self.subTest(path=path), self.assertRaises(PlanningError):
                validate_planning(draft)

    def test_strict_json_duplicate_nonfinite_float_and_extreme_int(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "synthetic.json"
            for text in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}', '{"a":1e999}',
                         '{"a":1.0}', '{"a":' + '9' * 5000 + '}', '[]', '{broken'):
                path.write_text(text, encoding="utf-8")
                with self.subTest(text=text[:30]), self.assertRaises(PlanningError):
                    validate_planning(load_planning(path))

    def test_referenced_evidence_is_not_read_and_report_is_redacted(self):
        self.contract["identity"]["campaign_id"] = "PRIVATE_CAMPAIGN"
        self.contract["evidence"]["jobxml"] = {"sha256": "b" * 64, "documentary_source": "PRIVATE_PATH"}
        with patch.object(Path, "read_text", side_effect=AssertionError("must not read evidence")):
            report = validate_planning(self.contract)
        serialized = json.dumps(report)
        for secret in ("PRIVATE_CAMPAIGN", "PRIVATE_PATH", "b" * 64):
            self.assertNotIn(secret, serialized)

    def test_cli_defaults_exit_codes_redaction_and_no_writes(self):
        with patch.object(Path, "write_text", side_effect=AssertionError("no writes")), patch.object(Path, "write_bytes", side_effect=AssertionError("no writes")):
            for args, expected in [([], 0), ([str(PACKAGE / 'planning' / '_template_flight_contract.json')], 0),
                                   (["PRIVATE_NONEXISTENT_PATH"], 1), (["--unknown"], 2), (["secret", "extra"], 2)]:
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(main(args), expected)
                report = json.loads(output.getvalue())
                self.no_permission(report)
                self.assertNotIn("PRIVATE_NONEXISTENT_PATH", output.getvalue())
                self.assertNotIn("secret", output.getvalue())

    def test_defaults_do_not_inherit_pilot_counts_or_equivalence(self):
        draft = default_contract()
        self.assertEqual(draft["expected_counts"], {"cameras": None, "transform_components": None})
        self.assertNotIn("transform_equivalence", json.dumps(draft))
        for evidence in draft["evidence"].values():
            self.assertIsNone(evidence["sha256"])

    def test_blocked_rejected_drafts_remain_no_permission(self):
        self.contract["review_status"] = "REJECTED"
        self.contract["phases"]["optimization"]["status"] = "BLOCKED"
        report = validate_planning(self.contract)
        self.no_permission(report)
        self.assertEqual(report["source_review_status"], "REJECTED")

    def test_reference_metadata_is_explicit_sourced_text_not_numeric_epoch(self):
        for value in (True, 2026, 2026.75, "NaN", "2026-10-02", "Infinity"):
            draft = copy.deepcopy(self.contract)
            draft["reference_metadata"]["coordinate_epoch"] = value
            with self.subTest(value=value), self.assertRaises(PlanningError):
                validate_planning(draft)
        self.contract["reference_metadata"]["coordinate_epoch"] = "2026.75"
        with self.assertRaises(PlanningError):
            validate_planning(self.contract)
        self.contract["evidence"]["coordinate_epoch"]["documentary_source"] = "synthetic source"
        self.assertTrue(validate_planning(self.contract)["structure_valid"])

    def test_exact_software_version_is_declarative_not_approval(self):
        for value in (True, 2, "2.3", "2.3.x", "latest"):
            draft = copy.deepcopy(self.contract)
            draft["identity"]["metashape_version"] = value
            with self.subTest(value=value), self.assertRaises(PlanningError):
                validate_planning(draft)
        self.contract["identity"]["metashape_version"] = "2.3.1"
        self.no_permission(validate_planning(self.contract))

    def test_fresh_cli_subprocess_creates_no_bytecode_or_other_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ("validate_planning.py", "planning_core.py", "optimization_core.py"):
                (root / name).write_bytes((PACKAGE / "scripts" / name).read_bytes())
            draft = root / "synthetic.json"
            draft.write_text(json.dumps(self.contract), encoding="utf-8")
            before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            env = dict(os.environ)
            env.pop("PYTHONDONTWRITEBYTECODE", None)
            run = subprocess.run([sys.executable, str(root / "validate_planning.py"), str(draft)],
                                 cwd=root, env=env, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertTrue(json.loads(run.stdout)["structure_valid"])
            self.no_permission(json.loads(run.stdout))
            after = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            self.assertEqual(before, after)
            self.assertFalse((root / "__pycache__").exists())


if __name__ == "__main__":
    unittest.main()
