/** Tie displayed stills to the same renderer and view presets as the live map. */
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

export async function galleryRendererSignature() {
  const hash = createHash('sha256');
  for (const path of [
    'web/src/viewer.js', 'web/src/surface-materials.js', 'web/src/model-cache.js',
    'web/src/model-loading.js', 'web/src/rendering-quality.js',
    'web/tools/gallery-views.json', 'web/tools/render_web_gallery.mjs',
    'web/tools/gallery_signature.mjs', 'package-lock.json',
  ]) hash.update(path).update(await readFile(path));
  return hash.digest('hex');
}

export async function galleryModelSignature(root = 'web/public') {
  const hash = createHash('sha256');
  // The catalogue covers every detailed/interior asset digest; include the base
  // campus too, so re-exporting an unchanged .blend cannot reuse stale images.
  for (const path of ['models/catalogue.json', 'models/campus.glb'])
    hash.update(path).update(await readFile(`${root}/${path}`));
  return hash.digest('hex');
}
