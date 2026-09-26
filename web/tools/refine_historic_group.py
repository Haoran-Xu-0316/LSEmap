"""Review ten historic exteriors; add only photographed, currently absent entrance parts.

Open with Blender's Text Editor. Keeps v18 and every existing object untouched.
The output is an append-only transfer blend, not a replacement campus release.
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
OUT = ROOT / 'result/blender/stage19/historic'
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / 'result/blender/LSE_campus_detailed_v18.blend'
CODES = ['OLD','CLM','CON','COL','SAL','KSW','COW','KGS','LAK','LCH']
bpy.ops.wm.open_mainfile(filepath=str(BASE))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
bpy.context.view_layer.update()
originals = list(bpy.data.objects)

def digest(objects):
    h = hashlib.sha256()
    for o in sorted(objects, key=lambda v:v.name):
        h.update(o.name.encode())
        h.update(array.array('f', [v for row in o.matrix_world for v in row]).tobytes())
        if o.type == 'MESH':
            coordinates = array.array('f', [0]) * (len(o.data.vertices)*3)
            o.data.vertices.foreach_get('co', coordinates)
            h.update(coordinates.tobytes())
    return h.hexdigest()

before = digest(originals)
references = {r['code']:r['reference'] for r in json.loads((ROOT/'result/blender/stage16/review/references.json').read_text())}
for key,color,metal in [('stone',(.52,.51,.47),0),('gold',(.62,.43,.12),.6),('bronze',(.12,.10,.055),.55),('dark',(.055,.06,.056),.25),('cream',(.90,.82,.58),0)]:
    m = bpy.data.materials.new('HIST19_'+key)
    m.use_nodes = True
    m.diffuse_color = (*color,1)
    shader=m.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value=m.diffuse_color
    shader.inputs['Roughness'].default_value=.55
    shader.inputs['Metallic'].default_value=metal
    materials[key]=m

records=[]
reviews={
 'OLD':'Entrance arch, rustication, relief, handrails, terrace railings and dormers already present.',
 'CLM':'Timber portals, paired columns, broken pediments, relief silhouettes and dormers already present.',
 'COL':'Recessed stone bays, panelled doors, hardware, cafe frontage and cornices already present.',
 'SAL':'Oriel balconies, Dutch gables, roof lanterns, forecourt railings and pavilion already present.',
 'COW':'Chamfered arched entrance, consoles, dormer pediments, chimneys and dentils already present.',
 'KGS':'Canted bays, broken entrance pediment, fanlight lettering, ribbed dome and finial already present.',
 'LAK':'Street and plaza windows, shopfronts, rainwater pipes, dormers and dentils already present.',
 'LCH':'Three-arch entrance, timber joinery, mosaic fascia, checkerboard porch and hardware already present.',
 'KSW':'Rusticated entrance, carved portal approximation and projecting bay already present; approach lacked the visible lower step run.',
 'CON':'Recessed portal and brass-framed vestibule already present; fanlight badge and vestibule wall light absent.'}
limitations={
 'OLD':'Carved relief remains simplified. Rear elevations, roofs and whole-building interior are not surveyed.',
 'CLM':'Sculptural portal figures are silhouettes. Side and rear geometry is estimated. Separate room sample is outside this task.',
 'COL':'Upper repetition and mansard remain estimates; whole-building interior is absent.',
 'SAL':'Some roof and rear details remain inferred; no whole-building interior.',
 'COW':'Carved figures and unseen elevations remain simplified; no whole-building interior.',
 'KGS':'Shop fit-outs, rear elevation and whole-building interior remain unverified.',
 'LAK':'Roof and upper dormer dimensions remain estimates; no whole-building interior.',
 'LCH':'Rear roof and complete room layouts remain unverified.',
 'KSW':'Step count follows the street photo; tread width and rise fit the existing estimated threshold, not surveyed dimensions.',
 'CON':'Badge is an intentionally simplified shield-and-crown silhouette, not a reproduction of heraldic lettering. Dimensions and vestibule lighting location are approximate.'}

site={r['code']:r for r in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings'] if r['code']}
ring=site['CON']['rings'][0]
p,q=Vector(ring[4]),Vector(ring[5]);u=(q-p).normalized()
sign=1 if sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ring,ring[1:]+ring[:1]))>0 else -1
n=Vector((u.y,-u.x))*sign
congroups={}
con=Facade({'code':'CON'}, {'p':p,'q':q,'length':(q-p).length,'outward':n}, congroups)
x=con.length/2
# The fanlight sits behind the granite portal. Place the relief just in front of its glass.
shield=[(-.16,.12),(.16,.12),(.145,-.07),(.08,-.17),(0,-.225),(-.08,-.17),(-.145,-.07)]
g=con.group('shield_relief','gold')
verts=[con.point(x+dx,3.43+dz,d) for d in [-.13,-.11] for dx,dz in shield]
count=len(shield)
g.add(verts,[tuple(range(count-1,-1,-1)),tuple(range(count,count*2))]+[(i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count)])
con.box('crown_base','gold',x,3.59,.28,.042,.02,-.11)
for dx in [-.105,0,.105]:
    con.box('crown_points','gold',x+dx,3.637,.045,.08,.02,-.11)
# Retain a plain silhouette rather than inventing unreadable heraldic figures.
# Visible warm vertical fitting on the left vestibule reveal in the archive photo.
con.box('vestibule_light_backplate','bronze',x+.92,1.91,.09,.38,.11,-.48)
con.box('vestibule_light_diffuser','cream',x+.92,1.91,.055,.30,.13,-.41)

kswgroups={}
path=json.loads((ROOT/'result/blender/stage03/clm_ksw/build_report.json').read_text())['geometry']['KSW']['frontage_path']
p,q=map(Vector,path);u=(q-p).normalized();n=Vector((-u.y,u.x))
ksw=Facade({'code':'KSW'},{'p':p,'q':q,'length':(q-p).length,'outward':n},kswgroups)
threshold=bpy.data.objects['KSW_D3_door_threshold']
points=[threshold.matrix_world @ v.co for v in threshold.data.vertices]
localx=[(Vector((p.x,p.y))-ksw.wall['p']).dot(ksw.u) for p in points]
locald=[(Vector((p.x,p.y))-ksw.wall['p']).dot(ksw.n) for p in points]
center=(min(localx)+max(localx))/2
width=max(localx)-min(localx)
front=max(locald)
# Preserve the existing .245 m threshold: two lower treads descend to pavement.
for index,height in enumerate([.16,.08]):
    ksw.box('approach_step','stone',center,height/2,width+.10+index*.08,height,.28,front+.14+index*.28)
    ksw.box('step_nosing','stone',center,height-.013,width+.10+index*.08,.026,.035,front+.28+index*.28)

new_objects=[]
for code,groups in [('CON',congroups),('KSW',kswgroups)]:
    for key,group in groups.items():
        group.name=code+'_V19_HIST_'+key
        o=group.finish()
        o['evidence_path']=references[code]
        o['scope']=limitations[code]
        new_objects.append(o)

assert digest(originals)==before, 'Existing native geometry changed'
for code in CODES:
    added=[o for o in new_objects if o.name.startswith(code+'_')]
    records.append({'code':code,'status':'refined' if added else 'reviewed-no-change','review':reviews[code],
      'changes':('Added two approach steps and their stone nosings.' if code=='KSW' else 'Added simplified fanlight shield/crown relief and a vestibule wall light.' if code=='CON' else 'No extra generic facade components added.'),
      'sources':[references[code]],'limitations':limitations[code],
      'addedObjects':[{'name':o.name,'collection':code+'_EXTERIOR'} for o in added]})

# Object-level visibility checks and dedicated close views isolate additions from other campus models.
visibility=[]
for code,facade,targetx in [('CON',con,x),('KSW',ksw,center)]:
    scene=bpy.data.scenes.new(code+'_V19_HIST_REVIEW')
    scene.collection.children.link(bpy.data.collections[code+'_EXTERIOR'])
    world=bpy.data.worlds.new(code+'_V19_HIST_WORLD');world.use_nodes=True
    world.node_tree.nodes['Background'].inputs['Color'].default_value=(.7,.75,.8,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65
    scene.world=world
    cam=bpy.data.objects.new(code+'_V19_HIST_CAMERA',bpy.data.cameras.new(code+'_V19_HIST_CAMERA'))
    scene.collection.objects.link(cam);scene.camera=cam
    cam.location=facade.point(targetx+.7,3.6,8.5)
    target=Vector(facade.point(targetx,2.2,0))
    cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=43
    light=bpy.data.objects.new(code+'_V19_HIST_LIGHT',bpy.data.lights.new(code+'_V19_HIST_LIGHT','AREA'))
    scene.collection.objects.link(light);light.location=facade.point(targetx-2,7,5);light.data.energy=850;light.data.shape='DISK';light.data.size=5
    light.rotation_euler=(target-light.location).to_track_quat('-Z','Y').to_euler()
    scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True
    scene.render.resolution_x=900;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.render.filepath=str(OUT/(code.lower()+'-entrance.png'))
    bpy.context.window.scene=scene;bpy.context.view_layer.update()
    for o in new_objects:
        if not o.name.startswith(code+'_'):continue
        assert o.visible_get() and not o.hide_render
        assert len(o.data.vertices)>0 and all(math.isfinite(v) for p in o.data.vertices for v in p.co)
        visibility.append({'name':o.name,'visible':True,'vertices':len(o.data.vertices)})
    bpy.ops.render.render(write_still=True)

bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
assert digest(originals)==before
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'refined.blend'))
manifest={'baseline':str(BASE.relative_to(ROOT)),'transferBlend':str((OUT/'refined.blend').relative_to(ROOT)),
 'existingGeometryUnchanged':True,'originalGeometrySha256':before,'buildings':records,'visibilityChecks':visibility,
 'scope':'Historical exterior studies. No changes to the three v18 independent room samples.'}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
print('HISTORIC_REFINEMENT_COMPLETE',len(new_objects),flush=True)
