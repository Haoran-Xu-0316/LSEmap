"""Refine LRB's John Watkins Plaza frontage from daylight photographic evidence.

Run in Blender's Text Editor. Bay widths, levels and entrance position remain
photo-based estimates. The 2008 photograph is not evidence of 2026 access gates.
"""
from pathlib import Path
import array,hashlib,json,math,shutil
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage35';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v34.blend'))
site=json.loads((ROOT/'result/blender/site_geometry.json').read_text());ring=next(b for b in site['buildings'] if b['code']=='LRB')['rings'][0]
origin=Vector((*ring[0],0));end=Vector((*ring[13],0));axis=(end-origin).normalized();normal=Vector((axis.y,-axis.x,0));length=(end-origin).length
collection=bpy.data.collections['LRB_EXTERIOR']
def fingerprint(o):
    v=array.array('f',[0])*(3*len(o.data.vertices));o.data.vertices.foreach_get('co',v)
    i=array.array('i',[0])*len(o.data.loops);o.data.loops.foreach_get('vertex_index',i)
    return hashlib.sha256(v.tobytes()+i.tobytes()).hexdigest()
before={o.name:fingerprint(o) for o in bpy.data.objects if o.type=='MESH'}
changed=[];removed=[]
for obj in list(collection.all_objects):
    if obj.type!='MESH' or 'roof' in obj.name.lower() or obj.name.startswith('LRB_V31_'):continue
    coords=[obj.matrix_world@v.co-origin for v in obj.data.vertices]
    if not coords or max(p.dot(normal) for p in coords)<-.20 or max(p.dot(axis) for p in coords)<0 or min(p.dot(axis) for p in coords)>length:continue
    bm=bmesh.new();bm.from_mesh(obj.data);inv=obj.matrix_world.inverted()
    for point,n in [(origin-normal*.2,normal),(origin,axis),(end,axis)]:
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=inv@point,plane_no=obj.matrix_world.to_3x3().transposed()@n,dist=1e-6)
    faces=[]
    for f in bm.faces:
        p=obj.matrix_world@f.calc_center_median()-origin
        if -.0001<=p.dot(axis)<=length+.0001 and p.dot(normal)>=-.2001:faces.append(f)
    if not faces:bm.free();continue
    bmesh.ops.delete(bm,geom=faces,context='FACES');changed.append(obj.name)
    if not bm.faces:removed.append(obj.name);bm.free();bpy.data.objects.remove(obj,do_unlink=True)
    else:bm.to_mesh(obj.data);bm.free();obj.data.update()

def material(name,rgb,roughness=.7):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*rgb,1);p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=m.diffuse_color;p.inputs['Roughness'].default_value=roughness;return m
stone=material('LRB_V35_light_stone_bands',(.66,.64,.59))
brick=material('LRB_V35_warm_brown_brick',(.29,.15,.105),.86)
glass=material('LRB_V35_neutral_blue_glass',(.19,.245,.26),.17)
frame=material('LRB_V35_graphite_frames',(.09,.105,.105),.45)
base=material('LRB_V35_grey_plinth',(.35,.37,.365),.8)
n=brick.node_tree.nodes;t=n.new('ShaderNodeTexBrick');uv=n.new('ShaderNodeTexCoord');t.inputs['Scale'].default_value=1;t.inputs['Brick Width'].default_value=.225;t.inputs['Row Height'].default_value=.075;t.inputs['Mortar Size'].default_value=.004
for key,rgb in [('Color1',(.25,.125,.085)),('Color2',(.34,.19,.135)),('Mortar',(.32,.29,.245))]:t.inputs[key].default_value=(*rgb,1)
brick.node_tree.links.new(uv.outputs['UV'],t.inputs['Vector']);brick.node_tree.links.new(t.outputs['Color'],n.get('Principled BSDF').inputs['Base Color'])
batches={}
def box(name,mat,p,size):
    b=batches.setdefault(name,{'material':mat,'v':[],'f':[]});offset=len(b['v']);x,y,z=p;a,d,h=[v/2 for v in size]
    b['v'].extend((x+i*a,y+j*d,z+k*h) for i,j,k in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)])
    b['f'].extend(tuple(offset+i for i in f) for f in [(0,2,6,4),(1,5,7,3),(0,4,5,1),(2,3,7,6),(0,1,3,2),(4,6,7,5)])
def wall(name,mat,left,right,bottom,top,depth=.42):
    if right-left>1e-5 and top-bottom>1e-5:box(name,mat,((left+right)/2,-depth/2,(bottom+top)/2),(right-left,depth,top-bottom))

