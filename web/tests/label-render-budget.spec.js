import { test, expect } from '@playwright/test';
import { createServer } from 'vite';
import { mkdir, writeFile } from 'node:fs/promises';

test('labels avoid layout reads and repeated writes while still samples settle', async ({ page }) => {
  const server = await createServer({ logLevel: 'error', server: { host: '127.0.0.1', port: 0 } });
  try {
    await server.listen();
    await page.route('**/__label-budget', route => route.fulfill({ contentType: 'text/html', body:
      '<!doctype html><div id="stage" style="width:960px;height:768px"></div><div id="labels"></div>' }));
    await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__label-budget`);
    const result = await page.evaluate(async () => {
      const { CampusViewer } = await import('/src/viewer.js');
      const { THREE } = await import('/tests/interaction239-fixture.js');
      const catalogue = await (await fetch('/models/catalogue.json')).json();
      const stage = document.querySelector('#stage'), layer = document.querySelector('#labels');
      const viewer = new CampusViewer(stage, layer, catalogue.buildings, () => {}, () => {});
      cancelAnimationFrame(viewer.frame);
      viewer.transition = null;
      viewer.controls.enableDamping = false;
      viewer.controls.update();
      for (const building of catalogue.buildings) {
        viewer.addLabel(building);
        viewer.groups.set(building.code, new THREE.Group());
      }
      // Observe the real label layer, not a substitute layout implementation.
      const observer = new MutationObserver(() => {});
      observer.observe(layer, { subtree: true, attributes: true });
      let reads = 0;
      for (const name of ['clientWidth', 'clientHeight']) {
        const get = Object.getOwnPropertyDescriptor(Element.prototype, name).get;
        Object.defineProperty(stage, name, { configurable: true, get() { reads++; return get.call(this); } });
      }
      const step = () => { viewer.tick(performance.now()); cancelAnimationFrame(viewer.frame); };
      viewer.lastNavigationAt = performance.now() - 1000;
      viewer.needsRender = true;
      step();
      const firstWrites = observer.takeRecords().length;
      reads = 0;
      for (let index = 0; index < 3; index++) step();
      const settleWrites = observer.takeRecords().length, settleReads = reads;
      const initial = viewer.labels.map(label => label.button.style.transform);
      viewer.camera.position.x += 20;
      viewer.controls.update();
      viewer.needsRender = true;
      step();
      const movementWrites = observer.takeRecords().length;
      const positionsChanged = viewer.labels.some((label, i) => label.button.style.transform !== initial[i]);
      viewer.toggleLabels(false); step();
      const allHidden = viewer.labels.every(label => label.button.hidden);
      stage.style.width = '390px'; stage.style.height = '600px'; viewer.resize();
      viewer.toggleLabels(true); step();
      const phoneAspect = viewer.camera.aspect;
      observer.disconnect(); viewer.dispose();
      return { labelCount: catalogue.buildings.length, firstWrites, settleWrites, settleReads,
        movementWrites, positionsChanged, allHidden, phoneAspect };
    });
    await mkdir('result/web/label-render-budget', { recursive: true });
    await writeFile('result/web/label-render-budget/measurement.json', JSON.stringify(result, null, 2) + '\n');
    expect(result.labelCount).toBe(31);
    expect(result.settleReads).toBe(0);
    expect(result.settleWrites).toBe(0);
    expect(result.movementWrites).toBeGreaterThan(0);
    expect(result.positionsChanged).toBe(true);
    expect(result.allHidden).toBe(true);
    expect(result.phoneAspect).toBeCloseTo(390 / 600);
  } finally { await server.close(); }
});
