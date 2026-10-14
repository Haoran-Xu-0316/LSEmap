"""Refine 61 Aldwych glazing without exposing its unregistered empty envelope.

Use Blender's Text Editor. Source207 remains read-only. Historical photography
supports glazing appearance, not measured optics or a new survey.
The unresolved whole-building registration is deliberately retained.
"""
from pathlib import Path
import array
import hashlib
import json
import sys
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/61a-exterior208'
BASE = ROOT / 'result/blender/LSE_campus_detailed_v207.blend'
SOURCE_SHA = '44a0b2f09a6a13bbb9532e3a75e415aea7798bef63798e62036bbceb89ded7b0'
COMPONENT = OUT / '61a-exterior208-component.blend'
COLLECTION = '61A_EXTERIOR'
GLASS = [
    'GLASS181_61A_D5_entrance_glass_glass',
    'GLASS181_61A_D5_pavilion63_clerestory_glass_glass',
    'GLASS181_61A_D5_pavilion63_lower_glass_glass',
    'GLASS181_61A_D5_roof_window_glass',
    'GLASS181_61A_NEXT_corner_glass_glass',
    'GLASS181_61A_NEXT_retained_glazing_glass',
]
ROOF = 'GLASS181_61A_D5_roof_window_glass'
BACKED_DORMERS = set(range(6, 16))

sys.path.insert(0, str(ROOT / 'web/tools'))
from integrate_exterior_round194 import object_fingerprint, set_layer_hidden, update_scene
from refine_saw_exterior206 import geometry, optics
from refine_portsmouth_exterior207 import material_fingerprint


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def shape_fingerprint(obj):
    """Coordinate, topology, UV, smooth/normal and transform identity; slots excluded."""
    digest = hashlib.sha256(str([list(r) for r in obj.matrix_world]).encode())
    for items,field,kind,n in [(obj.data.vertices,'co','f',3),(obj.data.loops,'vertex_index','i',1),
                               (obj.data.polygons,'loop_total','i',1),(obj.data.polygons,'normal','f',3)]:
        values=array.array(kind,[0])*(len(items)*n)
        items.foreach_get(field,values)
        digest.update(values.tobytes())
    for uv in obj.data.uv_layers:
        values=array.array('f',[0])*(len(uv.data)*2)
        uv.data.foreach_get('uv',values)
        digest.update(uv.name.encode()+values.tobytes())
    digest.update(str([p.use_smooth for p in obj.data.polygons]).encode())
    return digest.hexdigest()


def render_views(label):
    scene = bpy.data.scenes.new('61A208_REVIEW_' + label)
    scene.collection.children.link(bpy.data.collections[COLLECTION])
    bpy.context.window.scene = scene
    world = bpy.data.worlds.new('61A208_REVIEW_WORLD_' + label)
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.68, .74, .8, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = .7
    scene.world = world
    sun = bpy.data.objects.new('61A208_REVIEW_SUN_' + label,
                              bpy.data.lights.new('61A208_REVIEW_SUN_' + label, 'SUN'))
    scene.collection.objects.link(sun)
    sun.data.energy = 2
    sun.data.angle = .2
    sun.rotation_euler = (.4, -.5, -.1)
    camera = bpy.data.objects.new('61A208_REVIEW_CAMERA_' + label,
                                 bpy.data.cameras.new('61A208_REVIEW_CAMERA_' + label))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = 'ORTHO'
    camera.data.clip_end = 500
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'AgX'
    scene.render.image_settings.file_format = 'PNG'
    cameras = []
    for name, target, position, scale in [
        ('whole', (-51, -92, 17), (-128, -192, 67), 94),
        ('corner', (-40.8, -128.5, 12), (-73, -196, 28), 31),
    ]:
        camera.location = position
        camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera.data.ortho_scale = scale
        scene.render.filepath = str(OUT / (label + '-' + name + '.png'))
        bpy.ops.render.render(write_still=True)
        cameras.append(dict(view=name, target=target, position=position, orthoScale=scale))
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    for obj in (camera, sun):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.scenes.remove(scene)
    return cameras


