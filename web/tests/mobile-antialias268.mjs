/** Fixed, independent WebKit measurement. Run this file; production sources are read only. */
import assert from 'node:assert/strict';
import {mkdir, readFile, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {webkit, devices} from 'playwright';
import {createServer} from 'vite';

const OUTPUT = 'result/web/mobile268';
const TRACKED_SOURCES = ['web/src/rendering-quality.js', 'web/src/surface-materials.js', 'web/src/viewer.js'];
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const sourceHashes = Object.fromEntries(await Promise.all(TRACKED_SOURCES.map(async path => [path, sha256(await readFile(path))])));
await mkdir(OUTPUT, {recursive: true});

// Each result is compared with its own matched-pose reference. Camera movement
// between poses is deliberately excluded from the image-error calculation.
async function installHarness() {
  const THREE = await import(window.moduleBase + 'three/build/three.module.js');
  const {CampusViewer} = await import('/src/viewer.js');
  const {createRenderPipeline} = await import('/src/rendering-quality.js');
  const {ProgressiveStill} = await import('/src/progressive-still.js');
  const {OutputPass} = await import(window.moduleBase + 'three/examples/jsm/postprocessing/OutputPass.js');
  const catalogue = await (await fetch('/models/catalogue.json')).json();
  const building = catalogue.buildings.find(item => item.code === 'SAW');
  const viewer = new CampusViewer(document.querySelector('#stage'), document.querySelector('#labels'), catalogue.buildings,
    () => {}, () => { window.contextLost = true; }, () => {}, catalogue.sourceModelSha256);
  window.viewer = viewer;
  await viewer.load();
  await viewer.environmentReady;
  viewer.select(building);
  await viewer.upgradeModel(building, 'exterior');
  await viewer.localContext.ready;
  cancelAnimationFrame(viewer.frame);
  viewer.transition = null;
  viewer.interacting = false;
  viewer.controls.enableDamping = false;
  const selected = viewer.exteriors.get('SAW');
  if (!selected || viewer.canvas.dataset.detailReady !== 'exterior-SAW') throw Error('Original detailed SAW not loaded');
  for (const child of viewer.scene.children) if (child !== selected && !child.isLight) child.visible = false;
  selected.visible = true;
  viewer.scene.updateMatrixWorld(true);

  const {renderer, scene, camera, renderPipeline: pipeline} = viewer;
  const shaderUniforms = new Set();
  const materials = new Set();
  selected.traverse(object => {
    for (const material of [object.material].flat()) if (material) materials.add(material);
  });
  for (const material of materials) {
    const previousCompile = material.onBeforeCompile;
    const previousKey = material.customProgramCacheKey.bind(material);
    material.customProgramCacheKey = () => previousKey() + "|mobile268-instrumented";
    material.onBeforeCompile = function(shader, renderer) {
      previousCompile.call(this, shader, renderer);
      if (shader.uniforms.surfaceMobileFilter) shaderUniforms.add(shader.uniforms.surfaceMobileFilter);
    };
    material.needsUpdate = true;
  }
  const filter = value => { for (const uniform of shaderUniforms) uniform.value = value; };
  const centre = new THREE.Box3().setFromObject(selected).getCenter(new THREE.Vector3());
  const direction = new THREE.Vector3(...building.exteriorDirection).normalize();
  const baseOffset = direction.multiplyScalar(98);
  camera.clearViewOffset();
  camera.fov = 38;
  camera.position.copy(centre).add(baseOffset);
  camera.lookAt(centre);
  camera.updateProjectionMatrix();
  camera.updateMatrixWorld(true);
  renderer.setRenderTarget(null);
  pipeline.render(); // Compile source hooks and finish the one scheduled shadow update.
  renderer.shadowMap.needsUpdate = false;
  renderer.info.autoReset = false;
  const nativeRender = renderer.render.bind(renderer);
  let sceneSubmissions = 0;
  renderer.render = function(candidateScene, candidateCamera) {
    if (candidateScene === scene && candidateCamera === camera) sceneSubmissions++;
    return nativeRender(candidateScene, candidateCamera);
  };
  const drawingSize = () => renderer.getDrawingBufferSize(new THREE.Vector2());
  function capture() {
    const {x: width, y: height} = drawingSize();
    const pixels = new Uint8Array(width * height * 4);
    renderer.getContext().readPixels(0, 0, width, height, renderer.getContext().RGBA,
      renderer.getContext().UNSIGNED_BYTE, pixels);
    return {pixels, width, height, png: viewer.canvas.toDataURL('image/png')};
  }
  function pose(yaw) {
    const offset = baseOffset.clone().applyAxisAngle(new THREE.Vector3(0, 1, 0), yaw * Math.PI / 180);
    camera.clearViewOffset();
    camera.position.copy(centre).add(offset);
    camera.lookAt(centre);
    camera.updateProjectionMatrix();
    camera.updateMatrixWorld(true);
    scene.updateMatrixWorld(true);
    return {position: camera.position.toArray(), target: centre.toArray(), projection: camera.projectionMatrix.toArray()};
  }
  function objectRegion(width, height) {
    const box = new THREE.Box3().setFromObject(selected), corners = [];
    for (const x of [box.min.x, box.max.x]) for (const y of [box.min.y, box.max.y])
      for (const z of [box.min.z, box.max.z]) corners.push(new THREE.Vector3(x, y, z).project(camera));
    return {
      x0: Math.max(1, Math.floor(Math.min(...corners.map(p => (p.x + 1) * width / 2)))),
      x1: Math.min(width - 2, Math.ceil(Math.max(...corners.map(p => (p.x + 1) * width / 2)))),
      y0: Math.max(1, Math.floor(Math.min(...corners.map(p => (p.y + 1) * height / 2)))),
      y1: Math.min(height - 2, Math.ceil(Math.max(...corners.map(p => (p.y + 1) * height / 2)))),
    };
  }
  function errors(actual, reference, region) {
    let squared = 0, absolute = 0, channels = 0, edgeSquared = 0, edgeChannels = 0;
    let foregroundSquared = 0, foregroundAbsolute = 0, foregroundChannels = 0;
    const background = reference.pixels.slice(0, 3);
    const width = reference.width;
    for (let y = region.y0; y <= region.y1; y++) for (let x = region.x0; x <= region.x1; x++) {
      const at = (y * width + x) * 4;
      let gradient = 0;
      for (let c = 0; c < 3; c++) gradient += Math.abs(reference.pixels[at + c + 4] - reference.pixels[at + c - 4]) +
        Math.abs(reference.pixels[at + c + width * 4] - reference.pixels[at + c - width * 4]);
      const edge = gradient / 6 > 12; // Fixed before measuring; never tuned to the result.
      const foreground = [0, 1, 2].some(c => Math.abs(reference.pixels[at + c] - background[c]) > 3);
      for (let c = 0; c < 3; c++) {
        const difference = actual.pixels[at + c] - reference.pixels[at + c];
        squared += difference * difference; absolute += Math.abs(difference); channels++;
        if (edge) { edgeSquared += difference * difference; edgeChannels++; }
        if (foreground) { foregroundSquared += difference * difference; foregroundAbsolute += Math.abs(difference); foregroundChannels++; }
      }
    }
    return {rmse: Math.sqrt(squared / channels), mae: absolute / channels,
      edgeRmse: Math.sqrt(edgeSquared / Math.max(1, edgeChannels)), channels, edgeChannels,
      foregroundRmse: Math.sqrt(foregroundSquared / Math.max(1, foregroundChannels)),
      foregroundMae: foregroundAbsolute / Math.max(1, foregroundChannels), foregroundChannels};
  }
  function targetAllocation(target) {
    const gl = renderer.getContext(), properties = renderer.properties.get(target);
    const previousBinding = gl.getParameter(gl.RENDERBUFFER_BINDING), buffers = [];
    const candidates = [...(properties.__webglColorRenderbuffer ?? []), properties.__webglDepthRenderbuffer, properties.__webglDepthbuffer].filter(Boolean);
    for (const buffer of new Set(candidates)) {
      gl.bindRenderbuffer(gl.RENDERBUFFER, buffer);
      const width = gl.getRenderbufferParameter(gl.RENDERBUFFER, gl.RENDERBUFFER_WIDTH);
      const height = gl.getRenderbufferParameter(gl.RENDERBUFFER, gl.RENDERBUFFER_HEIGHT);
      const samples = gl.getRenderbufferParameter(gl.RENDERBUFFER, gl.RENDERBUFFER_SAMPLES);
      const format = gl.getRenderbufferParameter(gl.RENDERBUFFER, gl.RENDERBUFFER_INTERNAL_FORMAT);
      const bytesPerPixel = format === gl.RGBA16F ? 8 : 4;
      buffers.push({width, height, samples, format, bytesPerPixel, bytes: width * height * Math.max(1, samples) * bytesPerPixel});
    }
    gl.bindRenderbuffer(gl.RENDERBUFFER, previousBinding);
    const textureBytes = target.width * target.height * (target.texture.type === THREE.HalfFloatType ? 8 : 4);
    return {width: target.width, height: target.height, type: target.texture.type,
      depthBuffer: target.depthBuffer, requestedSamples: target.samples, renderbuffers: buffers,
      textureBytes, allocationBytes: textureBytes + buffers.reduce((sum, buffer) => sum + buffer.bytes, 0)};
  }
  function targetProof() {
    const targets = new Set(), original = renderer.setRenderTarget.bind(renderer);
    renderer.setRenderTarget = function(target, ...rest) { if (target) targets.add(target); return original(target, ...rest); };
    renderer.info.reset(); sceneSubmissions = 0;
    try { pipeline.render({moving: true}); }
    finally { renderer.setRenderTarget = original; }
    const allocations = [...targets].map(targetAllocation), gl = renderer.getContext();
    const supportedSamples = format => [...gl.getInternalformatParameter(gl.RENDERBUFFER, format, gl.SAMPLES)];
    return {antialiasMode: pipeline.antialiasMode, pixelRatio: renderer.getPixelRatio(),
      size: drawingSize().toArray(), bufferBytes: pipeline.bufferBytes,
      actualBufferBytes: allocations.reduce((sum, target) => sum + target.allocationBytes, 0),
      rgba16fSupportedSamples: supportedSamples(gl.RGBA16F), rgba8SupportedSamples: supportedSamples(gl.RGBA8),
      depth24SupportedSamples: supportedSamples(gl.DEPTH_COMPONENT24),
      sceneSubmissions, triangles: renderer.info.render.triangles,
      targetCount: targets.size, targets: allocations,
      sampleLevel: pipeline.scenePass.sampleLevel, hasHistory: Boolean(pipeline.temporalPass.history),
      hasComposer: Boolean(pipeline.composer), contextLost: renderer.getContext().isContextLost()};
  }
  window.measurePose = yaw => {
    const cameraPose = pose(yaw);
    filter(0);
    renderer.info.reset(); sceneSubmissions = 0;
    renderer.setRenderTarget(null); renderer.render(scene, camera);
    const before = capture(), oldDraw = {sceneSubmissions, triangles: renderer.info.render.triangles};
    filter(1);
    const resources = targetProof(), after = capture();
    filter(0); // Reference retains original surface detail; it is not preblurred to favour the new filter.
    const referencePass = new ProgressiveStill(scene, camera), outputPass = new OutputPass();
    const size = drawingSize(); referencePass.setSize(size.x, size.y);
    renderer.info.reset(); sceneSubmissions = 0;
    let reference;
    try {
      for (let sample = 0; sample < 4; sample++) referencePass.accumulate(renderer);
      outputPass.renderToScreen = true;
      outputPass.render(renderer, null, referencePass.accumulation);
      reference = capture();
    } finally { referencePass.dispose(); outputPass.dispose(); }
    const referenceSceneSubmissions = sceneSubmissions;
    filter(1);
    const region = objectRegion(size.x, size.y);
    return {yaw, cameraPose, region, oldDraw, resources, referenceSceneSubmissions,
      before: errors(before, reference, region), after: errors(after, reference, region),
      backgroundColour: {before: [...before.pixels.slice(0, 3)], after: [...after.pixels.slice(0, 3)], reference: [...reference.pixels.slice(0, 3)]},
      images: {before: before.png, after: after.png, reference: reference.png}};
  };
  window.checkColour = () => {
    const colourScene = new THREE.Scene(), colourCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, .1, 10);
    colourCamera.position.z = 1;
    const material = new THREE.MeshBasicMaterial({toneMapped: true});
    const plane = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), material); colourScene.add(plane);
    const testPipeline = createRenderPipeline(renderer, colourScene, colourCamera); testPipeline.resize();
    const rows = [];
    try {
      for (const linearColour of [[.18, .18, .18], [4, 2, 1]]) {
        material.color.setRGB(...linearColour);
        renderer.setRenderTarget(null); renderer.render(colourScene, colourCamera); const direct = capture();
        testPipeline.render(); const processed = capture();
        const at = (Math.floor(direct.height / 2) * direct.width + Math.floor(direct.width / 2)) * 4;
        const before = [...direct.pixels.slice(at, at + 3)], after = [...processed.pixels.slice(at, at + 3)];
        rows.push({linearColour, direct: before, processed: after, maxChannelError: Math.max(...before.map((c, i) => Math.abs(c - after[i])))});
      }
    } finally { testPipeline.dispose(); plane.geometry.dispose(); material.dispose(); }
    pipeline.render(); return rows;
  };
  window.checkFallback = () => {
    const calibrationScene = new THREE.Scene();
    const calibrationCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, .1, 10);
    calibrationCamera.position.z = 1;
    const material = new THREE.MeshBasicMaterial({color: new THREE.Color(.18, .18, .18), toneMapped: true});
    const plane = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), material);
    calibrationScene.add(plane);
    renderer.setRenderTarget(null);
    renderer.render(calibrationScene, calibrationCamera);
    const direct = capture(), memoryBefore = {...renderer.info.memory};
    const originalHas = renderer.extensions.has;
    const missing = ['EXT_color_buffer_float', 'EXT_color_buffer_half_float'];
    let fallback;
    // Simulate only factory capability detection; restore the real extension
    // accessor before any render or disposal, including if construction fails.
    try {
      renderer.extensions.has = function(name) { return missing.includes(name) ? false : originalHas.call(this, name); };
      fallback = createRenderPipeline(renderer, calibrationScene, calibrationCamera);
    } finally { renderer.extensions.has = originalHas; }
    const targets = new Set(), originalSetTarget = renderer.setRenderTarget;
    let processed, proof;
    try {
      renderer.setRenderTarget = function(target, ...rest) {
        if (target) targets.add(target);
        return originalSetTarget.call(this, target, ...rest);
      };
      fallback.resize();
      renderer.info.reset();
      fallback.render({moving: true});
      processed = capture();
      const at = (Math.floor(direct.height / 2) * direct.width + Math.floor(direct.width / 2)) * 4;
      const directPixel = [...direct.pixels.slice(at, at + 3)];
      const fallbackPixel = [...processed.pixels.slice(at, at + 3)];
      proof = {antialiasMode: fallback.antialiasMode, bufferBytes: fallback.bufferBytes,
        targetCount: targets.size, hasHistory: Boolean(fallback.temporalPass.history),
        hasComposer: Boolean(fallback.composer), needsSettle: fallback.needsSettle,
        forcedMissingExtensions: missing, capabilityInterceptionLimitedToFactory: true,
        extensionAccessorRestored: renderer.extensions.has === originalHas,
        directPixel, fallbackPixel, maxChannelError: Math.max(...directPixel.map((value, i) => Math.abs(value - fallbackPixel[i]))),
        drawCalls: renderer.info.render.calls, contextLost: renderer.getContext().isContextLost(), memoryBefore};
    } finally {
      renderer.setRenderTarget = originalSetTarget;
      fallback.dispose();
      plane.geometry.dispose();
      material.dispose();
    }
    proof.memoryAfterPipelineDisposeAndOwnedGeometryRelease = {...renderer.info.memory};
    proof.pipelineTextureDelta = proof.memoryAfterPipelineDisposeAndOwnedGeometryRelease.textures - memoryBefore.textures;
    pipeline.render();
    return {...proof, images: {direct: direct.png, fallback: processed.png}};
  };
  window.resourceProof = () => { viewer.resize(); return targetProof(); };
  window.measurementInfo = {building: building.code, originalAsset: building.detailedExterior,
    sourceModelSha256: catalogue.sourceModelSha256, filterUniformCount: shaderUniforms.size,
    budget: viewer.budget, userAgent: navigator.userAgent, maxTouchPoints: navigator.maxTouchPoints,
    nativeMaxTouchPoints: window.nativeMaxTouchPoints, maxTouchPointsOverride: 5,
    coarsePointer: matchMedia('(pointer:coarse)').matches, hardwareAntialias: renderer.getContext().getContextAttributes().antialias};
  window.ready = true;
}

