import {test,expect} from '@playwright/test';
import {createServer} from 'vite';
import {mkdir,readFile,writeFile} from 'node:fs/promises';

const outputRoot='result/blender/lincoln51_oblique151';
test('isolate 51L entrance chips under actual production camera and decoded GLB',async({page})=>{
 test.setTimeout(120000);
 const current=JSON.parse(await readFile('web/public/models/catalogue.json','utf8'));
 const output=outputRoot+(current.version==='150'?'/web-diagnostic':'/web-acceptance');
 await mkdir(output,{recursive:true});
 const job=JSON.parse(await readFile('web/tools/gallery-views.json','utf8')).find(j=>j.name==='51l-entrance');
 const script=`
 import * as THREE from '/@fs/${process.cwd()}/node_modules/three/build/three.module.js';
 import {CampusViewer} from '/src/viewer.js';
 const catalogue=await(await fetch('/models/catalogue.json')).json(),building=catalogue.buildings.find(b=>b.code==='51L');
 const viewer=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},catalogue.sourceModelSha256);
 await viewer.load();await viewer.loadExterior(building);viewer.select(building);viewer.showDetail(building);await viewer.upgradeModel(building,'exterior');
 cancelAnimationFrame(viewer.frame);viewer.transition=null;viewer.controls.enableDamping=false;
 const job=${JSON.stringify(job)};
 viewer.camera.fov=job.view.fov;viewer.updateCameraProjection();viewer.moveCamera(new THREE.Vector3(...job.view.position),new THREE.Vector3(...job.view.target),false);viewer.controls.update();viewer.camera.updateMatrixWorld();
 const meshes=[];viewer.scene.traverseVisible(o=>{if(o.isMesh)meshes.push(o);});
 const originals=meshes.map(o=>({o,material:o.material,visible:o.visible}));
 const materials=[...new Set(meshes.flatMap(o=>Array.isArray(o.material)?o.material:[o.material]))];
 const states=new Map(materials.map(m=>[m,{opacity:m.opacity,transparent:m.transparent,side:m.side}]));
 function reset(){for(const s of originals){s.o.material=s.material;s.o.visible=s.visible;}for(const [m,s]of states){Object.assign(m,s);m.needsUpdate=true;}viewer.renderer.shadowMap.enabled=true;viewer.renderer.shadowMap.needsUpdate=true;}
 window.capture=variant=>{
  reset();const temporaries=[];
  if(variant==='no-shadows'){viewer.renderer.shadowMap.enabled=false;for(const m of materials)m.needsUpdate=true;}
  if(variant==='opaque-glass')for(const m of materials)if(/glass|glazing/i.test(m.name)){m.transparent=false;m.opacity=1;m.needsUpdate=true;}
  if(variant==='no-glass')for(const o of meshes)if((Array.isArray(o.material)?o.material:[o.material]).every(m=>/glass|glazing/i.test(m.name)))o.visible=false;
  if(variant==='unlit')for(const o of meshes){const replace=m=>{const material=new THREE.MeshBasicMaterial({color:m.color,transparent:m.transparent,opacity:m.opacity,side:m.side});temporaries.push(material);return material;};o.material=Array.isArray(o.material)?o.material.map(replace):replace(o.material);}
  viewer.renderPipeline.render();const image=viewer.canvas.toDataURL('image/png').split(',')[1];reset();for(const m of temporaries)m.dispose();
  return {variant,image,camera:viewer.camera.position.toArray(),target:viewer.controls.target.toArray(),glazingMaterials:materials.filter(m=>/glass|glazing/i.test(m.name)).map(m=>({name:m.name,opacity:m.opacity,transparent:m.transparent,side:m.side})),objects:meshes.map(o=>o.name)};
 };
 window.viewer=viewer;window.ready=true;
 `;
 const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{name:'lincoln-oblique',configureServer(s){s.middlewares.use('/__lincoln-oblique',(_,r)=>{r.setHeader('Content-Type','text/html');r.end(`<!doctype html><style>body{margin:0}#stage{width:1400px;height:1120px}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">${script}</script>`);});}}]});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  await server.listen();await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__lincoln-oblique`);await page.waitForFunction(()=>window.ready,null,{timeout:90000});
  const records=[];
  for(const variant of ['production','no-shadows','opaque-glass','no-glass','unlit']){
   const capture=await page.evaluate(v=>window.capture(v),variant);await writeFile(`${output}/${variant}.png`,Buffer.from(capture.image,'base64'));delete capture.image;records.push(capture);
  }
  expect(errors).toEqual([]);for(let axis=0;axis<3;axis++)expect(records[0].camera[axis]).toBeCloseTo(job.view.position[axis],10);
  await writeFile(`${output}/diagnostic.json`,JSON.stringify({sourceVersion:current.version,sourceModelSha256:current.sourceModelSha256,job,records,errors},null,2)+'\n');await page.evaluate(()=>viewer.dispose());
 }finally{await server.close();}
});
