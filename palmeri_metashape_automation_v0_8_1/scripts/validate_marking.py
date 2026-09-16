# -*- coding: utf-8 -*-
"""
Palmeri marking validator v0.7.
Validates the official *_MASTER.psx only.
"""

from pathlib import Path
import csv, json, os, traceback
import Metashape

ROOT = Path(__file__).resolve().parent.parent
GLOBAL_PATH = ROOT / "config" / "global.json"
CAMPAIGN_ID = os.environ.get("PALMERI_CAMPAIGN", "").strip()
MODE = os.environ.get("PALMERI_VALIDATE_MODE", "pilot").strip().lower()

def die(msg):
    raise RuntimeError(msg)

def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def resolve_root_relative(path_str):
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p

def load_configs():
    if not CAMPAIGN_ID:
        die("Falta PALMERI_CAMPAIGN.")
    return (
        load_json(GLOBAL_PATH),
        load_json(ROOT / "campaigns" / f"{CAMPAIGN_ID}.json")
    )

def resolve_gcp_file(campaign, flight):
    return resolve_root_relative(
        flight.get("gcp_file") or campaign["default_gcp_file"]
    )

def load_roles(gcp_path):
    roles = {}
    with gcp_path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            label = row["label"].strip()
            if label:
                roles[label] = row["role"].strip().upper()
    if not roles:
        die(f"{gcp_path} no contiene puntos.")
    return roles

def projection_count(marker):
    try:
        return sum(1 for _, proj in marker.projections.items() if proj is not None)
    except Exception:
        return 0

def crs_text(crs):
    if crs is None:
        return ""
    try:
        return str(crs.authority)
    except Exception:
        return str(crs)

def normalize_crs_id(value):
    """
    Normalize Metashape/API CRS identifiers for robust comparison.
    Examples:
      EPSG::25830 -> EPSG:25830
      EPSG:25830  -> EPSG:25830
    """
    if value is None:
        return ""
    s = str(value).strip().upper()
    s = s.replace("EPSG::", "EPSG:")
    return s


def validate_photo_paths(chunk):
    issues = []
    absolute = 0
    existing = 0

    for camera in chunk.cameras:
        if camera.photo is None:
            issues.append(f"{camera.label}: camera.photo is None")
            continue

        photo_path = Path(str(camera.photo.path))
        if photo_path.is_absolute():
            absolute += 1
        else:
            issues.append(f"{camera.label}: relative photo path: {camera.photo.path}")

        if photo_path.exists():
            existing += 1
        else:
            issues.append(f"{camera.label}: file not found: {camera.photo.path}")

    return issues, absolute, existing

def validate_project(psx, global_cfg, campaign, roles):
    doc = Metashape.Document()
    doc.open(str(psx))
    chunk = doc.chunk
    if chunk is None:
        die("No hay chunk activo.")

    issues = []

    photo_issues, photo_absolute, photo_existing = validate_photo_paths(chunk)
    issues.extend(photo_issues)

    total = len(chunk.cameras)
    aligned = sum(c.transform is not None for c in chunk.cameras)
    cam_source = sum(c.reference.location is not None for c in chunk.cameras)
    cam_enabled = sum(bool(c.reference.enabled) for c in chunk.cameras)

    if aligned != total:
        issues.append(f"Alineadas {aligned}/{total}")
    if cam_source != total:
        issues.append(f"Camera Source GPS {cam_source}/{total}")
    if cam_enabled:
        issues.append(f"{cam_enabled} cámaras reference ON")

    exp_output = normalize_crs_id(campaign["output_crs"])
    exp_camera = normalize_crs_id(campaign["camera_reference_crs"])
    exp_marker = normalize_crs_id(campaign["marker_crs"])

    got_output = normalize_crs_id(crs_text(chunk.crs))
    got_camera = normalize_crs_id(crs_text(chunk.camera_crs))
    got_marker = normalize_crs_id(crs_text(chunk.marker_crs))

    if exp_output != got_output:
        issues.append(
            f"Chunk CRS={crs_text(chunk.crs)}; esperado={campaign['output_crs']}"
        )
    if exp_camera != got_camera:
        issues.append(
            f"Camera CRS={crs_text(chunk.camera_crs)}; "
            f"esperado={campaign['camera_reference_crs']}"
        )
    if exp_marker != got_marker:
        issues.append(
            f"Marker CRS={crs_text(chunk.marker_crs)}; esperado={campaign['marker_crs']}"
        )

    expected_acc = [float(x) for x in campaign["marker_accuracy_m"]]
    got_acc = list(chunk.marker_location_accuracy)
    if any(abs(a-b) > 1e-9 for a,b in zip(expected_acc, got_acc)):
        issues.append(f"Marker accuracy={got_acc}; esperado={expected_acc}")

    expected_proj = float(campaign["marker_projection_accuracy_px"])
    got_proj = float(chunk.marker_projection_accuracy)
    if abs(expected_proj - got_proj) > 1e-9:
        issues.append(f"Marker projection accuracy={got_proj}; esperado={expected_proj}")

    min_proj = int(global_cfg["validation"]["minimum_projections_per_marker"])
    by_label = {m.label: m for m in chunk.markers}
    marker_rows = []

    for label, role in roles.items():
        marker = by_label.get(label)
        if marker is None:
            issues.append(f"Falta {label}")
            marker_rows.append((label, role, 0, False, False))
            continue

        nproj = projection_count(marker)
        has_source = marker.reference.location is not None
        enabled = bool(marker.reference.enabled)

        if not has_source:
            issues.append(f"{label}: Source XYZ vacío")
        if enabled:
            issues.append(f"{label}: reference ON")
        if nproj < min_proj:
            issues.append(f"{label}: {nproj} projections < {min_proj}")

        marker_rows.append((label, role, nproj, has_source, enabled))

    if chunk.point_cloud is not None:
        issues.append("Existe Point Cloud")
    if chunk.elevation is not None:
        issues.append("Existe DEM/DSM")
    if chunk.orthomosaic is not None:
        issues.append("Existe Orthomosaic")

    return {
        "status": "PASS" if not issues else "FAIL",
        "cameras": total,
        "aligned": aligned,
        "camera_source_xyz": cam_source,
        "camera_reference_enabled": cam_enabled,
        "photo_paths_absolute": photo_absolute,
        "photo_files_existing": photo_existing,
        "issues": " | ".join(issues),
        "markers": marker_rows,
    }

