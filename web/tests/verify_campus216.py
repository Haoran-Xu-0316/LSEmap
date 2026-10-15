"""Verify saved216 source preservation and actual surface support in Blender."""
from pathlib import Path
import hashlib
import json
import sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from integrate_exterior_round194 import object_fingerprint, update_scene
from refine_portsmouth_exterior207 import material_fingerprint
OUT = ROOT / 'result/blender/stage216'
BASE = ROOT / 'result/blender/LSE_campus_detailed_v215.blend'
FINAL = ROOT / 'result/blender/LSE_campus_detailed_v216.blend'
BASE_SHA = 'b6c726056d7e98dc229e1ac2dc1d01e7be35eb1835a28cd7a6bb88155a9c1a11'
material_state=OUT/'source-material-state.json'
if BASE.exists():
 assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE))
 original_materials={material.name:material_fingerprint(material) for material in bpy.data.materials}
 material_state.write_text(json.dumps(dict(baselineSha256=BASE_SHA,materials=original_materials),indent=2)+'\n')
else:
 stored=json.loads(material_state.read_text());assert stored['baselineSha256']==BASE_SHA
 original_materials=stored['materials']
assert len(original_materials)==1958
record = json.loads((OUT / 'building-refinement.json').read_text())
assert hashlib.sha256(FINAL.read_bytes()).hexdigest() == record['sourceModelSha256']
bpy.ops.wm.open_mainfile(filepath=str(FINAL)); update_scene()
assert all(material_fingerprint(bpy.data.materials[name]) == digest for name, digest in original_materials.items())
baseline = json.loads((OUT / 'baseline-state.json').read_text())
previous=json.loads((ROOT/'result/blender/stage215/building-refinement.json').read_text())
assert previous['sourceModelSha256']==BASE_SHA
expected=json.loads((ROOT/'result/blender/stage215/baseline-state.json').read_text())['fingerprints']
expected.update(previous['addedFingerprints'])
assert baseline['fingerprints']==expected, 'The new baseline must match the previous accepted geometry'
assert all(object_fingerprint(bpy.data.objects[name]) == digest for name, digest in baseline['fingerprints'].items())
site = [obj for obj in bpy.data.collections['00_SITE'].all_objects if obj.type == 'MESH' and not obj.hide_render]
trees = []
for obj in site:
 points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
 trees.append((obj.name, BVHTree.FromPolygons(points, [tuple(face.vertices) for face in obj.data.polygons])))
def surface(x, y, z):
 hits=[]
 for name, tree in trees:
  point, normal, index, distance = tree.ray_cast(Vector((x,y,z)), Vector((0,0,-1)), 2)
  if point is not None: hits.append((distance,name,list(point)))
 return min(hits) if hits else None
samples=[]
for name,x,y,z,expected_height,expected_object in [
 ('tunnel_exclusive',-59.4476302605,-168.539049565,.1,-.05,'SITE216_Expanded_flat_map_datum'),
 ('surface_footway',-146.33,-347.5,.1,.024,'SITE215_mapped_footway_body'),
 ('footway_support',-146.33,-347.5,0,-.05,'SITE216_Expanded_flat_map_datum'),
]:
 hit=surface(x,y,z);assert hit is not None,name
 assert abs(hit[2][2]-expected_height)<.0001,(name,hit)
 assert hit[1] == expected_object,(name,hit)
 samples.append(dict(name=name,object=hit[1],height=hit[2][2],xy=[x,y]))
datum = json.loads((ROOT / 'result/blender/context-datum216/audit.json').read_text())
for name in ['SITE215_mapped_footway_body','SITE215_mapped_footway_edge']:
 for vertex in bpy.data.objects[name].data.vertices:
  point=bpy.data.objects[name].matrix_world@vertex.co
  assert all(datum['newBounds']['min'][i]<=point[i]<=datum['newBounds']['max'][i] for i in range(2))
result=dict(sourceModelSha256=record['sourceModelSha256'],baselineSha256=BASE_SHA,originalObjectFingerprintsVerified=len(baseline['fingerprints']),originalMaterialNodesVerified=len(original_materials),groundSamples=samples,allMappedFootwaysSupported=True,completeModelReopened=True)
(OUT / 'native-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print('CAMPUS216_NATIVE',result,flush=True)
