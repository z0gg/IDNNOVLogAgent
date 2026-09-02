"""Generate the initial configuration from persisted settings."""
import json, os
from pathlib import Path
from .config import render_fluent_bit

def main():
    root=Path(os.environ["SYNOPKG_PKGVAR"]); etc=root/"etc"; pkg=Path(os.environ["SYNOPKG_PKGDEST"])
    settings=json.loads((etc/"settings.json").read_text()); token=(etc/"token").read_text() if (etc/"token").is_file() else None
    candidate=etc/"fluent-bit.conf.tmp"; candidate.write_text(render_fluent_bit(settings,token,str(root/"buffer"),str(pkg/"etc/parsers.conf"))); candidate.chmod(0o600); os.replace(candidate,etc/"fluent-bit.conf")
if __name__=="__main__": main()
