import { test, expect } from '@playwright/test';
import { createServer } from 'vite';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';

const output = 'result/web/street-surface262';
const digest = bytes => createHash('sha256').update(bytes).digest('hex');

// Both pages use the production CampusViewer and the same current GLBs. The
// baseline is the exact saved 261 material source, served through Vite normally.
test('existing stone photographs gain readable close wear while overview and motion remain stable', async ({ browser }) => {
  test.setTimeout(150000);
  await mkdir(output, { recursive: true });
  const sourceHashes = JSON.parse(await readFile(`${output}/before-source-hashes.json`, 'utf8'));
  for (const name of ['ground-textures.js', 'surface-materials.js']) {
    expect(digest(await readFile(`${output}/before-${name}`))).toBe(sourceHashes[`web/src/${name}`].sha256);
  }
  const server = await createServer({
    server: { host: '127.0.0.1', port: 0 }, logLevel: 'error',
    plugins: [{ name: 'saved-street-baseline262', enforce: 'pre',
      async load(id) {
        for (const name of ['ground-textures.js', 'surface-materials.js']) if (id.endsWith(`/src/${name}?baseline262`)) {
          return (await readFile(`${output}/before-${name}`, 'utf8')).replaceAll('./ground-textures.js', './ground-textures.js?baseline262');
        }
      },
      transform(code, id) {
        if (id.endsWith('/src/viewer.js?baseline262')) return code.replaceAll('./surface-materials.js', './surface-materials.js?baseline262').replaceAll('./ground-textures.js', './ground-textures.js?baseline262');
      },
      configureServer(server) {
        server.middlewares.use('/__street262', (request, response) => {
          const suffix = request.url.includes('baseline') ? '?baseline262' : '';
          response.setHeader('Content-Type', 'text/html');
          response.end(`<!doctype html><link rel="icon" href="data:,"><style>body{margin:0}#stage{width:1000px;height:800px}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">
            import * as THREE from '/@fs/${process.cwd()}/node_modules/three/build/three.module.js';
            import {CampusViewer} from '/src/viewer.js${suffix}';
            const catalogue=await(await fetch('/models/catalogue.json')).json();
            const v=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},catalogue.sourceModelSha256);
            window.viewer=v;window.THREE=THREE;window.catalogue=catalogue;v.loadCampusExteriors=async()=>{};
            await v.load();await v.environmentReady;cancelAnimationFrame(v.frame);v.controls.enableDamping=false;v.home(false);
            await new Promise(resolve=>{const timer=setInterval(()=>{if(v.groundTextures.reliefReady.value){clearInterval(timer);resolve();}},20)});window.ready=true;
          </script>`);
        });
      },
    }],
  });
  await server.listen();
  const errors = [], records = {}, images = {};
  try {
    for (const mode of ['baseline', 'candidate']) {
      const page = await browser.newPage({ viewport: { width: 1000, height: 800 } });
      page.on('pageerror', error => errors.push(error.message));
      page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
      try {
        await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__street262?${mode}`);
        await page.waitForFunction(() => window.ready, null, { timeout: 90000 });
        records[mode] = await page.evaluate(async () => {
          const v = viewer, p = v.renderPipeline, gl = v.renderer.getContext();
          const canvas = document.createElement('canvas'); canvas.width = 1000; canvas.height = 800;
          const context = canvas.getContext('2d', { willReadFrequently: true });
          const read = () => { context.drawImage(v.canvas, 0, 0, 1000, 800); return context.getImageData(0, 0, 1000, 800).data; };
          const pose = (position, target) => { v.camera.fov = 48; v.updateCameraProjection(); v.moveCamera(new THREE.Vector3(...position), new THREE.Vector3(...target), false); v.controls.update(); v.camera.updateMatrixWorld(); p.resetHistory(); };
          const images = {}, views = {};
          let pavement;
          const sceneTarget = p.scenePass._sampleRenderTarget;
          for (const [name, position, target] of [['near', [-2, 1.8, 103], [-.5, .05, 92]], ['overview', [-280, 330, 370], [10, 0, -10]]]) {
            pose(position, target);
            const frames = [], references = [];
            for (let frame = 0; frame < 4; frame++) {
              const x = frame * .012;
              v.moveCamera(new THREE.Vector3(...position).add(new THREE.Vector3(x, 0, 0)), new THREE.Vector3(...target).add(new THREE.Vector3(x, 0, 0)), false); v.camera.updateMatrixWorld();
              p.render({ moving: true, stabilize: false }); frames.push(read());
              if (!frame) images[name + '-moving'] = canvas.toDataURL('image/png').split(',')[1];
              p.scenePass.sampleLevel = 3; p.render({ stabilize: false }); references.push(read());
            }
            pose(position, target);
            for (let sample = 0; sample < 4; sample++) p.render({ moving: false, progressive: true, restart: sample === 0 });
            const settled = read(); images[name + '-settled'] = canvas.toDataURL('image/png').split(',')[1];
            if (name === 'near') {
              v.scene.updateMatrixWorld(true);
              const ray = new THREE.Raycaster();
              const hits = [[-.002, 95], [.002, 95], [-1, 95], [0, 105]].map(([x, z]) => {
                ray.set(new THREE.Vector3(x, 2, z), new THREE.Vector3(0, -1, 0));
                const hit = ray.intersectObject(v.campus, true)[0];
                const material = Array.isArray(hit.object.material) ? hit.object.material[hit.face.materialIndex] : hit.object.material;
                return { point: hit.point.toArray(), material: material.name, uv: hit.uv.toArray() };
              });
              ray.setFromCamera(new THREE.Vector2(0, -.75), v.camera); const first = ray.intersectObject(v.campus, true)[0].point;
              ray.setFromCamera(new THREE.Vector2(.002, -.75), v.camera); const second = ray.intersectObject(v.campus, true)[0].point;
              let stone;
              v.campus.traverse(object => { if (object.isMesh && !stone) stone = (Array.isArray(object.material) ? object.material : [object.material]).find(m => /SITE172_SITE_V47_slab_4_Houghton/.test(m.name)); });
              const shader = { uniforms: {}, vertexShader: '#include <project_vertex>', fragmentShader: '#include <color_fragment>\n#include <roughnessmap_fragment>\n#include <normal_fragment_maps>' };
              stone.onBeforeCompile(shader, v.renderer);
              pavement = { hits, metresPerPixel: first.distanceTo(second), repeatMetres: shader.uniforms.groundMetres.value, reliefMetres: shader.uniforms.groundHeight.value, capturedTextureReads: (shader.fragmentShader.match(/texture2D\(ground(?:Finish|Relief),/g) ?? []).length };
            }
            let spatial = 0, motion = 0, n = 0, motionN = 0, mean = 0, square = 0;
            const roi = name === 'near' ? [100, 480, 900, 790] : [100, 120, 900, 750];
            for (let y = roi[1]; y < roi[3]; y++) for (let x = roi[0]; x < roi[2]; x++) for (let c = 0; c < 3; c++) {
              const i = (y * 1000 + x) * 4 + c;
              mean += settled[i]; square += settled[i] ** 2;
              for (let frame = 0; frame < 4; frame++) {
                spatial += (frames[frame][i] - references[frame][i]) ** 2; n++;
                if (frame) { motion += ((frames[frame][i] - frames[frame - 1][i]) - (references[frame][i] - references[frame - 1][i])) ** 2; motionN++; }
              }
            }
            const pixels = (roi[2] - roi[0]) * (roi[3] - roi[1]) * 3; mean /= pixels;
            views[name] = { spatialRms: Math.sqrt(spatial / n), motionRms: Math.sqrt(motion / motionN), mean, contrast: Math.sqrt(square / pixels - mean ** 2), background: Array.from(settled.slice(0, 3)) };
          }
          // Measure a short identical near-street orbit with actual GPU timers.
          pose([-2, 1.8, 103], [-.5, .05, 92]);
          for (let warm = 0; warm < 3; warm++) p.render({ moving: true, stabilize: false });
          const ext = gl.getExtension('EXT_disjoint_timer_query_webgl2'), queries = [], cpu = [];
          for (let frame = 0; frame < 12; frame++) {
            v.camera.position.x += .012; v.controls.target.x += .012; v.controls.update(); v.camera.updateMatrixWorld();
            const query = ext ? gl.createQuery() : null; if (query) gl.beginQuery(ext.TIME_ELAPSED_EXT, query);
            const started = performance.now(); p.render({ moving: true, stabilize: false }); cpu.push(performance.now() - started);
            if (query) { gl.endQuery(ext.TIME_ELAPSED_EXT); queries.push(query); } gl.flush();
          }
          for (let wait = 0; ext && wait < 30 && queries.some(q => !gl.getQueryParameter(q, gl.QUERY_RESULT_AVAILABLE)); wait++) await new Promise(requestAnimationFrame);
          const valid = ext && !gl.getParameter(ext.GPU_DISJOINT_EXT) && queries.every(q => gl.getQueryParameter(q, gl.QUERY_RESULT_AVAILABLE));
          const gpu = queries.map(q => { const value = valid ? gl.getQueryParameter(q, gl.QUERY_RESULT) / 1e6 : null; gl.deleteQuery(q); return value; });
          const percentile = (values, f) => values.slice().sort((a, b) => a - b)[Math.ceil(values.length * f) - 1];
          return { pavement, views, images, gpuP50Ms: valid ? percentile(gpu, .5) : null, gpuP95Ms: valid ? percentile(gpu, .95) : null, cpuP50Ms: percentile(cpu, .5), sourceModelSha256: catalogue.sourceModelSha256, sceneSamples: sceneTarget.samples, textureSlots: ['asphalt', 'stone', 'asphaltRelief', 'stoneRelief'].filter(slot => v.groundTextures[slot].value).length, glError: gl.getError() };
        });
        Object.assign(images, Object.fromEntries(Object.entries(records[mode].images).map(([name, bytes]) => [mode + '-' + name, bytes])));
        delete records[mode].images;
      } finally { await page.evaluate(() => window.viewer?.dispose()).catch(() => {}); await page.close(); }
    }
    for (const [name, data] of Object.entries(images)) await writeFile(`${output}/${name}.png`, Buffer.from(data, 'base64'));
    const afterSourceHashes = {};
    for (const name of ['ground-textures.js', 'surface-materials.js']) afterSourceHashes[`web/src/${name}`] = digest(await readFile(`web/src/${name}`));
    await writeFile(`${output}/verification.json`, JSON.stringify({ sourceHashes, afterSourceHashes, records, errors }, null, 2) + '\n');
    expect(errors).toEqual([]);
    expect(records.candidate.sourceModelSha256).toBe(records.baseline.sourceModelSha256);
    expect(records.candidate.glError).toBe(0);
    expect(records.candidate.textureSlots).toBe(4);
    expect(records.candidate.pavement.hits).toEqual(records.baseline.pavement.hits);
    expect(records.candidate.pavement.repeatMetres).toBe(2);
    expect(records.candidate.pavement.reliefMetres).toBe(.0025);
    expect(records.candidate.pavement.capturedTextureReads).toBe(records.baseline.pavement.capturedTextureReads);
    expect(records.candidate.views.near.contrast).toBeGreaterThan(records.baseline.views.near.contrast * 1.05);
    expect(records.candidate.sceneSamples).toBe(2);
    for (const name of ['near', 'overview']) {
      expect(records.candidate.views[name].motionRms).toBeLessThan(records.baseline.views[name].motionRms * 1.15);
      expect(records.candidate.views[name].background).toEqual(records.baseline.views[name].background);
    }
    expect(Math.abs(records.candidate.views.overview.mean - records.baseline.views.overview.mean)).toBeLessThan(.25);
  } finally { await server.close(); }
});
