import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const read=async path=>JSON.parse(await readFile(path,'utf8'));
test.use({reducedMotion:'reduce',deviceScaleFactor:1.5});

test('saved Sardinia portal supplies this release and retains every unrelated asset',async()=>{
 const before=await read('result/blender/stage119/catalogue-before.json');
 const after=await read('dist/models/catalogue.json');
 const proof=await read('result/blender/stage119/saved-verification.json');
 expect(after.version).toBe('120');const merged=await read('result/blender/stage120/saved-verification.json');expect(after.sourceModelSha256).toBe(merged.sourceModelSha256);expect(merged.baselineSha256).toBe(proof.sourceModelSha256);expect(merged.originalGeometryRetained).toBe(true);
 expect(proof.originalGeometryRetained).toBe(true);expect(proof.originalVisibilityPreserved).toBe(true);
 expect(proof.roofGeometryRetained).toBe(true);expect(proof.clearApertures).toBe(30);
 expect(proof.bayCount).toBe(5);expect(proof.centralEntry).toBe(true);
 for(const b of before.buildings){
  const next=after.buildings.find(x=>x.code===b.code);
  if(!['SAR','KGS','PAR'].includes(b.code))expect(next.detailedExterior,b.code).toEqual(b.detailedExterior);
  expect(next.detailedInterior,b.code).toEqual(b.detailedInterior);
  expect(next.interiorSpaces,b.code).toEqual(b.interiorSpaces);
  expect(next.interiorView,b.code).toEqual(b.interiorView);
 }
 expect(after.spaces).toEqual(before.spaces);expect(after.generatedTextures).toEqual(before.generatedTextures);
});

test('Sardinia brick, stone, glazing and metal agree in overview and close-up',async()=>{
 const c=await read('dist/models/catalogue.json');const b=c.buildings.find(x=>x.code==='SAR');const summaries=[];
 for(const url of ['/models/campus.glb',b.detailedExterior.url]){
  const data=await readFile('dist'+url);const glb=JSON.parse(data.subarray(20,20+data.readUInt32LE(12)));
  const primitives=[];
  for(const mesh of glb.meshes)for(const p of mesh.primitives){
   const m=glb.materials[p.material];if(!m.name.includes('SAR_V119_'))continue;
   const a=glb.accessors[p.attributes.POSITION];
   primitives.push({material:m.name.replace('WEB_DETAIL_','WEB_'),indices:glb.accessors[p.indices].count,min:a.min,max:a.max,pbr:m.pbrMetallicRoughness,finish:m.extras?.surfaceDetail});
  }
  expect(primitives.length).toBe(7);summaries.push(primitives);
 }
 expect(summaries[0]).toEqual(summaries[1]);
});

test('Sardinia exterior, portal close-up, galleries and retained interior work on desktop and phone',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});await page.goto('/#SAR');
  const canvas=page.locator('canvas');
  await expect(canvas).toHaveAttribute('data-detail-ready','exterior-SAR',{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();
  await page.locator('#detail-view').click();await expect(page.locator('#detail-view')).toHaveAttribute('aria-pressed','true');
  await expect(canvas).toHaveAttribute('data-detail-ready','exterior-SAR');
  for(const name of ['sar-exterior','sar-windows']){
   await page.locator(`.detail-gallery img[src*="${name}"]`).click();
   await expect.poll(()=>page.locator('#gallery-image').evaluate(i=>i.complete&&i.naturalWidth>0)).toBeTruthy();
   await page.locator('#gallery-dialog [data-close]').click();
  }
  await page.locator('#interior-view').click();await expect(canvas).toHaveAttribute('data-detail-ready','interior-SAR',{timeout:60000});
 }
 expect(errors).toEqual([]);
});

test('Sardinia entrance gallery matches the settled live close-up',async({page})=>{
 await page.emulateMedia({reducedMotion:'reduce'});
 await page.goto('/#SAR');const canvas=page.locator('canvas');
 await expect(canvas).toHaveAttribute('data-detail-ready','exterior-SAR',{timeout:60000});
 const box=await canvas.boundingBox();const viewport=page.viewportSize();
 await page.setViewportSize({width:Math.round(viewport.width+1400-box.width),height:Math.round(viewport.height+1120-box.height)});
 await page.reload();await expect(canvas).toHaveAttribute('data-detail-ready','exterior-SAR',{timeout:60000});
 await page.locator('#detail-view').click();await page.waitForLoadState('networkidle');
 await expect(page.locator('#detail-view')).toHaveAttribute('aria-pressed','true');
 await page.addStyleTag({content:'#stage > :not(#canvas-container){visibility:hidden!important}'});
 await page.waitForTimeout(250);
 const live=await canvas.screenshot();const image=await readFile('dist/images/sar-windows.webp');
 const error=await page.evaluate(async({live,image})=>{
  const decode=src=>new Promise(resolve=>{const i=new Image();i.onload=()=>resolve(i);i.src=src;});
  const [a,b]=await Promise.all([decode(live),decode(image)]);
  const ctx=document.createElement('canvas').getContext('2d');ctx.canvas.width=1400;ctx.canvas.height=1120;
  ctx.drawImage(a,0,0,1400,1120);const x=ctx.getImageData(0,0,1400,1120).data;
  ctx.clearRect(0,0,1400,1120);ctx.drawImage(b,0,0,1400,1120);const y=ctx.getImageData(0,0,1400,1120).data;
  let sum=0,count=0;
  for(let i=0;i<y.length;i+=4){
   if(Math.abs(y[i]-y[0])+Math.abs(y[i+1]-y[1])+Math.abs(y[i+2]-y[2])<30)continue;
   for(let j=0;j<3;j++){sum+=Math.abs(x[i+j]-y[i+j]);count++;}
  }
  return {average:sum/(255*count),samples:count};
 },{live:`data:image/png;base64,${live.toString('base64')}`,image:`data:image/webp;base64,${image.toString('base64')}`});
 expect(error.samples).toBeGreaterThan(10000);expect(error.average).toBeLessThan(.035);
});
