"""Pure-Python contracts and metrics for controlled optimization experiments."""

import math


OPTIMIZATION_CONTRACT = {
    "fit_f": True,
    "fit_cx": True,
    "fit_cy": True,
    "fit_b1": False,
    "fit_b2": False,
    "fit_k1": True,
    "fit_k2": True,
    "fit_k3": True,
    "fit_k4": False,
    "fit_p1": True,
    "fit_p2": True,
    "fit_corrections": False,
    "adaptive_fitting": False,
    "tiepoint_covariance": True,
}

CALIBRATION_PARAMETERS = ("f", "cx", "cy", "b1", "b2", "k1", "k2", "k3", "k4", "p1", "p2", "p3", "p4")
FIXED_TOLERANCE_CONTRACT = {name: 1e-12 for name in ("b1", "b2", "k4", "p3", "p4")}
TRANSFORM_EQUIVALENCE_CONTRACT = {
    "source_master_transform_sha256": "49925af981c6a0076cb5f43490d8b4b344864ebe71a2d0407cb4ec3b2fe24d10",
    "source_master_live_transform_sha256": "e75f994cfff3a0a286ee7e3283b4ae2f202ce7869ee4e42c3b4caf0107831520",
    "source_master_common_12sig_transform_sha256": "53c4790ff878b4b5cc2e132e87f4df5394beba4093bbf928ddfb8ba25b3cc0d1",
    "source_master_equivalence_max_abs_delta": 1e-15,
    "transform_equivalence_significant_digits": 12,
    "transform_equivalence_allowed_difference_indices": [0, 1, 2, 4, 5, 6, 8, 9, 10],
    "expected_camera_count": 43,
    "expected_transform_component_count": 688,
}


def require_approved_experiment(global_config, run_id):
    experiments = global_config.get("optimization_experiments", {})
    if run_id not in experiments:
        raise RuntimeError(f"Unknown optimization run_id: {run_id!r}")
    experiment = experiments[run_id]
    validate_experiment_contract(experiment)
    if experiment.get("review_status") != "APPROVED":
        raise RuntimeError(
            f"Experiment {run_id!r} is {experiment.get('review_status')!r}; "
            "geomatic review must set review_status=APPROVED before execution"
        )
    validate_optimization_contract(global_config.get("optimization", {}))
    return experiment


def validate_experiment_contract(experiment):
    tolerances = experiment.get("fixed_parameter_absolute_tolerance", {})
    if set(tolerances) != set(FIXED_TOLERANCE_CONTRACT):
        raise RuntimeError(
            f"Fixed tolerance keys differ from the reviewed contract: {sorted(tolerances)}"
        )
    for name, expected in FIXED_TOLERANCE_CONTRACT.items():
        value = float(tolerances[name])
        if not math.isfinite(value) or value < 0 or value != expected:
            raise RuntimeError(
                f"Tolerance {name}={value!r}; reviewed finite non-negative value is {expected!r}"
            )
    change_tolerance = float(experiment.get("calibration_change_detection_absolute_tolerance", float("nan")))
    if not math.isfinite(change_tolerance) or change_tolerance < 0 or change_tolerance != 1e-12:
        raise RuntimeError(
            "calibration_change_detection_absolute_tolerance must equal the reviewed value 1e-12"
        )
    if experiment.get("allowed_calibration_parameters") != ["f", "cx", "cy", "k1", "k2", "k3", "p1", "p2"]:
        raise RuntimeError("Allowed calibration parameters differ from the reviewed contract")
    if experiment.get("fixed_calibration_parameters") != ["b1", "b2", "k4"]:
        raise RuntimeError("Fixed calibration parameters differ from the reviewed contract")
    if experiment.get("nonadjustable_calibration_parameters_audited") != ["p3", "p4"]:
        raise RuntimeError("Audited non-adjustable parameters differ from the reviewed contract")
    if experiment.get("reviewed_metashape_version") != "2.3.1":
        raise RuntimeError("Reviewed Metashape version must be exactly '2.3.1'")
    for name, expected in TRANSFORM_EQUIVALENCE_CONTRACT.items():
        if experiment.get(name) != expected:
            raise RuntimeError(
                f"Transform equivalence field {name}={experiment.get(name)!r}; "
                f"reviewed value is {expected!r}"
            )
    return experiment


def validate_metashape_version(actual, expected):
    actual_text = str(actual)
    if actual_text != str(expected):
        raise RuntimeError(f"Metashape version={actual_text!r}; reviewed version is {expected!r}")
    return actual_text


def validate_optimization_contract(parameters):
    if parameters != OPTIMIZATION_CONTRACT:
        missing = sorted(set(OPTIMIZATION_CONTRACT) - set(parameters))
        extra = sorted(set(parameters) - set(OPTIMIZATION_CONTRACT))
        changed = {
            key: {"expected": value, "actual": parameters.get(key)}
            for key, value in OPTIMIZATION_CONTRACT.items()
            if parameters.get(key) != value
        }
        raise RuntimeError(
            f"Optimization parameters violate the fixed-model contract: "
            f"missing={missing}, extra={extra}, changed={changed}"
        )
    return dict(parameters)


