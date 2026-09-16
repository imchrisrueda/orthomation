# -*- coding: utf-8 -*-
"""
PALMERI / METASHAPE AUTOMATION v0.8.1
Robust multi-campaign pipeline for Agisoft Metashape Professional 2.3.x.

Main v0.7 change:
- GCP/CP are imported BEFORE matching/alignment.
- A clearly named *_INCOMPLETE.psx is used while processing.
- *_MASTER.psx is created ONLY after all validation checks pass.
- On success, *_INCOMPLETE.psx is promoted (moved/renamed) to MASTER by default.
"""

from pathlib import Path
from collections import Counter
from datetime import datetime
import csv, json, os, traceback, shutil, gc
import Metashape

ROOT = Path(__file__).resolve().parent.parent
GLOBAL_PATH = ROOT / "config" / "global.json"

CAMPAIGN_ID = os.environ.get("PALMERI_CAMPAIGN", "").strip()
MODE = os.environ.get("PALMERI_MODE", "pilot").strip().lower()
OVERWRITE = os.environ.get("PALMERI_OVERWRITE", "0") == "1"
VALID_MODES = {"inventory", "pilot", "remaining", "all"}

def die(msg):
    raise RuntimeError(msg)

def load_json(path):
    if not path.exists():
        die(f"No existe: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def resolve_root_relative(path_str):
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p

def load_configs():
    if not CAMPAIGN_ID:
        die("Falta PALMERI_CAMPAIGN.")
    global_cfg = load_json(GLOBAL_PATH)
    campaign = load_json(ROOT / "campaigns" / f"{CAMPAIGN_ID}.json")
    if str(campaign.get("campaign_id")) != CAMPAIGN_ID:
        die("campaign_id no coincide con PALMERI_CAMPAIGN.")
    return global_cfg, campaign

def campaign_paths(global_cfg, campaign):
    base = Path(global_cfg["generated_root"]) / campaign["campaign_id"]
    project_root = base / "projects" / "metashape"
    work_root = base / "work"
    log_root = base / "logs"
    for p in (base, project_root, work_root, log_root):
        p.mkdir(parents=True, exist_ok=True)
    return (
        base,
        project_root,
        work_root,
        log_root,
        base / "inventory.csv",
        base / "phase2_projects.csv",
    )

def log_line(log_path, text):
    print(text)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(text + "\n")

def check_version(global_cfg):
    version = str(Metashape.app.version)
    prefix = str(global_cfg["metashape"]["target_version_prefix"])
    if not version.startswith(prefix):
        die(f"Metashape {version}; esperado {prefix}.x")
    return version

def list_files(folder, recursive=False):
    folder = Path(folder)
    it = folder.rglob("*") if recursive else folder.glob("*")
    return sorted((p for p in it if p.is_file()), key=lambda p: p.name.lower())

def make_inventory(global_cfg, campaign, inventory_csv, log_path):
    ps = global_cfg["photo_selection"]
    accepted = {x.upper() for x in ps["accepted_extensions"]}
    selected = {x.upper() for x in ps["selected_extensions"]}
    recursive = bool(ps["recursive"])
    fail_mixed = bool(ps["fail_if_jpg_and_dng_coexist"])

    rows = []
    log_line(log_path, f"=== INVENTARIO CAMPAÑA {campaign['campaign_id']} ===")

    for flight in campaign["flights"]:
        folder = Path(flight["input_dir"])
        exists = folder.exists()
        files = list_files(folder, recursive) if exists else []
        images = [p for p in files if p.suffix.upper() in accepted]
        counts = Counter(p.suffix.upper() for p in images)
        selected_files = [p for p in images if p.suffix.upper() in selected]

        jpg = counts[".JPG"] + counts[".JPEG"]
        dng = counts[".DNG"]
        warnings = []

        if not exists:
            warnings.append("DIRECTORY_NOT_FOUND")
        elif not images:
            warnings.append("NO_ACCEPTED_IMAGES")
        if fail_mixed and jpg and dng:
            warnings.append("JPG_AND_DNG_PRESENT")
        if exists and not selected_files:
            warnings.append("NO_SELECTED_JPG_JPEG")

        gcp_file = flight.get("gcp_file") or campaign["default_gcp_file"]
        row = {
            "campaign_id": campaign["campaign_id"],
            "date": flight["date"],
            "input_dir": str(folder),
            "exists": str(exists),
            "jpg": jpg,
            "dng": dng,
            "tif_tiff": counts[".TIF"] + counts[".TIFF"],
            "selected_count": len(selected_files),
            "gcp_file": gcp_file,
            "warnings": ";".join(warnings),
        }
        rows.append(row)

        status = "OK" if not warnings else "REVISAR"
        log_line(
            log_path,
            f"{flight['date']} | {status} | JPG={jpg} | DNG={dng} | "
            f"seleccionadas={len(selected_files)} | GCP={gcp_file}"
        )

    fields = [
        "campaign_id","date","input_dir","exists","jpg","dng","tif_tiff",
        "selected_count","gcp_file","warnings"
    ]
    with inventory_csv.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    return {r["date"]: r for r in rows}

def resolve_gcp_file(campaign, flight):
    return resolve_root_relative(flight.get("gcp_file") or campaign["default_gcp_file"])

def load_ground_control(gcp_path):
    if not gcp_path.exists():
        die(f"No existe archivo GCP: {gcp_path}")

    coords = {}
    gcp_ids = []
    checkpoint_ids = []

    with gcp_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"label","x","y","z","role","vertical_status"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            die(f"{gcp_path.name}: columnas incorrectas.")

        for row in reader:
            label = row["label"].strip()
            if not label:
                continue
            if label in coords:
                die(f"Label duplicado: {label}")

            try:
                x, y, z = float(row["x"]), float(row["y"]), float(row["z"])
            except Exception:
                die(f"Coordenadas inválidas para {label}")

            role = row["role"].strip().upper()
            if role not in {"GCP","CHECK_POINT"}:
                die(f"Role inválido para {label}: {role}")

            coords[label] = {
                "x": x, "y": y, "z": z,
                "role": role,
                "vertical_status": row["vertical_status"].strip()
            }

            if role == "GCP":
                gcp_ids.append(label)
            else:
                checkpoint_ids.append(label)

    if not coords:
        die(f"{gcp_path} está vacío.")
    if len(gcp_ids) < 3:
        die("Se requieren al menos 3 GCP.")
    if len(checkpoint_ids) < 1:
        die("Se requiere al menos 1 CHECK_POINT.")

    return coords, gcp_ids, checkpoint_ids

def select_photos(flight, global_cfg):
    selected = {x.upper() for x in global_cfg["photo_selection"]["selected_extensions"]}
    recursive = bool(global_cfg["photo_selection"]["recursive"])
    return [
        p for p in list_files(flight["input_dir"], recursive)
        if p.suffix.upper() in selected
    ]

def set_reference_settings(chunk, campaign):
    chunk.crs = Metashape.CoordinateSystem(campaign["output_crs"])
    chunk.camera_crs = Metashape.CoordinateSystem(campaign["camera_reference_crs"])
    chunk.marker_crs = Metashape.CoordinateSystem(campaign["marker_crs"])

    acc = campaign["marker_accuracy_m"]
    chunk.marker_location_accuracy = Metashape.Vector(
        [float(acc[0]), float(acc[1]), float(acc[2])]
    )
    chunk.marker_projection_accuracy = float(campaign["marker_projection_accuracy_px"])

def disable_camera_control(chunk):
    for camera in chunk.cameras:
        camera.reference.enabled = False

def camera_source_stats(chunk):
    return {
        "total": len(chunk.cameras),
        "with_location": sum(c.reference.location is not None for c in chunk.cameras),
        "with_accuracy": sum(c.reference.accuracy is not None for c in chunk.cameras),
        "with_rotation": sum(c.reference.rotation is not None for c in chunk.cameras),
        "enabled": sum(bool(c.reference.enabled) for c in chunk.cameras),
    }

def import_gcp_source(chunk, campaign, coords, gcp_ids, checkpoint_ids):
    runtime_csv = ROOT / "_runtime_gcp_nxyz.csv"

    with runtime_csv.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["label","x","y","z"])
        for label in gcp_ids + checkpoint_ids:
            r = coords[label]
            w.writerow([label, r["x"], r["y"], r["z"]])

    try:
        chunk.importReference(
            path=str(runtime_csv),
            format=Metashape.ReferenceFormatCSV,
            columns="nxyz",
            delimiter=",",
            skip_rows=1,
            items=Metashape.ReferenceItemsMarkers,
            crs=Metashape.CoordinateSystem(campaign["marker_crs"]),
            create_markers=True,
            load_enabled=False,
        )
    finally:
        try:
            runtime_csv.unlink()
        except Exception:
            pass

    by_label = {m.label: m for m in chunk.markers}
    failures = []

    for label in gcp_ids + checkpoint_ids:
        marker = by_label.get(label)
        if marker is None:
            failures.append(f"{label}: no creado")
            continue

        marker.reference.enabled = False
        if marker.reference.location is None:
            failures.append(f"{label}: Source XYZ vacío")
            continue

        got = tuple(float(marker.reference.location[i]) for i in range(3))
        exp = (coords[label]["x"], coords[label]["y"], coords[label]["z"])
        if any(abs(a-b) > 1e-4 for a,b in zip(exp, got)):
            failures.append(f"{label}: esperado={exp}, cargado={got}")

    if failures:
        die("Fallo importando GCP/CP:\n" + "\n".join(failures))

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
    """
    Ensure image references are absolute and currently reachable.

    This is critical because the working project is promoted from work/
    to projects/. Relative paths would change meaning after that move.
    """
    issues = []
    absolute_count = 0
    existing_count = 0

    for camera in chunk.cameras:
        if camera.photo is None:
            issues.append(f"{camera.label}: camera.photo is None")
            continue

        path_text = str(camera.photo.path)
        photo_path = Path(path_text)

        if photo_path.is_absolute():
            absolute_count += 1
        else:
            issues.append(f"{camera.label}: relative photo path: {path_text}")

        if photo_path.exists():
            existing_count += 1
        else:
            issues.append(f"{camera.label}: photo file not found: {path_text}")

    if issues:
        preview = issues[:10]
        suffix = "" if len(issues) <= 10 else f"\n... +{len(issues)-10} incidencias"
        raise RuntimeError(
            "Validación de rutas de imágenes fallida:\n- "
            + "\n- ".join(preview)
            + suffix
        )

    return {
        "total": len(chunk.cameras),
        "absolute": absolute_count,
        "existing": existing_count,
    }

