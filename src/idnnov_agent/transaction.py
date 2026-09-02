"""Atomic validate/apply/health-check/rollback."""
import os
from pathlib import Path

class ApplyError(RuntimeError): pass

def _write(path, data):
    tmp = path.with_name(path.name + ".candidate")
    tmp.write_text(data)
    os.chmod(tmp, 0o600)
    return tmp

def apply_config(current, content, validator, restart, running):
    current = Path(current)
    candidate = _write(current, content)
    if not validator(candidate):
        candidate.unlink(missing_ok=True)
        raise ApplyError("CONFIG_INVALID")
    last_good = current.with_name(current.name + ".last-good")
    previous = current.read_bytes() if current.exists() else None
    if previous is not None:
        last_good.write_bytes(previous)
        os.chmod(last_good, 0o600)
    os.replace(candidate, current)
    if not restart() or not running():
        if previous is not None:
            rollback = _write(current, previous.decode())
            os.replace(rollback, current)
            restart()
            running()
        raise ApplyError("SERVICE_RESTART_FAILED")
    last_good.write_bytes(current.read_bytes())
    os.chmod(last_good, 0o600)
    return True
