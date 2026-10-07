"""Remove stacked closed glass faces from the restored Old Curiosity Shop.

The2023restoration photograph supports a glazed shopfront and sash windows.
Keep original outward planes, aperture dimensions, glass hue and historic
restoration colours. Dark backing remains a recess study, not an invented shop.
"""
from pathlib import Path
import hashlib
import bpy, bmesh
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
SOURCES = ['OCS_D3_upper_sash_glass','OCS_D3_shop_display_glass','OCS_D3_glazed_door_pane']
NAMES = ['OCS_NEXT_EXTERIOR168_'+name.removeprefix('OCS_D3_') for name in SOURCES]
PHOTO = 'data/collections/exterior_photos_round4/images/OCS/OCS_ayesa_9.jpg'


def apply_ocs_exterior168():
    if all(bpy.data.objects.get(name) for name in NAMES):
        return dict(alreadyApplied=True, addedObjects=[], archivedObjects=[], changedObjects=[])
    assert not any(bpy.data.objects.get(name) for name in NAMES)
    collection = bpy.data.collections['OCS_EXTERIOR']
    # Retained native/GIS footprint center; used only to choose the outward face.
    center = Vector((-42.639500347788456, 43.07689434417981, 0))
    material = bpy.data.objects[SOURCES[0]].data.materials[0].copy()
    material.name = 'OCS_EXTERIOR168_dielectric_single_glass'
    node = material.node_tree.nodes['Principled BSDF']
    node.inputs['Metallic'].default_value = 0
    node.inputs['IOR'].default_value = 1.5
    material['webOpacity'] = .30
    material['opticsBasis'] = 'One-sheet alpha approximation; source hue, roughness and transmission retained. No measured optics.'
    panes = []
    for source_name, owned_name in zip(SOURCES, NAMES):
        source = bpy.data.objects[source_name]
        assert not source.hide_render
        owned = source.copy(); owned.data = source.data.copy(); owned.name = owned_name
        collection.objects.link(owned)
        bm = bmesh.new(); bm.from_mesh(owned.data); bm.normal_update()
        seen = set(); keep = set()
        for seed in bm.verts:
            if seed in seen: continue
            todo = [seed]; seen.add(seed); vertices = []
            while todo:
                vertex = todo.pop(); vertices.append(vertex)
                for edge in vertex.link_edges:
                    other = edge.other_vert(vertex)
                    if other not in seen: seen.add(other); todo.append(other)
            faces = set(face for vertex in vertices for face in vertex.link_faces)
            assert len(vertices) == 8 and len(faces) == 6
            vertical = [face for face in faces if abs(face.normal.z) < .05]
            large = sorted(vertical, key=lambda face:face.calc_area(), reverse=True)[:2]
            assert len(large) == 2 and abs(large[0].calc_area()-large[1].calc_area()) < 1e-4
            def alignment(face):
                world_normal = (owned.matrix_world.to_3x3() @ face.normal).normalized()
                radial = owned.matrix_world @ face.calc_center_median() - center
                radial.z = 0
                return world_normal.dot(radial.normalized())
            front = max(large, key=alignment)
            assert alignment(front) > .2
            keep.add(front)
            point = owned.matrix_world @ front.calc_center_median()
            normal = (owned.matrix_world.to_3x3() @ front.normal).normalized()
            panes.append(dict(object=owned_name, center=list(point), normal=list(normal), area=front.calc_area()))
        bmesh.ops.delete(bm, geom=[face for face in bm.faces if face not in keep], context='FACES_ONLY')
        bmesh.ops.delete(bm, geom=[vertex for vertex in bm.verts if not vertex.link_faces], context='VERTS')
        bm.to_mesh(owned.data); bm.free(); owned.data.update()
        owned.data.materials.clear(); owned.data.materials.append(material)
        source.hide_render = True; source.hide_set(True)
    assert len(panes) == 8
    return dict(alreadyApplied=False, addedObjects=NAMES, archivedObjects=SOURCES,
                changedObjects=[], panes=panes, material=material.name,
                sourcePhoto=PHOTO, sourcePhotoSha256=hashlib.sha256((ROOT/PHOTO).read_bytes()).hexdigest(),
                sourceURL='https://www.ayesa.com/en/projects/the-old-curiosity-shop/',
                restorationPeriod='September2021-June2023', photographDate='unknown',
                limitations=['Retained photograph-informed colours and estimated window dimensions.',
                             'Opaque recesses retained; no whole shop interior or2026condition survey.',
                             'Glass alpha and IOR are approximations, not measured material values.'])
