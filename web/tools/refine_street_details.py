"""Build edition47's street surfaces and furniture in native Blender geometry."""
from pathlib import Path
import json, math, array, hashlib
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage47'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v46.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
for layer in bpy.context.scene.view_layers:layer.update()
plan=json.loads((OUT/'street-plan.json').read_text())
def fingerprint(obj):
    digest=hashlib.sha256(str([list(r) for r in obj.matrix_world]).encode())
    if obj.type=='MESH':
        digest.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
    return digest.hexdigest()
before={o.name:fingerprint(o) for o in bpy.data.objects}
materials={}
def material(name,color,roughness=.85,metal=0,grain=0):
    m=bpy.data.materials.new('SITE_V47_'+name);m.diffuse_color=(*color,1);m.use_nodes=True
    shader=m.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=m.diffuse_color
    shader.inputs['Roughness'].default_value=roughness;shader.inputs['Metallic'].default_value=metal
    if grain:
        nodes=m.node_tree.nodes;links=m.node_tree.links
        geometry=nodes.new('ShaderNodeNewGeometry');noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=grain
        ramp=nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].color=(*(c*.96 for c in color),1)
        ramp.color_ramp.elements[1].color=(*(c*1.025 for c in color),1)
        bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.20;bump.inputs['Distance'].default_value=.0005
        links.new(geometry.outputs['Position'],noise.inputs['Vector']);links.new(noise.outputs['Fac'],ramp.inputs['Fac'])
        links.new(ramp.outputs['Color'],shader.inputs['Base Color']);links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],shader.inputs['Normal'])
        m['siteDetail']=True
    materials[name]=m
material('grout',(.27,.28,.26))
material('iron',(.11,.13,.14),.72,.32);material('steel',(.36,.40,.42),.50,.65)
material('soil',(.12,.10,.075));material('band',(.71,.70,.63))
for kind,color in [('slab',(.43,.445,.42)),('yorkstone',(.47,.44,.37)),('edge',(.43,.425,.38)),('wood',(.37,.245,.12))]:
    for shade in range(5):material(f'{kind}_{shade}',tuple(c*(.95+shade*.025) for c in color),.88 if kind!='wood' else .74,grain=24 if kind!='wood' else 9)

class MeshGroup:
    def __init__(self,name,collection):self.name=name;self.collection=collection;self.vertices=[];self.faces=[];self.slots=[];self.indices=[]
    def add(self,vertices,faces,mat):
        offset=len(self.vertices);self.vertices.extend(vertices);self.faces.extend(tuple(offset+i for i in f) for f in faces)
        if mat not in self.slots:self.slots.append(mat)
        self.indices.extend([self.slots.index(mat)]*len(faces))
    def triangles(self,triangles,mat,z=.05):
        for tri in triangles:self.add([(p[0],p[1],p[2] if len(p)>2 else z) for p in tri],[(0,1,2)],mat)
    def box(self,center,size,mat,angle=0):
        x,y,z=center;w,d,h=size;c,s=math.cos(angle),math.sin(angle)
        points=[(x+c*a-s*b,y+s*a+c*b,z+t) for t in [-h/2,h/2] for a,b in [(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)]]
        self.add(points,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)
    def ring(self,x,y,r,width,z,mat):
        points=[(x+radius*math.cos(i*math.tau/48),y+radius*math.sin(i*math.tau/48),z) for radius in [r-width/2,r+width/2] for i in range(48)]
        self.add(points,[(i,(i+1)%48,(i+1)%48+48,i+48) for i in range(48)],mat)
    def cylinder(self,x,y,r,z,height,mat):
        points=[(x+r*math.cos(i*math.tau/16),y+r*math.sin(i*math.tau/16),level) for level in [z,z+height] for i in range(16)]
        self.add(points,[tuple(reversed(range(16))),tuple(range(16,32))]+[(i,(i+1)%16,(i+1)%16+16,i+16) for i in range(16)],mat)
    def save(self):
        if not self.faces:return None
        mesh=bpy.data.meshes.new(self.name);mesh.from_pydata(self.vertices,[],self.faces)
        for key in self.slots:mesh.materials.append(materials[key])
        for face,index in zip(mesh.polygons,self.indices):face.material_index=index
        mesh.update();obj=bpy.data.objects.new(self.name,mesh);bpy.data.collections[self.collection].objects.link(obj)
        obj['scope']='Source-guided street study; detailed dimensions and gully positions estimated'
        return obj

hidden=[]
for obj in bpy.data.objects:
    if obj.name.startswith('SITE_V46_') or obj.name.startswith('SITE_V44_') or obj.name.startswith('Public_bench_oak') or obj.name=='03_PUBLIC_REALM_Public_bench_leg':
        obj.hide_render=True;obj.hide_set(True);hidden.append(obj.name)
for record in plan['records']:
    name=record['street'].replace(' ','_');group=MeshGroup('SITE_V47_'+name,'00_SITE')
    group.triangles(record['base'],'grout',.040)
    kind='yorkstone' if record['street']=='Portsmouth Street' else 'slab'
    for tile in record['tiles']:
        group.triangles(tile['top'],f"{kind}_{tile['shade']}")
        group.triangles(tile['bevel'],f"{kind}_{tile['shade']}",.047)
    for border in record['borders']:
        group.triangles(border['top'],f"edge_{border['shade']+1}")
        group.triangles(border['bevel'],f"edge_{border['shade']+1}",.047)
    group.save()

