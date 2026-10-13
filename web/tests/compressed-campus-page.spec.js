import {test,expect} from '@playwright/test';
import {readFile,mkdir} from 'node:fs/promises';
const transport=JSON.parse(await readFile('dist/models/campus-parts.json','utf8'));
for(const width of [1440,390])test(`lossless compressed campus loads at${width}px`,async({page})=>{
 const requests=[],errors=[];
 page.on('request',request=>requests.push(new URL(request.url()).pathname));
 page.on('pageerror',error=>errors.push(error.message));
 await page.setViewportSize({width,height:1000});await page.goto('/');
 await expect(page.locator('canvas')).toHaveAttribute('data-ready','true');
 await expect(page.locator('#loading')).toBeHidden();
 expect(requests.filter(path=>path.endsWith('.bin.gz'))).toEqual(expect.arrayContaining(transport.parts.map(part=>part.compressed.path)));
 expect(requests.filter(path=>/^\/models\/campus-.*\.bin$/.test(path))).toEqual([]);
 expect(await page.locator('#fallback').isVisible()).toBe(false);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 expect(errors).toEqual([]);
 await mkdir('result/web/loading-optimization',{recursive:true});
 await page.screenshot({path:`result/web/loading-optimization/compressed-${width}.png`});
});
test('unsupported decompression retains working raw transport',async({page})=>{
 await page.addInitScript(()=>{window.DecompressionStream=undefined});
 const requests=[],errors=[];page.on('request',r=>requests.push(new URL(r.url()).pathname));page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');await expect(page.locator('canvas')).toHaveAttribute('data-ready','true');
 expect(requests.filter(path=>path.endsWith('.bin.gz'))).toEqual([]);
 expect(requests.filter(path=>/^\/models\/campus-.*\.bin$/.test(path))).toEqual(expect.arrayContaining(transport.parts.map(part=>part.path)));
 expect(await page.locator('#fallback').isVisible()).toBe(false);expect(errors).toEqual([]);
});
