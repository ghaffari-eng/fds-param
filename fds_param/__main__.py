"""CLI entry point for fds_param.

Usage:
    python -m fds_param config.yaml [--dry-run] [--collect-only]
"""

import argparse
import os
import sys

from . import config, template, runner, collector, report, optimizer


def main():
    parser = argparse.ArgumentParser(
        prog="fds_param",
        description="FDS parameter study and optimization tool",
    )
    parser.add_argument("config_file", help="Path to YAML configuration file")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Generate input files only, do not run FDS",
    )
    parser.add_argument(
        "--collect-only", action="store_true",
        help="Collect results from a previous run (skip generation and execution)",
    )
    args = parser.parse_args()

    # Load configuration
    try:
        cfg = config.load_config(args.config_file)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    study_type = cfg.get("study", {}).get("type", "parametric")

    if study_type == "optimization":
        if args.dry_run or args.collect_only:
            print("Error: --dry-run and --collect-only are not supported for optimization studies.",
                  file=sys.stderr)
            sys.exit(1)
        result = optimizer.optimize(cfg)
        print(f"\nOptimization log written to: {result['log_path']}")
        return

    # --- Parametric study ---
    param_names, param_matrix = config.build_parameter_matrix(cfg["parameters"])
    total = len(param_matrix)
    print(f"Parameter study: {total} run(s) over {len(param_names)} parameter(s)")

    output_dir = cfg["output_dir"]
    os.makedirs(output_dir, exist_ok=True)

    # Generate run IDs
    run_ids = [f"run_{i:03d}" for i in range(1, total + 1)]

    if not args.collect_only:
        # Generate input files
        input_files = []
        for run_id, params in zip(run_ids, param_matrix):
            fds_path = template.generate_input_file(
                cfg["template"], params, run_id, output_dir
            )
            input_files.append((fds_path, run_id))
            print(f"  Generated: {fds_path}")

        if args.dry_run:
            print(f"\nDry run complete. {total} input file(s) generated in {output_dir}/")
            return

        # Run simulations
        run_status = runner.run_all(
            cfg["fds_command"], input_files, cfg.get("parallel_runs", 1)
        )

        # Filter to successful runs for collection
        successful_ids = [rid for rid in run_ids if run_status.get(rid, (False,))[0]]
    else:
        successful_ids = run_ids

    # Collect results
    print("\nCollecting results...")
    results = collector.collect_results(output_dir, successful_ids, cfg["objectives"])

    # Report
    report.print_summary(param_names, param_matrix, results, cfg["objectives"])
    csv_path = report.write_summary_csv(
        output_dir, param_names, param_matrix, results, cfg["objectives"]
    )
    print(f"Summary CSV written to: {csv_path}")


if __name__ == "__main__":
    main()