def main():
    global_cfg, campaign = load_configs()
    base = Path(global_cfg["generated_root"]) / campaign["campaign_id"]
    project_root = base / "projects" / "metashape"

    flights = [f for f in campaign["flights"] if f.get("enabled", True)]
    if MODE == "pilot":
        flights = [f for f in flights if f["date"] == campaign["pilot_date"]]
    elif MODE == "remaining":
        flights = [f for f in flights if f["date"] != campaign["pilot_date"]]
    elif MODE != "all":
        die("PALMERI_VALIDATE_MODE debe ser pilot, remaining o all.")

    summary = []
    details = []

    for flight in flights:
        date = flight["date"]
        roles = load_roles(resolve_gcp_file(campaign, flight))
        psx = (
            project_root / date / "RGB_P1"
            / f"{date}_RGB_P1_{campaign['alignment_preset']}_MASTER.psx"
        )

        if not psx.exists():
            summary.append({
                "campaign_id": campaign["campaign_id"],
                "date": date,
                "status": "FAIL",
                "issues": "MASTER_NOT_FOUND"
            })
            continue

        try:
            r = validate_project(psx, global_cfg, campaign, roles)
            print(f"\n{campaign['campaign_id']} / {date}: {r['status']}")
            if r["issues"]:
                print("  ", r["issues"])

            summary.append({
                "campaign_id": campaign["campaign_id"],
                "date": date,
                "status": r["status"],
                "cameras": r["cameras"],
                "aligned": r["aligned"],
                "camera_source_xyz": r["camera_source_xyz"],
                "camera_reference_enabled": r["camera_reference_enabled"],
                "photo_paths_absolute": r["photo_paths_absolute"],
                "photo_files_existing": r["photo_files_existing"],
                "issues": r["issues"]
            })

            for label, role, nproj, source, enabled in r["markers"]:
                details.append({
                    "campaign_id": campaign["campaign_id"],
                    "date": date,
                    "marker": label,
                    "role": role,
                    "projections": nproj,
                    "has_source_xyz": source,
                    "reference_enabled": enabled,
                })

        except Exception as exc:
            traceback.print_exc()
            summary.append({
                "campaign_id": campaign["campaign_id"],
                "date": date,
                "status": "FAIL",
                "issues": str(exc)
            })

    summary_path = base / "validation_marking.csv"
    details_path = base / "validation_marking_markers.csv"

    summary_fields = [
        "campaign_id","date","status","cameras","aligned",
        "camera_source_xyz","camera_reference_enabled",
        "photo_paths_absolute","photo_files_existing","issues"
    ]
    with summary_path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=summary_fields)
        w.writeheader()
        for row in summary:
            full = {k: row.get(k, "") for k in summary_fields}
            w.writerow(full)

    detail_fields = [
        "campaign_id","date","marker","role","projections",
        "has_source_xyz","reference_enabled"
    ]
    with details_path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=detail_fields)
        w.writeheader()
        w.writerows(details)

    print("\nSummary:", summary_path)
    print("Markers:", details_path)

if __name__ == "__main__":
    main()
