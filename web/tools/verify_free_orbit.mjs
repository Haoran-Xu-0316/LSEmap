/** Exercise real pointer rotation in all view modes on a private, unshipped page. */
import {createServer} from 'vite';
import {chromium} from 'playwright';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
const source=await readFile('web/tools/render_web_gallery.mjs','utf8');
const html=source.split('const html = `')[1].split('`;\nconst server')[0].replace('window.galleryReady=true;', 'window.roofViewer=viewer;window.galleryReady=true;');
const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{name:'roof-diagnostic',configureServer(server){server.middlewares.use('/__roof',(_req,res)=>{res.setHeader('Content-Type','text/html');res.end(html);});}}]});
let browser;
try{
 await server.listen();browser=await chromium.launch({args:['--use-angle=metal']});
 const page=await browser.newPage({viewport:{width:1400,height:1120},reducedMotion:'reduce'});
 await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__roof`);
 await page.waitForFunction(()=>window.galleryReady,null,{timeout:120000});

 const results=[];
 for(const mode of ['campus','exterior','detail','interior']){
  await page.evaluate(async mode=>{
   const v=window.roofViewer,b=v.buildings.find(b=>b.code===(['detail','interior'].includes(mode)?'MAR':'CBG'));
   if(mode==='campus')v.home(false);
   else if(mode==='interior'){await v.showInterior(b);await v.upgradeModel(b,'interior');}
   else {v.select(b);await v.upgradeModel(b,'exterior');if(mode==='detail')v.showDetail(b);}
  },mode);
  await page.mouse.move(900,1000);await page.mouse.down();
  await page.mouse.move(900,100,{steps:15});await page.mouse.up();
  await page.waitForTimeout(300);
  const result=await page.evaluate(mode=>{
   const c=window.roofViewer.controls;
   return {mode,actualMode:window.roofViewer.mode,polar:c.getPolarAngle(),max:c.maxPolarAngle,minAzimuth:String(c.minAzimuthAngle),maxAzimuth:String(c.maxAzimuthAngle)};
  },mode);
  if((['detail','interior'].includes(mode)&&result.actualMode!==mode)||result.polar<=Math.PI/2||result.max!==Math.PI)throw Error(JSON.stringify(result));
  results.push(result);
 }
 await mkdir('result/web/orbit-verification',{recursive:true});
 await writeFile('result/web/orbit-verification/results.json',JSON.stringify(results,null,2));
 console.log(JSON.stringify(results));
}finally{await browser?.close();await server.close();}