def validate_pre_alignment(chunk, campaign, gcp_ids, checkpoint_ids):
    issues = []

    photo_stats = validate_photo_paths(chunk)
    stats = camera_source_stats(chunk)
    if stats["total"] == 0:
        issues.append("No hay cámaras.")
    if stats["with_location"] != stats["total"]:
        issues.append(f"Camera Source GPS {stats['with_location']}/{stats['total']}")
    if stats["enabled"]:
        issues.append(f"{stats['enabled']} cámaras reference ON")

    by_label = {m.label: m for m in chunk.markers}
    for label in gcp_ids + checkpoint_ids:
        m = by_label.get(label)
        if m is None:
            issues.append(f"Falta marcador {label}")
        else:
            if m.reference.location is None:
                issues.append(f"{label}: Source XYZ vacío")
            if m.reference.enabled:
                issues.append(f"{label}: reference ON")

    exp_output = normalize_crs_id(campaign["output_crs"])
    exp_camera = normalize_crs_id(campaign["camera_reference_crs"])
    exp_marker = normalize_crs_id(campaign["marker_crs"])

    got_output = normalize_crs_id(crs_text(chunk.crs))
    got_camera = normalize_crs_id(crs_text(chunk.camera_crs))
    got_marker = normalize_crs_id(crs_text(chunk.marker_crs))

    if exp_output != got_output:
        issues.append(
            f"Chunk CRS incorrecto: {crs_text(chunk.crs)}; "
            f"esperado {campaign['output_crs']}"
        )
    if exp_camera != got_camera:
        issues.append(
            f"Camera CRS incorrecto: {crs_text(chunk.camera_crs)}; "
            f"esperado {campaign['camera_reference_crs']}"
        )
    if exp_marker != got_marker:
        issues.append(
            f"Marker CRS incorrecto: {crs_text(chunk.marker_crs)}; "
            f"esperado {campaign['marker_crs']}"
        )

    expected_acc = [float(x) for x in campaign["marker_accuracy_m"]]
    got_acc = list(chunk.marker_location_accuracy)
    if any(abs(a-b) > 1e-9 for a,b in zip(expected_acc, got_acc)):
        issues.append(f"Marker accuracy {got_acc}; esperado {expected_acc}")

    expected_proj = float(campaign["marker_projection_accuracy_px"])
    got_proj = float(chunk.marker_projection_accuracy)
    if abs(expected_proj - got_proj) > 1e-9:
        issues.append(f"Marker projection accuracy {got_proj}; esperado {expected_proj}")

    if issues:
        die("Validación PRE-ALIGN fallida:\n- " + "\n- ".join(issues))

    return stats

