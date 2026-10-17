import { test, expect } from '@playwright/test';
import { createServer } from 'vite';
import { mkdir, writeFile } from 'node:fs/promises';

// Full production geometry and renderer; gl.finish includes queued GPU work.
test('progressive stills preserve pixels and leave a scene-draw budget for new input', async ({ page }) => {
  test.setTimeout(150000);
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const server = await createServer({ logLevel: 'error', server: { host: '127.0.0.1', port: 0 } });
  try {
    await server.listen();
    await page.route('**/__smoothness', route => route.fulfill({ contentType: 'text/html', body:
      '<!doctype html><style>body{margin:0}#stage{width:960px;height:768px}#labels{display:none}</style><div id="stage"></div><div id="labels"></div>' }));
    await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__smoothness`);
    const proof = await page.evaluate(async () => {
      const { CampusViewer } = await import('/src/viewer.js');
      const catalogue = await (await fetch('/models/catalogue.json')).json();
      const viewer = new CampusViewer(document.querySelector('#stage'), document.querySelector('#labels'), catalogue.buildings, () => {}, () => {});
      window.viewer = viewer;
      await viewer.load();
      await viewer.environmentReady;
      await Promise.all(catalogue.buildings.filter(b => b.detailedExterior).map(b => viewer.loadExterior(b)));
      cancelAnimationFrame(viewer.frame);
      viewer.transition = null;
      viewer.home(false);
      const pipeline = viewer.renderPipeline, renderer = viewer.renderer, gl = renderer.getContext();
      let draws = 0;
      const render = renderer.render.bind(renderer);
      renderer.render = (scene, camera) => { if (scene === viewer.scene) draws++; return render(scene, camera); };
      const pixels = () => {
        const data = new Uint8Array(viewer.canvas.width * viewer.canvas.height * 4);
        gl.readPixels(0, 0, viewer.canvas.width, viewer.canvas.height, gl.RGBA, gl.UNSIGNED_BYTE, data);
        return data;
      };
      const measure = options => {
        draws = 0;
        const start = performance.now();
        pipeline.render(options);
        gl.finish();
        return { ms: performance.now() - start, draws };
      };
      const records = [];
      for (const code of ['CAMPUS', 'CBG']) {
        if (code === 'CBG') {
          const building = catalogue.buildings.find(b => b.code === code);
          viewer.select(building);
          await viewer.upgradeModel(building, 'exterior');
          viewer.transition = null;
          viewer.fit(building.bounds, false);
        }
        pipeline.render({ moving: false, stabilize: false });
        const reference = pixels(), position = viewer.camera.position.clone(), projection = viewer.camera.projectionMatrix.clone();
        const synchronous = [], progressive = [], batches = [];
        for (let round = 0; round < 7; round++) {
          synchronous.push(measure({ moving: false, stabilize: false }).ms);
          pipeline.resetHistory();
          const batch = [];
          for (let index = 0; index < 4; index++) batch.push(measure({ moving: false, progressive: true, restart: index === 0 }));
          batches.push(batch);
          progressive.push(...batch.map(r => r.ms));
        }
        const actual = pixels();
        let maxPixelDifference = 0, sum = 0, foreground = 0;
        for (let i = 0; i < actual.length; i++) {
          const difference = Math.abs(actual[i] - reference[i]);
          maxPixelDifference = Math.max(maxPixelDifference, difference);
          sum += difference;
          if (i % 4 === 0 && actual[i] < 200) foreground++;
        }
        const median = values => [...values].sort((a, b) => a - b)[Math.floor(values.length / 2)];
        records.push({ code, synchronousMedianMs: median(synchronous), progressiveMedianMs: median(progressive),
          batches, maxPixelDifference, meanPixelDifference: sum / actual.length, foreground,
          poseUnchanged: position.equals(viewer.camera.position) && projection.equals(viewer.camera.projectionMatrix),
          settled: !pipeline.needsSettle });
      }
      // Begin a refinement, interrupt with a real wheel event, then settle again.
      pipeline.render({ moving: true });
      pipeline.render({ moving: false, progressive: true, restart: true });
      const partialWasPending = pipeline.needsSettle;
      viewer.canvas.dispatchEvent(new WheelEvent('wheel', { deltaY: 100, bubbles: true, cancelable: true }));
      draws = 0;
      viewer.tick(performance.now()); cancelAnimationFrame(viewer.frame);
      const interruptedDraws = draws, motionSamples = 2 ** pipeline.scenePass.sampleLevel;
      await new Promise(resolve => setTimeout(resolve, 250));
      const settleDraws = [];
      for (let index = 0; index < 4; index++) {
        draws = 0; viewer.tick(performance.now()); cancelAnimationFrame(viewer.frame); settleDraws.push(draws);
      }
      draws = 0; viewer.tick(performance.now()); cancelAnimationFrame(viewer.frame);
      const idleDraws = draws, settled = !pipeline.needsSettle;
      viewer.frame = requestAnimationFrame(viewer.tick);
      return { records, lifecycle: { partialWasPending, interruptedDraws, motionSamples, settleDraws, idleDraws, settled }, scope: 'Local Chromium/Metal at 960x768 CSS pixels; not a guarantee for every device' };
    });
    await mkdir('result/web/interaction-smoothness', { recursive: true });
    await writeFile('result/web/interaction-smoothness/measurement.json', JSON.stringify(proof, null, 2) + '\n');
    for (const record of proof.records) {
      expect(record.foreground).toBeGreaterThan(10000);
      expect(record.maxPixelDifference).toBeLessThanOrEqual(1);
      expect(record.meanPixelDifference).toBeLessThan(.05);
      expect(record.batches.every(batch => batch.every(frame => frame.draws === 1))).toBe(true);
      expect(record.poseUnchanged).toBe(true);
      expect(record.settled).toBe(true);
    }
    expect(proof.records[0].progressiveMedianMs).toBeLessThan(proof.records[0].synchronousMedianMs * .65);
    expect(proof.lifecycle).toEqual({ partialWasPending: true, interruptedDraws: 1, motionSamples: 1, settleDraws: [1, 1, 1, 1], idleDraws: 0, settled: true });
    await page.locator('canvas').screenshot({ path: 'result/web/interaction-smoothness/settled.png' });
    expect(errors).toEqual([]);
  } finally { await page.evaluate(() => window.viewer?.dispose()).catch(() => {}); await server.close(); }
});

test('resize cancels unfinished samples and phone rendering keeps its light budget', async ({ page }) => {
  const server = await createServer({ logLevel: 'error', server: { host: '127.0.0.1', port: 0 } });
  try {
    await server.listen();
    await page.route('**/__smoothness-resize', route => route.fulfill({ contentType: 'text/html', body: '<!doctype html><div id="stage" style="width:800px;height:600px"></div><div id="labels"></div>' }));
    await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__smoothness-resize`);
    const result = await page.evaluate(async () => {
      const { CampusViewer } = await import('/src/viewer.js');
      const viewer = new CampusViewer(document.querySelector('#stage'), document.querySelector('#labels'), [], () => {}, () => {});
      cancelAnimationFrame(viewer.frame);
      const pipeline = viewer.renderPipeline;
      pipeline.render({ moving: false, progressive: true, restart: true });
      const pendingBeforeResize = pipeline.needsSettle;
      viewer.container.style.width = '390px'; viewer.resize();
      pipeline.render({ moving: false, progressive: true, restart: true });
      const phone = { settled: !pipeline.needsSettle, samples: 2 ** pipeline.scenePass.sampleLevel };
      viewer.container.style.width = '900px'; viewer.resize();
      const pose = viewer.camera.position.clone(), projection = viewer.camera.projectionMatrix.clone();
      const pending = [];
      for (let i = 0; i < 4; i++) { pipeline.render({ moving: false, progressive: true, restart: i === 0 }); pending.push(pipeline.needsSettle); }
      const poseUnchanged = pose.equals(viewer.camera.position) && projection.equals(viewer.camera.projectionMatrix);
      const sizeUnchanged = viewer.canvas.width === 1350 && viewer.canvas.height === 900;
      viewer.dispose();
      return { pendingBeforeResize, phone, pending, poseUnchanged, sizeUnchanged };
    });
    expect(result).toEqual({ pendingBeforeResize: true, phone: { settled: true, samples: 1 }, pending: [true, true, true, false], poseUnchanged: true, sizeUnchanged: true });
  } finally { await server.close(); }
});
