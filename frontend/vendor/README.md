# Vendored dependency

This folder keeps a local ECharts build so the data story can still be opened if a public CDN is unavailable. It is a **backup copy**, not the bundle used by `npm run build`.

- **Vendored file:** Apache ECharts 5.5.0 (`echarts.min.js`)
- **Runtime / build:** `package.json` depends on `echarts@^5.6.0`, which esbuild packs into `frontend/build/echarts-main.*.js`. The archived volume pages use a frozen `archive/volumes/build/echarts-volume.*.js`.
- **Upstream (backup file):** `https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js`
- **License:** Apache-2.0 (the upstream license header is retained in the file)
- **SHA-256 (vendored 5.5.0 file):** `42F8329D989B6F6539DD2B15BBDF0D82025762AC112FBB60DC57B27D7BCF3946`
