import contextlib
from hashlib import sha256
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_jobxml_candidate import STATUS_EXIT_CODES, main, validate_candidate


def jobxml(points, extra_ids=()):
    records = []
    reductions = []
    for point_id, east, north, h_ellipsoid, H_orthometric in points:
        records.append(
            f"""<PointRecord TimeStamp="2026-05-06T10:00:00">
              <Name>{point_id}</Name><Deleted>false</Deleted><SurveyMethod>NetworkFix</SurveyMethod>
              <Precision><Horizontal>0.010</Horizontal><Vertical>0.020</Vertical></Precision>
              <QualityControl1><NumberOfSatellites>19</NumberOfSatellites><PDOP>1.2</PDOP></QualityControl1>
              <Warnings><PoorPrecisionsWarning>No</PoorPrecisionsWarning></Warnings>
            </PointRecord>"""
        )
        reductions.append(
            f"""<Point><Name>{point_id}</Name>
              <WGS84><Latitude>40.123</Latitude><Longitude>-3.456</Longitude><Height>{h_ellipsoid}</Height></WGS84>
              <Grid><North>{north}</North><East>{east}</East><Elevation>{H_orthometric}</Elevation></Grid>
            </Point>"""
        )
    for point_id in extra_ids:
        records.append(
            f"<PointRecord><Name>{point_id}</Name><SurveyMethod>NetworkFix</SurveyMethod>"
            "</PointRecord>"
        )
        reductions.append(f"<Point><Name>{point_id}</Name></Point>")
    return (
        '<JOBFile jobName="synthetic" version="5.72">'
        "<CoordinateSystemRecord><SystemName>UTM</SystemName><ZoneName>30 North</ZoneName>"
        "<DatumName>ETRS89</DatumName></CoordinateSystemRecord>"
        "<VerticalAdjustmentRecord><Type>GeoidModel</Type><GeoidName>EGM08IGN</GeoidName>"
        "</VerticalAdjustmentRecord>"
        + "".join(records)
        + "<Reductions>"
        + "".join(reductions)
        + "</Reductions></JOBFile>"
    )


def campaign(candidate_hash, labels=None):
    labels = labels or {"1": ("E1", "GCP"), "2": ("C2", "CHECK_POINT")}
    return {
        "campaign_id": "synthetic-2026",
        "jobxml_rules": {
            "expected_survey_year": 2026,
            "expected_geoid": "EGM08IGN",
            "expected_coordinate_tokens": ["UTM", "30 North", "ETRS89"],
            "required_survey_method": "NetworkFix",
            "require_no_poor_precision_warning": True,
            "expected_sha256": candidate_hash,
        },
        "control_points": {
            point_id: {"label": label, "role": role}
            for point_id, (label, role) in labels.items()
        },
        "jobxml_semantic_acceptance": {
            "identity_mapping_accepted": False,
            "roles_accepted": False,
            "horizontal_semantics_accepted": False,
            "precision_units_accepted": True,
        },
        "crs_acceptance": {
            "source": "campaign_config",
            "horizontal_epsg": "EPSG::25830",
            "horizontal_epsg_accepted": False,
            "coordinate_units": "metre",
            "coordinate_units_accepted": False,
            "coordinate_epoch": None,
            "coordinate_epoch_accepted": False,
        },
    }


