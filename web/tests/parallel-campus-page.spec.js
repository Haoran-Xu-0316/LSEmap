import {test,expect} from '@playwright/test';
test('published campus loads through concurrent verified segments',async({page})=>{
 const requests=[],errors=[];page.on('request',r=>requests.push(new URL(r.url()).pathname));page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');await page.waitForFunction(()=>document.querySelector('canvas')?.dataset.ready==='true');
 expect(requests.filter(p=>/^\/models\/campus-\d+-.*\.bin$/.test(p))).toHaveLength(3);
 expect(requests.includes('/models/campus.glb')).toBe(false);
 expect(requests.includes('/draco/draco_decoder.wasm')).toBe(true);
 expect(await page.locator('#fallback').isVisible()).toBe(false);expect(errors).toEqual([]);
});
