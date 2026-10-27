import {test, expect} from '@playwright/test';
import {readFile, writeFile} from 'node:fs/promises';
const out = 'result/web/release279';
const read = async path => JSON.parse(await readFile(path, 'utf8'));

test('accepted street surfaces survive both desktop and derived mobile exports', async ({browser}) => {
  const release = await read('dist/release.json');
  const module = Object.keys(release.assets).find(p=>/^\/assets\/viewer-.*\.js$/.test(p));
  const allProbes = await read('result/blender/stage279/production-probes.json');
  expect(new Set(allProbes.map(p=>p.object)).size).toBe(4);
  const probes = allProbes;
  const html = `<!doctype html><link rel="icon" href="data:,"><style>body{margin:0}#stage{width:100vw;height:100vh}</style><div id="stage"></div><div id="labels"></div><script type="module">
  import {CampusViewer} from '${module}';const c=await(await fetch('/models/catalogue.json')).json();if(c.version!=='279')throw Error('Wrong campus');
  const v=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),c.buildings,()=>{},()=>{window.lost=true;},()=>{},c.sourceModelSha256);
  window.viewer=v;v.loadCampusExteriors=async()=>{};await v.load();await v.environmentReady;
  window.ready=true;
  </script>`;
  const rows=[], errors=[];
  for (const mobile of [false,true]) {
    const context=await browser.newContext({viewport:{width:mobile?390:1000,height:800},hasTouch:mobile,
      userAgent:mobile?'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) EdgiOS/131.0':undefined});
    const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
    try {
      await page.route('**/__campus279',r=>r.fulfill({contentType:'text/html',body:html}));
      await page.goto('/__campus279');await page.waitForFunction(()=>window.ready,null,{timeout:90000});
      const result=await page.evaluate(probes=>{
        const v=viewer,roots={CONTEXT:v.groups.get('CONTEXT')};if(Object.values(roots).some(r=>!r?.children.length))throw Error('Missing context or SAW');v.scene.updateMatrixWorld(true);
        const web=p=>v.controls.target.clone().set(p[0],p[2],-p[1]);
        return {profile:v.budget.mobile,lost:!!window.lost||v.renderer.getContext().isContextLost(),rows:probes.map(p=>{
          v.raycaster.set(web(p.origin),web(p.direction));v.raycaster.near=0;v.raycaster.far=p.distance+.02;
          const hits=v.raycaster.intersectObject(roots[p.code],true).map(h=>({distance:h.distance,material:(Array.isArray(h.object.material)?h.object.material[h.face.materialIndex]:h.object.material).name}));
          return {...p,hits,expected:p.materials.map(m=>'WEB_'+m)};
        })};
      },probes);
      expect(result.profile).toBe(mobile);expect(result.lost).toBe(false);
      for(const row of result.rows)expect(row.hits.some(h=>row.expected.includes(h.material)&&Math.abs(h.distance-row.distance)<.001),JSON.stringify(row)).toBeTruthy();
      rows.push({mobile,matched:result.rows.length,CONTEXT:'overview'});
    } finally {await page.evaluate(()=>window.viewer?.dispose()).catch(()=>{});await context.close();}
  }
  expect(errors).toEqual([]);
  await writeFile(out+'/geometry-verification.json',JSON.stringify({passed:true,rows,errors,scope:'All97 native street surface probes match desktop and derived mobile overviews.'},null,2)+'\n');
});

test('unrelated building and all35room asset identities remain intact', async()=>{
  const before=await read(out+'/catalogue-before.json'),now=await read('dist/models/catalogue.json');
  expect(now.version).toBe('279');expect(now.buildings.map(b=>b.code)).toEqual(before.buildings.map(b=>b.code));
  const priorRelease=await read(out+'/release-before.json'),release=await read('dist/release.json');
  let exteriors=0,interiors=0,rooms=0;
  for(const old of before.buildings){const current=now.buildings.find(b=>b.code===old.code);
    if(old.detailedExterior){expect(current.detailedExterior,old.code).toEqual(old.detailedExterior);exteriors++;}
    if(old.detailedInterior){expect(current.detailedInterior,old.code).toEqual(old.detailedInterior);interiors++;}
    expect(current.interiorSpaces,old.code).toEqual(old.interiorSpaces);rooms+=(old.interiorSpaces??[]).length;
  }
  for(const[path,hash]of Object.entries(priorRelease.assets))if(/^\/models\/[^/]+-interior\.glb$/.test(path))expect(release.assets[path],path).toEqual(hash);
  for(const value of before.generatedTextures)expect(now.generatedTextures.find(t=>t.name===value.name),value.name).toEqual(value);
  expect(exteriors).toBe(30);expect(interiors).toBe(25);expect(rooms).toBe(35);
  await writeFile(out+'/asset-protection.json',JSON.stringify({passed:true,exteriors,interiors,rooms,previousGeneratedTexturesPreserved:true},null,2)+'\n');
});
