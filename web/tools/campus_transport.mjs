import {gzipSync} from 'node:zlib';

/** Lossless gzip with a platform-neutral header for reproducible release hashes. */
export function compressCampusSegment(bytes) {
  const compressed = gzipSync(bytes, {level:6});
  // Gzip's OS byte does not affect decoding or the payload checksum. Node emits
  // 19 on macOS and3 on Linux;255 means unspecified and is identical on both.
  compressed[9] = 255;
  return compressed;
}
