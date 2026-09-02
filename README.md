# IDNNOV Log Agent for Synology DSM

Production-oriented SPK source for exactly one v1 target: DS920+, `geminilake`, `x86_64`, DSM 7.3 (minimum build 86009), package `1.0.0-1001`. It exposes a DSM-served UI through `dsmuidir="ui"`; it does not run an application web server.

The package listens for RFC5424 TCP syslog only on `127.0.0.1:5514` and forwards over HTTPS with certificate verification and a 128 MB filesystem queue. Settings live in `/var/packages/IDNNOVLogAgent/etc/settings.json`; the token is a separate mode-0600 file and is never returned to the UI.

## Build and verification

Pinned upstream hashes and the mandatory NAS release gate are documented in `third_party/`. Download and verify the official Synology toolchain and Fluent Bit source, cross-build with the reviewed minimal flags, then:

```sh
SOURCE_DATE_EPOCH=1788230400 python3 scripts/build.py --fluent-bit build/fluent-bit-minimal/bin/fluent-bit
PYTHONPATH=src python3 -m unittest discover -v
node --test repository/test/worker.test.mjs
python3 /home/z0gg/.hermes/skills/devops/synology-idnnov-log-agent-spk/scripts/validate_spk.py artifacts/IDNNOVLogAgent-1.0.0-1001-geminilake.spk
```

Two builds with the same inputs and `SOURCE_DATE_EPOCH` must have identical SHA-256. `artifacts/manifest.json` records payload paths, modes, and sizes.

## Release status

Do not deploy or publish directly from a workstation. The unsigned artifact is a release candidate until installation, DSM UI/session/admin authorization, lifecycle, dynamic linkage, real RFC5424→HTTPS, TLS failure, 128 MB buffer, outage recovery, reboot, and upgrade tests pass on a DS920+ running DSM 7.3. See `third_party/FLUENT_BIT_BLOCKER.md`.

The read-only Cloudflare Worker catalogue in `repository/` filters DSM architecture/build parameters and points only to immutable public GitHub Release assets. Its catalogue remains empty until the release gate passes.
