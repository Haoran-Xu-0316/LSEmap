/** Validate explicitly approved packed maps in any browser model. */
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';

export function verifyApprovedImageMaps(buffer, document, records = [], label = 'model') {
  const approved = new Map(records.filter(record=>
    ['cartography','material-finish'].includes(record.kind)).map(record=>[record.sha256,record]));
  const jsonLength = buffer.readUInt32LE(12);
  const verified = [];
  for(const image of document.images ?? []) {
    assert(image.bufferView !== undefined && !image.uri,
      `${label}: image maps must be embedded and self-contained`);
    const view = document.bufferViews[image.bufferView];
    assert(view && view.byteLength > 0, `${label}: invalid image buffer`);
    const start = 28 + jsonLength + (view.byteOffset ?? 0);
    const bytes = buffer.subarray(start,start+view.byteLength);
    assert.equal(bytes.length,view.byteLength,`${label}: truncated image map`);
    const sha256 = createHash('sha256').update(bytes).digest('hex');
    assert(approved.has(sha256), `${label}: unapproved image or source photograph`);
    assert.equal(bytes.length,approved.get(sha256).bytes,`${label}: image size mismatch`);
    verified.push({name:image.name,sha256,kind:approved.get(sha256).kind});
  }
  return verified;
}
