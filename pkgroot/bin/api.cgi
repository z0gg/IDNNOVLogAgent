#!/bin/sh
set -eu
PKG_ROOT="/var/packages/IDNNOVLogAgent/target"
export PYTHONPATH="$PKG_ROOT/lib"
exec "$PKG_ROOT/bin/py" -m idnnov_agent.cgi
