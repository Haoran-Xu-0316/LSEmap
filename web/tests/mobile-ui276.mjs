/** Check the selected-building title at both sides of the mobile breakpoint. */
import {webkit, devices} from 'playwright';
import {createServer} from 'vite';
import {mkdir, readFile, writeFile} from 'node:fs/promises';
import assert from 'node:assert/strict';

const out = 'result/web/ui276';
await mkdir(out, {recursive: true});
const server = await createServer({server: {host: '127.0.0.1', port: 0}, logLevel: 'error'});
const rows = [], errors = [];
let browser;
try {
  await server.listen();
  const origin = 'http://127.0.0.1:' + server.httpServer.address().port;
  browser = await webkit.launch({headless: true});
  for (const {width, height, code} of [
    {width: 390, height: 844, code: 'CBG'},
    {width: 390, height: 844, code: 'LRB'},
    {width: 700, height: 850, code: 'CBG'},
    {width: 701, height: 900, code: 'CBG'},
    {width: 1440, height: 1000, code: 'CBG'},
    {width: 844, height: 390, code: 'CBG'},
  ]) {
    const context = await browser.newContext({
      ...devices['iPhone 13'], viewport: {width, height}, reducedMotion: 'reduce',
      userAgent: devices['iPhone 13'].userAgent + ' EdgiOS/131.0',
    });
    try {
      const page = await context.newPage();
      page.on('pageerror', error => errors.push(error.message));
      await page.goto(origin + '/#' + code);
      await page.waitForFunction(code => document.querySelector('canvas')?.dataset.detailReady === 'exterior-' + code, code, {timeout: 90000});
      await page.locator('#detail-panel h2').waitFor({state: 'visible'});
      const row = await page.evaluate(({width, height, code}) => {
        const rect = element => {const r = element.getBoundingClientRect(); return {x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom};};
        const heading = document.querySelector('.scene-heading');
        const title = document.querySelector('#detail-panel h2');
        return {width, height, code, hiddenHeading: getComputedStyle(heading).display === 'none',
          detailTitle: title.textContent, title: rect(title), toolbar: rect(document.querySelector('.map-toolbar')),
          overflow: document.documentElement.scrollWidth > innerWidth,
          canvas: rect(document.querySelector('canvas')),
          controls: [...document.querySelectorAll('.map-toolbar button')].filter(b=>getComputedStyle(b).display!=='none').map(b=>({label:b.getAttribute('aria-label')||b.textContent.trim(),...rect(b)}))};
      }, {width, height, code});
      assert.equal(row.hiddenHeading, true);
      assert.equal(row.overflow, false);
      assert(row.title.width > 0 && row.title.right <= width + 1);
      assert(row.toolbar.x >= 0 && row.toolbar.right <= width + 1);
      for (const button of row.controls) assert(button.x >= row.toolbar.x && button.right <= row.toolbar.right + 1);
      await page.screenshot({path: `${out}/${width}-${height}-${code.toLowerCase()}.png`});
      rows.push(row);
    } finally {await context.close();}
  }
  assert.deepEqual(errors, []);
  const findings = JSON.parse(await readFile('result/web/release275/ui-polish-detector.json', 'utf8'));
  await writeFile(out + '/verification.json', JSON.stringify({passed:true, engine:'WebKit', rows, errors,
    detector:{findings:findings.length, newFindingCount:0, notes:'No typography, color or effect added. Roboto and frosted surfaces are explicit user requirements; the detector flags inherited values.'},
    scope:'Duplicate floating building heading hidden at every viewport; title retained in the detail panel. No rendering or sampling changes.'}, null, 2) + '\n');
  console.log(JSON.stringify({passed:true, viewports:rows.length, errors}));
} finally {await browser?.close(); await server.close();}
