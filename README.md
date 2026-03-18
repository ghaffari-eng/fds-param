# fds_param — FDS Parameter Study and Optimization Tool

A command-line tool for running parametric studies and optimizations with FDS (Fire Dynamics Simulator). It generates multiple FDS input files from a template, runs them in parallel, collects device output results, and reports a summary.

## Requirements

- Python 3.8+
- [PyYAML](https://pypi.org/project/PyYAML/)
- [NumPy](https://pypi.org/project/numpy/)
- [SciPy](https://pypi.org/project/scipy/) (only needed for optimization studies)
- A compiled FDS binary

## Quick Start

```bash
# From any directory containing your config and template files:
PYTHONPATH=/path/to/fds/Utilities/Python:$PYTHONPATH python3 -m fds_param config.yaml
```

## Usage

```bash
# Run a parametric study
python3 -m fds_param config.yaml

# Generate input files only (no FDS execution)
python3 -m fds_param config.yaml --dry-run

# Collect results from a previous run (skip generation and execution)
python3 -m fds_param config.yaml --collect-only

# Show help
python3 -m fds_param --help
```

## Template Files

FDS input template files use double-brace syntax for parameters:

```
&HEAD CHID='{{chid}}', TITLE='My case HRRPUA={{hrrpua}}' /
&MESH IJK={{nx}},{{ny}},{{nz}}, XB=0.0,{{lx}},0.0,{{ly}},0.0,{{lz}} /
&SURF ID='BURNER', HRRPUA={{hrrpua}} /
```

- `{{chid}}` is automatically set to the run ID (e.g., `run_001`)
- All other parameters must be defined in the YAML configuration

## Configuration File

YAML format with these sections:

```yaml
# Path to the FDS template file (relative to config file or absolute)
template: room_fire.fds.template

# Path to the FDS executable
fds_command: ~/firemodels/fds/Build/ompi_gnu_linux/fds_ompi_gnu_linux

# Output directory for all runs
output_dir: ./results

# Number of parallel FDS runs
parallel_runs: 4

# Parameters to vary
parameters:
  hrrpua:
    type: sweep        # linearly spaced values
    min: 500
    max: 2000
    steps: 4           # generates [500, 1000, 1500, 2000]

  k_concrete:
    type: list          # explicit list of values
    values: [0.5, 1.0, 1.5, 2.0]

  mesh_res:
    type: fixed         # constant value across all runs
    value: 10

# What to extract from FDS output
objectives:
  - device_id: T_ceiling     # DEVC ID from the FDS input
    quantity: max             # max, min, mean, final, time_to_threshold

  - device_id: T_ceiling
    quantity: time_to_threshold
    threshold: 200.0          # required for time_to_threshold

# Study type
study:
  type: parametric            # parametric or optimization
```

### Parameter Types

| Type | Description | Required Fields |
|------|-------------|-----------------|
| `sweep` | Linearly spaced values from min to max | `min`, `max`, `steps` |
| `list` | Explicit list of values | `values` |
| `fixed` | Single constant value | `value` |
| `optimize` | Variable to optimize (optimization studies only) | `min`, `max` |

For parametric studies, the tool generates the Cartesian product of all sweep/list parameters.

### Objective Quantities

| Quantity | Description |
|----------|-------------|
| `max` | Maximum value over the simulation |
| `min` | Minimum value over the simulation |
| `mean` | Time-averaged mean |
| `final` | Value at the last timestep |
| `time_to_threshold` | First time the value exceeds the threshold |

## Optimization Studies

For optimization, use `type: optimize` parameters and set the study type:

```yaml
parameters:
  hrrpua:
    type: optimize
    min: 100
    max: 2000

study:
  type: optimization
  method: Nelder-Mead          # or differential_evolution, L-BFGS-B, etc.
  objective: T_ceiling         # device to optimize
  objective_quantity: max      # quantity to optimize
  minimize: true               # true to minimize, false to maximize
```

The optimizer uses `scipy.optimize.minimize` (or `differential_evolution` for global optimization) and logs each evaluation to `optimization_log.csv`.

## Output

### Console Summary

A formatted table showing all runs with parameter values and objective results, plus identification of the best run for each objective.

### Summary CSV

Written to `<output_dir>/summary.csv` with columns for run ID, all parameters, and all objectives.

### Run Directories

Each run gets its own subdirectory under `output_dir`:

```
results/
├── run_001/
│   ├── run_001.fds        # Generated FDS input
│   ├── run_001.log        # FDS stdout
│   ├── run_001.err        # FDS stderr
│   ├── run_001.out        # FDS output file
│   ├── run_001_devc.csv   # Device output (read by collector)
│   └── ...                # Other FDS output files
├── run_002/
│   └── ...
└── summary.csv
```

## Example

See the verification test case in `examples/` for a complete working example.
