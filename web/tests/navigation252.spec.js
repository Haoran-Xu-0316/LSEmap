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
  await page.route('**/__navigation252',route=>route.fulfill({contentType:'text/html',body:`<!doctype html>
    <style>body{margin:0}#stage{position:relative;width:800px;height:600px}#labels{position:absolute;inset:0;pointer-events:none}#labels button{position:absolute;left:410px;top:220px;width:90px;height:40px;pointer-events:auto}</style>
    <div id="stage"><div id="canvas"></div><div id="labels"><button>MAR</button></div></div>`}));
  await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__navigation252`);
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
async function save(name,result){await mkdir('result/web/navigation252',{recursive:true});await writeFile(`result/web/navigation252/${name}.json`,JSON.stringify(result,null,2)+'\n');}



async function pose(page){return page.evaluate(()=>({position:viewer.camera.position.toArray(),target:viewer.controls.target.toArray(),rotation:viewer.camera.quaternion.toArray(),azimuth:viewer.controls.getAzimuthalAngle()}));}
async function drag(page,button,from,to,shift=false){if(shift)await page.keyboard.down('Shift');await page.mouse.move(...from);await page.mouse.down({button});await page.mouse.move(...to,{steps:10});await page.mouse.up({button});if(shift)await page.keyboard.up('Shift');}

test('one set of gestures pans with left drag and orbits with right drag or Shift',async({page})=>{
 await openFixture(page);const before=await pose(page);
 await drag(page,'left',[250,330],[330,370]);const pan=await pose(page);
 for(let i=0;i<3;i++)expect(pan.position[i]-before.position[i]).toBeCloseTo(pan.target[i]-before.target[i],6);
 for(let i=0;i<4;i++)expect(pan.rotation[i]).toBeCloseTo(before.rotation[i],6);
 expect(Math.hypot(...pan.position.map((v,i)=>v-before.position[i]))).toBeGreaterThan(1);
 await drag(page,'right',[260,340],[440,340]);const right=await pose(page);
 expect(Math.abs(right.azimuth-pan.azimuth)).toBeGreaterThan(.1);
 await page.evaluate(()=>{viewer.controls.enableDamping=false;viewer.controls.update();viewer.controls.enableDamping=true;});
 const startShift=await pose(page);await drag(page,'left',[260,340],[440,340],true);const shift=await pose(page);
 expect(Math.abs(shift.azimuth-startShift.azimuth)).toBeGreaterThan(.1);
 const mappings=await page.evaluate(()=>({left:viewer.controls.mouseButtons.LEFT===THREE.MOUSE.PAN,right:viewer.controls.mouseButtons.RIGHT===THREE.MOUSE.ROTATE,single:viewer.controls.touches.ONE===THREE.TOUCH.PAN,double:viewer.controls.touches.TWO===THREE.TOUCH.DOLLY_ROTATE}));
 expect(mappings).toEqual({left:true,right:true,single:true,double:true});await save('direct-gestures',{before,pan,right,shift,mappings});
});

test('two-finger movement rotates while one-finger movement pans',async({page})=>{
 await openFixture(page);
 await page.evaluate(()=>{viewer.controls.enableDamping=false;viewer.controls.update();});
 const result=await page.evaluate(()=>{
  viewer.canvas.setPointerCapture=()=>{};viewer.canvas.releasePointerCapture=()=>{};
  const send=(type,id,x,y)=>viewer.canvas.dispatchEvent(new PointerEvent(type,{pointerId:id,pointerType:'touch',isPrimary:id===1,button:0,buttons:type==='pointerup'?0:1,clientX:x,clientY:y,bubbles:true}));
  const before=viewer.camera.quaternion.clone(),position=viewer.camera.position.clone(),target=viewer.controls.target.clone();
  send('pointerdown',1,250,330);send('pointermove',1,290,350);send('pointerup',1,290,350);
  const single={angle:before.angleTo(viewer.camera.quaternion),offsetError:viewer.camera.position.clone().sub(position).distanceTo(viewer.controls.target.clone().sub(target))};
  viewer.controls.enableDamping=false;viewer.controls.update();
  const rotation=viewer.camera.quaternion.clone();
  send('pointerdown',1,250,330);send('pointerdown',2,350,330);send('pointermove',1,290,340);send('pointermove',2,390,340);send('pointerup',1,290,340);send('pointerup',2,390,340);
  return{single,doubleAngle:rotation.angleTo(viewer.camera.quaternion),remaining:viewer.zoomTouches.size,labelClicks};
 });
 expect(result.single.angle).toBeLessThan(.00001);expect(result.single.offsetError).toBeLessThan(.00001);expect(result.doubleAngle).toBeGreaterThan(.001);expect(result.remaining).toBe(0);expect(result.labelClicks).toBe(0);await save('touch-orbit',result);
});

test('touch pinch still approaches the selected surface without a mode button',async({page})=>{
 await openFixture(page);
 const result=await page.evaluate(()=>{
  viewer.canvas.setPointerCapture=()=>{};viewer.canvas.releasePointerCapture=()=>{};
  const projection=new THREE.Vector3(6,7,48.5).project(viewer.camera),x=Math.round((projection.x+1)*400),y=Math.round((1-projection.y)*300);
  const anchor=viewer.surfaceAt({clientX:x,clientY:y}).point.clone(),before=viewer.camera.position.distanceTo(anchor);
  const send=(type,id,px)=>viewer.canvas.dispatchEvent(new PointerEvent(type,{pointerId:id,pointerType:'touch',isPrimary:id===1,button:0,buttons:type==='pointerup'?0:1,clientX:px,clientY:y,bubbles:true}));
  send('pointerdown',1,x-30);send('pointerdown',2,x+30);send('pointermove',1,x-45);send('pointermove',2,x+45);send('pointerup',1,x-45);send('pointerup',2,x+45);
  return{before,after:viewer.camera.position.distanceTo(anchor),remaining:viewer.zoomTouches.size};
 });
 expect(result.after).toBeLessThan(result.before*.8);expect(result.remaining).toBe(0);await save('touch-pinch',result);
});

test('label drags navigate and stationary taps activate only once',async({page})=>{
 await openFixture(page);const before=await pose(page);
 await drag(page,'left',[455,240],[540,270]);await page.waitForTimeout(350);
 const after=await pose(page);expect(Math.hypot(...after.position.map((n,i)=>n-before.position[i]))).toBeGreaterThan(1);
 expect(await page.evaluate(()=>labelClicks)).toBe(0);
 const menuPrevented=await page.evaluate(()=>!document.querySelector('#labels button').dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true})));
 expect(menuPrevented).toBe(true);
 await page.locator('#labels button').click();expect(await page.evaluate(()=>labelClicks)).toBe(1);
 await save('label-drag',{before,after});
});

test('camera changes cancel a pending tap without changing gesture mappings',async({page})=>{
 await openFixture(page);
 const result=await page.evaluate(async()=>{
  let jumped=false;viewer.pickTimer=setTimeout(()=>jumped=true,20);
  viewer.moveCamera(viewer.camera.position.clone(),viewer.controls.target.clone(),false);
  await new Promise(resolve=>setTimeout(resolve,30));
  return{jumped,leftPan:viewer.controls.mouseButtons.LEFT===THREE.MOUSE.PAN,rightOrbit:viewer.controls.mouseButtons.RIGHT===THREE.MOUSE.ROTATE};
 });
 expect(result).toEqual({jumped:false,leftPan:true,rightOrbit:true});
});

test('production toolbar has no navigation modes and stays compact across views and mobile',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/`);
 await expect(page.locator('#loading')).toBeHidden();await expect(page.locator('#pan-toggle,#rotate-toggle')).toHaveCount(0);
 await page.locator('#building-list').getByRole('button',{name:'MAR Marshall Building',exact:true}).click();
 await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready','exterior-MAR');
 await expect(page.locator('canvas')).toHaveCSS('cursor','grab');await page.locator('#overview').click();
 await page.setViewportSize({width:390,height:844});const bounds=await page.locator('.map-toolbar').boundingBox();
 expect(bounds.x).toBeGreaterThanOrEqual(0);expect(bounds.x+bounds.width).toBeLessThanOrEqual(390);
 const buttons=await page.locator('.map-toolbar button').evaluateAll(elements=>elements.map(b=>{const r=b.getBoundingClientRect();return{left:r.left,right:r.right};}));
 for(let i=1;i<buttons.length;i++)expect(buttons[i].left-buttons[i-1].right).toBeGreaterThanOrEqual(4);
 expect(buttons).toHaveLength(5);expect(errors).toEqual([]);await save('production-ui',{bounds,buttons,errors});await page.screenshot({path:'result/web/navigation252/mobile-toolbar.png'});
});

test('leaving a loading page does not show a failed-model state',async({page})=>{
 const applicationErrors=[];page.on('console',message=>{if(message.text().startsWith('Campus viewer could not load:'))applicationErrors.push(message.text());});
 let abandoned=false;
 await page.route('**/models/campus*',async route=>{
  if(!abandoned){abandoned=true;await page.evaluate(()=>window.dispatchEvent(new Event('pagehide')));}
  await route.abort();
 });
 await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/`);
 await expect.poll(()=>abandoned).toBe(true);await page.waitForTimeout(50);
 await expect(page.locator('#fallback')).toBeHidden();expect(applicationErrors).toEqual([]);
});

test.afterEach(async({page})=>{await page.evaluate(()=>window.viewer?.dispose());});
