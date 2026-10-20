import {test,expect} from '@playwright/test';
import {readFile,mkdir,writeFile} from 'node:fs/promises';

let catalogue, viewerModule;
test.beforeAll(async()=>{
  catalogue=JSON.parse(await readFile('dist/models/catalogue.json','utf8'));
  const release=JSON.parse(await readFile('dist/release.json','utf8'));
  viewerModule=Object.keys(release.assets).find(path=>/^\/assets\/viewer-.*\.js$/.test(path));
});

async function openViewer(page) {
  await page.route('**/__resource253',route=>route.fulfill({contentType:'text/html',body:`<!doctype html><link rel="icon" href="data:,"><style>body{margin:0}#stage{width:1000px;height:800px}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">
    import {CampusViewer} from '${viewerModule}';
    const catalogue=await(await fetch('/models/catalogue.json')).json();
    const viewer=new CampusViewer(document.querySelector('#stage'),document.querySelector('#labels'),catalogue.buildings,()=>{},()=>{},()=>{},catalogue.sourceModelSha256);
    viewer.loadCampusExteriors=async()=>{};
    await viewer.load(); await viewer.environmentReady;
    window.viewer=viewer; window.building=catalogue.buildings.find(b=>b.code==='MAR');
    viewer.activeCode='MAR';
    const parse=viewer.loader.parseAsync.bind(viewer.loader);
    window.parses=0; viewer.loader.parseAsync=(...args)=>{window.parses++;return parse(...args);};
    window.fixtureReady=true;
  </script>`}));
  await page.goto('/__resource253');
  await page.waitForFunction(()=>window.fixtureReady,null,{timeout:60000});
}

async function roomState(page,id) {
  return page.evaluate(id=>({parses:window.parses,detail:viewer.canvas.dataset.detailReady,
    sameScene:viewer.activeDetail?.group===viewer.interiors.get(`MAR:${id}`),
    pending:viewer.interiorLoads.size,cachedDetailCopies:viewer.detailCache.models.size}),id);
}

async function save(name,result) {
  await mkdir('result/web/loading253',{recursive:true});
  await writeFile(`result/web/loading253/${name}.json`,JSON.stringify(result,null,2)+'\n');
}

test('a room entry and repeated selection share one transfer, decode and scene',async({page})=>{
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  const room=catalogue.buildings.find(b=>b.code==='MAR').interiorSpaces.find(s=>s.id==='mar-104');
  let requests=0;page.on('request',request=>{if(new URL(request.url()).pathname===room.interiorAsset)requests++;});
  await openViewer(page);
  await page.evaluate(()=>Promise.all([viewer.showInterior(building,'mar-104'),viewer.showInterior(building,'mar-104')]));
  await expect.poll(()=>roomState(page,'mar-104')).toMatchObject({parses:1,detail:'interior-MAR:mar-104',sameScene:true,pending:0,cachedDetailCopies:0});
  await page.evaluate(()=>viewer.showInterior(building,'mar-104'));
  const state=await roomState(page,'mar-104');
  expect(requests).toBe(1);expect(state.parses).toBe(1);expect(state.sameScene).toBe(true);expect(errors).toEqual([]);
  await save('shared-room',{requests,...state,errors});
});

for(const kind of ['initial-room','detail-upgrade']) {
  test(`switching rooms aborts an obsolete ${kind} request`,async({page})=>{
    const building=catalogue.buildings.find(b=>b.code==='MAR');
    const heldUrl=kind==='initial-room'
      ? building.interiorSpaces.find(room=>room.id==='mar-104').interiorAsset
      : building.detailedInterior.url;
    let release; const gate=new Promise(resolve=>{release=resolve;});
    await page.route(`**${heldUrl}`,async route=>{await gate;await route.continue().catch(()=>{});});
    try {
      await openViewer(page);
      const started=page.waitForRequest(request=>new URL(request.url()).pathname===heldUrl);
      await page.evaluate(kind=>{
        window.oldResult=null;
        window.oldRequest=viewer.showInterior(building,kind==='initial-room'?'mar-104':null).then(value=>{window.oldResult=value;});
      },kind);
      await started;
      const aborted=page.waitForEvent('requestfailed',{predicate:request=>new URL(request.url()).pathname===heldUrl});
      await page.evaluate(()=>viewer.showInterior(building,'mar-108'));
      const request=await aborted;
      await expect.poll(()=>roomState(page,'mar-108')).toMatchObject({detail:'interior-MAR:mar-108',sameScene:true,pending:0});
      const state=await roomState(page,'mar-108');
      expect(request.failure()?.errorText).toContain('ABORTED');
      expect(await page.evaluate(()=>viewer.detailCache.pending.size)).toBe(0);
      if(kind==='initial-room') {
        expect(await page.evaluate(()=>window.oldResult)).toBe(false);
        expect(await page.evaluate(()=>viewer.interiors.has('MAR:mar-104'))).toBe(false);
        expect(state.parses).toBe(1);
      } else expect(state.parses).toBe(2);
      await save(kind,{aborted:request.failure(),...state});
    } finally {release();}
  });
}

test('background exterior work pauses inside a room and resumes in the campus',async({page})=>{
  await openViewer(page);
  await page.evaluate(()=>{
    viewer.mode='interior'; viewer.transition=null; viewer.interacting=false;
    viewer.lastNavigationAt=-10000;
    viewer.buildings=[{code:'TEST',detailedExterior:{url:'/unused.glb'}}];
    window.backgroundStarts=0; viewer.loadExterior=async()=>{window.backgroundStarts++;};
    delete viewer.loadCampusExteriors;
    window.backgroundWork=viewer.loadCampusExteriors();
  });
  await page.waitForTimeout(160);
  expect(await page.evaluate(()=>window.backgroundStarts)).toBe(0);
  await page.evaluate(()=>{viewer.mode='campus';});
  await expect.poll(()=>page.evaluate(()=>window.backgroundStarts)).toBe(1);
  await page.evaluate(()=>window.backgroundWork);
  await save('background-pause',{startedInsideRoom:0,startedAfterReturning:1});
});

test.afterEach(async({page})=>{await page.evaluate(()=>window.viewer?.dispose()).catch(()=>{});});
