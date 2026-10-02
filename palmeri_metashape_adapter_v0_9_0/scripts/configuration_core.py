"""Offline configuration validation. Reads JSON configuration only, never survey data."""

import datetime
import json
import math
from pathlib import Path, PurePosixPath, PureWindowsPath
import re

from optimization_core import validate_experiment_contract, validate_optimization_contract, validate_phase_authorizations


class ConfigurationError(ValueError):
    def __init__(self, code, configuration=None):
        super().__init__(code)
        self.code = code
        self.configuration = configuration


def _fail(code):
    raise ConfigurationError(code)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail("duplicate_json_key")
        result[key] = value
    return result


def load_configuration(path):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_pairs,
                           parse_constant=lambda value: _fail("nonfinite_json"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigurationError("configuration_unreadable_or_invalid") from exc
    if type(value) is not dict:
        _fail("configuration_not_object")
    def finite(item):
        if type(item) is float and not math.isfinite(item):
            _fail("nonfinite_json")
        if isinstance(item, dict):
            for child in item.values():
                finite(child)
        if isinstance(item, list):
            for child in item:
                finite(child)
    finite(value)
    return value


def _object(value, keys, code):
    if type(value) is not dict or not set(keys) <= set(value):
        _fail(code)
    return value


def _text(value):
    return type(value) is str and bool(value.strip())


def _number(value, positive=True):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value) and (value > 0 if positive else value >= 0)
    except OverflowError:
        return False


def valid_path(value):
    if not _text(value) or any(ord(c) < 32 for c in value):
        return False
    windows = PureWindowsPath(value)
    if "\\" in value or windows.drive:
        if windows.drive and not windows.is_absolute():
            return False
        if value.startswith("\\") and not windows.is_absolute():
            return False
        parts = windows.parts[1:] if windows.anchor else windows.parts
        if any(re.search(r'[<>:"|?*]', part) or part.endswith((".", " "))
               or PureWindowsPath(part).is_reserved() for part in parts):
            return False
    else:
        parts = PurePosixPath(value).parts
        if ":" in value:
            return False
    return bool(parts) and ".." not in parts


def _date(value):
    if type(value) is not str or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        _fail("flight_date_invalid")
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        _fail("flight_date_invalid")


def _hash(value):
    return type(value) is str and re.fullmatch(r"[0-9a-fA-F]{64}", value) is not None


