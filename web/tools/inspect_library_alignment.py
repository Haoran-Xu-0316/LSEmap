"""Inventory geometry affected by plan registration, without editing the model."""
from pathlib import Path
import bpy,json,math
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v37.blend'))
for scene in bpy.data.scenes:
 for layer in scene.view_layers:layer.update()
centre=Vector((69.63215041268096,13.996751978703918))
report=[]
for obj in bpy.data.collections['LRB_EXTERIOR'].all_objects:
 if obj.type!='MESH':continue
 pts=[obj.matrix_world@v.co for v in obj.data.vertices]
 near=sum(abs((Vector((p.x,p.y))-centre).length-9.8)<.015 for p in pts)
 if 'roof' in obj.name.lower() or near:
  report.append({'name':obj.name,'vertices':len(pts),'openingRimVertices':near,'minZ':min(p.z for p in pts),'maxZ':max(p.z for p in pts)})
(ROOT/'result/blender/stage38/coupled-inventory.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
