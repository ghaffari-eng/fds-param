"""Optimization wrapper using scipy.optimize.

Wraps FDS simulations as an objective function for scipy optimizers.
"""

import csv
import os

from scipy.optimize import minimize, differential_evolution

from . import template, runner, collector


def optimize(cfg):
    """Run an optimization study.

    Args:
        cfg: Validated configuration dict (from config.load_config).

    Returns:
        Dict with keys 'optimal_params', 'optimal_value', 'log_path'.
    """
    from .config import get_optimize_params, get_fixed_params

    opt_names, bounds = get_optimize_params(cfg["parameters"])
    fixed = get_fixed_params(cfg["parameters"])
    objectives = cfg["objectives"]
    study = cfg["study"]

    # Determine which objective to optimize
    obj_device = study.get("objective", objectives[0]["device_id"])
    obj_quantity = study.get("objective_quantity", objectives[0]["quantity"])
    obj_threshold = study.get("objective_threshold")
    do_minimize = study.get("minimize", True)
    method = study.get("method", "Nelder-Mead")

    output_dir = cfg["output_dir"]
    os.makedirs(output_dir, exist_ok=True)

    log_path = os.path.join(output_dir, "optimization_log.csv")
    eval_count = [0]

    # Write log header
    with open(log_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["eval"] + opt_names + ["objective"])

    def objective_function(x):
        eval_count[0] += 1
        run_id = f"opt_{eval_count[0]:04d}"

        # Build full parameter set
        params = dict(fixed)
        for name, val in zip(opt_names, x):
            params[name] = float(val)

        # Generate and run
        fds_path = template.generate_input_file(
            cfg["template"], params, run_id, output_dir
        )
        run_results = runner.run_all(
            cfg["fds_command"], [(fds_path, run_id)], parallel_runs=1
        )

        # Collect
        obj_def = {
            "device_id": obj_device,
            "quantity": obj_quantity,
        }
        if obj_threshold is not None:
            obj_def["threshold"] = obj_threshold

        collected = collector.collect_results(output_dir, [run_id], [obj_def])
        run_data = collected.get(run_id, {})

        # Get the scalar value
        key = f"{obj_device}_{obj_quantity}"
        if obj_quantity == "time_to_threshold" and obj_threshold is not None:
            key = f"{obj_device}_time_to_{obj_threshold}"

        val = run_data.get(key)
        if val is None:
            val = 1e12  # penalty for failed runs

        scalar = val if do_minimize else -val

        # Log
        with open(log_path, "a", newline="") as fh:
            w = csv.writer(fh)
            w.writerow([eval_count[0]] + [f"{v:.6g}" for v in x] + [val])

        print(f"  Eval {eval_count[0]}: {dict(zip(opt_names, x))} -> {key} = {val}")
        return scalar

    # Initial guess: midpoints
    x0 = [(b[0] + b[1]) / 2 for b in bounds]

    print(f"\nStarting optimization ({method}) over {opt_names}...")

    if method.lower() == "differential_evolution":
        result = differential_evolution(objective_function, bounds)
    else:
        result = minimize(
            objective_function, x0, method=method,
            bounds=bounds if method in ("L-BFGS-B", "TNC", "SLSQP") else None,
        )

    optimal_params = dict(zip(opt_names, result.x))
    optimal_value = result.fun if do_minimize else -result.fun

    print(f"\nOptimization complete after {eval_count[0]} evaluations.")
    print(f"  Optimal parameters: {optimal_params}")
    print(f"  Optimal objective value: {optimal_value}")

    return {
        "optimal_params": optimal_params,
        "optimal_value": optimal_value,
        "log_path": log_path,
        "evaluations": eval_count[0],
    }
