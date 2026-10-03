import {test,expect} from '@playwright/test';
import {createServer} from 'vite';
import * as THREE from 'three';
import {refineMaterialFinish,prepareDetailedModel} from '../src/surface-materials.js';

test('shared daylight binds to glazing in both preparation paths without changing recorded alpha',()=>{
 const environment=new THREE.Texture(),glass=new THREE.MeshStandardMaterial({color:0x728a8b,opacity:.78,transparent:true});
 glass.name='Facade_glass';refineMaterialFinish(glass);
 const tint=glass.color.clone(),hook=glass.onBeforeCompile;
 refineMaterialFinish(glass,environment);
 expect(glass.envMap).toBe(environment);expect(glass.envMapIntensity).toBe(1.65);
 expect(glass.opacity).toBe(.78);expect(glass.color.toArray()).toEqual(tint.toArray());expect(glass.onBeforeCompile).toBe(hook);
 const group=new THREE.Group(),other=glass.clone();other.envMap=null;
 group.add(new THREE.Mesh(new THREE.PlaneGeometry(),other));prepareDetailedModel(group,environment);
 expect(other.envMap).toBe(environment);expect(other.opacity).toBe(.78);
 const stone=new THREE.MeshStandardMaterial({color:0xeeeeee});stone.name='Portland_stone';refineMaterialFinish(stone,environment);
 expect(stone.envMap).toBeNull();
 const authored=new THREE.Texture(),custom=new THREE.MeshStandardMaterial({envMap:authored});custom.name='custom_glass';refineMaterialFinish(custom,environment);
 expect(custom.envMap).toBe(authored);
});

test('rendered glass uses material daylight intensity without extra passes or textures',async({page})=>{
 const html=`<script type="module">
 import * as THREE from '/@fs/${process.cwd()}/node_modules/three/build/three.module.js';
 import {refineMaterialFinish} from '/src/surface-materials.js';
 const renderer=new THREE.WebGLRenderer();renderer.setSize(128,128);
 renderer.toneMapping=THREE.NoToneMapping;renderer.setClearColor(0);
 const pixels=new Float32Array(256*128*4);for(let i=0;i<pixels.length;i+=4)pixels.set([.6,.7,.8,1],i);
 const sky=new THREE.DataTexture(pixels,256,128,THREE.RGBAFormat,THREE.FloatType);sky.mapping=THREE.EquirectangularReflectionMapping;sky.needsUpdate=true;
 const generator=new THREE.PMREMGenerator(renderer),environment=generator.fromEquirectangular(sky);
 const scene=new THREE.Scene();scene.environment=environment.texture;scene.environmentIntensity=.35;
 const camera=new THREE.PerspectiveCamera(35,1,.1,10);camera.position.z=3;
 const glass=new THREE.MeshStandardMaterial({color:0,roughness:.15,metalness:0});glass.name='probe_glass';refineMaterialFinish(glass);
 const pane=new THREE.Mesh(new THREE.PlaneGeometry(2,2),glass);scene.add(pane);
 const target=new THREE.WebGLRenderTarget(128,128);target.texture.colorSpace=THREE.SRGBColorSpace;renderer.setRenderTarget(target);
 const sample=()=>{renderer.render(scene,camera);const pixel=new Uint8Array(4);renderer.readRenderTargetPixels(target,64,64,1,1,pixel);return {rgb:Array.from(pixel).slice(0,3),alpha:pixel[3],calls:renderer.info.render.calls,textures:renderer.info.memory.textures};};
 const inherited=sample();refineMaterialFinish(glass,environment.texture);const bound=sample();
 scene.environmentIntensity=.05;const dimmedScene=sample();
 window.proof={inherited,bound,dimmedScene,sharedEnvironment:glass.envMap===environment.texture,programsReady:renderer.info.programs.every(p=>p.diagnostics?.runnable!==false)};
 pane.geometry.dispose();glass.dispose();target.dispose();environment.dispose();sky.dispose();generator.dispose();renderer.dispose();
 </script>`;
 const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{name:'daylight-render-check',configureServer(s){s.middlewares.use('/__daylight-check',(_,res)=>{res.setHeader('Content-Type','text/html');res.end(html);});}}]});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 try{
  await server.listen();await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__daylight-check`);
  await page.waitForFunction(()=>window.proof,null,{timeout:20000});const proof=await page.evaluate(()=>window.proof);
  expect(errors).toEqual([]);expect(proof.programsReady).toBe(true);expect(proof.sharedEnvironment).toBe(true);
  expect(proof.bound.rgb.reduce((a,b)=>a+b,0)).toBeGreaterThan(proof.inherited.rgb.reduce((a,b)=>a+b,0)*1.5);
  expect(proof.dimmedScene.rgb).toEqual(proof.bound.rgb);
  expect(proof.bound.alpha).toBe(proof.inherited.alpha);
  expect(proof.bound.calls).toBe(proof.inherited.calls);expect(proof.bound.calls).toBe(1);
  expect(proof.bound.textures).toBe(proof.inherited.textures);
 }finally{await server.close();}
});
