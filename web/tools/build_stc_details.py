"""Refine St Clement's photographed street corner and entrance.

Run inside Blender. Footprint stays fixed; unmeasured heights and hidden surfaces
remain estimates. Reference photographs and artworks are never used as textures.
"""
from pathlib import Path
import array
import hashlib
import json
import sys
import bpy
from mathutils import Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, Facade, materials

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage11/stc'
OUT.mkdir(parents=True, exist_ok=True)
profile = next(p for p in json.loads((ROOT/'result/blender/stage05/infill-geometry.json').read_text()) if p['code']=='STC')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v10.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
collection = bpy.data.collections['STC_EXTERIOR']

def protected_geometry():
    digest = hashlib.sha256()
    excluded = set(collection.all_objects)
    for obj in sorted(bpy.data.objects, key=lambda obj: obj.name):
        if obj.type != 'MESH' or obj in excluded:
            continue
        digest.update(obj.name.encode())
        digest.update(array.array('f', [v for row in obj.matrix_world for v in row]).tobytes())
        coordinates = array.array('f', [0]) * (len(obj.data.vertices)*3)
        obj.data.vertices.foreach_get('co', coordinates)
        digest.update(coordinates.tobytes())
    return digest.hexdigest()

before = protected_geometry()
for obj in list(collection.all_objects):
    bpy.data.objects.remove(obj, do_unlink=True)
materials.clear()
colors = {'render': (.64,.65,.60), 'stone': (.49,.51,.47),
          'frame': (.66,.67,.59), 'glass': (.08,.13,.14),
          'metal': (.10,.12,.12), 'red': (.51,.018,.026),
          'terracotta': (.32,.11,.07), 'shadow': (.055,.065,.060),
          'roof': (.22,.24,.22), 'soil': (.065,.045,.027),
          'leaf': (.065,.13,.063), 'panel': (.20,.28,.29)}
for name, color in colors.items():
    material = bpy.data.materials.new('STC11_'+name)
    material.use_nodes = True
    material.diffuse_color = (*color,1)
    shader = material.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = material.diffuse_color
    shader.inputs['Roughness'].default_value = .24 if name=='glass' else .78
    materials[name] = material
groups = {}
facades = [Facade(profile, wall, groups) for wall in profile['walls']]
front = facades[5]
entry_x = front.length*.52


def opening(facade, x, bottom, top, width, pitch, z0, z1, sill=True):
    """Actual wall opening with 0.34 m reveals, rather than glass over a solid wall."""
    for side in [-1,1]:
        facade.box('wall_pier','render',x+side*(pitch+width)/4,(bottom+top)/2,(pitch-width)/2,top-bottom,.42,-.21)
    for low,high in [(z0,bottom),(top,z1)]:
        facade.box('wall_spandrel','render',x,(low+high)/2,pitch,high-low,.42,-.21)
    facade.box('recessed_glass','glass',x,(bottom+top)/2,width,top-bottom,.045,-.35)
    for side in [-1,1]:
        facade.box('window_reveal','stone',x+side*width/2,(bottom+top)/2,.07,top-bottom,.37,-.19)
        facade.box('recessed_window_jamb','frame',x+side*(width/2-.05),(bottom+top)/2,.045,top-bottom,.055,-.30)
    for z in [bottom,top,bottom+(top-bottom)*.72]:
        facade.box('window_transom','frame',x,z,width,.046,.07,-.29)
    facade.box('window_mullion','frame',x,(bottom+top)/2,.048,top-bottom,.07,-.29)
    if sill:
        facade.box('projecting_sill','stone',x,bottom-.035,width+.15,.085,.49,-.16)
        facade.box('sill_drip','shadow',x,bottom-.071,width+.07,.013,.02,.085)

# The long Clare Market side: four upper window rows, a distinct ground floor,
# and a recessed top storey. The entry opening replaces, rather than covers, a bay.
for index, facade in enumerate(facades):
    if index in {0,4,6}:
        continue
    count = 14 if index==5 else max(1,round(facade.length/2.9))
    pitch = facade.length/count
    for row in range(4):
        z0 = 3.7 + row*3.55
        for bay in range(count):
            opening(facade,(bay+.5)*pitch,z0+.78,z0+2.74,min(1.72,pitch*.64),pitch,z0,z0+3.55)
    if index==5:
        # Keep entry placement from the Clare Market address study; exact bay is estimated.
        a,b = entry_x-1.62, entry_x+1.62
        for start,end in [(0,a),(b,facade.length)]:
            bays = max(1,round((end-start)/2.9)); span=(end-start)/bays
            for bay in range(bays):
                opening(facade,start+(bay+.5)*span,.22,2.74,span*.78,span,0,3.7)
        facade.box('entrance_upper_wall','render',entry_x,3.52,3.24,.36,.42,-.21)
    else:
        for bay in range(count):
            opening(facade,(bay+.5)*pitch,.35,2.74,pitch*.72,pitch,0,3.7)
    facade.box('ground_plinth','stone',facade.length/2,.105,facade.length,.21,.47,-.19)
    facade.box('upper_edge','render',facade.length/2,17.96,facade.length,.12,.53,-.16)

