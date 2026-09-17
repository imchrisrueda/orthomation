"""Create non-destructive, run-scoped fixed-model branches from the MASTER."""

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
sha256_file = orthomation_core.sha256_file
transform_fingerprint = orthomation_core.transform_fingerprint
camera_transform_rows = orthomation_core.camera_transform_rows
persisted_active_chunk_transform_rows = orthomation_core.persisted_active_chunk_transform_rows
transform_representation_equivalence = orthomation_core.transform_representation_equivalence

ROOT = Path(__file__).resolve().parent.parent
RUN_ID = os.environ.get("PALMERI_RUN_ID", "fixed_model_v1").strip()


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as stream:
        return json.load(stream)


def write_json_forbid(path, payload):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False)


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


def projection_count(marker):
    return sum(
        1 for _, projection in marker.projections.items()
        if projection is not None and bool(getattr(projection, "pinned", False))
    )


def derived_products(chunk):
    names = ("point_cloud", "elevation", "orthomosaic", "model", "tiled_model", "depth_maps")
    return [name for name in names if getattr(chunk, name, None) is not None]


def validate_master(master, project_path, job, experiment):
    issues = []
    if meta_value(master, "orthomation/stage") not in {"MASTER_MARKING_VALIDATED", "MASTER_BRANCHED"}:
        issues.append(f"MASTER stage is not validated/branched: {meta_value(master, 'orthomation/stage')!r}")
    if meta_value(master, "orthomation/campaign_id") != experiment["campaign_id"]:
        issues.append("MASTER campaign does not match the experiment")
    if meta_value(master, "orthomation/flight_date") != experiment["flight_date"]:
        issues.append("MASTER flight does not match the authorized pilot")
    if meta_value(master, "orthomation/branch"):
        issues.append("Active chunk is a branch, not the MASTER")
    if not master.label.endswith("_MASTER"):
        issues.append(f"Active chunk label is not a MASTER: {master.label!r}")
    if meta_value(master, "orthomation/jobxml_sha256") != experiment["jobxml_sha256"]:
        issues.append("MASTER JobXML fingerprint differs from the approved experiment")
    if job["sha256"] != experiment["jobxml_sha256"]:
        issues.append("Current JobXML fingerprint differs from the approved experiment")
    persisted = persisted_active_chunk_transform_rows(project_path)
    if persisted["chunk_label"] != master.label:
        issues.append(
            f"Saved active chunk={persisted['chunk_label']!r}; live active chunk={master.label!r}"
        )
    transform_equivalence = transform_representation_equivalence(
        persisted["rows"], camera_transform_rows(master), experiment
    )
    issues.extend(transform_equivalence["issues"])
    if len(master.cameras) != int(experiment["expected_camera_count"]):
        issues.append(f"MASTER cameras={len(master.cameras)}; expected {experiment['expected_camera_count']}")

    expected = {point["label"]: point for point in job["points"].values()}
    markers = {marker.label: marker for marker in master.markers}
    required = int(experiment["required_marker_projections"])
    marker_rows = []
    for label, point in expected.items():
        marker = markers.get(label)
        if marker is None:
            issues.append(f"Missing marker {label}")
            continue
        count = projection_count(marker)
        enabled = location_enabled(marker.reference)
        if enabled:
            issues.append(f"{label}: reference must be OFF in MASTER")
        if count != required:
            issues.append(f"{label}: projections={count}; expected exactly {required}")
        marker_rows.append({"label": label, "role": point["role"], "enabled": enabled, "projections": count})

    for camera in master.cameras:
        if camera.reference.location is None:
            issues.append(f"{camera.label}: source XYZ missing")
        if location_enabled(camera.reference):
            issues.append(f"{camera.label}: location constraint is ON in MASTER")
        if bool(getattr(camera.reference, "rotation_enabled", False)):
            issues.append(f"{camera.label}: rotation constraint is ON in MASTER")
    products = derived_products(master)
    if products:
        issues.append(f"Derived products exist in MASTER: {products}")
    if issues:
        raise RuntimeError("MASTER is not eligible for the fixed-model experiment:\n- " + "\n- ".join(issues))
    return persisted, transform_equivalence, marker_rows


def configure_branch(chunk, job, experiment, branch):
    use_p1 = branch == "GCP_P1"
    by_label = {marker.label: marker for marker in chunk.markers}
    for point in job["points"].values():
        set_location(by_label[point["label"]].reference, point["role"] == "GCP")

    source_count = 0
    enabled_count = 0
    for camera in chunk.cameras:
        has_source = camera.reference.location is not None
        source_count += int(has_source)
        set_location(camera.reference, bool(use_p1 and has_source))
        set_rotation(camera.reference, False)
        enabled_count += int(location_enabled(camera.reference))

    expected_cameras = int(experiment["expected_camera_count"])
    expected_enabled = expected_cameras if use_p1 else 0
    if source_count != expected_cameras:
        raise RuntimeError(f"Source camera coordinates={source_count}; expected {expected_cameras}")
    if enabled_count != expected_enabled:
        raise RuntimeError(f"Enabled camera XYZ={enabled_count}; expected {expected_enabled}")

    chunk.meta["orthomation/stage"] = "BRANCH_READY_FOR_FIXED_MODEL_OPTIMIZE"
    chunk.meta["orthomation/branch"] = branch
    chunk.meta["orthomation/run_id"] = RUN_ID
    chunk.meta["orthomation/source_master_transform_sha256"] = experiment["source_master_transform_sha256"]
    chunk.meta["orthomation/source_master_persisted_transform_sha256"] = experiment["source_master_transform_sha256"]
    chunk.meta["orthomation/source_master_live_transform_sha256"] = experiment["source_master_live_transform_sha256"]
    chunk.meta["orthomation/source_master_common_12sig_transform_sha256"] = experiment["source_master_common_12sig_transform_sha256"]
    chunk.meta["orthomation/preopt_transform_sha256"] = transform_fingerprint(chunk)
    chunk.meta["orthomation/camera_location_constraints"] = "ON" if use_p1 else "OFF"
    chunk.meta["orthomation/camera_rotation_constraints"] = "OFF"
    return {"source_cameras": source_count, "enabled_camera_locations": enabled_count}


