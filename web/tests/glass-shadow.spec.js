import {test,expect} from '@playwright/test';
import {createServer} from 'vite';
import {writeFile} from 'node:fs/promises';
import * as THREE from 'three';
import {prepareDetailedModel} from '../src/surface-materials.js';

test('clear pane shadows do not suppress daylight while solid frames keep their shadows',()=>{
 const glass=new THREE.MeshStandardMaterial({transparent:true,opacity:.78});glass.name='Facade_glass';
 const frame=new THREE.MeshStandardMaterial();frame.name='Window_frame';
 const masked=glass.clone();masked.alphaTest=.5;
 const opaque=glass.clone();opaque.transparent=false;opaque.opacity=1;
 const group=new THREE.Group();
 const pane=new THREE.Mesh(new THREE.PlaneGeometry(),glass),solid=new THREE.Mesh(new THREE.BoxGeometry(),frame),cutout=new THREE.Mesh(new THREE.PlaneGeometry(),masked),reserve=new THREE.Mesh(new THREE.PlaneGeometry(),opaque),mixed=new THREE.Mesh(new THREE.BoxGeometry(),[glass,frame]);
 group.add(pane,solid,cutout,reserve,mixed);prepareDetailedModel(group);
 expect(pane.castShadow).toBe(false);expect(pane.receiveShadow).toBe(true);
 for(const object of [solid,cutout,reserve,mixed])expect(object.castShadow).toBe(true);
 expect(glass.opacity).toBe(.78);expect(group.children).toHaveLength(5);
});

test('rendered daylight passes clear glazing and retains the frame shadow without extra meshes',async({page})=>{
 const html=`<script type="module">
 import * as THREE from '/@fs/${process.cwd()}/node_modules/three/build/three.module.js';
 import {prepareDetailedModel} from '/src/surface-materials.js';
 const renderer=new THREE.WebGLRenderer();renderer.setSize(256,256);renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
 const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(40,1,.1,20);camera.position.set(0,1.3,4);camera.lookAt(0,0,0);
 scene.add(new THREE.AmbientLight(0xffffff,.08));const sun=new THREE.DirectionalLight(0xffffff,3);sun.position.set(0,5,0);sun.castShadow=true;sun.shadow.mapSize.set(512,512);Object.assign(sun.shadow.camera,{left:-2,right:2,top:2,bottom:-2,near:.1,far:10});sun.shadow.bias=-.0001;scene.add(sun);
 const floor=new THREE.Mesh(new THREE.PlaneGeometry(5,5),new THREE.MeshStandardMaterial({color:0xffffff,roughness:1}));floor.rotation.x=-Math.PI/2;floor.receiveShadow=true;scene.add(floor);
 const glass=new THREE.MeshStandardMaterial({color:0x728a8b,transparent:true,opacity:.3,side:THREE.DoubleSide});glass.name='probe_glass';
 const pane=new THREE.Mesh(new THREE.PlaneGeometry(2,2),glass);pane.rotation.x=-Math.PI/2;pane.position.y=2;pane.castShadow=true;
 const frame=new THREE.Mesh(new THREE.BoxGeometry(.22,.15,2),new THREE.MeshStandardMaterial({color:0x333333}));frame.material.name='probe_frame';frame.position.set(.65,2,0);frame.castShadow=true;
 const group=new THREE.Group();group.add(pane,frame);scene.add(group);
 const target=new THREE.WebGLRenderTarget(256,256);target.texture.colorSpace=THREE.SRGBColorSpace;renderer.setRenderTarget(target);
 const sample=()=>{renderer.render(scene,camera);const at=x=>{const p=new THREE.Vector3(x,0,0).project(camera),pixel=new Uint8Array(4);renderer.readRenderTargetPixels(target,Math.round((p.x+1)*128),Math.round((p.y+1)*128),1,1,pixel);return Array.from(pixel).slice(0,3);};return {paneFloor:at(0),frameFloor:at(.65),litFloor:at(-1.4),calls:renderer.info.render.calls,meshes:group.children.length,textures:renderer.info.memory.textures};};
 const before=sample();prepareDetailedModel(group);group.visible=true;const after=sample();
 window.proof={before,after,paneCastsShadow:pane.castShadow,frameCastsShadow:frame.castShadow,programsReady:renderer.info.programs.every(p=>p.diagnostics?.runnable!==false)};
 renderer.dispose();
 </script>`;
 const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{name:'glazing-shadow-check',configureServer(s){s.middlewares.use('/__glazing-shadow-check',(_,res)=>{res.setHeader('Content-Type','text/html');res.end(html);});}}]});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 try{
  await server.listen();await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__glazing-shadow-check`);await page.waitForFunction(()=>window.proof,null,{timeout:20000});
  const proof=await page.evaluate(()=>window.proof),sum=rgb=>rgb.reduce((a,b)=>a+b,0);
  expect(errors).toEqual([]);expect(proof.programsReady).toBe(true);
  expect(sum(proof.after.paneFloor)).toBeGreaterThan(sum(proof.before.paneFloor)*1.5);
  expect(sum(proof.after.paneFloor)).toBeGreaterThan(sum(proof.after.frameFloor)*1.5);
  expect(proof.after.frameFloor).toEqual(proof.before.frameFloor);
  expect(proof.after.litFloor).toEqual(proof.before.litFloor);
  expect(proof.after.meshes).toBe(proof.before.meshes);expect(proof.after.calls).toBeLessThanOrEqual(proof.before.calls);expect(proof.after.textures).toBe(proof.before.textures);
  await writeFile('result/blender/stage139/glass-shadow-verification.json',JSON.stringify(proof,null,2)+'\n');
 }finally{await server.close();}
});