def validate_post_alignment(chunk, campaign, gcp_ids, checkpoint_ids):
    issues = []

    photo_stats = validate_photo_paths(chunk)
    aligned = sum(c.transform is not None for c in chunk.cameras)
    if aligned != len(chunk.cameras):
        issues.append(f"Alineación incompleta: {aligned}/{len(chunk.cameras)}")

    stats = camera_source_stats(chunk)
    if stats["with_location"] != stats["total"]:
        issues.append(f"Camera Source GPS {stats['with_location']}/{stats['total']}")
    if stats["enabled"]:
        issues.append(f"{stats['enabled']} cámaras reference ON")

    by_label = {m.label: m for m in chunk.markers}
    for label in gcp_ids + checkpoint_ids:
        m = by_label.get(label)
        if m is None:
            issues.append(f"Falta marcador {label}")
        else:
            if m.reference.location is None:
                issues.append(f"{label}: Source XYZ vacío")
            if m.reference.enabled:
                issues.append(f"{label}: reference ON")

    if chunk.point_cloud is not None:
        issues.append("Existe Point Cloud")
    if chunk.elevation is not None:
        issues.append("Existe DEM/DSM")
    if chunk.orthomosaic is not None:
        issues.append("Existe Orthomosaic")

    if issues:
        die("Validación POST-ALIGN fallida:\n- " + "\n- ".join(issues))

    tie_points = len(chunk.tie_points.points) if chunk.tie_points is not None else 0
    return aligned, tie_points, stats


