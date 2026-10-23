import { test, expect } from '@playwright/test';
import { createServer } from 'vite';
import { mkdir, readFile, writeFile } from 'node:fs/promises';

const output = 'result/web/scene-context263';

test('all detailed buildings keep a bounded public street crop across repeated selections', async ({ page }) => {
  test.setTimeout(240000);
  await mkdir(output, { recursive: true });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  const server = await createServer({ server: { host: '127.0.0.1', port: 0 }, logLevel: 'error', plugins: [{
    name: 'all-selected-context263', configureServer(server) { server.middlewares.use('/__all-context263', (_, response) => {
      response.setHeader('Content-Type', 'text/html'); response.end(`<!doctype html><link rel="icon" href="data:,"><style>body{margin:0}#stage{width:1000px;height:800px}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">
        import * as THREE from '/@fs/${process.cwd()}/node_modules/three/build/three.module.js';
        import {CampusViewer} from '/src/viewer.js';
        const c=await(await fetch('/models/catalogue.json')).json();
        const v=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),c.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},c.sourceModelSha256);
        window.viewer=v;window.THREE=THREE;window.catalogue=c;v.loadCampusExteriors=async()=>{};await v.load();await v.environmentReady;cancelAnimationFrame(v.frame);v.controls.enableDamping=false;window.ready=true;
      </script>`);
    }); },
  }] });
  await server.listen();
  const rows = [];
  const cycleProbes = JSON.parse(await readFile('result/blender/stage263/production-probes.json', 'utf8')).filter(probe => probe.code === 'LANDSCAPE' && probe.object === 'SHEFFIELD263_Five_U_cycle_stands');
  let cycleBank;
  try {
    await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__all-context263`);
    await page.waitForFunction(() => window.ready, null, { timeout: 90000 });
    const buildings = await page.evaluate(() => catalogue.buildings.filter(b => b.detailedExterior).map(b => b.code));
    for (const code of buildings) {
      const row = await page.evaluate(async code => {
        const v=viewer,b=catalogue.buildings.find(b=>b.code===code);
        const started=performance.now();v.select(b);const selectMs=performance.now()-started;
        await Promise.all([v.localContext.ready,v.upgradeModel(b,'exterior')]);
        if(v.transition)v.moveCamera(v.transition.position,v.transition.target,false);
        v.controls.update();v.camera.updateMatrixWorld();
        const local=v.localContext.activeGroup,region=local.userData.streetContext.bounds;
        const actualBounds=new THREE.Box3().setFromObject(local);
        const oversize=[];
        local.traverse(object=>{
          if(!object.isMesh||/foliage|bark|Oak public interior/i.test(object.material.name))return;
          const box=new THREE.Box3().setFromObject(object);
          const excess=Math.max(region.min[0]-box.min.x,box.max.x-region.max[0],region.min[2]-box.min.z,box.max.z-region.max[2]);
          if(excess>8)oversize.push({name:object.name,material:object.material.name,excess});
        });
        const allowed=new Set([code,code==='PAN'?'FAW':code==='FAW'?'PAN':null]);
        const otherBuildings=[...v.groups].filter(([name,group])=>!['SITE','LANDSCAPE','CONTEXT'].includes(name)&&group.visible&&!allowed.has(name)).map(([name])=>name);
        const otherExteriors=[...v.exteriors].filter(([name,group])=>group.visible&&!allowed.has(name)).map(([name])=>name);
        return{code,selectMs,...local.userData.streetContext,actualBounds:{min:actualBounds.min.toArray(),max:actualBounds.max.toArray()},cacheSize:v.localContext.cache.size,publicOriginalsVisible:['SITE','LANDSCAPE','CONTEXT'].filter(code=>v.groups.get(code)?.visible),visibleContextGroups:v.localContext.root.children.filter(group=>group.visible).length,otherBuildings,otherExteriors,oversize,ready:v.canvas.dataset.detailReady};
      }, code);
      rows.push(row);
      if (['SAW', 'OLD', 'CLM'].includes(code)) {
        await page.evaluate(()=>{for(let i=0;i<4;i++)viewer.renderPipeline.render({moving:false,progressive:true,restart:i===0});});
        await page.locator('canvas').screenshot({ path: `${output}/all-selected-${code.toLowerCase()}.png` });
      }
    }
    cycleBank = await page.evaluate(async probes => {
      const v=viewer,b=catalogue.buildings.find(b=>b.code==='SAW');v.select(b);await Promise.all([v.localContext.ready,v.upgradeModel(b,'exterior')]);
      v.scene.updateMatrixWorld(true);
      const transform = vector => new THREE.Vector3(vector[0],vector[2],-vector[1]);
      return probes.map(probe=>{
        const ray=new THREE.Raycaster(transform(probe.origin),transform(probe.direction).normalize(),0,.1);
        const original=ray.intersectObject(v.groups.get('LANDSCAPE'),true).find(hit=>probe.materials.includes(hit.object.material.name.replace(/^WEB_(?:DETAIL_)?/,'')));
        const local=ray.intersectObject(v.localContext.activeGroup,true).find(hit=>probe.materials.includes(hit.object.material.name.replace(/^WEB_(?:DETAIL_)?/,'')));
        return{stand:Math.round((probe.origin[1]+21.4391404141)/1.05)+2,origin:transform(probe.origin).toArray(),originalDistance:original?.distance??null,localDistance:local?.distance??null,difference:original&&local?original.point.distanceTo(local.point):null,material:local?.object.material.name??null};
      });
    },cycleProbes);
    await page.evaluate(()=>{const v=viewer;v.camera.fov=48;v.updateCameraProjection();v.moveCamera(new THREE.Vector3(-48,3.5,28),new THREE.Vector3(-54.98,.5,21.44),false);v.controls.update();v.camera.updateMatrixWorld();for(let i=0;i<4;i++)v.renderPipeline.render({moving:false,progressive:true,restart:i===0});});
    await page.locator('canvas').screenshot({path:`${output}/saw-five-cycle-stands.png`});
    const lifecycle = await page.evaluate(async () => {
      const v=viewer,b=catalogue.buildings.find(b=>b.code==='SAW');v.select(b);await Promise.all([v.localContext.ready,v.upgradeModel(b,'exterior')]);
      await v.showInterior(b);await v.upgradeModel(b,'interior');
      const inside={localVisible:v.localContext.root.visible,canvasMode:v.mode,campusVisible:v.campus.visible};
      v.home(false);const overview={localVisible:v.localContext.root.visible,siteVisible:v.groups.get('SITE').visible,landscapeVisible:v.groups.get('LANDSCAPE').visible};
      return{inside,overview,sourceModelSha256:catalogue.sourceModelSha256,version:catalogue.version,cacheSize:v.localContext.cache.size};
    });
    await writeFile(`${output}/all-buildings-verification.json`, JSON.stringify({ rows, cycleBank, lifecycle, errors }, null, 2) + '\n');
    expect(errors).toEqual([]); expect(rows).toHaveLength(30);
    for(const row of rows){
      expect(row.cacheSize,row.code).toBeLessThanOrEqual(3);
      expect(row.visibleContextGroups,row.code).toBe(1);
      expect(row.publicOriginalsVisible,row.code).toEqual([]);
      expect(row.otherBuildings,row.code).toEqual([]);expect(row.otherExteriors,row.code).toEqual([]);
      expect(row.oversize,row.code).toEqual([]);
      expect(row.ready,row.code).toBe('exterior-'+row.code);
      expect(row.selectMs,row.code).toBeLessThan(20);
    }
    expect([...new Set(cycleBank.map(hit=>hit.stand))].sort()).toEqual([0,1,2,3,4]);
    for(const hit of cycleBank){expect(hit.originalDistance).not.toBeNull();expect(hit.localDistance).not.toBeNull();expect(hit.difference).toBeLessThan(1e-6);}
    expect(lifecycle.inside).toEqual({localVisible:false,canvasMode:'interior',campusVisible:false});
    expect(lifecycle.overview).toEqual({localVisible:false,siteVisible:true,landscapeVisible:true});
  } finally { await page.evaluate(()=>window.viewer?.dispose()).catch(()=>{});await server.close(); }
});
