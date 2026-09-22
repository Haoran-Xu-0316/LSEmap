"""Build edition 04 street details from the archived footprint and photographs.

Run in Blender's Text Editor. The earlier edition and reference archive are read-only.
COL: stone openings, corner cafe and panelled entrance; CON: recessed front portal.
Every unsurveyed dimension and repeated upper bay is an explicit approximation.
"""
from pathlib import Path
from mathutils import Vector, Matrix
from array import array
import bpy
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'result/blender/stage04'
OUTPUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v03.blend'))
main = bpy.data.scenes['00_CAMPUS_COMPLETE']
bpy.context.window.scene = main
site = json.loads((ROOT / 'result/blender/site_geometry.json').read_text())
records = {b['code']: b for b in site['buildings'] if b['code']}
collections = {code: bpy.data.collections[code + '_EXTERIOR'] for code in ('COL', 'CON')}
changed = {o for c in collections.values() for o in c.all_objects}


def digest_untouched():
    digest = hashlib.sha256()
    for obj in sorted((o for o in main.objects if o not in changed and not o.name.startswith(('COL_D4_', 'CON_D4_'))), key=lambda o: o.name):
        digest.update(obj.name.encode())
        digest.update(str(list(obj.matrix_world)).encode())
        if obj.type == 'MESH':
            coordinates = array('f', [0]) * (len(obj.data.vertices) * 3)
            obj.data.vertices.foreach_get('co', coordinates)
            digest.update(coordinates.tobytes())
    return digest.hexdigest()


before = digest_untouched()