def project_files_dir(psx_path):
    """
    Metashape .psx projects normally use an associated sibling .files directory.
    Example:
      project.psx
      project.files/
    """
    return psx_path.with_suffix(".files")

def release_document(doc, chunk):
    """
    Save references are released before filesystem promotion.
    Metashape has no explicit Document.close() API. Replacing the Document
    object is the established way to release an opened project in scripts.
    """
    try:
        if doc is not None:
            doc.save()
    except Exception:
        pass

    chunk = None
    doc = None
    gc.collect()

    # Creating a fresh Document object helps Metashape release the previous
    # project handle before moving/renaming its files.
    fresh = Metashape.Document()
    fresh = None
    gc.collect()

def move_with_rollback(src_path, dst_path, moved):
    if not src_path.exists():
        return

    dst_path.parent.mkdir(parents=True, exist_ok=True)

    if dst_path.exists():
        raise RuntimeError(f"Destino ya existe durante promoción: {dst_path}")

    shutil.move(str(src_path), str(dst_path))
    moved.append((src_path, dst_path))

def rollback_moves(moved):
    for src_path, dst_path in reversed(moved):
        try:
            if dst_path.exists() and not src_path.exists():
                src_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(dst_path), str(src_path))
        except Exception:
            pass

def promote_incomplete_to_master(
    incomplete_psx,
    master_psx,
    global_cfg,
    campaign,
    gcp_ids,
    checkpoint_ids,
    log_path,
):
    """
    Promote a validated working project to the official MASTER.

    Default behaviour:
      INCOMPLETE.psx + INCOMPLETE.files/
          -> MASTER.psx + MASTER.files/

    No second full copy is retained on success.

    If processing.keep_incomplete_on_success=true, Save As is used instead
    and the working project is intentionally preserved.
    """
    processing_cfg = global_cfg.get("processing", {})
    keep_incomplete = bool(
        processing_cfg.get("keep_incomplete_on_success", False)
    )
    verify_promoted = bool(
        processing_cfg.get("verify_promoted_master", True)
    )

    incomplete_files = project_files_dir(incomplete_psx)
    master_files = project_files_dir(master_psx)

    if master_psx.exists() or master_files.exists():
        raise RuntimeError(
            f"No se puede promover: ya existe MASTER o su .files: {master_psx}"
        )

    if keep_incomplete:
        # Debug/archival mode: preserve working project and create MASTER copy.
        source_doc = Metashape.Document()
        source_doc.open(str(incomplete_psx))
        source_doc.save(str(master_psx))
        source_doc = None
        gc.collect()
        log_line(
            log_path,
            "Promotion mode: COPY (keep_incomplete_on_success=true)"
        )
    else:
        # Normal mode: one project only. Move/rename after all validations pass.
        moved = []
        try:
            # Move .files first and .psx second. If anything fails, rollback.
            if incomplete_files.exists():
                move_with_rollback(incomplete_files, master_files, moved)
            move_with_rollback(incomplete_psx, master_psx, moved)
        except Exception:
            rollback_moves(moved)
            raise

        log_line(
            log_path,
            "Promotion mode: MOVE/RENAME "
            "(keep_incomplete_on_success=false)"
        )

    # Reopen the promoted MASTER to ensure that the renamed project is readable
    # and still satisfies the final state checks.
    if verify_promoted:
        verify_doc = Metashape.Document()
        verify_doc.open(str(master_psx), read_only=True)
        verify_chunk = verify_doc.chunk

        if verify_chunk is None:
            raise RuntimeError("MASTER promovido no contiene chunk activo.")

        validate_post_alignment(
            verify_chunk, campaign, gcp_ids, checkpoint_ids
        )

        verify_chunk = None
        verify_doc = None
        gc.collect()

        log_line(log_path, "Promoted MASTER reopen validation: OK")

    # Clean empty per-flight work directories, but retain campaign work root.
    try:
        work_rgb_dir = incomplete_psx.parent
        work_date_dir = work_rgb_dir.parent

        if work_rgb_dir.exists() and not any(work_rgb_dir.iterdir()):
            work_rgb_dir.rmdir()

        if work_date_dir.exists() and not any(work_date_dir.iterdir()):
            work_date_dir.rmdir()
    except Exception as cleanup_error:
        log_line(
            log_path,
            f"WARNING: empty work directory cleanup failed: {cleanup_error}"
        )


