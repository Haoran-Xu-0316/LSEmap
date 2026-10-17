"""Fixed236Clare entrance contact repair. Source native is read-only."""
from pathlib import Path
import hashlib
import json
import sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/street-public236'
DATA = ROOT / 'data/collections/street-public236'
BASE = ROOT / 'result/blender/LSE_campus_detailed_v234.blend'
BASE_SHA = '0c9c4d7d5793ac3693c6ff7b9789e5300ebca32a5de39e0a39b75a910182d0b7'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def inspect():
    import bpy
    sys.path.insert(0, str(ROOT / 'web/tools'))
    from mathutils import Vector
    assert sha(BASE) == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    bpy.context.window.scene = scene
    bpy.context.view_layer.update()
    rows = []
    for obj in scene.objects:
        if obj.type != 'MESH' or obj.hide_render:
            continue
        if not any(term in obj.name.lower() for term in ['step','stair','landing','threshold','ramp','clare','houghton','slab','paving','kerb','drain']):
            continue
        points = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
        low = [min(p[i] for p in points) for i in range(3)]
        high = [max(p[i] for p in points) for i in range(3)]
        if high[0] < -30 or low[0] > 75 or high[1] < -120 or low[1] > 25 or low[2] > 2:
            continue
        rows.append(dict(name=obj.name, low=low, high=high, owners=[c.name for c in obj.users_collection], vertices=len(obj.data.vertices), polygons=len(obj.data.polygons), materials=[m.name if m else None for m in obj.data.materials]))
    write(OUT / 'native-inspection.json', dict(baselineSha256=BASE_SHA, objects=len(bpy.data.objects), materials=len(bpy.data.materials), rows=rows))
    from refine_streets230 import components
    ring = next(b for b in json.loads((ROOT / 'result/blender/site_geometry.json').read_text())['buildings'] if b['code'] == 'OLD')['rings'][0]
    a, b = Vector((*ring[7], 0)), Vector((*ring[8], 0))
    origin = (a + b) / 2
    right = (a - b).normalized()
    normal = Vector((right.y, -right.x, 0))
    detailed = []
    for name in ['OLD201_CLARE_pulls', 'OLD194_STONE_OLD_CLARE165_retained_edge_stone', 'OLD_V53_Clare_metal']:
        obj = bpy.data.objects[name]
        groups = []
        for part in components(obj):
            points = [obj.matrix_world @ obj.data.vertices[i].co for i in part]
            local = [[(p-origin).dot(right), (p-origin).dot(normal), p.z] for p in points]
            if name.endswith('retained_edge_stone') and min(p[2] for p in local) > 1.1:
                continue
            groups.append(dict(indices=part, local=local, world=[list(p) for p in points]))
        mats = []
        for material in obj.data.materials:
            p = material.node_tree.nodes.get('Principled BSDF') if material.use_nodes else None
            mats.append(dict(name=material.name, diffuse=list(material.diffuse_color), roughness=p.inputs['Roughness'].default_value if p else None, metalness=p.inputs['Metallic'].default_value if p else None, alpha=p.inputs['Alpha'].default_value if p else None))
        detailed.append(dict(name=name, hidden=obj.hide_render, materials=mats, groups=groups))
    write(OUT / 'entrance-detail.json', dict(origin=list(origin), right=list(right), normal=list(normal), length=(a-b).length, objects=detailed))

    from mathutils.bvhtree import BVHTree
    centre = -(a-b).length * .4
    focus = origin + right * centre + normal * .5
    vertices, faces, names = [], [], []
    for obj in scene.objects:
        if obj.type != 'MESH' or obj.hide_render:
            continue
        box = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        if min(p.x for p in box) > focus.x+4 or max(p.x for p in box) < focus.x-4 or min(p.y for p in box) > focus.y+4 or max(p.y for p in box) < focus.y-4 or min(p.z for p in box) > 1.1:
            continue
        obj.data.calc_loop_triangles()
        for tri in obj.data.loop_triangles:
            ps = [obj.matrix_world @ obj.data.vertices[i].co for i in tri.vertices]
            if max(p.z for p in ps) > 1.1 or max(p.z for p in ps) < -.1 or abs((ps[1]-ps[0]).cross(ps[2]-ps[0]).z) <= 1e-9:
                continue
            start = len(vertices)
            vertices.extend(ps)
            faces.append((start, start+1, start+2))
            names.append(obj.name)
    index = BVHTree.FromPolygons(vertices, faces, all_triangles=True)
    samples = []
    for side in [-1.0, 0, 1.0]:
        for depth in [-.4, -.2, 0, .20, .221, .23, .25, .27, .294, .296, .37, .5, .7, .72, 1.0, 1.4, 1.7, 1.8, 2.0]:
            p = origin + right * (centre+side) + normal * depth
            hit = index.ray_cast(Vector((p.x,p.y,1.11)), Vector((0,0,-1)), 1.3)
            samples.append(dict(side=side,depth=depth,world=[p.x,p.y],supportZ=hit[0].z if hit[0] is not None else None,source=names[hit[2]] if hit[2] is not None else None))
    write(OUT / 'entry-route-diagnosis.json', dict(samples=samples, triangles=len(faces), method='Actual saved active mesh horizontal triangles below1.1m, including either winding, all actual scene owners; highest walking support at each sample.'))
    import math
    camera = bpy.data.objects.new('STREET236_DIAGNOSIS_CAMERA', bpy.data.cameras.new('STREET236_DIAGNOSIS_CAMERA'))
    scene.collection.objects.link(camera)
    scene.camera = camera
    eye = focus + normal*7 + right*1.2 + Vector((0,0,2.6))
    target = focus + Vector((0,0,.6))
    camera.location = eye
    camera.rotation_euler = (target-eye).to_track_quat('-Z','Y').to_euler()
    camera.data.sensor_fit='VERTICAL'
    camera.data.lens=camera.data.sensor_height/(2*math.tan(math.radians(46)/2))
    scene.render.engine='BLENDER_EEVEE'
    scene.render.resolution_x=1100
    scene.render.resolution_y=825
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    for obj in scene.objects:
        if obj.hide_render:obj.hide_set(True)
    scene.render.filepath=str(OUT/'before-clare-entrance-contact.png')
    if not (OUT/'before-clare-entrance-contact.png').exists():
        bpy.ops.render.render(write_still=True)
    write(OUT/'diagnosis-camera.json',dict(eye=list(eye),target=list(target),fov=46))

    print('STREET236_INSPECTION', len(rows), flush=True)