const harness = `<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><style>html,body{margin:0;overflow:hidden}#stage{width:100vw;height:100vh}#labels{display:none}</style><div id="stage"></div><div id="labels"></div><script type="module">window.moduleBase=${JSON.stringify('/@fs' + process.cwd() + '/node_modules/')};(${installHarness.toString()})().catch(error=>{window.harnessError=String(error.stack || error);console.error(error);});</script>`;
const server = await createServer({server: {host: '127.0.0.1', port: 0}, logLevel: 'error', plugins: [{
  name: 'independent-mobile-antialias268', configureServer(server) {
    server.middlewares.use('/__mobile268', (_, response) => { response.setHeader('Content-Type', 'text/html'); response.end(harness); });
  },
}]});
let browser, context, page;
const report = {engine: 'WebKit', device: 'iPhone13 touch emulation with EdgiOS UA', sourceHashes,
  method: 'Four nearby fixed poses; each before/after image is compared only with its own four-jitter linear-HDR spatial reference before tone mapping. RGB errors are in8-bit display values within the projected original SAW bounds. This measures spatial aliasing over motion poses, not raw frame-to-frame camera displacement.',
  referenceSurfaceFilter: 0, oldSurfaceFilter: 0, newSurfaceFilter: 1,
  foregroundMask: 'Exclude reference pixels within3levels in every RGB channel of the top-left uniform background. Report full ROI, foreground and reference-edge errors separately; this is not semantic segmentation.',
  fixedYawDegrees: [-.06, -.02, .02, .06], browserErrors: [], shaderErrors: [], requests: [], poses: [],
  limits: ['Desktop WebKit touch emulation does not prove physical iPhone GPU/memory behaviour.',
    'Four spatial samples approximate a reference; they are not an unlimited-sample ground truth.',
    'Production buffers are measured separately from short-lived reference/calibration buffers.',
    'WebKit touch input is verified with pointerType=touch; navigator.maxTouchPoints is explicitly emulated as5and the native reported value is recorded.']};
