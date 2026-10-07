import {test,expect} from '@playwright/test';
import {createServer} from 'vite';
import {writeFile} from 'node:fs/promises';

test('closed glazing has one optical layer; flat panes retain reverse visibility without additional draws',async({page})=>{
 const html=`<script type="module">
 import * as THREE from '/@fs/${process.cwd()}/node_modules/three/build/three.module.js';
 import {prepareGlazingSides} from '/src/surface-materials.js';
 const renderer=new THREE.WebGLRenderer();renderer.setSize(256,128);renderer.outputColorSpace=THREE.LinearSRGBColorSpace;
 const scene=new THREE.Scene();scene.background=new THREE.Color(1,1,1);
 const camera=new THREE.OrthographicCamera(-2,2,1,-1,.1,10);camera.position.z=4;
 const material=()=>{const m=new THREE.MeshBasicMaterial({color:new THREE.Color(.1,.3,.6),transparent:true,opacity:.4,depthWrite:false,side:THREE.DoubleSide});m.name='fixture_glass';m.forceSinglePass=true;return m;};
 const shell=new THREE.Mesh(new THREE.BoxGeometry(1,1,.05),material());shell.position.x=1;shell.material.userData.webClosedGlazing=true;
 const sheet=new THREE.Mesh(new THREE.PlaneGeometry(1,1),material());sheet.position.x=-1;scene.add(shell,sheet);
 const target=new THREE.WebGLRenderTarget(256,128);target.texture.colorSpace=THREE.LinearSRGBColorSpace;renderer.setRenderTarget(target);
 const sample=()=>{renderer.render(scene,camera);const pixel=x=>{const p=new THREE.Vector3(x,0,0).project(camera),bytes=new Uint8Array(4);renderer.readRenderTargetPixels(target,Math.round((p.x+1)*128),Math.round((p.y+1)*64),1,1,bytes);return Array.from(bytes);};return {shell:pixel(1),sheet:pixel(-1),calls:renderer.info.render.calls};};
 const before=sample();prepareGlazingSides(shell.material);prepareGlazingSides(sheet.material);const after=sample();
 sheet.rotation.y=Math.PI;const reverse=sample();window.proof={before,after,reverse,shellOpacity:shell.material.opacity,sheetOpacity:sheet.material.opacity,shellSide:shell.material.side,sheetSide:sheet.material.side};renderer.dispose();
 </script>`;
 const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{name:'glass-surface-proof',configureServer(s){s.middlewares.use('/__glass-surface-proof',(_,res)=>{res.setHeader('Content-Type','text/html');res.end(html);});}}]});
 try{
  await server.listen();await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__glass-surface-proof`);
  await page.waitForFunction(()=>window.proof);const proof=await page.evaluate(()=>window.proof);
  expect(proof.after.shell[0]).toBeGreaterThan(proof.before.shell[0]+30);
  for(let i=0;i<3;i++)expect(Math.abs(proof.after.shell[i]-proof.after.sheet[i])).toBeLessThanOrEqual(1);
  expect(proof.reverse.sheet).toEqual(proof.after.sheet);
  expect(proof.after.calls).toBeLessThanOrEqual(proof.before.calls);
  expect(proof.shellOpacity).toBe(.4);expect(proof.sheetOpacity).toBe(.4);
  expect(proof.shellSide).toBe(0);expect(proof.sheetSide).toBe(2);
  await writeFile('result/blender/stage181/glazing-render-proof.json',JSON.stringify(proof,null,2)+'\n');
 }finally{await server.close();}
});
