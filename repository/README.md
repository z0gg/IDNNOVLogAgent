# Package Center catalogue

The read-only Worker filters a versioned `CATALOG` manifest by DSM build and architecture and returns immutable public GitHub Release asset URLs. Production deployment is intentionally not performed by this repository build. Populate the manifest only after release asset size and SHA-256 have been verified, then deploy the catalogue last.
