"""Measure the saved setback and open vestibule, independent of browser export."""
from pathlib import Path
import json
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v68.blend'))
path=ROOT/'result/blender/stage68/connaught-vestibule-audit.json'
a=json.loads(path.read_text())
origin,right,outward=[Vector(a[k]) for k in ['origin','right','outward']]
def local(obj,v):
 p=obj.matrix_world@v.co;d=p-origin
 return (d.dot(right),d.dot(outward),p.z)
glass=bpy.data.objects['CON_D5_vestibule68_glass']
assert len(glass.data.vertices)==16
panels=[]
for i in [0,8]:
 pts=[local(glass,v) for v in glass.data.vertices[i:i+8]]
 depth=sum(p[1] for p in pts)/8
 assert abs(depth+2.78)<.0001
 assert abs(min(p[2] for p in pts)-.145)<.0001
 assert abs(max(p[2] for p in pts)-2.815)<.0001
 panels.append(depth)
wall=bpy.data.objects['CON_D5_vestibule68_wall']
for i in [0,8]:
 pts=[local(wall,v) for v in wall.data.vertices[i:i+8]]
 xs=[p[0] for p in pts]
 inner=max(xs) if max(xs)<0 else min(xs)
 assert abs(abs(inner)-.975)<.0001
lamp=bpy.data.objects['CON_D5_vestibule68_light']
assert sum(local(lamp,v)[0] for v in lamp.data.vertices)/len(lamp.data.vertices)>.89
granite=bpy.data.objects['CON_D5_vestibule68_granite']
assert abs(max(local(granite,v)[2] for v in granite.data.vertices)-3.12)<.0001
material=bpy.data.materials['CON_V68_glass']
assert abs(material['webOpacity']-.18)<.0001
assert material.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value>.1
for name in a['hiddenPreviousObjects']:assert bpy.data.objects[name].hide_render
assert not a['changedOtherObjects']
a['savedMeasurements']={'doorPanelDepths':panels,'clearHallWidth':1.95,'glazingOpacity':.18,'streetDoorRemoved':True}
path.write_text(json.dumps(a,indent=2)+'\n')
print('SAVED_CONNAUGHT_VESTIBULE_VERIFIED')
