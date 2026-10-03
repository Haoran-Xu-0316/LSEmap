import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import worker from '../worker.js';
const origin='https://lsemap.example';
const assets={fetch:async request=>{
 try {const bytes=await readFile('dist'+new URL(request.url).pathname);return new Response(bytes);}
 catch{return new Response(null,{status:404});}
}};
test('campus transport reconstructs exact GLB and supports cache validation',async()=>{
 const source=await readFile('dist/models/campus.glb');
 const response=await worker.fetch(new Request(origin+'/models/campus.glb'),{ASSETS:assets});
 expect(response.status).toBe(200);expect(response.headers.get('Content-Length')).toBe(String(source.length));
 expect(Buffer.from(await response.arrayBuffer()).equals(source)).toBe(true);
 const cached=await worker.fetch(new Request(origin+'/models/campus.glb',{headers:{'If-None-Match':response.headers.get('ETag')}}),{ASSETS:assets});
 expect(cached.status).toBe(304);
 const head=await worker.fetch(new Request(origin+'/models/campus.glb',{method:'HEAD'}),{ASSETS:assets});
 expect(head.body).toBeNull();expect(head.headers.get('ETag')).toBe(response.headers.get('ETag'));
});
test('missing campus segment returns failure instead of partial geometry',async()=>{
 const partial={fetch:request=>new URL(request.url).pathname.endsWith('.bin')?Promise.resolve(new Response(null,{status:404})):assets.fetch(request)};
 const response=await worker.fetch(new Request(origin+'/models/campus.glb'),{ASSETS:partial});
 expect(response.status).toBe(503);
});