def create_master(flight, global_cfg, campaign, project_root, work_root, inv, log_path):
    date = flight["date"]
    row = inv[date]

    if row["warnings"]:
        die(f"{date}: inventario con advertencias: {row['warnings']}")

    photos = select_photos(flight, global_cfg)
    expected = int(row["selected_count"])
    if not photos or len(photos) != expected:
        die(f"{date}: fotos={len(photos)}, inventario={expected}")

    gcp_path = resolve_gcp_file(campaign, flight)
    coords, gcp_ids, checkpoint_ids = load_ground_control(gcp_path)

    outdir = project_root / date / "RGB_P1"
    workdir = work_root / date / "RGB_P1"
    outdir.mkdir(parents=True, exist_ok=True)
    workdir.mkdir(parents=True, exist_ok=True)

    stem = f"{date}_RGB_P1_{campaign['alignment_preset']}"
    incomplete_psx = workdir / f"{stem}_INCOMPLETE.psx"
    master_psx = outdir / f"{stem}_MASTER.psx"

    if master_psx.exists() and not OVERWRITE:
        die(f"MASTER ya existe: {master_psx}")
    if incomplete_psx.exists() and not OVERWRITE:
        die(
            f"Existe un proyecto INCOMPLETE previo: {incomplete_psx}. "
            "Elimínalo o borra la carpeta de salida de la campaña para reiniciar."
        )

    log_line(log_path, f"\n=== MASTER {campaign['campaign_id']} / {date} ===")
    log_line(log_path, f"Working project: {incomplete_psx}")
    log_line(log_path, f"Final MASTER: {master_psx}")
    log_line(log_path, f"GCP file: {gcp_path}")

    # IMPORTANT: the work project is later moved/renamed to MASTER.
    # Store image references as absolute paths so promotion cannot break them.
    if global_cfg.get("processing", {}).get("store_photo_paths_absolute", True):
        Metashape.app.settings.project_absolute_paths = True
        log_line(log_path, "Photo path storage: ABSOLUTE")

    doc = Metashape.Document()
    doc.save(str(incomplete_psx))
    chunk = doc.addChunk()
    chunk.label = f"{campaign['campaign_id']}_{stem}_WORK"

    # 1. Set settings before image import.
    set_reference_settings(chunk, campaign)

    # 2. Load images WITH Source GPS/XMP.
    cam_cfg = global_cfg["camera_reference"]
    chunk.addPhotos(
        filenames=[str(p) for p in photos],
        strip_extensions=False,
        load_reference=bool(cam_cfg["load_source_coordinates"]),
        load_xmp_calibration=True,
        load_xmp_orientation=bool(cam_cfg["load_xmp_orientation"]),
        load_xmp_accuracy=bool(cam_cfg["load_xmp_accuracy"]),
        load_xmp_antenna=bool(cam_cfg["load_xmp_antenna"]),
    )

    # Defensive normalization: addPhotos receives absolute paths. Keep them
    # explicitly absolute in each Photo object as well.
    for camera in chunk.cameras:
        if camera.photo is not None:
            camera.photo.path = str(Path(camera.photo.path).resolve())

    # Reassert reference settings after metadata import.
    set_reference_settings(chunk, campaign)
    disable_camera_control(chunk)

    # 3. Import GCP/CP BEFORE alignment.
    import_gcp_source(chunk, campaign, coords, gcp_ids, checkpoint_ids)
    set_reference_settings(chunk, campaign)
    disable_camera_control(chunk)

    # 4. Validate and checkpoint PRE-ALIGN state.
    pre_stats = validate_pre_alignment(
        chunk, campaign, gcp_ids, checkpoint_ids
    )
    doc.save()

    log_line(
        log_path,
        f"PRE-ALIGN OK | cameras={pre_stats['total']} | "
        f"Source GPS={pre_stats['with_location']} | "
        f"markers={len(gcp_ids) + len(checkpoint_ids)}"
    )

    # 5. Alignment A0/A1. Camera positions are present but disabled;
    #    reference_preselection remains explicitly OFF.
    preset_name = campaign["alignment_preset"]
    a = global_cfg["metashape"]["alignment_presets"][preset_name]

    chunk.matchPhotos(
        downscale=int(a["downscale"]),
        generic_preselection=bool(a["generic_preselection"]),
        reference_preselection=False,
        filter_stationary_points=bool(a["filter_stationary_points"]),
        keypoint_limit=int(a["keypoint_limit"]),
        tiepoint_limit=int(a["tiepoint_limit"]),
        guided_matching=bool(a["guided_matching"]),
        reset_matches=True,
    )
    doc.save()

    chunk.alignCameras(
        adaptive_fitting=bool(a["adaptive_fitting"]),
        reset_alignment=False,
    )

    set_reference_settings(chunk, campaign)
    disable_camera_control(chunk)

    # 6. Full validation before a MASTER is allowed to exist.
    aligned, tie_points, stats = validate_post_alignment(
        chunk, campaign, gcp_ids, checkpoint_ids
    )

    # 7. Finalize the working project, release Metashape file handles,
    #    and promote INCOMPLETE -> MASTER without retaining a duplicate
    #    unless explicitly requested in config/global.json.
    chunk.label = f"{campaign['campaign_id']}_{stem}_MASTER"
    doc.save()

    # Release references before moving the .psx/.files pair.
    release_document(doc, chunk)
    chunk = None
    doc = None

    promote_incomplete_to_master(
        incomplete_psx=incomplete_psx,
        master_psx=master_psx,
        global_cfg=global_cfg,
        campaign=campaign,
        gcp_ids=gcp_ids,
        checkpoint_ids=checkpoint_ids,
        log_path=log_path,
    )

    log_line(log_path, f"MASTER CREATED: {master_psx}")
    log_line(log_path, f"Alineadas: {aligned}/{stats['total']}")
    log_line(log_path, f"Tie points: {tie_points}")
    log_line(
        log_path,
        f"Camera Source GPS: {stats['with_location']}/{stats['total']} | "
        f"XMP accuracy: {stats['with_accuracy']}/{stats['total']} | "
        f"camera reference enabled={stats['enabled']}"
    )
    log_line(
        log_path,
        f"Photo paths: absolute/existing = {stats['total']}/{stats['total']}"
    )
    log_line(
        log_path,
        f"CRS | chunk={campaign['output_crs']} | "
        f"camera={campaign['camera_reference_crs']} | "
        f"marker={campaign['marker_crs']}"
    )
    log_line(
        log_path,
        f"Marker accuracy={campaign['marker_accuracy_m']} m | "
        f"projection={campaign['marker_projection_accuracy_px']} px"
    )
    log_line(log_path, "GCP/CP loaded before alignment: YES")
    log_line(log_path, "Reference preselection: OFF")
    log_line(log_path, "Optimize Cameras: NOT RUN")

    return {
        "campaign_id": campaign["campaign_id"],
        "date": date,
        "gcp_file": str(gcp_path),
        "project": str(master_psx),
        "working_project": (
            str(incomplete_psx)
            if global_cfg.get("processing", {}).get(
                "keep_incomplete_on_success", False
            )
            else ""
        ),
        "images": stats["total"],
        "aligned": aligned,
        "tie_points": tie_points,
        "camera_source_xyz": stats["with_location"],
        "camera_xmp_accuracy": stats["with_accuracy"],
        "camera_reference_enabled": stats["enabled"],
        "status": "OK",
        "error": "",
    }

