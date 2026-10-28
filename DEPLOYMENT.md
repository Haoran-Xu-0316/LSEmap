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

The optional HDR sky, compact2048px sky backdrop, four512px ground colour/data textures and their source/license record belong to the verified release
asset set. Gallery capture waits for optional sky and ground loading and records its renderer signature.
After renderer changes, regenerate all current gallery views before building.
Campus transport uses browser-native gzip stream decoding, with raw segments as
a compatibility fallback. A single version-checked file-backed browser cache
avoids repeated campus downloads without accumulating model editions.

Touch devices load the verified `models/mobile-campus.json` descriptor and its
content-addressed overview. Native export writes to a private staging directory. After fresh native
verification, run `npm run publish:models`; it prepares the mobile overview and
checks file identities and binary structure before promoting the complete set.
An unsuccessful directory promotion restores the prior set. Regenerate the
gallery and build after promotion. Keep the
original detailed exteriors and public interiors for on-demand selection. iOS
acceptance uses WebKit with touch emulation and missing AbortSignal APIs in
`web/tests/ios-webkit266.mjs`; a narrow Chrome viewport alone is insufficient.

Mobile antialiasing is checked independently by `web/tests/mobile-antialias268.mjs`
against matched-pose spatial references in WebKit. Record actual renderbuffer
samples and allocation, colour calibration, landscape behaviour and the native
fallback; a requested sample count is not proof of the GPU allocation.

Overview clarity is measured by `web/tests/overview-clarity271.mjs` at matched
poses and common display dimensions, using the prior deployed pipeline and a
higher-density spatial reference. Compare changes in pose-matched image residuals
to check motion stability without counting real camera displacement as flicker.
`web/tests/mobile-render-budget271.mjs` checks
actual portrait, landscape and tablet attachments, HDR colour and native fallback.
Keep browser-owned display allocations separate from the offscreen buffer budget.

The release build also writes a lossless `.glb.gz` mobile transport, records it in
`mobile-campus.json` and checks that decompression exactly reproduces the original
GLB. `_headers` identifies this asset as a gzip file; capable browsers decompress its stream explicitly. This also tolerates an extra HTTP compression layer from the edge. Content-addressed model
files use immutable caching; mutable catalogue, transport and release descriptors
remain revalidated. No domain or routing changes are part of this optimization.

`web/tests/mobile-transfer282.mjs` compares original and compressed transfers over
the same bounded local connection in WebKit and verifies a cache-only model
reopen. It checks the existing pixel ratio and repeat-transfer count; its timings do not
establish physical-phone performance or domain reachability without a VPN.
