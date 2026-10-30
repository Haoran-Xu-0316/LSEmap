import {test, expect} from '@playwright/test';
import {readFile, writeFile} from 'node:fs/promises';

const out = 'result/web/release283';
const read = async path => JSON.parse(await readFile(path, 'utf8'));

test('reviewed OLD and MAR surfaces survive desktop and mobile loading', async ({browser}) => {
  const release = await read('dist/release.json');
  const module = Object.keys(release.assets).find(path => /^\/assets\/viewer-.*\.js$/.test(path));
  const probes = await read('result/blender/stage283/production-probes.json');
  expect(new Set(probes.map(p => p.object)).size).toBe(10);
  const html = `<!doctype html><link rel="icon" href="data:,"><style>body{margin:0}#stage{width:100vw;height:100vh}</style><div id="stage"></div><div id="labels"></div><script type="module">
  import {CampusViewer} from '${module}';
  const c=await(await fetch('/models/catalogue.json')).json();
  if(c.version!=='283')throw Error('Wrong campus edition');
  window.catalogue=c;
  const v=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),c.buildings,()=>{},()=>{window.lost=true;},()=>{},c.sourceModelSha256);
  window.viewer=v;v.loadCampusExteriors=async()=>{};
  await v.load();await v.environmentReady;window.ready=true;
  </script>`;
  const rows = [], errors = [];
  for (const mobile of [false, true]) {
    const context = await browser.newContext({viewport: {width: mobile ? 390 : 1000, height: 800}, hasTouch: mobile,
      userAgent: mobile ? 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) EdgiOS/131.0' : undefined});
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(error.message));
    try {
      await page.route('**/__campus283', route => route.fulfill({contentType: 'text/html', body: html}));
      await page.goto('/__campus283');
      await page.waitForFunction(() => window.ready, null, {timeout: 90000});
      for (const code of ['OLD', 'MAR', 'CONTEXT']) {
        if (mobile && code !== 'CONTEXT') await page.evaluate(async code => {
          const b = catalogue.buildings.find(b => b.code === code);
          viewer.select(b);await viewer.upgradeModel(b, 'exterior');await viewer.localContext.ready;
        }, code);
        const result = await page.evaluate(({code, probes}) => {
          const v = viewer;
          const root = v.budget.mobile && code !== 'CONTEXT' ? v.exteriors.get(code) : v.groups.get(code);
          if (!root?.children.length) throw Error('Missing building ' + code);
          v.scene.updateMatrixWorld(true);
          const web = p => v.controls.target.clone().set(p[0], p[2], -p[1]);
          return {mobile: v.budget.mobile, lost: !!window.lost || v.renderer.getContext().isContextLost(), rows: probes.map(p => {
            v.raycaster.set(web(p.origin), web(p.direction));v.raycaster.near=0;v.raycaster.far=p.distance+.02;
            const hits=v.raycaster.intersectObject(root,true).map(h=>({distance:h.distance,material:(Array.isArray(h.object.material)?h.object.material[h.face.materialIndex]:h.object.material).name}));
            return {...p,hits,expected:p.materials.map(m=>(v.budget.mobile&&code!=='CONTEXT'?'WEB_DETAIL_':'WEB_')+m)};
          })};
        }, {code, probes: probes.filter(p => p.code === code)});
        expect(result.mobile).toBe(mobile);expect(result.lost).toBe(false);
        for (const row of result.rows) expect(row.hits.some(h => row.expected.includes(h.material) && Math.abs(h.distance-row.distance)<.001), JSON.stringify(row)).toBeTruthy();
        rows.push({mobile, code, matched: result.rows.length});
      }
    } finally {
      await page.evaluate(() => window.viewer?.dispose()).catch(() => {});
      await context.close();
    }
  }
  expect(errors).toEqual([]);
  await writeFile(out+'/geometry-verification.json', JSON.stringify({passed:true, rows, errors}, null, 2)+'\n');
});

test('all unrelated building, room and texture identities remain unchanged', async () => {
  const before=await read(out+'/catalogue-before.json'), now=await read('dist/models/catalogue.json');
  const oldRelease=await read(out+'/release-before.json'), release=await read('dist/release.json');
  expect(now.version).toBe('283');
  expect(now.buildings.map(b=>b.code)).toEqual(before.buildings.map(b=>b.code));
  let rooms=0, exteriors=0, interiors=0;
  for(const old of before.buildings){
    const current=now.buildings.find(b=>b.code===old.code);
    if(old.detailedExterior){
      if(['OLD','MAR'].includes(old.code))expect(current.detailedExterior.sha256).not.toBe(old.detailedExterior.sha256);
      else{expect(current.detailedExterior,old.code).toEqual(old.detailedExterior);exteriors++;}
    }
    if(old.detailedInterior){
      if(old.code==='MAR')expect(current.detailedInterior.sha256).not.toBe(old.detailedInterior.sha256);
      else{expect(current.detailedInterior,old.code).toEqual(old.detailedInterior);interiors++;}
    }
    expect(current.interiorSpaces,old.code).toEqual(old.interiorSpaces);
    rooms+=(old.interiorSpaces??[]).length;
  }
  for(const[path,hash]of Object.entries(oldRelease.assets))if(path!=='/models/mar-interior.glb'&&/^\/models\/[^/]+-interior\.glb$/.test(path))expect(release.assets[path],path).toEqual(hash);
  expect(now.generatedTextures).toEqual(before.generatedTextures);
  expect(rooms).toBe(35);expect(exteriors).toBe(28);expect(interiors).toBe(24);
  await writeFile(out+'/asset-protection.json',JSON.stringify({passed:true,exteriors,interiors,rooms,generatedTexturesPreserved:true},null,2)+'\n');
});
