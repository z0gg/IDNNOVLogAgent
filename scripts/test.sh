#!/bin/sh
set -eu
PYTHONPATH=src python3 -m unittest discover -v
node --test repository/test/worker.test.mjs
python3 /home/z0gg/.hermes/skills/devops/synology-idnnov-log-agent-spk/scripts/validate_spk.py artifacts/IDNNOVLogAgent-1.0.0-1001-geminilake.spk
