import {test,expect} from '@playwright/test';
test('both historical classrooms load on demand and return to the unchanged exterior',async({page})=>{
 test.setTimeout(120000);const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 await page.goto('/#OLD');const canvas=page.locator('#stage canvas');
 for(const[code,id]of[['OLD','old-321'],['MAR','mar-107']]){
  if(code==='MAR'){await page.locator('.back-button').click();await page.locator('#building-list [data-code="MAR"]').click();}
  await expect(canvas).toHaveAttribute('data-detail-ready','exterior-'+code,{timeout:90000});await page.locator('#interior-view').click();await page.locator('#interior-space').selectOption(id);await expect(canvas).toHaveAttribute('data-detail-ready','interior-'+code+':'+id);await expect(page.locator('#interior-space')).toHaveValue(id);
  await page.screenshot({path:`result/blender/stage200/${id}-browser.png`});
  await page.locator('#exterior-view').click();await expect(canvas).toHaveAttribute('data-detail-ready','exterior-'+code);
 }
 expect(errors).toEqual([]);
});
