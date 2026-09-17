"""Read-only preflight for one run-scoped fixed-model branch."""

from pathlib import Path
import datetime
import importlib
import json
import os
import Metashape

import optimization_core
import orthomation_core

optimization_core = importlib.reload(optimization_core)
orthomation_core = importlib.reload(orthomation_core)
parse_jobxml = orthomation_core.parse_jobxml
transform_fingerprint = orthomation_core.transform_fingerprint

ROOT = Path(__file__).resolve().parent.parent
RUN_ID = os.environ.get("PALMERI_RUN_ID", "fixed_model_v1").strip()


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as stream:
        return json.load(stream)


def write_json_forbid(path, payload):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False)


def location_enabled(reference):
    return bool(reference.location_enabled) if hasattr(reference, "location_enabled") else bool(reference.enabled)


def crs_id(crs):
    if crs is None:
        return ""
    try:
        value = str(crs.authority)
    except Exception:
        value = str(crs)
    return value.upper().replace("EPSG::", "EPSG:")


def meta_value(owner, key, default=None):
    try:
        value = owner.meta[key]
    except (KeyError, TypeError):
        return default
    return default if value is None else value


def projection_count(marker):
    return sum(
        1 for _, projection in marker.projections.items()
        if projection is not None and bool(getattr(projection, "pinned", False))
    )


def derived_products(chunk):
    names = ("point_cloud", "elevation", "orthomosaic", "model", "tiled_model", "depth_maps")
    return [name for name in names if getattr(chunk, name, None) is not None]