def material(name, color, metallic=0, roughness=.65):
    mat = bpy.data.materials.new('STREET_D4_' + name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    node = mat.node_tree.nodes['Principled BSDF']
    node.inputs['Base Color'].default_value = (*color, 1)
    node.inputs['Metallic'].default_value = metallic
    node.inputs['Roughness'].default_value = roughness
    return mat


stone = material('limestone', (.61, .59, .52))
trim = material('cut_stone', (.73, .70, .61))
reveal = material('recessed_stone', (.40, .39, .35))
granite = material('granite_portal', (.39, .40, .38))
frame = material('dark_bronze_frames', (.075, .09, .085), .4, .3)
glass = material('blue_green_glass', (.15, .24, .25), .25, .2)
wood = material('painted_panelled_door', (.095, .07, .075), .1, .45)
brass = material('brass_hardware', (.54, .38, .13), .7, .3)
slate = material('slate_roof', (.16, .19, .21))
black = material('joint_and_recess', (.045, .05, .048))
batches = {}


class Batch:
    """One editable mesh per construction system, rather than thousands of objects."""
    def __init__(self, code, name, mat):
        self.code, self.name, self.mat = code, code + '_D4_' + name, mat
        self.vertices, self.faces, self.parts = [], [], 0

    def shape(self, vertices, faces):
        offset = len(self.vertices)
        self.vertices.extend(vertices)
        self.faces.extend(tuple(offset + i for i in face) for face in faces)
        self.parts += 1

    def box(self, facade, x, depth, z, width, thickness, height):
        vertices = [facade.point(x + dx * width / 2, depth + dy * thickness / 2, z + dz * height / 2)
                    for dx, dy, dz in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]
        self.shape(vertices, [(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)])

    def finish(self):
        mesh = bpy.data.meshes.new(self.name)
        mesh.from_pydata(self.vertices, [], self.faces)
        mesh.materials.append(self.mat)
        mesh.update()
        obj = bpy.data.objects.new(self.name, mesh)
        collections[self.code].objects.link(obj)
        obj['component_count'] = self.parts
        obj['dimension_status'] = 'Photo-informed estimates; not measured construction geometry'
        return obj


def box(code, name, mat, facade, x, depth, z, width, thickness, height):
    key = (code, name)
    if key not in batches:
        batches[key] = Batch(code, name, mat)
    batches[key].box(facade, x, depth, z, width, thickness, height)


class Facade:
    def __init__(self, code, index):
        ring = records[code]['rings'][0]
        self.p = Vector(ring[index])
        self.q = Vector(ring[(index + 1) % len(ring)])
        self.length = (self.q - self.p).length
        self.u = (self.q - self.p).normalized()
        signed = sum(p[0]*q[1] - q[0]*p[1] for p, q in zip(ring, ring[1:] + ring[:1]))
        self.n = Vector((self.u.y, -self.u.x)) * (1 if signed > 0 else -1)
        self.code = code

    def point(self, x, depth, z):
        p = self.p + self.u * x + self.n * depth
        return (p.x, p.y, z)

    def box(self, name, mat, x, depth, z, width, thickness, height):
        box(self.code, name, mat, self, x, depth, z, width, thickness, height)

    def text(self, name, text, x, depth, z, size, mat):
        curve = bpy.data.curves.new(self.code + '_D4_' + name, 'FONT')
        curve.body, curve.size, curve.align_x = text, size, 'CENTER'
        curve.extrude, curve.resolution_u = .008, 3
        curve.materials.append(mat)
        obj = bpy.data.objects.new(curve.name, curve)
        collections[self.code].objects.link(obj)
        # Baseline follows the wall; local up is world Z, face normal points out.
        axis = Vector((-self.n.y, self.n.x, 0))
        obj.matrix_world = Matrix((axis, Vector((0,0,1)), Vector((*self.n,0)))).transposed().to_4x4()
        obj.location = self.point(x, depth, z)


def opening(facade, x, z0, z1, width, ground=False):
    """Real deep jambs surround a recessed pane; no window decal on a solid wall."""
    height = z1 - z0
    for side in (-1, 1):
        facade.box('window_reveals', reveal, x + side*(width/2+.10), -.12, (z0+z1)/2, .20, .62, height+.18)
        facade.box('window_frames', frame, x + side*(width/2-.045), -.35, (z0+z1)/2, .075, .12, height)
    facade.box('recessed_glass', glass, x, -.40, (z0+z1)/2, width-.08, .055, height-.08)
    for z in (z0+.04, z1-.04, z0+height*.69):
        facade.box('window_frames', frame, x, -.30, z, width, .12, .065)
    facade.box('window_frames', frame, x, -.30, (z0+z1)/2, .055, .12, height)
    facade.box('projecting_sills', trim, x, .13, z0-.11, width+.46, .58, .20)
    facade.box('sill_drip_edges', reveal, x, .34, z0-.22, width+.36, .05, .025)
    if not ground:
        facade.box('lintel_mouldings', trim, x, .09, z1+.10, width+.44, .42, .18)


def portal(facade, x, kind):
    col = kind == 'COL'
    width, top = (1.65, 3.55) if col else (1.95, 3.75)
    mat = trim if col else granite
    # Deep side cheeks and a dark entrance pocket retain actual recess depth.
    facade.box('entrance_pocket', black, x, -.83, 1.95, width+.10, .055, 3.65)
    for side in (-1, 1):
        facade.box('portal_piers', mat, x+side*(width/2+.25), -.01, 2.12, .50, 1.02, 4.24)
        if col:
            for dx in (-.10, .10):
                facade.box('portal_reed_mouldings', reveal, x+side*(width/2+.25)+dx, .515, 2.1, .025, .025, 3.95)
    facade.box('portal_name_tablet', trim, x, .07, top+.37, width+.94, .92, .62)
    for z, w, dep in [(top+.72,width+1.16,1.08),(top+.84,width+1.30,1.18)]:
        facade.box('portal_stepped_cornice', trim, x, .10, z, w, dep, .13)
    # Door sits behind the front face, reached by three shallow stone steps.
    for step in range(3):
        facade.box('entrance_steps', granite, x, .25-step*.27, .06+step*.06, width+.18, .34, .12)
    if col:
        facade.box('double_timber_door', wood, x, -.64, 1.63, width-.09, .12, 2.91)
        for side in (-1,1):
            xx=x+side*width/4
            for z,h in [(0.75,.72),(1.7,.72),(2.60,.48)]:
                facade.box('door_raised_panels', wood, xx, -.556, z, width*.36, .065, h)
                for yy in (-1,1):
                    facade.box('door_panel_mouldings', frame, xx, -.51, z+yy*h/2, width*.38, .035, .025)
                for xx2 in (-1,1):
                    facade.box('door_panel_mouldings', frame, xx+xx2*width*.19, -.51, z, .025, .035, h)
            facade.box('door_brass_pushplates', brass, x+side*.12, -.49, 1.40, .065, .05, .29)
        facade.box('door_letterbox', brass, x-.40, -.49, 1.12, .28, .035, .07)
        facade.box('door_top_vent', black, x, -.62, 3.18, width-.18, .06, .36)
        for i in range(7):facade.box('vent_louvres', frame, x, -.55, 3.03+i*.044, width-.22, .07, .016)
        facade.text('portal_name', 'COLUMBIA\nHOUSE', x, .542, top+.38, .18, frame)
    else:
        facade.box('vestibule_glass', glass, x, -.72, 1.55, width-.12, .07, 2.8)
        for xx in (-width/2,0,width/2):facade.box('vestibule_door_frames', brass, x+xx, -.66, 1.57, .055, .09, 2.83)
        for zz in (.19,2.97):facade.box('vestibule_door_frames', brass, x, -.66, zz, width, .09, .065)
        for xx in (-.13,.13):facade.box('door_pull_handles', brass, x+xx, -.54, 1.48, .036, .10, .45)
        facade.box('bronze_fanlight', frame, x, -.26, 3.39, width, .16, .62)
        facade.box('fanlight_glass', glass, x, -.16, 3.39, width-.16, .03, .47)
    facade.box('entry_access_panel', frame, x+width/2+.53, .55, 1.65, .18, .09, .36)
    facade.box('entry_notice', trim, x+width/2+.53, .60, 1.66, .12, .016, .18)


def street_wall(facade, bays, levels, entrance=None, corner=False):
    pitch = facade.length / bays
    for level, (bottom, top) in enumerate(zip(levels, levels[1:])):
        for bay in range(bays):
            x = (bay+.5)*pitch
            is_door = level == 0 and (bay == entrance or corner)
            width = min(1.88 if level else 2.02, pitch*.66)
            sill = bottom + (.60 if level == 0 else .80)
            lintel = top - .65
            if is_door:width,sill,lintel=(1.65 if facade.code=='COL' and not corner else 1.95),.03,3.75
            # Wall fabric is subdivided around the opening, including deep returns.
            for sign in (-1,1):
                pier = (pitch-width)/2
                facade.box('stone_wall_piers', stone, x+sign*(width+pitch)/4, -.08, (bottom+top)/2, pier, .70, top-bottom)
            for z,h in [((bottom+sill)/2,sill-bottom),((lintel+top)/2,top-lintel)]:
                if h>0:facade.box('stone_spandrels', stone, x, -.08, z, width, .70, h)
            if is_door and not corner:portal(facade,x,facade.code)
            else:opening(facade,x,sill,lintel,width,level==0)
            if level < 2:
                # Short real grooves read as rusticated lower stone courses.
                for j in range(1,6):
                    z=bottom+j*(top-bottom)/6
                    if sill<z<lintel:
                        for sign in (-1,1):
                            facade.box('rustication_recesses', reveal, x+sign*(width+pitch)/4, .278, z, (pitch-width)/2-.07, .012, .024)
                    else:facade.box('rustication_recesses', reveal, x, .278, z, pitch-.045, .012, .024)
        if level in (1,5,6):
            for dz,thickness,projection in [(0,.22,.62),(.16,.12,.82)]:
                facade.box('continuous_cornices', trim, facade.length/2, .15, top+dz, facade.length+.13, projection, thickness)
    facade.box('roof_parapet', stone, facade.length/2, -.03, levels[-1]+.42, facade.length, .52, .68)
    facade.box('parapet_coping', trim, facade.length/2, -.03, levels[-1]+.8, facade.length+.1, .74, .12)
    return pitch


# COL: replace generic flat windows with three photographed street elevations.
for obj in list(collections['COL'].objects):bpy.data.objects.remove(obj, do_unlink=True)
levels=[0,4.8,8.6,12.1,15.6,19.1,22.6,26.1]
for index in range(len(records['COL']['rings'][0])):
    facade=Facade('COL',index)
    if index in (10,11,12):
        bays={10:4,11:1,12:9}[index]
        pitch=street_wall(facade,bays,levels,entrance=1 if index==10 else None,corner=index==11)
        if index==11:
            facade.box('garrick_signboard', trim, facade.length/2, .41, 4.24, facade.length*.89, .20, .52)
            facade.text('garrick_lettering','Garrick',facade.length/2,.525,4.12,.26,frame)
        if index==10:
            facade.text('school_name','The London School of Economics',facade.length/2,.295,8.12,.25,frame)
    else:
        facade.box('unseen_wall_estimate',stone,facade.length/2,-.10,13.1,facade.length,.5,26.2)
# A restrained inset slate roof, using the mapped outline; no claim of surveyed roof geometry.
ring=records['COL']['rings'][0];center=Vector(records['COL']['center'])
roof=Batch('COL','estimated_mansard',slate)
for p,q in zip(ring,ring[1:]+ring[:1]):
    pp=center+(Vector(p)-center)*.78;qq=center+(Vector(q)-center)*.78
    roof.shape([(*p,26.4),(*q,26.4),(*qq,29),(*pp,29)],[(0,1,2,3)])
for tri in records['COL']['triangles']:
    roof.shape([(*(center+(Vector(p)-center)*.78),29) for p in tri],[(0,1,2)])
batches[('COL','estimated_mansard')]=roof

# CON: retain unreviewed walls; rebuild only the photographed Aldwych front.
con=Facade('CON',4)
wall=bpy.data.objects.get('CON_wall_0_4')
if wall:bpy.data.objects.remove(wall,do_unlink=True)
# Existing window systems are disconnected solids. Remove whole connected components
# at the replaced wall, avoiding severed frames and duplicate glass layers.
for obj in list(collections['CON'].objects):
    if obj.type!='MESH' or not obj.name.startswith('CON_EXTERIOR_'):continue
    mesh=obj.data
    parent=list(range(len(mesh.vertices)))
    def find(v):
        while parent[v]!=v:parent[v]=parent[parent[v]];v=parent[v]
        return v
    for edge in mesh.edges:
        a,b=map(find,edge.vertices);parent[b]=a
    components={}
    for v in mesh.vertices:components.setdefault(find(v.index),[]).append(v.index)
    remove=set()
    for indices in components.values():
        points=[obj.matrix_world@mesh.vertices[i].co for i in indices]
        c=sum(points,Vector())/len(points);delta=Vector((c.x,c.y))-con.p
        if -.3<delta.dot(con.u)<con.length+.3 and abs(delta.dot(con.n))<.95:remove.update(indices)
    keep=[v.index for v in mesh.vertices if v.index not in remove];mapping={old:new for new,old in enumerate(keep)}
    faces=[p for p in mesh.polygons if all(i in mapping for i in p.vertices)]
    new=bpy.data.meshes.new(mesh.name+'_retained')
    new.from_pydata([tuple(mesh.vertices[i].co) for i in keep],[],[tuple(mapping[i] for i in p.vertices) for p in faces])
    for mat in mesh.materials:new.materials.append(mat)
    for new_face,old_face in zip(new.polygons,faces):new_face.material_index=old_face.material_index
    obj.data=new
street_wall(con,5,[0,4.8,8.6,12.6,16.6,20.6,24.6,28.5],entrance=2)
con.text('school_name','The London School of Economics',con.length/2,.30,8.08,.25,frame)
for batch in batches.values():batch.finish()
for code,col in collections.items():
    col['detail_phase']=4
    col['evidence']='LSE Estate archived photos; COL additionally LSE 2025/26 property handbook'
    col['limitations']='Street details photo-informed; heights, upper repetition and hidden elevations estimated'


def review_scene(code, facade, overview_position, target, scale):
    scene=bpy.data.scenes.new('12_COL_DETAIL_REVIEW' if code=='COL' else '13_CON_DETAIL_REVIEW')
    scene.collection.children.link(collections[code])
    stage=bpy.data.collections.new(code+'_D4_REVIEW_STAGE');scene.collection.children.link(stage)
    world=bpy.data.worlds.new(code+'_D4_world');world.use_nodes=True
    world.node_tree.nodes['Background'].inputs[0].default_value=(.43,.48,.53,1)
    world.node_tree.nodes['Background'].inputs[1].default_value=.7;scene.world=world
    def camera(name,position,look_at,ortho=None):
        data=bpy.data.cameras.new(name);obj=bpy.data.objects.new(name,data);stage.objects.link(obj)
        obj.location=position;obj.rotation_euler=(Vector(look_at)-obj.location).to_track_quat('-Z','Y').to_euler()
        if ortho:data.type='ORTHO';data.ortho_scale=ortho
        else:data.lens=47
        return obj
    scene.camera=camera(code+'_D4_facade',overview_position,target,scale)
    x=con.length/2 if code=='CON' else facade.length*.375
    camera(code+'_D4_entrance',facade.point(x+.8,11,5),facade.point(x,0,3.0))
    for name,position,energy,size in [('key',(target[0]-15,target[1]-20,38),6500,18),('fill',(target[0]+16,target[1]+5,30),4500,16)]:
        data=bpy.data.lights.new(code+'_D4_'+name,'AREA');data.energy=energy;data.shape='DISK';data.size=size
        obj=bpy.data.objects.new(data.name,data);stage.objects.link(obj);obj.location=position;obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    mesh=bpy.data.meshes.new(code+'_D4_ground');mesh.from_pydata([(-400,-400,-.12),(400,-400,-.12),(400,400,-.12),(-400,400,-.12)],[],[(0,1,2,3)])
    obj=bpy.data.objects.new(mesh.name,mesh);stage.objects.link(obj)
    mesh.materials.append(material(code+'_ground',(.32,.35,.36)))
    scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
    scene.render.resolution_x=1200;scene.render.resolution_y=1400;scene.render.resolution_percentage=100
    scene.view_settings.view_transform='AgX'
    scene.view_layers[0].update()
    return scene


review_scene('COL',Facade('COL',10),(-28,-163,33),(12,-115,13),43)
review_scene('CON',con,(-26,-174,39),(-17,-116,14),49)
assert digest_untouched()==before,'Unrelated geometry changed'
main['detail_phase']=4
main['detailed_buildings']='MAR, SAW, CBG, LRB, CKK, OLD, SAL, CLM, KSW, OCS, PAN, FAW, COL, CON'
report={'version':'04','unchanged_outside_scope':True,'outside_geometry_sha256':before,
        'components':{batch.name:batch.parts for batch in batches.values()},
        'references':['COL/exteriors_lse_estate_004.jpg','COL/small_round5_COL_handbook-000.png','CON/exteriors_lse_estate_005.jpg'],
        'limitations':'COL window rhythm, CON upper facade and all new dimensions are estimates. No complete new interiors.'}
text=bpy.data.texts.new('PHASE04_STREET_DETAIL_EVIDENCE');text.write(json.dumps(report,indent=2))
start = bpy.data.texts['START_HERE_DETAIL_EDITION']
start.clear()
start.write('LSE CAMPUS DETAIL EDITION 04\n\n'
            'Open 00_CAMPUS_COMPLETE for the complete campus. Fourteen buildings contain detail studies.\n'
            'Edition 04 adds COL street elevations and CON entrance detail. Their review scenes are 12 and 13.\n'
            'The five public-interior studies are inherited without geometry changes.\n'
            'COL upper repetition and roof, CON upper front and all new dimensions remain estimates.\n'
            'Other CON walls remain simplified. This is not a measured as-built survey.\n'
            'Read PHASE04_STREET_DETAIL_EVIDENCE for scope and reference records.\n')
bpy.context.window.scene=main
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v04.blend'))
(OUTPUT/'geometry-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('STREET_DETAIL_COMPLETE',sum(batch.parts for batch in batches.values()),'components',flush=True)
