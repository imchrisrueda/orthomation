"""Run the locked camera optimization after a fresh PASS preflight report."""

from hashlib import sha256
from pathlib import Path
import datetime
import json
import Metashape

ROOT = Path(__file__).resolve().parent.parent


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as stream:
        return json.load(stream)


def meta_value(owner, key, default=None):
    try:
        value = owner.meta[key]
    except (KeyError, TypeError):
        return default
    return default if value is None else value


def transform_fingerprint(chunk):
    rows = []
    for camera in sorted(chunk.cameras, key=lambda item: item.label):
        transform = camera.transform
        values = [] if transform is None else [float(value) for row in transform for value in row]
        rows.append((camera.label, values))
    return sha256(json.dumps(rows, separators=(",", ":")).encode("ascii")).hexdigest()


def calibration_snapshot(chunk):
    names = ("f", "cx", "cy", "b1", "b2", "k1", "k2", "k3", "k4", "p1", "p2")
    rows = []
    for sensor in chunk.sensors:
        calibration = sensor.calibration
        rows.append({
            "sensor": sensor.label,
            "type": str(sensor.type),
            "width": sensor.width,
            "height": sensor.height,
            "parameters": {name: float(getattr(calibration, name)) for name in names},
        })
    return rows


def main():
    doc = Metashape.app.document
    chunk = doc.chunk
    if chunk is None or not doc.path:
        raise RuntimeError("Open and save a validated branch first")
    branch = meta_value(chunk, "orthomation/branch")
    if branch not in {"GCP_ONLY", "GCP_P1"}:
        raise RuntimeError("Active chunk is not a controlled branch")
    if meta_value(chunk, "orthomation/stage") != "BRANCH_READY_FOR_OPTIMIZE":
        raise RuntimeError("Branch is not in BRANCH_READY_FOR_OPTIMIZE state")

    project_dir = Path(doc.path).resolve().parent
    preflight_path = project_dir / f"preopt_{branch}_v0_9_0.json"
    if not preflight_path.is_file():
        raise RuntimeError(f"Run validate_before_optimize.py first: {preflight_path}")
    preflight = load_json(preflight_path)
    current_fingerprint = transform_fingerprint(chunk)
    if preflight.get("status") != "PASS":
        raise RuntimeError("Latest pre-optimization report is not PASS")
    if preflight.get("preopt_transform_sha256") != current_fingerprint:
        raise RuntimeError("Branch changed after its pre-optimization report; validate again")
    if preflight.get("jobxml_sha256") != meta_value(chunk, "orthomation/jobxml_sha256"):
        raise RuntimeError("JobXML fingerprint changed after validation")

    config = load_json(ROOT / "config" / "global.json")
    parameters = dict(config["optimization"])
    calibration_before = calibration_snapshot(chunk)
    started = datetime.datetime.now().isoformat()
    chunk.optimizeCameras(**parameters)
    calibration_after = calibration_snapshot(chunk)
    after_fingerprint = transform_fingerprint(chunk)

    chunk.meta["orthomation/stage"] = "BRANCH_OPTIMIZED"
    chunk.meta["orthomation/optimized_at"] = datetime.datetime.now().isoformat()
    chunk.meta["orthomation/optimization_parameters"] = json.dumps(parameters, sort_keys=True)
    chunk.meta["orthomation/postopt_transform_sha256"] = after_fingerprint
    doc.save()

    report = {
        "adapter_version": "0.9.0",
        "branch": branch,
        "status": "OPTIMIZED",
        "started_at": started,
        "completed_at": datetime.datetime.now().isoformat(),
        "parameters": parameters,
        "jobxml_sha256": meta_value(chunk, "orthomation/jobxml_sha256"),
        "transform_sha256_before": current_fingerprint,
        "transform_sha256_after": after_fingerprint,
        "calibration_before": calibration_before,
        "calibration_after": calibration_after,
        "next_action": "Run the post-optimization metrics exporter; do not build products yet.",
    }
    output = project_dir / f"optimization_{branch}_v0_9_0.json"
    with output.open("w", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    Metashape.app.messageBox(f"{branch} optimization completed and saved. Do not build products before comparing both branches.")


if __name__ == "__main__":
    main()
