"""YAML configuration parser for fds_param.

Parses the study configuration, validates fields, and generates the
full parameter matrix (Cartesian product of sweep/list parameters).
"""

import itertools
import os

import yaml
import numpy as np


def load_config(path):
    """Load and validate a fds_param YAML configuration file.

    Args:
        path: Path to the YAML configuration file.

    Returns:
        Validated configuration dict.

    Raises:
        FileNotFoundError: If *path* does not exist.
        ValueError: If required fields are missing or invalid.
    """
    path = os.path.expanduser(path)
    with open(path, "r") as fh:
        cfg = yaml.safe_load(fh)

    _validate(cfg, path)

    # Resolve paths relative to the config file location
    config_dir = os.path.dirname(os.path.abspath(path))
    cfg["template"] = _resolve_path(cfg["template"], config_dir)
    cfg["fds_command"] = os.path.expanduser(cfg["fds_command"])
    cfg["output_dir"] = _resolve_path(cfg["output_dir"], config_dir)

    cfg.setdefault("parallel_runs", 1)
    cfg.setdefault("study", {"type": "parametric"})

    return cfg


def _resolve_path(p, base):
    p = os.path.expanduser(p)
    if not os.path.isabs(p):
        return os.path.join(base, p)
    return p


def _validate(cfg, path):
    for field in ("template", "fds_command", "parameters", "objectives"):
        if field not in cfg:
            raise ValueError(f"Missing required field '{field}' in {path}")

    for name, pdef in cfg["parameters"].items():
        ptype = pdef.get("type")
        if ptype not in ("sweep", "list", "fixed", "optimize"):
            raise ValueError(
                f"Parameter '{name}': type must be sweep, list, fixed, or optimize "
                f"(got '{ptype}')"
            )
        if ptype == "sweep":
            for k in ("min", "max", "steps"):
                if k not in pdef:
                    raise ValueError(f"Parameter '{name}' (sweep): missing '{k}'")
        elif ptype == "list":
            if "values" not in pdef:
                raise ValueError(f"Parameter '{name}' (list): missing 'values'")
        elif ptype == "fixed":
            if "value" not in pdef:
                raise ValueError(f"Parameter '{name}' (fixed): missing 'value'")
        elif ptype == "optimize":
            for k in ("min", "max"):
                if k not in pdef:
                    raise ValueError(f"Parameter '{name}' (optimize): missing '{k}'")

    for i, obj in enumerate(cfg["objectives"]):
        if "device_id" not in obj:
            raise ValueError(f"Objective {i}: missing 'device_id'")
        qty = obj.get("quantity")
        if qty not in ("max", "min", "mean", "final", "time_to_threshold"):
            raise ValueError(
                f"Objective {i}: quantity must be max/min/mean/final/time_to_threshold "
                f"(got '{qty}')"
            )
        if qty == "time_to_threshold" and "threshold" not in obj:
            raise ValueError(f"Objective {i}: time_to_threshold requires 'threshold'")


def expand_parameter(pdef):
    """Expand a single parameter definition into a list of values.

    Args:
        pdef: Parameter definition dict with 'type' and type-specific keys.

    Returns:
        List of numeric values.
    """
    ptype = pdef["type"]
    if ptype == "sweep":
        return list(np.linspace(pdef["min"], pdef["max"], pdef["steps"]))
    elif ptype == "list":
        return list(pdef["values"])
    elif ptype == "fixed":
        return [pdef["value"]]
    elif ptype == "optimize":
        # For optimization, the initial guess is the midpoint
        return [pdef.get("initial", (pdef["min"] + pdef["max"]) / 2)]
    return []


def build_parameter_matrix(parameters):
    """Build the Cartesian product of all parameter values.

    Args:
        parameters: Dict of parameter definitions from the config.

    Returns:
        Tuple of (param_names, list_of_param_dicts) where each dict maps
        parameter names to a specific combination of values.
    """
    names = sorted(parameters.keys())
    value_lists = [expand_parameter(parameters[n]) for n in names]
    combos = list(itertools.product(*value_lists))

    result = []
    for combo in combos:
        result.append(dict(zip(names, combo)))

    return names, result


def get_optimize_params(parameters):
    """Return names and bounds for parameters with type='optimize'.

    Args:
        parameters: Dict of parameter definitions from the config.

    Returns:
        Tuple of (list_of_names, list_of_(min,max)_bounds).
    """
    names = []
    bounds = []
    for name in sorted(parameters.keys()):
        pdef = parameters[name]
        if pdef["type"] == "optimize":
            names.append(name)
            bounds.append((pdef["min"], pdef["max"]))
    return names, bounds


def get_fixed_params(parameters):
    """Return a dict of fixed and non-optimize parameter values.

    For parametric studies these are combined with swept values.
    For optimization these provide the constant background.

    Args:
        parameters: Dict of parameter definitions from the config.

    Returns:
        Dict mapping parameter names to their fixed/default values.
    """
    result = {}
    for name, pdef in parameters.items():
        if pdef["type"] == "fixed":
            result[name] = pdef["value"]
    return result
