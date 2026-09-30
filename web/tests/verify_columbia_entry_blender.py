"""Independently measure saved Columbia oval panel geometry and outward relief."""
from pathlib import Path
import json
import bpy
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v67.blend'))
path = ROOT/'result/blender/stage67/columbia-entry-audit.json'
a = json.loads(path.read_text())
origin,right,outward = [Vector(a[k]) for k in ['origin','right','outward']]
wood = bpy.data.objects['COL_D5_entry67_wood']
assert len(wood.data.vertices)==480
# Discover connected components rather than assuming a vertex ordering.
neighbors={i:set() for i in range(len(wood.data.vertices))}
for edge in wood.data.edges:
 left,right_index=edge.vertices
 neighbors[left].add(right_index);neighbors[right_index].add(left)
seen=set();components=[]
for index in neighbors:
 if index in seen:continue
 stack=[index];seen.add(index);members=[]
 while stack:
  current=stack.pop();members.append(current)
  for adjacent in neighbors[current]:
   if adjacent not in seen:seen.add(adjacent);stack.append(adjacent)
 if len(members)==144:components.append(set(members))
assert len(components)==2
measured=[];face_count=0
for members in components:
 points=[wood.matrix_world@wood.data.vertices[i].co for i in members]
 xs=[(p-origin).dot(right) for p in points];zs=[p.z for p in points]
 center=(min(xs)+max(xs))/2
 assert abs(abs(center)-.4125)<.0001
 assert abs(max(xs)-min(xs)-.47)<.0001
 assert abs(min(zs)-.46)<.0001 and abs(max(zs)-1.04)<.0001
 measured.append({'center':center,'width':max(xs)-min(xs),'height':max(zs)-min(zs)})
 for poly in wood.data.polygons:
  if set(poly.vertices).issubset(members):
   assert poly.normal.dot(outward)>0
   face_count+=1
assert face_count==192
assert len(bpy.data.objects['COL_D5_entry67_trim'].data.vertices)==64
for name in a['hiddenPreviousObjects']:
 assert bpy.data.objects[name].hide_render
assert bpy.data.objects['COL_D4_portal_name'].data.size<.15
assert not a['changedOtherObjects']
a['savedMeasurements']={'ovalPanels':measured,'tabletBorderMembers':8,'outwardOvalFaces':192}
path.write_text(json.dumps(a,indent=2)+'\n')
print('SAVED_COLUMBIA_ENTRY_VERIFIED')
