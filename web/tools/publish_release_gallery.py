"""Publish validated native render outputs into the web gallery.
Run with the existing project Python environment after render_release_gallery.py.
"""
from pathlib import Path
import hashlib
import json
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
RELEASE=ROOT/'result/web/release16'
records=json.loads((RELEASE/'gallery-manifest.json').read_text())
plan=json.loads((RELEASE/'gallery-plan.json').read_text())
expected={r['name'] for r in plan}|{'campus'}
assert {r['name'] for r in records}==expected,'Gallery rendering is incomplete'
catalogue=json.loads((ROOT/'web/public/models/catalogue.json').read_text())
output=[]
for record in records:
 assert record['sourceModelSha256']==catalogue['sourceModelSha256']
 source=RELEASE/'renders'/(record['name']+'.png')
 target=ROOT/'web/public/images'/(record['name']+'.webp')
 with Image.open(source) as image:
  assert image.width>=1000 and image.height>=800
  image.convert('RGB').save(target,quality=92,method=6)
 data=target.read_bytes()
 output.append({**record,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
(ROOT/'web/public/gallery-manifest.json').write_text(json.dumps({'version':'16','sourceModelSha256':catalogue['sourceModelSha256'],'images':output},indent=2)+'\n')
print('Published',len(output),'edition-16 gallery images')