try {
  await server.listen();
  const origin = 'http://127.0.0.1:' + server.httpServer.address().port;
  browser = await webkit.launch({headless: true});
  context = await browser.newContext({...devices['iPhone 13'], userAgent: devices['iPhone 13'].userAgent + ' EdgiOS/131.0'});
  page = await context.newPage();
  page.on('pageerror', error => report.browserErrors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') { report.shaderErrors.push(message.text()); console.error(message.text()); } });
  page.on('request', request => { const path = new URL(request.url()).pathname; if (path.includes('/models/')) report.requests.push(path); });
  await page.addInitScript(() => { window.nativeMaxTouchPoints = navigator.maxTouchPoints; Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 5}); window.touchEvents = []; document.addEventListener('pointerdown', event => window.touchEvents.push(event.pointerType)); });
  await page.goto(origin + '/__mobile268');
  await page.waitForFunction(() => window.ready || window.harnessError, null, {timeout: 120000});
  const harnessError = await page.evaluate(() => window.harnessError); if (harnessError) throw Error(harnessError);
  report.info = await page.evaluate(() => window.measurementInfo);
  await page.touchscreen.tap(15, 15);
  report.touchEvents = await page.evaluate(() => window.touchEvents);
  for (const [index, yaw] of report.fixedYawDegrees.entries()) {
    const row = await page.evaluate(yaw => window.measurePose(yaw), yaw);
    for (const [kind, data] of Object.entries(row.images)) await writeFile(`${OUTPUT}/pose-${index + 1}-${kind}.png`, Buffer.from(data.split(',')[1], 'base64'));
    delete row.images; report.poses.push(row);
    console.log(JSON.stringify({pose: index + 1, beforeRmse: row.before.rmse, afterRmse: row.after.rmse,
      beforeEdgeRmse: row.before.edgeRmse, afterEdgeRmse: row.after.edgeRmse, bufferMiB: row.resources.bufferBytes / 1048576}));
  }
  report.colour = await page.evaluate(() => window.checkColour());
  report.fallback = await page.evaluate(() => window.checkFallback());
  for (const [kind, data] of Object.entries(report.fallback.images)) await writeFile(OUTPUT + '/native-fallback-' + kind + '.png', Buffer.from(data.split(',')[1], 'base64'));
  delete report.fallback.images;
  await page.screenshot({path: OUTPUT + '/portrait.png'});
  await page.setViewportSize({width: 844, height: 390});
  report.landscape = await page.evaluate(() => window.resourceProof());
  await page.screenshot({path: OUTPUT + '/landscape.png'});
  await page.setViewportSize({width: 1366, height: 1024});
  report.tablet = await page.evaluate(() => window.resourceProof());
  assert(report.tablet.bufferBytes <= 24 * 1024 * 1024);
  assert(report.tablet.actualBufferBytes <= 24 * 1024 * 1024);
  assert.equal(report.tablet.sceneSubmissions, 1);
  assert.equal(report.tablet.contextLost, false);
  const average = field => report.poses.reduce((sum, row) => sum + row[field].rmse, 0) / report.poses.length;
  report.aggregate = {beforeRmse: average('before'), afterRmse: average('after')};
  report.aggregate.relativeRmseImprovement = 1 - report.aggregate.afterRmse / report.aggregate.beforeRmse;
  report.aggregate.beforeForegroundRmse = report.poses.reduce((sum, row) => sum + row.before.foregroundRmse, 0) / report.poses.length;
  report.aggregate.afterForegroundRmse = report.poses.reduce((sum, row) => sum + row.after.foregroundRmse, 0) / report.poses.length;
  report.aggregate.foregroundImprovement = 1 - report.aggregate.afterForegroundRmse / report.aggregate.beforeForegroundRmse;
  report.aggregate.beforeEdgeRmse = report.poses.reduce((sum, row) => sum + row.before.edgeRmse, 0) / report.poses.length;
  report.aggregate.afterEdgeRmse = report.poses.reduce((sum, row) => sum + row.after.edgeRmse, 0) / report.poses.length;
  report.improvementSupported = report.aggregate.afterRmse < report.aggregate.beforeRmse && report.poses.every(row => row.after.rmse <= row.before.rmse && row.after.foregroundRmse <= row.before.foregroundRmse && row.after.edgeRmse <= row.before.edgeRmse);
  assert(report.info.budget.mobile && report.info.coarsePointer && report.info.maxTouchPoints > 0);
  assert(report.touchEvents.includes('touch'));
  assert(report.requests.includes(report.info.originalAsset.url), 'Original detailed GLB must be requested');
  assert(report.info.filterUniformCount > 0, 'The comparison must exercise production surface-filter uniforms');
  for (const row of [...report.poses.map(p => p.resources), report.landscape]) {
    assert.equal(row.antialiasMode, 'mobile-fxaa'); assert.equal(row.targetCount, 2);
    assert.equal(row.sceneSubmissions, 1); assert.equal(row.hasHistory, false); assert.equal(row.hasComposer, false);
    assert.equal(row.sampleLevel, 0); assert(row.actualBufferBytes < 24 * 1048576, "Actual renderbuffer allocations exceed24MiB"); assert.equal(row.contextLost, false);
    assert(row.targets.some(t => t.depthBuffer && t.requestedSamples <= 2));
    assert(row.targets.some(t => !t.depthBuffer && t.type === 1009));
  }
  for (const row of report.poses) {
    assert.equal(row.oldDraw.sceneSubmissions, 1); assert.equal(row.referenceSceneSubmissions, 4);
    assert(row.resources.triangles <= row.oldDraw.triangles + 4, 'Moving geometry must be drawn once; only two fullscreen quads may be added');
  }
  assert(report.colour.every(row => row.maxChannelError <= 2), 'HDR tone mapping/sRGB must agree with direct constant-patch output');
  assert.equal(report.fallback.antialiasMode, 'native');
  assert.equal(report.fallback.bufferBytes, 0); assert.equal(report.fallback.targetCount, 0);
  assert.equal(report.fallback.hasHistory, false); assert.equal(report.fallback.hasComposer, false);
  assert.equal(report.fallback.needsSettle, false); assert.equal(report.fallback.extensionAccessorRestored, true);
  assert.equal(report.fallback.maxChannelError, 0); assert.equal(report.fallback.drawCalls, 1);
  assert.equal(report.fallback.pipelineTextureDelta, 0); assert.equal(report.fallback.contextLost, false);
  assert.equal(report.fallback.memoryAfterPipelineDisposeAndOwnedGeometryRelease.geometries, report.fallback.memoryBefore.geometries - 1);
  assert.deepEqual(report.browserErrors, []); assert.deepEqual(report.shaderErrors, []);
  for (const path of TRACKED_SOURCES) assert.equal(sha256(await readFile(path)), sourceHashes[path], 'Production source changed during measurement: ' + path);
  report.resourceAndColourChecksPassed = true;
  report.passed = report.improvementSupported;
  await writeFile(OUTPUT + '/measurement.json', JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({passed: report.passed, aggregate: report.aggregate, landscape: report.landscape, colour: report.colour, fallback: report.fallback}));
  if (!report.improvementSupported) process.exitCode = 1;
} catch (error) {
  report.passed = false; report.failure = error.stack;
  await writeFile(OUTPUT + '/measurement.json', JSON.stringify(report, null, 2) + '\n');
  console.error(error.stack); process.exitCode = 1;
} finally {
  await page?.evaluate(() => window.viewer?.dispose()).catch(() => {});
  await context?.close().catch(() => {});
  await browser?.close().catch(() => {});
  await server.close();
}
