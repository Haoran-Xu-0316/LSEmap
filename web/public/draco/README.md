# Self-hosted Draco decoder

The glTF WebAssembly decoder and JavaScript wrapper are copied from Three.js 0.186.0
`examples/jsm/libs/draco/gltf`. Both files are served locally; no external decoder
CDN is required. The project uses the WASM decoder rather than the legacy pure-JS
fallback. Unsupported browsers retain access to the rendered image gallery.

Draco: [Apache License 2.0](LICENSE.txt).
Three.js: [MIT License](THREE-LICENSE.txt).
Upstream: https://github.com/google/draco
