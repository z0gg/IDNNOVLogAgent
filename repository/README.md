# Package Center catalogue

The Cloudflare Pages Function in `src/worker.mjs` filters the versioned public manifest in `catalog/releases.json` by DSM build and architecture. It returns immutable public GitHub Release asset URLs using the DSM 7/spkrepo-compatible GET and POST form protocol.

## Local verification

```sh
npm ci
npm test
npm run build
```

The build creates the advanced-mode Pages Function at `pages-dist/_worker.js`. The production Pages project is `idnnov-package-catalogue`; its custom domain is `https://packages.idnnov.com/`.

Release order is mandatory:

1. publish immutable GitHub Release assets;
2. download them publicly and verify size, MD5, and SHA-256;
3. update `catalog/releases.json`;
4. run all tests and build the Pages bundle;
5. deploy Pages last;
6. verify GET, POST, public download, and SHA-256.

There are no public write, administration, or upload routes. Do not replace published release assets; promote a new version instead.
