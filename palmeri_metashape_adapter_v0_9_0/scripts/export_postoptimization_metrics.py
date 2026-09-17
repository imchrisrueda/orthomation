"""Export objective fixed-model metrics without modifying the Metashape document."""

from pathlib import Path
import datetime
import importlib
import json
import math
import os
import platform
import Metashape

import optimization_core
import orthomation_core

optimization_core = importlib.reload(optimization_core)
orthomation_core = importlib.reload(orthomation_core)
parse_jobxml = orthomation_core.parse_jobxml
sha256_file = orthomation_core.sha256_file
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


def marker_coordinate_solution(chunk, marker):
    transform = chunk.transform.matrix
    source_crs = chunk.crs
    target_crs = chunk.marker_crs or source_crs
    if source_crs is None or target_crs is None:
        raise RuntimeError("Chunk and marker CRS are required for marker residuals")
    if str(source_crs) != str(target_crs):
        transform = Metashape.CoordinateSystem.datumTransform(source_crs, target_crs) * transform
    geocentric = target_crs.geoccs or Metashape.CoordinateSystem("LOCAL")
    estimated_geocentric = transform.mulp(marker.position)
    estimated = Metashape.CoordinateSystem.transform(estimated_geocentric, geocentric, target_crs)
    reference = marker.reference.location
    reference_geocentric = Metashape.CoordinateSystem.transform(reference, target_crs, geocentric)
    delta_geocentric = estimated_geocentric - reference_geocentric
    local_residual = target_crs.localframe(estimated_geocentric).rotation() * delta_geocentric
    projected_delta = estimated - reference
    return estimated, local_residual, projected_delta


def vector2_components(vector):
    return float(vector[0]), float(vector[1])


def marker_reprojection_rows(marker):
    rows = []
    if marker.position is None:
        return rows
    for camera, projection in marker.projections.items():
        if projection is None or camera.transform is None:
            continue
        if not bool(getattr(projection, "valid", True)):
            continue
        if not bool(getattr(projection, "pinned", False)):
            continue
        error = camera.error(marker.position, projection.coord)
        dx, dy = vector2_components(error)
        rows.append({
            "camera": camera.label,
            "dx_px": dx,
            "dy_px": dy,
            "error_px": math.hypot(dx, dy),
            "pinned": True,
        })
    return rows


def marker_metrics(chunk, job):
    expected = {point["label"]: point for point in job["points"].values()}
    markers = {marker.label: marker for marker in chunk.markers}
    rows = []
    all_marker_errors = []
    issues = []
    for label in sorted(expected):
        point = expected[label]
        marker = markers.get(label)
        if marker is None or marker.position is None or marker.reference.location is None:
            issues.append(f"{label}: marker position/reference unavailable")
            continue
        estimated, local_residual, projected_delta = marker_coordinate_solution(chunk, marker)
        reference = marker.reference.location
        dx = float(local_residual[0])
        dy = float(local_residual[1])
        dz = float(local_residual[2])
        reprojections = marker_reprojection_rows(marker)
        reprojection_values = [row["error_px"] for row in reprojections]
        all_marker_errors.extend(reprojection_values)
        rows.append({
            "label": label,
            "role": point["role"],
            "reference_enabled": location_enabled(marker.reference),
            "reference_xyz_m": [float(reference[i]) for i in range(3)],
            "estimated_xyz_m": [float(estimated[i]) for i in range(3)],
            "projected_coordinate_delta_m": {
                "easting": float(projected_delta[0]),
                "northing": float(projected_delta[1]),
                "height": float(projected_delta[2]),
            },
            "residual_m": {
                "x": dx,
                "y": dy,
                "z": dz,
                "xy": math.hypot(dx, dy),
                "3d": math.sqrt(dx * dx + dy * dy + dz * dz),
            },
            "projection_count": len(reprojections),
            "reprojection": {
                "summary": optimization_core.reprojection_statistics(reprojection_values),
                "individual": reprojections,
            },
        })

    by_role = {}
    reprojection_by_role = {}
    for role in ("GCP", "CHECK_POINT"):
        role_rows = [row["residual_m"] for row in rows if row["role"] == role]
        by_role[role] = optimization_core.residual_statistics(role_rows)
        role_reprojection = [
            projection["error_px"]
            for row in rows if row["role"] == role
            for projection in row["reprojection"]["individual"]
        ]
        reprojection_by_role[role] = optimization_core.reprojection_statistics(role_reprojection)
    checkpoints = {row["label"]: row for row in rows if row["label"] in {"C2", "C5"}}
    if set(checkpoints) != {"C2", "C5"}:
        issues.append(f"Individual check-point metrics incomplete: {sorted(checkpoints)}")
    return {
        "coordinate_convention": "estimated minus reference, transformed to the local Cartesian frame at the estimated marker position following Agisoft save_estimated_reference.py; x/y/z are local-frame components in metres",
        "projected_coordinate_delta_convention": "estimated minus reference directly in marker CRS (EPSG:25830 easting/northing and ellipsoidal height), exported separately and not used for RMSE",
        "individual": rows,
        "summary_by_role": by_role,
        "check_points": checkpoints,
        "marker_reprojection_all": optimization_core.reprojection_statistics(all_marker_errors),
        "marker_reprojection_by_role": reprojection_by_role,
    }, issues


