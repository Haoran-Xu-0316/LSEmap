import { test, expect } from '@playwright/test';
import { createServer } from 'vite';
import { mkdir, writeFile } from 'node:fs/promises';

// Compare actual dense campus facades with a 32-sample reference, at identical
// cameras. Frame differences alone cannot distinguish smoothing from lost detail.
test('overview history reduces pan orbit and zoom aliasing without trails or persistent blur', async ({ page }) => {
  test.setTimeout(180000);
  const output = 'result/web/overview-shimmer155';
  await mkdir(output, {recursive:true});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});
  const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{
    name:'shimmer-measurement',configureServer(server){server.middlewares.use('/__shimmer155',(_,res)=>{
      res.setHeader('Content-Type','text/html');res.end(`<!doctype html><style>body{margin:0}#stage{width:960px;height:768px}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">
      import * as THREE from '/@fs/${process.cwd()}/node_modules/three/build/three.module.js';
      import {CampusViewer} from '/src/viewer.js';

      const catalogue=await(await fetch('/models/catalogue.json')).json();
      const viewer=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},catalogue.sourceModelSha256);
      await viewer.load();await Promise.all(catalogue.buildings.filter(b=>b.detailedExterior).map(b=>viewer.loadExterior(b)));
      cancelAnimationFrame(viewer.frame);viewer.transition=null;viewer.controls.enableDamping=false;viewer.home(false);
      viewer.camera.position.lerp(viewer.controls.target,.58);viewer.controls.update();viewer.camera.updateMatrixWorld();
      const {renderer,camera,renderPipeline:pipeline}=viewer;
      const capture=document.createElement('canvas');capture.width=960;capture.height=768;
      const context=capture.getContext('2d',{willReadFrequently:true});
      const position=camera.position.clone(),target=viewer.controls.target.clone();
      const right=new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld,0);
      const frames=new Map(); 
      window.benchmark=()=>{
        // Interleave both renderers. A costly reference render between two
        // timings changes GPU temperature, cache state and memory pressure.
        pipeline.scenePass.sampleLevel=2;const timings={baseline:[],temporal:[]};
        for(let pair=0;pair<12;pair++)for(const stabilize of (pair%2?[true,false]:[false,true])){
          pipeline.resetHistory();
          for(let frame=0;frame<3;frame++){
            const offset=(pair*3+frame)*.04;camera.position.copy(position).addScaledVector(right,offset);viewer.controls.target.copy(target).addScaledVector(right,offset);viewer.controls.update();camera.updateMatrixWorld();
            const start=performance.now();pipeline.render({stabilize,moving:true});renderer.getContext().finish();
            if(frame===2)timings[stabilize?'temporal':'baseline'].push(performance.now()-start);
          }
        }
        const median=values=>values.slice().sort((a,b)=>a-b)[Math.floor(values.length/2)];
        return {baselineMs:median(timings.baseline),temporalMs:median(timings.temporal),pairedFrames:timings};
      };
      window.measure=async(level)=>{
        const temporal=level===6; pipeline.resetHistory();
        renderer.setPixelRatio(1.5);renderer.setSize(960,768);pipeline.resize(960,768);
        
        pipeline.scenePass.sampleLevel=temporal?2:level;const pixels=[],times=[];
        for(let f=0;f<36;f++){ const offset=f<8?0:Math.min(f-7,12)*.04;
          camera.position.copy(position).addScaledVector(right,offset);viewer.controls.target.copy(target).addScaledVector(right,offset);
          if(f>=20){const delta=camera.position.clone().sub(viewer.controls.target);delta.applyAxisAngle(new THREE.Vector3(0,1,0),Math.min(f-19,8)*.0015);if(f>=28)delta.multiplyScalar(1-(f-27)*.001);camera.position.copy(viewer.controls.target).add(delta);}
          viewer.controls.update();camera.updateMatrixWorld();
          const started=performance.now();pipeline.render({stabilize:temporal,time:f*1000/60});renderer.getContext().finish();times.push(performance.now()-started);
          context.drawImage(renderer.domElement,0,0,960,768);if(f>=7)pixels.push(context.getImageData(0,0,960,768).data);
        }
        frames.set(level,pixels);
        return {samples:temporal?'reprojected4':2**level,medianMs:times.slice(2).sort((a,b)=>a-b)[8],background:Array.from(pixels[0].slice(0,3)),image:capture.toDataURL('image/png').split(',')[1]};
      };
      window.compare=()=>{
        const reference=frames.get(5),records=[];
        for(const level of [2,6]){
          const candidate=frames.get(level);let staticSquares=0,motionSquares=0,staticCount=0,motionCount=0;
          // Central buildings; camera times are fixed to a 60Hz input sequence.
          // Readback/GPU contention must not change history expiry in image comparisons.
          for(let f=0;f<candidate.length;f++)for(let y=160;y<650;y++)for(let x=170;x<800;x++)for(let c=0;c<3;c++){
            const i=(y*960+x)*4+c;const d=candidate[f][i]-reference[f][i];staticSquares+=d*d;staticCount++;
            if(f){const e=(candidate[f][i]-candidate[f-1][i])-(reference[f][i]-reference[f-1][i]);motionSquares+=e*e;motionCount++;}
          }
          records.push({samples:level===6?'reprojected4':2**level,spatialError:Math.sqrt(staticSquares/staticCount),motionError:Math.sqrt(motionSquares/motionCount)});
        }
        return {records,sourceModelSha256:catalogue.sourceModelSha256,camera:camera.position.toArray(),pixelRatio:renderer.getPixelRatio(),defaultSamples:2**window.initialSampleLevel};
      };
      window.behavior=()=>{
        pipeline.scenePass.sampleLevel=2;
        let time=1000;const snapshot=()=>{time+=1000/60;pipeline.render({time});context.drawImage(renderer.domElement,0,0,960,768);return context.getImageData(0,0,960,768).data;};
        const maximumDifference=(a,b)=>{let maximum=0;for(let i=0;i<a.length;i+=4)for(let c=0;c<3;c++)maximum=Math.max(maximum,Math.abs(a[i+c]-b[i+c]));return maximum;};
        pipeline.resetHistory();snapshot();camera.position.addScaledVector(right,.04);viewer.controls.target.addScaledVector(right,.04);viewer.controls.update();snapshot();
        const activeWeight=pipeline.temporalPass.uniforms.historyWeight.value;
        snapshot();const settleFlag=pipeline.needsSettle,clean=snapshot();pipeline.render({stabilize:false,time:time+=1000/60});context.drawImage(renderer.domElement,0,0,960,768);const baseline=context.getImageData(0,0,960,768).data;
        snapshot();camera.position.applyAxisAngle(new THREE.Vector3(0,1,0),.4);viewer.controls.update();const cut=snapshot(),cutWeight=pipeline.temporalPass.uniforms.historyWeight.value;
        pipeline.render({stabilize:false,time:time+=1000/60});context.drawImage(renderer.domElement,0,0,960,768);const cutReference=context.getImageData(0,0,960,768).data;
        snapshot();renderer.shadowMap.needsUpdate=true;snapshot();const sceneChangeWeight=pipeline.temporalPass.uniforms.historyWeight.value;
        const buildingsBefore=catalogue.buildings.map(b=>b.detailedExterior?.sha256);
        renderer.setSize(390,700);pipeline.resize(390,700);pipeline.render();
        return {activeWeight,settleFlag,settledMaximumError:maximumDifference(clean,baseline),cutWeight,cutMaximumError:maximumDifference(cut,cutReference),sceneChangeWeight,phoneHistoryEnabled:pipeline.temporalPass.enabled,phoneSamples:2**pipeline.scenePass.sampleLevel,modelsUnchanged:JSON.stringify(buildingsBefore)===JSON.stringify(catalogue.buildings.map(b=>b.detailedExterior?.sha256))};
      };
      window.verifyIdle=async()=>{
        viewer.container.style.width='960px';viewer.container.style.height='768px';viewer.resize();viewer.controls.enableDamping=false;viewer.controls.update();
        const original=pipeline.render.bind(pipeline);let renders=0;pipeline.render=(...args)=>{renders++;return original(...args);};
        viewer.needsRender=true;viewer.frame=requestAnimationFrame(viewer.tick);
        await new Promise(resolve=>setTimeout(resolve,300));const before=renders;
        await new Promise(resolve=>setTimeout(resolve,400));cancelAnimationFrame(viewer.frame);
        pipeline.render=original;return {before,after:renders};
      };
      window.originalFxaa=pipeline.antialiasPass.material.fragmentShader;window.initialSampleLevel=pipeline.scenePass.sampleLevel;window.viewer=viewer;window.ready=true;
      </script>`);
    });}
  }]});
  await server.listen();
  try{
    await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__shimmer155`);
    await page.waitForFunction(()=>window.ready,null,{timeout:100000});
    const benchmark=await page.evaluate(()=>window.benchmark());
    const measurements=[];
    for(const level of [2,5,6]){
      const record=await page.evaluate(level=>window.measure(level),level);
      await writeFile(`${output}/samples-${record.samples}.png`,Buffer.from(record.image,'base64'));delete record.image;measurements.push(record);
    }
    const proof=await page.evaluate(()=>window.compare());
    await writeFile(`${output}/comparison.json`,JSON.stringify({...proof,measurements,benchmark,errors},null,2)+'\n');
    expect(errors).toEqual([]);
    expect(benchmark.temporalMs).toBeLessThanOrEqual(benchmark.baselineMs*1.35);
    expect(proof.records[1].spatialError).toBeLessThanOrEqual(proof.records[0].spatialError);
    expect(proof.records[1].motionError).toBeLessThan(proof.records[0].motionError*.9);
    expect(Math.max(...measurements[2].background.map((c,i)=>Math.abs(c-measurements[0].background[i])))).toBeLessThanOrEqual(1);
    const behavior=await page.evaluate(()=>window.behavior());
    await writeFile(`${output}/behavior.json`,JSON.stringify(behavior,null,2)+'\n');
    expect(behavior.activeWeight).toBe(.7);expect(behavior.settleFlag).toBe(false);
    expect(behavior.settledMaximumError).toBeLessThanOrEqual(1);
    expect(behavior.cutWeight).toBe(0);expect(behavior.cutMaximumError).toBeLessThanOrEqual(1);
    expect(behavior.sceneChangeWeight).toBe(0);expect(behavior.phoneHistoryEnabled).toBe(false);expect(behavior.phoneSamples).toBe(1);expect(behavior.modelsUnchanged).toBe(true);
    const idle=await page.evaluate(()=>window.verifyIdle());
    expect(idle.after).toBe(idle.before);expect(idle.before).toBeGreaterThan(0);
    await writeFile(`${output}/idle.json`,JSON.stringify(idle,null,2)+'\n');
    await page.evaluate(()=>viewer.dispose());
  }finally{await server.close();}
});
