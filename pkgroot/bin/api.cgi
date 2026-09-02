#!/bin/sh
set -eu
PKG_ROOT="/var/packages/IDNNOVLogAgent/target"
export PYTHONPATH="$PKG_ROOT/lib"
PY="$("$PKG_ROOT/bin/py")"
exec "$PY" -m idnnov_agent.cgi
