"""Read-only pre-optimization validation for a controlled branch."""

from pathlib import Path
import datetime
import importlib
import json
import Metashape

import orthomation_core

orthomation_core = importlib.reload(orthomation_core)
parse_jobxml = orthomation_core.parse_jobxml
transform_fingerprint = orthomation_core.transform_fingerprint

ROOT = Path(__file__).resolve().parent.parent


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as stream:
        return json.load(stream)


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


def main():
    doc = Metashape.app.document
    chunk = doc.chunk
    if chunk is None or not doc.path:
        raise RuntimeError("Open and save a branch first")
    campaign_id = meta_value(chunk, "orthomation/campaign_id")
    campaign = load_json(ROOT / "campaigns" / f"{campaign_id}.json")
    global_cfg = load_json(ROOT / "config" / "global.json")
    job = parse_jobxml(
        meta_value(chunk, "orthomation/jobxml_path"),
        campaign["control_points"],
        campaign["jobxml_rules"],
    )
    branch = meta_value(chunk, "orthomation/branch")
    issues = []
    if meta_value(chunk, "orthomation/stage") != "BRANCH_READY_FOR_OPTIMIZE":
        issues.append("Chunk stage is not BRANCH_READY_FOR_OPTIMIZE")
    if branch not in {"GCP_ONLY", "GCP_P1"}:
        issues.append(f"Unknown branch metadata: {branch!r}")
    if meta_value(chunk, "orthomation/jobxml_sha256") != job["sha256"]:
        issues.append("JobXML fingerprint mismatch")
    if crs_id(chunk.crs) != crs_id(campaign["output_crs"]):
        issues.append("Chunk CRS mismatch")
    if crs_id(chunk.camera_crs) != crs_id(campaign["camera_reference_crs"]):
        issues.append("Camera CRS mismatch")
    if crs_id(chunk.marker_crs) != crs_id(campaign["marker_crs"]):
        issues.append("Marker CRS mismatch")

    stored_fingerprint = meta_value(chunk, "orthomation/preopt_transform_sha256")
    current_fingerprint = transform_fingerprint(chunk)
    if stored_fingerprint != current_fingerprint:
        issues.append("Camera transforms changed after branch creation; optimization/update may already have occurred")

    expected_cam_on = len(chunk.cameras) if branch == "GCP_P1" else 0
    camera_location_on = 0
    camera_rotation_on = 0
    camera_accuracy_invalid = []
    maximum_sigma = float(global_cfg["camera_reference"]["maximum_position_sigma_m"])
    for camera in chunk.cameras:
        if camera.reference.location is None:
            issues.append(f"{camera.label}: source location missing")
        if location_enabled(camera.reference):
            camera_location_on += 1
        if bool(getattr(camera.reference, "rotation_enabled", False)):
            camera_rotation_on += 1
        accuracy = camera.reference.accuracy
        values = [] if accuracy is None else [float(accuracy[i]) for i in range(3)]
        if len(values) != 3 or any(value <= 0 or value > maximum_sigma for value in values):
            camera_accuracy_invalid.append(f"{camera.label}: {values}")
    if camera_location_on != expected_cam_on:
        issues.append(f"Camera XYZ ON={camera_location_on}; expected {expected_cam_on}")
    if camera_rotation_on:
        issues.append(f"Camera rotation constraints ON={camera_rotation_on}; expected 0")
    if camera_accuracy_invalid:
        issues.append("Invalid camera accuracies: " + " | ".join(camera_accuracy_invalid[:10]))

    markers = {marker.label: marker for marker in chunk.markers}
    minimum = int(global_cfg["validation"]["manual_minimum_if_fewer_visible"])
    coordinate_tolerance = float(global_cfg["validation"]["coordinate_tolerance_m"])
    accuracy_tolerance = float(global_cfg["validation"]["accuracy_tolerance_m"])
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
        projections = sum(
            1 for _, projection in marker.projections.items()
            if projection is not None and bool(getattr(projection, "pinned", False))
        )
        if enabled != should_be_enabled:
            issues.append(f"{point['label']}: enabled={enabled}; expected {should_be_enabled}")
        if len(loaded_location) != 3 or any(abs(a-b) > coordinate_tolerance for a,b in zip(loaded_location, expected_location)):
            issues.append(f"{point['label']}: coordinate differs from JobXML")
        if len(loaded_accuracy) != 3 or any(abs(a-b) > accuracy_tolerance for a,b in zip(loaded_accuracy, expected_accuracy)):
            issues.append(f"{point['label']}: accuracy differs from JobXML")
        if projections < minimum:
            issues.append(f"{point['label']}: {projections} projections; minimum {minimum}")
        marker_rows.append({"label": point["label"], "role": point["role"], "enabled": enabled, "projections": projections})

    if chunk.point_cloud is not None or chunk.elevation is not None or chunk.orthomosaic is not None:
        issues.append("Derived products exist before optimization")

    report = {
        "adapter_version": "0.9.0",
        "timestamp": datetime.datetime.now().isoformat(),
        "chunk": chunk.label,
        "branch": branch,
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
        "jobxml_sha256": job["sha256"],
        "preopt_transform_sha256": current_fingerprint,
        "camera_location_constraints_on": camera_location_on,
        "camera_rotation_constraints_on": camera_rotation_on,
        "markers": marker_rows,
        "next_action": "Optimize Cameras with the locked common parameter set" if not issues else "Correct all issues before optimization",
    }
    output = Path(doc.path).resolve().parent / f"preopt_{branch or 'UNKNOWN'}_v0_9_0.json"
    with output.open("w", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    Metashape.app.messageBox("Pre-optimize validation: " + report["status"] + "\n\n" + ("No blocking issues." if not issues else "\n".join(issues)))


if __name__ == "__main__":
    main()
