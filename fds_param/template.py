"""FDS template parameter substitution engine.

Reads FDS input template files with {{param_name}} placeholders and
generates concrete FDS input files with substituted values.
"""

import os
import re

PARAM_PATTERN = re.compile(r"\{\{(\w+)\}\}")


def find_parameters(template_text):
    """Return the set of parameter names found in a template string.

    Args:
        template_text: Raw template file contents.

    Returns:
        Set of parameter name strings.
    """
    return set(PARAM_PATTERN.findall(template_text))


def substitute(template_text, params):
    """Replace all {{param}} placeholders with concrete values.

    Args:
        template_text: Raw template string.
        params: Dict mapping parameter names to values.

    Returns:
        The rendered FDS input string.

    Raises:
        KeyError: If a placeholder has no corresponding entry in *params*.
    """
    def _replace(match):
        name = match.group(1)
        if name not in params:
            raise KeyError(f"Template parameter '{{{{{name}}}}}' has no value in params")
        value = params[name]
        if isinstance(value, float):
            # Format floats cleanly: drop trailing zeros but keep one decimal
            return f"{value:g}"
        return str(value)

    return PARAM_PATTERN.sub(_replace, template_text)


def generate_input_file(template_path, params, run_id, output_dir):
    """Create an FDS input file from a template with substituted parameters.

    The generated file is placed in *output_dir*/*run_id*/ and the CHID
    namelist value is set to *run_id*.

    Args:
        template_path: Path to the .fds.template file.
        params: Dict of parameter values for this run.
        run_id: Unique identifier for this run (used as CHID and directory name).
        output_dir: Base output directory.

    Returns:
        Path to the generated .fds input file.
    """
    with open(template_path, "r") as fh:
        template_text = fh.read()

    # Inject chid into params so the template can reference {{chid}}
    full_params = dict(params, chid=run_id)
    rendered = substitute(template_text, full_params)

    # Also force-update CHID if it was hardcoded in the template (not a placeholder)
    rendered = re.sub(
        r"CHID\s*=\s*'[^']*'",
        f"CHID='{run_id}'",
        rendered,
    )

    run_dir = os.path.join(output_dir, run_id)
    os.makedirs(run_dir, exist_ok=True)

    fds_path = os.path.join(run_dir, f"{run_id}.fds")
    with open(fds_path, "w") as fh:
        fh.write(rendered)

    return fds_path
