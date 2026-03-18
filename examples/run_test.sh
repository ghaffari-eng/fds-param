#!/bin/bash
# Run the fds_param verification test case
#
# Usage: ./run_test.sh
#
# Prerequisites:
#   - FDS binary built at ~/firemodels/fds/Build/ompi_gnu_linux/fds_ompi_gnu_linux
#   - Python 3 with PyYAML, numpy, and scipy installed

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FDS_PARAM_DIR="$(cd "$SCRIPT_DIR/../../../Utilities/Python" && pwd)"

cd "$SCRIPT_DIR"

# Clean previous results
rm -rf fds_param_results

echo "Running fds_param verification test..."
echo "Working directory: $SCRIPT_DIR"
echo ""

python3 -m fds_param param_config.yaml

echo ""
echo "Test complete. Results in: $SCRIPT_DIR/fds_param_results/"