def glass_shells(obj):
    """Record closed connected pane shells without remeshing their source."""
    links = {v.index: set() for v in obj.data.vertices}
    for edge in obj.data.edges:
        a, b = edge.vertices
        links[a].add(b)
        links[b].add(a)
    pending = set(links)
    shells = []
    while pending:
        group = {pending.pop()}
        queue = list(group)
        while queue:
            for index in links[queue.pop()] & pending:
                pending.remove(index)
                group.add(index)
                queue.append(index)
        faces = [f for f in obj.data.polygons if set(f.vertices) <= group]
        uses = {}
        for f in faces:
            ids = list(f.vertices)
            for a,b in zip(ids, ids[1:]+ids[:1]):
                edge = tuple(sorted((a,b)))
                uses[edge] = uses.get(edge, 0)+1
        assert uses and all(count == 2 for count in uses.values()), obj.name
        shells.append(dict(vertices=len(group), faces=len(faces), faceIndices=[f.index for f in faces], closed=True))
    return shells


def analyse_backing():
    """Check all pane centres and quarterpoints against existing opaque geometry."""
    from mathutils.bvhtree import BVHTree
    collection = bpy.data.collections[COLLECTION]
    vertices, faces, owners = [], [], []
    for obj in collection.all_objects:
        if obj.hide_render or obj.type != 'MESH' or obj.name in GLASS:
            continue
        offset = len(vertices)
        vertices.extend(obj.matrix_world @ vertex.co for vertex in obj.data.vertices)
        for face in obj.data.polygons:
            faces.append(tuple(offset + index for index in face.vertices))
            owners.append(obj.name)
    tree = BVHTree.FromPolygons(vertices, faces, all_triangles=False)
    rows = []
    for name in GLASS:
        obj = bpy.data.objects[name]
        for shell in glass_shells(obj):
            shell_faces = [obj.data.polygons[index] for index in shell['faceIndices']]
            area = max(face.area for face in shell_faces)
            front = max([face for face in shell_faces if face.area > area * .95],
                        key=lambda face: (obj.matrix_world.to_3x3() @ face.normal).dot(
                            obj.matrix_world @ face.center - Vector((-51, -90, 15))))
            normal = (obj.matrix_world.to_3x3() @ front.normal).normalized()
            centre = obj.matrix_world @ front.center
            points = [centre] + [centre.lerp(obj.matrix_world @ obj.data.vertices[index].co, .5)
                                 for index in front.vertices]
            hits = []
            for point in points:
                location, hit_normal, index, distance = tree.ray_cast(point - normal * .065, -normal, 30)
                hits.append(dict(point=list(point), owner=owners[index] if index is not None else None,
                                 distance=distance))
            rows.append(dict(source=name, centre=list(centre), normal=list(normal), hits=hits))
    report = dict(baselineSha256=SOURCE_SHA,
                  scope='All253closed exterior pane shells; centre and four quarterface rays inward. A distant opposite shell does not establish a room.',
                  panes=rows, byBatch={name: dict(
                      panes=sum(row['source'] == name for row in rows),
                      nearBackedRays=sum(hit['distance'] is not None and hit['distance'] < 3
                          for row in rows if row['source'] == name for hit in row['hits']),
                      rays=sum(len(row['hits']) for row in rows if row['source'] == name)) for name in GLASS})
    (OUT / 'backing-rays.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def run():
    OUT.mkdir(exist_ok=True)
    assert sha(BASE) == SOURCE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    originals = {o.name: object_fingerprint(o) for o in bpy.data.objects}
    materials = {m.name: material_fingerprint(m) for m in bpy.data.materials}
    visibility = {o.name: o.hide_render for o in bpy.data.objects}
    analyse_backing()
    cameras = render_views('before')
    candidates = [o for o in bpy.data.collections[COLLECTION].all_objects
                  if o.type == 'MESH' and not o.hide_render and
                  o.name in GLASS]
    assert set(GLASS) <= {o.name for o in candidates}
    owned, changes, material_copies, pane_shells = [], [], {}, {}
    for source in sorted(candidates, key=lambda o:o.name):
        assert source.parent is None
        name = '61A208_' + source.name.removeprefix('GLASS181_')
        clone = source.copy()
        clone.data = source.data.copy()
        clone.name = name
        clone.data.name = name
        clone['originalObject'] = source.name
        clone['webGeometrySource'] = source.name
        clone['destinationCollection'] = COLLECTION
        bpy.data.collections[COLLECTION].objects.link(clone)
        slot_changes = []
        for i, old in enumerate(source.data.materials):
            role = 'glass'
            key = (old.name, role)
            if key not in material_copies:
                new = old.copy()
                new.name = '61A208_' + role + '_' + old.name
                shader = new.node_tree.nodes['Principled BSDF']
                old_colour = list(shader.inputs['Base Color'].default_value)
                luminance = sum(a*b for a,b in zip(old_colour, (.2126,.7152,.0722)))
                colour = tuple(.25*x+.75*luminance for x in old_colour[:3])+(1,)
                shader.inputs['Base Color'].default_value = colour
                shader.inputs['Metallic'].default_value = 0
                shader.inputs['Roughness'].default_value = .12
                # These panes remain opaque proxies until actual internal
                # structure is registered; never see through an empty shell.
                shader.inputs['Transmission Weight'].default_value = 0
                shader.inputs['IOR'].default_value = 1.5
                shader.inputs['Alpha'].default_value = 1
                new['proxyPolicy'] = 'Original opacity retained: inward rays show no registered nearby room backing. Colour desaturated at unchanged linear luminance; not measured glass tint.'
                assert abs(sum(a*b for a,b in zip(colour, (.2126,.7152,.0722)))-luminance)<1e-7
                new.diffuse_color = colour
                material_copies[key] = new
            clone.data.materials[i] = material_copies[key]
            slot_changes.append(dict(slot=i, sourceMaterial=old.name, ownedMaterial=clone.data.materials[i].name,
                                     before=optics(old), after=optics(clone.data.materials[i])))
        assert geometry(clone) == geometry(source)
        if source.name in GLASS:
            pane_shells[source.name] = glass_shells(clone)
            assert all(x['before']['Transmission Weight']==0 for x in slot_changes)
        if source.name == ROOF:
            backing = json.loads((OUT/'backing-rays.json').read_text())
            rays = [p for p in backing['panes'] if p['source']==ROOF]
            glass = source.data.materials[-1].copy()
            glass.name = '61A208_backed_ten_dormer_dielectric'
            shader = glass.node_tree.nodes['Principled BSDF']
            glass.diffuse_color = (.78,.83,.84,1)
            shader.inputs['Base Color'].default_value = glass.diffuse_color
            shader.inputs['Transmission Weight'].default_value = .92
            shader.inputs['Metallic'].default_value = 0
            shader.inputs['Roughness'].default_value = .12
            shader.inputs['IOR'].default_value = 1.5
            glass['webOpacity'] = .62
            glass['opticsBasis'] = 'Ten previously registered Kingsway dormers only. All50rays hit existing roof backing at1.332m; no added interiors. Historical photo visual estimate.'
            new_slot = len(clone.data.materials)
            clone.data.materials.append(glass)
            material_copies[(source.data.materials[-1].name,'backed-dormer')] = glass
            for index in BACKED_DORMERS:
                assert all(h['owner']=='61A177_Kingsway_ten_dormer_roof_slope' and 1.3<h['distance']<1.4 for h in rays[index]['hits'])
                for face in pane_shells[source.name][index]['faceIndices']:
                    clone.data.polygons[face].material_index = new_slot
            slot_changes.append(dict(slot=new_slot,sourceMaterial=source.data.materials[-1].name,
                ownedMaterial=glass.name,after=optics(glass),connectedPaneIndices=sorted(BACKED_DORMERS)))
        assert shape_fingerprint(clone)==shape_fingerprint(source)
        owned.append(clone)
        changes.append(dict(source=source.name, owned=name, originalObject=source.name,
                            destinationCollection=COLLECTION, geometrySha256=geometry(source),
                            role='glass', materialChanges=slot_changes))
    assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
    assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in materials.items())
    added = [o.name for o in owned]
    archived = [x['source'] for x in changes]
    states = {o.name: object_fingerprint(o) for o in owned}
    bpy.data.libraries.write(str(COMPONENT), set(owned), fake_user=True, compress=True)
    audit = dict(baseline=str(BASE.relative_to(ROOT)), baselineSha256=SOURCE_SHA,
                 component=str(COMPONENT.relative_to(ROOT)), componentSha256=sha(COMPONENT),
                 addedObjects=added, ownedObjects=added, archivedObjects=archived,
                 destinationCollection=COLLECTION, retainNewMaterials=True,
                 changes=changes, cameras=cameras, glassShells=pane_shells,
                 closedPaneShellCount=sum(map(len,pane_shells.values())),backedTransparentPanes=10,retainedOpaqueProxyPanes=243,
                 backingRayReport='result/blender/61a-exterior208/backing-rays.json',
                 transparentDormerPolicy=dict(source=ROOF,sourceShellIndices=sorted(BACKED_DORMERS),webOpacity=.62,closedShells=True,rayCount=50,backing='61A177_Kingsway_ten_dormer_roof_slope',distanceRange=[1.332,1.333]),
                 materialCopies={new.name:key[0] for key,new in material_copies.items()},
                 sourceReferences=[
                     dict(local='data/documents/61aldwych_brochure_2021.pdf',sha256=sha(ROOT/'data/documents/61aldwych_brochure_2021.pdf'),pages=[8,9],date='May2021',url='https://s3-eu-west-1.amazonaws.com/agents-society-assets-files/ae303325518c4f9634961cdca4a7cfdc-61%20Aldwych_A4%20Brochure_2021_.pdf',rechecked='2026-10-15'),
                     dict(local='data/documents/property_handbook.pdf',sha256=sha(ROOT/'data/documents/property_handbook.pdf'),pages=[15],evidence='Official estate handbook built daylight entrance photograph; source photograph undated.'),
                     dict(local='data/collections/campus_photos_round2/images/61A/61A_aldwych_survey_01.jpg',sha256=sha(ROOT/'data/collections/campus_photos_round2/images/61A/61A_aldwych_survey_01.jpg'),url='https://www.walshandassociates.co.uk/projects',rechecked='2026-10-15',evidence='Built dusk photograph shows illuminated spaces through glazing, pale masonry, dark metal and slate. Not used to calibrate daytime colour.')],
                 footprintRegistration=dict(status='provisional',geometryChanges=0,previousReview='result/blender/61a-registration207/source-review.json',reason='Brochure floorplan has no surveyed world controls. Independent drawing-to-world transform remains unproved; matching twoOSMway bounds is not independent evidence.'),
                 improvement='Remove excessive cyan tint at retained linear luminance. Retain243unregistered window proxies opaque; restore only10registered roof-backed Kingsway dormers to dielectric glazing.',
                 limitations=['Optical values and glass chroma are visual estimates, not measured material specifications.',
                              'All mesh coordinates, UVs, normals, transforms and original material data remain unchanged. Ten roof pane face materialindices are assigned the new backed-glass slot.',
                              'No footprint movement, atrium excavation, opening relocation, room or backing geometry is invented.',
                              '2021photos document historical built appearance, not2026fitout or redevelopment completion.',
                              'Whole-building registration, unseen elevations and current interiors remain provisional.'])
    (OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    with bpy.data.libraries.load(str(COMPONENT),link=False)as(src,dst):
        assert set(src.objects)==set(added)
        dst.objects=list(added)
    for obj in dst.objects:
        bpy.data.collections[COLLECTION].objects.link(obj)
        obj.hide_render=False
    update_scene()
    for obj in dst.objects:
        assert object_fingerprint(obj)==states[obj.name], obj.name
        assert shape_fingerprint(obj)==shape_fingerprint(bpy.data.objects[obj['originalObject']])
        if obj['originalObject'] != ROOF:
            assert geometry(obj)==geometry(bpy.data.objects[obj['originalObject']])
    for name in added:set_layer_hidden(bpy.data.objects[name],False)
    for name in archived:
        bpy.data.objects[name].hide_render=True
        set_layer_hidden(bpy.data.objects[name],True)
    assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
    assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in materials.items())
    assert all(bpy.data.objects[n].hide_render==v for n,v in visibility.items()if n not in archived)
    render_views('after')
    (OUT/'verification.json').write_text(json.dumps(dict(savedComponentReopened=True,
        baselineSha256=sha(BASE),baselineUnchanged=sha(BASE)==SOURCE_SHA,
        componentSha256=sha(COMPONENT),originalObjectsVerified=len(originals),originalMaterialsVerified=len(materials),
        allOriginalGeometryUvsBindingsAndMaterialsPreserved=True,unrelatedRenderVisibilityPreserved=True,
        replacementsGeometryNormalsUvsAndTransformsExactlyPreserved=True,footprintUnchanged=True,stoneUnchanged=True,
        backedTransparentPanes=10,retainedOpaqueProxyPanes=243,backingRayReport='result/blender/61a-exterior208/backing-rays.json',
        newObjectCount=len(added),glassBatchCount=len(GLASS),closedPaneShellCount=audit['closedPaneShellCount'],
        newFingerprints=states,renderedBeforeAfter=True),indent=2)+'\n')
    print('61A208_VERIFIED',audit['componentSha256'],len(added),flush=True)


if __name__ == '__main__':
    run()
    bpy.ops.wm.quit_blender()
