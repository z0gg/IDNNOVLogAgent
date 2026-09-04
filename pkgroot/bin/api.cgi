#!/bin/sh
# CGI wrapper for the package UI.
#
# DSM's synoscgi runs package CGIs as root and passes neither the package
# environment (SYNOPKG_PKGDEST/PKGVAR) nor a usable identity, while the
# package data files are owned by the package user with mode 0700. The CGI
# therefore re-derives the package paths, drops to the package user when it
# can (so it shares the Fluent Bit service's file ownership), and defers the
# actual authorization decision to the DSM session user resolved by
# idnnov_agent.qcgi via authenticate.cgi.
PKG_ROOT="/var/packages/IDNNOVLogAgent/target"
PKG_VAR="/var/packages/IDNNOVLogAgent/var"
PKG_USER="idnnovlogagent"

export PYTHONPATH="$PKG_ROOT/lib"
export SYNOPKG_PKGDEST="$PKG_ROOT"
export SYNOPKG_PKGVAR="$PKG_VAR"
export SYNOPKG_PKGNAME="IDNNOVLogAgent"

if [ "$(id -u)" = "0" ] && command -v setpriv >/dev/null 2>&1; then
    exec setpriv --reuid "$PKG_USER" --regid "$PKG_USER" --clear-groups \
        "$PKG_ROOT/bin/py" -m idnnov_agent.qcgi
fi
exec "$PKG_ROOT/bin/py" -m idnnov_agent.qcgi
