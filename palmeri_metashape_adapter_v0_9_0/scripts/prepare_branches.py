"""Create controlled GCP_ONLY and GCP_P1 branches after manual marker QA."""

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


def set_location(reference, enabled):
    if hasattr(reference, "location_enabled"):
        reference.location_enabled = bool(enabled)
    else:
        reference.enabled = bool(enabled)


def set_rotation(reference, enabled):
    if hasattr(reference, "rotation_enabled"):
        reference.rotation_enabled = bool(enabled)


def location_enabled(reference):
    return bool(reference.location_enabled) if hasattr(reference, "location_enabled") else bool(reference.enabled)


def meta_value(owner, key, default=None):
    try:
        value = owner.meta[key]
    except (KeyError, TypeError):
        return default
    return default if value is None else value


def validate_master(master, campaign, job, minimum_projections):
    issues = []
    if meta_value(master, "orthomation/stage") != "MASTER_MARKING_VALIDATED":
        issues.append("Run validate_marking.py successfully before creating branches")
    if meta_value(master, "orthomation/jobxml_sha256") != job["sha256"]:
        issues.append("MASTER JobXML fingerprint mismatch")
    expected = {point["label"]: point for point in job["points"].values()}
    markers = {marker.label: marker for marker in master.markers}
    for label, point in expected.items():
        marker = markers.get(label)
        if marker is None:
            issues.append(f"Missing marker {label}")
            continue
        if location_enabled(marker.reference):
            issues.append(f"{label}: reference must be OFF in MASTER")
        count = sum(
            1 for _, projection in marker.projections.items()
            if projection is not None and bool(getattr(projection, "pinned", False))
        )
        if count < minimum_projections:
            issues.append(f"{label}: only {count} projections")
    for camera in master.cameras:
        if location_enabled(camera.reference):
            issues.append(f"{camera.label}: location constraint is ON in MASTER")
        if bool(getattr(camera.reference, "rotation_enabled", False)):
            issues.append(f"{camera.label}: rotation constraint is ON in MASTER")
    if master.point_cloud is not None or master.elevation is not None or master.orthomosaic is not None:
        issues.append("Derived products exist before optimization")
    if issues:
        raise RuntimeError("MASTER is not branchable:\n- " + "\n- ".join(issues))


def configure_branch(chunk, job, use_p1, preopt_fingerprint):
    by_label = {marker.label: marker for marker in chunk.markers}
    for point in job["points"].values():
        marker = by_label[point["label"]]
        set_location(marker.reference, point["role"] == "GCP")

    source_count = 0
    enabled_count = 0
    for camera in chunk.cameras:
        has_source = camera.reference.location is not None
        if has_source:
            source_count += 1
        set_location(camera.reference, bool(use_p1 and has_source))
        set_rotation(camera.reference, False)
        if location_enabled(camera.reference):
            enabled_count += 1
    if source_count != len(chunk.cameras):
        raise RuntimeError(f"Only {source_count}/{len(chunk.cameras)} cameras have source locations")
    if use_p1 and enabled_count != len(chunk.cameras):
        raise RuntimeError(f"Only {enabled_count}/{len(chunk.cameras)} camera constraints were enabled")
    chunk.meta["orthomation/stage"] = "BRANCH_READY_FOR_OPTIMIZE"
    chunk.meta["orthomation/branch"] = "GCP_P1" if use_p1 else "GCP_ONLY"
    chunk.meta["orthomation/preopt_transform_sha256"] = preopt_fingerprint
    chunk.meta["orthomation/camera_location_constraints"] = "ON" if use_p1 else "OFF"
    chunk.meta["orthomation/camera_rotation_constraints"] = "OFF"
    return {"source_cameras": source_count, "enabled_camera_locations": enabled_count}


def main():
    doc = Metashape.app.document
    master = doc.chunk
    if master is None or not doc.path:
        raise RuntimeError("Open and save the validated MASTER first")
    campaign_id = meta_value(master, "orthomation/campaign_id")
    if not campaign_id:
        raise RuntimeError("Active chunk has no orthomation campaign metadata")
    campaign = load_json(ROOT / "campaigns" / f"{campaign_id}.json")
    global_cfg = load_json(ROOT / "config" / "global.json")
    jobxml_path = meta_value(master, "orthomation/jobxml_path")
    if not jobxml_path:
        raise RuntimeError("MASTER does not record its JobXML path")
    job = parse_jobxml(jobxml_path, campaign["control_points"], campaign["jobxml_rules"])

    gcp_only_label = master.label + "_GCP_ONLY"
    gcp_p1_label = master.label + "_GCP_P1"
    existing = {chunk.label for chunk in doc.chunks}
    duplicates = sorted({gcp_only_label, gcp_p1_label} & existing)
    if duplicates:
        raise RuntimeError(f"Branches already exist: {duplicates}. This operation is intentionally not repeatable.")

    absolute_minimum = int(global_cfg["validation"]["manual_minimum_if_fewer_visible"])
    validate_master(master, campaign, job, absolute_minimum)
    fingerprint = transform_fingerprint(master)

    gcp_only = master.copy()
    gcp_only.label = gcp_only_label
    gcp_p1 = master.copy()
    gcp_p1.label = gcp_p1_label
    try:
        only_stats = configure_branch(gcp_only, job, False, fingerprint)
        p1_stats = configure_branch(gcp_p1, job, True, fingerprint)
        master.meta["orthomation/stage"] = "MASTER_BRANCHED"
        doc.save()
    except Exception:
        try:
            doc.remove([gcp_only, gcp_p1])
        finally:
            raise

    report = {
        "adapter_version": "0.9.0",
        "timestamp": datetime.datetime.now().isoformat(),
        "master": master.label,
        "jobxml_sha256": job["sha256"],
        "preopt_transform_sha256": fingerprint,
        "GCP_ONLY": only_stats,
        "GCP_P1": p1_stats,
        "gcp": sorted(point["label"] for point in job["points"].values() if point["role"] == "GCP"),
        "check_points": sorted(point["label"] for point in job["points"].values() if point["role"] == "CHECK_POINT"),
        "optimization_executed": False,
    }
    output = Path(doc.path).resolve().parent / "branch_setup_v0_9_0.json"
    with output.open("w", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    Metashape.app.messageBox("Branches created and saved. Run validate_before_optimize.py on each branch before optimization.")


if __name__ == "__main__":
    main()
