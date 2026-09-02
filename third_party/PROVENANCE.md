# Pinned build inputs

| Input | Official origin | SHA-256 | Additional verification |
|---|---|---|---|
| Synology DSM 7.3-86009 geminilake GCC 12.2/glibc 2.36 x86_64 toolchain | `https://global.synologydownload.com/download/ToolChain/toolchain/7.3-86009/Intel%20x86%20Linux%204.4.302%20%28GeminiLake%29/geminilake-gcc1220_glibc236_x86_64-GPL.txz` | `0d12018dffbf94a01b52abaebe4d840af581dfaf6c49ccb16595ccbfffae028d` | Official archive MD5 `bc93d88359a055b398d8e78965bc95cc` matched. |
| Fluent Bit v5.0.9 source | `https://github.com/fluent/fluent-bit/archive/refs/tags/v5.0.9.tar.gz` | `158e86d5fbf605e5aeced06ee94ce41a224b34311627f8f4083d722d1f6d7967` | Official upstream tag archive. |

Fluent Bit is Apache-2.0. The cross-built executable must pass ELF architecture, dependency, plugin, dry-run, RFC5424→HTTPS/TLS, filesystem-buffer, outage/recovery, and DS920+/DSM 7.3 runtime checks before release. A local cross-build alone is not proof of NAS compatibility.
