# IDNNOV Log Agent for Synology DSM

Production-oriented SPK source for Synology NAS using 64-bit Intel or AMD processors on DSM 7.2.2 or newer. Release `1.0.1-1002` targets the following package platforms with one x86-64-baseline binary:

`apollolake avoton braswell broadwell broadwellnk broadwellnkv2 broadwellntbap bromolow cedarview denverton epyc7002 geminilake geminilakenk grantley icelaked kvmx64 purley r1000 r1000nk v1000 v1000nk`

The package exposes a DSM-served UI through `dsmuidir="ui"`; it does not run an application Web server. It listens for RFC5424 TCP syslog only on `127.0.0.1:5514` and forwards over HTTPS with certificate verification and a 128 MB filesystem queue. Settings live in `/var/packages/IDNNOVLogAgent/etc/settings.json`; the token is a separate mode-0600 file and is never returned to the UI.

## Build and verification

Pinned upstream hashes and the mandatory NAS validation gate are documented in `third_party/`. The packaged Fluent Bit executable is ELF x86_64, requires x86-64-baseline, depends dynamically only on `libc` and `libm`, and uses glibc symbols no newer than 2.34. Synology DSM 7.2-72806 toolchains for the supported x86_64 platforms use GCC 12.2/glibc 2.36.

```sh
SOURCE_DATE_EPOCH=1788230400 python3 scripts/build.py --fluent-bit build/fluent-bit-final2/bin/fluent-bit
PYTHONPATH=src python3 -m unittest discover -s tests -v
npm --prefix repository test
python3 /home/z0gg/.hermes/skills/devops/synology-idnnov-log-agent-spk/scripts/validate_spk.py artifacts/IDNNOVLogAgent-1.0.1-1002-x86_64.spk
```

Two builds with the same inputs and `SOURCE_DATE_EPOCH` must have identical SHA-256. `artifacts/manifest.json` records payload paths, modes, and sizes.

## Release status

`1.0.1-1002` is a public validation candidate so Package Center can discover it on real fleet hardware. It is not considered production-validated until installation, DSM UI/session/admin authorization, lifecycle, dynamic linkage, real RFC5424→HTTPS, TLS failure, 128 MB buffer, outage recovery, reboot, and upgrade tests pass on representative AMD and Intel NAS models. See `third_party/FLUENT_BIT_BLOCKER.md`.

The read-only catalogue in `repository/` filters DSM architecture/build parameters and points only to immutable public GitHub Release assets. Publication makes the package available; it does not install it automatically on client NAS units.
