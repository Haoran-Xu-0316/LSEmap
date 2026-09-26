"""Review eleven remaining campus envelopes; add only observable missing features.

Open in Blender's Text Editor. The v18 source and all existing geometry/materials
are preserved. Output is an append-only v19 batch, not a claim of full survey.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import sys
import bpy
from mathutils import Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, Facade, materials
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage19/remaining'
OUT.mkdir(parents=True, exist_ok=True)
CODES = ['61A', '5LF', '35L', '49L', '50L', '51L', 'PAR', 'POR', 'SAR', 'SHF', 'STC']
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v18.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
bpy.context.view_layer.update()
originals = list(bpy.data.objects)

def digest(objects):
    value = hashlib.sha256()
    for obj in sorted(objects, key=lambda item: item.name):
        value.update(obj.name.encode())
        value.update(array.array('f', [v for row in obj.matrix_world for v in row]).tobytes())
        if obj.type != 'MESH':
            continue
        coords = array.array('f', [0]) * (len(obj.data.vertices) * 3)
        obj.data.vertices.foreach_get('co', coords)
        value.update(coords.tobytes())
        value.update('|'.join(m.name if m else '' for m in obj.data.materials).encode())
    return value.hexdigest()

before = digest(originals)
refs = {r['code']: r['reference'] for r in json.loads((ROOT / 'result/blender/stage16/review/references.json').read_text())}
profiles = {p['code']: p for p in json.loads((ROOT / 'result/blender/stage05/infill-geometry.json').read_text())}
for name, color in {'stone': (.56,.51,.41), 'pale_stone': (.65,.62,.54), 'shadow': (.12,.11,.09), 'wood': (.29,.13,.055), 'black': (.028,.031,.029), 'clay': (.36,.19,.105)}.items():
    mat = bpy.data.materials.new('V19_REM_' + name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    shader = mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = mat.diffuse_color
    shader.inputs['Roughness'].default_value = .72
    materials[name] = mat

def facade(code):
    profile = profiles[code]
    return Facade(profile, next(w for w in profile['walls'] if w['front']), {})

def circle(f, name, mat, x, z, radius, thickness, depth):
    """Full circular relief with a real annular section."""
    group = f.group(name, mat)
    for i in range(32):
        a, b = i*math.tau/32, (i+1)*math.tau/32
        points = [f.point(x+r*math.cos(t), z+r*math.sin(t), d)
                  for d in [depth-.035, depth+.035]
                  for r,t in [(radius,a),(radius,b),(radius+thickness,b),(radius+thickness,a)]]
        group.add(points, [(0,1,2,3),(4,7,6,5),(0,4,5,1),(3,2,6,7),(1,5,6,2),(0,3,7,4)])

builds = {}
# No.50: archived front photograph shows circular spandrel ornaments and a
# panelled timber door. Preserve the already-corrected 2022 block-plan envelope.
profile = next(p for p in json.loads((ROOT / 'result/blender/stage08/coopers-geometry.json').read_text())['profiles'] if p['code']=='50L')
p,q = map(Vector, [profile['ring'][5],profile['ring'][0]])
u=(q-p).normalized(); n=Vector((u.y,-u.x))
if n.dot((p+q)/2-Vector(profile['center']))<0:n=-n
f=Facade(profile, {'p':list(p),'q':list(q),'length':(q-p).length,'outward':list(n)}, {})
count=max(2,round(f.length/2.8));pitch=f.length/count;x=(count-.5)*pitch;width=min(1.55,pitch*.72)
for sign in [-1,1]:
    xx=x+sign*(width/2+.34)
    circle(f,'portal_roundel_rim','stone',xx,2.96,.19,.075,.14)
    # Dark circular inset, not a rectangular applique covering masonry.
    f.group('portal_roundel_recess','shadow').add([f.point(xx,2.96,.135)]+[f.point(xx+.19*math.cos(i*math.tau/32),2.96+.19*math.sin(i*math.tau/32),.135) for i in range(33)],[(0,i+1,i+2) for i in range(32)])
    f.box('portal_impost','stone',x+sign*(width/2+.10),2.66,.34,.105,.40,.11)
# Six raised timber panels stay inside the existing door opening.
for sign in [-1,1]:
    xx=x+sign*width*.23
    for z,h in [(.48,.57),(1.10,.46),(2.03,.66)]:
        for side in [-1,1]:
            f.box('door_panel_moulding','wood',xx+side*width*.18,z,.035,h,.035,-.125)
            f.box('door_panel_moulding','wood',xx,z+side*h/2,width*.36,.035,.035,-.125)
        f.box('door_panel_field','wood',xx,z,width*.30,h-.08,.022,-.145)
# Header's projecting upper cap and three short brackets observed over the arch.
f.box('portal_header_cap','stone',x,3.79,width+.86,.075,.60,.20)
for dx in [-.35,0,.35]:f.box('portal_header_brackets','stone',x+dx,3.48,.10,.22,.32,.17)
builds['50L']=(f,Vector(f.point(x,1.9,0)),5.1,['Circular stone spandrel ornaments with recessed centres','Six raised timber door panels and projecting header cap'])

# No.51: small entrance details only; upper storey proportions still estimated.
f=facade('51L');x=f.length/2;width=min(2.1,f.length*.45)
for sign in [-1,1]:
    xx=x+sign*(width/2+.16)
    f.box('portal_pilaster_plinth','pale_stone',xx,.25,.41,.38,.53,.14)
    f.box('portal_pilaster_capital','pale_stone',xx,3.12,.47,.15,.57,.15)
    for dx in [-.064,.064]:f.box('portal_pilaster_reed','pale_stone',xx+dx,1.66,.030,2.30,.05,.325)
    f.box('door_lower_panel','wood',x+sign*width*.24,.44,width*.31,.38,.035,.11)
builds['51L']=(f,Vector(f.point(x,1.8,0)),5.0,['Entrance pilaster plinths and capitals','Fine vertical stone profiles and lower door panels'])

# Sardinia House: the reference establishes a strongly projecting dentilled
# horizontal course, absent from the initial uniformly spaced window study.
f=facade('SAR');course=profiles['SAR']['height']/profiles['SAR']['floors']*2
for z,w,h,dep,off in [(course-.28,f.length,.10,.42,.15),(course+.04,f.length+.10,.14,.64,.21),(course+.18,f.length+.18,.09,.76,.24)]:
    f.box('projecting_dentil_cornice','pale_stone',f.length/2,z,w,h,dep,off)
count=max(2,round(f.length/.32))
for i in range(count):f.box('cornice_dentils','pale_stone',(i+.5)*f.length/count,course-.12,.14,.19,.27,.31)
builds['SAR']=(f,Vector(f.point(f.length/2,course-.1,0)),f.length*1.08,['Layered projecting street cornice with individually spaced dentils'])

# No.5: terminal caps on photographed tall chimney stacks. No assumed interior.
site=json.loads((ROOT/'result/blender/site_geometry.json').read_text())
b=next(b for b in site['buildings'] if b['id']=='way/1184094775');p,q=map(Vector,[b['rings'][0][1],b['rings'][0][2]])
u=(q-p).normalized();n=Vector((u.y,-u.x))
if n.dot((p+q)/2-Vector(b['center']))<0:n=-n
f=Facade({'code':'5LF'},{'p':list(p),'q':list(q),'length':(q-p).length,'outward':list(n)}, {})
for x in [.30,f.length-.30]:
    f.box('chimney_cap','clay',x,15.92,.54,.13,.98,-2)
    for y in [-2.2,-1.8]:
        # Hollow-looking pot top retains the existing solid clay pot below.
        f.box('chimney_pot_opening','shadow',x,16.236,.14,.010,.14,y)
builds['5LF']=(f,Vector(f.point(f.length/2,14.8,-1)),f.length*1.3,['Projecting chimney terminal caps and dark pot openings'])

records=[]
nochange={
 '61A':'Provisional tenancy attribution and approximate massing; no new geometry without a confirmed facade match.',
 '35L':'Only indicative construction hoarding is retained. Historical building photograph cannot establish current workstage.',
 '49L':'Existing shutters, corner canopy, oculus and rustication already represent the archived photograph; no duplicate finish pass.',
 'PAR':'Existing gable, dormers, chimney and entrance were specifically rebuilt from the archive; no defensible missing feature added.',
 'POR':'Existing chamfered bookshop, glazing, roof rails and street plaques were specifically rebuilt; no duplicate details.',
 'SHF':'Archive has partial oblique frontage and occlusion; reliable large changes require a better reference.',
 'STC':'Existing detailed entry, landings and attic remain; mural content is deliberately not invented.'}
for code in CODES:
    added=[]
    if code in builds:
        f,target,scale,changes=builds[code]
        for family,g in f.groups.items():
            g.name=code+'_V19_REM_'+family
            obj=g.finish();obj['scope']='Archived visible feature; placement and dimensions estimated; no interior claim.'
            assert len(obj.data.vertices)>0 and all(math.isfinite(v) for p in obj.data.vertices for v in p.co)
            assert all(d>0 for d in obj.dimensions),obj.name
            added.append({'name':obj.name,'collection':code+'_EXTERIOR','components':g.parts})
        status='refined'
        limitations=['Only the photographed street feature is refined. Dimensions and hidden elevations remain estimates. Interior not modeled.', {'50L':'Existing upper arch still contains the earlier masonry spandrel; a true fanlight requires a future opening replacement.', '51L':'The earlier generic doorway and corner envelope are retained; photo-matched pediment and canted entrance require an envelope rebuild.', 'SAR':'The earlier rectangular ground-floor openings are retained; archived arched street windows require a separate facade rebuild.', '5LF':'Roof geometry behind the visible chimney remains estimated.'}[code]]
    else:
        status='reviewed-no-change';changes=[];limitations=[nochange[code]]
    records.append({'code':code,'status':status,'changes':changes,'sources':[refs[code]],'limitations':limitations,'addedObjects':added})
bpy.context.view_layer.update()
assert digest(originals)==before,'Original geometry or material assignment changed'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'refined.blend'))
manifest={'sourceModel':'result/blender/LSE_campus_detailed_v18.blend','output':'result/blender/stage19/remaining/refined.blend','protectedGeometrySha256':before,'protectedGeometryUnchanged':True,'buildings':records}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

# Independent orthographic close-ups verify appended components are visible in
# context. They render authored geometry only; no source photograph is loaded.
for code,(f,target,scale,changes) in builds.items():
    scene=bpy.data.scenes.new('V19_REM_REVIEW_'+code);scene.collection.children.link(bpy.data.collections[code+'_EXTERIOR']);bpy.context.window.scene=scene
    camera=bpy.data.objects.new(code+'_V19_REM_review_camera',bpy.data.cameras.new(code+'_V19_REM_review_camera'));scene.collection.objects.link(camera)
    camera.location=target+Vector((f.n.x*30,f.n.y*30,3));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=scale;scene.camera=camera
    scene.world=bpy.data.worlds.new(code+'_V19_REM_studio');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.6,.66,.72,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.8
    sun=bpy.data.objects.new(code+'_V19_REM_sun',bpy.data.lights.new(code+'_V19_REM_sun','SUN'));scene.collection.objects.link(sun);sun.data.energy=2;sun.rotation_euler=(.5,-.45,-.5)
    scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.use_denoising=True;scene.render.resolution_x=760;scene.render.resolution_y=760;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/(code.lower()+'-review.png'));scene.view_settings.view_transform='AgX'
    bpy.context.view_layer.update();bpy.ops.render.render(write_still=True)
    print('REMAINING_REVIEW_RENDERED',code,flush=True)
print('REMAINING_COMPLETE',len(records),sum(len(r['addedObjects']) for r in records),flush=True)
