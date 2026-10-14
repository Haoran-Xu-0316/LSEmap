import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {SKY_BACKDROP_URL} from '../src/outdoor-environment.js';
import {GROUND_FINISHES} from '../src/ground-textures.js';

test('sharp static sky and metre-scale asphalt stay within the optional asset budget', async () => {
 const manifest = JSON.parse(await readFile('web/public/environment/sources.json','utf8'));
 const sky = manifest.assets.find(item => item.path === SKY_BACKDROP_URL);
 const bytes = await readFile('web/public'+SKY_BACKDROP_URL);
 assert.equal(createHash('sha256').update(bytes).digest('hex'),sky.sha256);
 assert.equal(bytes.length,sky.bytes);assert(bytes.length<50_000);
 assert.deepEqual(sky.dimensions,[2048,1024]);assert.equal(sky.license,'CC0-1.0');
 const asphalt = GROUND_FINISHES.find(item => item.kind === 'asphalt');
 assert.equal(asphalt.metres,3);assert(asphalt.height<=.002);
 const relief = manifest.assets.find(item => item.path === asphalt.reliefUrl);
 assert.equal(relief.precisionBits,5);
 assert.equal(relief.source,'https://polyhaven.com/a/asphalt_02');
});
