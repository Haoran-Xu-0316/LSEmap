import {test, expect} from '@playwright/test';
import {readFile, mkdir, writeFile} from 'node:fs/promises';
const read = async path => JSON.parse(await readFile(path, 'utf8'));
const proof = 'result/blender/stage216/browser';

test('edition216 preserves unrelated buildings and all independent rooms', async () => {
 const before = await read('result/blender/stage216/catalogue-before.json');
 const after = await read('web/public/models/catalogue.json');
 expect(after.version).toBe('216');
 for (const old of before.buildings) {
  const current = after.buildings.find(item => item.code === old.code);
  for (const field of ['detailedExterior', 'detailedInterior']) {
   if (old.code !== 'SAW' && old[field]) expect(current[field].sha256, old.code + field).toBe(old[field].sha256);
  }
  for (const room of old.interiorSpaces || []) expect(current.interiorSpaces.find(item => item.id === room.id).detailedInterior.sha256, room.id).toBe(room.detailedInterior.sha256);
 }
 const saw = after.buildings.find(item => item.code === 'SAW');
 expect(saw.interiorSections.map(level => level.id)).toEqual(['G','1','2','3','4','5','6']);
 expect(saw.detailedInterior.sha256).not.toBe(before.buildings.find(item => item.code === 'SAW').detailedInterior.sha256);
 const gallery = await read('web/public/gallery-manifest.json');
 const image = gallery.images.find(item => item.name === 'saw-public-interior');
 expect(image.detail).toBe('interior-SAW');expect(image.sourceModelSha256).toBe(after.sourceModelSha256);
});

for (const width of [1440, 390]) test(`SAW floor sections and isolated rooms remain separate at ${width}px`, async ({page}) => {
 test.setTimeout(150000);await mkdir(proof, {recursive:true});
 await page.setViewportSize({width, height:width === 390 ? 844 : 1000});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto('/#SAW');await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-SAW',{timeout:90000});
 await page.locator('#interior-view').click();await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-SAW',{timeout:60000});
 await expect(page.locator('#interior-sections')).toBeVisible();
 await expect(page.locator('#interior-level option')).toHaveCount(8);await expect(page.locator('#interior-space-scope')).toBeHidden();
 for (const level of ['all','G','3','6']) {
  await page.locator('#interior-level').selectOption(level);
  await expect(page.locator('canvas')).toHaveAttribute('data-interior-section',level);
  await page.waitForTimeout(1000);await page.screenshot({path:`${proof}/saw-${level}-${width}.png`});
 }
 await page.locator('#interior-space').selectOption('saw-denning');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-SAW:saw-denning',{timeout:60000});
 await expect(page.locator('#interior-sections')).toBeHidden();await expect(page.locator('#interior-space-scope')).toBeVisible();
 await expect(page.locator('canvas')).not.toHaveAttribute('data-interior-section',/.+/);
 await page.locator('#interior-space').selectOption('default');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','interior-SAW',{timeout:60000});
 await expect(page.locator('#interior-sections')).toBeVisible();await expect(page.locator('#interior-level')).toHaveValue('all');
 await expect(page.locator('canvas')).not.toHaveAttribute('data-interior-section',/.+/);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.locator('#overview').click();await expect(page.locator('#fallback')).toBeHidden();expect(errors).toEqual([]);
});

