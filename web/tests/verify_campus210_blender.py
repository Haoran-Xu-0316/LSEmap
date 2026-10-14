"""Verify saved room isolation, plan seats, real door apertures and source materials."""
from pathlib import Path
import hashlib,json,sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from refine_portsmouth_exterior207 import material_fingerprint
BASE=ROOT/'result/blender/LSE_campus_detailed_v209.blend'
CURRENT=ROOT/'result/blender/LSE_campus_detailed_v210.blend'
OUT=ROOT/'result/blender/stage210'
bpy.ops.wm.open_mainfile(filepath=str(BASE))
materials={m.name:material_fingerprint(m) for m in bpy.data.materials}
bpy.ops.wm.open_mainfile(filepath=str(CURRENT))
for name,expected in materials.items():assert material_fingerprint(bpy.data.materials[name])==expected,name
room=json.loads((ROOT/'result/blender/con-room210/audit.json').read_text())
collection=bpy.data.collections[room['targetCollection']]
objects=list(collection.all_objects)
assert {o.name for o in objects}==set(room['addedObjects'])
assert room['collectionSpec']['scene'] in bpy.data.scenes
for obj in objects:
    owners=[scene.name for scene in bpy.data.scenes if obj.name in scene.objects]
    assert owners==[room['collectionSpec']['scene']],(obj.name,owners)
    assert not obj.hide_render

def tree(items):
    vertices,faces=[],[]
    for obj in items:
        offset=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        faces.extend(tuple(offset+i for i in f.vertices) for f in obj.data.polygons)
    return BVHTree.FromPolygons(vertices,faces,all_triangles=False)

floor=next(o for o in objects if 'registered_bay_floor' in o.name)
floor_tree=tree([floor])
seat=next(o for o in objects if 'eighteen_black_seat_cushions' in o.name)
assert len(seat.data.vertices)==18*8
actual=[]
for start in range(0,len(seat.data.vertices),8):
    center=sum((seat.matrix_world@v.co for v in seat.data.vertices[start:start+8]),Vector())/8
    actual.append((center.x,center.y))
assert len(actual)==18
expected=[s['center'] for s in room['seatPositions']]
for a,b in zip(actual,expected):
    assert (Vector(a)-Vector(b)).length<1e-5
    hit=floor_tree.ray_cast(Vector((a[0],a[1],.3)),Vector((0,0,-1)),.5)
    assert hit[0] is not None and abs(hit[0].z)<1e-6
minimum=min((Vector(a)-Vector(b)).length for i,a in enumerate(actual) for b in actual[i+1:])
assert minimum>=.60-1e-5
walls=tree([o for o in objects if any(tag in o.name for tag in ['full_long_oak_wall','short_oak_presentation_wall','cutaway_window_side_walls','door_lintel'])])
doors=tree([o for o in objects if any(tag in o.name for tag in ['two_oak_door_leaves','entrance_door_leaf','sectioned_fourth_door'])])
probes=[]
for a,b in room['doorIntervals']:
    probes.append((Vector(((a+b)/2,-2.6,1.0)),Vector((0,1,0)),.55))
a,b=room['mainDoorInterval'];probes.append((Vector((-4.2,(a+b)/2,1.0)),Vector((1,0,0)),.55))
probes.append((Vector((((190+226)/2-280)*.02,3.35,.4)),Vector((0,-1,0)),.55))
for origin,direction,distance in probes:
    assert walls.ray_cast(origin,direction,distance)[0] is None
    assert doors.ray_cast(origin,direction,distance)[0] is not None
roof=json.loads((ROOT/'result/blender/lrb-exterior210/audit.json').read_text())
for name in roof['archivedObjects']:assert bpy.data.objects[name].hide_render
for name in roof['addedObjects']:assert not bpy.data.objects[name].hide_render
proof=dict(sourceModelSha256=hashlib.sha256(CURRENT.read_bytes()).hexdigest(),completeModelReopened=True,
           originalMaterialsVerified=len(materials),newRoomOnlyInItsOwnScene=True,roomObjects=len(objects),
           actualSeatCount=len(actual),floorSupportRays=len(actual),minimumActualSeatSpacingMetres=minimum,
           doorWallAperturesVerified=len(probes),closedDoorLeavesVerified=len(probes),
           correctedRoofObjectsVisible=True,previousRoofObjectsArchived=True)
(OUT/'room-and-roof-verification.json').write_text(json.dumps(proof,indent=2)+'\n')
print('CAMPUS210_ROOM_ROOF_VERIFIED',len(objects),len(probes),flush=True)
