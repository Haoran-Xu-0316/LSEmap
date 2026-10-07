"""Correct photographed lower OLD dormer jamb finishes on an already loaded scene.

The five visible lower dormers have blue painted outer jambs, cream recessed
returns and white upper-dormer surrounds. Source geometry is cloned intact;
only the ten lower outer jamb components receive a copied OLD blue material.
No scene loading, campus saving, inferred roof contour or hidden facade work.
"""
import bpy
import bmesh
from mathutils import Vector

SOURCE = 'OLD_D5_houghton112_mansard_stone'
OWNED = 'OLD_EXTERIOR168_lower_dormer_blue_jambs'


def apply_old_exterior168():
    if bpy.data.objects.get(OWNED):
        return dict(alreadyApplied=True, addedObjects=[], archivedObjects=[], changedObjects=[])
    original = bpy.data.objects[SOURCE]
    assert not original.hide_render
    # Retained facade registration, embedded to avoid a private archive dependency.
    origin, axis, normal = (Vector(v) for v in ([6.868992805480957, -66.35987854003906, 0.0], [0.45541495084762573, 0.8902792930603027, 0.0], [0.8902792930603027, -0.45541495084762573, 0.0]))
    bm = bmesh.new()
    bm.from_mesh(original.data)
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()
    seen, selected, face_indices = set(), [], []
    for seed in bm.verts:
        if seed in seen:
            continue
        todo, group = [seed], []
        seen.add(seed)
        while todo:
            vertex = todo.pop()
            group.append(vertex)
            for edge in vertex.link_edges:
                other = edge.other_vert(vertex)
                if other not in seen:
                    seen.add(other)
                    todo.append(other)
        points = []
        for v in group:
            p = original.matrix_world @ v.co - origin
            points.append(Vector((p.dot(axis), p.dot(normal), p.z)))
        lo = [min(p[i] for p in points) for i in range(3)]
        hi = [max(p[i] for p in points) for i in range(3)]
        if not (lo[0] > -33 and abs(lo[2] - 21.05) < .001 and abs(hi[2] - 23.20) < .001
                and abs(hi[0] - lo[0] - .12) < .001):
            continue
        faces = set(f for v in group for f in v.link_faces)
        assert len(group) == 8 and len(faces) == 6
        assert all(e.is_manifold for v in group for e in v.link_edges)
        # Signed closed-component volume checks the original winding before cloning.
        volume = 0.0
        for face in faces:
            p = [v.co for v in face.verts]
            for i in range(1, len(p) - 1):
                volume += p[0].dot(p[i].cross(p[i + 1])) / 6
        assert abs(volume) > .04, volume
        indices = sorted(f.index for f in faces)
        face_indices.extend(indices)
        selected.append(dict(bounds=[lo, hi], faces=indices, originalSignedVolume=volume))
    bm.free()
    assert len(selected) == 10 and len(face_indices) == 60
    replacement = original.copy()
    replacement.data = original.data.copy()
    replacement.name = OWNED
    bpy.data.collections['OLD_EXTERIOR'].objects.link(replacement)
    blue = bpy.data.objects['OLD_NEXT_EXTERIOR156_horizontal_blue_caps'].data.materials[0].copy()
    blue.name = 'OLD_EXTERIOR168_blue_painted_dormer_jambs'
    replacement.data.materials.append(blue)
    blue_index = len(replacement.data.materials) - 1
    mesh = bmesh.new()
    mesh.from_mesh(replacement.data)
    mesh.faces.ensure_lookup_table()
    for part in selected:
        if part['originalSignedVolume'] < 0:
            for index in part['faces']:
                mesh.faces[index].normal_flip()
    for index in face_indices:
        mesh.faces[index].material_index = blue_index
    mesh.to_mesh(replacement.data)
    mesh.free()
    replacement.data.update()
    original.hide_render = True
    original.hide_set(True)
    return dict(alreadyApplied=False, addedObjects=[OWNED], archivedObjects=[SOURCE], changedObjects=[],
                affectedComponents=selected, affectedFaceIndices=sorted(face_indices),
                sourceURL='https://webbyates.com/projects/the-old-building/',
                sourceFile='data/collections/campus_photos_round2/images/OLD/OLD_old_webbyates_06.jpg',
                projectCompletionYear=2024, photographCaptureDate='unknown', uploadDate='unknown',
                limitations=['Ten blue outer jamb components identified in five photographed lower dormers only',
                             'Existing blue colour is copied; no colour calibration claimed',
                             'Dimensions, depth, roof slope, cream returns, upper white surrounds and unseen left dormer retained',
                             'No new surfaces; vertex positions, corner UV and collision relationships remain exact',
                             'Sixty existing inward-wound jamb faces are reversed in the clone only; original retained'])
