/** Fixed, independent WebKit measurement. Run this file; production sources are read only. */
import assert from 'node:assert/strict';
import {mkdir, readFile, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {webkit, devices} from 'playwright';
import {createServer} from 'vite';

const OUTPUT = 'result/web/clarity272/budget';
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
    sourceModelSha256: catalogue.sourceModelSha256, 
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
const report={engine:'WebKit',device:'iPhone13 touch emulation with EdgiOS UA',sourceHashes,browserErrors:[],shaderErrors:[],limits:['Desktop touch emulation does not prove physical iPhone memory pressure.','Reported attachment bytes exclude browser-owned canvas and shadow allocations.']};
try {
  await server.listen();
  browser=await webkit.launch({headless:true});
  context=await browser.newContext({...devices['iPhone 13'],userAgent:devices['iPhone 13'].userAgent+' EdgiOS/131.0'});
  page=await context.newPage();
  page.on('pageerror',e=>report.browserErrors.push(e.message));
  page.on('console',m=>{if(m.type()==='error')report.shaderErrors.push(m.text());});
  await page.addInitScript(()=>{window.nativeMaxTouchPoints=navigator.maxTouchPoints;Object.defineProperty(navigator,'maxTouchPoints',{get:()=>5});});
  await page.goto('http://127.0.0.1:'+server.httpServer.address().port+'/__mobile268');
  await page.waitForFunction(()=>window.ready||window.harnessError,null,{timeout:120000});
  const error=await page.evaluate(()=>window.harnessError);if(error)throw Error(error);
  report.info=await page.evaluate(()=>window.measurementInfo);
  report.colour=await page.evaluate(()=>window.checkColour());
  report.fallback=await page.evaluate(()=>window.checkFallback());delete report.fallback.images;
  report.portrait=await page.evaluate(()=>window.resourceProof());
  await page.setViewportSize({width:844,height:390});report.landscape=await page.evaluate(()=>window.resourceProof());
  await page.setViewportSize({width:1366,height:1024});report.tablet=await page.evaluate(()=>window.resourceProof());
  for(const r of[report.portrait,report.landscape,report.tablet]){
    assert.equal(r.antialiasMode,'mobile-fxaa');assert.equal(r.sceneSubmissions,1);assert.equal(r.targetCount,2);
    assert.equal(r.hasHistory,false);assert.equal(r.hasComposer,false);assert.equal(r.contextLost,false);
    assert(r.actualBufferBytes<=24*1024*1024);
    const samples=r.rgba16fSupportedSamples.includes(2)&&r.depth24SupportedSamples.includes(2)?2:0;
    assert.equal(r.targets[0].requestedSamples,samples);assert.equal(r.targets[1].requestedSamples,0);
    for(const buffer of r.targets[0].renderbuffers)assert([0,samples].includes(buffer.samples));
    if(samples)assert(r.targets[0].renderbuffers.some(buffer=>buffer.samples===samples));
  }
  assert(report.portrait.size[0]>487&&report.portrait.size[1]>830);
  assert(report.colour.every(r=>r.maxChannelError<=2));assert.equal(report.fallback.maxChannelError,0);
  assert.equal(report.fallback.bufferBytes,0);assert.equal(report.fallback.targetCount,0);assert.equal(report.fallback.drawCalls,1);assert.equal(report.fallback.pipelineTextureDelta,0);
  assert.deepEqual(report.browserErrors,[]);assert.deepEqual(report.shaderErrors,[]);
  for(const path of TRACKED_SOURCES)assert.equal(sha256(await readFile(path)),sourceHashes[path]);
  report.method='Actual portrait,landscape and tablet GPU attachments,HDR colour and native fallback checks; no image-error measurement in this file.';
  report.passed=true;console.log(JSON.stringify({passed:true,portrait:report.portrait,landscape:report.landscape,tablet:report.tablet,colour:report.colour,fallback:report.fallback}));
}catch(error){report.passed=false;report.failure=error.stack;console.error(error.stack);process.exitCode=1;}
finally{await page?.evaluate(()=>window.viewer?.dispose()).catch(()=>{});await context?.close();await browser?.close();await server.close();await writeFile(OUTPUT+'/verification.json',JSON.stringify(report,null,2)+'\n');}
