import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from orthomation_core import ValidationError, parse_jobxml, read_dji_xmp


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


if __name__ == "__main__":
    unittest.main()
