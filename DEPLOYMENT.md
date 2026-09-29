# Production deployment

The existing Cloudflare Worker `lsemap` is connected to `Haoran-Xu-0316/LSEmap`, production branch `main`, with repository root `/`.

- Build command: `npm run build`
- Deploy command: `npx wrangler deploy`
- Assets: `dist/`, as configured in `wrangler.jsonc`
- Production URL: https://lsemap.xhr0316.workers.dev

Push changes to `main` to trigger Cloudflare Workers Builds. Keep the Worker name and production URL unchanged. The build generates release metadata and validates the asset set before deployment.