def legacy_artifacts(doc, project_dir, master_label, experiment):
    labels = {chunk.label for chunk in doc.chunks}
    setup_report = project_dir / "branch_setup_v0_9_0.json"
    if not setup_report.is_file():
        raise RuntimeError(f"Legacy branch setup report missing: {setup_report}")
    rows = []
    for branch in ("GCP_ONLY", "GCP_P1"):
        label = f"{master_label}_{branch}"
        preflight_report = project_dir / f"preopt_{branch}_v0_9_0.json"
        optimization_report = project_dir / f"optimization_{branch}_v0_9_0.json"
        if label not in labels:
            raise RuntimeError(f"Legacy branch missing: {label}")
        for report in (preflight_report, optimization_report):
            if not report.is_file():
                raise RuntimeError(f"Legacy report missing: {report}")
        payload = load_json(optimization_report)
        recorded_adaptive_fitting = payload.get("parameters", {}).get("adaptive_fitting")
        if recorded_adaptive_fitting is not True:
            raise RuntimeError(
                f"Legacy {branch} report does not prove adaptive_fitting=true: {recorded_adaptive_fitting!r}"
            )
        rows.append({
            "branch": branch,
            "chunk": label,
            "reports": {
                "preflight": {"path": str(preflight_report), "sha256": sha256_file(preflight_report)},
                "optimization": {"path": str(optimization_report), "sha256": sha256_file(optimization_report)},
            },
            "recorded_adaptive_fitting": recorded_adaptive_fitting,
            "optimization_status": experiment["legacy_branch_disposition"]["optimization_status"],
            "selection_status": experiment["legacy_branch_disposition"]["selection_status"],
            "geometry_modified": False,
        })
    return {
        "branch_setup": {"path": str(setup_report), "sha256": sha256_file(setup_report)},
        "branches": rows,
    }


def main():
    doc = Metashape.app.document
    master = doc.chunk
    if master is None or not doc.path:
        raise RuntimeError("Open and save the authorized MASTER first")

    global_cfg = load_json(ROOT / "config" / "global.json")
    if global_cfg.get("processing", {}).get("overwrite_policy") != "forbid":
        raise RuntimeError("overwrite_policy must remain 'forbid'")
    experiment = optimization_core.require_approved_experiment(global_cfg, RUN_ID)
    optimization_core.validate_metashape_version(Metashape.app.version, experiment["reviewed_metashape_version"])
    campaign_id = meta_value(master, "orthomation/campaign_id")
    campaign = load_json(ROOT / "campaigns" / f"{campaign_id}.json")
    jobxml_path = meta_value(master, "orthomation/jobxml_path")
    if not jobxml_path:
        raise RuntimeError("MASTER does not record its JobXML path")
    job = parse_jobxml(jobxml_path, campaign["control_points"], campaign["jobxml_rules"])
    persisted, transform_equivalence, marker_rows = validate_master(master, doc.path, job, experiment)

    project_dir = Path(doc.path).resolve().parent
    output = project_dir / f"branch_setup_{RUN_ID}_v0_9_0.json"
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite experiment report: {output}")
    branch_labels = {
        branch: f"{master.label}_{branch}_{RUN_ID}"
        for branch in ("GCP_ONLY", "GCP_P1")
    }
    existing = {chunk.label for chunk in doc.chunks}
    duplicates = sorted(set(branch_labels.values()) & existing)
    if duplicates:
        raise RuntimeError(f"Run-scoped branches already exist: {duplicates}")
    legacy = legacy_artifacts(doc, project_dir, master.label, experiment)

    created = []
    stats = {}
    try:
        for branch in ("GCP_ONLY", "GCP_P1"):
            chunk = master.copy()
            created.append(chunk)
            chunk.label = branch_labels[branch]
            stats[branch] = configure_branch(chunk, job, experiment, branch)
        doc.save()
    except Exception:
        if created:
            doc.remove(created)
        raise

    report = {
        "adapter_version": "0.9.0",
        "run_id": RUN_ID,
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "BRANCHES_READY_FOR_PREFLIGHT",
        "master": master.label,
        "source_master_persisted_transform_sha256": transform_equivalence["persisted_transform_sha256"],
        "source_master_live_transform_sha256": transform_equivalence["live_transform_sha256"],
        "source_master_common_12sig_transform_sha256": transform_equivalence["common_significant_digit_transform_sha256"],
        "source_master_transform_equivalence": transform_equivalence,
        "persisted_active_chunk": {
            "id": persisted["chunk_id"],
            "label": persisted["chunk_label"],
            "archive": persisted["chunk_archive"],
        },
        "jobxml_sha256": job["sha256"],
        "optimization_parameters": global_cfg["optimization"],
        "new_branches": {
            branch: {"chunk": branch_labels[branch], **stats[branch]}
            for branch in ("GCP_ONLY", "GCP_P1")
        },
        "markers": marker_rows,
        "legacy_results": legacy,
        "optimization_executed": False,
    }
    write_json_forbid(output, report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    Metashape.app.messageBox(
        f"Run {RUN_ID}: new branches created without modifying legacy branches. "
        "Run validate_before_optimize.py on each new branch."
    )


if __name__ == "__main__":
    main()
