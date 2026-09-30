import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test('saved KSW oriel has a bowed cross-section and preserves other buildings',async()=>{
 const audit=JSON.parse(await readFile('result/blender/stage54/kingsway-oriel-audit.json'));
 const shape=JSON.parse(await readFile('result/blender/stage54/oriel-cross-section.json'));
 expect(audit.changedOtherObjects).toEqual([]);
 expect(audit.changedExistingObjects.every(name=>name.startsWith('KSW_D3_'))).toBeTruthy();
 expect(shape.measuredBowDifference).toBeGreaterThan(.2);
 expect(shape.measuredBowDifference).toBeLessThan(.5);
 expect(audit.components.find(c=>c.name==='KSW_D3_window_glass').parts).toBe(4);
});

test('KSW total view and close view load the same current exterior',async({page})=>{
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto('/#KSW');
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-KSW',{timeout:60000});
 await page.locator('#detail-view').click();
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-KSW');
 await expect(page.locator('#fallback')).toBeHidden();
 expect(errors).toEqual([]);
});
