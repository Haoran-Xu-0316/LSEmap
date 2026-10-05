import {test,expect} from '@playwright/test';
import {createServer} from 'vite';

test('landscape finishes compile with filtered detail and retain source maps',async({page})=>{
 const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error'});
 try{
  await server.listen();await page.goto('http://127.0.0.1:'+server.httpServer.address().port);
  const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  const result=await page.evaluate(async()=>{
   const THREE=await import('/@id/three');
   const {applySurfaceDetail,refineMaterialFinish}=await import('/src/surface-materials.js');
   const renderer=new THREE.WebGLRenderer();renderer.setSize(128,128);
   const scene=new THREE.Scene();scene.add(new THREE.HemisphereLight(0xffffff,0x555555,2));
   const camera=new THREE.PerspectiveCamera(50,1,.1,100);camera.position.z=5;
   const geometry=new THREE.SphereGeometry(1,16,12),map=new THREE.Texture();
   const records=[];
   for(const name of ['WEB_Road asphalt','WEB_SITE_V47_slab_0','WEB_MAR25_bark','WEB_SITE_NEXT_SITE_NEXT_PORTSMOUTH_soil','WEB_London plane foliage','WEB_Context muted stone']){
    const material=new THREE.MeshStandardMaterial({color:0x778866,map});material.name=name;
    const palette=material.color.toArray();refineMaterialFinish(material);applySurfaceDetail(material);
    const hook=material.onBeforeCompile;applySurfaceDetail(material);
    const shader={uniforms:{},vertexShader:'#include <project_vertex>',fragmentShader:'#include <color_fragment>\n#include <roughnessmap_fragment>\n#include <normal_fragment_maps>'};material.onBeforeCompile(shader);
    const mesh=new THREE.Mesh(geometry,material);scene.add(mesh);renderer.render(scene,camera);scene.remove(mesh);
    records.push({name,unchangedMap:material.map===map,palette:JSON.stringify(palette)===JSON.stringify(material.color.toArray()),idempotent:hook===material.onBeforeCompile,filtered:shader.fragmentShader.includes('coarseVisibility'),bump:shader.uniforms.surfaceBump.value});material.dispose();
   }
   const calls=renderer.info.render.calls;geometry.dispose();map.dispose();renderer.dispose();
   return{records,calls};
  });
  expect(errors).toEqual([]);expect(result.calls).toBe(1);
  for(const record of result.records){expect(record.unchangedMap).toBe(true);expect(record.palette).toBe(true);expect(record.idempotent).toBe(true);expect(record.filtered).toBe(true);}
  expect(result.records.find(r=>r.name.includes('foliage')).bump).toBe(0);
  expect(result.records.find(r=>r.name.includes('bark')).bump).toBeGreaterThan(result.records.find(r=>r.name.includes('slab')).bump);
 }finally{await server.close();}
});
