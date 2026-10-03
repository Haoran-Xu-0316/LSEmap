/** Package only current runtime assets; archived local model variants stay untouched. */
import { readFile, readdir, rm, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { join } from 'node:path';
import { detailFor } from '../src/content.js';
import { galleryRendererSignature, galleryModelSignature } from './gallery_signature.mjs';
const root = 'dist';
const catalogue = JSON.parse(await readFile(join(root, 'models/catalogue.json'), 'utf8'));
const gallery = JSON.parse(await readFile(join(root, 'gallery-manifest.json'), 'utf8'));
if (gallery.sourceModelSha256 !== catalogue.sourceModelSha256) throw new Error('Gallery/model source mismatch');
const rendererSha256 = await galleryRendererSignature();
const modelAssetsSha256 = await galleryModelSignature(root);
if (gallery.modelAssetsSha256 !== modelAssetsSha256) throw new Error("Gallery models are stale. Run npm run gallery.");
if (gallery.renderer !== 'campus-viewer' || gallery.rendererSha256 !== rendererSha256)
  throw new Error('Gallery renderer is stale. Run npm run gallery before building.');
if (gallery.images.some(image => image.rendererSha256 !== rendererSha256 || image.renderer !== 'campus-viewer' || image.modelAssetsSha256 !== modelAssetsSha256))
  throw new Error('Mixed gallery renderers or versions');
const models = new Set(['campus.glb', 'catalogue.json']);
for (const building of catalogue.buildings) {
  for (const detail of [building.detailedExterior, building.detailedInterior, ...(building.interiorSpaces || []).map(space => space.detailedInterior)].filter(Boolean)) models.add(detail.url.replace('/models/', ''));
  if (building.interior) models.add(`${building.code.toLowerCase()}-interior.glb`);
}
for (const entry of await readdir(join(root, 'models/details'))) {
  if (!models.has(`details/${entry}`)) await rm(join(root, 'models/details', entry));
}
const images = new Set(['campus', ...catalogue.buildings.flatMap(building => detailFor(building).images.map(([name]) => name))]);
for (const name of images) {
  const record = gallery.images.find(image => image.name === name);
  if (!record || record.sourceModelSha256 !== catalogue.sourceModelSha256) throw new Error(`Missing current render: ${name}`);
  const bytes = await readFile(join(root, `images/${name}.webp`));
  if (createHash('sha256').update(bytes).digest('hex') !== record.sha256) throw new Error(`Stale gallery render: ${name}`);
}
// Preserve the GLB byte-for-byte while fitting the static asset size limit.
const campus = await readFile(join(root, 'models/campus.glb'));
const campusHash = createHash('sha256').update(campus).digest('hex');
const parts = [];
for (let offset = 0; offset < campus.length; offset += 16 * 1024 * 1024) {
  const bytes = campus.subarray(offset, offset + 16 * 1024 * 1024);
  const hash = createHash('sha256').update(bytes).digest('hex');
  const path = `models/campus-${parts.length}-${hash.slice(0,12)}.bin`;
  await writeFile(join(root, path), bytes);
  parts.push({path:'/'+path, bytes:bytes.length, sha256:hash});
  models.add(path.replace('models/',''));
}
const campusTransport = {bytes:campus.length, sha256:campusHash, parts};
await writeFile(join(root, 'models/campus-parts.json'), JSON.stringify(campusTransport)+'\n');
models.delete('campus.glb');models.add('campus-parts.json');
const paths = [...models].map(name => `models/${name}`).concat([...images].map(name => `images/${name}.webp`));
// These public files are loaded at runtime rather than imported by Vite.
// Keep them in the same verified upload set as the model and application.
paths.push('gallery-manifest.json', 'index.html', 'favicon.svg', 'logo-lse.svg',
  'draco/draco_wasm_wrapper.js', 'draco/draco_decoder.wasm',
  'draco/LICENSE.txt', 'draco/THREE-LICENSE.txt', 'draco/README.md',
  '_headers', 'credits.txt', 'font-licenses/Roboto-OFL.txt');
const html = await readFile(join(root, 'index.html'), 'utf8');
const entryScript = html.match(/<script[^>]*src="(\/assets\/[^"]+\.js)"/)?.[1];
if (!entryScript) throw new Error('Missing application entry script');
for (const file of await readdir(join(root, 'assets'))) paths.push(`assets/${file}`);
const assets = {};
for (const path of paths) {
  const data = await readFile(join(root, path));
  assets[`/${path}`] = { bytes: data.length, sha256: createHash('sha256').update(data).digest('hex') };
}
await writeFile(join(root, 'release.json'), JSON.stringify({ version: catalogue.version, sourceModelSha256: catalogue.sourceModelSha256, modelAssetsSha256, rendererSha256, entryScript, campusTransport, assets }, null, 2)+'\n');
console.log(`Prepared edition ${catalogue.version}: ${models.size} model files and ${images.size} gallery images.`);
