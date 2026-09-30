"""Read-only measurements of the saved PEL entrance."""
from pathlib import Path
import bpy,json
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v61.blend'))
path=ROOT/'result/blender/stage61/pethick-entrance-audit.json';audit=json.loads(path.read_text());wall=audit['frontWall'];p=Vector((*wall['p'],0));u=Vector(((wall['q'][0]-wall['p'][0])/wall['length'],(wall['q'][1]-wall['p'][1])/wall['length'],0));n=Vector((*wall['outward'],0))
def extent(name):
 o=bpy.data.objects['PEL_D5_entry61_'+name];pts=[o.matrix_world@v.co for v in o.data.vertices];return {'width':max((q-p).dot(u)for q in pts)-min((q-p).dot(u)for q in pts),'frontDepth':max((q-p).dot(n)for q in pts),'zMin':min(q.z for q in pts),'zMax':max(q.z for q in pts)}
canopy=extent('canopy_fascia_silver');glass=extent('upper_glass_glass');assert abs(canopy['width']-5.68)<.0001;assert abs(canopy['frontDepth']-1.60)<.0001;assert abs(glass['zMin']-4.07)<.0001 and abs(glass['zMax']-5.86)<.0001
shell=bpy.data.objects['PEL_D5_entry61_revolving_glass'];assert len(shell.data.polygons)==20
for name in audit['hiddenObjects']:assert bpy.data.objects[name].hide_render
for o in bpy.data.collections['PEL_EXTERIOR'].all_objects:
 if o.type=='FONT' and o.name.startswith('PEL_entry61'):assert o.matrix_world.to_3x3().determinant()>0
assert audit['protectedBefore']==audit['protectedAfter'];audit['savedMeasurements']={'canopy':canopy,'upperGlass':glass,'revolvingFaces':len(shell.data.polygons)};path.write_text(json.dumps(audit,indent=2)+'\n');print('SAVED_PETHICK_ENTRANCE_VERIFIED')
