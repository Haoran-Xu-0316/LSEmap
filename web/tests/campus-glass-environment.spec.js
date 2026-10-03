import {test,expect} from '@playwright/test';
import {createServer} from 'vite';
import {writeFile,readFile} from 'node:fs/promises';

test('production overview every exterior and three interiors share the intended glazing environment',async({page})=>{
 test.setTimeout(120000);
 const html=`<!doctype html><style>body{margin:0}#canvas{width:960px;height:768px}#labels{display:none}</style><div id="canvas"></div><div id="labels"></div><script type="module">
 import {CampusViewer} from '/src/viewer.js';
 const catalogue=await(await fetch('/models/catalogue.json')).json();
 const viewer=new CampusViewer(document.querySelector('#canvas'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},catalogue.sourceModelSha256);
 await viewer.load();
 await Promise.all(catalogue.buildings.filter(b=>b.detailedExterior).map(b=>viewer.loadExterior(b)));
 const inspect=group=>{let glass=0,bound=0,clearPaneMeshes=0,opaquePaneShadowErrors=[];group.traverse(o=>{if(!o.isMesh)return;const materials=Array.isArray(o.material)?o.material:[o.material];for(const m of materials)if(/glass|glazing/i.test(m.name)){glass++;if(m.envMap===viewer.environmentTarget.texture&&m.envMapIntensity===1.65)bound++;}if(materials.length&&materials.every(m=>/glass|glazing/i.test(m.name)&&((m.transparent&&m.opacity<1)||m.transmission>0)&&!m.alphaTest&&!m.alphaToCoverage)){clearPaneMeshes++;if(o.castShadow)opaquePaneShadowErrors.push(o.name);}});return {glass,bound,clearPaneMeshes,opaquePaneShadowErrors};};
 const overview=inspect(viewer.campus),exteriors=catalogue.buildings.filter(b=>b.detailedExterior).map(b=>({code:b.code,...inspect(viewer.exteriors.get(b.code))})),interiors=[];
 for(const code of ['MAR','OLD','CBG']){const b=catalogue.buildings.find(b=>b.code===code);viewer.select(b);await viewer.showInterior(b);await viewer.upgradeModel(b,'interior');interiors.push({code,base:inspect(viewer.interiors.get(viewer.activeInterior.key)),detailed:inspect(viewer.activeDetail.group),ready:viewer.canvas.dataset.detailReady});}
 window.proof={overview,exteriors,interiors,sourceModelSha256:catalogue.sourceModelSha256,version:catalogue.version};
 viewer.dispose();
 </script>`;
 const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{name:'campus-glazing-check',configureServer(s){s.middlewares.use('/__campus-glazing-check',(_,res)=>{res.setHeader('Content-Type','text/html');res.end(html);});}}]});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 try{
  await server.listen();await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__campus-glazing-check`);
  await page.waitForFunction(()=>window.proof,null,{timeout:100000});const proof=await page.evaluate(()=>window.proof);
  expect(errors).toEqual([]);expect(proof.version).toBe('139');
  expect(proof.overview.glass).toBeGreaterThan(0);expect(proof.overview.bound).toBe(proof.overview.glass);expect(proof.overview.clearPaneMeshes).toBeGreaterThan(0);expect(proof.overview.opaquePaneShadowErrors).toEqual([]);
  const catalogue=JSON.parse(await readFile('web/public/models/catalogue.json','utf8'));
  expect(proof.exteriors.map(b=>b.code)).toEqual(catalogue.buildings.filter(b=>b.detailedExterior).map(b=>b.code));
  for(const b of proof.exteriors){expect(b.bound,b.code).toBe(b.glass);expect(b.opaquePaneShadowErrors,b.code).toEqual([]);}
  for(const b of proof.interiors){expect(b.ready).toBe('interior-'+b.code);for(const path of ['base','detailed']){expect(b[path].bound,b.code+' '+path).toBe(b[path].glass);expect(b[path].opaquePaneShadowErrors,b.code+' '+path).toEqual([]);}}
  await writeFile('result/blender/stage139/production-glass-verification.json',JSON.stringify(proof,null,2)+'\n');
 }finally{await server.close();}
});

test('OLD stair contradiction and CBG missing registration remain explicit without guessed geometry',async()=>{
 const read=async folder=>JSON.parse(await readFile('result/blender/'+folder+'/audit.json','utf8'));
 const old=await read('old_houghton_next'),cbg=await read('cbg_envelope_next');
 for(const audit of [old,cbg]){expect(audit.ownedObjects).toEqual([]);expect(audit.archivedObjects).toEqual([]);expect(audit.changes).toEqual([]);}
 expect(old.registration.nativeStairCount).toBe(6);expect(old.registration.nativeStairCountVerified).toBe(false);
 expect(cbg.readOnly).toBe(true);expect(cbg.floorBoundaryFinding).toBeTruthy();
});
