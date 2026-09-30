/** Deploy only verified release assets from an isolated temporary directory.
 * Duplicate files appearing in the desktop build folder cannot enter the upload.
 */
import {readFile,mkdtemp,mkdir,copyFile,rm} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {join,dirname} from 'node:path';
import {tmpdir} from 'node:os';
import {spawnSync} from 'node:child_process';
const release=JSON.parse(await readFile('dist/release.json','utf8'));
const staging=await mkdtemp(join(tmpdir(),'lsemap-release-'));
try {
  for(const [path,record] of Object.entries(release.assets)) {
    if(!path.startsWith('/')||path.includes('..'))throw Error(`Invalid release path: ${path}`);
    const source=join('dist',path.slice(1));
    const bytes=await readFile(source);
    if(bytes.length!==record.bytes||createHash('sha256').update(bytes).digest('hex')!==record.sha256)
      throw Error(`Release asset changed: ${path}`);
    const target=join(staging,path.slice(1));
    await mkdir(dirname(target),{recursive:true});
    await copyFile(source,target);
  }
  await copyFile('dist/release.json',join(staging,'release.json'));
  console.log(`Deploying verified edition ${release.version}: ${Object.keys(release.assets).length+1} files`);
  const result=spawnSync('npx',['wrangler','deploy','--assets',staging],{stdio:'inherit'});
  if(result.error)throw result.error;
  if(result.status!==0)throw Error(`Deployment failed with status ${result.status}`);
} finally {
  await rm(staging,{recursive:true,force:true});
}
