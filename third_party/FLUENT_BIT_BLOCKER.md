# Release blocker: Fluent Bit target proof

The repository can cross-build Fluent Bit v5.0.9 with the official DSM 7.3-86009 geminilake x86_64 toolchain. Release remains blocked until the exact packaged bytes are exercised on a DS920+ running DSM 7.3 and prove: syslog RFC5424 TCP on loopback, HTTP output, certificate and hostname verification, 128 MB filesystem storage behavior, collector outage recovery, dynamic dependencies, restart, and reboot persistence. Do not publish or deploy the artifact before those checks pass.
