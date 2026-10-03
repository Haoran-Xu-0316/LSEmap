import {test,expect} from '@playwright/test';
import {createServer} from 'vite';
import * as THREE from 'three';
import {refineMaterialFinish} from '../src/surface-materials.js';

test('transparent glazing retains recorded alpha and avoids a second face pass',()=>{
 const pane=new THREE.MeshStandardMaterial({color:0x728a8b,opacity:.3,transparent:true,side:THREE.DoubleSide});
 pane.name='Facade_glass';refineMaterialFinish(pane);
 expect(pane.opacity).toBe(.3);expect(pane.depthWrite).toBe(false);expect(pane.forceSinglePass).toBe(true);
 const hook=pane.onBeforeCompile,key=pane.customProgramCacheKey();refineMaterialFinish(pane);
 expect(pane.onBeforeCompile).toBe(hook);expect(pane.customProgramCacheKey()).toBe(key);
 const opaque=new THREE.MeshStandardMaterial({opacity:1});opaque.name='opaque_glazing';
 const originalHook=opaque.onBeforeCompile;refineMaterialFinish(opaque);
 expect(opaque.transparent).toBe(false);expect(opaque.onBeforeCompile).toBe(originalHook);
});

test('production glass shader stays clear face-on and reflects more at grazing angles',async({page})=>{
 const html=`<script type="module">
 import * as THREE from '/@fs/${process.cwd()}/node_modules/three/build/three.module.js';
 import {refineMaterialFinish} from '/src/surface-materials.js';
 const renderer=new THREE.WebGLRenderer({alpha:true});renderer.setSize(128,128);renderer.setClearColor(0,0);
 const scene=new THREE.Scene();scene.add(new THREE.AmbientLight(0xffffff,1));
 const camera=new THREE.PerspectiveCamera(35,1,.1,10);camera.position.z=3;
 const material=new THREE.MeshStandardMaterial({color:0x728a8b,opacity:.3,transparent:true,side:THREE.DoubleSide});material.name='probe_glass';
 const pane=new THREE.Mesh(new THREE.PlaneGeometry(2,2),material);scene.add(pane);
 const target=new THREE.WebGLRenderTarget(128,128);renderer.setRenderTarget(target);
 const sample=angle=>{pane.rotation.y=angle;renderer.render(scene,camera);const pixel=new Uint8Array(4);renderer.readRenderTargetPixels(target,64,64,1,1,pixel);return {alpha:pixel[3]/255,calls:renderer.info.render.calls};};
 const before=sample(0);refineMaterialFinish(material);const facing=sample(0),grazing=sample(THREE.MathUtils.degToRad(80));
 window.proof={before,facing,grazing,programsReady:renderer.info.programs.every(p=>p.diagnostics?.runnable!==false)};
 pane.geometry.dispose();material.dispose();target.dispose();renderer.dispose();
 </script>`;
 const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{name:'private-glass-check',configureServer(s){s.middlewares.use('/__glass-check',(_,res)=>{res.setHeader('Content-Type','text/html');res.end(html);});}}]});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 try{
  await server.listen();await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__glass-check`);
  await page.waitForFunction(()=>window.proof,null,{timeout:20000});const proof=await page.evaluate(()=>window.proof);
  expect(errors).toEqual([]);expect(proof.programsReady).toBe(true);
  expect(proof.facing.alpha).toBeCloseTo(.3,1);expect(proof.grazing.alpha).toBeGreaterThan(proof.facing.alpha+.2);
  expect(proof.before.calls).toBe(2);expect(proof.facing.calls).toBe(1);
 }finally{await server.close();}
});
