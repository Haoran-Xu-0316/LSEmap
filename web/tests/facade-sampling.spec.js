import { test, expect } from '@playwright/test';
import { createServer } from 'vite';
import { mkdir, writeFile } from 'node:fs/promises';
import { stablePixelRatio } from '../src/rendering-quality.js';

const output = 'result/web/facade-sampling';

async function openHarness(page, script) {
  await mkdir(output, { recursive: true });
  const server = await createServer({
    server: { host: '127.0.0.1', port: 0 }, logLevel: 'error',
    plugins: [{ name: 'facade-sampling', configureServer(server) {
      server.middlewares.use('/__sampling', (_, response) => {
        response.setHeader('Content-Type', 'text/html');
        response.end(`<!doctype html><style>body{margin:0}#stage{width:960px;height:768px}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">${script}</script>`);
      });
    } }],
  });
  await server.listen();
  await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__sampling`);
  return server;
}

test('sampling grid remains bounded for desktop and phone', () => {
  expect(stablePixelRatio(960, 768)).toBe(1.5);
  expect(stablePixelRatio(390, 844)).toBe(1.5);
  expect(stablePixelRatio(1920, 1080) ** 2 * 1920 * 1080).toBeLessThanOrEqual(3_000_001);
  expect(stablePixelRatio(3840, 2160)).toBe(1);
});

test('supersampled thin frames reduce visible motion variation without changing color or camera', async ({ page }) => {
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  const server = await openHarness(page, `
    import * as THREE from '/@fs/${process.cwd()}/node_modules/three/build/three.module.js';
    import {createRenderPipeline,stablePixelRatio} from '/src/rendering-quality.js';
    const width=480,height=320;
    const renderer=new THREE.WebGLRenderer({antialias:false});renderer.setSize(width,height);
    renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.setClearColor(0xe9e8e3);
    document.querySelector('#stage').append(renderer.domElement);
    const scene=new THREE.Scene(),camera=new THREE.OrthographicCamera(-6,6,4,-4,.1,20);camera.position.z=10;
    const geometry=new THREE.BoxGeometry(.022,6,.08),material=new THREE.MeshBasicMaterial({color:0x243541});
    const grid=new THREE.InstancedMesh(geometry,material,45),matrix=new THREE.Matrix4(),rotation=new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,0,1),.18);
    for(let i=0;i<45;i++){matrix.compose(new THREE.Vector3(-5.5+i*.25,0,0),rotation,new THREE.Vector3(1,1,1));grid.setMatrixAt(i,matrix);}scene.add(grid);
    const pipeline=createRenderPipeline(renderer,scene,camera),capture=document.createElement('canvas');
    capture.width=width;capture.height=height;const context=capture.getContext('2d',{willReadFrequently:true});
    const delta=frames=>{let squares=0;for(let f=1;f<frames.length;f++)for(let i=0;i<frames[f].length;i+=4)for(let c=0;c<3;c++){const difference=frames[f][i+c]-frames[f-1][i+c];squares+=difference*difference;}return Math.sqrt(squares/(frames[0].length*.75*(frames.length-1)));};
    const records=[];
    for(const level of [0,1]){
      const ratio=stablePixelRatio(960,768);
      renderer.setPixelRatio(ratio);renderer.setSize(width,height);pipeline.resize(width,height);pipeline.scenePass.sampleLevel=level;
      const frames=[];for(const x of [0,.004,.008,.012,.016,.020]){
        camera.position.x=x;camera.updateMatrixWorld();pipeline.render();
        context.drawImage(renderer.domElement,0,0,width,height);frames.push(context.getImageData(0,0,width,height).data);
      }
      records.push({ratio,samples:2**level,rms:delta(frames),background:Array.from(frames[0].slice(0,3))});
    }
    window.proof={records,improvement:records[1].rms/records[0].rms,camera:camera.position.toArray()};
    pipeline.dispose();geometry.dispose();material.dispose();renderer.dispose();
  `);
  try {
    await page.waitForFunction(() => window.proof);
    const proof = await page.evaluate(() => window.proof);
    await writeFile(`${output}/thin-frame-verification.json`, JSON.stringify(proof, null, 2));
    expect(errors).toEqual([]);
    expect(proof.records[0].rms).toBeGreaterThan(.1);
    expect(proof.improvement).toBeLessThan(.95);
    expect(proof.records[1].background).toEqual(proof.records[0].background);
    expect(proof.camera).toEqual([.020, 0, 10]);
  } finally { await server.close(); }
});

test('actual campus keeps camera and raster stable through drag with two samples', async ({ page }) => {
  test.setTimeout(120000);
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  const server = await openHarness(page, `
    import {CampusViewer} from '/src/viewer.js';
    const catalogue=await(await fetch('/models/catalogue.json')).json();
    const viewer=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},catalogue.sourceModelSha256);
    await viewer.load();await Promise.all(catalogue.buildings.filter(b=>b.detailedExterior).map(b=>viewer.loadExterior(b)));
    cancelAnimationFrame(viewer.frame);viewer.transition=null;viewer.controls.enableDamping=false;
    window.viewer=viewer;window.ready=true;
  `);
  try {
    await page.waitForFunction(() => window.ready, null, { timeout: 90000 });
    const proof = await page.evaluate(async () => {
      const { renderer, camera, renderPipeline: pipeline } = viewer;
      const position = camera.position.clone(), projection = camera.projectionMatrix.clone();
      const samples = [];
      for (const level of [0, 1]) {
        const ratio=1.5;pipeline.scenePass.sampleLevel=level;
        renderer.setPixelRatio(ratio);renderer.setSize(960,768);pipeline.resize(960,768);
        const times=[];pipeline.render();
        for(let i=0;i<5;i++) {const started=performance.now();pipeline.render();renderer.getContext().finish();times.push(performance.now()-started);}
        samples.push({ratio,sceneSamples:2**level,medianMs:times.sort((a,b)=>a-b)[2]});
        await new Promise(resolve=>requestAnimationFrame(resolve));
      }
      viewer.needsRender=true;viewer.frame=requestAnimationFrame(viewer.tick);
      return {samples,positionUnchanged:position.equals(camera.position),projectionUnchanged:projection.equals(camera.projectionMatrix),width:viewer.canvas.width,height:viewer.canvas.height};
    });
    await page.locator('canvas').screenshot({ path: `${output}/campus-after.png` });
    const canvas = await page.locator('canvas').boundingBox();
    await page.mouse.move(canvas.x + 500, canvas.y + 300);await page.mouse.down();
    await page.mouse.move(canvas.x + 570, canvas.y + 325, {steps:8});await page.mouse.up();
    const after = await page.evaluate(() => ({width:viewer.canvas.width,height:viewer.canvas.height,ratio:viewer.renderer.getPixelRatio()}));
    expect(after).toEqual({width:1440,height:1152,ratio:1.5});
    expect(proof.positionUnchanged).toBe(true);expect(proof.projectionUnchanged).toBe(true);
    const phone=await page.evaluate(()=>{viewer.container.style.width='390px';viewer.container.style.height='700px';viewer.resize();return {samples:2**viewer.renderPipeline.scenePass.sampleLevel,ratio:viewer.renderer.getPixelRatio()};});
    expect(phone).toEqual({samples:1,ratio:1.5});
    expect(errors).toEqual([]);
    await writeFile(`${output}/campus-verification.json`,JSON.stringify({...proof,after,phone,errors},null,2));
    await page.evaluate(() => viewer.dispose());
  } finally { await server.close(); }
});
