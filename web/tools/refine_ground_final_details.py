"""Correct the photographed Australia fill on an owned globe candidate.
Run in Blender's Text Editor. Original political-map outlines, grid and labels
remain intact; this corrects one observed country fill, not a full map replica.
"""
from pathlib import Path
import array
import hashlib
import json
import subprocess
import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage116/ground'
OUT.mkdir(parents=True, exist_ok=True)
BASELINE = ROOT / 'result/blender/LSE_campus_detailed_v115.blend'
CANDIDATE = OUT / 'LSE_globe_color_candidate.blend'

# Reuse the original political geography; preserve every non-fill pixel.
# This is a generated cartographic texture, never a published photo texture.
PREPARE_TEXTURE = '''
from pathlib import Path
import json,hashlib
from PIL import Image,ImageDraw
import numpy as np
root=Path.cwd();out=root/'result/blender/stage116/ground'
source=out/'globe-map-original-packed.png'
image=Image.open(source).convert('RGB');width,height=image.size
features=json.loads((root/'data/collections/public-realm-2026/globe/countries.geojson').read_text())['features']
australia=next(f for f in features if f['properties'].get('NAME_EN')=='Australia')
mask=Image.new('L',image.size);draw=ImageDraw.Draw(mask)
def project(p):return ((p[0]+180)/360*width,(90-p[1])/180*height)
polygons=australia['geometry']['coordinates']
for polygon in polygons:
 draw.polygon([project(p) for p in polygon[0]],fill=255)
 for hole in polygon[1:]:draw.polygon([project(p) for p in hole],fill=0)
before=np.array(image);after=before.copy();inside=np.asarray(mask)>0
selected=inside & np.all(before==[159,188,152],axis=2)
after[selected]=[216,194,102]
assert selected.sum()>10000
assert np.array_equal(before[~selected],after[~selected])
Image.fromarray(after).save(out/'globe-map-australia-yellow.png',optimize=True)
(out/'texture-verification.json').write_text(json.dumps({'changedCountry':'Australia','sourcePoliticalGeometry':'Natural Earth 110m existing GeoJSON','sourceColor':[159,188,152],'photoEstimatedColor':[216,194,102],'changedPixels':int(selected.sum()),'outsideCountryUnchanged':bool(np.array_equal(before[~inside],after[~inside])),'nonFillPixelsUnchanged':True,'textureSize':[width,height],'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'candidateSha256':hashlib.sha256((out/'globe-map-australia-yellow.png').read_bytes()).hexdigest()},indent=2)+'\\n')
'''
bpy.ops.wm.open_mainfile(filepath=str(BASELINE))
original_globe = bpy.data.objects['SITE_V45_The_World_Turned_Upside_Down']
original_image = next(node.image for node in original_globe.data.materials[0].node_tree.nodes if node.type == 'TEX_IMAGE')
assert original_image.packed_file, 'The baseline must retain its authoritative packed map'
(OUT/'globe-map-original-packed.png').write_bytes(bytes(original_image.packed_file.data))
subprocess.run(['/opt/anaconda3/envs/MachineLearning/bin/python', '-c', PREPARE_TEXTURE], cwd=ROOT, check=True)
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()

def fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        coordinates = array.array('f', [0]) * (len(obj.data.vertices)*3)
        obj.data.vertices.foreach_get('co', coordinates)
        indices = array.array('i', [0]) * len(obj.data.loops)
        obj.data.loops.foreach_get('vertex_index', indices)
        digest.update(coordinates.tobytes())
        digest.update(indices.tobytes())
        digest.update(str([m.name if m else None for m in obj.data.materials]).encode())
    return digest.hexdigest()

before = {obj.name:fingerprint(obj) for obj in bpy.data.objects}
original = bpy.data.objects['SITE_V45_The_World_Turned_Upside_Down']
assert not original.hide_render
candidate = original.copy()
candidate.data = original.data.copy()
candidate.name = 'SITE_V116_Globe_photographed_Australia_fill'
bpy.data.collections['03_PUBLIC_REALM'].objects.link(candidate)
material = original.data.materials[0].copy()
material.name = 'SITE_V116_globe_cartography_Australia_yellow'
image = bpy.data.images.load(str(OUT/'globe-map-australia-yellow.png'),check_existing=False)
image.name = 'SITE_V116_globe_map_Australia_yellow'
image.pack()
image_node = next(node for node in material.node_tree.nodes if node.type == 'TEX_IMAGE')
image_node.image = image
material['globeMap'] = True
material['scope'] = 'Australia fill photo-corrected; other country colors remain unverified'
material['generatedTextureSha256'] = json.loads((OUT/'texture-verification.json').read_text())['candidateSha256']
candidate.data.materials.clear()
candidate.data.materials.append(material)
candidate['scope'] = 'Australia yellow fill from official2019/user reference; existing political outlines, other colors and heading retained'
assert candidate.parent is None
assert candidate.data != original.data and material != original.data.materials[0]
original.hide_render = True
original.hide_set(True)
for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()
changed = [name for name,value in before.items() if fingerprint(bpy.data.objects[name]) != value]
assert not changed, changed
bpy.ops.wm.save_as_mainfile(filepath=str(CANDIDATE))
audit = {
    'baseline':115,
    'candidate':str(CANDIDATE),
    'baselineSha256':hashlib.sha256(BASELINE.read_bytes()).hexdigest(),
    'originalFingerprints':before,
    'changedOriginalGeometry':changed,
    'addedObjects':[candidate.name],
    'archivedObjects':[original.name],
    'ownedMesh':candidate.data.name,
    'ownedMaterial':material.name,
    'ownedPackedImage':image.name,
    'sourceReferences':['data/collections/public-realm-2026/globe-lse-2019.webp','data/collections/public-realm-2026/user-references/reference-05.png'],
    'limitations':['Only Australia fill corrected; palette photo-estimated, not a material color measurement','Existing Natural Earth coastlines differ from sculpture UN cartography; not a full replica','Other country fills, exact labels, compass heading, current2026 condition remain unverified','No road, building or interior geometry changes'],
}
(OUT/'ground-final-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print('GROUND_FINAL_CANDIDATE_SAVED', candidate.name)
