import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

const catalogue = JSON.parse(await readFile('web/public/models/catalogue.json', 'utf8'));
const baseline = JSON.parse(await readFile('web/tests/fixtures/edition17-models.json', 'utf8'));
const changedExteriors = ['5LF', '50L', '51L', 'CON', 'KSW', 'PEA', 'PEL', 'SAR', 'SAW', 'LRB'];

test('all building groups are integrated and unaffected exported geometry is preserved', () => {
  expect(catalogue.version).toBe('24');
  expect(catalogue.buildings).toHaveLength(31);
  for (const building of catalogue.buildings) {
    expect(building.latestReview.version).toBe(24);

    for (const [kind, digest] of Object.entries(baseline[building.code])) {
      const changed = kind === 'detailedExterior'
        ? changedExteriors.includes(building.code)
        : ['SAW', 'LRB'].includes(building.code);
      if (changed) expect(building[kind].sha256).not.toBe(digest);
      else expect(building[kind].sha256).toBe(digest);
    }
  }

});