# North-west wall: deeply recessed red landings at the Portugal Street corner.
stair = facades[0]
stair_width = 3.1
stair.box('stair_backwall','shadow',stair_width/2,9.0,stair_width,18.0,.20,-1.25)
stair.box('stair_outer_pier','render',.22,9.0,.44,18.0,.50,-.24)
stair.box('stair_inner_pier','render',stair_width+.23,9.0,.46,18.0,.50,-.24)
for level in range(5):
    z = level*3.55
    stair.box('recessed_landing','stone',stair_width/2,z+.10,stair_width,.20,1.28,-.63)
    stair.box('red_landing_parapet','terracotta',stair_width/2,z+.66,stair_width-.38,1.0,.16,-.32)
    stair.box('landing_handrail','metal',stair_width/2,z+1.20,stair_width-.34,.055,.09,-.26)
    # Only the exterior landings are modeled; no fabricated interior stair route.
    stair.box('landing_rear_door','glass',stair_width/2,z+1.50,.95,2.4,.04,-1.12)
start = stair_width+.46
span = stair.length-start
for row in range(5):
    z0 = row*3.55 if row==0 else 3.7+(row-1)*3.55
    z1 = 3.7 if row==0 else z0+3.55
    for bay in range(2):
        opening(stair,start+(bay+.5)*span/2,z0+.65,z1-.65,span*.30,span/2,z0,z1)

# Narrow chamfer between Portugal Street and Clare Market. The historical artwork
# is represented only by its recessed panel and plaque, without a false replica.
corner = facades[6]
corner.box('corner_wall','render',corner.length/2,8.98,corner.length,17.96,.46,-.22)
panel_width = min(1.85,corner.length-.85)
corner.box('mural_stone_frame','stone',corner.length/2,11.10,panel_width+.16,11.95,.10,.065)
corner.box('mural_panel_placeholder','panel',corner.length/2,11.10,panel_width,11.78,.026,.13)
corner.box('mural_lower_plaque','panel',corner.length/2,4.80,panel_width+.35,.83,.07,.12)
corner.box('corner_display_case','metal',corner.length/2,1.35,corner.length-.82,2.1,.10,.07)
corner.box('corner_display_glazing','glass',corner.length/2,1.35,corner.length-.94,1.96,.035,.13)
corner.box('corner_plinth','stone',corner.length/2,.21,corner.length,.42,.51,-.20)
# The eastern end is a blank wall in the separate artwork photographs.
end = facades[4]
end.box('east_blank_wall','render',end.length/2,9.0,end.length,18.0,.42,-.21)

# Setback upper floor with terracotta panels, shallow ribbon windows and projecting coping.
for index, facade in enumerate(facades):
    facade.box('roof_edge_shadow','shadow',facade.length/2,18.10,facade.length,.15,.66,-.08)
    facade.box('top_floor_backwall','terracotta',facade.length/2,19.00,facade.length,1.72,.22,-.70)
    if index not in {4,6}:
        count=max(1,round(facade.length/2.6));pitch=facade.length/count
        for bay in range(count):
            x=(bay+.5)*pitch
            facade.box('attic_glass','glass',x,19.18,pitch*.73,.75,.05,-.56)
            for z in [18.80,19.56]:facade.box('attic_frame','frame',x,z,pitch*.75,.045,.075,-.52)
            for dx in [-pitch*.365,0,pitch*.365]:facade.box('attic_mullion','frame',x+dx,19.18,.042,.75,.075,-.52)
    for seam in range(1,max(1,round(facade.length/2.5))):
        facade.box('parapet_joint','stone',facade.length*seam/max(1,round(facade.length/2.5)),20.30,.015,.98,.025,.132)
# Miter the continuous roof edge at footprint corners to avoid open butt joints.
ring = profile['building']['rings'][0]
for name,material,inner,outer,bottom,top in [
    ('roof_parapet','render',-.36,.12,19.785,20.815),
    ('roof_coping','stone',-.38,.22,20.79,20.91),
]:
    inner_ring,outer_ring = [],[]
    for i,point in enumerate(ring):
        n0,n1 = facades[(i-1)%len(facades)].n,facades[i].n
        bisector = (n0+n1).normalized()
        scale = max(.20,bisector.dot(n1))
        inner_ring.append(Vector(point)+bisector*inner/scale)
        outer_ring.append(Vector(point)+bisector*outer/scale)
    geometry = Geometry('STC',name,material)
    for i in range(len(ring)):
        j=(i+1)%len(ring)
        points=[inner_ring[i],inner_ring[j],outer_ring[j],outer_ring[i]]
        geometry.add([(*point,z) for z in [bottom,top] for point in points],
                     [(0,3,2,1),(4,5,6,7),(0,1,5,4),(3,7,6,2)])
    groups[name]=geometry