def main():
    doc = Metashape.app.document
    chunk = doc.chunk
    if chunk is None or not doc.path:
        raise RuntimeError("Open and save a run-scoped branch first")
    global_cfg = load_json(ROOT / "config" / "global.json")
    if global_cfg.get("processing", {}).get("overwrite_policy") != "forbid":
        raise RuntimeError("overwrite_policy must remain 'forbid'")
    experiment = optimization_core.require_approved_experiment(global_cfg, RUN_ID)
    optimization_core.validate_metashape_version(Metashape.app.version, experiment["reviewed_metashape_version"])

    campaign_id = meta_value(chunk, "orthomation/campaign_id")
    campaign = load_json(ROOT / "campaigns" / f"{campaign_id}.json")
    jobxml_path = meta_value(chunk, "orthomation/jobxml_path")
    if not jobxml_path:
        raise RuntimeError("Branch does not record its JobXML path")
    job = parse_jobxml(jobxml_path, campaign["control_points"], campaign["jobxml_rules"])
    branch = meta_value(chunk, "orthomation/branch")
    issues = []

    if meta_value(chunk, "orthomation/run_id") != RUN_ID:
        issues.append(f"Chunk run_id={meta_value(chunk, 'orthomation/run_id')!r}; expected {RUN_ID!r}")
    if meta_value(chunk, "orthomation/stage") != "BRANCH_READY_FOR_FIXED_MODEL_OPTIMIZE":
        issues.append("Chunk stage is not BRANCH_READY_FOR_FIXED_MODEL_OPTIMIZE")
    if branch not in {"GCP_ONLY", "GCP_P1"}:
        issues.append(f"Unknown branch metadata: {branch!r}")
    if branch and not chunk.label.endswith(f"_{branch}_{RUN_ID}"):
        issues.append(f"Chunk label is not scoped to branch={branch!r}, run_id={RUN_ID!r}")
    if campaign_id != experiment["campaign_id"]:
        issues.append("Campaign does not match experiment")
    if meta_value(chunk, "orthomation/flight_date") != experiment["flight_date"]:
        issues.append("Flight is not the authorized pilot")
    if job["sha256"] != experiment["jobxml_sha256"]:
        issues.append("Current JobXML fingerprint differs from experiment")
    if meta_value(chunk, "orthomation/jobxml_sha256") != experiment["jobxml_sha256"]:
        issues.append("Chunk JobXML fingerprint differs from experiment")
    if meta_value(chunk, "orthomation/source_master_transform_sha256") != experiment["source_master_transform_sha256"]:
        issues.append("Source MASTER persisted fingerprint metadata differs from experiment")
    if meta_value(chunk, "orthomation/source_master_persisted_transform_sha256") != experiment["source_master_transform_sha256"]:
        issues.append("Explicit source MASTER persisted fingerprint metadata differs from experiment")
    if meta_value(chunk, "orthomation/source_master_live_transform_sha256") != experiment["source_master_live_transform_sha256"]:
        issues.append("Source MASTER live fingerprint metadata differs from experiment")
    if meta_value(chunk, "orthomation/source_master_common_12sig_transform_sha256") != experiment["source_master_common_12sig_transform_sha256"]:
        issues.append("Source MASTER common 12-significant-digit fingerprint metadata differs from experiment")
    if crs_id(chunk.crs) != crs_id(campaign["output_crs"]):
        issues.append("Chunk CRS mismatch")
    if crs_id(chunk.camera_crs) != crs_id(campaign["camera_reference_crs"]):
        issues.append("Camera CRS mismatch")
    if crs_id(chunk.marker_crs) != crs_id(campaign["marker_crs"]):
        issues.append("Marker CRS mismatch")

    current_fingerprint = transform_fingerprint(chunk)
    if current_fingerprint != experiment["source_master_live_transform_sha256"]:
        issues.append(
            f"Branch transform fingerprint={current_fingerprint}; "
            f"expected live source MASTER {experiment['source_master_live_transform_sha256']}"
        )
    if meta_value(chunk, "orthomation/preopt_transform_sha256") != current_fingerprint:
        issues.append("Branch transforms changed after run-scoped branch creation")

    expected_cameras = int(experiment["expected_camera_count"])
    if len(chunk.cameras) != expected_cameras:
        issues.append(f"Cameras={len(chunk.cameras)}; expected {expected_cameras}")
    expected_cam_on = expected_cameras if branch == "GCP_P1" else 0
    camera_location_on = 0
    camera_rotation_on = 0
    camera_accuracy_invalid = []
    maximum_sigma = float(global_cfg["camera_reference"]["maximum_position_sigma_m"])
    for camera in chunk.cameras:
        if camera.reference.location is None:
            issues.append(f"{camera.label}: source location missing")
        camera_location_on += int(location_enabled(camera.reference))
        camera_rotation_on += int(bool(getattr(camera.reference, "rotation_enabled", False)))
        accuracy = camera.reference.accuracy
        values = [] if accuracy is None else [float(accuracy[i]) for i in range(3)]
        if len(values) != 3 or any(value <= 0 or value > maximum_sigma for value in values):
            camera_accuracy_invalid.append(f"{camera.label}: {values}")
    if camera_location_on != expected_cam_on:
        issues.append(f"Camera XYZ ON={camera_location_on}; expected {expected_cam_on}")
    if camera_rotation_on != 0:
        issues.append(f"Camera rotation constraints ON={camera_rotation_on}; expected 0")
    if camera_accuracy_invalid:
        issues.append("Invalid camera accuracies: " + " | ".join(camera_accuracy_invalid[:10]))

    markers = {marker.label: marker for marker in chunk.markers}
    coordinate_tolerance = float(global_cfg["validation"]["coordinate_tolerance_m"])
    accuracy_tolerance = float(global_cfg["validation"]["accuracy_tolerance_m"])
    required_projections = int(experiment["required_marker_projections"])
    marker_rows = []
    for point in job["points"].values():
        marker = markers.get(point["label"])
        if marker is None:
            issues.append(f"Missing marker {point['label']}")
            continue
        expected_location = [point["easting"], point["northing"], point["h_ellipsoid"]]
        loaded_location = [] if marker.reference.location is None else [float(marker.reference.location[i]) for i in range(3)]
        expected_accuracy = [point["horizontal_precision"], point["horizontal_precision"], point["vertical_precision"]]
        loaded_accuracy = [] if marker.reference.accuracy is None else [float(marker.reference.accuracy[i]) for i in range(3)]
        enabled = location_enabled(marker.reference)
        should_be_enabled = point["role"] == "GCP"
        projections = projection_count(marker)
        if enabled != should_be_enabled:
            issues.append(f"{point['label']}: enabled={enabled}; expected {should_be_enabled}")
        if point["label"] in {"C2", "C5"} and enabled:
            issues.append(f"{point['label']}: check point must be disabled")
        if len(loaded_location) != 3 or any(abs(a - b) > coordinate_tolerance for a, b in zip(loaded_location, expected_location)):
            issues.append(f"{point['label']}: coordinate differs from JobXML")
        if len(loaded_accuracy) != 3 or any(abs(a - b) > accuracy_tolerance for a, b in zip(loaded_accuracy, expected_accuracy)):
            issues.append(f"{point['label']}: accuracy differs from JobXML")
        if projections != required_projections:
            issues.append(f"{point['label']}: projections={projections}; expected exactly {required_projections}")
        marker_rows.append({"label": point["label"], "role": point["role"], "enabled": enabled, "projections": projections})

    products = derived_products(chunk)
    if products:
        issues.append(f"Derived products exist: {products}")
    for sensor in chunk.sensors:
        photo_params = getattr(sensor, "photo_params", None)
        try:
            has_photo_params = photo_params is not None and len(photo_params) > 0
        except TypeError:
            has_photo_params = bool(photo_params)
        if has_photo_params:
            issues.append(f"{sensor.label}: per-photo calibration parameters are unsupported by this audit")
        calibration = sensor.calibration
        missing_parameters = [
            name for name in optimization_core.CALIBRATION_PARAMETERS
            if not hasattr(calibration, name)
        ]
        if missing_parameters:
            issues.append(f"{sensor.label}: calibration parameters unavailable: {missing_parameters}")
    report = {
        "adapter_version": "0.9.0",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "run_id": RUN_ID,
        "chunk": chunk.label,
        "branch": branch,
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
        "jobxml_sha256": job["sha256"],
        "source_master_persisted_transform_sha256": experiment["source_master_transform_sha256"],
        "source_master_live_transform_sha256": experiment["source_master_live_transform_sha256"],
        "source_master_common_12sig_transform_sha256": experiment["source_master_common_12sig_transform_sha256"],
        "preopt_transform_sha256": current_fingerprint,
        "optimization_parameters": global_cfg["optimization"],
        "camera_count": len(chunk.cameras),
        "camera_location_constraints_on": camera_location_on,
        "camera_rotation_constraints_on": camera_rotation_on,
        "derived_products": products,
        "markers": marker_rows,
        "next_action": "Run optimize_branch.py" if not issues else "Do not optimize; this run_id failed preflight",
    }
    output = Path(doc.path).resolve().parent / f"preopt_{RUN_ID}_{branch or 'UNKNOWN'}_v0_9_0.json"
    write_json_forbid(output, report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    Metashape.app.messageBox(
        f"Fixed-model preflight {RUN_ID}/{branch}: {report['status']}\n\n" +
        ("No blocking issues." if not issues else "\n".join(issues))
    )


if __name__ == "__main__":
    main()