test('actual production geometry supports surface footways without resurfacing the tunnel', async ({page}) => {
 test.setTimeout(150000);await mkdir(proof, {recursive:true});
 const release = await read('dist/release.json');
 const module = Object.keys(release.assets).find(path=>/\/viewer-[\w-]+\.js$/.test(path));
 const html = `<!doctype html><style>html,body{margin:0}#scene{width:100vw;height:100vh}#labels{display:none}</style><div id="scene"></div><div id="labels"></div><script type="module">import{CampusViewer}from'${module}';const c=await(await fetch('/models/catalogue.json')).json();window.viewer=new CampusViewer(document.querySelector('#scene'),document.querySelector('#labels'),c.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},c.sourceModelSha256);await viewer.load();await viewer.environmentReady;await new Promise(r=>setTimeout(r,1000));cancelAnimationFrame(viewer.frame);viewer.transition=null;viewer.controls.enableDamping=false;viewer.toggleContext(true);viewer.scene.updateMatrixWorld(true);window.ready=true;</script>`;
 await page.route('**/__campus216',route=>route.fulfill({contentType:'text/html',body:html}));
 const errors=[];page.on('pageerror',error=>errors.push(error.message));page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});
 await page.goto('/__campus216');await page.waitForFunction(()=>window.ready,null,{timeout:90000});
 const rays=await page.evaluate(()=>{
  const w=viewer;
  return [{name:'underground-exclusive',x:-59.4476302605,z:168.539049565,y:.1},{name:'mapped-footway',x:-146.33,z:347.5,y:.1},{name:'under-footway',x:-146.33,z:347.5,y:0}].map(sample=>{
   w.raycaster.set(w.camera.position.clone().set(sample.x,sample.y,sample.z),w.camera.position.clone().set(0,-1,0));
   const hit=w.raycaster.intersectObject(w.campus,true)[0];const material=hit?(Array.isArray(hit.object.material)?hit.object.material[hit.face.materialIndex]:hit.object.material):null;
   return {...sample,height:hit?.point.y,material:material?.name};
  });
 });
 expect(rays[0].height).toBeCloseTo(-.05,3);expect(rays[0].material).toMatch(/Pale campus paving/);
 expect(rays[1].height).toBeCloseTo(.024,3);expect(rays[1].material).toMatch(/footway_courses|flush_edge_courses/);
 expect(rays[2].height).toBeCloseTo(-.05,3);expect(rays[2].material).toMatch(/Pale campus paving/);
 await page.evaluate(()=>{const w=viewer;w.camera.position.set(-145,75,405);w.controls.target.set(-136,0,290);w.controls.update();w.camera.updateMatrixWorld();w.renderPipeline.resetHistory();for(let i=0;i<4;i++)w.renderPipeline.render({moving:false});});
 await page.locator('canvas').screenshot({path:proof+'/aldwych-context.png'});
 const floors=await page.evaluate(async()=>{
  const w=viewer,c=await(await fetch('/models/catalogue.json')).json(),b=c.buildings.find(item=>item.code==='SAW');
  w.select(b);await w.showInterior(b);await w.upgradeModel(b,'interior');
  const datums=[0,3.45,8.1,11.1,14.1,18,21.9];
  const measure=group=>{
   const areas=datums.map(()=>0);group.updateMatrixWorld(true);
   group.traverse(mesh=>{if(!mesh.isMesh)return;const position=mesh.geometry.attributes.position,index=mesh.geometry.index;
    for(let offset=0;offset<(index?index.count:position.count);offset+=3){
     const vertices=[0,1,2].map(i=>w.camera.position.clone().fromBufferAttribute(position,index?index.getX(offset+i):offset+i).applyMatrix4(mesh.matrixWorld));
     const floor=datums.findIndex(y=>vertices.every(point=>Math.abs(point.y-y)<.002));if(floor<0)continue;
     const[a,b,c]=vertices;areas[floor]+=Math.abs((b.x-a.x)*(c.z-a.z)-(b.z-a.z)*(c.x-a.x))*.5;
    }
   });return areas;
  };
  return{datums,fallback:measure(w.interiors.get('SAW:default')),detail:measure(w.activeDetail.group)};
 });
 for(const type of ['fallback','detail'])for(const [i,area]of floors[type].entries())expect(area,type+' floor '+floors.datums[i]).toBeGreaterThan(i===0?500:400);
 expect(errors).toEqual([]);await writeFile(proof+'/ground-rays.json',JSON.stringify({rays,floors,errors},null,2)+'\n');await page.evaluate(()=>viewer.dispose());
});
