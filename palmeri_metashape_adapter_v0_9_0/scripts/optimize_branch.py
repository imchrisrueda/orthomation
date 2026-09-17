"""Run a reviewed fixed-model optimization and fail closed on post-checks."""

from pathlib import Path
import datetime
import importlib
import json
import os
import platform
import traceback
import Metashape

import optimization_core
import orthomation_core

optimization_core = importlib.reload(optimization_core)
orthomation_core = importlib.reload(orthomation_core)
parse_jobxml = orthomation_core.parse_jobxml
transform_fingerprint = orthomation_core.transform_fingerprint

ROOT = Path(__file__).resolve().parent.parent
RUN_ID = os.environ.get("PALMERI_RUN_ID", "fixed_model_v1").strip()
CALIBRATION_NAMES = optimization_core.CALIBRATION_PARAMETERS


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as stream:
        return json.load(stream)


def write_json_forbid(path, payload):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False)


def meta_value(owner, key, default=None):
    try:
        value = owner.meta[key]
    except (KeyError, TypeError):
        return default
    return default if value is None else value


def location_enabled(reference):
    return bool(reference.location_enabled) if hasattr(reference, "location_enabled") else bool(reference.enabled)


def projection_count(marker):
    return sum(
        1 for _, projection in marker.projections.items()
        if projection is not None and bool(getattr(projection, "pinned", False))
    )


def calibration_snapshot(chunk):
    rows = []
    for sensor in chunk.sensors:
        calibration = sensor.calibration
        rows.append({
            "sensor_key": str(sensor.key),
            "sensor": sensor.label,
            "type": str(sensor.type),
            "width": sensor.width,
            "height": sensor.height,
            "parameters": {name: float(getattr(calibration, name)) for name in CALIBRATION_NAMES},
        })
    return rows


def sensor_photo_parameter_issues(chunk):
    issues = []
    for sensor in chunk.sensors:
        photo_params = getattr(sensor, "photo_params", None)
        try:
            present = photo_params is not None and len(photo_params) > 0
        except TypeError:
            present = bool(photo_params)
        if present:
            issues.append(f"{sensor.label}: per-photo calibration parameters are present and unsupported by this audit")
    return issues


def sensor_photo_parameter_state(chunk):
    rows = []
    for sensor in chunk.sensors:
        photo_params = getattr(sensor, "photo_params", None)
        try:
            count = 0 if photo_params is None else len(photo_params)
        except TypeError:
            count = int(bool(photo_params))
        rows.append({"sensor_key": str(sensor.key), "sensor": sensor.label, "count": count})
    return rows


def derived_products(chunk):
    names = ("point_cloud", "elevation", "orthomosaic", "model", "tiled_model", "depth_maps")
    return [name for name in names if getattr(chunk, name, None) is not None]


def current_preoptimization_issues(chunk, experiment, branch, preflight, job, config):
    issues = []
    expected_cameras = int(experiment["expected_camera_count"])
    if len(chunk.cameras) != expected_cameras:
        issues.append(f"Cameras={len(chunk.cameras)}; expected {expected_cameras}")
    camera_location_on = 0
    camera_rotation_on = 0
    for camera in chunk.cameras:
        if camera.reference.location is None:
            issues.append(f"{camera.label}: source XYZ missing")
        camera_location_on += int(location_enabled(camera.reference))
        camera_rotation_on += int(bool(getattr(camera.reference, "rotation_enabled", False)))
    expected_location_on = expected_cameras if branch == "GCP_P1" else 0
    if camera_location_on != expected_location_on:
        issues.append(f"Camera XYZ ON={camera_location_on}; expected {expected_location_on}")
    if camera_rotation_on:
        issues.append(f"Camera rotations ON={camera_rotation_on}; expected 0")

    expected_markers = {point["label"]: point for point in job["points"].values()}
    preflight_markers = {row["label"]: row for row in preflight.get("markers", [])}
    current_markers = {marker.label: marker for marker in chunk.markers}
    required_projections = int(experiment["required_marker_projections"])
    for label, expected in expected_markers.items():
        marker = current_markers.get(label)
        if marker is None:
            issues.append(f"Missing marker {label}")
            continue
        enabled = location_enabled(marker.reference)
        should_be_enabled = expected.get("role") == "GCP"
        if enabled != should_be_enabled:
            issues.append(f"{label}: enabled={enabled}; expected {should_be_enabled}")
        if label in {"C2", "C5"} and enabled:
            issues.append(f"{label}: check point must remain disabled")
        projections = projection_count(marker)
        if projections != required_projections:
            issues.append(f"{label}: projections={projections}; expected {required_projections}")
        expected_location = [expected["easting"], expected["northing"], expected["h_ellipsoid"]]
        loaded_location = [] if marker.reference.location is None else [float(marker.reference.location[i]) for i in range(3)]
        coordinate_tolerance = float(config["validation"]["coordinate_tolerance_m"])
        if len(loaded_location) != 3 or any(abs(a - b) > coordinate_tolerance for a, b in zip(loaded_location, expected_location)):
            issues.append(f"{label}: coordinate differs from live JobXML")
        expected_accuracy = [expected["horizontal_precision"], expected["horizontal_precision"], expected["vertical_precision"]]
        loaded_accuracy = [] if marker.reference.accuracy is None else [float(marker.reference.accuracy[i]) for i in range(3)]
        accuracy_tolerance = float(config["validation"]["accuracy_tolerance_m"])
        if len(loaded_accuracy) != 3 or any(abs(a - b) > accuracy_tolerance for a, b in zip(loaded_accuracy, expected_accuracy)):
            issues.append(f"{label}: accuracy differs from live JobXML")
    if set(expected_markers) != {"E1", "C2", "E3", "E4", "C5", "E6"}:
        issues.append(f"Live JobXML marker set is unexpected: {sorted(expected_markers)}")
    if set(preflight_markers) != set(expected_markers):
        issues.append(f"Preflight marker set differs from live JobXML: {sorted(preflight_markers)}")
    products = derived_products(chunk)
    if products:
        issues.append(f"Derived products exist before optimization: {products}")
    return issues


