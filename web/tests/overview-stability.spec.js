import {test,expect} from '@playwright/test';
import {createServer} from 'vite';
import {writeFile} from 'node:fs/promises';

async function pageFor(page,script){
 const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{name:'overview-stability',configureServer(s){s.middlewares.use('/__stability',(_,res)=>{res.setHeader('Content-Type','text/html');res.end(`<!doctype html><style>body{margin:0}#stage{width:960px;height:768px}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">${script}</script>`);});}}]});
 await server.listen();await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__stability`);return server;
}

test('subpixel facade edges vary less with filtered output and preserve flat colors',async({page})=>{
 test.setTimeout(30000);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const server=await pageFor(page,`
 import * as THREE from '/@fs/${process.cwd()}/node_modules/three/build/three.module.js';
 import {createRenderPipeline} from '/src/rendering-quality.js';
 const renderer=new THREE.WebGLRenderer({antialias:false});renderer.setPixelRatio(1.5);renderer.setSize(480,320);renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.setClearColor(0xe9e8e3);document.querySelector('#stage').append(renderer.domElement);
 const scene=new THREE.Scene(),camera=new THREE.OrthographicCamera(-6,6,4,-4,.1,20);camera.position.z=10;
 const geometry=new THREE.BoxGeometry(.022,6,.08),material=new THREE.MeshBasicMaterial({color:0x243541});
 const grid=new THREE.InstancedMesh(geometry,material,45),matrix=new THREE.Matrix4(),rotation=new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,0,1),.18);
 for(let i=0;i<45;i++){matrix.compose(new THREE.Vector3(-5.5+i*.25,0,0),rotation,new THREE.Vector3(1,1,1));grid.setMatrixAt(i,matrix);}scene.add(grid);
 const pipeline=createRenderPipeline(renderer,scene,camera);pipeline.resize(480,320);
 const gl=renderer.getContext(),read=()=>{const a=new Uint8Array(720*480*4);gl.readPixels(0,0,720,480,gl.RGBA,gl.UNSIGNED_BYTE,a);return a;};
 const raw=[],filtered=[];
 for(const x of [0,.004,.008,.012]){camera.position.x=x;camera.updateMatrixWorld();renderer.setRenderTarget(null);renderer.render(scene,camera);raw.push(read());pipeline.render();filtered.push(read());}
 // RMS measures visible jump amplitude; absolute displacement also includes normal edge motion.
 const delta=frames=>{let sum=0,squares=0;for(let f=1;f<frames.length;f++)for(let i=0;i<frames[f].length;i+=4)for(let c=0;c<3;c++){const difference=frames[f][i+c]-frames[f-1][i+c];sum+=Math.abs(difference);squares+=difference*difference;}const count=frames[0].length*.75*(frames.length-1);return {meanAbsolute:sum/count,rms:Math.sqrt(squares/count)};};
 const rawDelta=delta(raw),filteredDelta=delta(filtered),backgroundRaw=Array.from(raw[0].slice(0,3)),backgroundFiltered=Array.from(filtered[0].slice(0,3));
 let disposed=0;for(const target of [pipeline.composer.renderTarget1,pipeline.composer.renderTarget2])target.addEventListener('dispose',()=>disposed++);pipeline.dispose();geometry.dispose();material.dispose();renderer.dispose();
 window.proof={rawDelta,filteredDelta,ratio:filteredDelta.rms/rawDelta.rms,backgroundRaw,backgroundFiltered,disposed};
 `);
 try{
  await page.waitForFunction(()=>window.proof,null,{timeout:15000});const proof=await page.evaluate(()=>window.proof);
  expect(errors).toEqual([]);await writeFile('result/web/overview-stability/edge-verification.json',JSON.stringify(proof,null,2)+'\n');expect(proof.rawDelta.rms).toBeGreaterThan(.1);expect(proof.ratio).toBeLessThan(.9);expect(proof.backgroundFiltered).toEqual(proof.backgroundRaw);expect(proof.disposed).toBe(2);
  await writeFile('result/web/overview-stability/edge-verification.json',JSON.stringify(proof,null,2)+'\n');
 }finally{await server.close();}
});

test('campus gestures keep a stable raster grid and resize updates the filter',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const server=await pageFor(page,`
 import {CampusViewer} from '/src/viewer.js';
 const catalogue=await(await fetch('/models/catalogue.json')).json();
 const viewer=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},catalogue.sourceModelSha256);await viewer.load();window.viewer=viewer;window.ready=true;
 `);
 try{
  await page.waitForFunction(()=>window.ready,null,{timeout:60000});
  const before=await page.evaluate(()=>({width:viewer.canvas.width,height:viewer.canvas.height,ratio:viewer.renderer.getPixelRatio()}));
  const canvas=page.locator('canvas'),bounds=await canvas.boundingBox();await page.mouse.move(bounds.x+bounds.width*.55,bounds.y+bounds.height*.55);await page.mouse.down();await page.mouse.move(bounds.x+bounds.width*.55+50,bounds.y+bounds.height*.55+15,{steps:8});
  const during=await page.evaluate(()=>({width:viewer.canvas.width,height:viewer.canvas.height,ratio:viewer.renderer.getPixelRatio()}));await page.mouse.up();await page.waitForTimeout(400);
  const after=await page.evaluate(()=>({width:viewer.canvas.width,height:viewer.canvas.height,ratio:viewer.renderer.getPixelRatio()}));expect(during).toEqual(before);expect(after).toEqual(before);
  const resized=await page.evaluate(()=>{viewer.container.style.width='390px';viewer.container.style.height='700px';viewer.resize();return {width:viewer.canvas.width,height:viewer.canvas.height,resolution:viewer.renderPipeline.antialiasPass.uniforms.resolution.value.toArray()};});
  expect(resized.resolution[0]).toBeCloseTo(1/resized.width,8);expect(resized.resolution[1]).toBeCloseTo(1/resized.height,8);
  await page.evaluate(()=>{viewer.container.style.width='960px';viewer.container.style.height='768px';viewer.resize();viewer.home();});await page.waitForTimeout(1100);await canvas.screenshot({path:'result/web/overview-stability/overview.png'});
  await page.evaluate(()=>viewer.dispose());expect(errors).toEqual([]);
  await writeFile('result/web/overview-stability/gesture-verification.json',JSON.stringify({before,during,after,resized,errors},null,2)+'\n');
 }finally{await server.close();}
});
