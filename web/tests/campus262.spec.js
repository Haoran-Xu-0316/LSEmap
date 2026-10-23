import {test, expect} from '@playwright/test';
import {readFile, writeFile} from 'node:fs/promises';

const folder = 'result/blender/stage262';
const read = async path => JSON.parse(await readFile(path, 'utf8'));

async function prepareViewer(page) {
  const release = await read('dist/release.json');
  const module = Object.keys(release.assets).find(path => /^\/assets\/viewer-.*\.js$/.test(path));
  expect(module).toBeTruthy();
  const html = `<!doctype html><link rel="icon" href="data:,"><style>body{margin:0}#stage{width:1000px;height:800px}</style><div id="stage"></div><div id="labels"></div><script type="module">
    import {CampusViewer} from '${module}';
    const c=await(await fetch('/models/catalogue.json')).json();
    if(c.version!=='262')throw Error('Wrong campus');
    const v=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),c.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},c.sourceModelSha256);
    window.viewer=v;v.loadCampusExteriors=async()=>{};await v.load();await v.environmentReady;
    await Promise.all(c.buildings.filter(b=>['OLD','SAW'].includes(b.code)).map(b=>v.loadExterior(b)));window.ready=true;
  </script>`;
  await page.route('**/__campus262', route => route.fulfill({contentType: 'text/html', body: html}));
  await page.goto('/__campus262');
  await page.waitForFunction(() => window.ready, null, {timeout: 60000});
}

test('actual overview and detail retain the supported street fixtures',async({page})=>{
  const probes=await read(folder+'/production-probes.json');
  expect(probes.length).toBeGreaterThan(40);
  expect(new Set(probes.map(p=>p.object)).size).toBe(9);
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
    expect(rows).toHaveLength(probes.length*2);
    for(const row of rows){expect(row.hits.length,JSON.stringify(row)).toBeGreaterThan(0);expect(row.expectedMaterials,JSON.stringify(row)).toContain(row.hits[0].material);expect(row.hits[0].distance,JSON.stringify(row)).toBeCloseTo(row.distance,3);}
    expect(errors).toEqual([]);
    await writeFile(folder+'/production-geometry-verification.json',JSON.stringify({passed:true,rows,errors},null,2)+'\n');
  }finally{await page.evaluate(()=>window.viewer?.dispose()).catch(()=>{});}
});

test('only the two street-owner exterior assets change while all public interiors and35rooms keep their identities', async()=>{
  const before=await read(folder+'/catalogue-before.json');
  const current=await read('dist/models/catalogue.json');
  const previousRelease=await read(folder+'/release-before.json');
  const release=await read('dist/release.json');
  expect(current.version).toBe('262');
  expect(current.buildings.map(b=>b.code)).toEqual(before.buildings.map(b=>b.code));
  let exteriors=0,interiors=0,rooms=0,fallbacks=0;
  for(const old of before.buildings){
    const now=current.buildings.find(b=>b.code===old.code);
    if(old.detailedExterior){
      if(['OLD','SAW'].includes(old.code))expect(now.detailedExterior.sha256,old.code).not.toBe(old.detailedExterior.sha256);
      else{expect(now.detailedExterior,old.code).toEqual(old.detailedExterior);exteriors++;}}
    if(old.detailedInterior){expect(now.detailedInterior,old.code).toEqual(old.detailedInterior);interiors++;}
    expect(now.interiorSpaces,old.code).toEqual(old.interiorSpaces);
    rooms+=(old.interiorSpaces??[]).length;
    const path='/models/'+old.code.toLowerCase()+'-interior.glb';
    if(previousRelease.assets[path]){expect(release.assets[path],path).toEqual(previousRelease.assets[path]);fallbacks++;}
  }
  for(const code of ['OLD','SAW']){
    const prior=await readFile(folder+'/'+code.toLowerCase()+'-detailedExterior.glb');
    const asset=current.buildings.find(b=>b.code===code).detailedExterior;
    const latest=await readFile('dist'+asset.url);
    const glass=bytes=>JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12))).materials.filter(m=>m.extras?.webSurfaceRole==='glazing').sort((a,b)=>a.name.localeCompare(b.name));
    expect(glass(prior).length,code).toBeGreaterThan(0);for(const original of glass(prior)){expect(glass(latest).find(m=>m.name===original.name),code+original.name).toEqual(original);}
  }
  expect(exteriors).toBe(28);expect(interiors).toBe(25);expect(rooms).toBe(35);expect(fallbacks).toBe(25);
  await writeFile(folder+'/asset-protection.json',JSON.stringify({passed:true,unrelatedExteriors:exteriors,allDefaultInteriors:interiors,allRooms:rooms,allFallbackInteriors:fallbacks},null,2)+'\n');
});
