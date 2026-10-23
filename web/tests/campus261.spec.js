import {test, expect} from '@playwright/test';
import {readFile, writeFile} from 'node:fs/promises';

const folder = 'result/blender/stage261';
const read = async path => JSON.parse(await readFile(path, 'utf8'));

async function prepareViewer(page) {
  const release = await read('dist/release.json');
  const module = Object.keys(release.assets).find(path => /^\/assets\/viewer-.*\.js$/.test(path));
  expect(module).toBeTruthy();
  const html = `<!doctype html><link rel="icon" href="data:,"><style>body{margin:0}#stage{width:1000px;height:800px}</style><div id="stage"></div><div id="labels"></div><script type="module">
    import {CampusViewer} from '${module}';
    const c=await(await fetch('/models/catalogue.json')).json();
    if(c.version!=='261')throw Error('Wrong campus');
    const v=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),c.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},c.sourceModelSha256);
    window.viewer=v;v.loadCampusExteriors=async()=>{};await v.load();await v.environmentReady;
    await Promise.all(c.buildings.filter(b=>['CLM'].includes(b.code)).map(b=>v.loadExterior(b)));window.ready=true;
  </script>`;
  await page.route('**/__campus261', route => route.fulfill({contentType: 'text/html', body: html}));
  await page.goto('/__campus261');
  await page.waitForFunction(() => window.ready, null, {timeout: 60000});
}

test('actual overview and detail retain every upper sash pane and registered stile',async({page})=>{
  const probes=await read(folder+'/production-probes.json');
  expect(probes.filter(p=>p.kind==='stile')).toHaveLength(63);
  expect(probes.filter(p=>p.kind==='pane')).toHaveLength(84);
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  try{
    await prepareViewer(page);
    const rows=await page.evaluate(probes=>{
      const v=window.viewer;v.scene.updateMatrixWorld(true);const web=p=>v.controls.target.clone().set(p[0],p[2],-p[1]);const rows=[];
      for(const probe of probes)for(const[level,root,prefix]of[['overview',v.groups.get(probe.code),'WEB_'],['detail',v.exteriors.get(probe.code),'WEB_DETAIL_']]){
        if(!root)throw Error('Missing '+probe.code+level);
        v.raycaster.set(web(probe.origin),web(probe.direction));v.raycaster.near=0;v.raycaster.far=probe.distance+.02;
        const hits=v.raycaster.intersectObject(root,true).map(h=>({distance:h.distance,material:(Array.isArray(h.object.material)?h.object.material[h.face.materialIndex]:h.object.material).name}));
        rows.push({...probe,level,expectedMaterials:probe.materials.map(m=>prefix+m),hits});
      }return rows;
    },probes);
    await writeFile(folder+'/production-geometry-diagnostic.json',JSON.stringify({rows,errors},null,2)+'\n');
    expect(rows).toHaveLength(294);
    for(const row of rows){expect(row.hits.length,JSON.stringify(row)).toBeGreaterThan(0);expect(row.expectedMaterials,JSON.stringify(row)).toContain(row.hits[0].material);expect(row.hits[0].distance,JSON.stringify(row)).toBeCloseTo(row.distance,3);}
    expect(errors).toEqual([]);
    await writeFile(folder+'/production-geometry-verification.json',JSON.stringify({passed:true,rows,errors},null,2)+'\n');
  }finally{await page.evaluate(()=>window.viewer?.dispose()).catch(()=>{});}
});

test('only the Clement exterior asset changes while all public interiors and35rooms keep their identities', async()=>{
  const before=await read(folder+'/catalogue-before.json');
  const current=await read('dist/models/catalogue.json');
  const previousRelease=await read(folder+'/release-before.json');
  const release=await read('dist/release.json');
  expect(current.version).toBe('261');
  expect(current.buildings.map(b=>b.code)).toEqual(before.buildings.map(b=>b.code));
  let exteriors=0,interiors=0,rooms=0,fallbacks=0;
  for(const old of before.buildings){
    const now=current.buildings.find(b=>b.code===old.code);
    if(old.detailedExterior){
      if(['CLM'].includes(old.code))expect(now.detailedExterior.sha256,old.code).not.toBe(old.detailedExterior.sha256);
      else{expect(now.detailedExterior,old.code).toEqual(old.detailedExterior);exteriors++;}}
    if(old.detailedInterior){expect(now.detailedInterior,old.code).toEqual(old.detailedInterior);interiors++;}
    expect(now.interiorSpaces,old.code).toEqual(old.interiorSpaces);
    rooms+=(old.interiorSpaces??[]).length;
    const path='/models/'+old.code.toLowerCase()+'-interior.glb';
    if(previousRelease.assets[path]){expect(release.assets[path],path).toEqual(previousRelease.assets[path]);fallbacks++;}
  }
  for(const code of ['CLM']){
    const prior=await readFile(folder+'/'+code.toLowerCase()+'-detailedExterior.glb');
    const asset=current.buildings.find(b=>b.code===code).detailedExterior;
    const latest=await readFile('dist'+asset.url);
    const glass=bytes=>JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12))).materials.filter(m=>m.extras?.webSurfaceRole==='glazing').sort((a,b)=>a.name.localeCompare(b.name));
    expect(glass(prior).length,code).toBeGreaterThan(0);expect(glass(latest),code).toEqual(glass(prior));
  }
  expect(exteriors).toBe(29);expect(interiors).toBe(25);expect(rooms).toBe(35);expect(fallbacks).toBe(25);
  await writeFile(folder+'/asset-protection.json',JSON.stringify({passed:true,unrelatedExteriors:exteriors,allDefaultInteriors:interiors,allRooms:rooms,allFallbackInteriors:fallbacks},null,2)+'\n');
});
