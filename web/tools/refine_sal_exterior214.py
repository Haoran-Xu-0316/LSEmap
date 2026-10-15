"""Inspect SAL's native side registration without changing the campus file."""
from pathlib import Path
import hashlib, json, math
import bpy
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/sal-exterior214'
BASE = ROOT / 'result/blender/LSE_campus_detailed_v213.blend'
A = math.radians(24.35)
U = Vector((-math.cos(A), -math.sin(A), 0))
N = Vector((-math.sin(A), math.cos(A), 0))
def local(p):
    return [p.dot(U), p.dot(N), p.z]
def parts(obj):
    adjacency = [[] for _ in obj.data.vertices]
    for edge in obj.data.edges:
        a, b = edge.vertices
        adjacency[a].append(b); adjacency[b].append(a)
    visited = set(); rows = []
    for seed in range(len(adjacency)):
        if seed in visited: continue
        stack = [seed]; visited.add(seed); group = []
        while stack:
            k = stack.pop(); group.append(k)
            for j in adjacency[k]:
                if j not in visited: visited.add(j); stack.append(j)
        coords = [local(obj.matrix_world @ obj.data.vertices[k].co) for k in group]
        bounds = [[min(v[k] for v in coords), max(v[k] for v in coords)] for k in range(3)]
        center = [(a+b)/2 for a,b in bounds]
        if -137 < center[0] < -133:
            rows.append({'bounds':bounds, 'center':center, 'vertices':len(group)})
    return rows
bpy.ops.wm.open_mainfile(filepath=str(BASE))
scene = bpy.data.scenes['00_CAMPUS_COMPLETE']; bpy.context.window.scene = scene
col = bpy.data.collections['SAL_EXTERIOR']
rows = []
for obj in col.all_objects:
    if obj.type != 'MESH': continue
    coords = [local(obj.matrix_world @ Vector(v)) for v in obj.bound_box]
    rows.append({'name':obj.name, 'visible':not obj.hide_render,'bounds':[[min(v[k] for v in coords),max(v[k] for v in coords)] for k in range(3)],'vertices':len(obj.data.vertices),'materials':[m.name if m else None for m in obj.data.materials], 'sideParts':parts(obj) if not obj.hide_render and ('sash' in obj.name or 'glazing' in obj.name or 'wall' in obj.name.lower()) else []})
