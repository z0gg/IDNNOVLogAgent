# Release blocker: Fluent Bit target proof

The repository packages Fluent Bit v5.0.9 as an x86-64-baseline executable with dynamic dependencies limited to `libc`, `libm`, and the standard loader. Its newest required glibc symbol is 2.34; official DSM 7.2-72806 x86_64 toolchains use glibc 2.36.

Release `1.0.1-1002` is a public validation candidate for these Synology package platforms:

`apollolake avoton braswell broadwell broadwellnk broadwellnkv2 broadwellntbap bromolow cedarview denverton epyc7002 geminilake geminilakenk grantley icelaked kvmx64 purley r1000 r1000nk v1000 v1000nk`

Production-wide rollout remains blocked until the exact packaged bytes are exercised on representative AMD (`r1000`, beginning with the DS723+ DSM 7.2.2-72806 Update 3) and Intel (`geminilake`, plus the oldest Intel platform present in the fleet) targets and prove: installation, service lifecycle, DSM UI/session/admin authorization, syslog RFC5424 TCP on loopback, HTTPS output, certificate and hostname verification, 128 MB filesystem storage behavior, collector outage recovery, restart, and reboot persistence.

Use canary waves. Do not deploy simultaneously to the full fleet of more than 100 NAS units before these gates pass.