def write_summary(path, rows):
    fields = [
        "campaign_id","date","gcp_file","project","working_project",
        "images","aligned","tie_points","camera_source_xyz",
        "camera_xmp_accuracy","camera_reference_enabled","status","error"
    ]
    previous = {}
    if path.exists():
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                previous[row["date"]] = row
    for row in rows:
        previous[row["date"]] = row

    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for date in sorted(previous):
            w.writerow(previous[date])

def main():
    if MODE not in VALID_MODES:
        die(f"PALMERI_MODE inválido: {MODE}")

    global_cfg, campaign = load_configs()
    (
        _,
        project_root,
        work_root,
        log_root,
        inventory_csv,
        summary_csv,
    ) = campaign_paths(global_cfg, campaign)

    version = check_version(global_cfg)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_root / f"{stamp}_{MODE}.log"

    log_line(log_path, "Palmeri automation v0.8.1")
    log_line(log_path, f"Campaign: {campaign['campaign_id']} — {campaign['name']}")
    log_line(log_path, f"Metashape: {version}")
    log_line(log_path, f"Mode: {MODE}")

    inv = make_inventory(global_cfg, campaign, inventory_csv, log_path)
    if MODE == "inventory":
        return

    flights = [f for f in campaign["flights"] if f.get("enabled", True)]
    if MODE == "pilot":
        flights = [f for f in flights if f["date"] == campaign["pilot_date"]]
    elif MODE == "remaining":
        flights = [f for f in flights if f["date"] != campaign["pilot_date"]]

    results = []

    for flight in flights:
        try:
            results.append(
                create_master(
                    flight, global_cfg, campaign,
                    project_root, work_root, inv, log_path
                )
            )
        except Exception as exc:
            traceback.print_exc()
            log_line(log_path, f"ERROR {flight['date']}: {exc}")
            results.append({
                "campaign_id": campaign["campaign_id"],
                "date": flight["date"],
                "gcp_file": str(resolve_gcp_file(campaign, flight)),
                "project": "",
                "working_project": "",
                "images": "",
                "aligned": "",
                "tie_points": "",
                "camera_source_xyz": "",
                "camera_xmp_accuracy": "",
                "camera_reference_enabled": "",
                "status": "ERROR",
                "error": str(exc),
            })
            if MODE == "pilot":
                break

    write_summary(summary_csv, results)
    log_line(log_path, f"Resumen: {summary_csv}")

if __name__ == "__main__":
    main()
