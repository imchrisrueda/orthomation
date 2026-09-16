# Palmeri Metashape automation v8.0.2
# 01_apply_jobxml_vertical_to_master.py
#
# Run INSIDE Agisoft Metashape Professional 2.3.
# This script updates reference metadata/coordinates only.
# It DOES NOT align, optimize, update transform, or generate products.

import Metashape
import xml.etree.ElementTree as ET
import json, os, statistics, datetime

VERSION = "8.0.2"
LABEL_MAP = {"1":"E1", "2":"C2", "3":"E3", "4":"E4", "5":"C5", "6":"E6"}
ROLES = {"E1":"GCP","E3":"GCP","E4":"GCP","E6":"GCP","C2":"CHECK_POINT","C5":"CHECK_POINT"}
EXPECTED_GEOID = "EGM08IGN"
EXPECTED_CS_NAME_PARTS = ("UTM 30", "ETRS89")

def _set_location_enabled(ref, value):
    if hasattr(ref, "location_enabled"):
        ref.location_enabled = bool(value)
    elif hasattr(ref, "enabled"):
        ref.enabled = bool(value)
    else:
        raise RuntimeError("Reference object has no location_enabled/enabled property.")

def _set_rotation_enabled(ref, value):
    if hasattr(ref, "rotation_enabled"):
        ref.rotation_enabled = bool(value)

def _parse_jobxml(path):
    root = ET.parse(path).getroot()

    geoid = None
    cs_name = None
    zone_name = None
    datum_name = None

    for rec in root.iter("VerticalAdjustmentRecord"):
        typ = rec.findtext("Type")
        name = rec.findtext("GeoidName")
        if typ == "GeoidModel" and name:
            geoid = name

    for rec in root.iter("CoordinateSystemRecord"):
        s = rec.findtext("SystemName")
        z = rec.findtext("ZoneName")
        d = rec.findtext("DatumName")
        if any([s,z,d]):
            cs_name, zone_name, datum_name = s, z, d

    reductions = {}
    red = root.find("Reductions")
    if red is None:
        for e in root.iter("Reductions"):
            red = e
            break
    if red is None:
        raise RuntimeError("JobXML has no <Reductions> section.")

    for pt in red.findall("Point"):
        name = (pt.findtext("Name") or "").strip()
        if name not in LABEL_MAP:
            continue
        wgs = pt.find("WGS84")
        grid = pt.find("Grid")
        if wgs is None or grid is None:
            raise RuntimeError("Point %s lacks WGS84/Grid reductions." % name)
        reductions[name] = {
            "lat": float(wgs.findtext("Latitude")),
            "lon": float(wgs.findtext("Longitude")),
            "h": float(wgs.findtext("Height")),
            "north": float(grid.findtext("North")),
            "east": float(grid.findtext("East")),
            "H": float(grid.findtext("Elevation")),
        }

    precisions = {}
    for pr in root.iter("PointRecord"):
        name = (pr.findtext("Name") or "").strip()
        if name not in LABEL_MAP:
            continue
        precision = pr.find("Precision")
        if precision is None:
            continue
        precisions[name] = {
            "horizontal": float(precision.findtext("Horizontal")),
            "vertical": float(precision.findtext("Vertical")),
            "survey_method": pr.findtext("SurveyMethod"),
        }

    missing = sorted(set(LABEL_MAP) - set(reductions))
    if missing:
        raise RuntimeError("Missing control points in JobXML reductions: %s" % missing)

    return {
        "geoid": geoid,
        "system_name": cs_name,
        "zone_name": zone_name,
        "datum_name": datum_name,
        "points": reductions,
        "precisions": precisions,
    }

