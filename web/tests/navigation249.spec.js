import {test,expect} from '@playwright/test';
import {createServer} from 'vite';
import {mkdir,writeFile} from 'node:fs/promises';

test('overview supports cursor zoom, explicit drag pan, touch pan and surface approach',async({page})=>{
  const server=await createServer({logLevel:'error',server:{host:'127.0.0.1',port:0}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  try{
    await server.listen();
    await page.route('**/__navigation249',route=>route.fulfill({contentType:'text/html',body:'<style>body{margin:0}#stage{width:960px;height:768px}</style><div id="stage"></div><div id="labels"></div>'}));
    await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__navigation249`);
    await page.evaluate(async()=>{
      const {CampusViewer}=await import('/src/viewer.js'),{THREE}=await import('/tests/interaction239-fixture.js');
      const v=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),[],code=>window.picks.push(code),()=>{});window.picks=[];window.viewer=v;window.THREE=THREE;
      const group=new THREE.Group(),ground=new THREE.Mesh(new THREE.PlaneGeometry(1000,1000),new THREE.MeshBasicMaterial({color:0x888888}));ground.rotation.x=-Math.PI/2;group.add(ground);v.groups.set('SITE',group);group.userData.buildingCode='A';v.pickable=[group];v.scene.add(group);v.ready=true;v.controls.enableDamping=false;v.moveCamera(new THREE.Vector3(0,60,100),new THREE.Vector3(0,0,0),false);v.scene.updateMatrixWorld(true);
      v.frame=requestAnimationFrame(v.tick);
      window.hitAt=(x,y)=>{v.camera.updateMatrixWorld();const ray=new THREE.Raycaster();ray.setFromCamera(new THREE.Vector2(x/960*2-1,1-y/768*2),v.camera);return ray.intersectObject(ground)[0].point;};
      window.anchor=window.hitAt(690,450);window.beforeDistance=v.camera.position.distanceTo(window.anchor);
    });
    await page.mouse.move(690,450);await page.mouse.wheel(0,-300);
    const zoom=await page.evaluate(()=>({drift:window.hitAt(690,450).distanceTo(window.anchor),before:window.beforeDistance,after:viewer.camera.position.distanceTo(window.anchor)}));
    expect(zoom.after).toBeLessThan(zoom.before);expect(zoom.drift).toBeLessThan(.01);
    await page.evaluate(()=>{const label=document.createElement('button');label.textContent='A';label.style='position:absolute;left:660px;top:420px;width:60px;height:60px';document.querySelector('#labels').append(label);window.beforeDistance=viewer.camera.position.distanceTo(viewer.controls.target);});
    await page.mouse.move(690,450);await page.mouse.wheel(0,-150);
    await expect.poll(()=>page.evaluate(()=>viewer.camera.position.distanceTo(viewer.controls.target))).toBeLessThan(await page.evaluate(()=>window.beforeDistance));
    await page.evaluate(()=>document.querySelector('#labels').replaceChildren());
    const before=await page.evaluate(()=>{viewer.setPanMode(true);return{position:viewer.camera.position.toArray(),target:viewer.controls.target.toArray()};});
    await page.mouse.move(480,380);await page.mouse.down();await page.mouse.move(620,430,{steps:12});await page.mouse.up();
    const pan=await page.evaluate(before=>{const a=viewer.camera.position.clone().sub(new THREE.Vector3(...before.position)),b=viewer.controls.target.clone().sub(new THREE.Vector3(...before.target));return{distance:a.length(),sameOffset:a.distanceTo(b),touch:viewer.controls.touches.ONE===THREE.TOUCH.PAN,cursor:viewer.canvas.style.cursor};},before);
    expect(pan.distance).toBeGreaterThan(5);expect(pan.sameOffset).toBeLessThan(.001);expect(pan.touch).toBe(true);expect(pan.cursor).toBe('grab');
    await page.evaluate(()=>{viewer.setPanMode(false);window.anchor=window.hitAt(490,450);window.beforeDistance=viewer.camera.position.distanceTo(window.anchor);});
    await page.mouse.dblclick(490,450);
    await expect.poll(()=>page.evaluate(()=>viewer.transition===null)).toBe(true);
    const approach=await page.evaluate(()=>({distance:viewer.camera.position.distanceTo(window.anchor),before:window.beforeDistance,targetDrift:viewer.controls.target.distanceTo(window.anchor),overview:viewer.activeCode===null,touchRotate:viewer.controls.touches.ONE===THREE.TOUCH.ROTATE}));
    expect(approach.distance).toBeLessThan(approach.before*.5);expect(approach.targetDrift).toBeLessThan(.001);expect(approach.overview).toBe(true);expect(approach.touchRotate).toBe(true);expect(errors).toEqual([]);expect(await page.evaluate(()=>window.picks)).toEqual([]);
    await page.mouse.click(490,450);await expect.poll(()=>page.evaluate(()=>window.picks.length)).toBe(1);
    await mkdir('result/web/navigation249',{recursive:true});await writeFile('result/web/navigation249/proof.json',JSON.stringify({zoom,pan,approach},null,2)+'\n');
  }finally{await page.evaluate(()=>window.viewer?.dispose()).catch(()=>{});await server.close();}
});
