import {test,expect} from '@playwright/test';
import {createServer} from 'vite';

test('background attachment waits for navigation, cancels cleanly, and keeps authored finishes',async({page})=>{
 const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error'});
 try{
  await server.listen();await page.goto('http://127.0.0.1:'+server.httpServer.address().port);
  const result=await page.evaluate(async()=>{
   const {CampusViewer}=await import('/src/viewer.js');
   const THREE=await import('/@id/three');
   const {applySurfaceDetail}=await import('/src/surface-materials.js');
   const host={loadController:new AbortController(),disposed:false,interacting:true,transition:null,lastNavigationAt:0};
   let resolved=false;
   const pending=CampusViewer.prototype.waitForBackgroundFrame.call(host).then(value=>{resolved=true;return value;});
   await new Promise(r=>setTimeout(r,180));const paused=!resolved;
   host.interacting=false;host.lastNavigationAt=performance.now();
   await new Promise(r=>setTimeout(r,80));const quiet=!resolved;
   const resumed=await pending;
   host.interacting=true;
   const cancelled=CampusViewer.prototype.waitForBackgroundFrame.call(host);host.loadController.abort();
   const aborted=await cancelled;
   const finishes=[];
   for(const name of ['WEB_SITE_V47_slab_0','WEB_London plane foliage','WEB_SITE_V47_wood_0']){
    const m=new THREE.MeshStandardMaterial({color:0x778866});m.name=name;
    const initial=m.color.toArray();applySurfaceDetail(m);const hook=m.onBeforeCompile;
    applySurfaceDetail(m);
    const shader={uniforms:{},vertexShader:'#include <project_vertex>',fragmentShader:'#include <color_fragment>\n#include <roughnessmap_fragment>\n#include <normal_fragment_maps>'};
    m.onBeforeCompile(shader);
    finishes.push({name,palettePreserved:JSON.stringify(initial)===JSON.stringify(m.color.toArray()),idempotent:hook===m.onBeforeCompile,filtered:shader.fragmentShader.includes('noiseVisibility'),timber:shader.fragmentShader.includes('surfacePoint *= vec3(0.12, 2.5, 1.0)')});
   }
   return{paused,quiet,resumed,aborted,finishes};
  });
  expect(result.paused).toBe(true);expect(result.quiet).toBe(true);expect(result.resumed).toBe(true);expect(result.aborted).toBe(false);
  for(const finish of result.finishes){expect(finish.palettePreserved).toBe(true);expect(finish.idempotent).toBe(true);expect(finish.filtered).toBe(true);}
  expect(result.finishes[2].timber).toBe(true);
 }finally{await server.close();}
});
