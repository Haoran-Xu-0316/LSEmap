/** Generate every gallery still with the production CampusViewer and GLB assets.
 * A private Vite page supplies a plain canvas; it is never included in the build.
 * Browser, GPU context and server are closed even when a view fails.
 */
import { createServer } from 'vite';
import { chromium } from 'playwright';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { galleryRendererSignature, galleryModelSignature } from './gallery_signature.mjs';

const catalogue = JSON.parse(await readFile('web/public/models/catalogue.json', 'utf8'));
const jobs = JSON.parse(await readFile('web/tools/gallery-views.json', 'utf8'));
const rendererSha256 = await galleryRendererSignature();
const modelAssetsSha256 = await galleryModelSignature();
const html = `<!doctype html><style>html,body{margin:0}#canvas{width:1400px;height:1120px}#labels{display:none}</style>
<div id="canvas"></div><div id="labels"></div><script type="module">
import {CampusViewer} from '/src/viewer.js';
const catalogue=await (await fetch('/models/catalogue.json')).json();
const viewer=new CampusViewer(document.querySelector('#canvas'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('WebGL context lost')},()=>{},catalogue.sourceModelSha256);
await viewer.load();
await Promise.all(catalogue.buildings.filter(b=>b.detailedExterior).map(b=>viewer.loadExterior(b)));
viewer.toggleLabels(false);
window.renderGalleryView=async(job)=>{
 const building=catalogue.buildings.find(b=>b.code===job.code);
 const interior=job.name.endsWith('-interior')||['mar-hall','mar-stair'].includes(job.name);
 if(job.code==='CAMPUS') viewer.home(false);
 else {
  viewer.select(building);
  await viewer.upgradeModel(building,'exterior');
  if(interior){
   await viewer.showInterior(building,job.spaceId??null);
   await viewer.upgradeModel(building,'interior',job.spaceId??null);
  }else if(/-(entrance|windows)$/.test(job.name)&&building.detailView) {
   viewer.showDetail(building); await viewer.upgradeModel(building,'exterior');
  }
  const expected=(interior?'interior-':'exterior-')+job.code+(job.spaceId?':'+job.spaceId:'');
  if(viewer.canvas.dataset.detailReady!==expected) throw Error('Detail unavailable: '+job.name);
 }
 if(job.view){
  viewer.camera.fov=job.view.fov;viewer.updateCameraProjection();
  viewer.moveCamera(viewer.camera.position.clone().fromArray(job.view.position),viewer.controls.target.clone().fromArray(job.view.target),false);
 }
 viewer.transition=null;
 viewer.controls.update();
 viewer.camera.updateMatrixWorld();
 viewer.renderer.shadowMap.needsUpdate=true;
 viewer.renderer.render(viewer.scene,viewer.camera);
 const view={position:viewer.camera.position.toArray(),target:viewer.controls.target.toArray(),fov:viewer.camera.fov};
 return {image:viewer.canvas.toDataURL('image/webp',0.95).split(',')[1],view,
  mode:interior?'interior':job.code==='CAMPUS'?'campus':'exterior',
  detail:viewer.canvas.dataset.detailReady??null};
};
window.galleryReady=true;
</script>`;
const server = await createServer({
  server: { host: '127.0.0.1', port: 0 }, logLevel: 'error',
  plugins: [{ name: 'gallery-capture-page', configureServer(server) {
    server.middlewares.use('/__gallery-render', (_request, response) => {
      response.setHeader('Content-Type', 'text/html'); response.end(html);
    });
  } }],
});
let browser;
try {
  await server.listen();
  const { port } = server.httpServer.address();
  browser = await chromium.launch({ args: process.platform === 'darwin' ? ['--use-angle=metal'] : ['--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1120 }, reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', error => { errors.push(error.message); console.error(error.message); });
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  await page.goto(`http://127.0.0.1:${port}/__gallery-render`);
  await page.waitForFunction(() => window.galleryReady, null, { timeout: 120000 });
  const records = [];
  const output = `result/web/release${catalogue.version}/web-gallery`;
  await mkdir(output, { recursive: true });
  for (const job of jobs) {
    const capture = await page.evaluate(job => window.renderGalleryView(job), job);
    if (errors.length) throw Error(errors.join('\n'));
    const bytes = Buffer.from(capture.image, 'base64');
    if (bytes.length < 1000) throw Error(`Empty canvas: ${job.name}`);
    await writeFile(`${output}/${job.name}.webp`, bytes);
    records.push({ name: job.name, code: job.code, sourceModelSha256: catalogue.sourceModelSha256,
      renderer: 'campus-viewer', rendererSha256, modelAssetsSha256, bytes: bytes.length,
      sha256: createHash('sha256').update(bytes).digest('hex'),
      view: capture.view, mode: capture.mode, spaceId: job.spaceId ?? null, detail: capture.detail });
    console.log(`WEB_GALLERY ${records.length}/${jobs.length} ${job.name}`);
  }
  // Publish only after every view has rendered successfully.
  for (const record of records) await writeFile(`web/public/images/${record.name}.webp`, await readFile(`${output}/${record.name}.webp`));
  await writeFile('web/public/gallery-manifest.json', JSON.stringify({ version: catalogue.version,
    sourceModelSha256: catalogue.sourceModelSha256, renderer: 'campus-viewer', rendererSha256, modelAssetsSha256, images: records }, null, 2)+'\n');
} finally {
  await browser?.close();
  await server.close();
}