class JobxmlCandidateAuditTests(unittest.TestCase):
    def setUp(self):
        self.directory = ROOT / "tests"
        self.candidate = self.directory / ".test_candidate.jxl"
        self.candidate.write_text(
            jobxml([
                ("1", 100.0, 200.0, 650.0, 598.8),
                ("2", 110.0, 210.0, 651.0, 599.7),
            ]),
            encoding="utf-8",
        )
        self.campaign = self.directory / ".test_campaign.json"
        self.write_campaign(self.campaign, campaign(self.digest(self.candidate)))

    def tearDown(self):
        for name in (
            ".test_candidate.jxl",
            ".test_campaign.json",
            ".test_reference.jxl",
            ".test_reference.json",
        ):
            (self.directory / name).unlink(missing_ok=True)

    @staticmethod
    def digest(path):
        return sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def write_campaign(path, value):
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_2026_campaign_keeps_candidate_blocked_with_full_hash(self):
        configured = json.loads((ROOT / "campaigns" / "2026.json").read_text(encoding="utf-8"))
        self.assertEqual(configured["status"], "BLOCKED_GEOMATIC_REVIEW")
        self.assertEqual(
            configured["jobxml_rules"]["expected_sha256"],
            "3b8a66c5475505b90c7be77dfb9a42537971af963f0e01d55c307fa64aa7cd5d",
        )
        self.assertFalse(configured["jobxml_semantic_acceptance"]["identity_mapping_accepted"])
        self.assertFalse(configured["jobxml_semantic_acceptance"]["roles_accepted"])
        self.assertTrue(configured["jobxml_semantic_acceptance"]["precision_units_accepted"])
        self.assertFalse(configured["crs_acceptance"]["coordinate_units_accepted"])

    def test_report_is_redacted_and_requires_human_review(self):
        report = validate_candidate(self.candidate, self.campaign)
        encoded = json.dumps(report, sort_keys=True)
        self.assertEqual(report["schema_version"], "orthomation.jobxml-candidate-validation/1")
        self.assertEqual(report["status"], "REVIEW_REQUIRED")
        self.assertTrue(report["automatic_checks_passed"])
        self.assertFalse(report["campaign_unlock"])
        self.assertEqual(report["geomatic_acceptance"], "NOT_GRANTED")
        self.assertTrue(all(point["role_source"] == "campaign_config" for point in report["points"]))
        self.assertEqual(report["points"][0]["observation_year"], 2026)
        self.assertEqual(report["points"][0]["satellites"], 19)
        self.assertEqual(report["points"][0]["pdop"], 1.2)
        self.assertFalse(report["points"][0]["deleted"])
        self.assertAlmostEqual(report["height_references"]["spread_m"], 0.1)
        self.assertFalse(report["comparison"]["auto_assignment_performed"])
        for forbidden_key in (
            '"latitude"', '"longitude"', '"easting"', '"northing"',
            '"h_ellipsoid"', '"H_orthometric"', '"path"',
        ):
            self.assertNotIn(forbidden_key, encoded)
        for forbidden_value in ("40.123", "-3.456", "650.0", "598.8", str(self.directory)):
            self.assertNotIn(forbidden_value, encoded)
        self.assertNotIn("<JOBFile", encoded)

    def test_hash_mismatch_is_fail(self):
        value = campaign("0" * 64)
        self.write_campaign(self.campaign, value)
        report = validate_candidate(self.candidate, self.campaign)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("candidate_sha256_mismatch", report["errors"])
        self.assertFalse(report["campaign_unlock"])

    def test_invalid_expected_hash_is_fail(self):
        value = campaign("abc")
        self.write_campaign(self.campaign, value)
        report = validate_candidate(self.candidate, self.campaign)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("expected_candidate_sha256_invalid", report["errors"])

    def test_missing_expected_hash_is_fail(self):
        value = campaign(self.digest(self.candidate))
        del value["jobxml_rules"]["expected_sha256"]
        self.write_campaign(self.campaign, value)
        report = validate_candidate(self.candidate, self.campaign)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("expected_candidate_sha256_missing", report["errors"])
        self.assertFalse(report["automatic_checks_passed"])
        self.assertFalse(report["campaign_unlock"])

    def test_unexpected_ids_are_not_silently_filtered(self):
        self.candidate.write_text(
            jobxml(
                [("1", 100.0, 200.0, 650.0, 598.8), ("2", 110.0, 210.0, 651.0, 599.7)],
                extra_ids=("99",),
            ),
            encoding="utf-8",
        )
        self.write_campaign(self.campaign, campaign(self.digest(self.candidate)))
        report = validate_candidate(self.candidate, self.campaign)
        finding = next(
            item for item in report["findings"]
            if isinstance(item, dict) and item.get("code") == "unexpected_point_ids"
        )
        self.assertEqual(finding["point_record_ids"], ["99"])
        self.assertEqual(finding["reduction_ids"], ["99"])
        self.assertEqual(report["status"], "REVIEW_REQUIRED")

    def test_non_control_base_record_is_informational_and_redacted(self):
        current = self.candidate.read_text(encoding="utf-8")
        base_record = (
            "<PointRecord><Name>PRS689046862025</Name><Method>FromBase</Method>"
            "<SurveyMethod>KeyedIn</SurveyMethod></PointRecord>"
        )
        self.candidate.write_text(
            current.replace(
                "<Reductions>",
                base_record + "<Reductions><Point><Name>PRS689046862025</Name></Point>",
                1,
            ),
            encoding="utf-8",
        )
        self.write_campaign(self.campaign, campaign(self.digest(self.candidate)))
        report = validate_candidate(self.candidate, self.campaign)
        encoded = json.dumps(report, sort_keys=True)
        finding = next(
            item for item in report["findings"]
            if isinstance(item, dict) and item.get("code") == "non_control_records"
        )
        self.assertEqual(finding["count"], 1)
        self.assertEqual(finding["survey_methods"], ["KeyedIn"])
        self.assertEqual(finding["methods"], ["FromBase"])
        self.assertTrue(finding["identifiers_redacted"])
        self.assertNotIn("PRS689046862025", encoded)
        self.assertNotIn("unexpected_point_ids_require_geomatic_review", report["blockers"])

    def test_unknown_extra_record_is_review_blocker(self):
        current = self.candidate.read_text(encoding="utf-8")
        unknown_record = "<PointRecord><Name>UNKNOWN_EXTRA</Name></PointRecord>"
        self.candidate.write_text(
            current.replace("<Reductions>", unknown_record + "<Reductions>", 1),
            encoding="utf-8",
        )
        self.write_campaign(self.campaign, campaign(self.digest(self.candidate)))
        report = validate_candidate(self.candidate, self.campaign)
        finding = next(
            item for item in report["findings"]
            if isinstance(item, dict) and item.get("code") == "unexpected_point_ids"
        )
        self.assertEqual(finding["point_record_ids"], ["UNKNOWN_EXTRA"])
        self.assertIn("unexpected_point_ids_require_geomatic_review", report["blockers"])
        self.assertFalse(any(
            isinstance(item, dict) and item.get("code") == "non_control_records"
            for item in report["findings"]
        ))
        self.assertEqual(report["status"], "REVIEW_REQUIRED")

    def test_mixed_base_and_networkfix_records_with_same_id_are_review_blocker(self):
        current = self.candidate.read_text(encoding="utf-8")
        mixed_records = (
            "<PointRecord><Name>MIXED_EXTRA</Name><Method>FromBase</Method>"
            "<SurveyMethod>KeyedIn</SurveyMethod></PointRecord>"
            "<PointRecord><Name>MIXED_EXTRA</Name><Method>FromBase</Method>"
            "<SurveyMethod>NetworkFix</SurveyMethod></PointRecord>"
        )
        self.candidate.write_text(
            current.replace(
                "<Reductions>",
                mixed_records + "<Reductions><Point><Name>MIXED_EXTRA</Name></Point>",
                1,
            ),
            encoding="utf-8",
        )
        self.write_campaign(self.campaign, campaign(self.digest(self.candidate)))
        report = validate_candidate(self.candidate, self.campaign)
        finding = next(
            item for item in report["findings"]
            if isinstance(item, dict) and item.get("code") == "unexpected_point_ids"
        )
        self.assertEqual(finding["point_record_ids"], ["MIXED_EXTRA"])
        self.assertEqual(finding["reduction_ids"], ["MIXED_EXTRA"])
        self.assertIn("unexpected_point_ids_require_geomatic_review", report["blockers"])
        self.assertFalse(any(
            isinstance(item, dict) and item.get("code") == "non_control_records"
            for item in report["findings"]
        ))
        self.assertEqual(report["status"], "REVIEW_REQUIRED")

    def test_extra_reduction_ids_follow_last_section_parser_semantics(self):
        current = self.candidate.read_text(encoding="utf-8")
        historical = "<Reductions><Point><Name>99</Name></Point></Reductions>"
        self.candidate.write_text(current.replace("<Reductions>", historical + "<Reductions>", 1), encoding="utf-8")
        self.write_campaign(self.campaign, campaign(self.digest(self.candidate)))
        report = validate_candidate(self.candidate, self.campaign)
        unexpected = [
            item for item in report["findings"]
            if isinstance(item, dict) and item.get("code") == "unexpected_point_ids"
        ]
        self.assertEqual(unexpected, [])
        self.assertTrue(report["automatic_checks_passed"])

    def test_spatial_comparison_reports_contradiction_without_assignment(self):
        reference = self.directory / ".test_reference.jxl"
        reference.write_text(
            jobxml([
                ("1", 110.0, 210.0, 651.0, 599.7),
                ("2", 100.0, 200.0, 650.0, 598.8),
            ]),
            encoding="utf-8",
        )
        reference_campaign = self.directory / ".test_reference.json"
        self.write_campaign(reference_campaign, campaign(self.digest(reference)))
        report = validate_candidate(
            self.candidate,
            self.campaign,
            reference_path=reference,
            reference_campaign_path=reference_campaign,
        )
        self.assertTrue(report["comparison"]["performed"])
        self.assertFalse(report["comparison"]["auto_assignment_performed"])
        self.assertFalse(report["comparison"]["identity_classification_performed"])
        self.assertIsNone(report["comparison"]["identity_threshold_m"])
        self.assertIn("abs_ellipsoidal_height_delta_m", report["comparison"]["matches"][0])
        self.assertTrue(any("contradicts" in str(item) for item in report["findings"]))
        self.assertEqual(report["status"], "REVIEW_REQUIRED")

    def test_pass_automatic_requires_all_explicit_acceptances(self):
        value = campaign(self.digest(self.candidate))
        for key in value["jobxml_semantic_acceptance"]:
            value["jobxml_semantic_acceptance"][key] = True
        value["crs_acceptance"].update({
            "horizontal_epsg_accepted": True,
            "coordinate_units_accepted": True,
            "coordinate_epoch": "2026.0",
            "coordinate_epoch_accepted": True,
        })
        self.write_campaign(self.campaign, value)
        report = validate_candidate(self.candidate, self.campaign)
        self.assertEqual(report["status"], "PASS_AUTOMATIC")
        self.assertTrue(report["automatic_checks_passed"])
        self.assertFalse(report["campaign_unlock"])
        self.assertEqual(report["crs"]["horizontal_epsg_source"], "campaign_config")
        self.assertEqual(report["crs"]["horizontal_units_source"], "campaign_config")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main([str(self.candidate), str(self.campaign)])
        self.assertEqual(exit_code, STATUS_EXIT_CODES["PASS_AUTOMATIC"])

    def test_cli_exit_codes_and_json_output(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            review_code = main([str(self.candidate), str(self.campaign)])
        self.assertEqual(review_code, STATUS_EXIT_CODES["REVIEW_REQUIRED"])
        self.assertEqual(json.loads(stdout.getvalue())["status"], "REVIEW_REQUIRED")

        mismatch = campaign("f" * 64)
        self.write_campaign(self.campaign, mismatch)
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            fail_code = main([str(self.candidate), str(self.campaign)])
        self.assertEqual(fail_code, STATUS_EXIT_CODES["FAIL"])
        self.assertEqual(json.loads(stdout.getvalue())["status"], "FAIL")
        self.assertEqual(STATUS_EXIT_CODES["PASS_AUTOMATIC"], 0)

        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate_jobxml_candidate.py"),
             str(self.candidate), str(self.campaign)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, STATUS_EXIT_CODES["FAIL"])
        self.assertEqual(json.loads(completed.stdout)["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
