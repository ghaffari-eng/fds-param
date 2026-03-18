"""FDS execution engine.

Runs FDS simulations in serial or parallel using multiprocessing.
"""

import os
import subprocess
import sys
from multiprocessing import Pool


def run_single(args):
    """Run a single FDS simulation.

    Args:
        args: Tuple of (fds_command, fds_input_path, run_id).

    Returns:
        Tuple of (run_id, success_bool, message).
    """
    fds_command, fds_input_path, run_id = args
    run_dir = os.path.dirname(fds_input_path)
    fds_file = os.path.basename(fds_input_path)

    stdout_path = os.path.join(run_dir, f"{run_id}.log")
    stderr_path = os.path.join(run_dir, f"{run_id}.err")

    try:
        with open(stdout_path, "w") as fout, open(stderr_path, "w") as ferr:
            result = subprocess.run(
                [fds_command, fds_file],
                cwd=run_dir,
                stdout=fout,
                stderr=ferr,
                timeout=3600,  # 1-hour timeout per run
            )

        # Check for successful completion in stdout log and FDS .out file
        success_msg = "STOP: FDS completed successfully"
        for check_path in [stdout_path, os.path.join(run_dir, f"{run_id}.out")]:
            if os.path.exists(check_path):
                with open(check_path, "r") as fh:
                    if success_msg in fh.read():
                        return (run_id, True, "completed successfully")

        if result.returncode != 0:
            return (run_id, False, f"exited with code {result.returncode}")
        else:
            return (run_id, True, "completed (no explicit success message)")

    except subprocess.TimeoutExpired:
        return (run_id, False, "timed out after 3600s")
    except FileNotFoundError:
        return (run_id, False, f"FDS command not found: {fds_command}")
    except Exception as e:
        return (run_id, False, f"error: {e}")


def run_all(fds_command, input_files, parallel_runs=1):
    """Run multiple FDS simulations, optionally in parallel.

    Args:
        fds_command: Path to the FDS executable.
        input_files: List of (fds_input_path, run_id) tuples.
        parallel_runs: Number of simultaneous runs (default 1).

    Returns:
        Dict mapping run_id to (success_bool, message).
    """
    tasks = [(fds_command, path, rid) for path, rid in input_files]
    total = len(tasks)
    results = {}

    print(f"Running {total} FDS simulation(s) with {parallel_runs} parallel worker(s)...")

    if parallel_runs <= 1:
        for i, task in enumerate(tasks, 1):
            rid = task[2]
            print(f"  [{i}/{total}] Running {rid}...", end=" ", flush=True)
            run_id, success, msg = run_single(task)
            results[run_id] = (success, msg)
            status = "OK" if success else "FAILED"
            print(f"{status} — {msg}")
    else:
        with Pool(processes=parallel_runs) as pool:
            for i, (run_id, success, msg) in enumerate(
                pool.imap_unordered(run_single, tasks), 1
            ):
                results[run_id] = (success, msg)
                status = "OK" if success else "FAILED"
                print(f"  [{i}/{total}] {run_id}: {status} — {msg}")

    n_ok = sum(1 for s, _ in results.values() if s)
    n_fail = total - n_ok
    print(f"\nFinished: {n_ok} succeeded, {n_fail} failed out of {total} total.")

    return results
