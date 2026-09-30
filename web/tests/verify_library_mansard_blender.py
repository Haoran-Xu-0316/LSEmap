"""Read-only native library roof verification: connections, void and normals."""
from pathlib import Path
import bpy,json,math
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v60.blend'))
path=ROOT/'result/blender/stage60/library-mansard-audit.json';audit=json.loads(path.read_text())
deck=bpy.data.objects['LRB_roof_deck_around_atrium'];points=[deck.matrix_world@v.co for v in deck.data.vertices]
assert all(abs(p.z-audit['deckHeight'])<.0001 for p in points)
assert all(any((Vector((p.x,p.y))-Vector(before)).length<.0001 for p in points)for before in audit['holeXYBefore'])
roof=bpy.data.objects['LRB_D5_mansard60_slate'];assert all(p.normal.z>.1 for p in list(roof.data.polygons)[:audit['roofTriangleCount']])
for start in range(audit['roofTriangleCount']+2,len(roof.data.polygons),4):
 assert all(p.normal.z>0 for p in list(roof.data.polygons)[start:start+2])
dome=bpy.data.objects['LRB_V31_sliced_dome_shell'];dome_points=[dome.matrix_world@v.co for v in dome.data.vertices];assert abs(min(p.z for p in dome_points)-audit['deckHeight'])<.0001
lining=bpy.data.objects['LRB_D5_mansard60_lining'];cx=(min(p.x for p in dome_points)+max(p.x for p in dome_points))/2;cy=(min(p.y for p in dome_points)+max(p.y for p in dome_points))/2
for polygon in list(lining.data.polygons)[::3]:
 center=polygon.center;assert Vector((center.x-cx,center.y-cy,0)).dot(polygon.normal)<0
# Dormer glazing centres must sit just inside each retained public facade.
ring=[Vector(p)for p in next(b for b in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings']if b['code']=='LRB')['rings'][0]]
glass=bpy.data.objects['LRB_D5_mansard60_glass'];verts=list(glass.data.vertices);centres=[sum((glass.matrix_world@v.co for v in verts[i:i+8]),Vector())/8 for i in range(0,len(verts),8)]
for window,center in zip(audit['dormers'],centres):
 a,b=ring[window['edge']],ring[(window['edge']+1)%len(ring)];direction=(b-a).normalized();normal=Vector((-direction.y,direction.x));offset=(Vector(center.xy)-a).dot(normal);assert abs(offset+.415)<.001,offset
 assert abs(center.z-(window['low']+window['high'])/2)<.001
aperture=bpy.data.objects['LRB_V31_north_aperture_glass'];origin=aperture.matrix_world@aperture.data.vertices[0].co
u=Vector((1,0,0));v=Vector((0,-1,1)).normalized();normal=u.cross(v)
grid=bpy.data.objects['LRB_D5_mansard60_aperture_steel'];grid_vertices=list(grid.data.vertices);assert len(grid_vertices)==12*len(audit['triangularGridLines'])
for index,line in enumerate(audit['triangularGridLines']):
 grid_points=[grid.matrix_world@p.co for p in grid_vertices[index*12:(index+1)*12]]
 for endpoint,vertices in zip(line['endpoints'],[grid_points[:6],grid_points[6:]]):
  center=sum(vertices,Vector())/6;expected=origin+u*endpoint[0]+v*endpoint[1];assert (center-expected).length<.0001
audit['savedMeasurements']={'deckHeight':min(p.z for p in points),'domeBase':min(p.z for p in dome_points),'perimeterUpwardFaces':audit['roofTriangleCount'],'preservedVoidPoints':len(audit['holeXYBefore']),'verifiedDormers':len(centres),'inwardLightwellLining':True,'verifiedGridLines':len(audit['triangularGridLines']),'gridFamilies':len(set(line['family']for line in audit['triangularGridLines']))};path.write_text(json.dumps(audit,indent=2)+'\n');print('LIBRARY_ROOF_VERIFIED',audit['savedMeasurements'])