def residual_statistics(rows):
    """Return axis, horizontal and 3-D bias/RMSE without averaging magnitudes."""
    if not rows:
        return {"count": 0, "bias_m": None, "rmse_m": None}
    axes = ("x", "y", "z")
    values = {axis: [float(row[axis]) for row in rows] for axis in axes}
    for axis_values in values.values():
        if any(not math.isfinite(value) for value in axis_values):
            raise ValueError("Residuals must be finite")
    count = len(rows)
    bias = {axis: sum(values[axis]) / count for axis in axes}
    rmse = {
        axis: math.sqrt(sum(value * value for value in values[axis]) / count)
        for axis in axes
    }
    rmse["xy"] = math.sqrt(sum(x * x + y * y for x, y in zip(values["x"], values["y"])) / count)
    rmse["3d"] = math.sqrt(
        sum(x * x + y * y + z * z for x, y, z in zip(values["x"], values["y"], values["z"])) / count
    )
    return {"count": count, "bias_m": bias, "rmse_m": rmse}


def reprojection_statistics(errors_px):
    values = [float(value) for value in errors_px]
    if any(not math.isfinite(value) or value < 0 for value in values):
        raise ValueError("Reprojection errors must be finite and non-negative")
    if not values:
        return {"count": 0, "mean_px": None, "rms_px": None, "maximum_px": None}
    return {
        "count": len(values),
        "mean_px": sum(values) / len(values),
        "rms_px": math.sqrt(sum(value * value for value in values) / len(values)),
        "maximum_px": max(values),
    }


def compare_calibrations(before, after, allowed, fixed, nonadjustable, tolerances, change_tolerance):
    """Compare snapshots and fail closed on sensor/parameter or fixed-value changes."""
    issues = []
    before_keys = [row.get("sensor_key") for row in before]
    after_keys = [row.get("sensor_key") for row in after]
    if None in before_keys or len(before_keys) != len(set(before_keys)):
        issues.append(f"Before-calibration sensor keys are missing or duplicated: {before_keys}")
    if None in after_keys or len(after_keys) != len(set(after_keys)):
        issues.append(f"After-calibration sensor keys are missing or duplicated: {after_keys}")
    before_by_sensor = {row.get("sensor_key"): row for row in before}
    after_by_sensor = {row.get("sensor_key"): row for row in after}
    if set(before_by_sensor) != set(after_by_sensor):
        issues.append(
            f"Sensor set changed: before={sorted(before_by_sensor)}, after={sorted(after_by_sensor)}"
        )

    fixed_or_nonadjustable = set(fixed) | set(nonadjustable)
    expected = set(allowed) | fixed_or_nonadjustable
    if expected != set(CALIBRATION_PARAMETERS):
        issues.append(
            f"Calibration contract does not cover exactly {list(CALIBRATION_PARAMETERS)}"
        )

    rows = []
    inferred_changed = set()
    for sensor in sorted(set(before_by_sensor) & set(after_by_sensor)):
        if before_by_sensor[sensor].get("sensor") != after_by_sensor[sensor].get("sensor"):
            issues.append(
                f"Sensor key {sensor}: label changed from "
                f"{before_by_sensor[sensor].get('sensor')!r} to {after_by_sensor[sensor].get('sensor')!r}"
            )
        before_parameters = before_by_sensor[sensor].get("parameters", {})
        after_parameters = after_by_sensor[sensor].get("parameters", {})
        if set(before_parameters) != set(CALIBRATION_PARAMETERS):
            issues.append(f"{sensor}: incomplete before-calibration parameter set")
        if set(after_parameters) != set(CALIBRATION_PARAMETERS):
            issues.append(f"{sensor}: incomplete after-calibration parameter set")
        for name in CALIBRATION_PARAMETERS:
            if name not in before_parameters or name not in after_parameters:
                continue
            old = float(before_parameters[name])
            new = float(after_parameters[name])
            delta = new - old
            if not all(math.isfinite(value) for value in (old, new, delta)):
                issues.append(f"{sensor}/{name}: non-finite calibration value")
                continue
            changed = abs(delta) > float(change_tolerance)
            if changed:
                inferred_changed.add(name)
            tolerance = None
            within_tolerance = None
            if name in fixed_or_nonadjustable:
                if name not in tolerances:
                    issues.append(f"{sensor}/{name}: fixed-parameter tolerance missing")
                else:
                    tolerance = float(tolerances[name])
                    within_tolerance = abs(delta) <= tolerance
                    if not within_tolerance:
                        issues.append(
                            f"{sensor}/{name}: fixed parameter changed by {delta!r}; "
                            f"absolute tolerance is {tolerance!r}"
                        )
            elif name not in allowed:
                issues.append(f"{sensor}/{name}: parameter is not authorized")
            rows.append({
                "sensor_key": sensor,
                "sensor": before_by_sensor[sensor].get("sensor"),
                "parameter": name,
                "before": old,
                "after": new,
                "delta": delta,
                "authorized_to_vary": name in allowed,
                "fixed_tolerance": tolerance,
                "within_fixed_tolerance": within_tolerance,
            })
    return {
        "rows": rows,
        "inferred_changed_parameters": sorted(inferred_changed),
        "api_effective_parameter_set_available": False,
        "issues": issues,
    }
