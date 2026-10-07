"""Certify exterior glazing shells and retain authored optical colours.

This changes physical surface orientation/rendering, not photographic facade
shape or undocumented interiors. Closed glass is outward and single-sided;
open sheets retain two-sided visibility. Original meshes and finishes survive.
"""
import re
import bpy
import bmesh

PREFIX = 'GLASS181_'


def is_glazing(material):
    name = material.name.lower()
    return 'glass' in name or name.endswith('glazing') or ('glazing' in name and 'optics' in name)


def surface_components(mesh, slot):
    pending = {face for face in mesh.faces if face.material_index == slot}
    result = []
    while pending:
        seed = pending.pop(); group = {seed}; stack = [seed]
        while stack:
            for edge in stack.pop().edges:
                for neighbour in edge.link_faces:
                    if neighbour in pending:
                        pending.remove(neighbour); group.add(neighbour); stack.append(neighbour)
        edges = {edge for face in group for edge in face.edges}
        closed = all(sum(face in group for face in edge.link_faces) == 2 for edge in edges)
        volume = sum(face.verts[0].co.dot(face.verts[i].co.cross(face.verts[i+1].co))/6
                     for face in group for i in range(1,len(face.verts)-1)) if closed else 0
        result.append((group, closed and abs(volume)>1e-10, volume))
    return result


def apply_exterior_glass181():
    scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    if scene.get('exteriorGlazing181'):
        return dict(alreadyApplied=True,addedObjects=[],archivedObjects=[],changedObjects=[])
    cache = {}; records = []; codes = set()
    for source in list(bpy.data.objects):
        if source.type != 'MESH' or source.hide_render: continue
        owners = [c for c in source.users_collection if c.name.endswith('_EXTERIOR')]
        if not owners: continue
        codes.update(c.name.removesuffix('_EXTERIOR') for c in owners)
        slots = [i for i,m in enumerate(source.data.materials) if m and is_glazing(m)
                 and any(f.material_index==i for f in source.data.polygons)]
        if not slots: continue
        mesh = bmesh.new(); mesh.from_mesh(source.data)
        groups = {slot:surface_components(mesh,slot) for slot in slots}
        needs = any(closed for rows in groups.values() for _,closed,_ in rows) or any(
            source.data.materials[slot].node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value > 0 for slot in slots)
        if not needs: mesh.free(); continue
        target = source.copy(); target.data = source.data.copy(); target.name = PREFIX+source.name
        target.data.name = target.name
        for owner in source.users_collection: owner.objects.link(target)
        closed_count = inward_count = open_count = 0; bindings = []
        determinant = source.matrix_world.to_3x3().determinant()
        assert abs(determinant)>1e-12
        for slot,rows in groups.items():
            original = source.data.materials[slot]
            assigned = {}
            for faces,closed,volume in rows:
                closed_count += int(closed); open_count += int(not closed)
                if closed and volume*determinant < 0:
                    # Reverse winding with loop UV attached to its original vertex.
                    bmesh.ops.reverse_faces(mesh,faces=list(faces)); inward_count += 1
                key = (original.name,closed)
                if key not in cache:
                    material = original.copy(); material.name = PREFIX+('shell_' if closed else 'sheet_')+original.name
                    material.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value = 0
                    material['webClosedGlazing'] = closed
                    material['surfacePolicy'] = 'Outward closed shell uses front faces; open panes remain two-sided. Authored colour/opacity retained.'
                    cache[key] = material
                if key not in assigned:
                    target.data.materials.append(cache[key]); assigned[key]=len(target.data.materials)-1
                    bindings.append(dict(sourceSlot=slot,targetSlot=assigned[key],sourceMaterial=original.name,material=cache[key].name,closed=closed))
                for face in faces: face.material_index=assigned[key]
        mesh.to_mesh(target.data); mesh.free(); target.data.update()
        target['surfaceCorrection181']=True
        source.hide_render=True;source.hide_set(True)
        records.append(dict(source=source.name,target=target.name,code=owners[0].name.removesuffix('_EXTERIOR'),closedShells=closed_count,reversedShells=inward_count,openSheets=open_count,bindings=bindings))
    scene['exteriorGlazing181']=True
    return dict(alreadyApplied=False,addedObjects=[r['target'] for r in records],archivedObjects=[r['source'] for r in records],changedObjects=[],records=records,
                exteriorCollectionsChecked=sorted(codes),closedShells=sum(r['closedShells'] for r in records),reversedShells=sum(r['reversedShells'] for r in records),
                scope='Physical glass orientation and nonmetal finish across existing exterior components; colours, opacity, vertices and per-corner UV retained. No facade reconstruction or full interior claim.',
                sources=['https://threejs.org/docs/pages/Material.html','https://threejs.org/docs/pages/MeshStandardMaterial.html'])
