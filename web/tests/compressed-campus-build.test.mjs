import {test} from 'node:test';
import assert from 'node:assert/strict';
import {gunzipSync} from 'node:zlib';
import {compressCampusSegment} from '../tools/campus_transport.mjs';
test('release gzip keeps exact model bytes and has a reproducible platform-neutral header',()=>{
 const original=Buffer.from(Array.from({length:4096},(_,index)=>index%251));
 const first=compressCampusSegment(original),second=compressCampusSegment(original);
 assert.deepEqual([...first.subarray(0,10)],[31,139,8,0,0,0,0,0,0,255]);
 assert.deepEqual(first,second);assert.deepEqual(gunzipSync(first),original);
 for(const platform of [3,19]){const platformHeader=Buffer.from(first);platformHeader[9]=platform;
  assert.deepEqual(gunzipSync(platformHeader),original);
  platformHeader[9]=255;assert.deepEqual(platformHeader,first);
 }
});
