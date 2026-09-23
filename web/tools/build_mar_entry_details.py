"""Refine MAR's north screen, recessed entrance and forecourt from built photos.

Run inside Blender. Continue from v13: the interrupted POR v14 is kept as a
separate draft and is not integrated. Preserve MAR's existing public hall.
"""
from pathlib import Path
import array, hashlib, json, math, sys
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, Facade, materials
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage15/mar';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v13.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
collection=bpy.data.collections['MAR_EXTERIOR']
D=json.loads((ROOT/'result/blender/stage02/detail_geometry.json').read_text())
cx,cy=D['mar_center'];angle=math.radians(22);c,s=math.cos(angle),math.sin(angle)
def F(x,y,z):return (cx+c*x-s*y,cy+s*x+c*y,z)
def fingerprint(objects):
 digest=hashlib.sha256()
 for obj in sorted(objects,key=lambda o:o.name):
  if obj.type!='MESH':continue
  digest.update(obj.name.encode());digest.update(array.array('f',[v for row in obj.matrix_world for v in row]).tobytes())
  coordinates=array.array('f',[0])*(len(obj.data.vertices)*3);obj.data.vertices.foreach_get('co',coordinates);digest.update(coordinates.tobytes())
 return digest.hexdigest()
protected=[obj for obj in bpy.data.objects if obj not in set(collection.all_objects)]
before=fingerprint(protected)
for name in ['MAR_middle_deep_piers','MAR_entrance_door_frames','MAR_door_pull_handles','MAR_street_vertical_railings','MAR_street_horizontal_rails']:
 obj=bpy.data.objects.get(name)
 if obj:bpy.data.objects.remove(obj,do_unlink=True)
# The previous generic glazing filled the entire entry aperture in front of the
# doors. Remove that pane, its grid and sill so the recessed entrance is reachable.
def local_point(point):
    dx,dy=point.x-cx,point.y-cy
    return Vector((c*dx+s*dy,-s*dx+c*dy,point.z))
removed_entry_parts=0
for name in ['MAR_recessed_window_glass','MAR_window_frames','MAR_window_gaskets','MAR_window_sills']:
    obj=bpy.data.objects.get(name)
    if not obj:continue
    mesh_data=obj.data;links=[[] for _ in mesh_data.vertices]
    for edge in mesh_data.edges:
        a,b=edge.vertices;links[a].append(b);links[b].append(a)
    unseen=set(range(len(mesh_data.vertices)));reject=set()
    while unseen:
        pending=[unseen.pop()];island=set(pending)
        while pending:
            for index in links[pending.pop()]:
                if index in unseen:unseen.remove(index);island.add(index);pending.append(index)
        points=[local_point(obj.matrix_world@mesh_data.vertices[index].co) for index in island]
        center=sum(points,Vector())/len(points)
        if -7.07<center.x<1.58 and 20.34<center.y<20.86 and max(point.z for point in points)<4.61:
            reject.update(island);removed_entry_parts+=1
    if not reject:continue
    keep=[index for index in range(len(mesh_data.vertices)) if index not in reject]
    remap={old:new for new,old in enumerate(keep)}
    faces=[face for face in mesh_data.polygons if not any(index in reject for index in face.vertices)]
    replacement=bpy.data.meshes.new(mesh_data.name+'_open_entry')
    replacement.from_pydata([mesh_data.vertices[index].co[:] for index in keep],[],[[remap[index] for index in face.vertices] for face in faces])
    for material in mesh_data.materials:replacement.materials.append(material)
    for new,old in zip(replacement.polygons,faces):new.material_index=old.material_index
    if mesh_data.uv_layers.active:
        uv=replacement.uv_layers.new(name='MetricUV')
        for new,old in zip(replacement.polygons,faces):
            for ni,oi in zip(new.loop_indices,old.loop_indices):uv.data[ni].uv=mesh_data.uv_layers.active.data[oi].uv
    obj.data=replacement
