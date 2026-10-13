"""Keep one optical surface for each registered Portugal Street library pane.

Run the callable in the loaded full Blender scene. Face positions, corner UVs,
frames and authored optics are retained; unsupported interiors stay unexposed.
"""
from pathlib import Path
import json
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
PANES = (
    ('GLASS181_LRB_EXTERIOR172_D5_portugal110_glass',
     'LRB_WINDOW191_portugal_single_glass', 85),
    ('GLASS181_LRB_EXTERIOR172_D5_portugal110_roof_glass',
     'LRB_WINDOW191_portugal_roof_single_glass', 18),
)


def street_normal():
    geometry = json.loads((ROOT / 'result/blender/site_geometry.json').read_text())
    ring = next(b['rings'][0] for b in geometry['buildings'] if b['code'] == 'LRB')
    axis = Vector((*ring[2], 0)) - Vector((*ring[1], 0))
    return Vector((-axis.y, axis.x, 0)).normalized()


def connected_faces(mesh):
    incidence = [[] for _ in mesh.vertices]
    for face in mesh.polygons:
        for vertex in face.vertices:
            incidence[vertex].append(face.index)
    pending = set(range(len(mesh.polygons)))
    while pending:
        seed = min(pending)
        pending.remove(seed)
        component, stack = {seed}, [seed]
        while stack:
            for vertex in mesh.polygons[stack.pop()].vertices:
                for neighbour in incidence[vertex]:
                    if neighbour in pending:
                        pending.remove(neighbour)
                        component.add(neighbour)
                        stack.append(neighbour)
        yield [mesh.polygons[i] for i in sorted(component)]


def apply_lrb_window_surfaces():
    existing = [bpy.data.objects.get(target) for _, target, _ in PANES]
    if any(existing):
        assert all(existing), 'Partial library pane replacement needs review'
        return dict(alreadyApplied=True, addedObjects=[], archivedObjects=[], changedObjects=[])
    outward = street_normal()
    records = []
    for source_name, target_name, expected in PANES:
        source = bpy.data.objects[source_name]
        mesh = source.data
        assert not source.hide_render
        assert len(mesh.vertices) == expected * 8 and len(mesh.polygons) == expected * 6
        normal_matrix = source.matrix_world.to_3x3().inverted().transposed()
        vertices, faces, corner_uvs, slots, selected = [], [], [], [], []
        for component in connected_faces(mesh):
            assert len(component) == 6
            candidates = [f for f in component
                          if (normal_matrix @ f.normal).normalized().dot(outward) > .999]
            assert len(candidates) == 1, 'Each pane needs one outward broad face'
            face = candidates[0]
            assert len(face.vertices) == 4
            start = len(vertices)
            vertices.extend(mesh.vertices[mesh.loops[i].vertex_index].co.copy()
                            for i in face.loop_indices)
            faces.append(tuple(range(start, len(vertices))))
            corner_uvs.append([[layer.data[i].uv.copy() for i in face.loop_indices]
                              for layer in mesh.uv_layers])
            slots.append(face.material_index)
            selected.append(face.index)
        assert len(faces) == expected
        pane_mesh = bpy.data.meshes.new(target_name)
        pane_mesh.from_pydata(vertices, [], faces)
        pane_mesh.update()
        for slot, original in enumerate(mesh.materials):
            if slot in slots:
                material = original.copy()
                material.name = 'LRB_WINDOW191_sheet_' + original.name
                material['webClosedGlazing'] = False
                material['surfacePolicy'] = 'One optical sheet per retained street pane; authored opaque proxy finish retained'
            else:
                material = original
            pane_mesh.materials.append(material)
        for index, old in enumerate(mesh.uv_layers):
            layer = pane_mesh.uv_layers.new(name=old.name)
            for face, values in zip(pane_mesh.polygons, corner_uvs):
                for loop, uv in zip(face.loop_indices, values[index]):
                    layer.data[loop].uv = uv
        for face, slot in zip(pane_mesh.polygons, slots):
            face.material_index = slot
        target = source.copy()
        target.data, target.name = pane_mesh, target_name
        for collection in source.users_collection:
            collection.objects.link(target)
        target.hide_render = False
        target.hide_set(False)
        source.hide_render = True
        source.hide_set(True)
        records.append(dict(source=source_name, target=target_name, panes=expected,
                            sourceFaces=len(mesh.polygons), faces=len(faces),
                            selectedSourceFaces=selected,
                            removedTriangles=(len(mesh.polygons) - len(faces)) * 2))
    return dict(alreadyApplied=False,
                addedObjects=[r['target'] for r in records],
                archivedObjects=[r['source'] for r in records], changedObjects=[],
                records=records, paneCount=sum(r['panes'] for r in records),
                removedTriangles=sum(r['removedTriangles'] for r in records),
                sourceReferences=['data/collections/library-roof-2025/existing-nw-elevation.pdf'],
                drawing='4556-FBR-LR-ZZ-DR-A-114 P01, 17 April 2025',
                scope='Registered Portugal Street main and dormer panes; remove box backs and edges, preserve front coordinates, UV and optics',
                limitations=['Street registration and window dimensions remain inherited estimates',
                             'A single realtime optical sheet is not fabrication thickness',
                             'Opaque proxy finish retained where current rooms are not registered',
                             'Other elevations, roof shape and complete interiors remain unverified'])
