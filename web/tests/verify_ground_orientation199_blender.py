"""Compare the diagnosed native park shading before and after orientation repair."""
from pathlib import Path
import sys,json,hashlib
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
import refine_landscape199 as review
OUT=ROOT/'result/blender/ground-orientation199'
report=json.loads((OUT/'audit.json').read_text())
baseline=ROOT/report['baseline'];assert hashlib.sha256(baseline.read_bytes()).hexdigest()==report['baselineSha256']
bpy.ops.wm.open_mainfile(filepath=str(baseline));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
review.OUT=OUT
review.preview('before-orientation',only={'whole'})
names=list(report['addedObjects'])
with bpy.data.libraries.load(str(ROOT/report['componentPath']),link=False)as(source,target):target.objects=list(names)
for obj in target.objects:
    original=bpy.data.objects[obj['originalObject']]
    for collection in original.users_collection:collection.objects.link(obj)
    original.hide_render=True;original.hide_set(True);obj.hide_render=False;obj.hide_set(False)
park=bpy.data.objects['GROUND199_GIS_green_way/30613392'];normal=park.matrix_world.inverted().transposed().to_3x3()
assert all((normal@face.normal).z>.999 for face in park.data.polygons)
review.preview('after-orientation',only={'whole'})
assert hashlib.sha256(baseline.read_bytes()).hexdigest()==report['baselineSha256']
(OUT/'park-verification.json').write_text(json.dumps(dict(nativeParkFacesUpward=True,parkFaces=len(park.data.polygons),before='before-orientation-whole.png',after='after-orientation-whole.png',baselineUnchanged=True),indent=2)+'\n')
print('GROUND199_PARK_VERIFIED',len(park.data.polygons),flush=True)
