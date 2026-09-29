import { test, expect } from '@playwright/test';
import * as THREE from 'three';

async function viewerPrototype() {
  globalThis.matchMedia = () => ({ matches: false });
  return (await import('../src/viewer.js')).CampusViewer.prototype;
}

test('a returning drag never selects or recentres a building', async () => {
  const prototype = await viewerPrototype();
  const viewer = {
    ready: true, mode: 'campus',
    pointerStart: { x: 100, y: 100, id: 1, time: performance.now(), moved: false },
    canvas: { getBoundingClientRect() { throw Error('Drag was interpreted as a click'); } },
  };
  prototype.trackPointer.call(viewer, { pointerId: 1, clientX: 200, clientY: 100 });
  prototype.trackPointer.call(viewer, { pointerId: 1, clientX: 101, clientY: 100 });
  prototype.pick.call(viewer, { pointerId: 1, clientX: 101, clientY: 100, button: 0 });
  expect(viewer.pointerStart).toBeNull();
});

test('surface focus uses visible unclipped geometry without moving the camera', async () => {
  const prototype = await viewerPrototype();
  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 100);
  camera.updateMatrixWorld();
  const root = new THREE.Group();
  for (const [z, visible] of [[-2, false], [-4, true], [-6, true]]) {
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(8, 8), new THREE.MeshBasicMaterial());
    mesh.position.z = z; mesh.visible = visible; root.add(mesh);
  }
  root.updateMatrixWorld(true);
  const target = new THREE.Vector3(0, 0, -10);
  const viewer = {
    ready: true, activeCode: 'CBG', activeDetail: { group: root }, camera,
    canvas: { getBoundingClientRect: () => ({left:0, top:0, width:100, height:100}) },
    pointer: new THREE.Vector2(), raycaster: new THREE.Raycaster(),
    renderer: {clippingPlanes:[new THREE.Plane(new THREE.Vector3(0,0,-1),-5)]},
    controls: {target, minDistance:0.25, update(){camera.lookAt(target);}}, transition: {},
  };
  prototype.focusSurface.call(viewer, {button:0, clientX:50, clientY:50});
  expect(target.toArray()).toEqual([0,0,-6]);
  expect(camera.position.toArray()).toEqual([0,0,0]);
  expect(viewer.transition).toBeNull();
});

test('resizing preserves the entrance view and long titles clear the compass', async ({page}) => {
  await page.goto('/#CKK');
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-CKK',{timeout:60000});
  await page.locator('#detail-view').click();
  await page.setViewportSize({width:390,height:844});
  await expect(page.locator('#detail-view')).toHaveAttribute('aria-pressed','true');
  await expect(page.locator('#view-mode')).toHaveText('入口细节');
  await page.setViewportSize({width:1440,height:1000});
  await expect(page.locator('#detail-view')).toHaveAttribute('aria-pressed','true');
  await page.goto('/#LRB');
  await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-LRB',{timeout:60000});
  for (const width of [390,320]) {
    await page.setViewportSize({width,height:844});
    const heading = await page.locator('.scene-heading').boundingBox();
    const compass = await page.locator('#north').boundingBox();
    expect(heading.x + heading.width).toBeLessThan(compass.x);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
  await page.screenshot({path:'result/web/navigation-phone.png'});
});