def encoded_task(task):
    for method_name in ("encodeJSON", "encode"):
        method = getattr(task, method_name, None)
        if method is None:
            continue
        try:
            return {"method": method_name, "payload": method()}
        except Exception as exc:
            return {"method": method_name, "error": str(exc)}
    return {"method": None, "error": "Task serialization is not available"}


def build_task(parameters):
    task = Metashape.Tasks.OptimizeCameras()
    for name, value in parameters.items():
        setattr(task, name, value)
    recorded = {name: bool(getattr(task, name)) for name in parameters}
    if recorded != parameters:
        raise RuntimeError(f"OptimizeCameras task did not retain requested parameters: {recorded}")
    return task, recorded, encoded_task(task)


def reopen_saved_document(doc):
    path = str(doc.path)
    doc.open(path)


def base_report(chunk, branch, parameters, started):
    return {
        "adapter_version": "0.9.0",
        "run_id": RUN_ID,
        "branch": branch,
        "chunk": chunk.label,
        "started_at_utc": started,
        "completed_at_utc": None,
        "status": "FAIL",
        "issues": [],
        "metashape_version": str(Metashape.app.version),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "requested_parameters": parameters,
        "effective_parameter_set": {
            "api_available": False,
            "value": None,
            "note": "Metashape 2.3.1 does not expose a post-optimization effective fitted-parameter set.",
        },
        "additional_corrections": {
            "requested": parameters["fit_corrections"],
            "full_posthoc_coefficient_api_available": False,
            "verified_absent_with_observable_api": False,
        },
    }


