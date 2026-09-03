"""Generate the effective OpenObserve Fluent Bit configuration from settings."""
import json
import os
from pathlib import Path
from . import persistence
from .config import render_fluent_bit


def main():
    root = Path(os.environ["SYNOPKG_PKGVAR"])
    etc = root / "etc"
    pkg = Path(os.environ["SYNOPKG_PKGDEST"])
    raw = json.loads((etc / "settings.json").read_text())
    # Persists migrations (old generic endpoint/customer/site settings) atomically.
    settings = persistence.save(etc, raw, password_action="preserve")
    password = (etc / "token").read_text() if settings["ingest_user"] and (etc / "token").is_file() else None
    candidate = etc / "fluent-bit.conf.tmp"
    candidate.write_text(render_fluent_bit(settings, password, str(root / "buffer"), str(pkg / "etc/parsers.conf")))
    candidate.chmod(0o600)
    os.replace(candidate, etc / "fluent-bit.conf")


if __name__ == "__main__":
    main()
