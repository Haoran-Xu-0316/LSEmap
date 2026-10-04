import {test,expect} from '@playwright/test';
import {readFile,mkdtemp,mkdir,copyFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,dirname} from 'node:path';
import {createServer} from 'node:http';
import worker from '../worker.js';

// Serve precisely the manifest upload, not dist: a dist preview can conceal
// missing decoder, logo or other public files excluded by the deploy packager.
test('the exact deployment package boots 3D and displays every logo',async({page})=>{
 const release=JSON.parse(await readFile('dist/release.json'));
 for(const path of ['/favicon.svg','/logo-lse.svg','/draco/draco_wasm_wrapper.js','/draco/draco_decoder.wasm'])expect(release.assets[path],path).toBeTruthy();
 const root=await mkdtemp(join(tmpdir(),'lsemap-runtime-test-'));
 let server;
 try{
  for(const path of Object.keys(release.assets)){
   const target=join(root,path.slice(1));await mkdir(dirname(target),{recursive:true});await copyFile('dist'+path,target);
  }
  await copyFile('dist/release.json',join(root,'release.json'));
  // Exercise the production Worker too: the campus GLB is intentionally absent
  // from static assets and is assembled from the verified segment manifest.
  const assets={async fetch(request){
   const path=new URL(request.url).pathname;
   try{
    const bytes=await readFile(join(root,path==='/'?'index.html':path.slice(1)));
    const type=path.endsWith('.js')?'application/javascript':path.endsWith('.css')?'text/css':path.endsWith('.svg')?'image/svg+xml':path.endsWith('.wasm')?'application/wasm':path==='/'?'text/html':'application/octet-stream';
    return new Response(bytes,{headers:{'Content-Type':type}});
   }catch{return new Response(null,{status:404});}
  }};
  server=createServer(async(request,response)=>{
   try{
    const result=await worker.fetch(new Request('http://127.0.0.1'+request.url),{ASSETS:assets});
    response.writeHead(result.status,Object.fromEntries(result.headers));
    response.end(Buffer.from(await result.arrayBuffer()));
   }catch{response.writeHead(500);response.end();}
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400)errors.push(r.status()+' '+r.url())});
  await page.goto('http://127.0.0.1:'+server.address().port+'/#OLD');
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-OLD',{timeout:60000});
  await expect(page.locator('#fallback')).toBeHidden();
  expect(await page.locator('.brand-mark').evaluate(image=>image.complete&&image.naturalWidth>0)).toBeTruthy();
  expect(await page.locator('.about-logo').evaluate(image=>image.complete&&image.naturalWidth>0)).toBeTruthy();
  expect(errors).toEqual([]);
 }finally{
  if(server)await new Promise(resolve=>server.close(resolve));
  await rm(root,{recursive:true,force:true});
 }
});
