"""Correct remaining roof-pavilion glass metallic and alpha authoring.

Eighteen outward pane outlines and web opacity remain unchanged. Both native and web previews use alpha on one surface per pane.
"""
import bpy
import bmesh
from mathutils import Vector

SOURCES = ('CKK_D5_pavilion80_glazing_glass',)
PREFIX = 'CKK_EXTERIOR173_'


def apply_ckk_glass173():
    """Clone the existing pavilion batch in the loaded scene; never open or save the campus."""
    names = [PREFIX + source.removeprefix('CKK_') for source in SOURCES]
    if all(name in bpy.data.objects for name in names):
        return dict(alreadyApplied=True, addedObjects=names,
                    archivedObjects=list(SOURCES), changedObjects=[])
    if any(name in bpy.data.objects for name in names):
        raise RuntimeError('Incomplete CKK173 component already present')
    sources = [bpy.data.objects[name] for name in SOURCES]
    replacements = {}
    for source, name in zip(sources, names):
        clone = source.copy()
        clone.data = source.data.copy()
        clone.name = name
        clone.data.name = name
        for collection in source.users_collection:
            collection.objects.link(clone)
        for index, material in enumerate(source.data.materials):
            if material is None:
                continue
            if material.name not in replacements:
                replacement = material.copy()
                replacement.name = PREFIX + material.name
                shader = next(n for n in replacement.node_tree.nodes
                              if n.type == 'BSDF_PRINCIPLED')
                shader.inputs['Metallic'].default_value = 0.0
                shader.inputs['Roughness'].default_value = 0.16
                shader.inputs['Alpha'].default_value = 0.55
                shader.inputs['Transmission Weight'].default_value = 0.12
                replacement.diffuse_color = (*replacement.diffuse_color[:3], 0.55)
                shader.inputs['IOR'].default_value = 1.5
                replacement['opticalEstimate'] = 'Dielectric clear pavilion estimate; single native alpha surface avoids double attenuation; existing webOpacity retained'
                replacements[material.name] = replacement
            clone.data.materials[index] = replacements[material.name]
        # Each original pane is a closed thin box. Retain its outward main
        # face so webOpacity is applied once, without changing frame apertures.
        mesh = bmesh.new()
        mesh.from_mesh(clone.data)
        center = sum((v.co for v in mesh.verts), Vector()) / len(mesh.verts)
        seen = set()
        retained = set()
        for seed in mesh.verts:
            if seed in seen:
                continue
            todo = [seed]
            seen.add(seed)
            group = []
            while todo:
                vertex = todo.pop()
                group.append(vertex)
                for edge in vertex.link_edges:
                    other = edge.other_vert(vertex)
                    if other not in seen:
                        seen.add(other)
                        todo.append(other)
            faces = {face for vertex in group for face in vertex.link_faces}
            largest = max(face.calc_area() for face in faces)
            candidates = [face for face in faces if face.calc_area() > largest * 0.99]
            outward = sum((vertex.co for vertex in group), Vector()) / len(group) - center
            retained.add(max(candidates, key=lambda face: face.normal.dot(outward)))
        if len(retained) != 18:
            mesh.free()
            raise RuntimeError('Expected eighteen pavilion panes')
        bmesh.ops.delete(mesh, geom=[face for face in mesh.faces if face not in retained], context='FACES')
        bmesh.ops.delete(mesh, geom=[vertex for vertex in mesh.verts if not vertex.link_faces], context='VERTS')
        mesh.to_mesh(clone.data)
        mesh.free()
        clone.data.update()
        clone.hide_render = False
        clone.hide_viewport = False
        clone.hide_set(False)
        source.hide_render = True
        source.hide_set(True)
    return dict(alreadyApplied=False, addedObjects=names,
                archivedObjects=list(SOURCES), changedObjects=[])
