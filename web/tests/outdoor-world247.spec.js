import { test, expect } from '@playwright/test';
import { createServer } from 'vite';
import { mkdir, writeFile } from 'node:fs/promises';

test('park, streets and daylight form one outdoor world throughout navigation', async ({ page }) => {
  test.setTimeout(150000);
  const folder = 'result/web/outdoor-world247'; await mkdir(folder, { recursive: true });
  const errors = [], requests = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  page.on('request', request => { if (request.url().includes('/environment/')) requests.push(request.url()); });
  const server = await createServer({ logLevel: 'error', server: { host: '127.0.0.1', port: 0 } });
  try {
    await server.listen();
    await page.route('**/__outdoor-world', route => route.fulfill({ contentType: 'text/html', body:
      '<!doctype html><style>body{margin:0}#stage{width:100vw;height:100vh}#labels{display:none}</style><div id="stage"></div><div id="labels"></div>' }));
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__outdoor-world`);
    await page.evaluate(async () => {
      const { CampusViewer } = await import('/src/viewer.js');
      const catalogue = await (await fetch('/models/catalogue.json')).json();
      const viewer = new CampusViewer(document.querySelector('#stage'), document.querySelector('#labels'), catalogue.buildings, () => {}, () => {});
      window.viewer = viewer; window.catalogue = catalogue;
      viewer.loadCampusExteriors = async () => {};
      await viewer.load(); await viewer.environmentReady;
      for (const building of catalogue.buildings.filter(b => b.detailedExterior)) await viewer.loadExterior(building);
      cancelAnimationFrame(viewer.frame); viewer.transition = null;
    });
    const initialRequests = requests.length, records = [];
    for (const width of [1280,390]) {
      await page.setViewportSize({ width, height: 800 });
      for (const view of ['overview','park','park-path','portsmouth','sun']) {
        const record = await page.evaluate(async view => {
          const v = window.viewer;
          const { DAYLIGHT_DIRECTION } = await import('/src/outdoor-environment.js');
          v.resize(); v.home(false); v.toggleContext(true);
          v.camera.fov = view === 'overview' ? 38 : 52; v.updateCameraProjection();
          if (view === 'park') v.moveCamera(v.camera.position.clone().set(-140,150,0), v.controls.target.clone().set(10,0,-185), false);
          if (view === 'park-path') v.moveCamera(v.camera.position.clone().set(-45,2.3,-100), v.controls.target.clone().set(5,7,-175), false);
          if (view === 'portsmouth') v.moveCamera(v.camera.position.clone().set(-43,3.2,29), v.controls.target.clone().set(-49,10,7), false);
          if (view === 'sun') {
            const eye = v.camera.position.clone().set(0,800,0);
            v.moveCamera(eye, eye.clone().addScaledVector(DAYLIGHT_DIRECTION,100), false);
          }
          v.renderPipeline.resetHistory(); v.renderer.shadowMap.needsUpdate = true;
          v.renderPipeline.render({moving:false,stabilize:false});
          const gl = v.renderer.getContext(); gl.finish();
          const times = [];
          for (let i=0;i<7;i++) { const start=performance.now(); v.renderPipeline.render({moving:true}); gl.finish(); times.push(performance.now()-start); }
          v.renderPipeline.render({moving:false,stabilize:false});
          return {view,sky:v.scene.background===v.skyBackdrop,
            hazeBeyondCampus:v.scene.fog.near>v.camera.position.distanceTo(v.controls.target)+400,
            motionMedianMs:times.sort((a,b)=>a-b)[3],geometries:v.renderer.info.memory.geometries,
            skyReady:v.canvas.dataset.skyReady,backdropReady:v.canvas.dataset.skyBackdropReady};
        }, view);
        expect(record.sky).toBe(true); expect(record.hazeBeyondCampus).toBe(true);
        expect(record.skyReady).toBe('true'); expect(record.backdropReady).toBe('true'); expect(record.motionMedianMs).toBeLessThan(80);
        records.push({width,...record});
        await page.locator('canvas').screenshot({path:`${folder}/${view}-${width}.png`});
      }
    }
    const isolation = await page.evaluate(async () => {
      const v=window.viewer,b=window.catalogue.buildings.find(b=>b.code==='CON');
      v.select(b);await v.upgradeModel(b,'exterior');v.transition=null;v.fit(b.bounds,false);v.renderPipeline.render({moving:false,stabilize:false});
      const elevation={neutral:v.scene.background.isColor,noFog:v.scene.fog===null};
      v.mode='interior';v.renderPipeline.render({moving:false,stabilize:false});
      return {elevation,interiorNeutral:v.scene.background.isColor};
    });
    expect(isolation).toEqual({elevation:{neutral:true,noFog:true},interiorNeutral:true});
    expect(requests.length).toBe(initialRequests); expect(errors).toEqual([]);
    await writeFile(`${folder}/verification.json`,JSON.stringify({records,isolation,noNavigationDownloads:requests.length===initialRequests,errors},null,2)+'\n');
  } finally { await page.evaluate(()=>window.viewer?.dispose()).catch(()=>{}); await server.close(); }
});
