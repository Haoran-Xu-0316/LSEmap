import { test, expect } from '@playwright/test';
import { createServer } from 'vite';
import { mkdir, writeFile } from 'node:fs/promises';

test('thin court wires preserve holes and converge to stable distant coverage', async ({ page }) => {
  const errors=[];page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});page.on('pageerror',e=>errors.push(e.message));
  const server=await createServer({logLevel:'error',server:{host:'127.0.0.1',port:0}});
  try {
    await server.listen();
    await page.route('**/__wire-grid',route=>route.fulfill({contentType:'text/html',body:'<!doctype html><div id="stage"></div>'}));
    await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__wire-grid`);
    const proof=await page.evaluate(async()=>{
      const {THREE}=await import('/tests/interaction239-fixture.js');
      const {prepareWireGrid}=await import('/src/wire-grid-materials.js');
      const {prepareMeshShadows}=await import('/src/surface-materials.js');
      const renderer=new THREE.WebGLRenderer({alpha:true});renderer.setSize(256,256);renderer.setClearColor(0xffffff,0);
      document.querySelector('#stage').append(renderer.domElement);
      const scene=new THREE.Scene(),camera=new THREE.OrthographicCamera(-1,1,1,-1,.1,10);camera.position.z=2;
      scene.add(new THREE.HemisphereLight(0xffffff,0xffffff,2));
      const material=new THREE.MeshStandardMaterial({color:0x15251b});material.userData.wireMesh={pitchX:.075,pitchY:.15,width:.0025};
      prepareWireGrid(material);const hook=material.onBeforeCompile;prepareWireGrid(material);
      const geometry=new THREE.PlaneGeometry(2,2),original=geometry.attributes.uv.array.slice(),mesh=new THREE.Mesh(geometry,material);prepareMeshShadows(mesh);scene.add(mesh);
      const gl=renderer.getContext(),rows=[];
      for(const extent of [3,30,150])for(const offset of [0,.017,.037,.061]){
        const uv=geometry.attributes.uv;
        for(let i=0;i<uv.count;i++)uv.setXY(i,original[i*2]*extent+offset,original[i*2+1]*extent+offset);
        uv.needsUpdate=true;renderer.render(scene,camera);gl.finish();
        const bytes=new Uint8Array(256*256*4);gl.readPixels(0,0,256,256,gl.RGBA,gl.UNSIGNED_BYTE,bytes);
        let alpha=0,min=255,max=0;
        for(let i=3;i<bytes.length;i+=4){alpha+=bytes[i];min=Math.min(min,bytes[i]);max=Math.max(max,bytes[i]);}
        rows.push({extent,offset,meanAlpha:alpha/(256*256*255),minAlpha:min/255,maxAlpha:max/255});
      }
      const result={rows,expectedCoverage:1-(1-.0025/.075)*(1-.0025/.15),idempotent:material.onBeforeCompile===hook,
        transparent:material.transparent,depthWrite:material.depthWrite,singlePass:material.forceSinglePass,
        castsSolidShadow:mesh.castShadow};
      geometry.dispose();material.dispose();renderer.dispose();return result;
    });
    expect(errors).toEqual([]);expect(proof.idempotent).toBe(true);expect(proof.transparent).toBe(true);
    expect(proof.depthWrite).toBe(false);expect(proof.singlePass).toBe(true);expect(proof.castsSolidShadow).toBe(false);
    for(const row of proof.rows)expect(Math.abs(row.meanAlpha-proof.expectedCoverage)).toBeLessThan(.008);
    const near=proof.rows.filter(r=>r.extent===3),far=proof.rows.filter(r=>r.extent===150);
    expect(near.every(r=>r.minAlpha===0)).toBe(true);expect(far.every(r=>r.maxAlpha<.08)).toBe(true);
    expect(Math.max(...far.map(r=>r.meanAlpha))-Math.min(...far.map(r=>r.meanAlpha))).toBeLessThan(.003);
    await mkdir('result/web/wire-grid248',{recursive:true});await writeFile('result/web/wire-grid248/filter-proof.json',JSON.stringify(proof,null,2)+'\n');
  } finally {await server.close();}
});
