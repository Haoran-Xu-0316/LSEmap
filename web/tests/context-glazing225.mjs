/** Exercise the real production overview, including the shared context material pass.
 * Model loading, reflection maps and material cloning are not mocked. The temporary
 * browser/server are closed even on assertion failures and never enter the build.
 */
import {createServer} from 'vite';
import {chromium} from 'playwright';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const catalogue=JSON.parse(await readFile('web/public/models/catalogue.json','utf8'));
const bytes=await readFile('web/public/models/campus.glb');
const document=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
const originals=document.materials.map(material=>({name:material.name,opacity:material.pbrMetallicRoughness?.baseColorFactor?.[3]??1,transparent:material.alphaMode==='BLEND'}));
const html=`<!doctype html><style>body{margin:0}#scene{width:1280px;height:900px}#labels{display:none}</style><div id="scene"></div><div id="labels"></div><script type="module">
import {CampusViewer} from '/src/viewer.js';
import {isGlazingMaterial} from '/src/surface-materials.js';
const buildings=${JSON.stringify(catalogue.buildings)};
const viewer=new CampusViewer(document.querySelector('#scene'),document.querySelector('#labels'),buildings,()=>{},()=>{throw Error('Context lost')},()=>{},${JSON.stringify(catalogue.sourceModelSha256)});
await viewer.load();await viewer.environmentReady;
const materials=new Set();viewer.groups.get('CONTEXT').traverse(object=>{if(object.isMesh)for(const material of [object.material].flat())materials.add(material);});
window.result=[...materials].filter(isGlazingMaterial).map(material=>({name:material.name,roughness:material.roughness,metalness:material.metalness,reflectionEnvironment:!!material.envMap,opacity:material.opacity,transparent:material.transparent}));
window.ready=true;
</script>`;
const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{name:'context-glazing-check',configureServer(server){server.middlewares.use('/__context-glazing',(_request,response)=>{response.setHeader('Content-Type','text/html');response.end(html);});}}]});
let browser;
try{
 await server.listen();const port=server.httpServer.address().port;
 browser=await chromium.launch({args:process.platform==='darwin'?['--use-angle=metal']:['--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:1280,height:900},reducedMotion:'reduce'});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto(`http://127.0.0.1:${port}/__context-glazing`);
 await page.waitForFunction(()=>window.ready,null,{timeout:120000});
 const records=await page.evaluate(()=>window.result);
 const proof='result/blender/stage225/browser';await mkdir(proof,{recursive:true});
 await writeFile(proof+'/context-glazing.json',JSON.stringify({sourceModelSha256:catalogue.sourceModelSha256,realViewerAndAssets:true,records,errors},null,2)+'\n');
 assert(records.length>0,'The actual context has no authored glazing to exercise');
 for(const material of records){
  assert(material.roughness>=.12&&material.roughness<=.22,material.name+' context pass overwrote glazing roughness: '+material.roughness);
  assert.equal(material.metalness,0,material.name+' glazing became metallic');
  assert(material.reflectionEnvironment,material.name+' lacks the shared environment reflection');
  const source=originals.find(original=>original.name===material.name);assert(source,material.name+' missing source material');
  assert.equal(material.opacity,source.opacity,material.name+' source opacity changed');
  assert.equal(material.transparent,source.transparent,material.name+' source transparency changed');
 }
 assert.deepEqual(errors,[]);console.log('CONTEXT_GLAZING_VERIFIED',records.length);
}finally{await browser?.close();await server.close();}
