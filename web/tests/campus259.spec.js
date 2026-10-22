import {test, expect} from '@playwright/test';
import {readFile, writeFile} from 'node:fs/promises';

const folder = 'result/blender/stage259';
const read = async path => JSON.parse(await readFile(path, 'utf8'));

async function prepareViewer(page) {
  const release = await read('dist/release.json');
  const module = Object.keys(release.assets).find(path => /^\/assets\/viewer-.*\.js$/.test(path));
  expect(module).toBeTruthy();
  const html = `<!doctype html><link rel="icon" href="data:,"><style>body{margin:0}#stage{width:1000px;height:800px}</style><div id="stage"></div><div id="labels"></div><script type="module">
    import {CampusViewer} from '${module}';
    const c=await(await fetch('/models/catalogue.json')).json();
    if(c.version!=='259')throw Error('Wrong campus');
    const v=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),c.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},c.sourceModelSha256);
    window.viewer=v;v.loadCampusExteriors=async()=>{};await v.load();await v.environmentReady;
    await v.loadExterior(c.buildings.find(b=>b.code==='OLD'));window.ready=true;
  </script>`;
  await page.route('**/__campus259', route => route.fulfill({contentType: 'text/html', body: html}));
  await page.goto('/__campus259');
  await page.waitForFunction(() => window.ready, null, {timeout: 60000});
}

test('the eight Houghton boxes and clear upper windows agree in actual overview and detail GLBs', async ({page}) => {
  const audit = await read('result/blender/old259/audit.json');
  const proof = await read('result/blender/old259/verification.json');
  const frame = await read('result/blender/stage52/old-houghton-audit.json');
  const world = ([x,y,z]) => frame.origin.map((p, i) => p + frame.right[i]*x + frame.outward[i]*y + (i===2?z:0));
  const boxes = audit.planters.map(box => ({id: box.id, kind: 'box',
    origin: world([box.x, .9, box.low+.08]), direction: frame.outward.map(v=>-v),
    distance: .9-box.boxDepth[1], material: audit.replacementMaterialBindings.OLD259_Houghton_window_boxes[0]}));
  const panes = proof.proof.unobstructedUpperPaneRays.map((ray,index)=>({id:index,kind:'pane',origin:ray.start,
    direction:ray.direction,distance:ray.glassDistance,material:'GLASS181_shell_OLD172_dielectric_OLD_V112_glass'}));
  expect(boxes).toHaveLength(8);expect(panes).toHaveLength(120);
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  try {
    await prepareViewer(page);
    const rows=await page.evaluate(probes=>{
      const v=window.viewer;v.scene.updateMatrixWorld(true);
      const web=p=>v.controls.target.clone().set(p[0],p[2],-p[1]);
      const rows=[];
      for(const [level,root,prefix]of [['overview',v.groups.get('OLD'),'WEB_'],['detail',v.exteriors.get('OLD'),'WEB_DETAIL_']]){
        if(!root)throw Error('Missing OLD '+level);
        for(const probe of probes){
          v.raycaster.set(web(probe.origin),web(probe.direction));v.raycaster.near=0;v.raycaster.far=probe.distance+.02;
          const hits=v.raycaster.intersectObject(root,true).map(hit=>{
            const m=Array.isArray(hit.object.material)?hit.object.material[hit.face.materialIndex]:hit.object.material;
            return{distance:hit.distance,material:m.name};});
          rows.push({...probe,level,expectedMaterial:prefix+probe.material,hits});
        }
      }
      return rows;
    },[...boxes,...panes]);
    await writeFile(folder+'/production-old-diagnostic.json',JSON.stringify({rows,errors},null,2)+'\n');
    expect(rows).toHaveLength(256);
    for(const row of rows){expect(row.hits.length,JSON.stringify(row)).toBeGreaterThan(0);
      expect(row.hits[0].material,JSON.stringify(row)).toBe(row.expectedMaterial);
      expect(row.hits[0].distance,JSON.stringify(row)).toBeCloseTo(row.distance,3);}
    expect(errors).toEqual([]);
    await writeFile(folder+'/production-old-verification.json',JSON.stringify({passed:true,boxes:8,clearPaneRays:120,levels:2,rows,errors},null,2)+'\n');
  } finally {await page.evaluate(()=>window.viewer?.dispose()).catch(()=>{});}
});

test('only the two exterior assets change while all public interiors and35rooms keep their identities', async()=>{
  const before=await read(folder+'/catalogue-before.json');
  const current=await read('dist/models/catalogue.json');
  const previousRelease=await read(folder+'/release-before.json');
  const release=await read('dist/release.json');
  expect(current.version).toBe('259');
  expect(current.buildings.map(b=>b.code)).toEqual(before.buildings.map(b=>b.code));
  let exteriors=0,interiors=0,rooms=0,fallbacks=0;
  for(const old of before.buildings){
    const now=current.buildings.find(b=>b.code===old.code);
    if(old.detailedExterior){
      if(['OLD','LRB'].includes(old.code))expect(now.detailedExterior.sha256,old.code).not.toBe(old.detailedExterior.sha256);
      else{expect(now.detailedExterior,old.code).toEqual(old.detailedExterior);exteriors++;}}
    if(old.detailedInterior){expect(now.detailedInterior,old.code).toEqual(old.detailedInterior);interiors++;}
    expect(now.interiorSpaces,old.code).toEqual(old.interiorSpaces);
    rooms+=(old.interiorSpaces??[]).length;
    const path='/models/'+old.code.toLowerCase()+'-interior.glb';
    if(previousRelease.assets[path]){expect(release.assets[path],path).toEqual(previousRelease.assets[path]);fallbacks++;}
  }
  expect(exteriors).toBe(28);expect(interiors).toBe(25);expect(rooms).toBe(35);expect(fallbacks).toBe(25);
  await writeFile(folder+'/asset-protection.json',JSON.stringify({passed:true,unrelatedExteriors:exteriors,allDefaultInteriors:interiors,allRooms:rooms,allFallbackInteriors:fallbacks},null,2)+'\n');
});
