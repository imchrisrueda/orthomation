from pathlib import Path
import json
import sys
import Metashape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import palmeri_pipeline as pipeline

photo = Path(r"F:\datos_palmeri\2025-04-29_Poveda-Palmeri\1a_RGB\DJI_15m_202504291353_011_palmeri29-4-25\DJI_20250429141808_0001.JPG")
global_cfg = json.loads((ROOT / "config" / "global.json").read_text(encoding="utf-8"))
campaign = json.loads((ROOT / "campaigns" / "2025.json").read_text(encoding="utf-8"))
flight = campaign["flights"][0]
coords, gcp_ids, checkpoint_ids, job, jobxml_path = pipeline.load_ground_control(campaign, flight)

doc = Metashape.Document()
chunk = doc.addChunk()
pipeline.set_reference_settings(chunk, campaign)
chunk.addPhotos(
    filenames=[str(photo)],
    load_reference=True,
    load_xmp_calibration=True,
    load_xmp_orientation=True,
    load_xmp_accuracy=True,
    load_xmp_antenna=False,
)
pipeline.set_reference_settings(chunk, campaign)
pipeline.disable_camera_control(chunk)
pipeline.import_gcp_source(chunk, campaign, coords, gcp_ids, checkpoint_ids)
stats = pipeline.validate_pre_alignment(chunk, campaign, coords, gcp_ids, checkpoint_ids)
print("PREFLIGHT_SMOKE", stats, len(chunk.markers), job["sha256"], jobxml_path)
print("METASHAPE_PREFLIGHT_SMOKE_OK")
Metashape.app.quit()
