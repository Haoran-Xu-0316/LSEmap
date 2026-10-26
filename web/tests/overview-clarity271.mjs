/** Compare the actual old/new mobile pipelines at matched poses and display size. */
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {createServer} from 'vite';
import {webkit,chromium,devices} from 'playwright';
const out='result/web/clarity272';await mkdir(out,{recursive:true});
const hash=b=>createHash('sha256').update(b).digest('hex');
const paths=['web/src/device-budget.js','web/src/rendering-quality.js','web/src/viewer.js'];
const sourceHashes=Object.fromEntries(await Promise.all(paths.map(async p=>[p,hash(await readFile(p))])));
const oldRendering=(await readFile('web/tests/fixtures/clarity268/rendering-quality.js','utf8')).replaceAll('from "./','from "/src/').replace('from "/src/device-budget.js"','from "/__clarity271/old-budget.js"');
const oldBudget=await readFile('web/tests/fixtures/clarity268/device-budget.js','utf8');
async function harness(){
 const {width,height,displayDensity,desktop}=window.comparisonConfig;
 const THREE=await import(window.moduleBase+'three/build/three.module.js');
 const {CampusViewer}=await import('/src/viewer.js');
 const current=await import('/src/rendering-quality.js');
 const previous=await import('/__clarity271/old-rendering.js');
 const {ProgressiveStill}=await import('/src/progressive-still.js');
 const {OutputPass}=await import(window.moduleBase+'three/examples/jsm/postprocessing/OutputPass.js');
 const c=await(await fetch('/models/catalogue.json')).json();
 const v=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),c.buildings,()=>{},()=>{window.contextLost=true;},()=>{},c.sourceModelSha256);
 window.viewer=v;v.loadCampusExteriors=async()=>{};await v.load();await v.environmentReady;
 cancelAnimationFrame(v.frame);v.transition=null;v.controls.enableDamping=false;v.toggleLabels(false);
 v.renderPipeline.dispose();v.renderer.shadowMap.needsUpdate=false;
 const {renderer,scene,camera}=v;const context=renderer.getContext();const nativeRender=renderer.render.bind(renderer);let sceneDraws=0;
 renderer.render=(s,c)=>{if(s===scene&&c===camera)sceneDraws++;return nativeRender(s,c);};
 const common=document.createElement('canvas');common.width=width*displayDensity;common.height=height*displayDensity;
 const ctx=common.getContext('2d',{willReadFrequently:true});ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='low';
 const snapshots={};
 function capture(){ctx.clearRect(0,0,common.width,common.height);ctx.drawImage(v.canvas,0,0,common.width,common.height);return {pixels:ctx.getImageData(0,0,common.width,common.height).data,png:common.toDataURL('image/png')};}
 function resize(ratio){renderer.setPixelRatio(ratio);renderer.setSize(width,height);camera.aspect=width/height;camera.updateProjectionMatrix();camera.updateMatrixWorld(true);}
 function makePose(yaw){const delta=camera.position.clone().sub(v.controls.target);delta.applyAxisAngle(new THREE.Vector3(0,1,0),yaw*Math.PI/180);camera.position.copy(v.controls.target).add(delta);camera.lookAt(v.controls.target);camera.updateMatrixWorld(true);scene.updateMatrixWorld(true);}
 function roi(){let box=new THREE.Box3();for(const code of ['OLD','MAR','CBG','LRB','SAW','CKK']){const group=v.groups.get(code);if(group)box.union(new THREE.Box3().setFromObject(group));}if(v.mode!=='campus')box=new THREE.Box3().setFromObject(v.exteriors.get('OLD'));
  const p=[];for(const x of[box.min.x,box.max.x])for(const y of[box.min.y,box.max.y])for(const z of[box.min.z,box.max.z])p.push(new THREE.Vector3(x,y,z).project(camera));
  return {x0:Math.max(2,Math.floor(Math.min(...p.map(p=>(p.x+1)*common.width/2)))),x1:Math.min(common.width-3,Math.ceil(Math.max(...p.map(p=>(p.x+1)*common.width/2)))),y0:Math.max(2,Math.floor(Math.min(...p.map(p=>(1-p.y)*common.height/2)))),y1:Math.min(common.height-3,Math.ceil(Math.max(...p.map(p=>(1-p.y)*common.height/2))))};
 }
 function error(actual,reference,region){let sum=0,edges=0,edgeSum=0,n=0,energy=0,refEnergy=0;const w=common.width;
  for(let y=region.y0;y<=region.y1;y++)for(let x=region.x0;x<=region.x1;x++){const at=(y*w+x)*4;let g=0;for(let k=0;k<3;k++)g+=Math.abs(reference[at+k+4]-reference[at+k-4])+Math.abs(reference[at+k+w*4]-reference[at+k-w*4]);
   for(let k=0;k<3;k++){const d=actual[at+k]-reference[at+k];sum+=d*d;n++;if(g/6>12){edgeSum+=d*d;edges++;}const a=actual[at+k+4]-actual[at+k-4],r=reference[at+k+4]-reference[at+k-4];energy+=a*a;refEnergy+=r*r;}}
  return {rmse:Math.sqrt(sum/n),edgeRmse:Math.sqrt(edgeSum/Math.max(1,edges)),edgeChannels:edges,gradientEnergyRatio:energy/refEnergy};
 }
 async function profile(label,ratio,factory,moving=true){const renderOptions={moving,stabilize:desktop&&moving};resize(ratio);const pipeline=factory(renderer,scene,camera);pipeline.resize(width,height);for(let i=0;i<3;i++)pipeline.render(renderOptions);context.finish();
  const times=[];sceneDraws=0;for(let i=0;i<12;i++){const start=performance.now();pipeline.render(renderOptions);context.finish();times.push(performance.now()-start);}const image=capture();times.sort((a,b)=>a-b);
  const row={label,ratio,size:[v.canvas.width,v.canvas.height],sceneDrawsPerFrame:sceneDraws/12,bufferBytes:pipeline.bufferBytes,rasterSamples:pipeline.scenePass.rasterSamples,frameMedianMs:times[6],frameP95Ms:times[11],lost:context.isContextLost()};pipeline.dispose();return {image,row};
 }
 window.measure=async(name,yaw=0,moving=true)=>{makePose(yaw);const region=roi();const variants=[];for(const[label,ratio,factory]of(desktop?[['before',1.5,previous.createRenderPipeline],['desktop-clear',1.5,current.createRenderPipeline]]:[['before',1.25,previous.createRenderPipeline],['resolution150',1.5,current.createRenderPipeline],['resolution175',1.75,current.createRenderPipeline]]))variants.push(await profile(label,ratio,factory,moving));
  resize(displayDensity);const reference=new ProgressiveStill(scene,camera),output=new OutputPass();reference.setSize(v.canvas.width,v.canvas.height);try{for(let i=0;i<4;i++)reference.accumulate(renderer);output.renderToScreen=true;output.render(renderer,null,reference.accumulation);context.finish();snapshots[name+'-reference']=capture();}finally{reference.dispose();output.dispose();}
  const truth=snapshots[name+'-reference'];for(const v of variants){v.row.error=error(v.image.pixels,truth.pixels,region);snapshots[name+'-'+v.row.label]=v.image;}return {name,region,variants:variants.map(v=>v.row)};
 };
 window.detail=async()=>{const b=c.buildings.find(x=>x.code==='OLD');v.select(b);await v.upgradeModel(b,'exterior');await v.localContext.ready;cancelAnimationFrame(v.frame);v.transition=null;const centre=new THREE.Box3().setFromObject(v.exteriors.get('OLD')).getCenter(new THREE.Vector3());v.controls.target.copy(centre);camera.position.copy(centre).add(new THREE.Vector3(...b.exteriorDirection).normalize().multiplyScalar(98));camera.fov=38;camera.lookAt(centre);camera.updateProjectionMatrix();camera.updateMatrixWorld(true);};
 window.temporalResidual=region=>{const a=snapshots['overview-a-reference'].pixels,b=snapshots['overview-b-reference'].pixels,w=common.width,rows=[];
  for(const label of ['before','resolution175']){const pa=snapshots['overview-a-'+label].pixels,pb=snapshots['overview-b-'+label].pixels;let sum=0,n=0;
   for(let y=region.y0;y<=region.y1;y++)for(let x=region.x0;x<=region.x1;x++){const at=(y*w+x)*4;let gradient=0;for(let k=0;k<3;k++)gradient+=Math.abs(a[at+k+4]-a[at+k-4])+Math.abs(a[at+k+w*4]-a[at+k-w*4]);
    if(gradient/6>12)for(let k=0;k<3;k++){const delta=(pb[at+k]-b[at+k])-(pa[at+k]-a[at+k]);sum+=delta*delta;n++;}}
   rows.push({label,edgeResidualChangeRmse:Math.sqrt(sum/n)});
  }return {method:'Pose-matched reference change removes actual camera displacement before measuring edge residual instability.',rows};
 };
 window.images=()=>Object.fromEntries(Object.entries(snapshots).map(([k,v])=>[k,v.png]));
 window.testInfo={budget:v.budget,sourceModelSha256:c.sourceModelSha256,contextAttributes:context.getContextAttributes(),devicePixelRatio:devicePixelRatio,comparisonDisplaySize:[common.width,common.height]};
 v.home(false);v.transition=null;v.controls.update();window.ready=true;
}
const html=`<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><style>html,body{margin:0}#stage{width:390px;height:664px}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">window.moduleBase=${JSON.stringify('/@fs'+process.cwd()+'/node_modules/')};const desktop=new URLSearchParams(location.search).has('desktop');window.comparisonConfig={desktop,width:desktop?1200:390,height:desktop?800:664,displayDensity:desktop?2:3};document.querySelector('#stage').style.cssText='width:'+window.comparisonConfig.width+'px;height:'+window.comparisonConfig.height+'px';(${harness.toString()})().catch(e=>window.harnessError=String(e.stack||e));</script>`;
const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{name:'clarity-comparison',resolveId(id){if(id==='/__clarity271/old-rendering.js')return '\0old-rendering271';if(id==='/__clarity271/old-budget.js')return '\0old-budget271';},load(id){if(id==='\0old-rendering271')return oldRendering;if(id==='\0old-budget271')return oldBudget;},configureServer(s){s.middlewares.use('/__clarity271/page',(_,r)=>{r.setHeader('Content-Type','text/html');r.end(html);});}}]});
let browser,context,page;const report={sourceHashes,errors:[],cases:[],limits:['Desktop WebKit touch emulation does not establish physical iPhone frame time or memory pressure.','Each pose uses its own four-sample linear-HDR reference at mobile3x or desktop2x display density; no frame displacement is counted as flicker.','Buffer totals exclude browser-owned display and shadow allocations; frame times include gl.finish for comparable completed work.']};
try{await server.listen();browser=await webkit.launch({headless:true});context=await browser.newContext({...devices['iPhone 13'],userAgent:devices['iPhone 13'].userAgent+' EdgiOS/131.0'});await context.addInitScript(()=>Object.defineProperty(navigator,'maxTouchPoints',{get:()=>5}));page=await context.newPage();page.on('pageerror',e=>report.errors.push(e.message));page.on('console',m=>{if(m.type()==='error')report.errors.push(m.text());});await page.goto('http://127.0.0.1:'+server.httpServer.address().port+'/__clarity271/page');await page.waitForFunction(()=>window.ready||window.harnessError,null,{timeout:120000});const failure=await page.evaluate(()=>window.harnessError);if(failure)throw Error(failure);report.info=await page.evaluate(()=>window.testInfo);
 for(const[name,yaw]of[['overview-a',0],['overview-b',.04]])report.cases.push(await page.evaluate(([n,y])=>window.measure(n,y),[name,yaw]));report.temporal=await page.evaluate(region=>window.temporalResidual(region),report.cases[0].region);assert(report.temporal.rows[1].edgeResidualChangeRmse<=report.temporal.rows[0].edgeResidualChangeRmse*1.01,'Mobile motion stability regressed');await page.evaluate(()=>window.detail());report.cases.push(await page.evaluate(()=>window.measure('old-detail',0)));
 const images=await page.evaluate(()=>window.images());for(const[name,png]of Object.entries(images))await writeFile(out+'/'+name+'.png',Buffer.from(png.split(',')[1],'base64'));
 assert.deepEqual(report.errors,[]);for(const row of report.cases)for(const v of row.variants){assert.equal(v.sceneDrawsPerFrame,1);assert.equal(v.lost,false);assert(v.bufferBytes<=24*1024*1024);}
 await page.evaluate(()=>window.viewer?.dispose());await context.close();await browser.close();
 browser=await chromium.launch({channel:'chrome',args:['--use-angle=metal']});context=await browser.newContext({viewport:{width:1200,height:800},deviceScaleFactor:2});page=await context.newPage();page.on('pageerror',e=>report.errors.push(e.message));await page.goto('http://127.0.0.1:'+server.httpServer.address().port+'/__clarity271/page?desktop=1');await page.waitForFunction(()=>window.ready||window.harnessError,null,{timeout:120000});const desktopFailure=await page.evaluate(()=>window.harnessError);if(desktopFailure)throw Error(desktopFailure);
 report.desktopInfo=await page.evaluate(()=>window.testInfo);report.desktop=[];report.desktop.push(await page.evaluate(()=>window.measure('desktop-still',0,false)));report.desktop.push(await page.evaluate(()=>window.measure('desktop-moving',.04,true)));
 const desktopImages=await page.evaluate(()=>window.images());for(const[name,png]of Object.entries(desktopImages))await writeFile(out+'/'+name+'.png',Buffer.from(png.split(',')[1],'base64'));
 for(const row of report.desktop)for(const v of row.variants){assert.equal(v.sceneDrawsPerFrame,row.name==='desktop-still'?4:1);assert.equal(v.lost,false);}
 for(const row of report.cases){const before=row.variants.find(v=>v.label==='before'),after=row.variants.find(v=>v.label==='resolution175');assert(after.error.rmse<before.error.rmse&&after.error.edgeRmse<before.error.edgeRmse,'Mobile clarity did not improve: '+row.name);}
 for(const row of report.desktop){const[before,after]=row.variants;assert(after.error.rmse<=before.error.rmse*1.01&&after.error.edgeRmse<=before.error.edgeRmse*1.01,'Desktop clarity regressed: '+row.name);}
 for(const p of paths)assert.equal(hash(await readFile(p)),sourceHashes[p],'Rendering source changed during comparison');
 assert.deepEqual(report.errors,[]);report.passed=true;console.log(JSON.stringify(report));
} catch(e){report.passed=false;report.failure=e.stack;console.error(e.stack);process.exitCode=1;}finally{await page?.evaluate(()=>window.viewer?.dispose()).catch(()=>{});await context?.close();await browser?.close();await server.close();await writeFile(out+'/comparison.json',JSON.stringify(report,null,2)+'\n');}
