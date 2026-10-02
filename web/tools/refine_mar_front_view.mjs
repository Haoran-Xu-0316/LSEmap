/** Present MAR's north elevation at a photo-comparable height.
 * Geometry and all model bytes remain unchanged. No command-line options.
 */
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const path='web/public/models/catalogue.json';
const directory='result/blender/stage105';
await mkdir(directory,{recursive:true});
const sourceText=await readFile(path,'utf8');
const catalogue=JSON.parse(sourceText);
if(catalogue.version==='105'){
 const audit=JSON.parse(await readFile(`${directory}/mar-front-view-audit.json`));
 const mar=catalogue.buildings.find(b=>b.code==='MAR');
 if(JSON.stringify(mar.exteriorDirection)!==JSON.stringify(audit.direction))throw Error('Existing edition 105 differs from the authored view');
 console.log('MAR_FRONT_VIEW_ALREADY_SAVED');
}else{
 if(catalogue.version!=='104')throw Error('Expected verified edition 104');
 await writeFile(`${directory}/catalogue-before.json`,JSON.stringify(catalogue,null,2)+'\n');
 const models=[];
 for(const building of catalogue.buildings){
  for(const key of ['detailedExterior','detailedInterior'])if(building[key])models.push(building[key].url);
  for(const space of building.interiorSpaces??[])if(space.detailedInterior)models.push(space.detailedInterior.url);
 }
 const release=JSON.parse(await readFile('dist/release.json'));
 if(release.version!=='104')throw Error('Expected verified edition 104 release');
 for(const url of Object.keys(release.assets))if(url.startsWith('/models/')&&url.endsWith('.glb'))models.push(url);
 const hashes={};
 for(const url of new Set(['/models/campus.glb',...models]))hashes[url]=createHash('sha256').update(await readFile('web/public'+url)).digest('hex');
 for(const [url,hash] of Object.entries(hashes))if(hash!==release.assets[url]?.sha256)throw Error('Baseline model differs: '+url);
 const direction=[-.37460657954216003,.02,-.9271838665008545];
 const length=Math.hypot(...direction);
 const normalized=direction.map(value=>value/length);
 const mar=catalogue.buildings.find(b=>b.code==='MAR');
 mar.exteriorDirection=normalized;catalogue.version='105';
 const rendered=sourceText.replace('"version": "104"','"version": "105"').replace(/("code": "MAR"[\s\S]*?"exteriorDirection": )\[[^\]]*\]/,(_,prefix)=>prefix+JSON.stringify(normalized,null,2).replace(/\n/g,'\n      '));
 if(JSON.stringify(JSON.parse(rendered))!==JSON.stringify(catalogue))throw Error('Unexpected catalogue formatting result');
 await writeFile(path,rendered);
 await writeFile(`${directory}/mar-front-view-audit.json`,JSON.stringify({version:105,baseline:104,direction:normalized,modelHashes:hashes,
  nativeSourceUnchanged:catalogue.sourceModelSha256,reference:'Nick Kane north-elevation photographs 02 and 03; capture date unknown',
  scope:'Lower default facade viewing angle only. Model vertices, materials, asset URLs, interiors and free orbit controls unchanged.',
  limits:['Camera is a presentation estimate, not a recovered photographic camera','Roof, hidden elevations and full interiors still require fidelity review']},null,2)+'\n');
 console.log('MAR_FRONT_VIEW_SAVED',normalized, Object.keys(hashes).length,'retained model assets');
}