bench=MeshGroup('SITE_V47_Slatted_benches','03_PUBLIC_REALM')
for index,obj in enumerate([bpy.data.objects[n] for n in hidden if n.startswith('Public_bench_oak')]):
    points=[obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    x=(min(p.x for p in points)+max(p.x for p in points))/2
    y=(min(p.y for p in points)+max(p.y for p in points))/2
    xx=sum((p.x-x)**2 for p in points);yy=sum((p.y-y)**2 for p in points);xy=sum((p.x-x)*(p.y-y) for p in points)
    angle=.5*math.atan2(2*xy,xx-yy);c,s=math.cos(angle),math.sin(angle)
    def at(a,b,z):return (x+c*a-s*b,y+s*a+c*b,z)
    for slat in range(5):bench.box(at(0,(slat-2)*.115,.48),(2.8,.105,.055),f'wood_{(slat+index)%5}',angle)
    for offset in [-1.10,0,1.10]:
        bench.box(at(offset,0,.24),(.065,.47,.37),'iron',angle);bench.box(at(offset,0,.433),(.09,.55,.05),'iron',angle)
        for side in [-1,1]:
            bench.box(at(offset,side*.18,.10),(.07,.055,.18),'iron',angle)
            bench.box(at(offset,side*.18,.061),(.16,.11,.016),'iron',angle)
            for bolt in [-.045,.045]:
                bx,by,bz=at(offset+bolt,side*.18,.071)
                bench.cylinder(bx,by,.009,bz,.006,'steel')
bench.save()
fixtures=MeshGroup('SITE_V47_Mapped_street_furniture','03_PUBLIC_REALM')
counts={'tree':0,'bollard':0,'cycle':0}
for item in plan['objects']:
    x,y=item['xy'];kind=item['kind'];counts[kind]+=1
    if kind=='tree':
        fixtures.cylinder(x,y,.69,.040,.004,'soil')
        for radius in [.22,.29,.36,.43,.50,.57,.65]:fixtures.ring(x,y,radius,.016,.050,'iron')
        for i in range(12):
            a=i*math.tau/12;fixtures.box((x+.43*math.cos(a),y+.43*math.sin(a),.048),(.45,.018,.004),'iron',a)
    elif kind=='bollard':
        fixtures.cylinder(x,y,.095,.05,.016,'iron');fixtures.cylinder(x,y,.057,.066,.844,'iron');fixtures.cylinder(x,y,.059,.76,.045,'band');fixtures.ring(x,y,.061,.015,.913,'iron')
    else:
        # Tubular Sheffield-style stand, reconstructed dimensions at the mapped point.
        for dx in [-.34,.34]:fixtures.cylinder(x+dx,y,.028,.05,.66,'steel')
        points=[];segments=16
        for i in range(segments+1):
            a=math.pi*i/segments
            for j in range(8):
                b=math.tau*j/8;r=.34+.028*math.cos(b)
                points.append((x+r*math.cos(a),y+.028*math.sin(b),.71+r*math.sin(a)))
        faces=[(i*8+j,i*8+(j+1)%8,(i+1)*8+(j+1)%8,(i+1)*8+j) for i in range(segments) for j in range(8)]
        fixtures.add(points,faces,'steel')
fixtures.save()
gullies=MeshGroup('SITE_V47_Portsmouth_drainage_study','00_SITE')
for item in plan['gullies']:
    x,y=item['xy'];a=math.radians(item['angle']);c,s=math.cos(a),math.sin(a)
    # A recessed dark sump lies below the open bars, not against their underside.
    gullies.box((x,y,.030),(.60,.42,.006),'iron',a)
    for side in [-1,1]:
        gullies.box((x+c*side*.289,y+s*side*.289,.047),(.022,.42,.006),'steel',a)
    for i in range(12):
        offset=(i-5.5)*.045
        gullies.box((x+c*offset,y+s*offset,.049),(.018,.36,.006),'steel',a)
    for side in [-1,1]:gullies.box((x-s*side*.19,y+c*side*.19,.049),(.58,.028,.006),'steel',a)
gullies.save()
bpy.data.objects['SITE_V45_The_World_Turned_Upside_Down'].location.z=2.05
for layer in bpy.context.scene.view_layers:layer.update()
changed=[name for name,value in before.items() if fingerprint(bpy.data.objects[name])!=value]
assert changed==[],changed
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v47.blend'))
(OUT/'street-audit.json').write_text(json.dumps({'version':47,'baseline':46,'hiddenReplacedObjects':hidden,'changedExistingObjects':changed,'unchangedExistingGeometry':len(before)-len(changed),'mappedFixtures':counts,'gullies':len(plan['gullies']),'pavers':sum(len(r['tiles']) for r in plan['records']),'buildingOverlapArea':plan['buildingOverlapArea'],'limitations':plan['limitations']},indent=2)+'\n')
print('STREET_DETAILS_SAVED',counts)
