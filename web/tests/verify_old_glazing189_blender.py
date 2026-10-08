"""Verify the saved complete campus against its accepted188 baseline."""
from pathlib import Path
import hashlib,json,sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from refine_architectural_glass import shape_signature
from refine_old_lettering185 import font_signature
from refine_rooms import geometry_signatures
from refine_old_artwork_glazing import SOURCE,TARGET,ARTWORK,apply_old_artwork_glazing
from refine_building_details import BASE,TARGET as MODEL,REPORT
proof=json.loads((REPORT/'building-refinement.json').read_text())
assert hashlib.sha256(BASE.read_bytes()).hexdigest()==proof['baselineSha256']
assert hashlib.sha256(MODEL.read_bytes()).hexdigest()==proof['sourceModelSha256']
bpy.ops.wm.open_mainfile(filepath=str(BASE))
for scene in bpy.data.scenes:
 for layer in scene.view_layers:layer.update()
original=geometry_signatures()
shapes={o.name:shape_signature(o) for o in bpy.data.objects if o.type=='MESH'}
fonts={o.name:font_signature(o) for o in bpy.data.objects if o.type=='FONT'}
visibility={o.name:o.hide_render for o in bpy.data.objects}
collections={c.name:sorted(o.name for o in c.objects) for c in bpy.data.collections}
bpy.ops.wm.open_mainfile(filepath=str(MODEL))
for scene in bpy.data.scenes:
 for layer in scene.view_layers:layer.update()
after=geometry_signatures()
assert after==proof['geometrySignatures']
assert all(after[name]==value for name,value in original.items())
assert all(shape_signature(bpy.data.objects[name])==value for name,value in shapes.items())
assert all(font_signature(bpy.data.objects[name])==value for name,value in fonts.items())
assert all(bpy.data.objects[name].hide_render==value for name,value in visibility.items() if name!=SOURCE)
assert bpy.data.objects[SOURCE].hide_render
for name,objects in collections.items():
 assert sorted(o.name for o in bpy.data.collections[name].objects if o.name!=TARGET)==objects
assert set(bpy.data.objects)-set(bpy.data.objects[name] for name in visibility)=={bpy.data.objects[TARGET]}
assert TARGET in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects
assert apply_old_artwork_glazing()['alreadyApplied']
pane=bpy.data.objects[TARGET];source=bpy.data.objects[SOURCE]
assert len(pane.data.polygons)==1
assert [tuple(v.co) for v in pane.data.vertices]==[tuple(v.co) for v in source.data.vertices]
assert pane.data.materials[0]!=source.data.materials[0]
assert abs(pane.data.materials[0]['webOpacity']-.22)<1e-6
normal=Vector(proof['changes'][0]['normal'])
tree=BVHTree.FromPolygons([pane.matrix_world@v.co for v in pane.data.vertices],[tuple(p.vertices) for p in pane.data.polygons])
checks=0;minimum=100
for name in ARTWORK:
 obj=bpy.data.objects[name];matrix=obj.matrix_world.copy()
 for vertex in list(obj.data.vertices)[::50]:
  hit=tree.ray_cast(matrix@vertex.co,normal,2)
  assert hit[2] is not None and hit[3]>=.0349
  minimum=min(minimum,hit[3]);checks+=1
assert not bpy.data.libraries
assert not any(i.source=='FILE' and not i.packed_file for i in bpy.data.images)
result=dict(version=189,sourceModelSha256=proof['sourceModelSha256'],savedSceneReopened=True,
 baselineGeometryUVFontsAndBindingsPreserved=True,unrelatedVisibilityAndCollectionsPreserved=True,
 idempotent=True,singleProtectivePane=True,protectedArtworkSamples=checks,
 minimumSampleClearance=minimum,externalDependencies=False)
(REPORT/'reopened-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print('OLD189_FULL_MODEL_VERIFIED',checks,flush=True)
