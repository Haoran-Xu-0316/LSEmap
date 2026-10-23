import { test, expect } from '@playwright/test';
import { createServer } from 'vite';
import { mkdir, writeFile } from 'node:fs/promises';

const output = 'result/web/render-stability261';

// Exercise the production CampusViewer and accepted GLBs, rather than a grid
// proxy. Compare matching camera poses against a 32-sample spatial reference.
test('stone joints stay resolved in first and moving frames without changing settled colour', async ({ page }) => {
  test.setTimeout(150000);
  await mkdir(output, { recursive: true });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  const server = await createServer({
    server: { host: '127.0.0.1', port: 0 }, logLevel: 'error',
    plugins: [{ name: 'render-stability261', configureServer(server) {
      server.middlewares.use('/__render-stability261', (_, response) => {
        response.setHeader('Content-Type', 'text/html');
        response.end(`<!doctype html><link rel="icon" href="data:,"><style>body{margin:0}#stage{width:1000px;height:800px}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">
          import * as THREE from '/@fs/${process.cwd()}/node_modules/three/build/three.module.js';
          import {CampusViewer} from '/src/viewer.js';
          const catalogue=await(await fetch('/models/catalogue.json')).json();
          const viewer=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},catalogue.sourceModelSha256);
          window.viewer=viewer;window.THREE=THREE;window.catalogue=catalogue;
          viewer.loadCampusExteriors=async()=>{};await viewer.load();await viewer.environmentReady;
          const building=catalogue.buildings.find(b=>b.code==='CLM');
          await viewer.loadExterior(building);viewer.select(building);await viewer.upgradeModel(building,'exterior');
          cancelAnimationFrame(viewer.frame);viewer.moveCamera(viewer.transition.position,viewer.transition.target,false);
          viewer.controls.enableDamping=false;viewer.controls.update();viewer.camera.updateMatrixWorld();window.ready=true;
        </script>`);
      });
    } }],
  });
  await server.listen();
  try {
    await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__render-stability261`);
    await page.waitForFunction(() => window.ready, null, { timeout: 90000 });
    const proof = await page.evaluate(async measureTimings => {
      const v = viewer, { camera, renderer, renderPipeline: pipeline } = v;
      const capture = document.createElement('canvas'); capture.width = 1000; capture.height = 800;
      const context = capture.getContext('2d', { willReadFrequently: true });
      const read = () => { context.drawImage(renderer.domElement, 0, 0, 1000, 800); return context.getImageData(0, 0, 1000, 800).data; };
      const image = () => capture.toDataURL('image/png').split(',')[1];
      const position = camera.position.clone(), target = v.controls.target.clone();
      const right = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 0);
      const frames = {}, images = {};
      const sceneTarget = pipeline.scenePass._sampleRenderTarget;
      const candidateSamples = sceneTarget.samples;
      for (const [name, samples, level] of [['single', 0, 0], ['coverage', candidateSamples, 0], ['reference', 0, 5]]) {
        sceneTarget.dispose(); sceneTarget.samples = samples; pipeline.resetHistory();
        frames[name] = [];
        for (let frame = 0; frame < 4; frame++) {
          camera.position.copy(position).addScaledVector(right, frame * .025);
          v.controls.target.copy(target).addScaledVector(right, frame * .025);
          v.controls.update(); camera.updateMatrixWorld();
          pipeline.scenePass.sampleLevel = level;
          pipeline.render({ stabilize: false });
          frames[name].push(read());
          if (!frame) images[name + '-first'] = image();
        }
      }
      const compare = candidate => {
        let spatial = 0, motion = 0, count = 0, motionCount = 0;
        for (let frame = 0; frame < 4; frame++) for (let y = 390; y < 600; y++) for (let x = 315; x < 700; x++) for (let c = 0; c < 3; c++) {
          const i = (y * 1000 + x) * 4 + c;
          const difference = frames[candidate][frame][i] - frames.reference[frame][i];
          spatial += difference * difference; count++;
          if (frame) {
            const error = (frames[candidate][frame][i] - frames[candidate][frame - 1][i]) - (frames.reference[frame][i] - frames.reference[frame - 1][i]);
            motion += error * error; motionCount++;
          }
        }
        return { spatialRms: Math.sqrt(spatial / count), motionRms: Math.sqrt(motion / motionCount) };
      };
      // Warm each dedicated target before paired measurements. Reallocating the
      // target at every sample-count switch would measure allocation, not motion.
      let timing = [];
      const gl = renderer.getContext();
      if (measureTimings) {
        const targets = [0, 2, 4].map(samples => { const t = sceneTarget.clone(); t.samples = Math.min(samples, renderer.capabilities.maxSamples); return t; });
        const timings = [[], [], []], actualSamples = [], gpuQueries = [[], [], []];
        const timer = gl.getExtension('EXT_disjoint_timer_query_webgl2');
        for (let i = 0; i < targets.length; i++) {
          pipeline.scenePass._sampleRenderTarget = targets[i];
          for (let warm = 0; warm < 3; warm++) pipeline.render({ moving: true, stabilize: false });
          gl.finish();
          const colorBuffer = renderer.properties.get(targets[i]).__webglColorRenderbuffer?.[0];
          if (colorBuffer) { gl.bindRenderbuffer(gl.RENDERBUFFER, colorBuffer); actualSamples.push(gl.getRenderbufferParameter(gl.RENDERBUFFER, gl.RENDERBUFFER_SAMPLES)); gl.bindRenderbuffer(gl.RENDERBUFFER, null); }
          else actualSamples.push(0);
        }
        for (let pair = 0; pair < 18; pair++) for (const i of (pair % 2 ? [2, 1, 0] : [0, 1, 2])) {
          camera.position.copy(position).addScaledVector(right, pair * .025);
          v.controls.target.copy(target).addScaledVector(right, pair * .025); v.controls.update(); camera.updateMatrixWorld();
          pipeline.scenePass._sampleRenderTarget = targets[i];
          const query = timer ? gl.createQuery() : null;
          if (query) gl.beginQuery(timer.TIME_ELAPSED_EXT, query);
          const started = performance.now(); pipeline.render({ moving: true, stabilize: false });
          timings[i].push(performance.now() - started);
          if (query) { gl.endQuery(timer.TIME_ELAPSED_EXT); gpuQueries[i].push(query); }
          gl.flush();
        }
        for (let wait = 0; timer && wait < 30 && gpuQueries.flat().some(q => !gl.getQueryParameter(q, gl.QUERY_RESULT_AVAILABLE)); wait++) await new Promise(requestAnimationFrame);
        const gpuValid = timer && !gl.getParameter(timer.GPU_DISJOINT_EXT) && gpuQueries.flat().every(q => gl.getQueryParameter(q, gl.QUERY_RESULT_AVAILABLE));
        const gpuTimes = gpuQueries.map(queries => queries.map(q => { const ns = gpuValid ? gl.getQueryParameter(q, gl.QUERY_RESULT) : null; gl.deleteQuery(q); return ns === null ? null : ns / 1e6; }));
        pipeline.scenePass._sampleRenderTarget = sceneTarget;
        targets.forEach(target => target.dispose());
        const percentile = (values, p) => values.slice().sort((a, b) => a - b)[Math.ceil(values.length * p) - 1];
        timing = timings.map((values, i) => ({ requestedSamples: [0, 2, 4][i], actualSamples: actualSamples[i], cpuSubmissionP50Ms: percentile(values, .5), cpuSubmissionP95Ms: percentile(values, .95), gpuP50Ms: gpuValid ? percentile(gpuTimes[i], .5) : null, gpuP95Ms: gpuValid ? percentile(gpuTimes[i], .95) : null, frames: values.length }));
      }
      camera.position.copy(position); v.controls.target.copy(target); v.controls.update(); camera.updateMatrixWorld();
      sceneTarget.dispose(); sceneTarget.samples = candidateSamples;
      let sceneRenders = 0;
      const originalRender = renderer.render;
      renderer.render = function(scene, ...args) { if (scene === v.scene) sceneRenders++; return originalRender.call(this, scene, ...args); };
      pipeline.render({ moving: true, stabilize: false }); const first = read();
      const movingSceneRenders = sceneRenders; sceneRenders = 0;
      for (let sample = 0; sample < 4; sample++) pipeline.render({ moving: false, progressive: true, restart: sample === 0 });
      const settledSceneRenders = sceneRenders; renderer.render = originalRender;
      const settled = read(); images['coverage-settled'] = image();
      const rgb = data => Array.from(data.slice(0, 3));
      const retainedCamera = position.equals(camera.position) && target.equals(v.controls.target);
      // Bright-pixel rays distinguish real 3cm stone joints from coplanar skins.
      v.scene.updateMatrixWorld(true);
      const ray = new THREE.Raycaster(); ray.setFromCamera(new THREE.Vector2(359.5 / 1000 * 2 - 1, 1 - 434.5 / 800 * 2), camera);
      const hits = ray.intersectObject(v.activeDetail.group, true).slice(0, 2).map(hit => ({ distance: hit.distance, material: hit.object.material.name }));
      // Exercise resolved multisample depth in the existing overview history.
      v.home(false); camera.updateMatrixWorld(); pipeline.resetHistory();
      pipeline.render({ moving: true, time: 1000 });
      camera.position.x += .025; v.controls.target.x += .025; v.controls.update(); camera.updateMatrixWorld();
      pipeline.render({ moving: true, time: 1016 });
      const historyWeight = pipeline.temporalPass.uniforms.historyWeight.value;
      const depthSamples = pipeline.scenePass._sampleRenderTarget.samples;
      renderer.shadowMap.needsUpdate = true; pipeline.render({ moving: true, time: 1032 });
      const changedSceneWeight = pipeline.temporalPass.uniforms.historyWeight.value;
      v.container.style.width = '390px'; v.container.style.height = '700px'; v.resize(); pipeline.render({ moving: true });
      const phoneSamples = pipeline.scenePass._sampleRenderTarget.samples;
      return { phoneSamples, timing, timerQueryAvailable: !!gl.getExtension('EXT_disjoint_timer_query_webgl2'), single: compare('single'), coverage: compare('coverage'), candidateSamples, depthSamples, historyWeight, changedSceneWeight, background: { first: rgb(first), settled: rgb(settled) }, retainedCamera, movingSceneRenders, settledSceneRenders, hits, images, sourceModelSha256: catalogue.sourceModelSha256 };
    }, process.env.RENDER_STABILITY261_TIMINGS === '1');
    proof.interior = await page.evaluate(async () => {
      const v = viewer, p = v.renderPipeline, b = catalogue.buildings.find(b => b.code === 'CBG');
      v.container.style.width = '1000px'; v.container.style.height = '800px'; v.resize();
      v.select(b); await v.showInterior(b); await v.upgradeModel(b, 'interior');
      v.setInteriorSection(b, b.interiorSections[0].id);
      if (v.transition) v.moveCamera(v.transition.position, v.transition.target, false);
      v.controls.update(); v.camera.updateMatrixWorld();
      const capture = document.createElement('canvas'); capture.width = 1000; capture.height = 800;
      const context = capture.getContext('2d', { willReadFrequently: true });
      const data = {}, images = {};
      for (const [name, samples, level] of [['single', 0, 0], ['coverage', p.scenePass.rasterSamples, 0], ['reference', 0, 4]]) {
        const t = p.scenePass._sampleRenderTarget; t.dispose(); t.samples = samples;
        p.scenePass.sampleLevel = level; p.render({ stabilize: false });
        context.drawImage(v.canvas, 0, 0, 1000, 800); data[name] = context.getImageData(0, 0, 1000, 800).data;
        images['interior-' + name] = capture.toDataURL('image/png').split(',')[1];
      }
      const error = name => { let sum = 0; for (let i = 0; i < data[name].length; i += 4) for (let c = 0; c < 3; c++) sum += (data[name][i+c] - data.reference[i+c]) ** 2; return Math.sqrt(sum / (1000 * 800 * 3)); };
      return { code: b.code, section: b.interiorSections[0].id, clippingPlanes: v.renderer.clippingPlanes.length, singleRms: error('single'), coverageRms: error('coverage'), glError: v.renderer.getContext().getError(), images };
    });
    Object.assign(proof.images, proof.interior.images); delete proof.interior.images;
    for (const [name, data] of Object.entries(proof.images)) await writeFile(`${output}/verified-${name}.png`, Buffer.from(data, 'base64'));
    delete proof.images;
    await writeFile(`${output}/verification.json`, JSON.stringify({ ...proof, errors }, null, 2) + '\n');
    expect(errors).toEqual([]);
    expect(proof.interior.clippingPlanes).toBe(2);
    expect(proof.interior.glError).toBe(0);
    expect(proof.interior.coverageRms).toBeLessThan(proof.interior.singleRms);
    expect(proof.candidateSamples).toBe(2);
    expect(proof.phoneSamples).toBe(0);
    expect(proof.coverage.spatialRms).toBeLessThan(proof.single.spatialRms * .8);
    expect(proof.coverage.motionRms).toBeLessThan(proof.single.motionRms * .8);
    expect(proof.background.first).toEqual(proof.background.settled);
    expect(proof.retainedCamera).toBe(true);
    expect(proof.movingSceneRenders).toBe(1);
    expect(proof.settledSceneRenders).toBe(4);
    expect(proof.hits[1].distance - proof.hits[0].distance).toBeGreaterThan(.02);
    expect(proof.depthSamples).toBe(2);
    expect(proof.historyWeight).toBe(.7);
    expect(proof.changedSceneWeight).toBe(0);
  } finally {
    await page.evaluate(() => window.viewer?.dispose()).catch(() => {});
    await server.close();
  }
});
