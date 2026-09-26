import {test,expect} from '@playwright/test';
import * as THREE from 'three';

test('successive zoom presses accumulate and retain near/far safety limits',async()=>{
  globalThis.matchMedia=()=>({matches:false});
  const {CampusViewer}=await import('../src/viewer.js');
  const viewer={camera:{position:new THREE.Vector3(0,0,100)},controls:{target:new THREE.Vector3(),minDistance:.15,maxDistance:2400},transition:null,moveCamera:CampusViewer.prototype.moveCamera};
  for(let i=0;i<3;i++)CampusViewer.prototype.zoom.call(viewer,.78);
  expect(viewer.transition.position.length()).toBeCloseTo(100*.78**3,8);
  expect(viewer.transition.duration).toBe(180);
  for(let i=0;i<60;i++)CampusViewer.prototype.zoom.call(viewer,.5);
  expect(viewer.transition.position.length()).toBeCloseTo(.15,8);
  CampusViewer.prototype.zoom.call(viewer,1e6);
  expect(viewer.transition.position.length()).toBe(2400);
});

for(const width of [1440,390])test(`exterior lighting, zoom and interior return at ${width}px`,async({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.setViewportSize({width,height:width===390?844:1000});
  await page.goto('/#KGS');
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-KGS',{timeout:60000});
  await page.waitForTimeout(1000);
  await page.screenshot({path:`result/web/appearance/kgs-${width}.png`});
  await page.locator('#detail-view').click();await page.waitForTimeout(1000);
  await page.screenshot({path:`result/web/appearance/kgs-entrance-${width}.png`});
  await page.locator('#exterior-view').click();await page.waitForTimeout(1000);
  const canvas=page.locator('canvas');const before=await canvas.screenshot();
  await page.locator('#zoom-in').click({clickCount:3});await page.waitForTimeout(400);
  expect((await canvas.screenshot()).equals(before)).toBe(false);
  const box=await canvas.boundingBox();await page.mouse.move(box.x+box.width*.55,box.y+box.height*.4);await page.mouse.wheel(0,-300);await page.waitForTimeout(400);
  await page.locator('#interior-view').click();
  await expect(canvas).toHaveAttribute('data-detail-ready','interior-KGS');
  await page.locator('#overview').click();await expect(page.locator('#detail-panel')).toBeHidden();
  await page.waitForTimeout(1200);await page.screenshot({path:`result/web/appearance/campus-${width}.png`});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});
