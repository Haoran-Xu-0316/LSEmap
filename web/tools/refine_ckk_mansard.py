"""Replace CKK's east roof block with the photographed two-tier mansard.

Only the Lincoln's Inn Fields elevation is reconstructed. Dimensions are visual
estimates within the existing GIS envelope; rear pavilion and interiors remain
separate research tasks. Run in Blender's Text Editor without arguments.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import shutil
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage32'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v31.blend'))

def fingerprint(obj):
    v=array.array('f',[0])*(3*len(obj.data.vertices))
    obj.data.vertices.foreach_get('co',v)
    loops=array.array('i',[0])*len(obj.data.loops)
    obj.data.loops.foreach_get('vertex_index',loops)
    return hashlib.sha256(v.tobytes()+loops.tobytes()).hexdigest()

before={o.name:fingerprint(o) for o in bpy.data.objects if o.type=='MESH'}
collection=bpy.data.collections['CKK_EXTERIOR']
removed='CKK_setback_roof_wing.001'
assert removed in collection.objects
bpy.data.objects.remove(bpy.data.objects[removed],do_unlink=True)
site=json.loads((ROOT/'result/blender/site_geometry.json').read_text())
centre=next(b['center'] for b in site['buildings'] if b['code']=='CKK')
angle=math.radians(22)
cosine,sine=math.cos(angle),math.sin(angle)

def world(p):
    x,y,z=p
    return (centre[0]+cosine*x-sine*y,centre[1]+sine*x+cosine*y,z)

def material(name,colour,rough=.65,metal=0):
    mat=bpy.data.materials.new(name)
    mat.use_nodes=True
    mat.diffuse_color=(*colour,1)
    p=mat.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=mat.diffuse_color
    p.inputs['Roughness'].default_value=rough
    p.inputs['Metallic'].default_value=metal
    return mat

slate=material('CKK_V32_blue_grey_slate',(.16,.19,.21),.82)
frame=material('CKK_V32_dormer_zinc',(.12,.14,.15),.48,.35)
glass=material('CKK_V32_dormer_glass',(.24,.30,.32),.18)
stone=material('CKK_V32_cornice_stone',(.66,.64,.58),.78)
# Small regular slate courses, using metric face UVs rather than projected facade UVs.
nodes=slate.node_tree.nodes
brick=nodes.new('ShaderNodeTexBrick')
brick.inputs['Color1'].default_value=(.145,.172,.19,1)
brick.inputs['Color2'].default_value=(.20,.23,.25,1)
brick.inputs['Mortar'].default_value=(.055,.068,.078,1)
brick.inputs['Scale'].default_value=1
brick.inputs['Brick Width'].default_value=.30
brick.inputs['Row Height'].default_value=.20
brick.inputs['Mortar Size'].default_value=.003
uv=nodes.new('ShaderNodeTexCoord')
slate.node_tree.links.new(uv.outputs['UV'],brick.inputs['Vector'])
slate.node_tree.links.new(brick.outputs['Color'],nodes.get('Principled BSDF').inputs['Base Color'])

batches={}
def add(name,mat,vertices,faces):
    bucket=batches.setdefault(name,{'material':mat,'vertices':[],'faces':[]})
    offset=len(bucket['vertices'])
    bucket['vertices'].extend(vertices)
    bucket['faces'].extend(tuple(offset+i for i in face) for face in faces)

def box(name,mat,center,size):
    x,y,z=center;a,b,c=[v/2 for v in size]
    add(name,mat,[(x+dx*a,y+dy*b,z+dz*c) for dx,dy,dz in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]],
        [(0,2,6,4),(1,5,7,3),(0,4,5,1),(2,3,7,6),(0,1,3,2),(4,6,7,5)])

# Front roof: steep slate pitch, short flat crown, solid party/end walls.
profile=[(22,25),(18,32),(14.5,32),(14.5,25)]
vertices=[(x,y,z) for y in [-16.1,16.1] for x,z in profile]
add('CKK_V32_front_mansard',slate,vertices,[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
# The stone cornice and shallow projecting flashing establish the roof's lower edge.
for x,z,depth,height in [(22.1,24.74,.70,.22),(22.18,24.97,.87,.16)]:
    box('CKK_V32_roof_cornice',stone,(x,0,z),(depth,32.4,height))
box('CKK_V32_roof_flashings',frame,(18,0,32.08),(.28,32.4,.13))

rows=[(25.35,28.1),(28.8,31.4)]
for bottom,top in rows:
    for index in range(9):
        y=(index-4)*3.45
        half=.67
        front=22-(bottom-25)*4/7+.16
        back=22-(top-25)*4/7-.08
        # Vertical glazing stands forward of the pitch; cheeks return to the slate.
        box('CKK_V32_dormer_glazing',glass,(front+.012,y,(bottom+top)/2),(.045,2*half,top-bottom))
        for yy in [y-half-.07,y+half+.07]:
            box('CKK_V32_dormer_frames',frame,(front+.04,yy,(bottom+top)/2),(.13,.14,top-bottom+.22))
        for zz in [bottom-.06,top+.06]:
            box('CKK_V32_dormer_frames',frame,(front+.04,y,zz),(.18,2*half+.28,.13))
        box('CKK_V32_dormer_mullions',frame,(front+.055,y,(bottom+top)/2),(.08,.045,top-bottom))
        box('CKK_V32_dormer_caps',frame,((front+back)/2,y,top+.16),(front-back+.23,2*half+.34,.12))
        for yy in [y-half-.11,y+half+.11]:
            add('CKK_V32_dormer_cheeks',frame,[(front,yy,bottom),(front,yy,top+.12),(back,yy,top+.12)],[(0,1,2)])
        box('CKK_V32_dormer_sills',frame,(front+.06,y,bottom-.14),(.26,2*half+.34,.13))

created=[]
for name,batch in batches.items():
    data=bpy.data.meshes.new(name)
    data.from_pydata([world(p) for p in batch['vertices']],[],batch['faces'])
    data.materials.append(batch['material'])
    data.update()
    layer=data.uv_layers.new(name='SurfaceUV')
    for face in data.polygons:
        normal=face.normal.normalized()
        u=Vector((0,0,1)).cross(normal)
        if u.length<1e-6:u=Vector((1,0,0))
        u.normalize();v=normal.cross(u).normalized()
        for loop in face.loop_indices:
            point=data.vertices[data.loops[loop].vertex_index].co
            layer.data[loop].uv=(point.dot(u),point.dot(v))
    obj=bpy.data.objects.new(name,data)
    collection.objects.link(obj)
    obj['source_status']='Photographic front-roof reconstruction; metric dimensions estimated'
    created.append(name)

after={o.name:fingerprint(o) for o in bpy.data.objects if o.type=='MESH'}
assert all(after[name]==value for name,value in before.items() if name!=removed)
for name in ['room-studies.json','room-spaces.json','building-review.json']:
    shutil.copyfile(ROOT/'result/blender/stage31'/name,OUT/name)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v32.blend'))
(OUT/'ckk-mansard-audit.json').write_text(json.dumps({
    'reference':'data/collections/library_round5/photos/CKK_8f06506667f1.jpg',
    'architectSource':'https://grimshaw.global/projects/education-and-science/london-school-of-economics-new-academic-building/',
    'currentWorksSource':'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Cap-Dev/LTM-Campus-Map-25.26-V6.pdf',
    'removed':[removed],'created':created,'unchangedMeshes':len(before)-1,
    'estimates':{'roofBase':25,'roofTop':32,'roofWidth':32.2,'dormerRows':2,'dormersPerRow':9},
    'limitations':'Front roof only. Dimensions estimated. Main facade, rear pavilion and current Cafe54 layout remain unverified. Interiors unchanged.'
},indent=2)+'\n')
print('CKK_MANSARD_COMPLETE',len(created),'batches')
