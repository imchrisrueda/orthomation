import Metashape
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from optimize_branch import calibration_snapshot
from orthomation_core import transform_fingerprint


class FingerprintCamera:
    def __init__(self, label, transform):
        self.label = label
        self.transform = transform


class FingerprintChunk:
    def __init__(self, cameras):
        self.cameras = cameras

photo = r"F:\datos_palmeri\2025-04-29_Poveda-Palmeri\1a_RGB\DJI_15m_202504291353_011_palmeri29-4-25\DJI_20250429141808_0001.JPG"
doc = Metashape.Document()
chunk = doc.addChunk()
chunk.crs = Metashape.CoordinateSystem("EPSG::25830")
chunk.camera_crs = Metashape.CoordinateSystem("EPSG::4326")
chunk.marker_crs = Metashape.CoordinateSystem("EPSG::25830")
chunk.addPhotos(
    filenames=[photo],
    load_reference=True,
    load_xmp_calibration=True,
    load_xmp_orientation=True,
    load_xmp_accuracy=True,
    load_xmp_antenna=False,
)
camera = chunk.cameras[0]
print("SMOKE_CAMERA_LOCATION", list(camera.reference.location))
print("SMOKE_CAMERA_ACCURACY", list(camera.reference.accuracy))
camera.reference.location_enabled = False
camera.reference.rotation_enabled = False
task = Metashape.Tasks.AnalyzeImages()
task.apply(chunk)
print("SMOKE_IMAGE_QUALITY", camera.meta["Image/Quality"])
marker = chunk.addMarker()
marker.label = "TEST"
marker.reference.location = Metashape.Vector([458959.0, 4462779.0, 586.0])
marker.reference.accuracy = Metashape.Vector([0.01, 0.01, 0.02])
marker.reference.enabled = False
print("SMOKE_MARKER", list(marker.reference.location), list(marker.reference.accuracy), marker.reference.enabled)
print("SMOKE_CALIBRATION", calibration_snapshot(chunk))
matrix = Metashape.Matrix([[1.0, 0.0], [0.0, 1.0]])
fingerprint = transform_fingerprint(FingerprintChunk([FingerprintCamera("TEST", matrix)]))
assert len(fingerprint) == 64
print("SMOKE_TRANSFORM_FINGERPRINT", fingerprint)
print("METASHAPE_SMOKE_OK")
Metashape.app.quit()
