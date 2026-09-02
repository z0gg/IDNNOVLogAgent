#!/bin/sh
set -eu
export PYTHONPATH="${SYNOPKG_PKGDEST:?}/lib"
exec /var/packages/Python3/target/usr/local/bin/python3 -m idnnov_agent.cgi
