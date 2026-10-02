"""Adversarial offline controls with synthetic inputs only."""

import ast
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT.parent / "tools"))

from check_repository import frontmatter, markdown_links
from compare_branch_metrics import main as compare_cli
from comparison_core import ComparisonError, compare_reports
from comparison_html import render_comparison, write_comparison_html
from configuration_core import ConfigurationError, load_configuration, valid_path, validate_campaign, validate_configuration, validate_global
from optimization_core import EXECUTION_PHASES, require_approved_experiment
from package_integrity import IntegrityError, manifest_entries, source_files, verify_package, write_manifest
from test_compare_branch_metrics import report
from validate_configuration import main as configuration_cli


class PhaseTests(unittest.TestCase):
    def setUp(self):
        self.config = load_configuration(ROOT / "config" / "global.json")

    def test_global_approval_never_implies_phase_approval(self):
        self.assertEqual(require_approved_experiment(self.config, "fixed_model_v1", "prepare_branches")["flight_date"], "2025-04-29")
        for phase in (None, "unknown", "preflight", "optimization", "metrics_export"):
            with self.subTest(phase=phase), self.assertRaises(RuntimeError):
                require_approved_experiment(self.config, "fixed_model_v1", phase)
        del self.config["optimization_experiments"]["fixed_model_v1"]["phase_authorizations"]
        with self.assertRaises(RuntimeError):
            require_approved_experiment(self.config, "fixed_model_v1", "prepare_branches")

    def test_malformed_authorization_and_absent_source_fail_closed(self):
        for value in ({}, [], {"status": [], "evidence": "source"}, {"status": "APPROVED", "evidence": " "}, {"status": "APPROVED", "evidence": ["source"]}, {"status": "UNKNOWN", "evidence": ""}):
            config = copy.deepcopy(self.config)
            config["optimization_experiments"]["fixed_model_v1"]["phase_authorizations"]["prepare_branches"] = value
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                require_approved_experiment(config, "fixed_model_v1", "prepare_branches")
        with self.assertRaises(RuntimeError):
            require_approved_experiment(self.config, "other", "prepare_branches")

    def test_each_processing_entry_checks_its_phase_before_accessing_document(self):
        callers = {"prepare_branches.py": "prepare_branches", "validate_before_optimize.py": "preflight", "optimize_branch.py": "optimization", "export_postoptimization_metrics.py": "metrics_export"}
        for filename, phase in callers.items():
            tree = ast.parse((ROOT / "scripts" / filename).read_text(encoding="utf-8"))
            main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
            calls = [node for node in ast.walk(main) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "require_approved_experiment"]
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0].args[2].value, phase)
            documents = [node for node in ast.walk(main) if isinstance(node, ast.Attribute) and node.attr == "document"]
            self.assertLess(calls[0].lineno, min(node.lineno for node in documents))
            if phase == "prepare_branches":
                verify = next(node for node in ast.walk(main) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "verify_package")
                self.assertLess(verify.lineno, calls[0].lineno)


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.config = load_configuration(ROOT / "config" / "global.json")
        self.campaign = load_configuration(ROOT / "campaigns" / "2025.json")

    def test_current_structure_and_blocked_operation_are_separate(self):
        value = validate_configuration(ROOT)
        self.assertEqual(value["structural_status"], "PASS")
        self.assertEqual(value["geomatic_acceptance"], "NOT_GRANTED")
        reports = {row["configuration"]: row for row in value["campaigns"]}
        self.assertEqual(reports["2026.json"]["operational_status"], "REVIEW_REQUIRED")
        self.assertEqual(reports["_template_campaign.json"]["operational_status"], "NOT_EXECUTABLE")
        self.assertNotIn("expected_sha256", self.campaign["jobxml_rules"])
        self.assertEqual(reports["2025.json"]["structural_status"], "PASS")

    def test_campaign_dates_roles_crs_paths_and_types_are_rejected(self):
        variants = []
        for key, value in (("pilot_date", "2025-02-30"), ("camera_reference_crs", "EPSG::25830"), ("alignment_preset", {}), ("status", []), ("default_jobxml", "../secret.xml")):
            c = copy.deepcopy(self.campaign); c[key] = value; variants.append(c)
        c = copy.deepcopy(self.campaign); c["control_points"]["2"]["role"] = "GCP"; variants.append(c)
        c = copy.deepcopy(self.campaign); c["control_points"]["2"]["label"] = {}; variants.append(c)
        c = copy.deepcopy(self.campaign); c["flights"].append(c["flights"][0]); variants.append(c)
        c = copy.deepcopy(self.campaign); c["jobxml_semantic_acceptance"] = {}; variants.append(c)
        for value in variants:
            with self.subTest(value=value), self.assertRaises(ConfigurationError):
                validate_campaign(value, "2025.json", self.config)
        with self.assertRaises(ConfigurationError):
            validate_campaign(self.campaign, "other.json", self.config)

    def test_invariants_and_output_policy_fail_closed(self):
        for block, key, value in (("processing", "overwrite_policy", "replace"), ("camera_reference", "load_xmp_antenna", True), ("validation", "require_camera_rotation_off", False), ("optimization", "adaptive_fitting", True)):
            config = copy.deepcopy(self.config); config[block][key] = value
            with self.subTest(key=key), self.assertRaises(ConfigurationError):
                validate_global(config)
        self.config["generated_root"] = "relative/output"
        with self.assertRaises(ConfigurationError):
            validate_global(self.config)

    def test_paths_are_platform_independent_without_data_access(self):
        for value in (r"F:\survey\photos", r"D:\survey\photos", "/srv/survey/photos", "control/jobxml/source.jxl", r"\\server\share\photos"):
            self.assertTrue(valid_path(value), value)
        for value in (r"D:relative", "../photos", r"C:\bad?\photos", "http://example.org/photos", "bad\x00name"):
            self.assertFalse(valid_path(value), value)

    def test_contract_json_types_cannot_use_numeric_boolean_equivalence_or_coercion(self):
        for key, value in (("fit_f", 1), ("fit_corrections", 0)):
            config = copy.deepcopy(self.config)
            config["optimization"][key] = value
            with self.subTest(key=key), self.assertRaises(ConfigurationError):
                validate_global(config)
        for key in ("expected_camera_count", "expected_transform_component_count", "transform_equivalence_significant_digits", "required_marker_projections"):
            for convert in (float, bool):
                config = copy.deepcopy(self.config)
                experiment = config["optimization_experiments"]["fixed_model_v1"]
                experiment[key] = convert(experiment[key])
                with self.subTest(key=key, convert=convert), self.assertRaises(ConfigurationError):
                    validate_global(config)
        for index in (0.0, False):
            config = copy.deepcopy(self.config)
            config["optimization_experiments"]["fixed_model_v1"]["transform_equivalence_allowed_difference_indices"][0] = index
            with self.subTest(index=index), self.assertRaises(ConfigurationError):
                validate_global(config)
        for value in ("1e-12", True, float("inf"), float("nan")):
            for key in ("fixed_parameter_absolute_tolerance", "source_master_equivalence_max_abs_delta", "calibration_change_detection_absolute_tolerance"):
                config = copy.deepcopy(self.config)
                experiment = config["optimization_experiments"]["fixed_model_v1"]
                if key == "fixed_parameter_absolute_tolerance":
                    experiment[key]["b1"] = value
                else:
                    experiment[key] = value
                with self.subTest(key=key, value=value), self.assertRaises(ConfigurationError):
                    validate_global(config)

    def test_json_duplicates_nonfinite_and_cli_redaction(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "global.json"
            for value in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":1e400}'):
                path.write_text(value, encoding="utf-8")
                with self.assertRaises(ConfigurationError):
                    load_configuration(path)
            package = Path(directory) / "package"
            (package / "config").mkdir(parents=True)
            (package / "config" / "global.json").write_text('{"a":1,"a":2}', encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(configuration_cli(["--package", str(package)]), 1)
            self.assertEqual(json.loads(stdout.getvalue())["error"], "duplicate_json_key")
            self.assertNotIn(directory, stdout.getvalue())

    def test_unrepresentable_integer_is_invalid_configuration_without_crashing_cli(self):
        config = copy.deepcopy(self.config)
        config["validation"]["coordinate_tolerance_m"] = 10 ** 400
        with self.assertRaises(ConfigurationError):
            validate_global(config)
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory)
            (package / "config").mkdir()
            (package / "config" / "global.json").write_text(json.dumps(config), encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(configuration_cli(["--package", str(package)]), 1)
            self.assertEqual(json.loads(stdout.getvalue())["error"], "validation_bounds_invalid")
            self.assertNotIn(directory, stdout.getvalue())


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.package = Path(self.temporary.name)
        (self.package / "script.py").write_bytes(b"print('synthetic')\n")
        (self.package / "config.json").write_bytes(b"{}\n")
        write_manifest(self.package)

    def test_exact_bytes_and_set_changes_fail(self):
        source = self.package / "script.py"
        source.write_bytes(source.read_bytes().replace(b"\n", b"\r\n"))
        with self.assertRaisesRegex(IntegrityError, "hash_mismatch") as raised:
            verify_package(self.package)
        self.assertEqual(raised.exception.members, ["script.py"])
        write_manifest(self.package)
        self.assertTrue(verify_package(self.package)["byte_exact"])
        source.unlink()
        with self.assertRaisesRegex(IntegrityError, "source_set_mismatch"):
            verify_package(self.package)
        write_manifest(self.package)
        (self.package / "extra.py").write_bytes(b"pass\n")
        with self.assertRaisesRegex(IntegrityError, "source_set_mismatch"):
            verify_package(self.package)

    def test_manifest_duplicate_traversal_absolute_drive_backslash_and_malformed(self):
        manifest = self.package / "SHA256SUMS.txt"
        original = manifest.read_bytes()
        manifest.write_bytes(original + original.splitlines(keepends=True)[0])
        with self.assertRaisesRegex(IntegrityError, "duplicate"):
            manifest_entries(self.package)
        for name in ("../outside.py", "/outside.py", "D:/outside.py", r"scripts\source.py", "./source.py"):
            manifest.write_text("0" * 64 + "  " + name + "\n", encoding="ascii")
            with self.subTest(name=name), self.assertRaisesRegex(IntegrityError, "path_invalid"):
                manifest_entries(self.package)
        manifest.write_text("bad line\n", encoding="ascii")
        with self.assertRaisesRegex(IntegrityError, "line_invalid") as raised:
            manifest_entries(self.package)
        self.assertEqual(raised.exception.line, 1)

    def test_data_generated_and_temporary_sources_are_never_members(self):
        for directory in ("control", "generated", "tmp", "project.files"):
            (self.package / directory).mkdir()
            (self.package / directory / "data.json").write_bytes(b"not source")
        for name in ("flight.jxl", "project.psx", ".test_temp.json"):
            (self.package / name).write_bytes(b"not source")
        self.assertEqual(set(source_files(self.package)), {"script.py", "config.json"})
        verify_package(self.package)

    def test_symlink_source_and_manifest_are_rejected(self):
        link = self.package / "linked.py"
        try:
            link.symlink_to(self.package / "script.py")
        except OSError as exc:
            self.skipTest(f"Symlinks unavailable without privileges: {exc.__class__.__name__}")
        with self.assertRaisesRegex(IntegrityError, "symlink"):
            verify_package(self.package)
        link.unlink()
        (self.package / "SHA256SUMS.txt").unlink()
        (self.package / "SHA256SUMS.txt").symlink_to(self.package / "script.py")
        with self.assertRaisesRegex(IntegrityError, "symlink"):
            write_manifest(self.package)


class HtmlTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.inputs = [self.directory / "left.json", self.directory / "right.json"]
        for path, branch, offset in zip(self.inputs, ("GCP_ONLY", "GCP_P1"), (0.0, 0.25)):
            path.write_text(json.dumps(report(branch, offset)), encoding="utf-8")

    def test_html_and_stdout_use_same_validated_comparison_and_label_demo(self):
        output = self.directory / "comparison.html"
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(compare_cli([*map(str, self.inputs), "--html", str(output), "--demo"]), 0)
        result = json.loads(stdout.getvalue())
        html = output.read_text(encoding="utf-8")
        self.assertEqual(result["status"], "OBJECTIVE_COMPARISON_READY")
        self.assertIn("DEMO SINTÉTICA", html)
        self.assertIn(result["provenance"]["input_report_sha256_by_branch"]["GCP_ONLY"], html)
        self.assertIn("NOT_GRANTED", html)
        self.assertIn("GCP_P1", html)
        self.assertNotIn("<script", html.lower())

    def test_all_text_is_escaped_and_decision_flags_enforced(self):
        result = compare_reports(report("GCP_ONLY", 0.0), report("GCP_P1", 0.25), ["a" * 64, "b" * 64])
        result["provenance"]["run_id"] = '<script>alert("x")</script>'
        self.assertIn("&lt;script&gt;", render_comparison(result))
        self.assertNotIn("<script>", render_comparison(result))
        result["selection_performed"] = True
        with self.assertRaises(ComparisonError):
            render_comparison(result)

    def test_error_does_not_create_html_and_existing_output_not_overwritten(self):
        output = self.directory / "comparison.html"
        self.inputs[0].write_text('{"a":NaN}', encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(compare_cli([*map(str, self.inputs), "--html", str(output)]), 1)
        self.assertFalse(output.exists())
        self.inputs[0].write_text(json.dumps(report("GCP_ONLY", 0.0)), encoding="utf-8")
        output.write_text("preserved", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(compare_cli([*map(str, self.inputs), "--html", str(output)]), 1)
        self.assertEqual(output.read_text(), "preserved")
        result = compare_reports(report("GCP_ONLY", 0.0), report("GCP_P1", 0.25), ["a" * 64, "b" * 64])
        with self.assertRaises(ComparisonError):
            write_comparison_html(result, ROOT / "malicious.html", self.inputs)


class RepositoryTests(unittest.TestCase):
    def test_local_links_and_anchor_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            doc = root / "README.md"
            doc.write_text('# A título\n\n[link](#a-título)\n', encoding="utf-8")
            self.assertEqual(markdown_links(doc, root), 1)
            doc.write_text('[bad](#missing)\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                markdown_links(doc, root)

    def test_project_scalar_skill_subset_detects_missing_duplicate_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            skill = Path(directory) / "example"; skill.mkdir()
            doc = skill / "SKILL.md"
            for content in ("# no metadata", "---\nname: example\nname: example\n---\n", "---\nname: other\ndescription: text\n---\n"):
                doc.write_text(content, encoding="utf-8")
                with self.assertRaises(ValueError):
                    frontmatter(doc)


if __name__ == "__main__":
    unittest.main()