ring=next(b for b in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings'] if b.get('code')=='SAL')['rings'][0]
(OUT/'inspection.json').write_text(json.dumps({'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'ringLocal':[local(Vector((*p,0))) for p in ring],'objects':rows},indent=2)+'\n')
print('SAL214_INSPECTED', len(rows), flush=True)

import sys
from collections import Counter
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import object_fingerprint

def native_state():
    return {'objects':{o.name:object_fingerprint(o) for o in bpy.data.objects},
            'visibility':{o.name:[o.hide_render,o.hide_viewport] for o in bpy.data.objects},
            'collections':{o.name:sorted(c.name for c in o.users_collection) for o in bpy.data.objects},
            'materials':{m.name:material_state(m) for m in bpy.data.materials},
            'scenes':{s.name:sorted(o.name for o in s.objects) for s in bpy.data.scenes}}

def material_state(material):
    nodes=[]; links=[]
    if material.use_nodes:
        for node in material.node_tree.nodes:
            inputs=[]
            for socket in node.inputs:
                if hasattr(socket,'default_value'):
                    value=socket.default_value
                    try:value=list(value)
                    except TypeError:
                        if not isinstance(value,(str,int,float,bool,type(None))):value=str(value)
                    inputs.append([socket.identifier,value])
            nodes.append([node.name,node.bl_idname,inputs])
        links=sorted([link.from_node.name,link.from_socket.identifier,link.to_node.name,link.to_socket.identifier] for link in material.node_tree.links)
    return [list(material.diffuse_color),material.use_nodes,nodes,links]

state=native_state()
(OUT/'baseline-signatures.json').write_text(json.dumps(state,ensure_ascii=False)+'\n')
trees=[(o,BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(f.vertices) for f in o.data.polygons],all_triangles=False)) for o in col.all_objects if o.type=='MESH' and not o.hide_render and len(o.data.polygons)]
def first_surface(start,direction,distance):
    hits=[]
    for obj,tree in trees:
        hit=tree.ray_cast(start,direction,distance)
        if hit[0] is not None:
            face=obj.data.polygons[hit[2]]
            mat=obj.data.materials[face.material_index] if len(obj.data.materials)>face.material_index else None
            hits.append((hit[3],{'object':obj.name,'point':list(hit[0]),'localPoint':local(hit[0]),'material':mat.name if mat else None,'baseColor':list(mat.diffuse_color) if mat else None}))
    return min(hits,key=lambda h:h[0])[1] if hits else None
checks=[]; groups=[]
for edge,bays,label in [(0,2,'rear-near-charcoal'),(2,7,'recessed-middle-pale'),(4,2,'front-corner-blue')]:
    p,q=[Vector((*ring[k],0)) for k in [edge,edge+1]]
    axis=(q-p).normalized(); normal=Vector((axis.y,-axis.x,0))
    if normal.dot(U)<0:normal=-normal
    subset=[]
    for bay in range(bays):
        for z in [7.3,11.65,15.85]:
            for shift in [-1.055,1.055]:
                start=p+axis*((q-p).length*(bay+.5)/bays+shift)+Vector((0,0,z))+normal*.8
                record={'block':label,'bay':bay,'height':z,'firstSurface':first_surface(start,-normal,2)}
                checks.append(record);subset.append(record)
    groups.append({'label':label,'edge':edge,'length':(q-p).length,'bayCount':bays,'upperWindowCount':bays*3,'rowCenters':[7.3,11.65,15.85],'windowHeight':[3.45,3.35,3.35],'frameMaterialHits':dict(Counter(r['firstSurface']['material'] if r['firstSurface'] else None for r in subset))})
roof_checks=[]
for label,depth in [('near',26.4),('middle',42.25),('front',58.1)]:
    roof_checks.append({'block':label,'depth':depth,'sampleLocalX':-138.5,'hit':first_surface(U*-138.5+N*depth+Vector((0,0,50)),Vector((0,0,-1)),60)})
assert all(r['firstSurface'] for r in checks)
assert native_state()==state

# Render one current native view; the unresolved registration warrants no unchanged after render.
# No full-model file or guessed component is produced.
def render_review(filename):
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
    assert native_state()==state
    col=bpy.data.collections['SAL_EXTERIOR']; visible={o.name for o in col.all_objects}
    for obj in scene.objects:
        if obj.type in {'MESH','FONT','CURVE'} and obj.name not in visible:obj.hide_render=True
        if obj.type=='LIGHT':obj.hide_render=True
    world=bpy.data.worlds.new('SAL214_review_world');world.use_nodes=True
    world.node_tree.nodes['Background'].inputs['Color'].default_value=(.8,.8,.8,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=.7
    scene.world=world
    sun_data=bpy.data.lights.new('SAL214_review_sun','SUN');sun_data.energy=1.7;sun_data.angle=.1
    sun=bpy.data.objects.new(sun_data.name,sun_data);scene.collection.objects.link(sun)
    sun.rotation_euler=(math.radians(25),math.radians(-20),math.radians(-30))
    focus=U*-135.2+N*42.25+Vector((0,0,12))
    cd=bpy.data.cameras.new('SAL214_review_camera');camera=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(camera)
    camera.location=focus+U*80-N*18+Vector((0,0,6))
    camera.rotation_euler=(focus-camera.location).to_track_quat('-Z','Y').to_euler()
    cd.type='ORTHO';cd.ortho_scale=48;scene.camera=camera
    scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True
    scene.render.resolution_x=1000;scene.render.resolution_y=850;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/filename)
    scene.view_settings.view_transform='AgX'
    bpy.ops.render.render(write_still=True)
render_review('current-side.png')
bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
assert native_state()==state
base_hash=hashlib.sha256(BASE.read_bytes()).hexdigest()
assert base_hash=='31b15a84a0080a69db300183d107d51cddc019a9b54a6aed609e6ab050222bbb'
audit={'code':'SAL','version':214,'decision':'unresolved-side-massing-no-guessed-component','baseline':str(BASE.relative_to(ROOT)),'baselineSha256':base_hash,'targetCollection':'SAL_EXTERIOR','componentPath':None,'componentSha256':None,'addedObjects':[],'archivedObjects':[],'changedObjects':[],
'finding':'The native side already contains charcoal near and pale recessed-middle frames. A four-row 2/7/2-bay shell still does not establish the photographed side block heights, bay intervals or roof breaks. Repeating the old palette correction would add no new supported correction.',
'nativeBlockGroups':groups,'firstSurfaceChecks':checks,'roofSurfaceChecks':roof_checks,
'quantitativeIncompatibility':{'nativeSideLengthM':61.151100158691406-23.396469116210938,'middleRecessM':.46,'registeredNativeBaySequence':[2,7,2],'registeredNativeUpperRows':3,'nativeSideWindowCountIncludingGround':44,'nativeUniformMainWallTopM':18.15,'nativeUniformMainRoofRidgeM':22.65,'photoMeasuredCorrespondingBayCounts':None,'photoMeasuredCorrespondingBlockHeights':None,'photoToNativeDepthRegistration':'No measured side elevation or repeatable camera solve; 2/7/2 is a GIS-generated assumption, not a count established by this photograph.'},
'liveSourceCheck':{'date':'2026-10-15','projectUrl':'https://www.jesticowhiles.com/project/lincolns-inn-fields-london-school-of-economics/','status':'Accessible; Year2012,StatusBuilt; side photograph link2393_N32926_high-402x600.jpg opens. LSE Estates32L image opens.','projectYear':2012,'photoCaptureDate':'unknown','current2026ConditionVerified':False},
'references':[{'file':'data/collections/library_round5/photos/SAL_5b39324ea103.jpg','sha256':'5b39324ea1037bd7f153a490d70c20f1756d509b016107f2b11c82af7f710d34','url':'https://www.jesticowhiles.com/wp-content/uploads/2024/01/2393_N32926_high.jpg','evidence':'Completed-building photograph; capture date unknown; perspective and cropping prevent defensible full side height/bay reconstruction.'},{'url':'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Images/LSE-Estate/32L-300x400.jpg','evidence':'Official undated frontage photo; cannot resolve side massing.'}],
'limitations':['The native rear-near/middle/front block correspondence is a footprint-based estimate. Correct first-hit frame colors do not verify the model against the photograph.','Do not infer all eight stated internal floors as exposed side window rows.','Uncalibrated photograph colors do not warrant repeated brick or glazing changes.','No speculative transparency, interior backing, roof massing or extra floor geometry added.'],
'verification':{'nativeFileReopened':True,'objectsVerified':len(state['objects']),'allGeometryUVTransformsMaterialBindingsNodesAndRoomsPreserved':True,'baselineShaUnchanged':True,'fullModelSaved':False,'componentCreated':False,'currentSide':'current-side.png','nativeStateRecheckedAfterRender':True}}
(OUT/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
print('SAL214_UNRESOLVED_NO_COMPONENT',len(checks),len(state['objects']),flush=True)
bpy.ops.wm.quit_blender()
