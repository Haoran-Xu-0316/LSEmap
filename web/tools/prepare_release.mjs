/** Package only current runtime assets; archived local model variants stay untouched. */
import { readFile, readdir, rm, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { join } from 'node:path';
import { buildingDetails } from '../src/content.js';
const root = 'dist';
const catalogue = JSON.parse(await readFile(join(root, 'models/catalogue.json'), 'utf8'));
const gallery = JSON.parse(await readFile(join(root, 'gallery-manifest.json'), 'utf8'));
if (gallery.sourceModelSha256 !== catalogue.sourceModelSha256) throw new Error('Gallery/model source mismatch');
const models = new Set(['campus.glb', 'catalogue.json']);
for (const building of catalogue.buildings) {
  for (const detail of [building.detailedExterior, building.detailedInterior].filter(Boolean)) models.add(detail.url.replace('/models/', ''));
  if (building.interior) models.add(`${building.code.toLowerCase()}-interior.glb`);
}
for (const entry of await readdir(join(root, 'models/details'))) {
  if (!models.has(`details/${entry}`)) await rm(join(root, 'models/details', entry));
}
const images = new Set(['campus', ...Object.values(buildingDetails).flatMap(detail => detail.images.map(([name]) => name))]);
for (const name of images) {
  const record = gallery.images.find(image => image.name === name);
  if (!record || record.sourceModelSha256 !== catalogue.sourceModelSha256) throw new Error(`Missing current render: ${name}`);
  const bytes = await readFile(join(root, `images/${name}.webp`));
  if (createHash('sha256').update(bytes).digest('hex') !== record.sha256) throw new Error(`Stale gallery render: ${name}`);
}
const paths = [...models].map(name => `models/${name}`).concat([...images].map(name => `images/${name}.webp`));
paths.push('gallery-manifest.json');
const assets = {};
for (const path of paths) {
  const data = await readFile(join(root, path));
  assets[`/${path}`] = { bytes: data.length, sha256: createHash('sha256').update(data).digest('hex') };
}
await writeFile(join(root, 'release.json'), JSON.stringify({ version: catalogue.version, sourceModelSha256: catalogue.sourceModelSha256, assets }, null, 2)+'\n');
console.log(`Prepared edition ${catalogue.version}: ${models.size} model files and ${images.size} gallery images.`);
