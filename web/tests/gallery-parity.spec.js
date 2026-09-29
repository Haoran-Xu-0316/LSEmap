import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { galleryRendererSignature, galleryModelSignature } from '../tools/gallery_signature.mjs';

// Match the gallery render buffer: CSS-resolution screenshots resample fine windows twice.
test.use({ reducedMotion: 'reduce', deviceScaleFactor: 1.5 });

test('all gallery views use the current production renderer and source model', async () => {
  const gallery = JSON.parse(await readFile('dist/gallery-manifest.json', 'utf8'));
  const catalogue = JSON.parse(await readFile('dist/models/catalogue.json', 'utf8'));
  const expected = await galleryRendererSignature();
  expect(gallery.renderer).toBe('campus-viewer');
  expect(gallery.modelAssetsSha256).toBe(await galleryModelSignature('dist'));
  expect(gallery.rendererSha256).toBe(expected);
  const views = JSON.parse(await readFile('web/tools/gallery-views.json', 'utf8'));
  expect(gallery.images.map(image => image.name)).toEqual(views.map(view => view.name));
  for (const image of gallery.images) {
    expect(image.rendererSha256, image.name).toBe(expected);
    expect(image.modelAssetsSha256, image.name).toBe(gallery.modelAssetsSha256);
    expect(image.sourceModelSha256, image.name).toBe(catalogue.sourceModelSha256);
    expect(image.view.position.every(Number.isFinite), image.name).toBe(true);
    if (image.code !== 'CAMPUS') expect(image.detail, image.name).toContain(image.code);
  }
});

const exteriorViews = JSON.parse(await readFile('web/tools/gallery-views.json', 'utf8')).filter(view => view.name.endsWith('-exterior'));
for (const { code, name } of exteriorViews) test(`${code} enlarged image matches the live building canvas`, async ({ page }) => {
  await page.goto(`/#${code}`);
  const canvas = page.locator('canvas');
  await expect(canvas).toHaveAttribute('data-detail-ready', `exterior-${code}`, { timeout: 60000 });
  const bounds = await canvas.boundingBox();
  const viewport = page.viewportSize();
  await page.setViewportSize({ width: Math.round(viewport.width + 1400 - bounds.width), height: Math.round(viewport.height + 1120 - bounds.height) });
  await page.reload();
  await expect(canvas).toHaveAttribute('data-detail-ready', `exterior-${code}`, { timeout: 60000 });
  await page.addStyleTag({ content: '#stage > :not(#canvas-container){visibility:hidden!important}' });
  // Background exterior decoding can still replace a transient frame after selection.
  // Compare the settled scene, matching the gallery generator which awaits all assets.
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(250);
  const live = await canvas.screenshot();
  const image = await readFile(`dist/images/${name}.webp`);
  const error = await page.evaluate(async ({ live, image }) => {
    const decode = src => new Promise(resolve => { const img = new Image(); img.onload = () => resolve(img); img.src = src; });
    const [a, b] = await Promise.all([decode(live), decode(image)]);
    const context = document.createElement('canvas').getContext('2d');
    context.canvas.width = 1400; context.canvas.height = 1120;
    context.drawImage(a, 0, 0, 1400, 1120); const x = context.getImageData(0, 0, 1400, 1120).data;
    context.clearRect(0, 0, 1400, 1120); context.drawImage(b, 0, 0, 1400, 1120); const y = context.getImageData(0, 0, 1400, 1120).data;
    let sum = 0, count = 0;
    for (let i = 0; i < y.length; i += 4) {
      // Compare architecture and shadows; blank background cannot hide a mismatch.
      if (Math.abs(y[i]-y[0])+Math.abs(y[i+1]-y[1])+Math.abs(y[i+2]-y[2]) < 30) continue;
      for (let j = 0; j < 3; j++) { sum += Math.abs(x[i+j]-y[i+j]); count++; }
    }
    return { average: sum / (255 * count), samples: count };
  }, { live: `data:image/png;base64,${live.toString('base64')}`, image: `data:image/webp;base64,${image.toString('base64')}` });
  expect(error.samples).toBeGreaterThan(10000);
  expect(error.average).toBeLessThan(0.035);
});
