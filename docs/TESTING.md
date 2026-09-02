# Test evidence and DSM matrix

Automated tests cover HTTPS origin normalization, endpoint validation, SSRF ranges, deterministic Fluent Bit generation, token separation/preservation/deletion, settings migration, transactional validation and restart rollback, DNS/TCP/TLS/certificate/HTTP/auth classification, backend authentication/authorization/schema limits, package metadata, and multi-architecture catalogue filtering.

Required representative physical matrix before declaring the fleet release production-validated:

| Model class | Example platform | DSM | Status |
|---|---|---|---|
| AMD Ryzen embedded | DS723+ / r1000 | 7.2.2-72806 Update 3 | CURRENT VALIDATION TARGET — catalogue discovery and installation pending |
| Intel Celeron | DS920+ / geminilake | 7.3-86009 or later | Runtime validation pending |
| Older Intel x86_64 | avoton/braswell/bromolow or oldest platform present in fleet | 7.2.2-72806 or later | Runtime validation pending after inventory |

The validation candidate may be publicly discoverable, but broad rollout to more than 100 NAS units must remain paused until representative AMD and Intel canaries pass installation, start, UI, RFC5424→HTTPS, buffer, restart, and reboot tests. Roll out in bounded waves after canaries; never push directly to every NAS at once.
