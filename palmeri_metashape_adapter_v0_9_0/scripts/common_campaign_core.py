"""Documentary motor-neutral RGB campaign drafts; no importer or engine equivalence."""

import datetime
import re

from planning_core import BOUNDARIES, PROPOSED_REFERENCE, _exact, _fail, _object, _report, _text


ENGINES = ("metashape", "pix4dmapper")
IMAGE_EVIDENCE = ("total_inventory", "accepted_set", "human_acceptance", "human_exclusions")
CONTROL_EVIDENCE = ("jobxml", "marking", "identity_role_review", "precisions")
METASHAPE_EVIDENCE = ("common_master", "identical_parameters", "branch_constraints")


def _evidence():
    return {"sha256": None, "documentary_source": None}


def _metadata():
    return {name: {"value": None, "documentary_source": None}
            for name in ("datum", "coordinate_epoch", "ellipsoidal_height_reference")}


def default_flight():
    return {
        "flight_id": None, "flight_date": None, "accepted_image_count": None,
        "image_evidence": {name: _evidence() for name in IMAGE_EVIDENCE},
        "control_evidence": {name: _evidence() for name in CONTROL_EVIDENCE},
        "reference_metadata": {"camera": _metadata(), "control": _metadata(), "acceptance": "NOT_GRANTED"},
        "metashape_comparison_evidence": {name: _evidence() for name in METASHAPE_EVIDENCE},
    }


def default_contract_reference(engine):
    return {"engine": engine, "flight_id": None, "flight_date": None,
            "contract_schema": "planning-1" if engine == "metashape" else "NOT_DESIGNED",
            "contract_type": "flight_contract" if engine == "metashape" else "NOT_DESIGNED",
            "mapping_status": "UNVERIFIED", "sha256": None, "documentary_source": None}


def default_common_campaign():
    return {
        "schema_version": "common-campaign-1", "artifact_type": "common_campaign", "review_status": "DRAFT",
        "identity": {"campaign_id": None, "name": None, "document_version": None},
        "boundaries": dict(BOUNDARIES),
        "sensor_policy": {"status": "PROPOSED", "source": "project_policy", "acceptance": "NOT_GRANTED",
                          "sensor": "DJI Zenmuse P1", "kind": "RGB", "width_px": 8192, "height_px": 5460,
                          "bands": ["R", "G", "B"], "dimension_units": "pixel"},
        "reference_policy": {"status": "PROPOSED", "source": "project_policy", "acceptance": "NOT_GRANTED",
                             "camera_crs": "EPSG::4326", "control_crs": "EPSG::25830", "output_horizontal_crs": "EPSG::25830",
                             "camera_height": "h_ellipsoidal", "control_height": "h_ellipsoidal", "output_height": "h_ellipsoidal",
                             "camera_horizontal_units": "degree", "control_horizontal_units": "metre", "height_units": "metre",
                             "posterior_orthometric_reference": "H_EGM08IGN_ONLY_EXPLICIT_VALIDATED_TRANSFORMATION"},
        "control_policy": {"status": "PROPOSED", "source": "project_policy", "acceptance": "NOT_GRANTED",
                           "roles": dict(PROPOSED_REFERENCE["roles"]), "cp_scope": "TWO_CP_EXPLORATORY_NO_SPATIAL_EXTRAPOLATION",
                           "jobxml_adjustment_height_source": "WGS84/Height_h_ellipsoidal",
                           "jobxml_orthometric_height_source": "Grid/Elevation_H_SEPARATE_NOT_FOR_ADJUSTMENT",
                           "precision_interpretation": "ONLY_EXISTING_METASHAPE_APPROXIMATION_NOT_INDEPENDENT_COMPONENT_SIGMAS"},
        "camera_source_policy": {"source": "project_policy", "status": "PROPOSED", "acceptance": "NOT_GRANTED",
                                 "height_source": "XMP_AbsoluteAltitude_h_ellipsoidal",
                                 "precision_sources": ["XMP_RtkStdLon", "XMP_RtkStdLat", "XMP_RtkStdHgt"],
                                 "additional_lever_arm": False},
        "comparison_requirements": {"status": "PROPOSED", "acceptance": "NOT_GRANTED", "source": "project_policy",
                                    "same_accepted_image_set": "REQUIRED_NOT_VERIFIED_BY_DECLARED_HASH",
                                    "cross_engine_compatibility": "NOT_ESTABLISHED", "cross_engine_equivalence": "NOT_ESTABLISHED",
                                    "metashape_only": {"branches": ["GCP_ONLY", "GCP_P1"], "gcp_enabled": ["E1", "E3", "E4", "E6"],
                                                       "cp_enabled": False, "camera_rotation_enabled": False,
                                                       "camera_xyz_enabled": {"GCP_ONLY": False, "GCP_P1": True},
                                                       "only_camera_xyz_constraints_vary": True,
                                                       "parameters": "IDENTICAL_REQUIRED_NOT_VERIFIED", "master": "COMMON_REQUIRED_NOT_VERIFIED"}},
        "flights": [default_flight()],
        "engine_bindings": {engine: {"version": None, "edition": None, "license_description": None,
                                     "capability_evidence": _evidence(), "mapping_evidence": _evidence(),
                                     "mapping_status": "UNVERIFIED", "common_schema_adapter_status": "NOT_IMPLEMENTED"}
                            for engine in ENGINES},
        "flight_contract_references": [default_contract_reference(engine) for engine in ENGINES],
        "evaluation_protocol_reference": {"schema_version": "planning-1", "artifact_type": "evaluation_protocol",
                                          "review_status": "DRAFT", **_evidence()},
    }


