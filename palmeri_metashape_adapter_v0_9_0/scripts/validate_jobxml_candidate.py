"""Redacted, read-only audit of a JobXML candidate against campaign rules."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import statistics
import sys
import xml.etree.ElementTree as ET

from orthomation_core import ValidationError, parse_jobxml, sha256_file


SCHEMA = "orthomation.jobxml-candidate-validation/1"
TOOL_VERSION = "1.0.0"
STATUS_EXIT_CODES = {"PASS_AUTOMATIC": 0, "REVIEW_REQUIRED": 2, "FAIL": 1}
ACCEPTANCE_KEYS = (
    "identity_mapping_accepted",
    "roles_accepted",
    "horizontal_semantics_accepted",
    "precision_units_accepted",
)
CRS_ACCEPTANCE_FIELDS = (
    ("horizontal_epsg", "horizontal_epsg_accepted"),
    ("coordinate_units", "coordinate_units_accepted"),
    ("coordinate_epoch", "coordinate_epoch_accepted"),
)


def _config_hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _load_campaign(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("campaign configuration must be a JSON object")
    if not isinstance(value.get("control_points"), dict) or not value["control_points"]:
        raise ValueError("campaign configuration has no control_points mapping")
    if not isinstance(value.get("jobxml_rules"), dict):
        raise ValueError("campaign configuration has no jobxml_rules object")
    return value


def _candidate_metadata(path: Path) -> dict:
    result = {
        "basename": path.name,
        "sha256": None,
        "size_bytes": None,
        "jobxml_version": None,
        "observation_years": [],
    }
    if path.is_file():
        result["sha256"] = sha256_file(path)
        result["size_bytes"] = path.stat().st_size
    return result


def _redacted_rules(rules: dict) -> dict:
    allowed = (
        "expected_survey_year",
        "expected_geoid",
        "expected_coordinate_tokens",
        "required_survey_method",
        "require_no_poor_precision_warning",
        "expected_sha256",
    )
    return {key: rules.get(key) for key in allowed if key in rules}


def _crs_summary(job: dict, acceptance: dict | None = None) -> dict:
    coordinate = job["coordinate_system"]
    acceptance = acceptance or {}
    source = acceptance.get("source")
    coordinate_units = acceptance.get("coordinate_units")
    return {
        "system_name": coordinate.get("SystemName"),
        "zone_name": coordinate.get("ZoneName"),
        "datum_name": coordinate.get("DatumName"),
        "horizontal_epsg": acceptance.get("horizontal_epsg"),
        "horizontal_epsg_source": source if "horizontal_epsg" in acceptance else None,
        "horizontal_units": coordinate_units,
        "horizontal_units_source": source if "coordinate_units" in acceptance else None,
        "coordinate_epoch": acceptance.get("coordinate_epoch"),
        "coordinate_epoch_source": source if "coordinate_epoch" in acceptance else None,
        "vertical_adjustment": job.get("vertical_adjustment"),
        "geoid_name": job.get("geoid"),
        "vertical_units": coordinate_units,
        "vertical_units_source": source if "coordinate_units" in acceptance else None,
    }


def _separation_summary(job: dict) -> dict:
    values = [point["geoid_separation"] for point in job["points"].values()]
    return {
        "ellipsoidal_height_source": "Reductions.Point.WGS84.Height",
        "orthometric_height_source": "Reductions.Point.Grid.Elevation",
        "separation_definition": "ellipsoidal_minus_orthometric",
        "count": len(values),
        "minimum_m": min(values),
        "maximum_m": max(values),
        "mean_m": statistics.fmean(values),
        "spread_m": max(values) - min(values),
    }


def _point_summaries(job: dict) -> list[dict]:
    return [
        {
            "job_id": point["job_id"],
            "label": point["label"],
            "role": point["role"],
            "role_source": "campaign_config",
            "survey_method": point["survey_method"],
            "deleted": point["deleted"],
            "timestamp": point["timestamp"],
            "observation_year": (
                None if point["timestamp"] is None else int(point["timestamp"][:4])
            ),
            "satellites": point["satellites"],
            "pdop": point["pdop"],
            "horizontal_precision_m": point["horizontal_precision"],
            "vertical_precision_m": point["vertical_precision"],
            "poor_precision_warning": point["poor_precision_warning"],
        }
        for point in job["points"].values()
    ]


def _explicit_comparison_crs_matches(left: dict, right: dict) -> bool:
    keys = (
        "system_name",
        "zone_name",
        "datum_name",
        "vertical_adjustment",
        "geoid_name",
    )
    return all(left.get(key) is not None and left.get(key) == right.get(key) for key in keys)


def _jobxml_point_ids(path: Path) -> dict[str, list]:
    """Read identifiers, using the last Reductions section like parse_jobxml()."""
    root = ET.parse(path).getroot()

    def local(tag):
        return tag.rsplit("}", 1)[-1]

    def child_text(element, name):
        child = next((item for item in list(element) if local(item.tag) == name), None)
        if child is None or child.text is None:
            return None
        value = child.text.strip()
        return value or None

    records = []
    reduction_sections = []
    for element in root.iter():
        kind = local(element.tag)
        if kind == "PointRecord":
            name = child_text(element, "Name")
            if name is not None:
                records.append({
                    "name": name,
                    "survey_method": child_text(element, "SurveyMethod"),
                    "method": child_text(element, "Method"),
                })
        elif kind == "Reductions":
            reduction_sections.append([
                name
                for point in list(element)
                if local(point.tag) == "Point"
                for name in [child_text(point, "Name")]
                if name is not None
            ])
    reductions = reduction_sections[-1] if reduction_sections else []
    return {"point_records": records, "reduction_ids": reductions}


def _compare_jobs(candidate: dict, reference: dict) -> tuple[dict, list[str]]:
    rows = []
    contradictions = []
    reference_points = list(reference["points"].values())
    for candidate_point in candidate["points"].values():
        ranked = []
        for reference_point in reference_points:
            distance = math.hypot(
                candidate_point["easting"] - reference_point["easting"],
                candidate_point["northing"] - reference_point["northing"],
            )
            ranked.append((distance, reference_point))
        ranked.sort(key=lambda item: (item[0], item[1]["job_id"]))
        nearest_distance, nearest = ranked[0]
        second_distance = ranked[1][0] if len(ranked) > 1 else None
        row = {
            "candidate_id": candidate_point["job_id"],
            "candidate_label": candidate_point["label"],
            "candidate_role": candidate_point["role"],
            "nearest_reference_id": nearest["job_id"],
            "nearest_reference_label": nearest["label"],
            "nearest_reference_role": nearest["role"],
            "nearest_distance_m": nearest_distance,
            "second_nearest_distance_m": second_distance,
            "distance_margin_m": None if second_distance is None else second_distance - nearest_distance,
            "abs_ellipsoidal_height_delta_m": abs(
                candidate_point["h_ellipsoid"] - nearest["h_ellipsoid"]
            ),
            "configured_label_matches_nearest": candidate_point["label"] == nearest["label"],
            "configured_role_matches_nearest": candidate_point["role"] == nearest["role"],
        }
        if not row["configured_label_matches_nearest"] or not row["configured_role_matches_nearest"]:
            contradictions.append(
                "nearest-reference diagnostic contradicts configured label or role for "
                f"candidate point {candidate_point['job_id']}"
            )
        rows.append(row)
    return {
        "performed": True,
        "auto_assignment_performed": False,
        "identity_threshold_m": None,
        "identity_classification_performed": False,
        "reference": {
            "basename": Path(reference["path"]).name,
            "sha256": reference["sha256"],
            "jobxml_version": reference["jobxml_version"],
            "observation_years": reference["observation_years"],
        },
        "matches": rows,
    }, contradictions


def validate_candidate(
    candidate_path,
    campaign_path,
    reference_path=None,
    reference_campaign_path=None,
) -> dict:
    candidate_path = Path(candidate_path)
    campaign_path = Path(campaign_path)
    report = {
        "schema_version": SCHEMA,
        "tool_version": TOOL_VERSION,
        "status": "FAIL",
        "automatic_checks_passed": False,
        "geomatic_acceptance": "NOT_GRANTED",
        "campaign_unlock": False,
        "candidate": _candidate_metadata(candidate_path),
        "configuration": {
            "campaign_id": None,
            "basename": campaign_path.name,
            "sha256": None,
            "rules": {},
        },
        "crs": {
            "system_name": None,
            "zone_name": None,
            "datum_name": None,
            "horizontal_epsg": None,
            "horizontal_epsg_source": None,
            "horizontal_units": None,
            "horizontal_units_source": None,
            "coordinate_epoch": None,
            "coordinate_epoch_source": None,
            "vertical_adjustment": None,
            "geoid_name": None,
            "vertical_units": None,
            "vertical_units_source": None,
        },
        "height_references": None,
        "points": [],
        "comparison": {
            "performed": False,
            "auto_assignment_performed": False,
            "identity_threshold_m": None,
            "identity_classification_performed": False,
        },
        "errors": [],
        "warnings": [],
        "findings": [],
        "blockers": [],
    }
    try:
        campaign = _load_campaign(campaign_path)
        report["configuration"].update(
            campaign_id=str(campaign.get("campaign_id")) if campaign.get("campaign_id") is not None else None,
            sha256=_config_hash(campaign_path),
            rules=_redacted_rules(campaign["jobxml_rules"]),
        )
    except (OSError, ValueError, json.JSONDecodeError):
        report["errors"].append("campaign_config_invalid")
        return report

    if not candidate_path.is_file():
        report["errors"].append("candidate_not_found")
        return report

    expected_hash = campaign["jobxml_rules"].get("expected_sha256")
    if expected_hash is None:
        report["errors"].append("expected_candidate_sha256_missing")
        return report
    elif not isinstance(expected_hash, str) or re.fullmatch(r"[0-9a-fA-F]{64}", expected_hash) is None:
        report["errors"].append("expected_candidate_sha256_invalid")
        return report
    elif report["candidate"]["sha256"] != expected_hash.lower():
        report["errors"].append("candidate_sha256_mismatch")
        return report

    try:
        observed_ids = _jobxml_point_ids(candidate_path)
    except (OSError, ET.ParseError):
        report["errors"].append("candidate_xml_invalid")
        return report
    expected_ids = {str(value) for value in campaign["control_points"]}
    extra_records = [
        record for record in observed_ids["point_records"] if record["name"] not in expected_ids
    ]
    records_by_name = {}
    for record in extra_records:
        records_by_name.setdefault(record["name"], []).append(record)
    non_control_names = {
        name
        for name, records in records_by_name.items()
        if all(
            record["method"] == "FromBase" and record["survey_method"] == "KeyedIn"
            for record in records
        )
    }
    non_control_records = [
        record for record in extra_records if record["name"] in non_control_names
    ]
    extra_control_ids = sorted({
        record["name"] for record in extra_records if record["name"] not in non_control_names
    })
    extra_reduction_ids = sorted(
        set(observed_ids["reduction_ids"]) - expected_ids - non_control_names
    )
    if non_control_records:
        report["findings"].append({
            "code": "non_control_records",
            "count": len(non_control_records),
            "survey_methods": sorted({record["survey_method"] for record in non_control_records}, key=str),
            "methods": sorted({record["method"] for record in non_control_records}, key=str),
            "identifiers_redacted": True,
        })
    if extra_control_ids or extra_reduction_ids:
        report["findings"].append(
            {
                "code": "unexpected_point_ids",
                "point_record_ids": extra_control_ids,
                "reduction_ids": extra_reduction_ids,
            }
        )
        report["blockers"].append("unexpected_point_ids_require_geomatic_review")

    try:
        candidate = parse_jobxml(
            candidate_path,
            campaign["control_points"],
            campaign["jobxml_rules"],
        )
    except (OSError, ValueError, ET.ParseError, ValidationError):
        report["errors"].append("candidate_validation_failed")
        return report

    report["candidate"].update(
        jobxml_version=candidate["jobxml_version"],
        observation_years=candidate["observation_years"],
    )
    crs_acceptance = campaign.get("crs_acceptance", {})
    report["crs"] = _crs_summary(candidate, crs_acceptance)
    report["height_references"] = _separation_summary(candidate)
    report["points"] = _point_summaries(candidate)

    if report["errors"]:
        return report

    if reference_path is not None:
        reference_path = Path(reference_path)
        if reference_campaign_path is None:
            report["errors"].append("reference_campaign_required")
            return report
        reference_campaign_path = Path(reference_campaign_path)
        try:
            reference_campaign = _load_campaign(reference_campaign_path)
            reference = parse_jobxml(
                reference_path,
                reference_campaign["control_points"],
                reference_campaign["jobxml_rules"],
            )
        except (OSError, ValueError, json.JSONDecodeError, ET.ParseError, ValidationError):
            report["errors"].append("reference_validation_failed")
            return report
        reference_crs = _crs_summary(reference, reference_campaign.get("crs_acceptance", {}))
        if not _explicit_comparison_crs_matches(report["crs"], reference_crs):
            report["blockers"].append("reference_crs_not_explicitly_compatible")
        else:
            report["comparison"], contradictions = _compare_jobs(candidate, reference)
            report["findings"].extend(contradictions)
            if contradictions:
                report["blockers"].append("configured_identity_or_role_requires_geomatic_review")
            else:
                report["blockers"].append("spatial_correspondence_requires_geomatic_review")

    acceptance = campaign.get("jobxml_semantic_acceptance", {})
    missing = [key for key in ACCEPTANCE_KEYS if acceptance.get(key) is not True]
    if missing:
        report["blockers"].append("semantic_acceptance_not_recorded: " + ", ".join(missing))
    if crs_acceptance.get("source") != "campaign_config":
        report["blockers"].append("crs_acceptance_source_not_configured")
    for value_key, accepted_key in CRS_ACCEPTANCE_FIELDS:
        if crs_acceptance.get(value_key) is None:
            report["warnings"].append(f"{value_key}_not_explicitly_configured")
        if crs_acceptance.get(accepted_key) is not True or crs_acceptance.get(value_key) is None:
            report["blockers"].append(f"{value_key}_requires_geomatic_review")

    report["automatic_checks_passed"] = True
    report["status"] = "REVIEW_REQUIRED" if report["blockers"] else "PASS_AUTOMATIC"
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("campaign", type=Path)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--reference-campaign", type=Path)
    return parser


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    report = validate_candidate(
        args.candidate,
        args.campaign,
        args.reference,
        args.reference_campaign,
    )
    json.dump(report, sys.stdout, ensure_ascii=False, sort_keys=True)
    sys.stdout.write("\n")
    return STATUS_EXIT_CODES[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
