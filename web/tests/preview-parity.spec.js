import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
const release=JSON.parse(await readFile('dist/release.json','utf8'));
for (const code of ['KGS','MAR']) {
  test(`local demo and online ${code} load the same release and view`, async ({ browser }) => {
    test.skip(!process.env.LSE_LIVE_PARITY,'Opt-in comparison with the deployed release');
    const context=await browser.newContext({viewport:{width:1440,height:1000},deviceScaleFactor:1,reducedMotion:'reduce'});
    for (const [name,origin] of [['local','http://127.0.0.1:4174'],['online','https://lsemap.xhr0316.workers.dev']]) {
      const page=await context.newPage();
      const response=await page.request.get(origin+'/release.json',{headers:{'Cache-Control':'no-cache'}});
      expect(await response.json()).toEqual(release);
      await page.goto(origin+'/#'+code);
      await expect(page.locator('canvas')).toHaveAttribute('data-detail-ready',`exterior-${code}`,{timeout:60000});
      expect(await page.locator('script[type=module][src]').getAttribute('src')).toBe(release.entryScript);
      await page.locator('.detail-photo img').evaluate(image=>image.decode());
      await page.waitForTimeout(1100);
      await page.locator('canvas').screenshot({path:`result/web/release${release.version}/parity-${code}-${name}.png`});
      await page.close();
    }
    await context.close();
  });
}
