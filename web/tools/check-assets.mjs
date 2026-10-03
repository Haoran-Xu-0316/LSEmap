/** Fail a build before shipping missing content or oversized Cloudflare assets. */
import { readdir, stat, readFile } from "node:fs/promises";
import { resolve, relative, join } from "node:path";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { detailFor } from "../src/content.js";

const output = resolve("dist");
const files = [];
async function walk(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) await walk(path);
    else files.push(path);
  }
}
await walk(output);
for (const file of files) {
  assert(
    relative(output, file) === 'models/campus.glb' || (await stat(file)).size < 25 * 1024 * 1024,
    `${relative(output, file)} exceeds Cloudflare's per-asset limit`,
  );
  assert(
    !/\.(blend\d?|pdf|py)$/.test(file),
    `Research-only file in output: ${file}`,
  );
}
const transport = JSON.parse(await readFile(join(output, 'models/campus-parts.json'), 'utf8'));
const chunks = [];
for (const part of transport.parts) {
  const bytes = await readFile(join(output, part.path));
  assert.equal(bytes.length, part.bytes);
  assert.equal(createHash('sha256').update(bytes).digest('hex'), part.sha256);
  assert(bytes.length < 25 * 1024 * 1024);
  chunks.push(bytes);
}
const assembled = Buffer.concat(chunks);
assert.equal(assembled.length, transport.bytes);
assert.equal(createHash('sha256').update(assembled).digest('hex'), transport.sha256);
assert(assembled.equals(await readFile(join(output, 'models/campus.glb'))));
const release = JSON.parse(await readFile(join(output, 'release.json'), 'utf8'));
assert(!release.assets['/models/campus.glb']);
for (const asset of Object.values(release.assets)) assert(asset.bytes < 25 * 1024 * 1024);
const catalogue = JSON.parse(
  await readFile(join(output, "models/catalogue.json"), "utf8"),
);
assert.equal(catalogue.buildings.length, 31);
assert.equal(new Set(catalogue.buildings.map((b) => b.code)).size, 31);
assert.equal(
  catalogue.buildings.filter((b) => b.status === "detailed").length,
  14,
);
for (const building of catalogue.buildings) {
  if (["COL", "CON"].includes(building.code)) {
    const direction = building.exteriorDirection;
    assert(direction && Math.hypot(...direction) > 0.99);
    assert(Math.hypot(direction[0], direction[2]) > 0.25,
      `${building.code} must open toward its street facade`);
  }
  if (building.interior)
    await stat(
      join(output, `models/${building.code.toLowerCase()}-interior.glb`),
    );
  if (building.bounds)
    assert(
      [...building.bounds.min, ...building.bounds.max].every(Number.isFinite),
    );
}
for (const building of catalogue.buildings) {
  const detail = detailFor(building);
  for (const [image] of detail.images)
    await stat(join(output, `images/${image}.webp`));
}
const detailAssets = catalogue.buildings.flatMap((building) =>
  [building.detailedExterior, building.detailedInterior, ...(building.interiorSpaces || []).map(space => space.detailedInterior)].filter(Boolean));
assert.equal(detailAssets.length, 30 + catalogue.buildings.filter(b => b.interior).length + catalogue.buildings.reduce((count,b) => count + (b.interiorSpaces || []).length, 0));
assert.equal(catalogue.buildings.filter((b) => b.interior).length, 25);
assert.equal(catalogue.buildings.filter(b => b.interiorStudy).length, 20);
assert.equal(catalogue.buildings.filter((b) => b.status === "facade").length, 15);
for (const asset of detailAssets) {
  const buffer = await readFile(join(output, asset.url));
  assert.equal(buffer.length, asset.bytes);
  assert.equal(createHash("sha256").update(buffer).digest("hex"), asset.sha256);
  assert(asset.triangles > 0);
}
for (const filename of [
  ...detailAssets.map((asset) => asset.url.replace("/models/", "")),
  "campus.glb",
  ...catalogue.buildings
    .filter((b) => b.interior)
    .map((b) => `${b.code.toLowerCase()}-interior.glb`),
]) {
  const buffer = await readFile(join(output, "models", filename));
  assert.equal(buffer.toString("ascii", 0, 4), "glTF");
  const jsonLength = buffer.readUInt32LE(12);
  const document = JSON.parse(buffer.toString("utf8", 20, 20 + jsonLength));
  assert.equal(
    document.scenes.length,
    1,
    `${filename} unexpectedly contains research scenes`,
  );
  assert(document.extensionsUsed.includes("KHR_draco_mesh_compression"));
  for (const image of document.images ?? []) {
    // The sole image exception is the original, hash-identified globe map.
    const approved = catalogue.generatedTextures?.find(texture => texture.name === image.name);
    assert(filename === 'campus.glb' && approved && image.bufferView !== undefined && !image.uri,
      `${filename} must not redistribute source photographs`);
    const view = document.bufferViews[image.bufferView];
    const start = 28 + jsonLength + (view.byteOffset ?? 0);
    const hash = createHash('sha256').update(buffer.subarray(start, start + view.byteLength)).digest('hex');
    assert.equal(hash, approved.sha256, 'Embedded globe map differs from the generated source');
  }
  if (filename.startsWith("details/")) {
    for (const mesh of document.meshes) {
      for (const primitive of mesh.primitives) {
        const surface = document.materials[primitive.material]?.extras?.surfaceDetail;
        if (surface?.kind !== "brick") continue;
        assert("TEXCOORD_0" in primitive.attributes, `${filename} has no brick coordinates`);
        assert(!("TEXCOORD_1" in primitive.attributes), `${filename} has mismatched facade UV layers`);
      }
    }
  }
  if (filename === "campus.glb") {
    const codes = new Set(
      document.nodes.map((node) => node.extras?.buildingCode),
    );
    for (const building of catalogue.buildings.filter((b) => b.bounds))
      assert(codes.has(building.code), `Missing model: ${building.code}`);
  }
}
console.log(
  `Checked ${files.length} deployable files, 31 building records and every model/gallery reference.`,
);
