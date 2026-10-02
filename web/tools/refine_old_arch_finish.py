"""Refine OLD's curved stone reveal from the supplied entrance photograph.
Run in Blender Text Editor. Preserve geometry and archive the original object.
Colours and optical finish are photographic estimates, not measured samples.
"""
from pathlib import Path
import array, hashlib, json, math, shutil
import bpy
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage103'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v102.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']

def fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        digest.update(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i', [l.vertex_index for l in obj.data.loops]).tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data, 'materials', [])]).encode())
    return digest.hexdigest()

before = {o.name: fingerprint(o) for o in bpy.data.objects}
frame = json.loads((ROOT / 'result/blender/stage52/old-houghton-audit.json').read_text())
origin, right, outward = [Vector(frame[k]) for k in ['origin', 'right', 'outward']]
source = bpy.data.objects['OLD_D5_arch69_stone']
assert not source.hide_render
copy = source.copy(); copy.data = source.data.copy()
copy.name = 'OLD_V103_curved_limestone_arch'
bpy.data.collections['OLD_EXTERIOR'].objects.link(copy)
source.hide_render = True; source.hide_set(True)
copy.hide_render = False; copy.hide_set(False)
base = source.data.materials[0]
copy.data.materials.clear()
# Five shared materials keep each wedge consistent without one draw call per stone.
factors = [.955, .985, 1.0, 1.02, 1.045]
for index, factor in enumerate(factors):
    material = base.copy(); material.name = f'OLD_V103_arch_limestone_{index}'
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    output = nodes.new('ShaderNodeOutputMaterial')
    shader = nodes.new('ShaderNodeBsdfPrincipled')
    color = tuple(c * factor for c in base.diffuse_color[:3])
    material.diffuse_color = (*color, 1)
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = .88
    coordinates = nodes.new('ShaderNodeTexCoord')
    noise = nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 3.5
    noise.inputs['Detail'].default_value = 2
    ramp = nodes.new('ShaderNodeValToRGB')
    for element, shade in zip(ramp.color_ramp.elements, [.95, 1.035]):
        element.color = (*[c * shade for c in color], 1)
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .18
    bump.inputs['Distance'].default_value = .0008
    links.new(coordinates.outputs['Object'], noise.inputs['Vector'])
    links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
    links.new(ramp.outputs['Color'], shader.inputs['Base Color'])
    links.new(noise.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    links.new(shader.outputs['BSDF'], output.inputs['Surface'])
    material['siteDetail'] = True
    copy.data.materials.append(material)
mesh = copy.data
normals = [loop.vector.copy() for loop in mesh.corner_normals]
curved = []
segments = {}
for poly in mesh.polygons:
    points = [copy.matrix_world @ mesh.vertices[mesh.loops[i].vertex_index].co for i in poly.loop_indices]
    local = [((p-origin).dot(right), (p-origin).dot(outward), p.z-origin.z-4.8) for p in points]
    x = sum(p[0] for p in local)/len(local); z = sum(p[2] for p in local)/len(local)
    # Each of the twenty fan stones shares its hue through the whole reveal.
    segment = min(19, max(0, int(math.atan2(max(0,z), x)/math.pi*20)))
    poly.material_index = (segment * 7 + segment // 3) % len(factors)
    segments.setdefault(str(segment), []).append(poly.index)
    if all(2.89 <= math.hypot(px,pz) <= 4.21 and depth < .225 for px,depth,pz in local):
        curved.append(poly.index); poly.use_smooth = True
        for loop_index, (px,depth,pz) in zip(poly.loop_indices, local):
            radius = math.hypot(px,pz)
            t = max(.002, min(1, (radius-2.90)/1.30))
            slope = .85*.65/1.30*t**(-.35)
            radial = right*(px/radius) + Vector((0,0,pz/radius))
            normal = (outward-radial*slope).normalized()
            normals[loop_index] = copy.matrix_world.to_3x3().transposed() @ normal
assert len(curved) == 240, len(curved)
mesh.normals_split_custom_set(normals)
assert all(fingerprint(bpy.data.objects[n]) == h for n,h in before.items())
for filename in ['room-studies.json','room-spaces.json','building-review.json']:
    shutil.copyfile(ROOT/'result/blender/stage102'/filename, OUT/filename)
if not (OUT/'catalogue-before.json').exists():
    shutil.copyfile(ROOT/'web/public/models/catalogue.json', OUT/'catalogue-before.json')
assert json.loads((OUT/'catalogue-before.json').read_text())['version'] == '102'
audit = {'version':103,'baseline':102,'originalFingerprints':before,'source':source.name,'copy':copy.name,
         'frame':frame,'curvedFaces':curved,'segments':segments,'materialFactors':factors,
         'reference':'User supplied Old Building Houghton entrance photograph, received 2026-10-02; capture date unknown',
         'limits':['Colour and roughness estimated from photograph','Geometry, sculpture, whole roof and interiors unchanged; artwork and unseen elevations remain unresolved']}
(OUT/'old-arch-finish-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v103.blend'))
print('OLD_ARCH_FINISH_SAVED',len(curved),len(factors),flush=True)
