"""Results collector for FDS _devc.csv output files.

Reads device output files produced by FDS and extracts requested
statistical quantities (max, min, mean, final, time_to_threshold).
"""

import csv
import os

import numpy as np


def read_devc_csv(path):
    """Parse an FDS _devc.csv file into arrays.

    FDS _devc.csv layout:
        Row 1: units (e.g., s, C, kW, ...)
        Row 2: column headers (Time, device_id_1, device_id_2, ...)
        Row 3+: numeric data

    Args:
        path: Path to the _devc.csv file.

    Returns:
        Tuple of (headers_list, data_dict) where data_dict maps each
        header name to a numpy array of float values.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file cannot be parsed.
    """
    with open(path, "r") as fh:
        reader = csv.reader(fh)
        _units = next(reader)   # row 1: units
        headers = next(reader)  # row 2: column names

    # Clean whitespace from headers
    headers = [h.strip() for h in headers]

    # Read numeric data (skip first 2 rows)
    data = np.genfromtxt(path, delimiter=",", skip_header=2)

    if data.ndim == 1:
        data = data.reshape(1, -1)

    result = {}
    for i, name in enumerate(headers):
        if i < data.shape[1]:
            result[name] = data[:, i]

    return headers, result


def extract_quantity(data, device_id, quantity, threshold=None):
    """Extract a statistical quantity from device data.

    Args:
        data: Dict mapping device names to numpy arrays (from read_devc_csv).
        device_id: The device column name to analyse.
        quantity: One of 'max', 'min', 'mean', 'final', 'time_to_threshold'.
        threshold: Required if quantity is 'time_to_threshold'.

    Returns:
        The scalar result value, or None if the device was not found
        or the threshold was never reached.
    """
    if device_id not in data:
        return None

    values = data[device_id]
    time = data.get("Time")

    if quantity == "max":
        return float(np.max(values))
    elif quantity == "min":
        return float(np.min(values))
    elif quantity == "mean":
        if time is not None and len(time) > 1:
            # Time-weighted mean
            return float(np.trapz(values, time) / (time[-1] - time[0]))
        return float(np.mean(values))
    elif quantity == "final":
        return float(values[-1])
    elif quantity == "time_to_threshold":
        if threshold is None:
            return None
        if time is None:
            return None
        indices = np.where(values >= threshold)[0]
        if len(indices) == 0:
            return None  # threshold never reached
        return float(time[indices[0]])
    return None


def collect_results(output_dir, run_ids, objectives):
    """Collect results from all completed runs.

    Args:
        output_dir: Base output directory containing run subdirectories.
        run_ids: List of run_id strings.
        objectives: List of objective dicts from the config.

    Returns:
        Dict mapping run_id to a dict of objective results.
        Each objective result is keyed by '{device_id}_{quantity}'.
    """
    all_results = {}

    for run_id in run_ids:
        devc_path = os.path.join(output_dir, run_id, f"{run_id}_devc.csv")

        if not os.path.exists(devc_path):
            print(f"  Warning: No _devc.csv found for {run_id}")
            all_results[run_id] = {}
            continue

        try:
            _headers, data = read_devc_csv(devc_path)
        except Exception as e:
            print(f"  Warning: Could not parse _devc.csv for {run_id}: {e}")
            all_results[run_id] = {}
            continue

        run_results = {}
        for obj in objectives:
            dev = obj["device_id"]
            qty = obj["quantity"]
            thresh = obj.get("threshold")
            key = f"{dev}_{qty}"
            if qty == "time_to_threshold" and thresh is not None:
                key = f"{dev}_time_to_{thresh}"
            run_results[key] = extract_quantity(data, dev, qty, thresh)

        all_results[run_id] = run_results

    return all_results