assert removed_entry_parts>0, 'Old entry obstruction was not identified'
materials.clear()
# Reuse the MAR-only concrete material so new and old structural pieces agree.
concrete=bpy.data.materials.get('MAR_D3_concrete')
assert concrete is not None
materials['concrete']=concrete
colors={'joint':(.16,.155,.14),'bronze':(.16,.12,.083),'metal':(.075,.085,.08),'stone':(.48,.46,.41),'glass':(.30,.39,.40),'lens':(.78,.79,.68),'red':(.59,.012,.025),'white':(.78,.78,.72)}
for name,color in colors.items():
 mat=bpy.data.materials.new('MAR15_'+name);mat.use_nodes=True;mat.diffuse_color=(*color,1)
 shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=mat.diffuse_color;shader.inputs['Roughness'].default_value=.24 if name in {'glass','bronze','metal'} else .72
 if name=='glass':shader.inputs['Transmission Weight'].default_value=.35
 if name=='lens':
  shader.inputs['Emission Color'].default_value=(.92,.85,.65,1);shader.inputs['Emission Strength'].default_value=.3
 materials[name]=mat
groups={}
def group(name,material):
 key=name+'_'+material
 if key not in groups:groups[key]=Geometry('MAR',name,material)
 return groups[key]
def box(name,material,x,y,z,w,d,h):group(name,material).box(F(x,y,z),(w,d,h),angle)
def mesh(name,material,vertices,faces):group(name,material).add([F(*v) for v in vertices],faces)
def tube(name,material,a,b,r=.025,sides=10):
 a,b=Vector(a),Vector(b);axis=(b-a).normalized();ref=Vector((0,0,1)) if abs(axis.z)<.95 else Vector((1,0,0));u=axis.cross(ref).normalized();v=axis.cross(u).normalized()
 points=[p+r*(u*math.cos(j*math.tau/sides)+v*math.sin(j*math.tau/sides)) for p in [a,b] for j in range(sides)]
 mesh(name,material,points,[tuple(range(sides-1,-1,-1)),tuple(range(sides,2*sides))]+[(j,(j+1)%sides,(j+1)%sides+sides,j+sides) for j in range(sides)])

# Twenty bays: a narrow outward edge widens at the rear, giving the photographed
# middle screen real folded reveals instead of uniformly thin rectangular posts.
for j in range(21):
 x=-30+j*2.7
 plan=[(x-.14,21.03),(x+.14,21.03),(x+.79,18.97),(x-.14,18.97)]
 mesh('tapered_middle_blade','concrete',[(xx,yy,z) for z in [12.96,23.22] for xx,yy in plan],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
 # A shallow separation at the floor joint reads at close range without carving false holes.
 box('blade_panel_joint','joint',x,21.034,18.08,.275,.008,.016)
for j in range(20):
 x=-30+j*2.7
 for z in [13.01,23.20]:
  mesh('screen_return_sill','concrete',[(x+.14,21.04,z),(x+2.56,21.04,z),(x+2.56,18.98,z),(x+.79,18.98,z)],[(0,1,2,3)])
# Upper precast fins: subtle panel seams and small visible end fixings.
for j in range(43):
 x=-30+j*54/42
 for z in [27.5,31.55]:box('upper_fin_joint','joint',x,21.004,z,.187,.008,.014)
for x in [-29.7,23.7]:
 for z in [13.04,23.45,35.57]:box('screen_corner_cap','concrete',x,21.02,z,.32,.12,.16)

# Give the existing sloping concrete return a continuous lower cap.
a=Vector((-7.5,20.8,2.1));b=Vector((-1,12.0,5.2));normal=Vector((-(b-a).y,(b-a).x,0)).normalized()*.225
mesh('oblique_return_soffit','concrete',[tuple(p+side*normal+Vector((0,0,dz))) for dz in [0,.20] for p,side in [(a,-1),(b,-1),(b,1),(a,1)]],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(3,7,6,2)])
# Recessed podium glazing lies on two angled planes behind the central aperture.
def glazed_return(name,a,b,low,high,divisions):
 a,b=Vector(a),Vector(b);axis=(b-a).normalized();normal=Vector((-axis.y,axis.x))
 for j in range(divisions):
  p=a+(b-a)*(j+.015)/divisions;q=a+(b-a)*(j+.985)/divisions
  mesh(name+'_pane','glass',[(p.x,p.y,low),(q.x,q.y,low),(q.x,q.y,high),(p.x,p.y,high)],[(0,1,2,3)])
 for j in range(divisions+1):
  p=a+(b-a)*j/divisions
  tube(name+'_mullion','bronze',(p.x,p.y,low),(p.x,p.y,high),.035,8)
 for z in [low,(low+high)/2,high]:tube(name+'_transom','bronze',(*a,z),(*b,z),.037,8)
