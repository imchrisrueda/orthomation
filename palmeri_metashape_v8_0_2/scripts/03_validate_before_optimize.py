# Palmeri Metashape automation v8.0.2
# 03_validate_before_optimize.py
#
# Read-only QA of the active branch. Does not modify the project.

import Metashape, statistics, json

GCP = {"E1","E3","E4","E6"}
CP = {"C2","C5"}
EXPECTED = {
"E1":586.25523655183,
"C2":586.31980273008,
"E3":586.36660741895,
"E4":586.31578661195,
"C5":586.28476336478,
"E6":586.26396011814,
}
ORTHO = {
"E1":535.04365234275,
"C2":535.10820422906,
"E3":535.15503922849,
"E4":535.10411762094,
"C5":535.07310641573,
"E6":535.0522441815,
}

def loc_enabled(ref):
    if hasattr(ref, "location_enabled"):
        return bool(ref.location_enabled)
    if hasattr(ref, "enabled"):
        return bool(ref.enabled)
    return None

def rot_enabled(ref):
    if hasattr(ref, "rotation_enabled"):
        return bool(ref.rotation_enabled)
    return False

def main():
    chunk = Metashape.app.document.chunk
    if chunk is None:
        raise RuntimeError("No active chunk.")

    markers = {m.label:m for m in chunk.markers}
    issues = []
    marker_state = {}
    for label in sorted(GCP | CP):
        if label not in markers:
            issues.append("Missing marker: " + label)
            continue
        m = markers[label]
        loc = m.reference.location
        z = None if loc is None else float(loc[2])
        marker_state[label] = {"enabled": loc_enabled(m.reference), "z": z}
        if z is None:
            issues.append("%s has no reference Z." % label)
        else:
            if abs(z - EXPECTED[label]) > 0.002:
                if abs(z - ORTHO[label]) < 0.01:
                    issues.append("%s is using orthometric H instead of ellipsoidal h." % label)
                else:
                    issues.append("%s Z differs from JobXML h by %.4f m." % (label, z-EXPECTED[label]))

    cam_loc_on = 0
    cam_rot_on = 0
    cam_with_source = 0
    cam_alts = []
    for cam in chunk.cameras:
        if not cam.reference:
            continue
        loc = getattr(cam.reference, "location", None)
        if loc is not None:
            cam_with_source += 1
            if len(loc) >= 3:
                try: cam_alts.append(float(loc[2]))
                except: pass
        if loc_enabled(cam.reference):
            cam_loc_on += 1
        if rot_enabled(cam.reference):
            cam_rot_on += 1

    label_upper = chunk.label.upper()
    if "GCP_ONLY" in label_upper:
        expected_cam_on = 0
    elif "GCP_P1" in label_upper:
        expected_cam_on = cam_with_source
    else:
        expected_cam_on = None
        issues.append("Chunk label does not identify GCP_ONLY or GCP_P1.")

    for label in GCP:
        if label in marker_state and marker_state[label]["enabled"] is not True:
            issues.append("%s should be active as GCP." % label)
    for label in CP:
        if label in marker_state and marker_state[label]["enabled"] is not False:
            issues.append("%s must remain OFF as Check Point." % label)

    if expected_cam_on is not None and cam_loc_on != expected_cam_on:
        issues.append("Camera XYZ enabled count %d; expected %d." % (cam_loc_on, expected_cam_on))
    if cam_rot_on != 0:
        issues.append("Camera orientation constraints are ON for %d cameras; expected 0." % cam_rot_on)

    report = {
        "chunk": chunk.label,
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
        "markers": marker_state,
        "camera_source_locations": cam_with_source,
        "camera_location_constraints_on": cam_loc_on,
        "camera_rotation_constraints_on": cam_rot_on,
        "median_camera_source_altitude_m": statistics.median(cam_alts) if cam_alts else None,
        "next_action": (
            "Optimize Cameras using the same settings in both branches."
            if not issues else
            "Correct the listed issues before optimization."
        )
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    Metashape.app.messageBox(
        "Pre-optimize validation: %s\n\n%s" %
        (report["status"], "\n".join(issues) if issues else "No blocking issues detected.")
    )

main()