def tie_point_metrics(chunk):
    tie_points = chunk.tie_points
    if tie_points is None:
        raise RuntimeError("Tie points are unavailable")
    valid_points = {int(point.track_id): point for point in tie_points.points if bool(point.valid)}
    errors = []
    per_camera = []
    valid_track_ids_with_projections = set()
    aligned_cameras = 0
    for camera in chunk.cameras:
        if camera.transform is None:
            continue
        aligned_cameras += 1
        camera_errors = []
        for projection in tie_points.projections[camera]:
            track_id = int(projection.track_id)
            point = valid_points.get(track_id)
            if point is None:
                continue
            error = camera.error(point.coord, projection.coord)
            dx, dy = vector2_components(error)
            magnitude = math.hypot(dx, dy)
            camera_errors.append(magnitude)
            errors.append(magnitude)
            valid_track_ids_with_projections.add(track_id)
        per_camera.append({
            "camera": camera.label,
            "valid_projection_count": len(camera_errors),
            "reprojection": optimization_core.reprojection_statistics(camera_errors),
        })
    tracks = getattr(tie_points, "tracks", None)
    return {
        "valid_tie_point_count": len(valid_points),
        "valid_track_count_with_projection": len(valid_track_ids_with_projections),
        "raw_track_count": None if tracks is None else len(tracks),
        "valid_projection_count": len(errors),
        "aligned_camera_count": aligned_cameras,
        "reprojection": optimization_core.reprojection_statistics(errors),
        "per_camera": per_camera,
    }


