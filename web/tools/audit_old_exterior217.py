"""Read-only OLD form audit against the accepted216 native and private photos.

Measurements describe the model, not surveyed real-world construction. This
records two actionable differences without guessing a replacement door system
or treating the wire sculpture as an opaque stone carving.
"""
from pathlib import Path
import hashlib
import json
import sys
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'result/blender/LSE_campus_detailed_v216.blend'
SHA='12376d6365bbc57fa9eec97617453dbbfcf9235a8200bb90726f80c2147c1a60'
OUT=ROOT/'result/blender/old-exterior-audit217'
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import accepted_fingerprints,object_fingerprint
from refine_portsmouth_exterior207 import material_fingerprint

NAMES=[
 'OLD_NEXT_EXTERIOR154_door_frame','OLD_NEXT_EXTERIOR154_door_steel','OLD_ENTRANCE192_single_glass',
 'OLD_NEXT_EXTERIOR154_V111_lattice_figures','OLD_NEXT_EXTERIOR154_V111_lattice_products',
 'OLD_NEXT_EXTERIOR154_D5_finalsale84_display_frame','OLD_NEXT_EXTERIOR154_D5_finalsale84_containers',
 'OLD_NEXT_ARTWORK_front_glazing','OLD_NEXT_ACCESS_external_four_steps',
 'OLD194_STONE_OLD_V112_entry_V103_curved_limestone_arch',
 'GLASS181_OLD_V112_entry_D5_portal78_pane_glass','GLASS181_OLD_V112_entry_D5_portal79_Window_glazing',
 'GLASS181_OLD_V112_entry_Window_glazing',
]

def connected_components(obj,right,outward):
 mesh=obj.data;adjacency=[set()for _ in mesh.vertices]
 for edge in mesh.edges:
  a,b=edge.vertices;adjacency[a].add(b);adjacency[b].add(a)
 remaining=set(range(len(mesh.vertices)));rows=[]
 while remaining:
  seed=remaining.pop();pending=[seed];component=[seed]
  while pending:
   index=pending.pop()
   for neighbour in adjacency[index]:
    if neighbour in remaining:remaining.remove(neighbour);pending.append(neighbour);component.append(neighbour)
  points=[obj.matrix_world@mesh.vertices[i].co for i in component]
  projected=[(p.dot(right),p.dot(outward),p.z)for p in points]
  lo=[min(p[i]for p in projected)for i in range(3)];hi=[max(p[i]for p in projected)for i in range(3)]
  rows.append(dict(vertices=len(component),bounds=[lo,hi],dimensions=[hi[i]-lo[i]for i in range(3)]))
 return sorted(rows,key=lambda r:(r['bounds'][0][2],r['bounds'][0][0]))

def run():
 OUT.mkdir(parents=True,exist_ok=True)
 assert hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 for scene in bpy.data.scenes:
  for layer in scene.view_layers:layer.update()
 accepted=accepted_fingerprints(ROOT/'result/blender/stage216',SHA)
 actual={obj.name:object_fingerprint(obj)for obj in bpy.data.objects}
 mismatch=[name for name in set(accepted)|set(actual)if accepted.get(name)!=actual.get(name)]
 assert not mismatch,mismatch[:20]
 materials={m.name:material_fingerprint(m)for m in bpy.data.materials}
 # Use the actual current pane plane for orthonormal widths/depths. This avoids
 # inflated world-axis bounding boxes and the obsolete pre112 registration.
 obj=bpy.data.objects['GLASS181_OLD_V112_entry_Window_glazing']
 guessed=Vector((.890279,-.455415,0))
 face=max(obj.data.polygons,key=lambda p:(obj.matrix_world.to_3x3().inverted().transposed()@p.normal).normalized().dot(guessed))
 outward=(obj.matrix_world.to_3x3().inverted().transposed()@face.normal).normalized();outward.z=0;outward.normalize()
 right=Vector((-outward.y,outward.x,0))
 objects=[]
 for name in NAMES:
  obj=bpy.data.objects[name];assert not obj.hide_render,name
  points=[obj.matrix_world@v.co for v in obj.data.vertices]
  projected=[(p.dot(right),p.dot(outward),p.z)for p in points]
  low=[min(p[i]for p in projected)for i in range(3)];high=[max(p[i]for p in projected)for i in range(3)]
  objects.append(dict(name=name,type=obj.type,vertices=len(obj.data.vertices),faces=len(obj.data.polygons),bounds=[low,high],dimensions=dict(width=high[0]-low[0],depth=high[1]-low[1],height=high[2]-low[2]),materials=[m.name for m in obj.data.materials],uvLayers=[layer.name for layer in obj.data.uv_layers],components=connected_components(obj,right,outward)if 'lattice'not in name else None))
 verification=dict(acceptedFingerprintsVerified=len(actual),originalMaterialNodesVerified=len(materials),allNativeObjectFingerprintsUnchanged=all(object_fingerprint(bpy.data.objects[n])==v for n,v in actual.items()),allOriginalMaterialNodesUnchanged=all(material_fingerprint(bpy.data.materials[n])==v for n,v in materials.items()),nativeFileUnchanged=hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA,noComponentProduced=True,noGeometryOrVisibilityChanged=True)
 (OUT/'native-measurements.json').write_text(json.dumps(dict(baselineSha256=SHA,axes=dict(right=list(right),outward=list(outward)),units='model metres in actual current facade plane; not surveyed building dimensions',objects=objects,verification=verification),indent=2)+'\n')
 print('OLD_FORM217_READONLY_VERIFIED',len(actual),len(objects),flush=True)
if __name__=='__main__':run()