def validate_global(config):
    _object(config, ("schema_version", "package_name", "generated_root", "photo_selection", "camera_reference",
                     "image_quality", "validation", "metashape", "optimization", "optimization_experiments", "processing"), "global_fields_missing")
    if config["schema_version"] != "0.9.0" or not _text(config["package_name"]) or not valid_path(config["generated_root"]):
        _fail("global_identity_or_path_invalid")
    output = config["generated_root"]
    windows_output = PureWindowsPath(output)
    if not windows_output.is_absolute() and not PurePosixPath(output).is_absolute():
        _fail("generated_root_not_absolute")
    repository = Path(__file__).resolve().parents[2]
    if Path(output).is_absolute() and Path(output).resolve().is_relative_to(repository):
        _fail("generated_root_inside_repository")
    photo = _object(config["photo_selection"], ("recursive", "accepted_extensions", "selected_extensions", "fail_if_jpg_and_dng_coexist"), "photo_fields_missing")
    if type(photo["recursive"]) is not bool or photo["fail_if_jpg_and_dng_coexist"] is not True:
        _fail("photo_policy_invalid")
    for key in ("accepted_extensions", "selected_extensions"):
        if type(photo[key]) is not list or not photo[key] or any(type(v) is not str or not re.fullmatch(r"\.[A-Z]+", v) for v in photo[key]):
            _fail("photo_extensions_invalid")
        if len(set(photo[key])) != len(photo[key]):
            _fail("photo_extensions_duplicate")
    if not set(photo["selected_extensions"]) <= set(photo["accepted_extensions"]):
        _fail("photo_extension_selection_invalid")
    camera = _object(config["camera_reference"], ("maximum_position_sigma_m", "minimum_camera_agl_m", "maximum_camera_agl_m"), "camera_fields_missing")
    for key in ("load_source_coordinates", "load_xmp_accuracy", "load_xmp_orientation", "require_p1_rtk_fixed", "require_surveying_mode"):
        if camera.get(key) is not True:
            _fail("p1_policy_invalid")
    if camera.get("load_xmp_antenna") is not False:
        _fail("p1_antenna_policy_invalid")
    if not all(_number(camera[key]) for key in ("maximum_position_sigma_m", "minimum_camera_agl_m", "maximum_camera_agl_m")) or camera["minimum_camera_agl_m"] >= camera["maximum_camera_agl_m"]:
        _fail("camera_bounds_invalid")
    quality = _object(config["image_quality"], ("warning_threshold",), "quality_fields_missing")
    if quality.get("estimate_before_alignment") is not True or quality.get("automatic_exclusion") is not False or not _number(quality["warning_threshold"]) or quality["warning_threshold"] > 1:
        _fail("quality_policy_invalid")
    validation = _object(config["validation"], ("minimum_projections_per_marker", "manual_minimum_if_fewer_visible", "coordinate_tolerance_m", "accuracy_tolerance_m"), "validation_fields_missing")
    for key in ("require_all_camera_source_xyz", "require_all_camera_xmp_accuracy", "require_camera_location_off_in_master", "require_camera_rotation_off", "require_marker_reference_off_during_marking", "require_no_derived_products", "check_crs", "check_marker_accuracy"):
        if validation.get(key) is not True:
            _fail("validation_policy_invalid")
    for key in ("minimum_projections_per_marker", "manual_minimum_if_fewer_visible"):
        if type(validation[key]) is not int or validation[key] < 3:
            _fail("projection_policy_invalid")
    if validation["manual_minimum_if_fewer_visible"] > validation["minimum_projections_per_marker"] or not all(_number(validation[k]) for k in ("coordinate_tolerance_m", "accuracy_tolerance_m")):
        _fail("validation_bounds_invalid")
    metashape = _object(config["metashape"], ("target_version_prefix", "alignment_presets"), "metashape_fields_missing")
    if metashape["target_version_prefix"] != "2.3":
        _fail("metashape_version_invalid")
    presets = metashape["alignment_presets"]
    if type(presets) is not dict or not presets:
        _fail("presets_invalid")
    for name, preset in presets.items():
        _object(preset, ("downscale", "keypoint_limit", "tiepoint_limit", "generic_preselection", "reference_preselection", "filter_stationary_points", "guided_matching", "adaptive_fitting"), "preset_fields_missing")
        if not _text(name) or any(type(preset[k]) is not int or preset[k] < 0 for k in ("downscale", "keypoint_limit", "tiepoint_limit")) or any(type(preset[k]) is not bool for k in ("generic_preselection", "reference_preselection", "filter_stationary_points", "guided_matching", "adaptive_fitting")):
            _fail("preset_types_invalid")
    processing = _object(config["processing"], ("overwrite_policy", "keep_incomplete_on_success", "verify_promoted_master", "store_photo_paths_absolute"), "processing_fields_missing")
    if processing["overwrite_policy"] != "forbid" or processing["verify_promoted_master"] is not True or processing["store_photo_paths_absolute"] is not True or type(processing["keep_incomplete_on_success"]) is not bool:
        _fail("processing_policy_invalid")
    try:
        optimization = config["optimization"]
        if type(optimization) is not dict or any(type(value) is not bool for value in optimization.values()):
            _fail("optimization_boolean_invalid")
        validate_optimization_contract(config["optimization"])
        experiments = config["optimization_experiments"]
        if type(experiments) is not dict or not experiments:
            _fail("experiments_missing")
        for experiment in experiments.values():
            _object(experiment, ("review_status", "campaign_id", "flight_date", "jobxml_sha256", "required_marker_projections", "legacy_branch_disposition"), "experiment_fields_missing")
            if experiment["review_status"] not in {"APPROVED", "REVIEW_REQUIRED", "BLOCKED", "REJECTED"} or not _text(experiment["campaign_id"]) or not _hash(experiment["jobxml_sha256"]) or type(experiment["required_marker_projections"]) is not int or experiment["required_marker_projections"] < 3:
                _fail("experiment_metadata_invalid")
            _date(experiment["flight_date"])
            for key in ("expected_camera_count", "expected_transform_component_count", "transform_equivalence_significant_digits"):
                if type(experiment.get(key)) is not int or experiment[key] <= 0:
                    _fail("experiment_integer_invalid")
            indices = experiment.get("transform_equivalence_allowed_difference_indices")
            if type(indices) is not list or any(type(index) is not int or index < 0 for index in indices):
                _fail("experiment_indices_invalid")
            tolerances = experiment.get("fixed_parameter_absolute_tolerance")
            if type(tolerances) is not dict or any(not _number(value, positive=False) for value in tolerances.values()):
                _fail("experiment_tolerance_invalid")
            for key in ("source_master_equivalence_max_abs_delta", "calibration_change_detection_absolute_tolerance"):
                if not _number(experiment.get(key), positive=False):
                    _fail("experiment_tolerance_invalid")
            validate_experiment_contract(experiment)
            validate_phase_authorizations(experiment)
    except (RuntimeError, TypeError, KeyError, ValueError) as exc:
        if isinstance(exc, ConfigurationError):
            raise
        raise ConfigurationError("optimization_contract_invalid") from exc


