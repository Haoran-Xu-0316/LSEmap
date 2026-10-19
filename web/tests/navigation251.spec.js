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
  await page.route('**/__navigation251',route=>route.fulfill({contentType:'text/html',body:`<!doctype html>
    <style>body{margin:0}#stage{position:relative;width:800px;height:600px}#labels{position:absolute;inset:0;pointer-events:none}#labels button{position:absolute;left:410px;top:220px;width:90px;height:40px;pointer-events:auto}</style>
    <div id="stage"><div id="canvas"></div><div id="labels"><button>MAR</button></div></div>`}));
  await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__navigation251`);
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
async function save(name,result){await mkdir('result/web/navigation251',{recursive:true});await writeFile(`result/web/navigation251/${name}.json`,JSON.stringify(result,null,2)+'\n');}


test('sideways trackpad gestures pan without changing scale or selecting a building',async({page})=>{
  await openFixture(page);
  const before=await page.evaluate(()=>({position:viewer.camera.position.toArray(),target:viewer.controls.target.toArray(),rotation:viewer.camera.quaternion.toArray(),radius:viewer.camera.position.distanceTo(viewer.controls.target)}));
  await page.mouse.move(300,320);
  await page.mouse.wheel(100,12);
  // A diagonal tail remains a pan until the gesture ends.
  await page.mouse.wheel(2,40);
  const after=await page.evaluate(()=>({position:viewer.camera.position.toArray(),target:viewer.controls.target.toArray(),rotation:viewer.camera.quaternion.toArray(),radius:viewer.camera.position.distanceTo(viewer.controls.target),pan:viewer.wheelGesture.pan}));
  expect(after.pan).toBe(true);
  expect(after.radius).toBeCloseTo(before.radius,6);
  expect(Math.hypot(...after.position.map((n,i)=>n-before.position[i]))).toBeGreaterThan(1);
  for(let i=0;i<3;i++)expect(after.position[i]-before.position[i]).toBeCloseTo(after.target[i]-before.target[i],6);
  for(let i=0;i<4;i++)expect(after.rotation[i]).toBeCloseTo(before.rotation[i],6);
  await save('trackpad-pan',{before,after});
});

test('shift wheel pans over labels and pinch still zooms after sideways movement',async({page})=>{
  await openFixture(page);
  const result=await page.evaluate(()=>{
    const dispatch=(target,options)=>target.dispatchEvent(new WheelEvent('wheel',{bubbles:true,cancelable:true,clientX:455,clientY:240,...options}));
    const radius=viewer.camera.position.distanceTo(viewer.controls.target),before=viewer.camera.position.clone();
    dispatch(document.querySelector('#labels button'),{deltaY:10,deltaMode:1,shiftKey:true});
    const pan={delta:viewer.camera.position.clone().sub(before).toArray(),radius:viewer.camera.position.distanceTo(viewer.controls.target)};
    dispatch(viewer.canvas,{deltaY:-3,ctrlKey:true});
    return {radius,pan,pinchRadius:viewer.camera.position.distanceTo(viewer.controls.target),panLatch:viewer.wheelGesture.pan,labelClicks};
  });
  expect(result.pan.radius).toBeCloseTo(result.radius,6);
  expect(Math.hypot(...result.pan.delta)).toBeGreaterThan(.1);
  expect(result.pinchRadius).toBeLessThan(result.radius);
  expect(result.panLatch).toBe(false);expect(result.labelClicks).toBe(0);
  await save('label-pan-pinch',result);
});

test('zoom buttons approach the visible surface instead of the old campus centre',async({page})=>{
  await openFixture(page);
  const result=await page.evaluate(()=>{
    const box=viewer.groups.get('MAR').children[0];
    box.position.set(0,8,47);box.updateMatrixWorld(true);
    const event={clientX:400,clientY:300};
    const anchor=viewer.surfaceAt(event).point.clone();
    const before=viewer.camera.position.distanceTo(anchor),oldRadius=viewer.camera.position.distanceTo(viewer.controls.target);
    viewer.zoom(.8);
    const first={target:viewer.transition.target.toArray(),position:viewer.transition.position.toArray(),distance:viewer.transition.position.distanceTo(anchor)};
    viewer.zoom(.8);
    const secondDistance=viewer.transition.position.distanceTo(anchor);
    viewer.tick(viewer.transition.start+viewer.transition.duration);cancelAnimationFrame(viewer.frame);
    const screen=anchor.clone().project(viewer.camera);
    return{before,oldRadius,first,secondDistance,screen:screen.toArray(),targetError:viewer.controls.target.distanceTo(anchor),height:viewer.camera.position.y};
  });
  expect(result.before).toBeLessThan(result.oldRadius*.3);
  expect(result.first.distance).toBeCloseTo(result.before*.8,5);
  expect(result.secondDistance).toBeCloseTo(result.before*.64,5);
  expect(Math.hypot(result.screen[0],result.screen[1])).toBeLessThan(.0001);
  expect(result.targetError).toBeLessThan(.0001);expect(result.height).toBeGreaterThan(.25);
  await save('button-surface-zoom',result);
});

test('vertical mouse wheel remains cursor-anchored zoom and disabled controls remain still',async({page})=>{
  await openFixture(page);
  const result=await page.evaluate(()=>{
    const box=viewer.groups.get('MAR').children[0];
    const projected=box.position.clone().project(viewer.camera);
    const x=(projected.x+1)*400,y=(1-projected.y)*300;
    const anchor=viewer.surfaceAt({clientX:x,clientY:y}).point.clone(),before=viewer.camera.position.distanceTo(anchor);
    viewer.canvas.dispatchEvent(new WheelEvent('wheel',{clientX:x,clientY:y,deltaY:-100,bubbles:true,cancelable:true}));
    const drift=viewer.surfaceAt({clientX:x,clientY:y}).point.distanceTo(anchor),after=viewer.camera.position.distanceTo(anchor);
    viewer.controls.enabled=false;
    const position=viewer.camera.position.clone();
    viewer.canvas.dispatchEvent(new WheelEvent('wheel',{clientX:x,clientY:y,deltaX:100,deltaY:0,bubbles:true,cancelable:true}));
    return{before,after,drift,disabledMovement:position.distanceTo(viewer.camera.position)};
  });
  expect(result.after).toBeLessThan(result.before);expect(result.drift).toBeLessThan(.01);expect(result.disabledMovement).toBe(0);
  await save('wheel-regression',result);
});

test.afterEach(async({page})=>{await page.evaluate(()=>window.viewer?.dispose());});
