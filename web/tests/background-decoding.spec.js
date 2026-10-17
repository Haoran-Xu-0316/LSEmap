import {test, expect} from '@playwright/test';
import {createServer} from 'vite';
import {mkdir, writeFile} from 'node:fs/promises';

for (const finish of ['settle', 'select', 'dispose']) {
  test(`background GLTF parsing yields to navigation and handles ${finish}`, async ({page}) => {
    const server = await createServer({logLevel:'error', server:{host:'127.0.0.1', port:0}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    try {
      await server.listen();
      await page.route('**/__background-decode', route => route.fulfill({contentType:'text/html', body:
        '<div id="stage" style="width:800px;height:600px"></div><div id="labels"></div>'}));
      await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__background-decode`);
      const result = await page.evaluate(async finish => {
        const {CampusViewer} = await import('/src/viewer.js');
        const catalogue = await (await fetch('/models/catalogue.json')).json();
        const building = catalogue.buildings.find(b => b.code === 'PEA');
        const viewer = new CampusViewer(document.querySelector('#stage'), document.querySelector('#labels'), [building], () => {}, () => {});
        cancelAnimationFrame(viewer.frame);
        viewer.interacting = true;
        viewer.lastNavigationAt = performance.now();
        const parse = viewer.loader.parseAsync.bind(viewer.loader);
        let parses = 0, parseStart = null, downloaded;
        const bytesReady = new Promise(resolve => { downloaded = resolve; });
        const fetchModel = window.fetch;
        // Observe the real completed GLB response, not just response headers.
        window.fetch = async (...args) => {
          const response = await fetchModel(...args);
          if (String(args[0]) === building.detailedExterior.url) {
            const bytes = await response.arrayBuffer();
            downloaded();
            return new Response(bytes, {status:response.status, headers:response.headers});
          }
          return response;
        };
        viewer.loader.parseAsync = (...args) => {
          parses++; parseStart = performance.now(); return parse(...args);
        };
        const loaded = viewer.loadExterior(building, true);
        const completion = loaded.then(() => 'loaded', error => error.name);
        try {
          await bytesReady;
          await new Promise(resolve => setTimeout(resolve, 300));
          const parsesDuringGesture = parses;
          const resumedAt = performance.now();
          if (finish === 'dispose') viewer.dispose();
          else if (finish === 'select') viewer.activeCode = building.code;
          else { viewer.interacting = false; viewer.lastNavigationAt = resumedAt; }
          const outcome = await completion;
          return {finish, parsesDuringGesture, parses, outcome,
            resumeDelayMs:parseStart === null ? null : parseStart - resumedAt,
            attached:viewer.exteriors.has(building.code)};
        } finally {
          window.fetch = fetchModel;
          if (!viewer.disposed) viewer.dispose();
        }
      }, finish);
      expect(result.parsesDuringGesture).toBe(0);
      expect(result.parses).toBe(finish === 'dispose' ? 0 : 1);
      expect(result.attached).toBe(finish !== 'dispose');
      expect(result.outcome).toBe(finish === 'dispose' ? 'AbortError' : 'loaded');
      if (finish === 'settle') expect(result.resumeDelayMs).toBeGreaterThanOrEqual(195);
      if (finish === 'select') expect(result.resumeDelayMs).toBeLessThan(190);
      expect(errors).toEqual([]);
      await mkdir('result/web/background-decoding', {recursive:true});
      await writeFile(`result/web/background-decoding/${finish}.json`, JSON.stringify(result, null, 2)+'\n');
    } finally { await server.close(); }
  });
}
