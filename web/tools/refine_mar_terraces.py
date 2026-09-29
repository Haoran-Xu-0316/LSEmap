"""Develop the photo-supported north MAR roof terraces from the fin candidate.

Open in Blender's Text Editor. Estimated terrace details follow the attributed
Kane 03, 07 and 08 photographs. No source images are embedded in the model.
"""
from pathlib import Path
import array, hashlib, json, math, sys
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage25'
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials

def digest(obj):
    values=array.array('f',[0])*(3*len(obj.data.vertices))
    obj.data.vertices.foreach_get('co',values)
    return hashlib.sha256(values.tobytes()+str([tuple(p.vertices)for p in obj.data.polygons]).encode()+str(list(obj.matrix_world)).encode()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v24.blend'))
before={o.name:digest(o)for o in bpy.data.objects if o.type=='MESH'}
bpy.ops.wm.open_mainfile(filepath=str(OUT/'MAR_upper_screen_candidate.blend'))
D=json.loads((ROOT/'result/blender/stage02/detail_geometry.json').read_text())
cx,cy=D['mar_center'];angle=math.radians(22);c,s=math.cos(angle),math.sin(angle)
def point(x,y,z):return (cx+c*x-s*y,cy+s*x+c*y,z)
def local(p):return ((p[0]-cx)*c+(p[1]-cy)*s,-(p[0]-cx)*s+(p[1]-cy)*c)
roof=next(o for o in bpy.data.objects if 'MAR_floor_way/1376078543_35.6' in o.name)
assert all(abs((roof.matrix_world@v.co).z-35.6)<.01 for v in roof.data.vertices)
# The existing floor at 34.8m supports a thin terrace finish beneath the screen head.
for v in roof.data.vertices:v.co.z-=.77
roof.data.update()

def material(key,color,roughness=.8,metallic=0):
    m=bpy.data.materials.new('MAR25_'+key);m.use_nodes=True;m.diffuse_color=(*color,1)
    node=m.node_tree.nodes.get('Principled BSDF');node.inputs['Base Color'].default_value=(*color,1)
    node.inputs['Roughness'].default_value=roughness;node.inputs['Metallic'].default_value=metallic
    materials[key]=m
material('paving',(.53,.51,.45));material('joints',(.29,.28,.25))
material('planter',(.57,.55,.48));material('soil',(.075,.06,.038))
material('rail',(.19,.18,.15),.42,.65);material('bark',(.18,.12,.07))
for i,color in enumerate([(.10,.16,.047),(.16,.23,.068),(.21,.28,.085)]):material('leaves'+str(i),color)
roof.data.materials.clear();roof.data.materials.append(materials['joints'])
triangles=[]
for slab in D['slabs']:
    if slab['name']=='MAR_floor_way/1376078543_35.6':triangles += [[local(p)for p in tri]for tri in slab['triangles']]
def inside(x,y):
    for tri in triangles:
        signs=[]
        for a,b in zip(tri,tri[1:]+tri[:1]):signs.append((b[0]-a[0])*(y-a[1])-(b[1]-a[1])*(x-a[0]))
        if min(signs)>=-1e-7 or max(signs)<=1e-7:return True
    return False
groups={}
def group(key,mat):
    if key not in groups:groups[key]=Geometry('MAR','V25_'+key,mat)
    return groups[key]
count=0
for ix in range(-25,21):
    for iy in range(10,35):
        x,y=ix*1.2,iy*.6
        if all(inside(x+dx,y+dy)for dx in [-.6,.6]for dy in [-.3,.3]):
            group('terrace_pavers','paving').box(point(x,y,34.845),(1.194,.594,.03),angle);count+=1
# Photographed guards stand behind the concrete screen, with clear space to the edge.
for x0,x1 in [(-29.5,-15.8),(-1.4,23.4)]:
    for z in [34.98,35.86]:group('terrace_guard_rails','rail').box(point((x0+x1)/2,19.65,z),(x1-x0,.04,.045),angle)
    for i in range(math.ceil((x1-x0)/.12)+1):
        x=x0+i*(x1-x0)/math.ceil((x1-x0)/.12)
        group('terrace_guard_bars','rail').box(point(x,19.65,35.4),(.022,.032,.92),angle)
planters=[(-25,16,3.0,1.4),(-19,11,2.6,1.4),(14,16,3.0,1.4)]
def ellipsoid(g,centre,radii):
    vertices=[];faces=[];rings=8;segments=12
    for i in range(rings+1):
        phi=math.pi*i/rings
        for j in range(segments):
            theta=2*math.pi*j/segments
            vertices.append(point(centre[0]+radii[0]*math.sin(phi)*math.cos(theta),centre[1]+radii[1]*math.sin(phi)*math.sin(theta),centre[2]+radii[2]*math.cos(phi)))
    for i in range(rings):
        for j in range(segments):faces.append((i*segments+j,i*segments+(j+1)%segments,(i+1)*segments+(j+1)%segments,(i+1)*segments+j))
    g.add(vertices,faces)
for index,(x,y,w,d) in enumerate(planters):
    assert all(inside(x+dx,y+dy)for dx in [-w/2,w/2]for dy in [-d/2,d/2])
    for dy in [-d/2,d/2]:group('terrace_planters','planter').box(point(x,y+dy,35.23),(w,.055,.77),angle)
    for dx in [-w/2,w/2]:group('terrace_planters','planter').box(point(x+dx,y,35.23),(.055,d,.77),angle)
    group('terrace_soil','soil').box(point(x,y,35.56),(w-.06,d-.06,.08),angle)
    group('terrace_tree_stems','bark').box(point(x,y,36.35),(.065,.065,1.6),angle)
    for j in range(9):
        t=j*2.399963;dx=.65*math.cos(t);dy=.42*math.sin(t)
        ellipsoid(group('terrace_leaves'+str(j%3),'leaves'+str(j%3)),(x+dx,y+dy,36.85+(j%3)*.30),(.48,.35,.66))
    for j in range(5):ellipsoid(group('terrace_leaves'+str(j%3),'leaves'+str(j%3)),(x-w*.35+j*w*.175,y,35.78),(.40,.40,.26))
added=[]
for g in groups.values():
    obj=g.finish();obj['scope']='Photographed MAR roof-terrace character; heights, planting and layout estimated'
    if 'leaves' in obj.name:
        obj.modifiers.clear()
        for face in obj.data.polygons:face.use_smooth=True
    added.append(obj.name)
after={o.name:digest(o)for o in bpy.data.objects if o.type=='MESH'}
changed=[name for name in before if before[name]!=after[name]]
assert set(changed)=={'MAR_upper_screen_fins',roof.name},changed
assert set(after)-set(before)==set(added)
report={'changedMeshes':changed,'unchangedMeshes':len(before)-len(changed),'addedMeshes':added,'paverCount':count,'sourcePhotos':['MAR_mar_kane_03','MAR_mar_kane_07','MAR_mar_kane_08'],'scope':'North roof-terrace surfaces and partial guards/planting, estimated dimensions. Lower interiors and independent rooms preserved. Rear massing remains provisional.'}
(OUT/'mar-terrace-audit.json').write_text(json.dumps(report,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v25.blend'))
scene=bpy.data.scenes.new('MAR_TERRACE_REVIEW');scene.collection.children.link(bpy.data.collections['MAR_EXTERIOR']);scene.collection.children.link(bpy.data.collections['MAR_PUBLIC_INTERIOR_study']);bpy.context.window.scene=scene
camera=bpy.data.objects.new('MAR25_review_camera',bpy.data.cameras.new('MAR25_review_camera'));scene.collection.objects.link(camera);scene.camera=camera
camera.location=point(-58,106,82);target=Vector(point(-2,1,22));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=80
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.display.shading.background_type='WORLD';scene.world=bpy.data.worlds.new('MAR25_review_world');scene.world.color=(.7,.7,.7)
scene.render.resolution_x=1200;scene.render.resolution_y=1000;scene.render.resolution_percentage=100;scene.render.filepath=str(OUT/'mar-terrace-candidate.png');bpy.ops.render.render(write_still=True)
print(json.dumps(report))
