"""Validate the manual marker gate on official MASTER projects."""

from pathlib import Path
import csv
import json
import os
import statistics
import traceback
import Metashape

from orthomation_core import parse_jobxml, validate_p1_xmp

ROOT = Path(__file__).resolve().parent.parent
CAMPAIGN_ID = os.environ.get("PALMERI_CAMPAIGN", "").strip()
MODE = os.environ.get("PALMERI_VALIDATE_MODE", "pilot").strip().lower()
FLIGHT_DATE = os.environ.get("PALMERI_FLIGHT_DATE", "").strip()
JOBXML_OVERRIDE = os.environ.get("PALMERI_JOBXML", "").strip()


def die(message):
    raise RuntimeError(message)


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as stream:
        return json.load(stream)


def resolve_root_relative(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def location_enabled(reference):
    if hasattr(reference, "location_enabled"):
        return bool(reference.location_enabled)
    return bool(reference.enabled)


def rotation_enabled(reference):
    return bool(getattr(reference, "rotation_enabled", False))


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


def crs_id(crs):
    if crs is None:
        return ""
    try:
        value = str(crs.authority)
    except Exception:
        value = str(crs)
    return value.upper().replace("EPSG::", "EPSG:")


def expected_control(campaign, flight):
    selected = JOBXML_OVERRIDE or flight.get("jobxml") or campaign["default_jobxml"]
    job = parse_jobxml(
        resolve_root_relative(selected),
        campaign["control_points"],
        campaign["jobxml_rules"],
    )
    points = {}
    for point in job["points"].values():
        points[point["label"]] = {
            "role": point["role"],
            "location": [point["easting"], point["northing"], point["h_ellipsoid"]],
            "accuracy": [point["horizontal_precision"], point["horizontal_precision"], point["vertical_precision"]],
        }
    return job, points


def validate_project(psx, global_cfg, campaign, flight):
    job, expected = expected_control(campaign, flight)
    doc = Metashape.Document()
    doc.open(str(psx))
    chunk = doc.chunk
    if chunk is None:
        die("No active chunk")

    issues = []
    manual_review = []
    if meta_value(chunk, "orthomation/jobxml_sha256") != job["sha256"]:
        issues.append("JobXML fingerprint differs from the one used to create the MASTER")
    if meta_value(chunk, "orthomation/flight_date") != flight["date"]:
        issues.append("MASTER flight metadata does not match campaign flight")
    if crs_id(chunk.crs) != crs_id(campaign["output_crs"]):
        issues.append(f"Chunk CRS={crs_id(chunk.crs)}")
    if crs_id(chunk.camera_crs) != crs_id(campaign["camera_reference_crs"]):
        issues.append(f"Camera CRS={crs_id(chunk.camera_crs)}")
    if crs_id(chunk.marker_crs) != crs_id(campaign["marker_crs"]):
        issues.append(f"Marker CRS={crs_id(chunk.marker_crs)}")

    cameras = list(chunk.cameras)
    photo_paths = []
    for camera in cameras:
        if camera.photo is None:
            issues.append(f"{camera.label}: no photo")
            continue
        path = Path(str(camera.photo.path))
        photo_paths.append(path)
        if not path.is_absolute() or not path.exists():
            issues.append(f"{camera.label}: photo path invalid: {path}")
        if camera.reference.location is None:
            issues.append(f"{camera.label}: source XYZ missing")
        accuracy = camera.reference.accuracy
        values = [] if accuracy is None else [float(accuracy[i]) for i in range(3)]
        maximum = float(global_cfg["camera_reference"]["maximum_position_sigma_m"])
        if len(values) != 3 or any(value <= 0 or value > maximum for value in values):
            issues.append(f"{camera.label}: invalid XMP accuracy {values}")
        if location_enabled(camera.reference):
            issues.append(f"{camera.label}: camera location constraint must be OFF in MASTER")
        if rotation_enabled(camera.reference):
            issues.append(f"{camera.label}: camera rotation constraint must be OFF")

    if photo_paths:
        ground_h = statistics.median(point["location"][2] for point in expected.values())
        try:
            validate_p1_xmp(photo_paths, global_cfg["camera_reference"], ground_h)
        except Exception as exc:
            issues.append(str(exc))

    by_label = {marker.label: marker for marker in chunk.markers}
    rows = []
    preferred = int(global_cfg["validation"]["minimum_projections_per_marker"])
    absolute_minimum = int(global_cfg["validation"]["manual_minimum_if_fewer_visible"])
    coordinate_tolerance = float(global_cfg["validation"]["coordinate_tolerance_m"])
    accuracy_tolerance = float(global_cfg["validation"]["accuracy_tolerance_m"])
    for label, wanted in expected.items():
        marker = by_label.get(label)
        if marker is None:
            issues.append(f"Missing marker {label}")
            continue
        location = marker.reference.location
        loaded = [] if location is None else [float(location[i]) for i in range(3)]
        accuracy = marker.reference.accuracy
        loaded_accuracy = [] if accuracy is None else [float(accuracy[i]) for i in range(3)]
        count = projection_count(marker)
        if len(loaded) != 3 or any(abs(a-b) > coordinate_tolerance for a,b in zip(loaded, wanted["location"])):
            issues.append(f"{label}: reference coordinate differs from JobXML ellipsoidal XYZ")
        if len(loaded_accuracy) != 3 or any(abs(a-b) > accuracy_tolerance for a,b in zip(loaded_accuracy, wanted["accuracy"])):
            issues.append(f"{label}: accuracy differs from JobXML")
        if location_enabled(marker.reference):
            issues.append(f"{label}: reference must remain OFF during marking")
        if count < absolute_minimum:
            issues.append(f"{label}: {count} projections; absolute minimum is {absolute_minimum}")
        elif count < preferred:
            manual_review.append(f"{label}: {count} projections; confirm that fewer than {preferred} suitable images exist")
        rows.append({"label": label, "role": wanted["role"], "projections": count})

    if chunk.point_cloud is not None or chunk.elevation is not None or chunk.orthomosaic is not None:
        issues.append("Derived products exist before optimization gate")

    if not issues:
        chunk.meta["orthomation/stage"] = "MASTER_MARKING_VALIDATED"
        chunk.meta["orthomation/manual_projection_review"] = " | ".join(manual_review)
        doc.save()

    return {
        "status": "PASS_WITH_MANUAL_CONFIRMATION" if not issues and manual_review else ("PASS" if not issues else "FAIL"),
        "issues": issues,
        "manual_review": manual_review,
        "cameras": len(cameras),
        "aligned": sum(camera.transform is not None for camera in cameras),
        "markers": rows,
        "project": str(psx),
        "jobxml_sha256": job["sha256"],
    }


def main():
    if not CAMPAIGN_ID:
        die("PALMERI_CAMPAIGN is required")
    global_cfg = load_json(ROOT / "config" / "global.json")
    campaign = load_json(ROOT / "campaigns" / f"{CAMPAIGN_ID}.json")
    base = Path(global_cfg["generated_root"]) / campaign["campaign_id"]
    project_root = base / "projects" / "metashape"
    flights = [flight for flight in campaign["flights"] if flight.get("enabled", True)]
    if MODE == "pilot":
        flights = [flight for flight in flights if flight["date"] == campaign["pilot_date"]]
    elif MODE == "remaining":
        flights = [flight for flight in flights if flight["date"] != campaign["pilot_date"]]
    elif MODE == "single":
        if not FLIGHT_DATE:
            die("PALMERI_FLIGHT_DATE is required in single mode")
        flights = [flight for flight in flights if flight["date"] == FLIGHT_DATE]
    elif MODE != "all":
        die("PALMERI_VALIDATE_MODE must be pilot, remaining, all or single")

    results = []
    for flight in flights:
        stem = f"{flight['date']}_RGB_P1_{campaign['alignment_preset']}_MASTER.psx"
        psx = project_root / flight["date"] / "RGB_P1" / stem
        try:
            if not psx.exists():
                raise RuntimeError(f"MASTER not found: {psx}")
            result = validate_project(psx, global_cfg, campaign, flight)
        except Exception as exc:
            traceback.print_exc()
            result = {"status": "FAIL", "issues": [str(exc)], "manual_review": [], "project": str(psx), "markers": []}
        result.update({"campaign_id": campaign["campaign_id"], "date": flight["date"]})
        results.append(result)
        print(f"{campaign['campaign_id']} / {flight['date']}: {result['status']}")
        for issue in result.get("issues", []):
            print(" -", issue)
        for warning in result.get("manual_review", []):
            print(" ?", warning)

    output = base / "validation_marking.json"
    with output.open("w", encoding="utf-8") as stream:
        json.dump(results, stream, indent=2, ensure_ascii=False)
    print("Report:", output)


if __name__ == "__main__":
    main()