def _nullable_text(value, field, missing):
    if value is None:
        missing.append(field)
    elif not _text(value):
        _fail("common_text_invalid")


def _date(value, field, missing):
    _nullable_text(value, field, missing)
    if value is not None:
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            _fail("common_flight_date_invalid")
        try:
            datetime.date.fromisoformat(value)
        except ValueError:
            _fail("common_flight_date_invalid")


def _validate_evidence(value, field, missing):
    _object(value, ("sha256", "documentary_source"))
    _nullable_text(value["documentary_source"], field + ".documentary_source", missing)
    digest = value["sha256"]
    if digest is None:
        missing.append(field + ".sha256")
    elif type(digest) is not str or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
        _fail("common_evidence_hash_invalid")


def validate_common_campaign(value):
    template = default_common_campaign()
    _object(value, template)
    if type(value["review_status"]) is not str or value["review_status"] not in {"DRAFT", "REVIEW_REQUIRED", "REJECTED"}:
        _fail("common_review_status_invalid")
    for key in ("schema_version", "artifact_type", "boundaries", "sensor_policy", "reference_policy", "control_policy",
                "camera_source_policy", "comparison_requirements"):
        _exact(value[key], template[key])
    missing = []
    _object(value["identity"], template["identity"])
    for key, item in value["identity"].items():
        _nullable_text(item, "identity." + key, missing)
    flights = value["flights"]
    if type(flights) is not list or not flights:
        _fail("common_flights_required")
    by_id = {}
    dates = set()
    for index, flight in enumerate(flights):
        field = "flights[" + str(index) + "]"
        _object(flight, default_flight())
        _nullable_text(flight["flight_id"], field + ".flight_id", missing)
        _date(flight["flight_date"], field + ".flight_date", missing)
        if flight["flight_id"] is not None:
            if flight["flight_id"] in by_id:
                _fail("common_duplicate_flight_id")
            by_id[flight["flight_id"]] = flight
        if flight["flight_date"] is not None:
            dates.add(flight["flight_date"])
        count = flight["accepted_image_count"]
        if count is None:
            missing.append(field + ".accepted_image_count")
        elif type(count) is not int or not 0 < count <= 10**12:
            _fail("common_image_count_invalid")
        for group, names in (("image_evidence", IMAGE_EVIDENCE), ("control_evidence", CONTROL_EVIDENCE),
                             ("metashape_comparison_evidence", METASHAPE_EVIDENCE)):
            _object(flight[group], names)
            for name in names:
                _validate_evidence(flight[group][name], field + "." + group + "." + name, missing)
        metadata = flight["reference_metadata"]
        _object(metadata, ("camera", "control", "acceptance"))
        _exact(metadata["acceptance"], "NOT_GRANTED")
        for target in ("camera", "control"):
            _object(metadata[target], _metadata())
            for name, record in metadata[target].items():
                _object(record, ("value", "documentary_source"))
                prefix = field + ".reference_metadata." + target + "." + name
                _nullable_text(record["value"], prefix + ".value", missing)
                _nullable_text(record["documentary_source"], prefix + ".documentary_source", missing)
                if record["value"] is not None:
                    if record["documentary_source"] is None:
                        _fail("common_metadata_source_missing")
                    if name == "coordinate_epoch" and not re.fullmatch(r"[0-9]{4}(?:\.[0-9]{1,8})?", record["value"]):
                        _fail("common_epoch_format_invalid")
    _object(value["engine_bindings"], ENGINES)
    for engine in ENGINES:
        binding = value["engine_bindings"][engine]
        _object(binding, template["engine_bindings"][engine])
        for key in ("mapping_status", "common_schema_adapter_status"):
            _exact(binding[key], template["engine_bindings"][engine][key])
        for key in ("version", "edition", "license_description"):
            _nullable_text(binding[key], "engine_bindings." + engine + "." + key, missing)
        if binding["version"] is not None and not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", binding["version"]):
            _fail("common_engine_version_invalid")
        for key in ("capability_evidence", "mapping_evidence"):
            _validate_evidence(binding[key], "engine_bindings." + engine + "." + key, missing)
    references = value["flight_contract_references"]
    if type(references) is not list:
        _fail("common_contract_references_invalid")
    seen = set()
    for index, record in enumerate(references):
        _object(record, default_contract_reference("metashape"))
        engine = record["engine"]
        if type(engine) is not str or engine not in ENGINES:
            _fail("common_contract_engine_invalid")
        expected = default_contract_reference(engine)
        for key in ("contract_schema", "contract_type", "mapping_status"):
            _exact(record[key], expected[key])
        prefix = "flight_contract_references[" + str(index) + "]"
        _nullable_text(record["flight_id"], prefix + ".flight_id", missing)
        _date(record["flight_date"], prefix + ".flight_date", missing)
        _validate_evidence({key: record[key] for key in ("sha256", "documentary_source")}, prefix, missing)
        pair = (engine, record["flight_id"])
        if pair in seen:
            _fail("common_duplicate_contract_reference")
        seen.add(pair)
        if record["flight_id"] is not None:
            if record["flight_id"] not in by_id:
                _fail("common_contract_flight_missing")
            flight_date = by_id[record["flight_id"]]["flight_date"]
            if record["flight_date"] is not None and flight_date is not None and record["flight_date"] != flight_date:
                _fail("common_contract_date_mismatch")
        elif record["flight_date"] is not None and record["flight_date"] not in dates:
            _fail("common_contract_date_unresolved")
    for index, flight in enumerate(flights):
        for engine in ENGINES:
            if flight["flight_id"] is None or (engine, flight["flight_id"]) not in seen:
                missing.append("flights[" + str(index) + "].contract_reference." + engine)
    protocol = value["evaluation_protocol_reference"]
    _object(protocol, template["evaluation_protocol_reference"])
    for key in ("schema_version", "artifact_type", "review_status"):
        _exact(protocol[key], template["evaluation_protocol_reference"][key])
    _validate_evidence({key: protocol[key] for key in ("sha256", "documentary_source")}, "evaluation_protocol_reference", missing)
    report = _report("common_campaign", missing)
    report.update(source_review_status=value["review_status"], compatibility_verified=False,
                  cross_engine_equivalence="NOT_ESTABLISHED", common_schema_adapter_status="NOT_IMPLEMENTED")
    return report
