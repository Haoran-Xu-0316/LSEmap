import {test,expect} from '@playwright/test';
import {readFile,stat} from 'node:fs/promises';

test('GitHub checkout includes every required default interior and excludes oversized direct upload',async()=>{
 const catalogue=JSON.parse(await readFile('web/public/models/catalogue.json','utf8'));
 for(const building of catalogue.buildings.filter(b=>b.interior)){
  const path=`web/public/models/${building.code.toLowerCase()}-interior.glb`;
  const bytes=await readFile(path);
  expect(bytes.toString('ascii',0,4),path).toBe('glTF');
  expect(bytes.length,path).toBeLessThan(25*1024*1024);
 }
 const ignore=await readFile('dist/.assetsignore','utf8');
 expect(ignore.split(/\r?\n/)).toContain('/models/campus.glb');
 const release=JSON.parse(await readFile('dist/release.json','utf8'));
 expect(release.assets['/models/campus.glb']).toBeUndefined();
 for(const part of release.campusTransport.parts)expect((await stat('dist'+part.path)).size).toBe(part.bytes);
});
