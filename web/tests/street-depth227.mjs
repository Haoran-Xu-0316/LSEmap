/** Decode the actual campus through CampusViewer and inspect the repaired contact.
 * The private harness uses real Draco assets. All browser/server resources close.
 */
import {createServer} from 'vite';
import {chromium} from 'playwright';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const catalogue=JSON.parse(await readFile('web/public/models/catalogue.json','utf8'));
assert(['226','227'].includes(catalogue.version));
const phase=catalogue.version==='226'?'before':'after';
const html=`<!doctype html><style>#scene{width:1000px;height:800px}#labels{display:none}</style><div id="scene"></div><div id="labels"></div><script type="module">
import {CampusViewer} from '/src/viewer.js';
const catalogue=await(await fetch('/models/catalogue.json')).json();
const viewer=new CampusViewer(document.querySelector('#scene'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{throw Error('Context lost')},()=>{},catalogue.sourceModelSha256);
await viewer.load();
const site=viewer.groups.get('SITE');if(!site)throw Error('Missing production SITE');site.updateWorldMatrix(true,true);
const triangles={asphalt:[],stone:[]};const materials=new Set();const point=viewer.camera.position.clone();
site.traverse(mesh=>{
 if(!mesh.isMesh)return;
 const material=mesh.material;const kind=material.name==='WEB_Road asphalt.002'?'asphalt':material.name==='WEB_Pale campus paving.002'?'stone':null;
 if(!kind)return;materials.add(material.name);
 const geometry=mesh.geometry;const positions=geometry.attributes.position;const index=geometry.index;const count=index?index.count:positions.count;
 for(let i=0;i<count;i+=3){
  const face=[];
  for(let j=0;j<3;j++){point.fromBufferAttribute(positions,index?index.getX(i+j):i+j).applyMatrix4(mesh.matrixWorld);face.push([point.x,-point.z,point.y]);}
  // The contact is horizontal at authored24mm. Retain actual decoded coordinates.
  if(face.some(p=>Math.abs(p[2]-.024)>.002))continue;
  if(Math.max(...face.map(p=>p[0]))<20||Math.min(...face.map(p=>p[0]))>38||Math.max(...face.map(p=>p[1]))< -37||Math.min(...face.map(p=>p[1]))> -10)continue;
  triangles[kind].push(face);
 }
});
window.result={triangles,materials:[...materials]};window.ready=true;
</script>`;
const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{name:'street-depth-check',configureServer(server){server.middlewares.use('/__street-depth',(_request,response)=>{response.setHeader('Content-Type','text/html');response.end(html);});}}]});
let browser;
try{
 await server.listen();const port=server.httpServer.address().port;
 browser=await chromium.launch({args:process.platform==='darwin'?['--use-angle=metal']:['--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:1000,height:800}});const errors=[];
 page.on('pageerror',error=>errors.push(error.message));
 await page.goto(`http://127.0.0.1:${port}/__street-depth`);
 await page.waitForFunction(()=>window.ready,null,{timeout:120000});
 const result=await page.evaluate(()=>window.result);assert.deepEqual(errors,[]);
 assert(result.triangles.asphalt.length&&result.triangles.stone.length,'Missing real contact geometry');
 const proof='result/blender/stage227/browser';await mkdir(proof,{recursive:true});
 await writeFile(proof+'/street-decoded-'+phase+'.json',JSON.stringify({version:catalogue.version,sourceModelSha256:catalogue.sourceModelSha256,realViewerAndDracoAssets:true,errors,...result})+'\n');
 console.log('STREET_DECODED',phase,result.triangles.asphalt.length,result.triangles.stone.length);
}finally{await browser?.close();await server.close();}