glazed_return('left_recess_glazing',(-14.8,20.15),(-7.55,13.7),4.91,12.61,5)
glazed_return('right_recess_glazing',(.60,20.05),(-.80,12.2),5.05,12.61,5)
# Slender guards remain across elevated edges, with the ground entrance clear.
for start,end,depth,base in [(-14.8,-7.78,20.42,4.64),(-.75,.66,19.95,4.85)]:
 for j in range(math.ceil((end-start)/.14)+1):
  x=start+(end-start)*j/math.ceil((end-start)/.14)
  tube('podium_guard_bar','metal',(x,depth,base+.05),(x,depth,base+1.07),.014,8)
 for z in [base+.08,base+1.09]:tube('podium_guard_rail','metal',(start,depth,z),(end,depth,z),.025,10)
# A timber/bronze entrance screen tucked behind the oblique return.
for x in [-5.25,-3.95]:
 box('entry_door_glass','glass',x,19.03,1.45,1.22,.025,2.7)
 for xx in [x-.62,x+.62]:box('entry_door_jamb','bronze',xx,19.11,1.45,.065,.13,2.8)
 for z in [.07,2.84]:box('entry_door_rail','bronze',x,19.11,z,1.31,.13,.07)
 box('door_operator','metal',x,19.13,2.93,1.30,.17,.12)
 tube('entry_pull_handle','metal',(x+.42,19.23,1.00),(x+.42,19.23,1.71),.019)
 for k in range(7):
  xx=x-.47+k*.155
  box('glazing_manifestation','white',xx,19.052,1.42,.046,.012,.046)
box('entry_threshold','stone',-4.60,19.13,.065,2.85,.56,.13)
box('entry_recess_mat','joint',-4.6,18.65,.018,2.75,.85,.036)
# Forecourt railings are interrupted at the entrance, replacing the old continuous barrier.
for start,end in [(-30,-8.35),(-.6,24)]:
 count=math.ceil((end-start)/.20)
 for j in range(count+1):
  x=start+(end-start)*j/count
  tube('forecourt_vertical_rail','metal',(x,23.6,.18),(x,23.6,1.28),.014,8)
 for z in [.47,1.30]:tube('forecourt_horizontal_rail','metal',(start,23.6,z),(end,23.6,z),.025,10)
# Four low square lantern piers visible along the Lincoln's Inn Fields boundary.
for x in [-28,-8.3,-.65,22.6]:
 box('forecourt_stone_pier','stone',x,23.6,1.15,.73,.75,2.3)
 box('pier_lantern_lens','lens',x,23.6,2.61,.60,.60,.46)
 for dx in [-.34,.34]:
  for dy in [-.34,.34]:box('lantern_corner_post','metal',x+dx,23.6+dy,2.61,.045,.045,.55)
 for z in [2.32,2.90]:box('lantern_frame','metal',x,23.6,z,.78,.78,.08)
 box('pier_lse_marker','red',x,24.001,1.68,.19,.025,.24)
# Native close-up camera and persistent user-facing entrance preset.
for geometry in groups.values():geometry.finish()
bpy.context.view_layer.update();assert fingerprint(protected)==before
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v15.blend'))
normal=Vector((-s,c))
record={'code':'MAR','exteriorDirection':[normal.x,.50,-normal.y],
 'scope':'Built-photo refinement of the north middle screen, sloping entrance return, recessed podium glazing, balcony guards, entrance doors and lantern forecourt piers. Existing public hall retained. Positions, heights and profiles remain photo-proportion estimates.',
 'reference':'data/建筑图片/MAR_Marshall Building/01_建筑实拍/architecture_round5_MAR_mar_kane_02.jpg',
 'supportingReference':'data/建筑图片/MAR_Marshall Building/01_建筑实拍/exteriors_mar_archdaily_000.jpg',
 'protectedGeometrySha256':before,'removedEntryParts':removed_entry_parts,'components':sum(g.parts for g in groups.values()),
 'detailView':{'label':'入口细节','position':list(F(-5.3,39.0,5.2)),'target':list(F(-5.3,19.8,4.3)),'fov':46}}
(OUT/'mar-manifest.json').write_text(json.dumps({'buildings':[record]},indent=2)+'\n')
print('MAR_ENTRY_REFINEMENT_COMPLETE',record,flush=True)