def main():
    doc = Metashape.app.document
    chunk = doc.chunk
    if chunk is None or not doc.path:
        raise RuntimeError("Open and save a validated run-scoped branch first")
    config = load_json(ROOT / "config" / "global.json")
    if config.get("processing", {}).get("overwrite_policy") != "forbid":
        raise RuntimeError("overwrite_policy must remain 'forbid'")
    experiment = optimization_core.require_approved_experiment(config, RUN_ID)
    optimization_core.validate_metashape_version(Metashape.app.version, experiment["reviewed_metashape_version"])
    parameters = optimization_core.validate_optimization_contract(config["optimization"])

    branch = meta_value(chunk, "orthomation/branch")
    if branch not in {"GCP_ONLY", "GCP_P1"}:
        raise RuntimeError("Active chunk is not a controlled branch")
    if meta_value(chunk, "orthomation/run_id") != RUN_ID:
        raise RuntimeError("Active chunk run_id does not match requested run")
    if meta_value(chunk, "orthomation/stage") != "BRANCH_READY_FOR_FIXED_MODEL_OPTIMIZE":
        raise RuntimeError("Branch is not in BRANCH_READY_FOR_FIXED_MODEL_OPTIMIZE state")
    if not chunk.label.endswith(f"_{branch}_{RUN_ID}"):
        raise RuntimeError("Active chunk label does not match branch/run_id metadata")

    project_dir = Path(doc.path).resolve().parent
    preflight_path = project_dir / f"preopt_{RUN_ID}_{branch}_v0_9_0.json"
    output = project_dir / f"optimization_{RUN_ID}_{branch}_v0_9_0.json"
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite optimization report: {output}")
    if not preflight_path.is_file():
        raise RuntimeError(f"Run validate_before_optimize.py first: {preflight_path}")
    preflight = load_json(preflight_path)
    campaign_id = meta_value(chunk, "orthomation/campaign_id")
    if campaign_id != experiment["campaign_id"]:
        raise RuntimeError("Active branch campaign differs from the reviewed experiment")
    if meta_value(chunk, "orthomation/flight_date") != experiment["flight_date"]:
        raise RuntimeError("Active branch flight differs from the reviewed experiment")
    campaign = load_json(ROOT / "campaigns" / f"{campaign_id}.json")
    jobxml_path = meta_value(chunk, "orthomation/jobxml_path")
    if not jobxml_path:
        raise RuntimeError("Active branch does not record a JobXML path")
    job = parse_jobxml(jobxml_path, campaign["control_points"], campaign["jobxml_rules"])
    current_fingerprint = transform_fingerprint(chunk)
    gate_issues = []
    if preflight.get("status") != "PASS":
        gate_issues.append("Latest run-scoped preflight is not PASS")
    if preflight.get("run_id") != RUN_ID or preflight.get("branch") != branch:
        gate_issues.append("Preflight run_id/branch mismatch")
    if preflight.get("optimization_parameters") != parameters:
        gate_issues.append("Optimization parameters changed after preflight")
    if preflight.get("preopt_transform_sha256") != current_fingerprint:
        gate_issues.append("Branch changed after preflight")
    if current_fingerprint != experiment["source_master_live_transform_sha256"]:
        gate_issues.append("Branch no longer has the exact required live source MASTER fingerprint")
    if preflight.get("source_master_persisted_transform_sha256") != experiment["source_master_transform_sha256"]:
        gate_issues.append("Preflight persisted source MASTER fingerprint mismatch")
    if preflight.get("source_master_live_transform_sha256") != experiment["source_master_live_transform_sha256"]:
        gate_issues.append("Preflight live source MASTER fingerprint mismatch")
    if preflight.get("source_master_common_12sig_transform_sha256") != experiment["source_master_common_12sig_transform_sha256"]:
        gate_issues.append("Preflight common 12-significant-digit source MASTER fingerprint mismatch")
    if meta_value(chunk, "orthomation/source_master_persisted_transform_sha256") != experiment["source_master_transform_sha256"]:
        gate_issues.append("Chunk persisted source MASTER fingerprint metadata mismatch")
    if meta_value(chunk, "orthomation/source_master_transform_sha256") != experiment["source_master_transform_sha256"]:
        gate_issues.append("Chunk legacy persisted source MASTER fingerprint metadata mismatch")
    if meta_value(chunk, "orthomation/source_master_live_transform_sha256") != experiment["source_master_live_transform_sha256"]:
        gate_issues.append("Chunk live source MASTER fingerprint metadata mismatch")
    if meta_value(chunk, "orthomation/source_master_common_12sig_transform_sha256") != experiment["source_master_common_12sig_transform_sha256"]:
        gate_issues.append("Chunk common source MASTER fingerprint metadata mismatch")
    if preflight.get("jobxml_sha256") != experiment["jobxml_sha256"]:
        gate_issues.append("Preflight JobXML fingerprint mismatch")
    if job["sha256"] != experiment["jobxml_sha256"]:
        gate_issues.append("Live JobXML fingerprint differs from the reviewed experiment")
    if meta_value(chunk, "orthomation/jobxml_sha256") != job["sha256"]:
        gate_issues.append("Chunk JobXML fingerprint differs from the live JobXML")
    gate_issues.extend(current_preoptimization_issues(chunk, experiment, branch, preflight, job, config))
    gate_issues.extend(sensor_photo_parameter_issues(chunk))
    if gate_issues:
        raise RuntimeError("Optimization gate failed:\n- " + "\n- ".join(gate_issues))

    calibration_before = calibration_snapshot(chunk)
    photo_parameters_before = sensor_photo_parameter_state(chunk)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    report = base_report(chunk, branch, parameters, started)
    report.update({
        "jobxml_sha256": experiment["jobxml_sha256"],
        "source_master_persisted_transform_sha256": experiment["source_master_transform_sha256"],
        "source_master_live_transform_sha256": experiment["source_master_live_transform_sha256"],
        "source_master_common_12sig_transform_sha256": experiment["source_master_common_12sig_transform_sha256"],
        "transform_sha256_before": current_fingerprint,
        "calibration_before": calibration_before,
        "sensor_photo_parameters_before": photo_parameters_before,
        "fixed_parameter_absolute_tolerance": experiment["fixed_parameter_absolute_tolerance"],
    })

    try:
        task, recorded_parameters, task_serialization = build_task(parameters)
        report["task_recorded_parameters"] = recorded_parameters
        report["task_serialization"] = task_serialization
        task.apply(chunk)
        calibration_after = calibration_snapshot(chunk)
        photo_parameters_after = sensor_photo_parameter_state(chunk)
        after_fingerprint = transform_fingerprint(chunk)
        comparison = optimization_core.compare_calibrations(
            calibration_before,
            calibration_after,
            experiment["allowed_calibration_parameters"],
            experiment["fixed_calibration_parameters"],
            experiment.get("nonadjustable_calibration_parameters_audited", []),
            experiment["fixed_parameter_absolute_tolerance"],
            experiment["calibration_change_detection_absolute_tolerance"],
        )
        post_issues = list(comparison["issues"])
        post_issues.extend(sensor_photo_parameter_issues(chunk))
        before_photo_empty = all(row["count"] == 0 for row in photo_parameters_before)
        after_photo_empty = all(row["count"] == 0 for row in photo_parameters_after)
        products = derived_products(chunk)
        if products:
            post_issues.append(f"Derived products appeared during optimization: {products}")
        if recorded_parameters.get("adaptive_fitting") is not False:
            post_issues.append("OptimizeCameras did not record adaptive_fitting=false")
        if recorded_parameters.get("fit_corrections") is not False:
            post_issues.append("OptimizeCameras did not record fit_corrections=false")
        report.update({
            "completed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "issues": post_issues,
            "transform_sha256_after": after_fingerprint,
            "calibration_after": calibration_after,
            "sensor_photo_parameters_after": photo_parameters_after,
            "calibration_comparison": comparison,
            "derived_products_after": products,
        })
        report["additional_corrections"].update({
            "task_retained_fit_corrections_false": recorded_parameters.get("fit_corrections") is False,
            "sensor_photo_parameters_empty_before": before_photo_empty,
            "sensor_photo_parameters_empty_after": after_photo_empty,
            "verified_absent_with_observable_api": (
                recorded_parameters.get("fit_corrections") is False
                and before_photo_empty
                and after_photo_empty
            ),
            "note": "Metashape 2.3.1 exposes the task flag and per-photo parameter surface, but no complete post-hoc additional-correction coefficient set.",
        })
        if not report["additional_corrections"]["verified_absent_with_observable_api"]:
            post_issues.append("Observable additional-correction surfaces are not proven absent")
        if post_issues:
            reopen_saved_document(doc)
            write_json_forbid(output, report)
            raise RuntimeError("Post-optimization checks failed; saved project was reloaded without changes:\n- " + "\n- ".join(post_issues))

        report["status"] = "OPTIMIZED_FIXED_MODEL"
        report["next_action"] = "Run export_postoptimization_metrics.py; do not select a branch or build products."
        chunk.meta["orthomation/stage"] = "OPTIMIZED_FIXED_MODEL"
        chunk.meta["orthomation/optimized_at_utc"] = report["completed_at_utc"]
        chunk.meta["orthomation/optimization_run_id"] = RUN_ID
        chunk.meta["orthomation/optimization_parameters"] = json.dumps(parameters, sort_keys=True)
        chunk.meta["orthomation/postopt_transform_sha256"] = after_fingerprint
        doc.save()
        write_json_forbid(output, report)
    except Exception as exc:
        if report.get("completed_at_utc") is None:
            report["completed_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            report["issues"] = [str(exc)]
            report["traceback"] = traceback.format_exc()
            try:
                reopen_saved_document(doc)
            finally:
                write_json_forbid(output, report)
        raise

    print(json.dumps(report, indent=2, ensure_ascii=False))
    Metashape.app.messageBox(
        f"{RUN_ID}/{branch}: OPTIMIZED_FIXED_MODEL. "
        "Run the read-only metrics exporter; do not build products."
    )


if __name__ == "__main__":
    main()
