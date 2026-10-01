"""Refine Columbia House's photographed Garrick corner entrance.
Run in Blender Text Editor. Dimensions and finishes are photo estimates.
All originals remain archived; other facades and interiors are preserved.
"""
from pathlib import Path
import array, hashlib, json, shutil
import bpy, bmesh
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage99'; OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v98.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
collection = bpy.data.collections['COL_EXTERIOR']
ring = next(b for b in json.loads((ROOT / 'result/blender/site_geometry.json').read_text())['buildings'] if b['code']=='COL')['rings'][0]
p, q = Vector((*ring[11],0)), Vector((*ring[12],0))
right = (q-p).normalized()
signed = sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ring,ring[1:]+ring[:1]))
normal = Vector((right.y,-right.x,0)) * (1 if signed>0 else -1)
origin = (p+q)/2

def point(x,depth,z): return origin + right*x + normal*depth + Vector((0,0,z))
def fingerprint(obj):
    h=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type=='MESH':
        h.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
        h.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
    if obj.type=='FONT': h.update(str((obj.data.body,obj.data.size,obj.data.font.name,obj.data.extrude)).encode())
    h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return h.hexdigest()
def material(name,color,roughness,metallic=0):
    m=bpy.data.materials.new('COL_V99_'+name); m.diffuse_color=(*color,1); m.use_nodes=True
    shader=m.node_tree.nodes['Principled BSDF']; shader.inputs['Base Color'].default_value=m.diffuse_color
    shader.inputs['Roughness'].default_value=roughness; shader.inputs['Metallic'].default_value=metallic
    return m
before={o.name:fingerprint(o) for o in bpy.data.objects}; added=[]; partial=[]; copies=[]
metal=material('garrick_dark_metal',(.11,.125,.12),.26,.60)
glass=material('garrick_glass',(.14,.17,.16),.17,.04)
glass.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value=.55
glass['webOpacity']=.52
stone=material('garrick_sign_stone',(.45,.46,.435),.82)
red=material('garrick_logo_red',(.65,.008,.025),.40)
white=material('garrick_logo_white',(.91,.91,.88),.58)
steel=material('garrick_handle_steel',(.33,.35,.34),.24,.8)

# Extract whole connected ground-entry components; upper sashes stay untouched.
for name,finish,expected in [('COL_D4_window_frames',metal,6),('COL_D4_recessed_glass',glass,1)]:
    source=bpy.data.objects[name]; bm=bmesh.new(); bm.from_mesh(source.data)
    seen=set(); selected=[]; remaining=[]; count=0
    for seed in list(bm.verts):
        if seed in seen:continue
        component=[]; pending=[seed]; seen.add(seed)
        while pending:
            v=pending.pop(); component.append(v)
            for e in v.link_edges:
                o=e.other_vert(v)
                if o not in seen:seen.add(o);pending.append(o)
        ps=[source.matrix_world@v.co for v in component]
        eligible=all(abs((a-origin).dot(right))<1.10 and -.46<(a-origin).dot(normal)<-.22 and 0<a.z<3.80 for a in ps)
        (selected if eligible else remaining).extend(component)
        if eligible:count+=1
    assert count==expected,(name,count)
    keep=source.copy();keep.data=source.data.copy();keep.name='COL_V99_retained_'+name.removeprefix('COL_');collection.objects.link(keep)
    keep.hide_render=False;keep.hide_set(False)
    source.hide_render=True;source.hide_set(True)
    retained=[list(source.matrix_world@v.co) for v in remaining]
    new=source.copy();new.data=source.data.copy();new.name='COL_V99_corner_'+name.removeprefix('COL_');collection.objects.link(new)
    new.hide_render=False;new.hide_set(False)
    only=bmesh.new();only.from_mesh(new.data);only.verts.ensure_lookup_table()
    indices={v.index for v in selected}
    bmesh.ops.delete(only,geom=[v for v in only.verts if v.index not in indices],context='VERTS')
    only.to_mesh(new.data);only.free();new.data.materials.clear();new.data.materials.append(finish)
    bmesh.ops.delete(bm,geom=selected,context='VERTS');bm.to_mesh(keep.data);bm.free()
    added.extend([keep.name,new.name]);partial.append({'source':name,'retained':keep.name,'corner':new.name,'components':count,'retainedVertices':retained})

