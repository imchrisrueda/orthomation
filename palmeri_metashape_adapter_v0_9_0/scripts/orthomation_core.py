"""Pure-Python validation helpers shared by the Metashape adapter."""

from datetime import datetime
from hashlib import sha256
from pathlib import Path
import json
import math
import re
import xml.etree.ElementTree as ET
import zipfile


class ValidationError(RuntimeError):
    pass


def _flatten_numeric(value):
    """Return numeric values from flat or row-iterable Metashape objects."""
    try:
        return [float(value)]
    except (TypeError, ValueError):
        pass

    try:
        items = iter(value)
    except TypeError as exc:
        raise TypeError(f"Unsupported numeric container: {type(value).__name__}") from exc

    flattened = []
    for item in items:
        flattened.extend(_flatten_numeric(item))
    return flattened


def transform_fingerprint(chunk):
    """Hash camera transforms across Metashape matrix iteration variants."""
    rows = []
    for camera in sorted(chunk.cameras, key=lambda item: item.label):
        transform = camera.transform
        values = [] if transform is None else _flatten_numeric(transform)
        rows.append((camera.label, values))
    payload = json.dumps(rows, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return sha256(payload).hexdigest()


def camera_transform_rows(chunk):
    """Return the live camera-transform payload without changing fingerprint semantics."""
    rows = []
    for camera in sorted(chunk.cameras, key=lambda item: item.label):
        transform = camera.transform
        rows.append((camera.label, [] if transform is None else _flatten_numeric(transform)))
    return rows


def transform_rows_fingerprint(rows):
    """Hash already-extracted transform rows using the established JSON encoding."""
    normalized = [(str(label), [float(value) for value in values]) for label, values in rows]
    payload = json.dumps(normalized, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return sha256(payload).hexdigest()


def significant_transform_rows(rows, significant_digits):
    """Return a comparison-only significant-digit representation of transform rows."""
    digits = int(significant_digits)
    if digits < 1 or digits > 17:
        raise ValueError("significant_digits must be between 1 and 17")
    return [
        (str(label), [float(format(float(value), f".{digits}g")) for value in values])
        for label, values in rows
    ]


def persisted_active_chunk_transform_rows(project_path):
    """Read active-chunk camera transforms directly from a saved PSX without mutation."""
    psx_path = Path(project_path).resolve()
    root = ET.parse(psx_path).getroot()
    relative_archive = root.get("path")
    if not relative_archive:
        raise ValidationError(f"PSX does not reference a project archive: {psx_path}")
    archive_path = psx_path.parent / relative_archive.replace("{projectname}", psx_path.stem)
    with zipfile.ZipFile(archive_path) as project_archive:
        project_root = ET.fromstring(project_archive.read("doc.xml"))
    chunks = project_root.find("chunks")
    active_id = None if chunks is None else chunks.get("active_id")
    if chunks is None or active_id is None:
        raise ValidationError("Saved project does not identify an active chunk")
    chunk_node = next((node for node in chunks.findall("chunk") if node.get("id") == active_id), None)
    if chunk_node is None or not chunk_node.get("path"):
        raise ValidationError(f"Saved active chunk {active_id!r} has no archive path")
    chunk_archive_path = archive_path.parent / chunk_node.get("path")
    with zipfile.ZipFile(chunk_archive_path) as chunk_archive:
        chunk_root = ET.fromstring(chunk_archive.read("doc.xml"))
    rows = []
    for camera in chunk_root.findall(".//cameras/camera"):
        label = camera.get("label")
        if label is None:
            raise ValidationError("Saved active chunk contains an unlabeled camera")
        raw_transform = camera.findtext("transform")
        values = [] if raw_transform is None else [float(value) for value in raw_transform.split()]
        rows.append((label, values))
    return {
        "chunk_id": active_id,
        "chunk_label": chunk_root.get("label"),
        "chunk_archive": str(chunk_archive_path),
        "rows": sorted(rows),
    }


def transform_representation_equivalence(persisted_rows, live_rows, contract):
    """Compare persisted and live transforms against the reviewed dual-hash contract."""
    persisted = [(str(label), [float(value) for value in values]) for label, values in persisted_rows]
    live = [(str(label), [float(value) for value in values]) for label, values in live_rows]
    persisted.sort(key=lambda row: row[0])
    live.sort(key=lambda row: row[0])
    persisted_by_label = dict(persisted)
    live_by_label = dict(live)
    persisted_labels = [label for label, _ in persisted]
    live_labels = [label for label, _ in live]
    expected_camera_count = int(contract["expected_camera_count"])
    expected_component_count = int(contract["expected_transform_component_count"])
    significant_digits = int(contract["transform_equivalence_significant_digits"])
    allowed_indices = {int(value) for value in contract["transform_equivalence_allowed_difference_indices"]}
    maximum_delta = float(contract["source_master_equivalence_max_abs_delta"])
    issues = []

    persisted_hash = transform_rows_fingerprint(persisted)
    live_hash = transform_rows_fingerprint(live)
    if persisted_hash != contract["source_master_transform_sha256"]:
        issues.append(
            f"Persisted transform fingerprint={persisted_hash}; "
            f"expected {contract['source_master_transform_sha256']}"
        )
    if live_hash != contract["source_master_live_transform_sha256"]:
        issues.append(
            f"Live transform fingerprint={live_hash}; "
            f"expected {contract['source_master_live_transform_sha256']}"
        )
    if len(persisted) != expected_camera_count or len(live) != expected_camera_count:
        issues.append(
            f"Transform cameras persisted/live={len(persisted)}/{len(live)}; "
            f"expected {expected_camera_count}/{expected_camera_count}"
        )
    if len(persisted_labels) != len(set(persisted_labels)) or len(live_labels) != len(set(live_labels)):
        issues.append("Persisted or live transform camera labels are duplicated")
    if persisted_labels != live_labels:
        issues.append("Persisted and live transform camera labels differ")

    persisted_components = sum(len(values) for _, values in persisted)
    live_components = sum(len(values) for _, values in live)
    if persisted_components != expected_component_count or live_components != expected_component_count:
        issues.append(
            f"Transform components persisted/live={persisted_components}/{live_components}; "
            f"expected {expected_component_count}/{expected_component_count}"
        )

    different_indices = set()
    different_values = 0
    exact_equal_values = 0
    max_abs_delta = 0.0
    non_finite = False
    for label in sorted(set(persisted_by_label) & set(live_by_label)):
        saved_values = persisted_by_label[label]
        api_values = live_by_label[label]
        if len(saved_values) != len(api_values):
            issues.append(
                f"{label}: persisted/live transform lengths={len(saved_values)}/{len(api_values)}"
            )
            continue
        for index, (saved, api) in enumerate(zip(saved_values, api_values)):
            if not math.isfinite(saved) or not math.isfinite(api):
                non_finite = True
                continue
            delta = abs(api - saved)
            if delta == 0:
                exact_equal_values += 1
                continue
            different_values += 1
            different_indices.add(index)
            max_abs_delta = max(max_abs_delta, delta)
    if non_finite:
        issues.append("Persisted or live transforms contain non-finite values")
    unexpected_indices = sorted(different_indices - allowed_indices)
    if unexpected_indices:
        issues.append(f"Transform differences outside reviewed rotation indices: {unexpected_indices}")
    if max_abs_delta > maximum_delta:
        issues.append(
            f"Maximum persisted/live transform delta={max_abs_delta!r}; "
            f"reviewed maximum is {maximum_delta!r}"
        )

    persisted_common_hash = transform_rows_fingerprint(
        significant_transform_rows(persisted, significant_digits)
    )
    live_common_hash = transform_rows_fingerprint(significant_transform_rows(live, significant_digits))
    expected_common_hash = contract["source_master_common_12sig_transform_sha256"]
    if persisted_common_hash != expected_common_hash or live_common_hash != expected_common_hash:
        issues.append(
            f"Common {significant_digits}-significant-digit hash persisted/live="
            f"{persisted_common_hash}/{live_common_hash}; expected {expected_common_hash}"
        )

    return {
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
        "persisted_transform_sha256": persisted_hash,
        "live_transform_sha256": live_hash,
        "common_significant_digit_transform_sha256": expected_common_hash if not issues else None,
        "persisted_common_transform_sha256": persisted_common_hash,
        "live_common_transform_sha256": live_common_hash,
        "significant_digits": significant_digits,
        "camera_count_persisted": len(persisted),
        "camera_count_live": len(live),
        "component_count_persisted": persisted_components,
        "component_count_live": live_components,
        "labels_exactly_equal": persisted_labels == live_labels,
        "exact_equal_values": exact_equal_values,
        "different_values": different_values,
        "different_indices": sorted(different_indices),
        "allowed_difference_indices": sorted(allowed_indices),
        "maximum_absolute_delta": max_abs_delta,
        "maximum_allowed_absolute_delta": maximum_delta,
    }


def sha256_file(path):
    digest = sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _children(element, name):
    return [child for child in list(element) if _local(child.tag) == name]


def _child(element, name):
    matches = _children(element, name)
    return matches[0] if matches else None


def _text(element, name, default=None):
    child = _child(element, name)
    if child is None or child.text is None:
        return default
    value = child.text.strip()
    return value if value else default


def _iter(root, name):
    return (element for element in root.iter() if _local(element.tag) == name)


def _descendant(element, name):
    return next((item for item in element.iter() if _local(item.tag) == name), None)


def _required_float(element, name, context):
    raw = _text(element, name)
    if raw is None:
        raise ValidationError(f"{context}: missing {name}")
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValidationError(f"{context}: invalid {name}={raw!r}") from exc
    if not math.isfinite(value):
        raise ValidationError(f"{context}: non-finite {name}")
    return value


def _last_nonempty_record(root, record_name, fields):
    selected = None
    for record in _iter(root, record_name):
        candidate = {field: _text(record, field) for field in fields}
        if any(candidate.values()):
            selected = candidate
    return selected or {field: None for field in fields}


def parse_jobxml(path, point_map, rules):
    """Parse and strictly validate the control information used by a campaign."""
    path = Path(path).resolve()
    if not path.is_file():
        raise ValidationError(f"JobXML not found: {path}")

    root = ET.parse(path).getroot()
    expected_ids = set(str(key) for key in point_map)
    coordinate = _last_nonempty_record(
        root, "CoordinateSystemRecord", ("SystemName", "ZoneName", "DatumName")
    )
    coordinate_text = " | ".join(value or "" for value in coordinate.values())

    geoid = None
    vertical_type = None
    for record in _iter(root, "VerticalAdjustmentRecord"):
        kind = _text(record, "Type")
        name = _text(record, "GeoidName")
        if kind == "GeoidModel" and name:
            vertical_type, geoid = kind, name

    records = {}
    duplicate_records = set()
    observation_years = set()
    for record in _iter(root, "PointRecord"):
        name = (_text(record, "Name") or "").strip()
        if name not in expected_ids:
            continue
        if name in records:
            duplicate_records.add(name)
        timestamp = record.attrib.get("TimeStamp")
        if timestamp:
            try:
                observation_years.add(datetime.fromisoformat(timestamp).year)
            except ValueError as exc:
                raise ValidationError(f"Point {name}: invalid TimeStamp={timestamp!r}") from exc
        precision = _child(record, "Precision")
        quality = _child(record, "QualityControl1")
        warnings = _descendant(record, "Warnings")
        records[name] = {
            "deleted": (_text(record, "Deleted", "false") or "false").lower() == "true",
            "survey_method": _text(record, "SurveyMethod"),
            "horizontal_precision": None if precision is None else _required_float(precision, "Horizontal", f"Point {name} precision"),
            "vertical_precision": None if precision is None else _required_float(precision, "Vertical", f"Point {name} precision"),
            "satellites": None if quality is None or _text(quality, "NumberOfSatellites") is None else int(_text(quality, "NumberOfSatellites")),
            "pdop": None if quality is None or _text(quality, "PDOP") is None else float(_text(quality, "PDOP")),
            "poor_precision_warning": None if warnings is None else _text(warnings, "PoorPrecisionsWarning"),
            "timestamp": timestamp,
        }

    reductions = {}
    reductions_sections = list(_iter(root, "Reductions"))
    if not reductions_sections:
        raise ValidationError("JobXML has no Reductions section")
    for point in _children(reductions_sections[-1], "Point"):
        name = (_text(point, "Name") or "").strip()
        if name not in expected_ids:
            continue
        if name in reductions:
            raise ValidationError(f"Duplicate reduction for point {name}")
        wgs = _child(point, "WGS84")
        grid = _child(point, "Grid")
        if wgs is None or grid is None:
            raise ValidationError(f"Point {name}: missing WGS84 or Grid reduction")
        reductions[name] = {
            "latitude": _required_float(wgs, "Latitude", f"Point {name} WGS84"),
            "longitude": _required_float(wgs, "Longitude", f"Point {name} WGS84"),
            "h_ellipsoid": _required_float(wgs, "Height", f"Point {name} WGS84"),
            "northing": _required_float(grid, "North", f"Point {name} Grid"),
            "easting": _required_float(grid, "East", f"Point {name} Grid"),
            "H_orthometric": _required_float(grid, "Elevation", f"Point {name} Grid"),
        }

    issues = []
    if duplicate_records:
        issues.append(f"duplicate PointRecord ids: {sorted(duplicate_records)}")
    for name in sorted(expected_ids):
        if name not in records:
            issues.append(f"point {name}: PointRecord missing")
            continue
        if name not in reductions:
            issues.append(f"point {name}: reduction missing")
            continue
        record = records[name]
        if record["deleted"]:
            issues.append(f"point {name}: marked Deleted")
        required_method = rules.get("required_survey_method")
        if required_method and record["survey_method"] != required_method:
            issues.append(f"point {name}: SurveyMethod={record['survey_method']!r}, expected {required_method!r}")
        if record["horizontal_precision"] is None or record["vertical_precision"] is None:
            issues.append(f"point {name}: precision missing")
        elif record["horizontal_precision"] <= 0 or record["vertical_precision"] <= 0:
            issues.append(f"point {name}: precision must be positive")
        if rules.get("require_no_poor_precision_warning") and record["poor_precision_warning"] not in (None, "No"):
            issues.append(f"point {name}: PoorPrecisionsWarning={record['poor_precision_warning']!r}")

    expected_geoid = rules.get("expected_geoid")
    if expected_geoid and geoid != expected_geoid:
        issues.append(f"geoid={geoid!r}, expected {expected_geoid!r}")
    if vertical_type != "GeoidModel":
        issues.append(f"vertical adjustment={vertical_type!r}, expected 'GeoidModel'")
    for token in rules.get("expected_coordinate_tokens", []):
        if token.lower() not in coordinate_text.lower():
            issues.append(f"coordinate system lacks token {token!r}: {coordinate_text}")
    expected_year = rules.get("expected_survey_year")
    if expected_year is not None and observation_years != {int(expected_year)}:
        issues.append(f"observation years={sorted(observation_years)}, expected [{expected_year}]")

    if issues:
        raise ValidationError("Invalid JobXML:\n- " + "\n- ".join(issues))

    points = {}
    for job_id, mapping in point_map.items():
        job_id = str(job_id)
        point = dict(reductions[job_id])
        point.update(records[job_id])
        point.update({
            "job_id": job_id,
            "label": mapping["label"],
            "role": mapping["role"],
            "geoid_separation": point["h_ellipsoid"] - point["H_orthometric"],
        })
        points[job_id] = point

    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "job_name": root.attrib.get("jobName"),
        "jobxml_version": root.attrib.get("version"),
        "coordinate_system": coordinate,
        "coordinate_system_text": coordinate_text,
        "vertical_adjustment": vertical_type,
        "geoid": geoid,
        "observation_years": sorted(observation_years),
        "points": points,
    }


_XMP_ATTRIBUTE = re.compile(r'([A-Za-z0-9_-]+):([A-Za-z0-9_-]+)="([^"]*)"')


def read_dji_xmp(path):
    path = Path(path)
    with path.open("rb") as stream:
        payload = stream.read(1024 * 1024)
    start = payload.find(b"<x:xmpmeta")
    end = payload.find(b"</x:xmpmeta>", start)
    if start < 0 or end < 0:
        raise ValidationError(f"{path.name}: embedded XMP packet not found in first MiB")
    text = payload[start:end + len(b"</x:xmpmeta>")].decode("utf-8", "replace")
    return {f"{prefix}:{name}": value for prefix, name, value in _XMP_ATTRIBUTE.findall(text)}


def validate_p1_xmp(paths, camera_rules, median_ground_h=None):
    rows = []
    issues = []
    max_sigma = float(camera_rules.get("maximum_position_sigma_m", 0.5))
    for raw_path in paths:
        path = Path(raw_path)
        try:
            xmp = read_dji_xmp(path)
            required = {
                "drone-dji:GpsLatitude", "drone-dji:GpsLongitude",
                "drone-dji:AbsoluteAltitude", "drone-dji:RtkStdLon",
                "drone-dji:RtkStdLat", "drone-dji:RtkStdHgt",
            }
            missing = sorted(required - set(xmp))
            if missing:
                raise ValidationError(f"missing XMP fields {missing}")
            row = {
                "file": str(path.resolve()),
                "gps_status": xmp.get("drone-dji:GpsStatus"),
                "altitude_type": xmp.get("drone-dji:AltitudeType"),
                "rtk_flag": int(xmp.get("drone-dji:RtkFlag", "-1")),
                "surveying_mode": int(xmp.get("drone-dji:SurveyingMode", "-1")),
                "latitude": float(xmp["drone-dji:GpsLatitude"]),
                "longitude": float(xmp["drone-dji:GpsLongitude"]),
                "h_ellipsoid": float(xmp["drone-dji:AbsoluteAltitude"]),
                "sigma_lon": float(xmp["drone-dji:RtkStdLon"]),
                "sigma_lat": float(xmp["drone-dji:RtkStdLat"]),
                "sigma_h": float(xmp["drone-dji:RtkStdHgt"]),
            }
            if camera_rules.get("require_p1_rtk_fixed") and (row["gps_status"] != "Normal" or row["rtk_flag"] != 50):
                issues.append(f"{path.name}: RTK is not fixed/normal")
            if camera_rules.get("require_surveying_mode") and row["surveying_mode"] != 1:
                issues.append(f"{path.name}: SurveyingMode is not 1")
            if row["altitude_type"] != "RtkAlt":
                issues.append(f"{path.name}: AltitudeType={row['altitude_type']!r}")
            sigmas = (row["sigma_lon"], row["sigma_lat"], row["sigma_h"])
            if any(not math.isfinite(value) or value <= 0 or value > max_sigma for value in sigmas):
                issues.append(f"{path.name}: invalid/excessive RTK sigma {sigmas}")
            if median_ground_h is not None:
                agl = row["h_ellipsoid"] - float(median_ground_h)
                row["ellipsoidal_height_difference_to_ground_m"] = agl
                lower = float(camera_rules.get("minimum_camera_agl_m", 2.0))
                upper = float(camera_rules.get("maximum_camera_agl_m", 250.0))
                if not lower <= agl <= upper:
                    issues.append(f"{path.name}: camera-ground ellipsoidal difference {agl:.3f} m outside configured range")
            rows.append(row)
        except Exception as exc:
            issues.append(f"{path.name}: {exc}")

    if issues:
        raise ValidationError("Invalid P1 XMP:\n- " + "\n- ".join(issues[:50]))
    return rows
