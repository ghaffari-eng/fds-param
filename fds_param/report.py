"""Results reporting for fds_param.

Generates CSV summaries and console output tables from collected results.
"""

import csv
import os


def write_summary_csv(output_dir, param_names, param_matrix, results, objectives):
    """Write a summary CSV combining parameters and results.

    Args:
        output_dir: Directory to write the summary CSV into.
        param_names: Sorted list of parameter names.
        param_matrix: List of param dicts (one per run).
        results: Dict mapping run_id to objective results dict.
        objectives: List of objective dicts from config.

    Returns:
        Path to the written CSV file.
    """
    obj_keys = _objective_keys(objectives)
    csv_path = os.path.join(output_dir, "summary.csv")

    with open(csv_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        header = ["run_id"] + param_names + obj_keys
        writer.writerow(header)

        for i, params in enumerate(param_matrix, 1):
            run_id = _run_id_from_index(i)
            row = [run_id]
            row += [params.get(n, "") for n in param_names]
            run_results = results.get(run_id, {})
            row += [run_results.get(k, "") for k in obj_keys]
            writer.writerow(row)

    return csv_path


def print_summary(param_names, param_matrix, results, objectives):
    """Print a formatted console summary table.

    Args:
        param_names: Sorted list of parameter names.
        param_matrix: List of param dicts (one per run).
        results: Dict mapping run_id to objective results dict.
        objectives: List of objective dicts from config.
    """
    obj_keys = _objective_keys(objectives)
    all_cols = ["run_id"] + param_names + obj_keys

    # Build rows
    rows = []
    for i, params in enumerate(param_matrix, 1):
        run_id = _run_id_from_index(i)
        row = [run_id]
        row += [_fmt(params.get(n, "")) for n in param_names]
        run_results = results.get(run_id, {})
        row += [_fmt(run_results.get(k, "N/A")) for k in obj_keys]
        rows.append(row)

    # Compute column widths
    widths = [len(c) for c in all_cols]
    for row in rows:
        for j, val in enumerate(row):
            widths[j] = max(widths[j], len(str(val)))

    # Print header
    header_line = "  ".join(str(c).ljust(widths[j]) for j, c in enumerate(all_cols))
    print(f"\n{'=' * len(header_line)}")
    print("PARAMETER STUDY RESULTS")
    print(f"{'=' * len(header_line)}")
    print(header_line)
    print("-" * len(header_line))

    for row in rows:
        print("  ".join(str(v).ljust(widths[j]) for j, v in enumerate(row)))
    print()

    # Identify best runs per objective
    for key in obj_keys:
        best_id = None
        best_val = None
        for i, params in enumerate(param_matrix, 1):
            run_id = _run_id_from_index(i)
            run_results = results.get(run_id, {})
            val = run_results.get(key)
            if val is not None:
                if best_val is None or val > best_val:
                    best_val = val
                    best_id = run_id
        if best_id is not None:
            print(f"  Highest {key}: {best_id} = {_fmt(best_val)}")

    print()


def _objective_keys(objectives):
    """Build column key strings for objectives."""
    keys = []
    for obj in objectives:
        dev = obj["device_id"]
        qty = obj["quantity"]
        thresh = obj.get("threshold")
        if qty == "time_to_threshold" and thresh is not None:
            keys.append(f"{dev}_time_to_{thresh}")
        else:
            keys.append(f"{dev}_{qty}")
    return keys


def _run_id_from_index(i):
    return f"run_{i:03d}"


def _fmt(v):
    """Format a value for display."""
    if v is None or v == "":
        return "N/A"
    if isinstance(v, float):
        return f"{v:.4g}"
    return str(v)
