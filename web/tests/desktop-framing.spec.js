import {test, expect} from '@playwright/test';
import * as THREE from 'three';

test('a narrow desktop canvas frames the building centre without a phantom bottom sheet', async()=>{
  globalThis.matchMedia = () => ({matches:false});
  const {CampusViewer} = await import('../src/viewer.js');
  const bounds={min:[-20,0,-10],max:[20,50,10]};
  const camera=new THREE.PerspectiveCamera(38,476/630,0.02,6000);
  let target;
  const viewer={camera,container:{clientWidth:476,clientHeight:630},activeCode:'CBG',
    moveCamera(position, centre){target=centre.clone();camera.position.copy(position);camera.lookAt(centre);camera.updateMatrixWorld();}};
  CampusViewer.prototype.fit.call(viewer,bounds,false,new THREE.Vector3(-.7,.9,1).normalize());
  expect(target.toArray()).toEqual([0,25,0]);
  expect(new THREE.Vector3(0,25,0).project(camera).y).toBeCloseTo(0,8);
  viewer.mode='detail';
  CampusViewer.prototype.updateCameraProjection.call(viewer);
  expect(camera.view?.enabled ?? false).toBe(false);
});

for(const width of [724,1000,390]) {
  test(`CBG and CKK retain usable exterior and entrance framing at ${width}px`,async({page})=>{
    await page.setViewportSize({width,height:844});
    await page.goto('/#CBG');
    await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-CBG',{timeout:60000});
    await page.waitForTimeout(1000);
    await page.screenshot({path:`result/web/framing-cbg-${width}.png`});
    await page.goto('/#CKK');
    // Reload also exercises direct-link selection, not only in-page navigation.
    await page.reload();
    await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-CKK',{timeout:60000});
    await page.locator('#detail-view').click();
    await expect(page.locator('#view-mode')).toHaveText('入口细节');
    await page.waitForTimeout(1000);
    await page.screenshot({path:`result/web/framing-ckk-${width}.png`});
  });
}
