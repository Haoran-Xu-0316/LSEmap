import { test, expect } from '@playwright/test';
import { createServer } from 'vite';
import { mkdir, writeFile } from 'node:fs/promises';

const output = 'result/web/overview-sampling-quality';
async function openScene(page, script) {
  await mkdir(output, { recursive: true });
  const server = await createServer({
    server: { host: '127.0.0.1', port: 0 }, logLevel: 'error',
    plugins: [{ name: 'sampling-quality', configureServer(server) {
      server.middlewares.use('/__sampling-quality', (_, response) => {
        response.setHeader('Content-Type', 'text/html');
        response.end(`<!doctype html><style>body{margin:0}#stage{width:960px;height:768px}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">${script}</script>`);
      });
    } }],
  });
  await server.listen();
  await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__sampling-quality`);
  return server;
}
const measurement = `
 const capture=document.createElement('canvas');capture.width=960;capture.height=768;
 const context=capture.getContext('2d',{willReadFrequently:true});
 const snapshot=()=>{context.drawImage(renderer.domElement,0,0,960,768);return context.getImageData(0,0,960,768).data;};
 const rms=frames=>{let squares=0;for(let f=1;f<frames.length;f++)for(let i=0;i<frames[f].length;i+=4)for(let c=0;c<3;c++){const d=frames[f][i+c]-frames[f-1][i+c];squares+=d*d;}return Math.sqrt(squares/(frames[0].length*.75*(frames.length-1)));};
`;

test('compare four sample facade coverage against the current two sample baseline', async ({ page }) => {
  const server=await openScene(page, `
    import * as THREE from '/@fs/${process.cwd()}/node_modules/three/build/three.module.js';
    import {createRenderPipeline} from '/src/rendering-quality.js';
    const renderer=new THREE.WebGLRenderer({antialias:false});renderer.setPixelRatio(1.5);renderer.setSize(960,768);
    renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.setClearColor(0xe9e8e3);document.querySelector('#stage').append(renderer.domElement);
    const scene=new THREE.Scene(),camera=new THREE.OrthographicCamera(-12,12,9.6,-9.6,.1,20);camera.position.z=10;
    const geometry=new THREE.BoxGeometry(.022,12,.08),material=new THREE.MeshBasicMaterial({color:0x243541});
    const grid=new THREE.InstancedMesh(geometry,material,85),matrix=new THREE.Matrix4(),rotation=new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,0,1),.18);
    for(let i=0;i<85;i++){matrix.compose(new THREE.Vector3(-10.5+i*.25,0,0),rotation,new THREE.Vector3(1,1,1));grid.setMatrixAt(i,matrix);}scene.add(grid);
    const pipeline=createRenderPipeline(renderer,scene,camera);pipeline.resize(960,768);
    ${measurement}
    const records=[],allFrames=[];
    for(const level of [1,2,3,5]){
      pipeline.scenePass.sampleLevel=level;const frames=[];
      for(const x of [0,.004,.008,.012,.016,.020]){camera.position.x=x;camera.updateMatrixWorld();pipeline.render();frames.push(snapshot());}
      allFrames.push(frames);records.push({samples:2**level,rms:rms(frames),background:Array.from(frames[0].slice(0,3))});
    }
    for(let l=0;l<3;l++){let energy=0,count=0;for(let f=1;f<allFrames[l].length;f++)for(let i=0;i<allFrames[l][f].length;i+=4)for(let c=0;c<3;c++){const d=(allFrames[l][f][i+c]-allFrames[l][f-1][i+c])-(allFrames[3][f][i+c]-allFrames[3][f-1][i+c]);energy+=d*d;count++;}records[l].motionError=Math.sqrt(energy/count);}
    window.proof={records};pipeline.dispose();geometry.dispose();material.dispose();renderer.dispose();
  `);
  try {
    await page.waitForFunction(()=>window.proof);
    const proof=await page.evaluate(()=>window.proof);
    await writeFile(`${output}/frames.json`,JSON.stringify(proof,null,2));
    expect(proof.records[1].motionError).toBeLessThan(proof.records[0].motionError);
    expect(proof.records[1].background).toEqual(proof.records[0].background);
  } finally {await server.close();}
});

test('measure actual overview motion with and without shadows at equal camera and resolution', async ({ page }) => {
  test.setTimeout(150000);
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  const server=await openScene(page, `
    import * as THREE from '/@fs/${process.cwd()}/node_modules/three/build/three.module.js';
    import {CampusViewer} from '/src/viewer.js';
    const catalogue=await(await fetch('/models/catalogue.json')).json();
    const viewer=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},catalogue.sourceModelSha256);
    await viewer.load();await Promise.all(catalogue.buildings.filter(b=>b.detailedExterior).map(b=>viewer.loadExterior(b)));
    cancelAnimationFrame(viewer.frame);viewer.transition=null;viewer.controls.enableDamping=false;viewer.home(false);viewer.camera.position.lerp(viewer.controls.target,.35);viewer.controls.update();
    const {renderer,camera,renderPipeline:pipeline}=viewer;
    ${measurement}
    window.defaults={samples:2**pipeline.scenePass.sampleLevel,ratio:renderer.getPixelRatio()};
    const position=camera.position.clone(),target=viewer.controls.target.clone(),right=new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld,0);
    window.measure=async(shadows,level)=>{
      renderer.shadowMap.enabled=shadows;renderer.shadowMap.needsUpdate=true;
      viewer.scene.traverse(o=>{if(o.isMesh)for(const m of Array.isArray(o.material)?o.material:[o.material])m.needsUpdate=true;});
      pipeline.scenePass.sampleLevel=level;
      const frames=[];const times=[];
      for(const offset of [0,.02,.04,.06,.08,.10]){
        camera.position.copy(position).addScaledVector(right,offset);viewer.controls.target.copy(target).addScaledVector(right,offset);viewer.controls.update();camera.updateMatrixWorld();
        const start=performance.now();pipeline.render();renderer.getContext().finish();times.push(performance.now()-start);frames.push(snapshot());
      }
      camera.position.copy(position);viewer.controls.target.copy(target);viewer.controls.update();camera.updateMatrixWorld();pipeline.render();
      return {shadows,samples:2**level,rms:rms(frames),medianMs:times.slice(1).sort((a,b)=>a-b)[2],camera:camera.position.toArray(),ratio:renderer.getPixelRatio(),image:renderer.domElement.toDataURL('image/png').split(',')[1]};
    };
    window.viewer=viewer;window.ready=true;
  `);
  try {
    await page.waitForFunction(()=>window.ready,null,{timeout:100000});
    const defaults=await page.evaluate(()=>window.defaults);expect(defaults.samples).toBe(4);
    const records=[];
    for(const shadows of [true,false])for(const level of [1,2]){
      const record=await page.evaluate(([shadows,level])=>window.measure(shadows,level),[shadows,level]);
      await writeFile(`${output}/overview-${shadows?'shadows':'unlit'}-${record.samples}.png`,Buffer.from(record.image,'base64'));
      delete record.image;records.push(record);
    }
    await writeFile(`${output}/campus.json`,JSON.stringify({defaults,records,errors},null,2));
    expect(errors).toEqual([]);
    expect(records[1].rms).toBeLessThan(records[0].rms);
    expect(records[1].camera).toEqual(records[0].camera);
    await page.evaluate(()=>viewer.dispose());
  } finally {await server.close();}
});