# Retain the original stone board dimensions and support position.
source=bpy.data.objects['COL_D4_garrick_signboard'];board=source.copy();board.data=source.data.copy();board.name='COL_V99_garrick_signboard';collection.objects.link(board)
board.data.materials[0]=stone;source.hide_render=True;source.hide_set(True);board.hide_render=False;board.hide_set(False);added.append(board.name);copies.append({'source':source.name,'copy':board.name})
source=bpy.data.objects['COL_D4_garrick_lettering'];letters=source.copy();letters.data=source.data.copy();letters.name='COL_V99_garrick_lettering';collection.objects.link(letters)
letters.data.body='garrick';letters.data.size=.33;letters.data.materials[0]=metal
letters.matrix_world.translation=point(-.22,.537,4.12)
source.hide_render=True;source.hide_set(True);letters.hide_render=False;letters.hide_set(False);added.append(letters.name)

# Viewer-left on this clockwise facade is the positive frontage direction.
bm=bmesh.new();result=bmesh.ops.create_cube(bm,size=1)
for v in result['verts']:
    x,d,z=v.co;v.co=point(.82+x*.38,.526+d*.032,4.25+z*.38)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
mesh=bpy.data.meshes.new('COL_V99_logo_badge_mesh');bm.to_mesh(mesh);bm.free()
badge=bpy.data.objects.new('COL_V99_logo_badge',mesh);collection.objects.link(badge);mesh.materials.append(red);added.append(badge.name)
logo=bpy.data.objects['OLD_LSE_entry_sign'].copy();logo.data=logo.data.copy();logo.name='COL_V99_logo_lettering';collection.objects.link(logo)
logo.data.size=.34;logo.data.align_x='CENTER';logo.data.materials.clear();logo.data.materials.append(white)
logo.matrix_world=letters.matrix_world.copy();logo.matrix_world.translation=point(.82,.549,4.095)
logo.hide_render=False;logo.hide_set(False)
# Fit the actual glyph bounds, including this font's descenders, inside the badge.
bpy.context.view_layer.update()
bounds=[Vector(corner) for corner in logo.bound_box]
width=max(v.x for v in bounds)-min(v.x for v in bounds)
height=max(v.y for v in bounds)-min(v.y for v in bounds)
logo.data.size*=min(.29/width,.29/height)
bpy.context.view_layer.update()
bounds=[Vector(corner) for corner in logo.bound_box]
center=Vector(((min(v.x for v in bounds)+max(v.x for v in bounds))/2,(min(v.y for v in bounds)+max(v.y for v in bounds))/2,0))
logo.matrix_world.translation=point(.82,.549,4.25)-logo.matrix_world.to_3x3()@center
added.append(logo.name)

# Slim pull handles stand proud of the retained central door frame.
bm=bmesh.new()
for x in [-.13,.13]:
    made=bmesh.ops.create_cone(bm,cap_ends=True,cap_tris=False,segments=12,radius1=.013,radius2=.013,depth=.42)
    for v in made['verts']:v.co+=point(x,-.20,1.32)
    for z in [1.13,1.51]:
        made=bmesh.ops.create_cube(bm,size=1)
        for v in made['verts']:
            dx,dd,dz=v.co;v.co=point(x+dx*.026,-.23+dd*.06,z+dz*.026)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
mesh=bpy.data.meshes.new('COL_V99_handle_mesh');bm.to_mesh(mesh);bm.free()
handles=bpy.data.objects.new('COL_V99_pull_handles',mesh);collection.objects.link(handles);mesh.materials.append(steel);added.append(handles.name)
assert all(fingerprint(bpy.data.objects[n])==h for n,h in before.items())
for name in ['room-studies.json','room-spaces.json','building-review.json']:shutil.copyfile(ROOT/'result/blender/stage98'/name,OUT/name)
audit={'version':99,'baseline':98,'originalFingerprints':before,'frame':{'origin':list(origin),'right':list(right),'outward':list(normal)},'partialCopies':partial,'copies':copies,'addedObjects':added,
       'reference':'data/建筑图片/COL_Columbia House/01_建筑实拍/exteriors_lse_estate_004.jpg','referenceUrl':'https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/lse-estate','captureDate':None,
       'scope':'Corner entrance finish, paired pull handles and red LSE badge beside lowercase Garrick name. Aperture, stone architecture, main timber entry, upper windows, roof and interiors retained. Existing native LSE lettering reused; no source photo textures.',
       'limits':['Dimensions, handle form and optical finish estimated from an undated photo','Upper elevations, whole roof and complete interiors remain unresolved']}
(OUT/'garrick-corner-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v99.blend'))
print('GARRICK_CORNER_SAVED',len(added))
