#!/usr/bin/env bash

set -u

PYTHON_INCLUDE_DIR=$(python -c "from sysconfig import get_paths as gp; print(gp()[\"include\"])")

sh compile_math_utils.sh -I"$PYTHON_INCLUDE_DIR"

sh compile_map_utils.sh -I"$PYTHON_INCLUDE_DIR"