roof = Geometry('STC','flat_roof','roof')
for triangle in profile['building']['triangles']:
    roof.add([(*point,20.79) for point in triangle],[(0,1,2)])
groups['roof']=roof

# Entry source: red left jamb, grey fascia, recessed right-hand door and left planter.
# Facade local x increases to the viewer's left, so the red jamb is at positive x.
front.box('entry_soffit','stone',entry_x,2.93,3.20,.15,1.02,-.47)
front.box('entry_rear_glass','glass',entry_x,1.45,2.88,2.9,.06,-.76)
front.box('red_entry_jamb','red',entry_x+1.37,1.48,.48,2.96,.55,-.03)
front.box('entry_right_reveal','stone',entry_x-1.55,1.48,.13,2.96,.90,-.40)
front.box('entry_name_fascia','stone',entry_x,3.23,3.24,.61,.35,.005)
front.box('entry_lse_square','red',entry_x+1.05,3.23,.43,.43,.055,.21)
front.label('LSE',entry_x+1.05,3.095,.265,'frame',.245)
front.label("St Clement's",entry_x-.20,3.09,.30,'metal',.19)
door_x=entry_x-.54
for x in [door_x-.53,door_x+.53]:
    front.box('entry_door_jamb','frame',x,1.42,.045,2.80,.075,-.62)
for z in [.06,2.81]:front.box('entry_door_frame','frame',door_x,z,1.08,.045,.08,-.62)
front.box('door_kickplate','metal',door_x,.20,1.02,.30,.055,-.58)
front.box('door_pull','metal',door_x+.38,1.19,.026,.51,.08,-.52)
front.box('entry_threshold','stone',entry_x,.025,3.15,.05,1.18,-.28)
front.box('entry_callplate','metal',entry_x-1.84,1.63,.28,.55,.075,.015)
front.box('entry_call_screen','glass',entry_x-1.84,1.73,.18,.19,.016,.06)
front.box('entry_call_button','frame',entry_x-1.84,1.47,.05,.05,.025,.064)
front.box('entry_floodlight_arm','metal',entry_x+.42,4.02,.045,.20,.35,.09)
front.box('entry_floodlight','metal',entry_x+.42,3.99,.56,.21,.20,.30)
front.box('entry_floodlight_lens','frame',entry_x+.42,3.94,.47,.09,.018,.41)
front.box('entry_information_panel','stone',entry_x+.49,1.93,.78,1.64,.08,-.67)
for text,z,size in [("St Clement's",2.48,.115),('Main Entrance',2.31,.10)]:front.label(text,entry_x+.49,z,size,'metal',-.62)
front.box('entry_planter','metal',entry_x+.56,.25,1.04,.50,.52,-.20)
front.box('planter_soil','soil',entry_x+.56,.49,.94,.02,.43,-.20)
# Small grouped leaf blades provide volume without importing reference imagery.
for i in range(19):
    x=entry_x+.13+(i%7)*.13;depth=-.36+(i%3)*.15;h=.23+(i%5)*.045
    front.box('planter_stem','leaf',x,.49+h/2,.018,h,.018,depth)
    for side in [-1,1]:
        front.group('planter_leaf','leaf').add([front.point(x,.52,depth),front.point(x+side*.075,.52+h*.70,depth+.028),front.point(x+side*.025,.52+h,depth)],[(0,1,2)])

for geometry in groups.values():
    geometry.finish()
bpy.context.view_layer.update()
assert protected_geometry()==before, 'Geometry outside St Clements changed'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v11.blend'))
direction=(Vector(corner.n)+Vector(stair.n)*.40).normalized()
record={'code':'STC','exteriorDirection':[direction.x,.42,-direction.y],
        'scope':'Photo-informed Clare Market window reveals, recessed roof storey, red landing strip, corner panel and recessed entrance. Artwork represented by panel placement only; heights, exact entry bay and unseen surfaces estimated. No verified interior.',
        'reference':profile['reference'],
        'supportingReference':'data/建筑图片/STC_St Clement_s/01_建筑实拍/campus_photos_round2_STC_geograph_7222785_01.jpg',
        'components':sum(g.parts for g in groups.values()),'protectedGeometrySha256':before,
        'orientation':{'mainWindowWall':5,'cornerPanelWall':6,'landingWall':0,'blankEndWall':4},
        'detailView':{'label':'入口细节','position':list(front.point(entry_x,3.30,12)),'target':list(front.point(entry_x,2.25,0)),'fov':44}}
(OUT/'stc-manifest.json').write_text(json.dumps({'buildings':[record]},indent=2)+'\n')
print('STC_REFINEMENT_COMPLETE',record,flush=True)
