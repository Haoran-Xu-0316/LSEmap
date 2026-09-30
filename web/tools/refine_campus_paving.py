"""Build edition44 paving in Blender from reviewed street footprints.
Run in Blender's Text Editor after prepare_campus_paving.py.
"""
from pathlib import Path
import array
import hashlib
import json
import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage44'
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v43.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()

def extract_existing_road_surfaces():
    """Keep the plan input reproducible from the preserved native baseline."""
    surfaces = []
    for obj in bpy.data.collections['00_SITE'].all_objects:
        if obj.type != 'MESH' or obj.hide_render:
            continue
        for street in ['Houghton Street', 'Sheffield Street', 'Portsmouth Street', 'Clare Market', 'John Watkins Plaza']:
            if street not in obj.name:
                continue
            top = []
            for face in obj.data.polygons:
                points = [obj.matrix_world @ obj.data.vertices[index].co for index in face.vertices]
                if min(p.z for p in points) > .023 and max(p.z for p in points) < .025:
                    top.append([[p.x, p.y] for p in points])
            if top:
                surfaces.append({'object': obj.name, 'street': street, 'polygons': top})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'road-surfaces.json').write_text(json.dumps(surfaces))

extract_existing_road_surfaces()

plan = json.loads((OUT / 'paving-plan.json').read_text())

def fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        digest.update(array.array('f',[c for vertex in obj.data.vertices for c in vertex.co]).tobytes())
        digest.update(array.array('i',[loop.vertex_index for loop in obj.data.loops]).tobytes())
        digest.update(str([m.name if m else None for m in obj.data.materials]).encode())
    return digest.hexdigest()

before = {o.name:fingerprint(o) for o in bpy.data.objects}
collection = bpy.data.collections['00_SITE']
materials = {}
for kind, colour in {'grout':(.28,.29,.28),'edge':(.45,.44,.39),'yorkstone':(.49,.46,.38),'slab':(.46,.47,.44)}.items():
    materials[kind] = []
    for shade in range(5 if kind in ['yorkstone','slab'] else 1):
        factor = 1+(shade-2)*.025 if kind in ['yorkstone','slab'] else 1
        mat = bpy.data.materials.new(f'SITE_V44_{kind}_{shade}')
        mat.diffuse_color = (*(c*factor for c in colour),1)
        mat.use_nodes = True
        shader = mat.node_tree.nodes['Principled BSDF']
        shader.inputs['Base Color'].default_value = mat.diffuse_color
        shader.inputs['Roughness'].default_value = .88
        materials[kind].append(mat)

def create_surface(name, triangles, z, material):
    if not triangles:
        return
    vertices = [(x,y,z) for tri in triangles for x,y in tri]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices,[],[(i,i+1,i+2) for i in range(0,len(vertices),3)])
    mesh.materials.append(material)
    # World-metric UVs keep the native surface suitable for later material work.
    uv = mesh.uv_layers.new(name='SurfaceUV')
    for loop in mesh.loops:
        vertex = mesh.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = (vertex.x,vertex.y)
    mesh.update()
    obj = bpy.data.objects.new(name,mesh)
    collection.objects.link(obj)
    obj['scope'] = 'Photo-guided paving; estimated courses on mapped road footprint'
    return obj

created = []
for record in plan['records']:
    label = record['street'].replace(' ','_')
    for component, triangles,z,mat in [('bedding',record['base'],.032,materials['grout'][0]),('flush_border',record['edge'],.040,materials['edge'][0])]:
        obj = create_surface(f'SITE_V44_{label}_{component}',triangles,z,mat)
        if obj:created.append(obj.name)
    kind = 'yorkstone' if record['street']=='Portsmouth Street' else 'slab'
    for shade in range(5):
        triangles = [tri for tile in record['tiles'] if tile['shade']==shade for tri in tile['triangles']]
        obj = create_surface(f'SITE_V44_{label}_pavers_{shade}',triangles,.040,materials[kind][shade])
        if obj:created.append(obj.name)
for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()
assert all(fingerprint(bpy.data.objects[name])==digest for name,digest in before.items())
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v44.blend'))
# A lightweight review export includes the base site and new paving in one GLB.
for obj in bpy.data.objects:
    obj.select_set(False)
for obj in collection.all_objects:
    if obj.type=='MESH' and not obj.hide_render:
        obj.hide_set(False)
        obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'site-preview.glb'),export_format='GLB',use_selection=True,use_active_scene=True,export_cameras=False,export_lights=False)
(OUT/'paving-audit.json').write_text(json.dumps({'baseline':43,'version':44,'protectedObjectsUnchanged':len(before),'addedObjects':created,'paverCount':sum(len(r['tiles']) for r in plan['records']),'footprintOverlapArea':plan['footprintOverlapArea'],'references':['data/collections/public-realm-2026/sources.json','data/collections/streets/coverage.json'],'limitations':plan['notes'],'status':'Native model saved; candidate awaiting web visual review'},indent=2)+'\n')
print('PAVING_BUILT',len(created))
