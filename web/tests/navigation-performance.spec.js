import {test,expect} from '@playwright/test';
test('map heading and toolbar buttons remain separated on phone and desktop',async({page})=>{
 for(const width of [1440,390,320]){
  await page.setViewportSize({width,height:900});await page.goto('/');
  if(width<=700)await page.locator('#index-toggle').click();
  await expect(page.locator('h1')).toHaveText('LSE校园地图');
  if(width<=700)await page.locator('#index-toggle').click();
  const a=await page.locator('#labels-toggle').boundingBox(),b=await page.locator('#context-toggle').boundingBox();
  expect(b.x-a.x-a.width).toBeGreaterThanOrEqual(3.9);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 }
});
test('drag keeps the display resolution stable and preserves the loaded model',async({page})=>{
 await page.goto('/#CBG');const canvas=page.locator('canvas');
 await expect(canvas).toHaveAttribute('data-detail-ready','exterior-CBG',{timeout:60000});
 const pixels=()=>canvas.evaluate(el=>el.width*el.height);
 const before=await pixels();const box=await canvas.boundingBox();
 await page.mouse.move(box.x+box.width*.65,box.y+box.height*.6);await page.mouse.down();
 await page.mouse.move(box.x+box.width*.7,box.y+box.height*.65,{steps:8});
 await expect.poll(pixels).toBe(before);
 await page.mouse.up();await expect.poll(pixels).toBe(before);
 await expect(canvas).toHaveAttribute('data-detail-ready','exterior-CBG');
 await page.screenshot({path:'result/web/navigation-polish/restored.png'});
});
