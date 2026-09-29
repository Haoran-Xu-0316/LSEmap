"""Read-only native level inventory for the LRB datum correction."""
from pathlib import Path
import json
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v36.blend'))
records=[]
for o in bpy.data.collections['LRB_PUBLIC_INTERIOR_study'].all_objects:
 if o.type not in {'MESH','CAMERA'}:continue
 points=[o.matrix_world@Vector(v) for v in o.bound_box] if o.type=='MESH' else [o.matrix_world.translation]
 records.append({'name':o.name,'type':o.type,'minZ':min(p.z for p in points),'maxZ':max(p.z for p in points),'parent':o.parent.name if o.parent else None,'floorId':o.get('floorId'),'roomSample':o.get('roomSample')})
(ROOT/'result/blender/stage37/level-inventory.json').write_text(json.dumps(records,indent=2)+'\n')
print('LRB_LEVEL_INVENTORY',len(records))
