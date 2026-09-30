"""Read-only geometry acceptance for the saved Peacock exterior."""
from pathlib import Path
import bpy,json
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v62.blend'));p=ROOT/'result/blender/stage62/peacock-exterior-audit.json';a=json.loads(p.read_text())
def obj(name):return bpy.data.objects['PEA_D5_exterior62_'+name]
def extent(name):
 o=obj(name);pts=[o.matrix_world@v.co for v in o.data.vertices];return {'low':min(p.z for p in pts),'high':max(p.z for p in pts),'vertices':len(pts)}
low=extent('podium_roof_stone');high=extent('upper_roof_stone');glass=extent('upper_glass_glass')
assert abs(low['high']-6.6)<.0001 and abs(high['high']-19.5)<.0001
assert len(obj('upper_glass_glass').data.vertices)//8==9
assert len(obj('poster_blank_display').data.vertices)//8==3
assert len(obj('starburst_gold').data.vertices)//32==19
assert all(p.normal.z>.99 for p in obj('upper_roof_stone').data.polygons)
assert all(bpy.data.objects[n].hide_render for n in a['hiddenObjects'])
assert a['protectedBefore']==a['protectedAfter']
wall=a['frontWall'];origin=Vector((*wall['p'],0));u=Vector(((wall['q'][0]-wall['p'][0])/wall['length'],(wall['q'][1]-wall['p'][1])/wall['length'],0))
assert min((obj('upper_roof_stone').matrix_world@v.co-origin).dot(u)for v in obj('upper_roof_stone').data.vertices)>-.0001
normal=Vector((*wall['outward'],0))
frame_front=max((obj('window_rail_frame').matrix_world@v.co-origin).dot(normal)for v in obj('window_rail_frame').data.vertices)
stone_front=max((obj('upper_pier_stone').matrix_world@v.co-origin).dot(normal)for v in obj('upper_pier_stone').data.vertices)
assert frame_front>stone_front+.04,'Joinery must stand proud of the stone plane'
signs=[o for o in bpy.data.collections['PEA_EXTERIOR'].all_objects if o.type=='FONT' and o.name.startswith('PEA_exterior62')];assert len(signs)==17 and all(o.matrix_world.to_3x3().determinant()>0 for o in signs)
a['savedMeasurements']={'podium':low,'upper':high,'glazing':glass,'windows':9,'posters':3,'starbursts':19,'signObjects':len(signs),'joineryProjection':frame_front-stone_front};p.write_text(json.dumps(a,indent=2)+'\n');print('SAVED_PEACOCK_EXTERIOR_VERIFIED')
