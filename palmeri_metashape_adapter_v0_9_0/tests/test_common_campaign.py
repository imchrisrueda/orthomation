"""Motor-neutral campaign draft validation, with synthetic inputs and adversarial gates."""

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
from common_campaign_core import default_common_campaign, default_contract_reference, default_flight
from planning_core import PlanningError, load_planning, validate_planning
from validate_planning import main


class CommonCampaignTests(unittest.TestCase):
    def setUp(self):
        self.draft = load_planning(PACKAGE / "planning" / "_template_common_campaign.json")

    def assert_no_acceptance(self, report):
        self.assertFalse(report["execution_authorized"])
        self.assertFalse(report["products_authorized"])
        self.assertFalse(report["evidence_verified"])
        self.assertFalse(report["compatibility_verified"])
        self.assertEqual(report["geomatic_acceptance"], "NOT_GRANTED")
        self.assertEqual(report["operational_status"], "NOT_EXECUTABLE")
        self.assertEqual(report["common_schema_adapter_status"], "NOT_IMPLEMENTED")

    def concrete_flights(self):
        self.draft["flights"] = [default_flight(), default_flight()]
        self.draft["flight_contract_references"] = []
        for index, flight in enumerate(self.draft["flights"]):
            flight.update(flight_id="SYNTHETIC_" + str(index), flight_date="2026-10-0" + str(index + 1))
            for engine in ("metashape", "pix4dmapper"):
                ref = default_contract_reference(engine)
                ref.update(flight_id=flight["flight_id"], flight_date=flight["flight_date"])
                self.draft["flight_contract_references"].append(ref)

    def test_default_is_valid_incomplete_and_not_executable(self):
        report = validate_planning(self.draft)
        self.assertTrue(report["structure_valid"])
        self.assertFalse(report["evidence_complete"])
        self.assertIn("flights[0].contract_reference.pix4dmapper", report["missing_evidence"])
        self.assert_no_acceptance(report)

    def test_multiple_flights_coherent_refs_and_missing_refs_are_declarative(self):
        self.concrete_flights()
        report = validate_planning(self.draft)
        self.assertTrue(report["structure_valid"])
        self.draft["flight_contract_references"] = []
        missing = validate_planning(self.draft)["missing_evidence"]
        self.assertIn("flights[0].contract_reference.metashape", missing)
        self.assertIn("flights[1].contract_reference.pix4dmapper", missing)

    def test_duplicate_flights_and_contracts_inexistent_and_mismatched_dates_fail(self):
        self.concrete_flights()
        for mutation in ("duplicate_flight", "duplicate_reference", "inexistent", "date_mismatch"):
            draft = copy.deepcopy(self.draft)
            if mutation == "duplicate_flight":
                draft["flights"][1]["flight_id"] = draft["flights"][0]["flight_id"]
            elif mutation == "duplicate_reference":
                draft["flight_contract_references"].append(copy.deepcopy(draft["flight_contract_references"][0]))
            elif mutation == "inexistent":
                draft["flight_contract_references"][0]["flight_id"] = "INEXISTENT_SECRET"
            else:
                draft["flight_contract_references"][0]["flight_date"] = "2026-11-01"
            with self.subTest(mutation=mutation), self.assertRaises(PlanningError):
                validate_planning(draft)

    def test_pending_null_id_and_date_remain_incomplete(self):
        self.draft["flights"].append(default_flight())
        report = validate_planning(self.draft)
        self.assertTrue(report["structure_valid"])
        self.assertIn("flights[1].flight_id", report["missing_evidence"])

    def test_fully_declared_records_still_no_authentication_compatibility_or_permission(self):
        self.concrete_flights()
        def fill(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    if child is None:
                        value[key] = ("c" * 64 if key == "sha256" else 12 if key == "accepted_image_count"
                                      else "2.3.1" if key == "version" else "synthetic declaration")
                    else:
                        fill(child)
            elif isinstance(value, list):
                for child in value:
                    fill(child)
        fill(self.draft)
        for flight in self.draft["flights"]:
            for target in ("camera", "control"):
                flight["reference_metadata"][target]["coordinate_epoch"]["value"] = "2026.75"
        self.draft["review_status"] = "REJECTED"
        report = validate_planning(self.draft)
        self.assertTrue(report["evidence_complete"])
        self.assertEqual(report["source_review_status"], "REJECTED")
        self.assert_no_acceptance(report)

    def test_missing_extra_keys_at_each_object_are_rejected(self):
        def objects(value, path=()):
            if type(value) is dict:
                yield path
                for key, child in value.items():
                    yield from objects(child, path + (key,))
            elif type(value) is list:
                for index, child in enumerate(value):
                    yield from objects(child, path + (index,))
        for path in objects(self.draft):
            for mutation in ("missing", "extra"):
                draft = copy.deepcopy(self.draft)
                node = draft
                for part in path:
                    node = node[part]
                if mutation == "missing":
                    del node[next(iter(node))]
                else:
                    node["injected_authorization"] = True
                with self.subTest(path=path, mutation=mutation), self.assertRaises(PlanningError):
                    validate_planning(draft)

    def test_geomatic_and_engine_policies_cannot_change(self):
        mutations = [(('reference_policy', 'camera_crs'), 'EPSG::25830'),
                     (('reference_policy', 'control_height'), 'H_orthometric'),
                     (('reference_policy', 'control_horizontal_units'), 'degree'),
                     (('control_policy', 'roles', 'C2'), 'GCP'),
                     (('control_policy', 'precision_interpretation'), 'PIX4D_EQUIVALENT'),
                     (('camera_source_policy', 'additional_lever_arm'), True),
                     (('comparison_requirements', 'cross_engine_equivalence'), 'VERIFIED'),
                     (('comparison_requirements', 'metashape_only', 'cp_enabled'), True),
                     (('comparison_requirements', 'metashape_only', 'camera_xyz_enabled', 'GCP_ONLY'), True),
                     (('engine_bindings', 'pix4dmapper', 'mapping_status'), 'VERIFIED'),
                     (('engine_bindings', 'metashape', 'common_schema_adapter_status'), 'IMPLEMENTED'),
                     (('boundaries', 'execution_authorized'), 1),
                     (('sensor_policy', 'width_px'), True), (('review_status',), 'APPROVED')]
        for path, value in mutations:
            draft = copy.deepcopy(self.draft)
            node = draft
            for part in path[:-1]:
                node = node[part]
            node[path[-1]] = value
            with self.subTest(path=path), self.assertRaises(PlanningError):
                validate_planning(draft)

    def test_pix4d_cannot_reuse_metashape_contract(self):
        ref = self.draft["flight_contract_references"][1]
        ref["contract_type"] = "flight_contract"
        ref["contract_schema"] = "planning-1"
        with self.assertRaises(PlanningError):
            validate_planning(self.draft)

    def test_counts_dates_hashes_epochs_and_versions_have_strict_types(self):
        for value in (True, 1.0, "12", 0, -1, 10**13):
            draft = copy.deepcopy(self.draft)
            draft["flights"][0]["accepted_image_count"] = value
            with self.subTest(value=value), self.assertRaises(PlanningError):
                validate_planning(draft)
        for group, key, value in [("flight", "flight_date", "2026-02-29"), ("engine", "version", "latest"),
                                  ("hash", "sha256", "private/path"), ("epoch", "value", 2026.5)]:
            draft = copy.deepcopy(self.draft)
            node = (draft["flights"][0] if group == "flight" else draft["engine_bindings"]["pix4dmapper"] if group == "engine"
                    else draft["flights"][0]["image_evidence"]["accepted_set"] if group == "hash"
                    else draft["flights"][0]["reference_metadata"]["camera"]["coordinate_epoch"])
            node[key] = value
            with self.subTest(group=group), self.assertRaises(PlanningError):
                validate_planning(draft)

    def test_metadata_declared_value_requires_source_without_reading_it(self):
        datum = self.draft["flights"][0]["reference_metadata"]["camera"]["datum"]
        datum["value"] = "PRIVATE_DATUM"
        with self.assertRaises(PlanningError):
            validate_planning(self.draft)
        datum["documentary_source"] = "PRIVATE_NONEXISTENT_PATH"
        with patch.object(Path, "read_text", side_effect=AssertionError("no evidence reads")):
            report = validate_planning(self.draft)
        self.assertNotIn("PRIVATE", json.dumps(report))

    def test_common_json_uses_existing_strict_loader_and_cli_codes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "secret.json"
            for raw in ('{"artifact_type":"common_campaign","x":NaN}', '{"x":1,"x":2}', '{"x":' + '9' * 5000 + '}'):
                path.write_text(raw, encoding="utf-8")
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    self.assertEqual(main([str(path)]), 1)
                self.assertNotIn(str(path), out.getvalue())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main([]), 0)
        self.assertEqual(len(json.loads(out.getvalue())["drafts"]), 3)

    def test_clean_cli_subprocess_with_three_templates_writes_no_files(self):
        with tempfile.TemporaryDirectory() as folder:
            package = Path(folder)
            (package / "scripts").mkdir()
            (package / "planning").mkdir()
            for name in ("validate_planning.py", "planning_core.py", "optimization_core.py", "common_campaign_core.py"):
                (package / "scripts" / name).write_bytes((PACKAGE / "scripts" / name).read_bytes())
            for name in ("_template_flight_contract.json", "evaluation_protocol.json", "_template_common_campaign.json"):
                (package / "planning" / name).write_bytes((PACKAGE / "planning" / name).read_bytes())
            before = {p.relative_to(package): p.read_bytes() for p in package.rglob("*") if p.is_file()}
            env = dict(os.environ)
            env.pop("PYTHONDONTWRITEBYTECODE", None)
            run = subprocess.run([sys.executable, str(package / "scripts" / "validate_planning.py")],
                                 cwd=package, env=env, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(len(json.loads(run.stdout)["drafts"]), 3)
            self.assertEqual(before, {p.relative_to(package): p.read_bytes() for p in package.rglob("*") if p.is_file()})
            self.assertFalse(list(package.rglob("__pycache__")))


if __name__ == "__main__":
    unittest.main()
