import {test,expect} from '@playwright/test';
import {mkdir,writeFile} from 'node:fs/promises';

test('production reload reuses verified campus bytes without fetching any segment',async({page})=>{
 const errors=[],requests=[];page.on('pageerror',e=>errors.push(e.message));
 page.on('request',request=>{if(/\/models\/campus-\d+-.*\.bin/.test(request.url()))requests.push(request.url());});
 const coldStart=Date.now();await page.goto('/');
 await expect(page.locator('canvas')).toHaveAttribute('data-ready','true',{timeout:70000});
 const coldMs=Date.now()-coldStart;expect(requests.length).toBe(3);
 await expect.poll(()=>page.evaluate(()=>new Promise(resolve=>{
  const request=indexedDB.open('lsemap-model-bytes',1);
  request.onsuccess=()=>{
   const db=request.result,transaction=db.transaction('current-model','readonly');
   const entry=transaction.objectStore('current-model').get('campus');
   entry.onsuccess=()=>{resolve(entry.result?.blob?.size>40_000_000);db.close();};
   entry.onerror=()=>{resolve(false);db.close();};
  };
  request.onerror=()=>resolve(false);
 })),{timeout:15000}).toBe(true);
 requests.length=0;const warmStart=Date.now();await page.reload();
 await expect(page.locator('canvas')).toHaveAttribute('data-ready','true',{timeout:70000});
 const warmMs=Date.now()-warmStart;
 expect(requests).toEqual([]);await expect(page.locator('canvas')).toHaveAttribute('data-sky-ready','true');
 await expect(page.locator('#fallback')).toBeHidden();expect(errors).toEqual([]);
 await mkdir('result/web/loading-cache-acceptance',{recursive:true});
 await writeFile('result/web/loading-cache-acceptance/measurement.json',JSON.stringify({coldMs,warmMs,coldCampusSegments:3,warmCampusSegments:0,errors},null,2)+'\n');
 await page.screenshot({path:'result/web/loading-cache-acceptance/desktop.png'});
});

test('mobile remains usable when optional sky and persistent storage are unavailable',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.setViewportSize({width:390,height:844});
 await page.addInitScript(()=>{Object.defineProperty(window,'indexedDB',{value:undefined});});
 await page.route('**/environment/*.hdr',route=>route.abort());
 await page.goto('/#MAR');
 await expect(page.locator('canvas')).toHaveAttribute('data-ready','true',{timeout:70000});
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-MAR',{timeout:70000});
 await expect(page.locator('canvas')).toHaveAttribute('data-sky-ready','fallback');
 await expect(page.locator('#fallback')).toBeHidden();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 expect(errors).toEqual([]);await page.screenshot({path:'result/web/loading-cache-acceptance/mobile-fallback.png'});
});
