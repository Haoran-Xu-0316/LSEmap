/** Serve the unchanged campus GLB from bounded static asset segments. */
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname !== '/models/campus.glb') return env.ASSETS.fetch(request);
    if (!['GET', 'HEAD'].includes(request.method)) return new Response(null, {status:405});
    const manifestUrl = new URL('/models/campus-parts.json', url);
    const manifestResponse = await env.ASSETS.fetch(new Request(manifestUrl));
    if (!manifestResponse.ok) return new Response('Campus model unavailable', {status:503});
    const manifest = await manifestResponse.json();
    const headers = {
      'Content-Type':'model/gltf-binary',
      'Content-Length':String(manifest.bytes),
      'Cache-Control':'public, max-age=3600, must-revalidate',
      'ETag':`"${manifest.sha256}"`,
      'X-Content-Type-Options':'nosniff',
    };
    if (request.headers.get('If-None-Match') === headers.ETag) return new Response(null, {status:304, headers});
    if (request.method === 'HEAD') return new Response(null, {headers});
    const responses = await Promise.all(manifest.parts.map(part => env.ASSETS.fetch(new Request(new URL(part.path,url)))));
    if (responses.some(response => !response.ok || !response.body)) return new Response('Campus segment unavailable', {status:503});
    let index=0, reader=null;
    const body = new ReadableStream({
      async pull(controller) {
        try {
          while(index<responses.length){
            reader ??= responses[index].body.getReader();
            const {done,value}=await reader.read();
            if(!done){controller.enqueue(value);return;}
            reader.releaseLock();reader=null;index++;
          }
          controller.close();
        } catch(error) {controller.error(error);}
      },
      async cancel(reason) {
        if(reader) await reader.cancel(reason);
        for(let i=index+(reader?1:0);i<responses.length;i++)await responses[i].body.cancel(reason);
      },
    });
    return new Response(body,{headers});
  },
};
