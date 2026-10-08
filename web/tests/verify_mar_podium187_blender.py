"""Verify saved MAR facade, unchanged source geometry and photo-registered opening."""
from pathlib import Path
import bpy,json,hashlib,sys
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'web/tools'))
from refine_mar_exterior174 import world,N
from refine_mar_podium187 import NAMES,apply_mar_podium187
from refine_rooms import geometry_signatures
from refine_architectural_glass import shape_signature
from refine_old_lettering185 import font_signature
out=ROOT/'result/blender/stage187';proof=json.loads((out/'building-refinement.json').read_text())
model=ROOT/'result/blender/LSE_campus_detailed_v187.blend'
assert hashlib.sha256(model.read_bytes()).hexdigest()==proof['sourceModelSha256']
bpy.ops.wm.open_mainfile(filepath=str(model));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
for scene in bpy.data.scenes:
 for layer in scene.view_layers:layer.update()
assert geometry_signatures()==proof['geometrySignatures']
assert all(shape_signature(bpy.data.objects[n])==h for n,h in proof['originalShapesAndUVs'].items())
assert all(font_signature(bpy.data.objects[n])==h for n,h in proof['originalFonts'].items())
assert apply_mar_podium187()['alreadyApplied']
visible=set()
def walk(collection):
 if collection.hide_render:return
 visible.update(o for o in collection.objects if not o.hide_render)
 for child in collection.children:walk(child)
walk(bpy.context.scene.collection)
trees=[]
for o in visible:
 if o.type=='MESH' and o.name.startswith('MAR') and len(o.data.polygons):
  trees.append((o.name,BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(f.vertices)for f in o.data.polygons])))
def first(x,z):
 hits=[]
 for name,tree in trees:
  p,n,face,d=tree.ray_cast(world(x,23,z),-N,30)
  if p is not None:hits.append((d,name))
 return min(hits)if hits else None
checks=[]
for x in [-13.3,-12.2,-11.1]:
 for z in [6.6,8.4,9.8,11.5]:
  hit=first(x,z);assert hit[1]==NAMES[1],(x,z,hit);checks.append({'x':x,'z':z,'firstHit':hit})
for x,z in [(-14.4,8),(-9,8),(-12.2,5.2),(-12.2,12.5)]:assert first(x,z)[1]==NAMES[0]
assert first(-12.2,9.1)[1]==NAMES[2]
for x in [19.5,-25.9]:
 for z in [7.3,10.8]:assert first(x,z)[1]=='MAR174_retained_loggia_12'
for z in [7.3,10.8]:assert first(6.6,z) is None,'Open loggia obstructed'
(out/'podium-verification.json').write_text(json.dumps({'savedSourceVerified':True,'allOriginalShapesAndUVsPreserved':True,'allOriginalFontsPreserved':True,'newPaneSightlines':checks,'surroundChecks':4,'retainedWindowChecks':4,'openLoggiaChecks':2},indent=2))
print('MAR187_VERIFIED',len(checks))
