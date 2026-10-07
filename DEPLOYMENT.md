# Production deployment

Production Worker: `lsemap`
URL: https://lsemap.xhr0316.workers.dev/
GitHub: `Haoran-Xu-0316/LSEmap`, branch `main`

Run `npm run deploy` from the repository root with an authenticated Wrangler
session. It builds the website, verifies gallery/model signatures, validates the
runtime asset set and uploads only the checked files through an isolated temporary
directory. That temporary directory is removed after deployment.

For an already verified build, `node web/tools/deploy_release.mjs` checks each
file against `dist/release.json` before uploading. The Worker streams the unchanged
campus GLB from bounded static segments; other runtime assets are served directly.

Cloudflare Workers Builds is connected to `Haoran-Xu-0316/LSEmap`, branch `main`.
The configured pipeline uses `npm run build`, followed by `npx wrangler deploy`.
Recent releases required the verified direct deployment command when the connected
build did not publish the latest source; do not infer publication from a push. The public
`.assetsignore` excludes the oversized complete campus GLB; its verified bounded
segments are uploaded and served by the Worker. Keep all25 default interior
models required by the build and viewer fallback, alongside detailed assets.

A successful push does not guarantee a successful build. Verify the GitHub branch SHA and
the online `/release.json`, then compare changed asset checksums and open the
updated buildings on desktop and mobile before reporting release completion.
Keep the existing Worker name, URL and self-hosted runtime dependencies.
