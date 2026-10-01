"""Correct KSW lower red block finish and occluded horizontal joints.
Run in Blender Text Editor. Use owned mesh copies; source geometry and all
other buildings remain intact. Joint registration and depth are photo estimates.
"""
from pathlib import Path
import array, hashlib, json, shutil
import bpy, bmesh
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage90'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v89.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']

def fingerprint(obj):
    digest=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type=='MESH':
        digest.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return digest.hexdigest()

before={obj.name:fingerprint(obj) for obj in bpy.data.objects}
building=next(b for b in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings'] if b['code']=='KSW')
ring=building['rings'][0]
a,b=Vector((*ring[11],0)),Vector((*ring[0],0))
origin,right=(a+b)/2,(b-a).normalized()
normal=Vector((right.y,-right.x,0))
if (origin-Vector((*building['center'],0))).dot(normal)<0:
    normal=-normal

def material(name,color,roughness):
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    mat.diffuse_color=(*color,1)
    shader=mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value=mat.diffuse_color
    shader.inputs['Roughness'].default_value=roughness
    return mat

red=material('KSW_V90_red_block_face',(.43,.105,.063),.79)
red['siteDetail']=True
# Mild granular finish; unlike the upper wall this is not a fine brick grid.
tree=red.node_tree
texture=tree.nodes.new('ShaderNodeTexNoise');texture.inputs['Scale'].default_value=2
ramp=tree.nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].color=(.412,.101,.061,1)
ramp.color_ramp.elements[1].color=(.448,.110,.066,1)
tree.links.new(texture.outputs['Fac'],ramp.inputs['Fac'])
tree.links.new(ramp.outputs['Color'],tree.nodes['Principled BSDF'].inputs['Base Color'])
bump=tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.1
bump.inputs['Distance'].default_value=.00025
tree.links.new(texture.outputs['Fac'],bump.inputs['Height'])
tree.links.new(bump.outputs['Normal'],tree.nodes['Principled BSDF'].inputs['Normal'])
joint=material('KSW_V90_recessed_red_joint',(.19,.044,.027),.88)
levels=[5.45+.53*i for i in range(7)]
half_width=.0225
shoulder=.008
depth=.055
copies=[];hidden=[]
families=['brick_lower_piers','brick_lower_spandrels','brick_window_banded_jambs','brick_flat_arch_voussoirs']
for family in families:
    source=bpy.data.objects['KSW_D3_'+family]
    obj=source.copy();obj.data=source.data.copy()
    obj.name='KSW_D5_rustic90_'+family
    bpy.data.collections['KSW_EXTERIOR'].objects.link(obj)
    obj.data.materials.clear();obj.data.materials.append(red);obj.data.materials.append(joint)
    inverse=obj.matrix_world.inverted()
    local_normal=(obj.matrix_world.transposed().to_3x3()@Vector((0,0,1))).normalized()
    mesh=bmesh.new();mesh.from_mesh(obj.data)
    for z in levels:
        for height in [z-half_width-shoulder,z-half_width,z+half_width,z+half_width+shoulder]:
            plane=inverse@Vector((origin.x,origin.y,height))
            bmesh.ops.bisect_plane(mesh,geom=list(mesh.verts)+list(mesh.edges)+list(mesh.faces),
                                   dist=1e-6,plane_co=plane,plane_no=local_normal,
                                   clear_inner=False,clear_outer=False)
    for vertex in mesh.verts:
        p=obj.matrix_world@vertex.co
        if any(abs(p.z-z)<=half_width+1e-5 for z in levels):
            vertex.co=inverse@(p-normal*depth)
    recessed_faces=0
    for face in mesh.faces:
        heights=[(obj.matrix_world@v.co).z for v in face.verts]
        inside=any(all(abs(h-z)<=half_width+1e-5 for h in heights) for z in levels)
        face.material_index=1 if inside else 0
        recessed_faces+=int(inside)
    bmesh.ops.recalc_face_normals(mesh,faces=list(mesh.faces))
    mesh.to_mesh(obj.data);mesh.free()
    # Preserve the cut shoulders; a generic bevel can cover a narrow groove.
    for modifier in list(obj.modifiers):
        obj.modifiers.remove(modifier)
    obj['scope']='Lower photographed red block courses; groove heights and depth estimated on retained openings'
    source.hide_render=True;source.hide_set(True);hidden.append(source.name)
    copies.append({'source':source.name,'copy':obj.name,'recessedFaces':recessed_faces})
old_bands=bpy.data.objects['KSW_D3_rusticated_brick_recessed_bands']
old_bands.hide_render=True;old_bands.hide_set(True);hidden.append(old_bands.name)
assert all(fingerprint(bpy.data.objects[n])==value for n,value in before.items())
for name in ['room-studies.json','room-spaces.json','building-review.json']:
    shutil.copyfile(ROOT/'result/blender/stage89'/name,OUT/name)
if not (OUT/'catalogue-before.json').exists():
    shutil.copyfile(ROOT/'web/public/models/catalogue.json',OUT/'catalogue-before.json')
audit={'version':90,'baseline':89,'baselineFingerprint':before,
       'frame':{'origin':list(origin),'right':list(right),'normal':list(normal)},
       'copies':copies,'hiddenObjects':hidden,'jointCentres':levels,
       'jointHalfWidth':half_width,'shoulderWidth':shoulder,'jointDepth':depth,
       'reference':'LSE Estate 20 Kingsway exterior photograph, corroborated by 2025/26 property handbook; image capture dates unknown',
       'referenceUrl':'https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate',
       'limitations':['Horizontal course registration retained as a photo estimate, not surveyed dimensions',
                      'Only lower red block faces and occluded joints corrected; upper fine brick and retained curved oriel unchanged',
                      'Roof, unseen elevations and complete interiors remain unverified; no photo texture exported']}
(OUT/'kingsway-rustication-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v90.blend'))
print('KINGSWAY_RUSTICATION_SAVED',copies,flush=True)
