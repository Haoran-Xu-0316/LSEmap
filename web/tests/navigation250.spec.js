import {test, expect} from '@playwright/test';
import {createServer} from 'vite';
import {mkdir, writeFile} from 'node:fs/promises';

let server;
test.beforeAll(async()=>{
  server=await createServer({logLevel:'error',server:{host:'127.0.0.1',port:0}});
  await server.listen();
});
test.afterAll(async()=>{await server.close();});
async function openFixture(page){
  await page.route('**/__navigation250',route=>route.fulfill({contentType:'text/html',body:`<!doctype html>
    <style>body{margin:0}#stage{position:relative;width:800px;height:600px}#labels{position:absolute;inset:0;pointer-events:none}#labels button{position:absolute;left:410px;top:220px;width:90px;height:40px;pointer-events:auto}</style>
    <div id="stage"><div id="canvas"></div><div id="labels"><button>MAR</button></div></div>`}));
  await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__navigation250`);
  await page.evaluate(async()=>{
    const {CampusViewer}=await import('/src/viewer.js');
    const {THREE}=await import('/tests/interaction239-fixture.js');
    const container=document.querySelector('#canvas');container.style.cssText='width:800px;height:600px';
    const viewer=new CampusViewer(container,document.querySelector('#labels'),[],()=>{},()=>{});
    cancelAnimationFrame(viewer.frame);viewer.transition=null;viewer.ready=true;viewer.pickable=[];
    viewer.camera.position.set(0,10,60);viewer.controls.target.set(0,0,0);viewer.controls.update();viewer.camera.updateMatrixWorld();
    const box=new THREE.Mesh(new THREE.BoxGeometry(5,10,3),new THREE.MeshStandardMaterial());box.position.set(6,7,47);box.updateMatrixWorld();
    const group=new THREE.Group();group.add(box);group.updateMatrixWorld(true);viewer.scene.add(group);viewer.groups.set('MAR',group);
    window.viewer=viewer;window.THREE=THREE;window.labelClicks=0;
    document.querySelector('#labels button').addEventListener('click',()=>window.labelClicks++);
  });
}
async function save(name,result){await mkdir('result/web/navigation250',{recursive:true});await writeFile(`result/web/navigation250/${name}.json`,JSON.stringify(result,null,2)+'\n');}

test('overview pans directly and still supports a full azimuth orbit',async({page})=>{
  await openFixture(page);
  const before=await page.evaluate(()=>({position:viewer.camera.position.toArray(),target:viewer.controls.target.toArray(),rotation:viewer.camera.quaternion.toArray(),mode:viewer.panMode}));
  await page.mouse.move(250,330);await page.mouse.down();await page.mouse.move(320,360,{steps:8});await page.mouse.up();
  const pan=await page.evaluate(()=>({position:viewer.camera.position.toArray(),target:viewer.controls.target.toArray(),rotation:viewer.camera.quaternion.toArray()}));
  expect(before.mode).toBe(true);
  const delta=pan.position.map((v,i)=>v-before.position[i]);expect(Math.hypot(...delta)).toBeGreaterThan(1);
  for(let i=0;i<3;i++)expect(delta[i]).toBeCloseTo(pan.target[i]-before.target[i],7);
  for(let i=0;i<4;i++)expect(pan.rotation[i]).toBeCloseTo(before.rotation[i],7);
  await page.mouse.move(270,330);await page.mouse.down({button:'right'});await page.mouse.move(580,330,{steps:20});await page.mouse.up({button:'right'});
  const orbit=await page.evaluate(()=>({azimuth:viewer.controls.getAzimuthalAngle(),minimum:viewer.controls.minAzimuthAngle,maximum:viewer.controls.maxAzimuthAngle}));
  expect(Math.abs(orbit.azimuth)).toBeGreaterThan(1);expect(orbit.minimum).toBe(-Infinity);expect(orbit.maximum).toBe(Infinity);
  await save('pan-and-orbit',{before,pan,orbit});
});

test('cursor zoom approaches the actual facade without passing it or drifting on screen',async({page})=>{
  await openFixture(page);
  const result=await page.evaluate(()=>{
    const approximate=new THREE.Vector3(6,7,48.5).project(viewer.camera);
    const x=Math.round((approximate.x+1)*400),y=Math.round((1-approximate.y)*300);
    // Wheel coordinates are integer CSS pixels. Verify the surface under that
    // actual cursor, not a nearby unrounded point that diverges at high zoom.
    const anchor=viewer.surfaceAt({clientX:x,clientY:y}).point.clone();
    const projection=anchor.clone().project(viewer.camera);
    const initial=viewer.camera.position.distanceTo(anchor),samples=[];
    let queries=0;const surface=viewer.surfaceAt.bind(viewer);viewer.surfaceAt=event=>{queries++;return surface(event);};
    for(let i=0;i<55;i++){
      viewer.canvas.dispatchEvent(new WheelEvent('wheel',{clientX:x,clientY:y,deltaY:-100,bubbles:true,cancelable:true}));
      const projected=anchor.clone().project(viewer.camera);
      samples.push({distance:viewer.camera.position.distanceTo(anchor),error:Math.hypot((projected.x-projection.x)*400,(projected.y-projection.y)*300)});
    }
    return{initial,queries,samples,minimum:viewer.controls.minDistance};
  });
  await save('surface-zoom',result);
  expect(result.queries).toBe(1);expect(result.samples.at(-1).distance).toBeLessThan(.5);
  for(let i=0;i<result.samples.length;i++){
    expect(result.samples[i].error).toBeLessThan(.01);
    expect(result.samples[i].distance).toBeGreaterThanOrEqual(result.minimum-.00001);
    expect(result.samples[i].distance).toBeLessThanOrEqual((result.samples[i-1]?.distance??result.initial)+1e-6);
  }
  await save('surface-zoom',result);
});

test('a label can start a drag while a stationary label tap activates exactly once',async({page})=>{
  await openFixture(page);
  const before=await page.evaluate(()=>viewer.controls.target.toArray());
  await page.mouse.move(440,240);await page.mouse.down();await page.mouse.move(550,300,{steps:10});await page.mouse.up();
  const drag=await page.evaluate(()=>({target:viewer.controls.target.toArray(),clicks:labelClicks}));
  expect(Math.hypot(...drag.target.map((v,i)=>v-before[i]))).toBeGreaterThan(1);expect(drag.clicks).toBe(0);
  await page.locator('#labels button').click();
  expect(await page.evaluate(()=>labelClicks)).toBe(1);
  await page.locator('#labels button').focus();await page.keyboard.press('Enter');
  expect(await page.evaluate(()=>labelClicks)).toBe(2);
  await save('label-gestures',{before,drag,stationaryAndKeyboardClicks:2});
});

test('exterior navigation stays above ground and interior navigation keeps its full range',async({page})=>{
  await openFixture(page);
  const result=await page.evaluate(()=>{
    viewer.camera.position.set(0,-8,20);viewer.controls.target.set(0,4,0);viewer.tick(performance.now());cancelAnimationFrame(viewer.frame);
    const exterior={height:viewer.camera.position.y,targetHeight:viewer.controls.target.y,polar:viewer.controls.getPolarAngle()};
    viewer.mode='interior';viewer.camera.position.set(0,-8,20);viewer.tick(performance.now());cancelAnimationFrame(viewer.frame);
    return{exterior,interiorHeight:viewer.camera.position.y};
  });
  expect(result.exterior.height).toBeCloseTo(.25,7);expect(result.exterior.targetHeight).toBe(4);
  expect(result.exterior.polar).toBeGreaterThan(Math.PI/2);expect(result.interiorHeight).toBeLessThan(0);
  await save('ground-clearance',result);
});

test('two-finger pinch starts from the real surface depth and cancels a label tap',async({page})=>{
  await openFixture(page);
  const result=await page.evaluate(()=>{
    // Synthetic touch identifiers do not belong to the OS pointer registry.
    viewer.canvas.setPointerCapture=()=>{};viewer.canvas.releasePointerCapture=()=>{};
    const projection=new THREE.Vector3(6,7,48.5).project(viewer.camera);
    const x=Math.round((projection.x+1)*400),y=Math.round((1-projection.y)*300);
    const anchor=viewer.surfaceAt({clientX:x,clientY:y}).point.clone();
    const before=viewer.camera.position.distanceTo(anchor),initialOrbitRadius=viewer.camera.position.distanceTo(viewer.controls.target);
    let queries=0;const surface=viewer.surfaceAt.bind(viewer);viewer.surfaceAt=event=>{queries++;return surface(event);};
    const pointer=(type,id,px)=>viewer.canvas.dispatchEvent(new PointerEvent(type,{pointerId:id,pointerType:'touch',isPrimary:id===1,button:0,buttons:type==='pointerup'?0:1,clientX:px,clientY:y,bubbles:true}));
    pointer('pointerdown',1,x-30);pointer('pointerdown',2,x+30);
    const fittedRadius=viewer.camera.position.distanceTo(viewer.controls.target);
    pointer('pointermove',1,x-45);pointer('pointermove',2,x+45);
    pointer('pointerup',1,x-45);pointer('pointerup',2,x+45);
    return{before,initialOrbitRadius,fittedRadius,after:viewer.camera.position.distanceTo(anchor),queries,remainingTouches:viewer.zoomTouches.size,labelClicks};
  });
  expect(result.fittedRadius).toBeCloseTo(result.before,5);expect(result.fittedRadius).toBeLessThan(result.initialOrbitRadius*.4);
  expect(result.after).toBeLessThan(result.before*.8);expect(result.queries).toBe(1);expect(result.remainingTouches).toBe(0);expect(result.labelClicks).toBe(0);
  await save('touch-pinch',result);
});

test('surface anchoring skips hidden meshes and clipped front intersections',async({page})=>{
  await openFixture(page);
  const result=await page.evaluate(()=>{
    const root=viewer.groups.get('MAR');const front=root.children[0];
    const hiddenParent=new THREE.Group();hiddenParent.visible=false;
    const hidden=front.clone();hidden.position.z+=5;hiddenParent.add(hidden);root.add(hiddenParent);
    const back=front.clone();back.position.z-=6;root.add(back);root.updateMatrixWorld(true);
    const projected=front.position.clone().project(viewer.camera),event={clientX:(projected.x+1)*400,clientY:(1-projected.y)*300};
    const visibleHit=viewer.surfaceAt(event);
    // Keep the far half-space. Nearer intersections on the front mesh are cut.
    viewer.renderer.clippingPlanes=[new THREE.Plane(new THREE.Vector3(0,0,-1),44)];
    const clippedHit=viewer.surfaceAt(event);
    return{visibleWasFront:visibleHit.object===front,clippedWasBack:clippedHit.object===back};
  });
  expect(result).toEqual({visibleWasFront:true,clippedWasBack:true});await save('surface-visibility',result);
});

test('production controls stay in sync across overview, building selection and mobile layout',async({page})=>{
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/`);
  await expect(page.locator('#loading')).toBeHidden();
  await expect(page.locator('#pan-toggle')).toHaveAttribute('aria-pressed','true');
  await page.locator('#rotate-toggle').click();
  await expect(page.locator('#pan-toggle')).toHaveAttribute('aria-pressed','false');
  await expect(page.locator('#rotate-toggle')).toHaveAttribute('aria-pressed','true');
  await page.locator('#building-list').getByRole('button',{name:'MAR Marshall Building',exact:true}).click();
  await expect(page).toHaveURL(/#MAR$/);
  await expect(page.locator('#rotate-toggle')).toHaveAttribute('aria-pressed','true');
  await page.locator('#overview').click();
  await expect(page.locator('#pan-toggle')).toHaveAttribute('aria-pressed','true');
  await expect(page.locator('#rotate-toggle')).toHaveAttribute('aria-pressed','false');
  await page.setViewportSize({width:390,height:844});
  const bounds=await page.locator('.map-toolbar').boundingBox();
  expect(bounds.x).toBeGreaterThanOrEqual(0);expect(bounds.x+bounds.width).toBeLessThanOrEqual(390);
  const buttons=await page.locator('.map-toolbar button').evaluateAll(elements=>elements.map(button=>{const r=button.getBoundingClientRect();return{left:r.left,right:r.right};}));
  for(let i=1;i<buttons.length;i++)expect(buttons[i].left-buttons[i-1].right).toBeGreaterThanOrEqual(4);
  expect(errors).toEqual([]);await save('production-ui',{mobileToolbar:bounds,buttons,errors});
  await page.screenshot({path:'result/web/navigation250/mobile-controls.png'});
});

test.afterEach(async({page})=>{await page.evaluate(()=>window.viewer?.dispose());});
