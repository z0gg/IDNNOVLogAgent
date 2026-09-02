# Pinned build inputs

| Input | Official origin | SHA-256 | Additional verification |
|---|---|---|---|
| Synology DSM 7.3-86009 geminilake GCC 12.2/glibc 2.36 x86_64 toolchain (packaged-binary build input) | `https://global.synologydownload.com/download/ToolChain/toolchain/7.3-86009/Intel%20x86%20Linux%204.4.302%20%28GeminiLake%29/geminilake-gcc1220_glibc236_x86_64-GPL.txz` | `0d12018dffbf94a01b52abaebe4d840af581dfaf6c49ccb16595ccbfffae028d` | Official archive MD5 `bc93d88359a055b398d8e78965bc95cc` matched. |
| Synology DSM 7.2-72806 r1000 GCC 12.2/glibc 2.36 x86_64 toolchain (AMD compatibility reference) | `https://global.synologydownload.com/download/ToolChain/toolchain/7.2-72806/AMD%20x86%20Linux%204.4.302%20%28r1000%29/r1000-gcc1220_glibc236_x86_64-GPL.txz` | `0415940ad9d7c9199855cfacb8eeb6f708607016a07145d3ade5fb2135efabaf` | Official archive MD5 `0c38e3a1633f42c32791695123951112` matched. Both target toolchains use GCC 12.2/glibc 2.36. |
| Fluent Bit v5.0.9 source | `https://github.com/fluent/fluent-bit/archive/refs/tags/v5.0.9.tar.gz` | `158e86d5fbf605e5aeced06ee94ce41a224b34311627f8f4083d722d1f6d7967` | Official upstream tag archive. |

Fluent Bit is Apache-2.0. The cross-built executable must pass ELF architecture, dependency, plugin, dry-run, RFC5424→HTTPS/TLS, filesystem-buffer, outage/recovery, and representative AMD/Intel DSM 7.2.2+ runtime checks before fleet-wide production rollout. A local cross-build alone is not proof of NAS compatibility.