OWNER = 'OLD_EXTERIOR'
SOURCES = ['OLD201_CLARE_pulls', 'OLD194_STONE_OLD_CLARE165_retained_edge_stone']
ADDED = ['OLD236_CLARE_supported_pulls_and_side_rails', 'OLD236_CLARE_continuous_entry_landing_edge_stone']


def native_state():
    import bpy
    from integrate_exterior_round194 import object_fingerprint
    from refine_portsmouth_exterior207 import material_fingerprint
    from refine_ksw_exterior219 import modifier_state
    metadata = json.loads((DATA / 'metadata-baseline.json').read_text())
    rooms = {r['collection']: sorted(o.name for o in bpy.data.collections[r['collection']].all_objects) for r in metadata['spaces']}
    return dict(objects={o.name: object_fingerprint(o) for o in bpy.data.objects}, materials={m.name: material_fingerprint(m) for m in bpy.data.materials}, owners={o.name: sorted(c.name for c in o.users_collection) for o in bpy.data.objects}, modifiers={o.name: modifier_state(o) for o in bpy.data.objects}, props={o.name: repr(sorted(o.items())) for o in bpy.data.objects}, visibility={o.name: o.hide_render for o in bpy.data.objects}, rooms=rooms)


def preserve(state):
    import bpy
    from integrate_exterior_round194 import object_fingerprint
    from refine_portsmouth_exterior207 import material_fingerprint
    from refine_ksw_exterior219 import modifier_state
    for name, value in state['objects'].items():
        assert object_fingerprint(bpy.data.objects[name]) == value, name
    for name, value in state['materials'].items():
        assert material_fingerprint(bpy.data.materials[name]) == value, name
    for name, value in state['owners'].items():
        assert sorted(c.name for c in bpy.data.objects[name].users_collection) == value, name
    for name, value in state['modifiers'].items():
        assert modifier_state(bpy.data.objects[name]) == value, name
    for name, value in state['props'].items():
        assert repr(sorted(bpy.data.objects[name].items())) == value, name
    for name, value in state['visibility'].items():
        assert bpy.data.objects[name].hide_render == value, name
    for name, value in state['rooms'].items():
        assert sorted(o.name for o in bpy.data.collections[name].all_objects) == value, name
    assert sha(BASE) == BASE_SHA


