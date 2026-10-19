import {test,expect} from '@playwright/test';
import {mkdir} from 'node:fs/promises';

test('pan control stays accessible and separated on desktop and phone',async({page})=>{
  test.setTimeout(120000);await mkdir('result/web/navigation249',{recursive:true});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  for(const width of [1440,390]){
    await page.setViewportSize({width,height:900});await page.goto('/');
    await expect(page.locator('canvas')).toHaveAttribute('data-ready','true',{timeout:60000});
    await expect(page.locator('#loading')).toBeHidden();
    const pan=page.getByRole('button',{name:'平移',exact:true});await expect(pan).toBeVisible();await pan.click();await expect(pan).toHaveAttribute('aria-pressed','true');
    const bounds=await page.locator('.map-toolbar button').evaluateAll(buttons=>buttons.map(b=>{const r=b.getBoundingClientRect();return{x:r.x,right:r.right,width:r.width};}));
    for(let i=0;i<bounds.length;i++){expect(bounds[i].x).toBeGreaterThanOrEqual(0);expect(bounds[i].right).toBeLessThanOrEqual(width);if(i)expect(bounds[i].x-bounds[i-1].right).toBeGreaterThanOrEqual(3);}
    await pan.click();await expect(pan).toHaveAttribute('aria-pressed','false');
    await expect(page.locator('canvas')).toHaveAttribute('data-sky-backdrop-ready','true',{timeout:30000});
    await page.screenshot({path:`result/web/navigation249/ui-${width}.png`});
  }
  expect(errors).toEqual([]);
});