def main():
    app = Metashape.app
    doc = app.document
    chunk = doc.chunk
    if chunk is None:
        raise RuntimeError("No active chunk.")
    if not doc.path:
        raise RuntimeError("Save the project before running this script.")

    path = app.getOpenFileName("Select Trimble JobXML/JXL for this flight")
    if not path:
        print("Cancelled.")
        return

    job = _parse_jobxml(path)

    if job["geoid"] != EXPECTED_GEOID:
        raise RuntimeError("Expected geoid %s, found %r." % (EXPECTED_GEOID, job["geoid"]))

    cs_text = " | ".join(x or "" for x in [job["system_name"], job["zone_name"], job["datum_name"]])
    for token in EXPECTED_CS_NAME_PARTS:
        if token.lower() not in cs_text.lower():
            raise RuntimeError("Unexpected JobXML coordinate system: %s" % cs_text)

    # Explicit CRS configuration: EPSG:25830 for chunk/markers, WGS84 for camera source.
    chunk.crs = Metashape.CoordinateSystem("EPSG::25830")
    if hasattr(chunk, "marker_crs"):
        chunk.marker_crs = Metashape.CoordinateSystem("EPSG::25830")
    if hasattr(chunk, "camera_crs"):
        chunk.camera_crs = Metashape.CoordinateSystem("EPSG::4326")

    if hasattr(chunk, "marker_projection_accuracy"):
        chunk.marker_projection_accuracy = 0.5

    markers = {m.label: m for m in chunk.markers}
    required = set(ROLES)
    missing_markers = sorted(required - set(markers))
    if missing_markers:
        raise RuntimeError("These markers are missing from the active chunk: %s" % missing_markers)

    audit_points = []
    for job_id, label in LABEL_MAP.items():
        src = job["points"][job_id]
        prec = job["precisions"].get(job_id)
        marker = markers[label]

        # IMPORTANT: Z in EPSG::25830-only reference is h (ellipsoidal), not orthometric H.
        marker.reference.location = Metashape.Vector([src["east"], src["north"], src["h"]])

        if prec and hasattr(marker.reference, "accuracy"):
            # JobXML provides one horizontal precision and one vertical precision.
            # v8.0.2 maps horizontal conservatively to both X and Y.
            marker.reference.accuracy = Metashape.Vector([
                prec["horizontal"], prec["horizontal"], prec["vertical"]
            ])

        # MASTER must remain unconstrained until branching.
        _set_location_enabled(marker.reference, False)

        audit_points.append({
            "job_id": job_id,
            "label": label,
            "role": ROLES[label],
            "east": src["east"],
            "north": src["north"],
            "h_ellipsoid": src["h"],
            "H_orthometric_EGM08IGN": src["H"],
            "N_geoid": src["h"] - src["H"],
            "horizontal_precision": None if not prec else prec["horizontal"],
            "vertical_precision": None if not prec else prec["vertical"],
            "survey_method": None if not prec else prec["survey_method"],
        })

    # MASTER: camera location and orientation constraints OFF.
    cam_source_altitudes = []
    for cam in chunk.cameras:
        if not cam.reference:
            continue
        _set_location_enabled(cam.reference, False)
        _set_rotation_enabled(cam.reference, False)
        loc = getattr(cam.reference, "location", None)
        if loc is not None and len(loc) >= 3:
            try:
                cam_source_altitudes.append(float(loc[2]))
            except Exception:
                pass

    ns = [p["N_geoid"] for p in audit_points]
    hs = [p["h_ellipsoid"] for p in audit_points]

    audit = {
        "package_version": VERSION,
        "timestamp": datetime.datetime.now().isoformat(),
        "project": doc.path,
        "chunk": chunk.label,
        "jobxml": path,
        "job_coordinate_system": cs_text,
        "job_vertical_adjustment": "GeoidModel",
        "job_geoid": job["geoid"],
        "metashape_chunk_crs": "EPSG::25830",
        "metashape_marker_crs": "EPSG::25830",
        "metashape_camera_crs": "EPSG::4326",
        "marker_z_used": "ellipsoidal h from JobXML WGS84/Height",
        "marker_reference_state": "ALL OFF in MASTER",
        "camera_location_reference_state": "ALL OFF in MASTER",
        "camera_rotation_reference_state": "ALL OFF in MASTER",
        "mean_geoid_separation_m": statistics.mean(ns),
        "geoid_separation_range_m": max(ns) - min(ns),
        "median_ground_h_m": statistics.median(hs),
        "median_camera_source_altitude_m": statistics.median(cam_source_altitudes) if cam_source_altitudes else None,
        "median_camera_minus_ground_h_m": (
            statistics.median(cam_source_altitudes) - statistics.median(hs)
            if cam_source_altitudes else None
        ),
        "points": audit_points,
        "next_action": "Inspect C2, E1 and E4 projection marking. Do NOT optimize yet."
    }

    out_dir = os.path.dirname(doc.path)
    out_path = os.path.join(out_dir, "vertical_audit_MASTER_v8_0_2.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2, ensure_ascii=False)

    doc.save()
    print(json.dumps(audit, indent=2, ensure_ascii=False))
    app.messageBox(
        "v8.0.2 applied to MASTER.\n\n"
        "Markers now use JobXML ellipsoidal heights (h).\n"
        "EGM08IGN orthometric heights (H) are retained in the audit only.\n"
        "All camera and marker reference constraints remain OFF.\n\n"
        "Next: inspect C2, E1 and E4 projection marks. Do NOT optimize yet.\n\n"
        "Audit: " + out_path
    )

main()
