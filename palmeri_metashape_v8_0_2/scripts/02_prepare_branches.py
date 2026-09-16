# Palmeri Metashape automation v8.0.2
# 02_prepare_branches.py
#
# Run INSIDE Metashape only AFTER projection QA is complete.
# Creates two identical copies from the active MASTER:
#   GCP_ONLY: GCP ON, camera XYZ OFF, camera orientation OFF
#   GCP_P1:   GCP ON, camera XYZ ON,  camera orientation OFF
# C2/C5 remain Check Points (OFF) in both branches.
# No optimization is executed.

import Metashape
import os, json, datetime

GCP = {"E1","E3","E4","E6"}
CP = {"C2","C5"}

def _set_location_enabled(ref, value):
    if hasattr(ref, "location_enabled"):
        ref.location_enabled = bool(value)
    elif hasattr(ref, "enabled"):
        ref.enabled = bool(value)
    else:
        raise RuntimeError("Reference object has no location_enabled/enabled property.")

def _get_location_enabled(ref):
    if hasattr(ref, "location_enabled"):
        return bool(ref.location_enabled)
    if hasattr(ref, "enabled"):
        return bool(ref.enabled)
    return None

def _set_rotation_enabled(ref, value):
    if hasattr(ref, "rotation_enabled"):
        ref.rotation_enabled = bool(value)

def configure_branch(chunk, use_p1):
    markers = {m.label:m for m in chunk.markers}
    missing = sorted((GCP | CP) - set(markers))
    if missing:
        raise RuntimeError("Missing markers in %s: %s" % (chunk.label, missing))

    for label in GCP:
        _set_location_enabled(markers[label].reference, True)
    for label in CP:
        _set_location_enabled(markers[label].reference, False)

    source_location_count = 0
    enabled_camera_count = 0
    for cam in chunk.cameras:
        if not cam.reference:
            continue
        if getattr(cam.reference, "location", None) is not None:
            source_location_count += 1
        _set_location_enabled(cam.reference, use_p1)
        _set_rotation_enabled(cam.reference, False)
        if _get_location_enabled(cam.reference):
            enabled_camera_count += 1

    if use_p1 and source_location_count == 0:
        raise RuntimeError("GCP_P1 requested, but no camera source locations were found.")

    return {
        "source_camera_locations": source_location_count,
        "enabled_camera_locations": enabled_camera_count,
        "camera_orientation_constraints": 0
    }

def main():
    app = Metashape.app
    doc = app.document
    master = doc.chunk
    if master is None:
        raise RuntimeError("No active MASTER chunk.")
    if not doc.path:
        raise RuntimeError("Save the project first.")

    # Safety: MASTER should be unconstrained before branching.
    for m in master.markers:
        if m.label in GCP | CP:
            _set_location_enabled(m.reference, False)
    for cam in master.cameras:
        if cam.reference:
            _set_location_enabled(cam.reference, False)
            _set_rotation_enabled(cam.reference, False)

    master_label = master.label
    a = master.copy()
    a.label = master_label + "_GCP_ONLY"
    b = master.copy()
    b.label = master_label + "_GCP_P1"

    summary = {
        "package_version": "8.0.2",
        "timestamp": datetime.datetime.now().isoformat(),
        "master": master_label,
        "GCP_ONLY": configure_branch(a, False),
        "GCP_P1": configure_branch(b, True),
        "gcp": sorted(GCP),
        "check_points": sorted(CP),
        "note": "No Optimize Cameras has been executed. Camera yaw/pitch/roll are OFF in both branches."
    }

    doc.save()
    out_path = os.path.join(os.path.dirname(doc.path), "branch_setup_v8_0_2.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    app.messageBox(
        "Branches created.\n\n"
        + a.label + ": GCP ON, P1 XYZ OFF, P1 angles OFF\n"
        + b.label + ": GCP ON, P1 XYZ ON, P1 angles OFF\n"
        "C2/C5: OFF in both branches\n\n"
        "No optimization was run.\n"
        "Validate both branches before Optimize Cameras."
    )

main()