def validate_campaign(campaign, filename, config):
    _object(campaign, ("campaign_id", "name", "status", "sensor", "kind", "output_crs", "camera_reference_crs", "marker_crs", "final_vertical_reference", "marker_projection_accuracy_px", "default_jobxml", "jobxml_rules", "control_points", "pilot_date", "alignment_preset", "flights"), "campaign_fields_missing")
    if filename == "_template_campaign.json":
        if campaign["status"] != "DRAFT" or not all(_text(campaign[k]) for k in ("campaign_id", "name", "sensor", "pilot_date")) or type(campaign["flights"]) is not list or type(campaign["control_points"]) is not dict:
            _fail("template_must_be_draft")
        return {"configuration": filename, "structural_status": "DRAFT", "operational_status": "NOT_EXECUTABLE"}
    if campaign["campaign_id"] != Path(filename).stem or type(campaign["status"]) is not str or campaign["status"] not in {"READY_FOR_PILOT", "BLOCKED_GEOMATIC_REVIEW", "BLOCKED_REVIEW", "DRAFT"}:
        _fail("campaign_identity_or_status_invalid")
    if not all(_text(campaign[k]) for k in ("name", "sensor", "final_vertical_reference")) or campaign["sensor"] != "DJI Zenmuse P1" or campaign["kind"] != "RGB":
        _fail("campaign_sensor_invalid")
    if (campaign["output_crs"], campaign["camera_reference_crs"], campaign["marker_crs"]) != ("EPSG::25830", "EPSG::4326", "EPSG::25830"):
        _fail("campaign_crs_invalid")
    if not _number(campaign["marker_projection_accuracy_px"]) or not valid_path(campaign["default_jobxml"]):
        _fail("campaign_accuracy_or_path_invalid")
    if type(campaign["alignment_preset"]) is not str or campaign["alignment_preset"] not in config["metashape"]["alignment_presets"]:
        _fail("campaign_preset_missing")
    rules = _object(campaign["jobxml_rules"], ("expected_survey_year", "expected_geoid", "expected_coordinate_tokens", "required_survey_method", "require_no_poor_precision_warning"), "jobxml_rules_missing")
    if type(rules["expected_survey_year"]) is not int or not 1900 <= rules["expected_survey_year"] <= 9999 or rules["expected_geoid"] != "EGM08IGN" or rules["required_survey_method"] != "NetworkFix" or rules["require_no_poor_precision_warning"] is not True or rules["expected_coordinate_tokens"] != ["UTM", "30 North", "ETRS89"]:
        _fail("jobxml_rules_invalid")
    if "expected_sha256" in rules and not _hash(rules["expected_sha256"]):
        _fail("jobxml_hash_invalid")
    points = campaign["control_points"]
    expected = {"E1": "GCP", "E3": "GCP", "E4": "GCP", "E6": "GCP", "C2": "CHECK_POINT", "C5": "CHECK_POINT"}
    if type(points) is not dict or len(points) != 6 or any(type(p) is not dict or set(p) != {"label", "role"} for p in points.values()):
        _fail("control_points_invalid")
    if any(not _text(k) for k in points) or any(not _text(p["label"]) or not _text(p["role"]) for p in points.values()) or {p["label"]: p["role"] for p in points.values()} != expected:
        _fail("control_roles_invalid")
    flights = campaign["flights"]
    if type(flights) is not list or not flights:
        _fail("flights_missing")
    dates = []
    for flight in flights:
        _object(flight, ("date", "input_dir", "enabled"), "flight_fields_missing")
        date = _date(flight["date"])
        if date.year != rules["expected_survey_year"] or not valid_path(flight["input_dir"]) or type(flight["enabled"]) is not bool or ("jobxml" in flight and not valid_path(flight["jobxml"])):
            _fail("flight_year_path_or_enabled_invalid")
        dates.append(flight["date"])
    _date(campaign["pilot_date"])
    if len(set(dates)) != len(dates) or campaign["pilot_date"] not in dates:
        _fail("pilot_or_duplicate_dates_invalid")
    warnings = []
    for block in ("jobxml_semantic_acceptance", "crs_acceptance"):
        if block in campaign:
            record = campaign[block]
            if type(record) is not dict:
                _fail("acceptance_record_invalid")
            required = {"identity_mapping_accepted", "roles_accepted", "horizontal_semantics_accepted", "precision_units_accepted"} if block == "jobxml_semantic_acceptance" else {"source", "horizontal_epsg", "horizontal_epsg_accepted", "coordinate_units", "coordinate_units_accepted", "coordinate_epoch", "coordinate_epoch_accepted"}
            if set(record) != required:
                _fail("acceptance_fields_invalid")
            for key, value in record.items():
                if key.endswith("_accepted"):
                    if type(value) is not bool:
                        _fail("acceptance_boolean_invalid")
                    if not value:
                        warnings.append(key + "_not_accepted")
            if block == "crs_acceptance":
                if record.get("source") != "campaign_config" or record.get("horizontal_epsg") != "EPSG::25830" or record.get("coordinate_units") != "metre":
                    _fail("crs_acceptance_fields_invalid")
                epoch = record.get("coordinate_epoch")
                if epoch is None:
                    warnings.append("coordinate_epoch_not_recorded")
                elif not _number(epoch):
                    _fail("coordinate_epoch_invalid")
    if campaign["status"] != "READY_FOR_PILOT":
        warnings.append("campaign_not_ready")
    return {"configuration": filename, "structural_status": "PASS", "operational_status": "REVIEW_REQUIRED" if warnings else "NO_CONFIGURATION_BLOCKER_IDENTIFIED", "warnings": warnings, "geomatic_acceptance": "NOT_GRANTED"}


def validate_configuration(package):
    package = Path(package)
    try:
        global_config = load_configuration(package / "config" / "global.json")
        validate_global(global_config)
    except ConfigurationError as exc:
        exc.configuration = "global.json"
        raise
    campaigns, reports = {}, []
    for path in sorted((package / "campaigns").glob("*.json")):
        try:
            value = load_configuration(path)
            reports.append(validate_campaign(value, path.name, global_config))
        except ConfigurationError as exc:
            exc.configuration = path.name
            raise
        if path.name != "_template_campaign.json":
            campaigns[value["campaign_id"]] = value
    if not campaigns:
        _fail("campaigns_missing")
    for experiment in global_config["optimization_experiments"].values():
        campaign = campaigns.get(experiment["campaign_id"])
        if campaign is None or campaign["status"] == "DRAFT" or experiment["flight_date"] != campaign["pilot_date"] or experiment["flight_date"] not in [f["date"] for f in campaign["flights"] if f["enabled"]]:
            _fail("experiment_campaign_flight_mismatch")
    return {"structural_status": "PASS", "geomatic_acceptance": "NOT_GRANTED", "campaigns": reports}
