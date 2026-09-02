# Test evidence and DSM matrix

Automated tests cover HTTPS origin normalization, endpoint validation, SSRF ranges, deterministic Fluent Bit generation, token separation/preservation/deletion, settings migration, transactional validation and restart rollback, DNS/TCP/TLS/certificate/HTTP/auth classification, backend authentication/authorization/schema limits, package metadata, and catalogue filtering.

Required physical target matrix before release:

| Model | Platform | DSM | Status |
|---|---|---|---|
| DS920+ | geminilake / x86_64 | 7.3 build 86009 or later 7.3 build | BLOCKED — no NAS is connected to this workspace |

The artifact must remain unpublished and undeployed while this row is blocked.
