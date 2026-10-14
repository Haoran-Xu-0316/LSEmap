import {test,expect} from '@playwright/test';

test('published page loads captured road relief and selects both newly registered room studies',async({page})=>{
 test.setTimeout(140000);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 await page.goto('/#FAW');
 const canvas=page.locator('#stage canvas');
 await expect(canvas).toHaveAttribute('data-ground-ready','true',{timeout:90000});
 await expect(canvas).toHaveAttribute('data-ground-relief-ready','true');
 await expect(canvas).toHaveAttribute('data-sky-ready','true');
 for(const [code,id]of [['FAW','faw-401'],['CLM','clm-502']]){
  if(code==='CLM'){await page.locator('.back-button').click();await page.locator('#building-list [data-code="CLM"]').click();}
  await expect(canvas).toHaveAttribute('data-detail-ready','exterior-'+code);
  await page.locator('#interior-view').click();
  await expect(page.locator('#interior-space')).toBeVisible();
  await page.locator('#interior-space').selectOption(id);
  await expect(canvas).toHaveAttribute('data-detail-ready','interior-'+code+':'+id);
  await expect(page.locator('#interior-space')).toHaveValue(id);
 }
 expect(errors).toEqual([]);
});
