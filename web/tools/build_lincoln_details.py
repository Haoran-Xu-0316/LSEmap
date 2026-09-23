"""Rebuild the photographed Lincoln Chambers recessed three-arch entrance.

Run inside Blender. The entrance is an exterior study, not an inferred interior.
Retain the earlier upper envelope where photographs do not support a replacement.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import sys
import bpy
from mathutils import Vector, Matrix
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Facade, Geometry, materials
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'result/blender/stage12/lincoln'
OUT.mkdir(parents=True, exist_ok=True)
profile = next(p for p in json.loads((ROOT/'result/blender/stage05/infill-geometry.json').read_text()) if p['code']=='LCH')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v11.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
collection=bpy.data.collections['LCH_EXTERIOR']

def protected_geometry():
    digest=hashlib.sha256();excluded=set(collection.all_objects)
    for obj in sorted(bpy.data.objects,key=lambda o:o.name):
        if obj.type!='MESH' or obj in excluded:continue
        digest.update(obj.name.encode())
        digest.update(array.array('f',[v for row in obj.matrix_world for v in row]).tobytes())
        coordinates=array.array('f',[0])*(len(obj.data.vertices)*3)
        obj.data.vertices.foreach_get('co',coordinates);digest.update(coordinates.tobytes())
    return digest.hexdigest()

before=protected_geometry()
groups={}
front=Facade(profile,next(w for w in profile['walls'] if w['front']),groups)
# Preserve the upper and neighbouring envelopes; remove only the old ground-floor
# component islands of the entrance-facing wall and the generic portal ornaments.
# Geometry's original boxes and arches have disconnected vertices per component.
def component_islands(mesh):
    links=[[] for _ in mesh.vertices]
    for edge in mesh.edges:
        a,b=edge.vertices;links[a].append(b);links[b].append(a)
    unseen=set(range(len(mesh.vertices)))
    while unseen:
        pending=[unseen.pop()];island=set(pending)
        while pending:
            for neighbour in links[pending.pop()]:
                if neighbour in unseen:
                    unseen.remove(neighbour);island.add(neighbour);pending.append(neighbour)
        yield island

removed=0
for obj in list(collection.all_objects):
    if obj.type=='FONT' or any(name in obj.name for name in [
        'entrance_','door_','threshold','arched_portal','portal_keystone','side_arches','green_name_board']):
        bpy.data.objects.remove(obj,do_unlink=True);continue
    if obj.type!='MESH':continue
    reject=set()
    for island in component_islands(obj.data):
        points=[obj.matrix_world@obj.data.vertices[i].co for i in island]
        center=sum(points,Vector())/len(points)
        delta=Vector(center.xy)-Vector(front.wall['p'])
        x,depth=delta.dot(front.u),delta.dot(front.n)
        # Remove all ground facade modules on edge 0, leaving the upper study intact.
        if -.12<x<front.length+.12 and abs(depth)<.5 and max(p.z for p in points)<4.21:
            reject.update(island);removed+=1
    if not reject:continue
    keep=[i for i in range(len(obj.data.vertices)) if i not in reject]
    remap={old:new for new,old in enumerate(keep)}
    faces=[poly for poly in obj.data.polygons if not any(i in reject for i in poly.vertices)]
    oldmesh=obj.data;mesh=bpy.data.meshes.new(oldmesh.name+'_preserved')
    mesh.from_pydata([oldmesh.vertices[i].co[:] for i in keep],[],[[remap[i] for i in poly.vertices] for poly in faces])
    for mat in oldmesh.materials:mesh.materials.append(mat)
    for new,old in zip(mesh.polygons,faces):new.material_index=old.material_index
    if oldmesh.uv_layers.active:
        uv=mesh.uv_layers.new(name='SurfaceUV')
        for new,old in zip(mesh.polygons,faces):
            for ni,oi in zip(new.loop_indices,old.loop_indices):uv.data[ni].uv=oldmesh.uv_layers.active.data[oi].uv
    obj.data=mesh

materials.clear()
colors={'stone':(.49,.47,.41),'joint':(.25,.25,.22),'plinth':(.25,.115,.09),
        'wood':(.25,.10,.043),'wood_dark':(.12,.045,.022),'glass':(.075,.135,.14),
        'gold':(.56,.40,.12),'green':(.065,.15,.075),'cream':(.70,.68,.57),
        'tile_green':(.055,.115,.085),'metal':(.12,.14,.14),'red':(.57,.018,.026)}
for name,color in colors.items():
    mat=bpy.data.materials.new('LCH12_'+name);mat.use_nodes=True;mat.diffuse_color=(*color,1)
    shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=mat.diffuse_color
    shader.inputs['Roughness'].default_value=.29 if name in {'glass','gold'} else .73
    materials[name]=mat
x0=front.length/2
opening_half=1.85
back_depth=-1.30
spring=2.63
radius=.77
header_bottom=3.54
# Two stone piers frame a splayed vestibule. Ground modules outside remain simple
# shopfronts because the provided images do not establish their full configuration.
for sign in [-1,1]:
    outer=x0+sign*opening_half
    width=front.length/2-opening_half
    x=outer+sign*width/2
    front.box('ground_stone_pier','stone',outer+sign*.23,1.83,.46,3.66,.50,-.22)
    window_width=max(.4,width-.62)
    front.box('ground_shop_glass','glass',x+sign*.20,1.66,window_width,2.72,.04,-.24)
    for dx in [-window_width/2,0,window_width/2]:front.box('ground_shop_mullion','cream',x+sign*.20+dx,1.66,.055,2.72,.09,-.18)
    for z in [.30,2.90]:front.box('ground_shop_rail','cream',x+sign*.20,z,window_width,.07,.10,-.16)
    front.box('ground_stone_apron','stone',x,.16,width,.32,.38,-.19)
    front.box('ground_shop_head','stone',x,3.37,width,.70,.38,-.19)
    front.box('porch_red_plinth','plinth',outer+sign*.22,.61,.47,1.22,.51,-.21)
    for z in [1.24,2.16,3.04]:front.box('pier_bed_joint','joint',outer+sign*.22,z,.46,.013,.02,.041)

# Recessed back face and two angled side faces, all normals point into the porch.
def inner_facade(a,b):
    p,q=Vector(front.point(a[0],0,a[1])[:2]),Vector(front.point(b[0],0,b[1])[:2])
    tangent=(q-p).normalized();normal=Vector((-tangent.y,tangent.x))
    courtyard=Vector(front.point(x0,0,-.3)[:2])
    if normal.dot(courtyard-(p+q)/2)<0:normal=-normal
    return Facade(profile,{'p':list(p),'q':list(q),'length':(q-p).length,'outward':list(normal)},groups)
back=inner_facade((x0-.98,back_depth),(x0+.98,back_depth))
left=inner_facade((x0+opening_half,0),(x0+.98,back_depth))
right=inner_facade((x0-.98,back_depth),(x0-opening_half,0))


def arched_leaf(facade,center,width,is_main=False):
    r=width/2
    # Stone spandrel above the arch follows the curve instead of crossing the opening.
    for j in range(36):
        a,b=j*math.pi/36,(j+1)*math.pi/36
        points=[facade.point(center+r*math.cos(a),spring+r*math.sin(a),0),
                facade.point(center+r*math.cos(b),spring+r*math.sin(b),0),
                facade.point(center+r*math.cos(b),header_bottom,0),
                facade.point(center+r*math.cos(a),header_bottom,0)]
        facade.group('arch_stone_spandrel','stone').add(points,[(0,1,2,3)])
    side=(facade.length-width)/2
    for sign in [-1,1]:
        facade.box('porch_side_stone','stone',center+sign*(width+side)/2,header_bottom/2,side,header_bottom,.22,-.11)
        facade.box('porch_side_plinth','plinth',center+sign*(width+side)/2,.6,side,1.2,.24,-.09)
    # Arched glass fanlight and two profiled timber rings.
    facade.group('arched_fanlight','glass').add([facade.point(center,spring,-.055)]+[facade.point(center+r*math.cos(i*math.pi/36),spring+r*math.sin(i*math.pi/36),-.055) for i in range(37)],[(0,i+1,i+2) for i in range(36)])
    facade.arch('timber_arch_outer','wood_dark',center,spring,r,.075,.065)
    facade.arch('timber_arch_inner','wood',center,spring,r-.045,.05,.085)
    facade.box('door_main_transom','wood',center,spring,width,.095,.18,.025)
    facade.box('door_leaf_back','wood_dark',center,1.33,width,2.59,.06,-.08)
    for sign in [-1,1]:
        facade.box('door_outer_jamb','wood',center+sign*r,1.34,.09,2.62,.18,.025)
    # Main portal double doors; side openings remain glazed rather than invented rooms.
    leaves=2 if is_main else 1
    for leaf in range(leaves):
        span=width/leaves;cx=center-width/2+(leaf+.5)*span
        facade.box('door_glazed_panel','glass',cx,1.97,span-.13,1.18,.028,-.033)
        for sign in [-1,1]:facade.box('door_stile','wood',cx+sign*(span-.055)/2,1.35,.065,2.58,.13,.012)
        for z in [.11,1.29,2.60]:facade.box('door_rail','wood',cx,z,span,.11,.13,.020)
        # Raised lower panels have four profiled frame strips and a recessed field.
        facade.box('raised_door_panel','wood',cx,.68,span-.19,.88,.055,-.004)
        for sign in [-1,1]:facade.box('panel_bead','wood_dark',cx+sign*(span-.19)/2,.68,.025,.91,.035,.031)
        for z in [.24,1.12]:facade.box('panel_bead','wood_dark',cx,z,span-.16,.026,.035,.031)
        if is_main:facade.box('door_brass_pull','gold',cx+(.19 if leaf==0 else -.19),1.18,.034,.30,.085,.093)
    if is_main:
        facade.box('letter_plate','gold',center,.89,.29,.075,.05,.09)
        facade.label('3',center,2.92,.29,'metal',.00)
        facade.label('LINCOLN CHAMBERS',center,2.74,.095,'metal',.003)

arched_leaf(back,back.length/2,1.54,True)
arched_leaf(left,left.length/2,left.length-.24)
arched_leaf(right,right.length/2,right.length-.24)
# Header, deep soffit and profiled cornice sit above the open vestibule.
front.box('porch_header_stone','stone',x0,3.85,4.32,.62,.62,-.10)
front.box('mosaic_name_field','green',x0,3.88,3.83,.47,.032,.235)
for z,w,h,d in [(3.55,4.37,.075,.66),(4.18,4.49,.11,.72),(4.29,4.62,.10,.82)]:front.box('header_cornice','stone',x0,z,w,h,d,.03)
front.label('LINCOLN CHAMBERS',x0,3.735,.30,'gold',.26)
# Stylised shallow volutes follow the photographed scroll silhouette; profiles estimated.
for sign in [-1,1]:
    cx=x0+sign*2.00
    points=[]
    for i in range(32):
        angle=i*math.pi*1.7/31;r=.04+.16*i/31
        points.append((cx+sign*r*math.cos(angle),3.99+r*math.sin(angle)))
    for a,b in zip(points,points[1:]):
        dx,dz=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dz)
        normal=Vector((-dz/length,dx/length))*.045
        front.group('header_scroll','stone').add([front.point(x+sx*normal.x,z+sx*normal.y,d) for d in [.25,.34] for (x,z),sx in [(a,-1),(b,-1),(b,1),(a,1)]],[(0,1,2,3),(4,7,6,5),(0,4,5,1),(3,2,6,7)])
# Soffit follows the splayed plan, no wall or glass plane blocks the entrance.
plan=[(x0-opening_half,0),(x0+opening_half,0),(x0+.98,back_depth),(x0-.98,back_depth)]
front.group('porch_soffit','cream').add([front.point(x,3.535,d) for x,d in plan],[(0,1,2,3)])
# Checker tiles clipped to the trapezoid; this is a shallow exterior threshold only.
# Clip each square against the two sloping porch sides.
def clip_polygon(poly,side):
    def value(p):
        x,d=p;half=opening_half+(opening_half-.98)*d/1.30
        return half-side*(x-x0)
    result=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        va,vb=value(a),value(b)
        if va>=-1e-9:result.append(a)
        if (va>=0)!=(vb>=0):
            t=va/(va-vb);result.append((a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])))
    return result
step=.245
for row in range(6):
    da=max(back_depth,-(row+1)*step);db=-row*step
    if db<back_depth:continue
    for col in range(16):
        xa=x0-opening_half+col*step;xb=min(x0+opening_half,xa+step)
        if xa>=x0+opening_half:continue
        poly=[(xa,da),(xb,da),(xb,db),(xa,db)]
        for side in [-1,1]:poly=clip_polygon(poly,side) if poly else []
        if len(poly)>2:front.group('checker_floor','cream' if (row+col)%2 else 'tile_green').add([front.point(x,.075,d) for x,d in poly],[tuple(range(len(poly)))])
front.box('stone_step','cream',x0,.025,4.06,.05,.48,.20)
front.box('door_saddle','gold',x0,.09,1.58,.05,.21,back_depth+.035)
front.box('entry_plaque','metal',x0-2.05,2.24,.26,.39,.05,.095)
front.box('entry_plaque_red','red',x0-2.05,2.37,.075,.065,.02,.129)
front.label('Lincoln',x0-2.05,2.22,.045,'cream',.128)
front.label('Chambers',x0-2.05,2.15,.039,'cream',.128)
for geometry in groups.values():
    obj=geometry.finish()
    if 'timber_arch' in obj.name or 'header_scroll' in obj.name:
        for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
font_path=Path('/System/Library/Fonts/Supplemental/Georgia.ttf')
if font_path.exists():
    font=bpy.data.fonts.load(str(font_path))
    for obj in collection.objects:
        if obj.type=='FONT' and obj.data.body=='LINCOLN CHAMBERS':obj.data.font=font

bpy.context.view_layer.update()
assert protected_geometry()==before,'Geometry outside Lincoln Chambers changed'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v12.blend'))
record={'code':'LCH','exteriorDirection':[front.n.x,.45,-front.n.y],
        'scope':'Photographed recessed entrance with splayed side arches, timber doors, green name panel and checker floor. Upper envelope retained from the prior approximate study. Dimensions, ornamental profiles and unseen elevations estimated; no verified interior.',
        'reference':profile['reference'],
        'supportingReference':'data/建筑图片/LCH_Lincoln Chambers/01_建筑实拍/exterior_photos_round4_LCH_geograph_2726383.jpg',
        'protectedGeometrySha256':before,'removedGroundComponents':removed,
        'components':sum(g.parts for g in groups.values()),
        'detailView':{'label':'入口细节','position':list(front.point(x0,3.70,9.5)),'target':list(front.point(x0,2.08,-.40)),'fov':42}}
(OUT/'lincoln-manifest.json').write_text(json.dumps({'buildings':[record]},indent=2)+'\n')
print('LINCOLN_REFINEMENT_COMPLETE',record,flush=True)