def mesh_record(obj):
    obj.data.calc_loop_triangles()
    return dict(name=obj.name, matrix=[list(r) for r in obj.matrix_world], vertices=[list(v.co) for v in obj.data.vertices], faces=[list(p.vertices) for p in obj.data.polygons], materialIndices=[p.material_index for p in obj.data.polygons], uv={u.name: [list(v.uv) for v in u.data] for u in obj.data.uv_layers}, customNormals=obj.data.has_custom_normals, normals=[list(n.vector) for n in obj.data.corner_normals], triangles=len(obj.data.loop_triangles))


def affine_uv(point, coordinates, values):
    """Extend the original planar corner mapping in metres, without rescaling it."""
    from mathutils import Vector
    a = coordinates[0]
    for j in range(1, len(coordinates)):
        for k in range(j+1, len(coordinates)):
            u, v = coordinates[j]-a, coordinates[k]-a
            det = u.dot(u)*v.dot(v)-u.dot(v)**2
            if abs(det) < 1e-12:
                continue
            q = point-a
            wu = (q.dot(u)*v.dot(v)-q.dot(v)*u.dot(v))/det
            wv = (q.dot(v)*u.dot(u)-q.dot(u)*u.dot(v))/det
            return Vector(values[0]) + (Vector(values[j])-Vector(values[0]))*wu + (Vector(values[k])-Vector(values[0]))*wv
    raise AssertionError('Degenerate source polygon')


