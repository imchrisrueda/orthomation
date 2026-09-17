"""Non-processing API smoke test for the reviewed fixed-model workflow."""

from pathlib import Path
import json
import sys
import Metashape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from optimization_core import CALIBRATION_PARAMETERS, validate_metashape_version, validate_optimization_contract
from orthomation_core import (
    camera_transform_rows,
    parse_jobxml,
    persisted_active_chunk_transform_rows,
    transform_representation_equivalence,
)
from export_postoptimization_metrics import marker_coordinate_solution
from optimize_branch import build_task


class SyntheticTransform:
    def __init__(self, matrix):
        self.matrix = matrix


class SyntheticChunk:
    def __init__(self, crs, matrix):
        self.crs = crs
        self.marker_crs = crs
        self.transform = SyntheticTransform(matrix)


class SyntheticReference:
    def __init__(self, location):
        self.location = location


class SyntheticMarker:
    def __init__(self, position, reference):
        self.position = position
        self.reference = SyntheticReference(reference)

config = json.loads((ROOT / "config" / "global.json").read_text(encoding="utf-8"))
parameters = validate_optimization_contract(config["optimization"])
experiment = config["optimization_experiments"]["fixed_model_v1"]
validate_metashape_version(Metashape.app.version, experiment["reviewed_metashape_version"])
task, recorded, serialized = build_task(parameters)
assert recorded == parameters
assert recorded["adaptive_fitting"] is False
assert recorded["fit_corrections"] is False
assert recorded["tiepoint_covariance"] is True

calibration = Metashape.Calibration()
snapshot = {name: float(getattr(calibration, name)) for name in CALIBRATION_PARAMETERS}
assert set(snapshot) == set(CALIBRATION_PARAMETERS)

campaign = json.loads((ROOT / "campaigns" / "2025.json").read_text(encoding="utf-8"))
job = parse_jobxml(ROOT / campaign["default_jobxml"], campaign["control_points"], campaign["jobxml_rules"])
assert job["sha256"] == experiment["jobxml_sha256"]

master_path = (
    Path(config["generated_root"])
    / experiment["campaign_id"]
    / "projects"
    / "metashape"
    / experiment["flight_date"]
    / "RGB_P1"
    / f"{experiment['flight_date']}_RGB_P1_{campaign['alignment_preset']}_MASTER.psx"
)
persisted = persisted_active_chunk_transform_rows(master_path)
read_only_document = Metashape.Document()
read_only_document.open(str(master_path), read_only=True)
assert read_only_document.chunk is not None
assert persisted["chunk_label"] == read_only_document.chunk.label
equivalence = transform_representation_equivalence(
    persisted["rows"], camera_transform_rows(read_only_document.chunk), experiment
)
assert equivalence["status"] == "PASS", equivalence["issues"]
assert equivalence["camera_count_persisted"] == 43
assert equivalence["camera_count_live"] == 43
assert equivalence["component_count_persisted"] == 688
assert equivalence["component_count_live"] == 688
assert equivalence["different_indices"] == [0, 1, 2, 4, 5, 6, 8, 9, 10]
assert equivalence["maximum_absolute_delta"] <= 1e-15

crs = Metashape.CoordinateSystem("EPSG::25830")
reference = Metashape.Vector([458959.0, 4462779.0, 586.0])
geocentric = crs.geoccs
reference_geocentric = Metashape.CoordinateSystem.transform(reference, crs, geocentric)
identity = Metashape.Matrix([
    [1.0, 0.0, 0.0, 0.0],
    [0.0, 1.0, 0.0, 0.0],
    [0.0, 0.0, 1.0, 0.0],
    [0.0, 0.0, 0.0, 1.0],
])
estimated, local_residual, projected_delta = marker_coordinate_solution(
    SyntheticChunk(crs, identity),
    SyntheticMarker(reference_geocentric, reference),
)
assert max(abs(float(local_residual[i])) for i in range(3)) < 1e-8
assert max(abs(float(projected_delta[i])) for i in range(3)) < 1e-8

print("FIXED_MODEL_TASK_PARAMETERS", json.dumps(recorded, sort_keys=True))
print("FIXED_MODEL_TASK_SERIALIZATION", serialized)
print("FIXED_MODEL_CALIBRATION_PARAMETERS", sorted(snapshot))
print("FIXED_MODEL_JOBXML_SHA256", job["sha256"])
print("FIXED_MODEL_MASTER_OPEN_MODE", "read_only=True")
print("FIXED_MODEL_MASTER_PERSISTED_SHA256", equivalence["persisted_transform_sha256"])
print("FIXED_MODEL_MASTER_LIVE_SHA256", equivalence["live_transform_sha256"])
print("FIXED_MODEL_MASTER_COMMON_12SIG_SHA256", equivalence["common_significant_digit_transform_sha256"])
print("FIXED_MODEL_MASTER_MAX_ABS_DELTA", equivalence["maximum_absolute_delta"])
print("FIXED_MODEL_SYNTHETIC_ESTIMATED", list(estimated))
print("FIXED_MODEL_SYNTHETIC_LOCAL_RESIDUAL", list(local_residual))
print("METASHAPE_FIXED_MODEL_SMOKE_OK")
Metashape.app.quit()
