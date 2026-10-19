import {test,expect} from '@playwright/test';
import {createServer} from 'vite';
import {mkdir,writeFile} from 'node:fs/promises';

test('sky keeps its upper hemisphere upright and uses neutral distance below the horizon',async({page})=>{
  const server=await createServer({logLevel:'error',server:{host:'127.0.0.1',port:0}});
  try{
    await server.listen();await page.route('**/__sky249',route=>route.fulfill({contentType:'text/html',body:'<!doctype html><body style="margin:0">'}));
    await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__sky249`);
    const proof=await page.evaluate(async()=>{
      const {THREE}=await import('/tests/interaction239-fixture.js');const {createSkySurround}=await import('/src/outdoor-environment.js');
      const data=new Uint8Array(8*8*4);
      for(let row=0;row<8;row++)for(let col=0;col<8;col++){const i=(row*8+col)*4;data[i]=row<4?255:0;data[i+2]=row>=4?255:0;data[i+3]=255;}
      const texture=new THREE.DataTexture(data,8,8);texture.needsUpdate=true;
      const scene=new THREE.Scene(),sky=createSkySurround(texture);scene.add(sky);
      const camera=new THREE.PerspectiveCamera(30,1,.1,100),renderer=new THREE.WebGLRenderer();renderer.setSize(128,128);document.body.append(renderer.domElement);
      const pixels=new Uint8Array(4),samples=[];
      for(const elevation of [30,-10,-45]){const angle=elevation*Math.PI/180;camera.lookAt(0,Math.sin(angle),-Math.cos(angle));renderer.render(scene,camera);const gl=renderer.getContext();gl.readPixels(64,64,1,1,gl.RGBA,gl.UNSIGNED_BYTE,pixels);samples.push({elevation,rgb:[...pixels].slice(0,3)});}
      const runnable=renderer.info.programs.every(p=>p.diagnostics?.runnable!==false);renderer.dispose();sky.geometry.dispose();sky.material.dispose();texture.dispose();return{samples,runnable};
    });
    expect(proof.runnable).toBe(true);const upper=proof.samples[0].rgb;expect(upper[2]).toBeGreaterThan(250);expect(upper[0]).toBeLessThan(3);
    for(const {rgb} of proof.samples.slice(1)){expect(Math.max(...rgb)-Math.min(...rgb)).toBeLessThan(30);expect(Math.min(...rgb)).toBeGreaterThan(150);}
    await mkdir('result/web/sky249',{recursive:true});await writeFile('result/web/sky249/proof.json',JSON.stringify(proof,null,2)+'\n');
  }finally{await server.close();}
});