def build():
    import bpy
    import bmesh
    import math
    from mathutils import Vector
    sys.path.insert(0, str(ROOT / 'web/tools'))
    from integrate_exterior_round194 import object_fingerprint, update_scene
    from refine_portsmouth_exterior207 import material_fingerprint
    from refine_streets230 import components
    assert sha(BASE) == BASE_SHA
    frozen = DATA / 'metadata-baseline.json'
    if not frozen.exists():
        frozen.write_bytes((ROOT / 'web/tools/building-metadata.json').read_bytes())
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    state = native_state()
    assert len(state['objects']) == 8582 and len(state['materials']) == 2327
    assert len(state['rooms']) == 35 and len(set().union(*(set(r) for r in state['rooms'].values()))) == 1485
    detail = json.loads((OUT / 'entrance-detail.json').read_text())
    origin, right, normal = (Vector(detail[k]) for k in ['origin', 'right', 'normal'])
    centre = -detail['length']*.4
    local = lambda obj, index: Vector(((obj.matrix_world@obj.data.vertices[index].co-origin).dot(right), (obj.matrix_world@obj.data.vertices[index].co-origin).dot(normal), (obj.matrix_world@obj.data.vertices[index].co).z))
    owned, edits, original_meshes = [], {}, {}
    for source_name, added_name in zip(SOURCES, ADDED):
        source = bpy.data.objects[source_name]
        assert not source.hide_render and sorted(c.name for c in source.users_collection) == [OWNER]
        assert not source.data.has_custom_normals
        original_meshes[source_name] = mesh_record(source)
        clone = source.copy()
        clone.data = source.data.copy()
        clone.name = added_name
        clone.data.name = added_name
        bpy.data.collections[OWNER].objects.link(clone)
        clone['originalObject'] = source_name
        clone['scope236'] = 'Local entry contact repair only; all original datums and four stair treads retained'
        parts = components(clone)
        moved = []
        if source_name == SOURCES[0]:
            posts = [part for part in parts if abs(min(local(clone, i).z for i in part)-.8) < 1e-5 and max(local(clone, i).y for i in part) < .4]
            assert len(posts) == 2
            for part in posts:
                for i in part:
                    if abs(local(clone, i).z-.8) < 1e-5:
                        point = clone.matrix_world@clone.data.vertices[i].co
                        point.z = .729
                        clone.data.vertices[i].co = clone.matrix_world.inverted()@point
                        moved.append(i)
            assert len(moved) == 16
            changed_polygons = [p.index for p in clone.data.polygons if set(p.vertices).intersection(moved)]
        else:
            stairs = [part for part in parts if abs(max(local(clone, i).z for i in part)-.73) < 1e-5 and min(local(clone, i).y for i in part) > .29]
            assert len(stairs) == 1
            stair = set(stairs[0])
            changed_polygons = [p.index for p in clone.data.polygons if set(p.vertices) <= stair]
            assert len(changed_polygons) == 6
            for i in stair:
                if abs(local(clone, i).y-.295) < 1e-5:
                    p = clone.matrix_world@clone.data.vertices[i].co
                    p += normal*(.13-local(clone, i).y)
                    clone.data.vertices[i].co = clone.matrix_world.inverted()@p
                    moved.append(i)
            assert len(moved) == 4
            for layer in clone.data.uv_layers:
                source_layer = source.data.uv_layers[layer.name]
                for polygon in clone.data.polygons:
                    if polygon.index not in changed_polygons:
                        continue
                    indices = list(polygon.loop_indices)
                    coordinates = [source.matrix_world@source.data.vertices[source.data.loops[i].vertex_index].co for i in indices]
                    values = [list(source_layer.data[i].uv) for i in indices]
                    for loop in indices:
                        vertex = clone.data.loops[loop].vertex_index
                        if vertex in moved:
                            layer.data[loop].uv = affine_uv(clone.matrix_world@clone.data.vertices[vertex].co, coordinates, values)
            # The inherited box has inward winding. Correct only this modified
            # closed landing solid; all other inherited solids retain their winding.
            bm = bmesh.new()
            bm.from_mesh(clone.data)
            bm.verts.ensure_lookup_table()
            selected = [f for f in bm.faces if {v.index for v in f.verts} <= stair]
            volume = sum(f.verts[0].co.dot(f.verts[j].co.cross(f.verts[j+1].co))/6 for f in selected for j in range(1, len(f.verts)-1))
            if volume < 0:
                bmesh.ops.reverse_faces(bm, faces=selected)
            bm.to_mesh(clone.data)
            bm.free()
        clone.data.update()
        owned.append(clone)
        edits[source_name] = dict(added=added_name, changedVertices=sorted(moved), modifiedPolygons=changed_polygons, retainedVertexCount=len(source.data.vertices)-len(moved), uvPolicy='Original affine planar mapping extrapolated only at moved landing corners; all unchanged corners kept exact')
    update_scene()
    preserve(state)
    fingerprints = {o.name: object_fingerprint(o) for o in owned}
    bindings = {o.name: [m.name for m in o.data.materials] for o in owned}
    material_fingerprints = {m.name: material_fingerprint(m) for o in owned for m in o.data.materials}
    component = OUT / 'component.blend'
    assert not component.exists(), 'Do not overwrite the frozen component'
    bpy.data.libraries.write(str(component), set(owned), fake_user=True, compress=True)
    component_sha = sha(component)
    write(OUT / 'serialized-mesh.json', dict(componentSha256=component_sha, source=original_meshes, replacement={o.name: mesh_record(o) for o in owned}, edits=edits))
    # Same-camera full active campus, rather than an isolated shadow plane.
    scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    camera = bpy.data.objects.new('STREET236_REVIEW_CAMERA', bpy.data.cameras.new('STREET236_REVIEW_CAMERA'))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.sensor_fit = 'VERTICAL'
    camera.data.clip_end = 1000
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x, scene.render.resolution_y = 1100, 825
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    near = json.loads((OUT / 'diagnosis-camera.json').read_text())
    focus = origin+right*centre+normal*.8+Vector((0,0,1.1))
    wide_eye = Vector(near['eye'])
    views = [dict(name='clare-entrance-contact', **near), dict(name='clare-street-context', eye=list(wide_eye), target=near['target'], fov=74)]
    for obj in scene.objects:
        if obj.hide_render:
            obj.hide_set(True)
    for view in views:
        eye, target = Vector(view['eye']), Vector(view['target'])
        camera.location = eye
        camera.rotation_euler = (target-eye).to_track_quat('-Z','Y').to_euler()
        camera.data.lens = camera.data.sensor_height/(2*math.tan(math.radians(view['fov'])/2))
        for phase in ['before', 'after']:
            for name in SOURCES:
                bpy.data.objects[name].hide_render = phase == 'after'
                bpy.data.objects[name].hide_set(phase == 'after')
            for obj in owned:
                obj.hide_render = phase == 'before'
                obj.hide_set(phase == 'before')
            update_scene()
            scene.render.filepath = str(OUT / (phase+'-'+view['name']+'.png'))
            bpy.ops.render.render(write_still=True)
    for name in SOURCES:
        bpy.data.objects[name].hide_render = False
        bpy.data.objects[name].hide_set(False)
    for obj in owned:
        obj.hide_render = False
        obj.hide_set(False)
    preserve(state)
    refs = ['result/blender/site_geometry.json', 'data/collections/old-clare-reference/front.png', 'data/collections/public-realm-2026/user-references/reference-04.png', 'data/collections/streets/raw/public_realm_strategy_2022.pdf', 'data/collections/street-public236/metadata-baseline.json', 'result/blender/street-public236/entrance-detail.json', 'result/blender/street-public236/entry-route-diagnosis.json']
    write(OUT / 'audit.json', dict(version=236, status='SAVED_PENDING_INDEPENDENT_REOPEN', baseline=str(BASE.relative_to(ROOT)), baselineSha256=BASE_SHA, componentPath=str(component.relative_to(ROOT)), componentSha256=component_sha, destinationCollection=OWNER, targetCollection=OWNER, addedObjects=ADDED, archivedObjects=SOURCES, changedObjects=[], addedFingerprints=fingerprints, replacementMaterialBindings=bindings, addedMaterialFingerprints=material_fingerprints, objectOwners={n: OWNER for n in ADDED}, archiveOwners={n: state['owners'][n] for n in SOURCES}, sourceHashes={p: sha(ROOT/p) for p in refs}, sourceManifest='data/collections/street-public236/sources.json', edits=edits, budget=dict(addedObjects=2, archivedObjects=2, newMaterials=0, newTextures=0, triangleDelta=0), preservation=dict(originalObjects=8582, originalMaterials=2327, oldSpaces=35, spaceMembers=1485, originalGeometryUVTransformsBindingsMaterialNodesPropsModifiersOwnersUnchanged=True, noFullNativeSaved=True), views=views, previews=[p+'-'+v['name']+'.png' for v in views for p in ['before','after']], limitations=['User photo and front.png are the same underlying photograph, not independent date evidence. Capture date unknown.', 'Four inherited stair treads, all tread Z, street Z and door Z retained. The inherited75mm sill height transition remains; no accessibility or survey claim.', 'Only the modified landing solid winding is corrected outward. Other inherited solid winding and all original native geometry remain untouched.', 'New landing depth0.13m is a bounded registration repair with under-sill overlap; not a surveyed historical construction detail.']))
    assert sha(BASE) == BASE_SHA and sha(component) == component_sha
    print('STREET236_COMPONENT_SAVED', component_sha, flush=True)

if __name__ == '__main__':
    build()