pitch=length/12
rows=[(.65,4.35),(5.5,8.8),(9.85,13.15),(14.2,17.5),(18.55,21.85)]
for bay in range(12):
    left,right=bay*pitch,(bay+1)*pitch
    mat=stone if bay<2 else brick
    openings=[(left+pitch*.5,pitch*.70)] if bay>=2 else [(left+pitch*f,pitch*.21) for f in [.22,.50,.78]]
    previous=0
    for level,(bottom,top) in enumerate(rows):
        wall('LRB_V35_stone_spandrels' if bay<2 else 'LRB_V35_brick_spandrels',mat,left,right,previous,bottom)
        edge=left
        for center,width in openings:
            wall('LRB_V35_stone_piers' if bay<2 else 'LRB_V35_brick_piers',mat,edge,center-width/2,bottom,top)
            wall('LRB_V35_glazing',glass,center-width/2,center+width/2,bottom,top,.06)
            for side in [-1,1]:box('LRB_V35_window_frames',frame,(center+side*(width/2-.04),.07,(bottom+top)/2),(.08,.12,top-bottom))
            for z in [bottom+.04,top-.04]:box('LRB_V35_window_frames',frame,(center,.07,z),(width,.12,.08))
            divisions=3 if bay>=2 and level>0 else 2
            for k in range(1,divisions):box('LRB_V35_window_mullions',frame,(center-width/2+width*k/divisions,.075,(bottom+top)/2),(.055,.13,top-bottom))
            for fraction in ([.6] if level==0 else [.33,.67]):box('LRB_V35_window_transoms',frame,(center,.075,bottom+(top-bottom)*fraction),(width,.13,.055))
            box('LRB_V35_sills',stone,(center,.10,bottom-.09),(width+.15,.32,.13))
            edge=center+width/2
        wall('LRB_V35_stone_piers' if bay<2 else 'LRB_V35_brick_piers',mat,edge,right,bottom,top);previous=top
    wall('LRB_V35_stone_spandrels' if bay<2 else 'LRB_V35_brick_spandrels',mat,left,right,previous,23)
    box('LRB_V35_plinth',base,((left+right)/2,-.20,.29),(right-left,.48,.58))
# Broad pale floor bands form the characteristic warehouse facade rhythm.
for z,h in [(4.85,.52),(9.35,.31),(13.7,.31),(18.05,.31),(22.6,.42)]:
    box('LRB_V35_stone_floor_bands',stone,(length/2,.04,z),(length,.20,h))
box('LRB_V35_cornice',stone,(length/2,.17,22.94),(length,.52,.16))
# A recessed entrance is retained within the first brick bay; gates are not modelled.
entry=pitch*2.5
for x in [entry-.65,entry,entry+.65]:box('LRB_V35_entry_door_frames',frame,(x,.12,1.8),(.075,.16,2.3))
box('LRB_V35_entry_transom',frame,(entry,.12,2.95),(1.38,.16,.1))
for x in [entry-.14,entry+.14]:box('LRB_V35_entry_handles',frame,(x,.22,1.7),(.035,.06,.45))
box('LRB_V35_entry_canopy',frame,(entry,.7,3.3),(2.2,1.45,.13))
created=[]
for name,b in batches.items():
    me=bpy.data.meshes.new(name);me.from_pydata([origin+axis*x+normal*(y+.16)+Vector((0,0,z)) for x,y,z in b['v']],[],b['f']);me.materials.append(b['material']);me.update()
    layer=me.uv_layers.new(name='SurfaceUV')
    for face in me.polygons:
        u=Vector((0,0,1)).cross(face.normal)
        if u.length<1e-6:u=Vector((1,0,0))
        u.normalize();v=face.normal.cross(u).normalized()
        for i in face.loop_indices:
            p=me.vertices[me.loops[i].vertex_index].co;layer.data[i].uv=(p.dot(u),p.dot(v))
    obj=bpy.data.objects.new(name,me);collection.objects.link(obj);obj['source_status']='Photo-informed plaza frontage, dimensions and bay pitch estimated';created.append(name)
after={o.name:fingerprint(o) for o in bpy.data.objects if o.type=='MESH'}
assert all(after.get(name)==value for name,value in before.items() if name not in changed)
for name in ['room-studies.json','room-spaces.json','building-review.json']:shutil.copyfile(ROOT/'result/blender/stage34'/name,OUT/name)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v35.blend'))
(OUT/'library-frontage-audit.json').write_text(json.dumps({'reference':'data/collections/campus_photos_round3/images/LRB/LRB_LAK_geograph_668683.jpg','sourceDate':'2008-01-23','photoPage':'https://www.geograph.org.uk/photo/668683','currentWorksSource':'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Cap-Dev/2025-03-24-CD-Newsletter-FINAL.pdf','photoDirection':112,'changed':changed,'removed':removed,'created':created,'unchangedMeshes':len(before)-len(changed),'length':length,'estimatedBayCount':12,'facadeOffsetForSlabClearance':.16,'scope':'Plaza edge 13 only. Current entry gates, other elevations and perimeter roof remain unverified. Heights, bay pitch and portal position estimated.'},indent=2)+'\n')
print('LIBRARY_FRONTAGE_COMPLETE',len(changed),len(created))