def main():
    doc = Metashape.app.document
    chunk = doc.chunk
    if chunk is None or not doc.path:
        raise RuntimeError("Open and save an OPTIMIZED_FIXED_MODEL branch first")
    config = load_json(ROOT / "config" / "global.json")
    if config.get("processing", {}).get("overwrite_policy") != "forbid":
        raise RuntimeError("overwrite_policy must remain 'forbid'")
    experiment = optimization_core.require_approved_experiment(config, RUN_ID)
    optimization_core.validate_metashape_version(Metashape.app.version, experiment["reviewed_metashape_version"])
    branch = meta_value(chunk, "orthomation/branch")
    if branch not in {"GCP_ONLY", "GCP_P1"}:
        raise RuntimeError("Active chunk is not a controlled branch")
    if meta_value(chunk, "orthomation/run_id") != RUN_ID:
        raise RuntimeError("Active chunk run_id mismatch")
    if meta_value(chunk, "orthomation/stage") != "OPTIMIZED_FIXED_MODEL":
        raise RuntimeError("Branch status is not OPTIMIZED_FIXED_MODEL")

    project_dir = Path(doc.path).resolve().parent
    optimization_path = project_dir / f"optimization_{RUN_ID}_{branch}_v0_9_0.json"
    preflight_path = project_dir / f"preopt_{RUN_ID}_{branch}_v0_9_0.json"
    output = project_dir / f"metrics_{RUN_ID}_{branch}_v0_9_0.json"
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite metrics report: {output}")
    if not optimization_path.is_file() or not preflight_path.is_file():
        raise RuntimeError("Run-scoped optimization/preflight report missing")
    optimization = load_json(optimization_path)
    preflight = load_json(preflight_path)
    issues = []
    if optimization.get("status") != "OPTIMIZED_FIXED_MODEL":
        issues.append("Optimization report is not OPTIMIZED_FIXED_MODEL")
    if optimization.get("run_id") != RUN_ID or optimization.get("branch") != branch:
        issues.append("Optimization report run_id/branch mismatch")
    current_fingerprint = transform_fingerprint(chunk)
    if current_fingerprint != optimization.get("transform_sha256_after"):
        issues.append("Current transforms differ from the optimization report")
    if optimization.get("requested_parameters") != config["optimization"]:
        issues.append("Current optimization configuration differs from executed report")

    campaign = load_json(ROOT / "campaigns" / f"{experiment['campaign_id']}.json")
    job = parse_jobxml(
        meta_value(chunk, "orthomation/jobxml_path"),
        campaign["control_points"],
        campaign["jobxml_rules"],
    )
    if job["sha256"] != experiment["jobxml_sha256"]:
        issues.append("JobXML fingerprint mismatch")
    markers, marker_issues = marker_metrics(chunk, job)
    issues.extend(marker_issues)
    tie_points = tie_point_metrics(chunk)
    current_calibration = calibration_snapshot(chunk)
    if current_calibration != optimization.get("calibration_after"):
        issues.append("Current calibration differs from optimization report")

    report = {
        "adapter_version": "0.9.0",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "METRICS_EXPORTED" if not issues else "FAIL",
        "issues": issues,
        "selection_performed": False,
        "run_id": RUN_ID,
        "branch": branch,
        "chunk": chunk.label,
        "project": str(Path(doc.path).resolve()),
        "metashape_version": str(Metashape.app.version),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "campaign_id": experiment["campaign_id"],
        "flight_date": experiment["flight_date"],
        "jobxml_sha256": job["sha256"],
        "source_master_persisted_transform_sha256": experiment["source_master_transform_sha256"],
        "source_master_live_transform_sha256": experiment["source_master_live_transform_sha256"],
        "source_master_common_12sig_transform_sha256": experiment["source_master_common_12sig_transform_sha256"],
        "postoptimization_transform_sha256": current_fingerprint,
        "preflight_report": {"path": str(preflight_path), "sha256": sha256_file(preflight_path)},
        "optimization_report": {"path": str(optimization_path), "sha256": sha256_file(optimization_path)},
        "configuration": {"path": str(ROOT / "config" / "global.json"), "sha256": sha256_file(ROOT / "config" / "global.json")},
        "optimization_parameters": optimization.get("requested_parameters"),
        "task_recorded_parameters": optimization.get("task_recorded_parameters"),
        "effective_parameter_set": optimization.get("effective_parameter_set"),
        "additional_corrections": optimization.get("additional_corrections"),
        "counts": {
            "cameras": len(chunk.cameras),
            "aligned_cameras": sum(camera.transform is not None for camera in chunk.cameras),
            "markers": len(markers["individual"]),
            "marker_projections": sum(row["projection_count"] for row in markers["individual"]),
            "valid_tie_points": tie_points["valid_tie_point_count"],
            "valid_tie_point_projections": tie_points["valid_projection_count"],
        },
        "markers": markers,
        "tie_points": tie_points,
        "calibration_before": optimization.get("calibration_before"),
        "calibration_after": optimization.get("calibration_after"),
        "calibration_variation": optimization.get("calibration_comparison"),
        "next_action": "Independent geomatic review; this exporter does not select a branch.",
    }
    write_json_forbid(output, report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    Metashape.app.messageBox(
        f"Metrics export {RUN_ID}/{branch}: {report['status']}. No branch was selected."
    )


if __name__ == "__main__":
    main()
