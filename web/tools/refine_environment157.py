"""Refine existing campus vegetation shading without changing mapped geometry.

Run in Blender's Text Editor. The saved latest edition can be reopened safely;
only named foliage meshes and their two material finishes are changed.
"""
from pathlib import Path
from array import array
import hashlib
import json
import bpy

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / 'result/blender/LSE_campus_detailed_v157.blend'
BASELINE = ROOT / 'result/blender/LSE_campus_detailed_v156.blend'
REPORT = ROOT / 'result/blender/stage157'
REPORT.mkdir(parents=True, exist_ok=True)
NAMES = ('03_PUBLIC_REALM_Plane_tree_crown', 'SITE_NEXT_PORTSMOUTH_registered_seven_tree_crowns')

def geometry_digest(mesh):
    points = array('f', [0.0]) * (len(mesh.vertices) * 3)
    mesh.vertices.foreach_get('co', points)
    loops = array('i', [0]) * len(mesh.loops)
    mesh.loops.foreach_get('vertex_index', loops)
    digest = hashlib.sha256(points.tobytes() + loops.tobytes()).hexdigest()
    return digest

def refine_environment():
    bpy.ops.wm.open_mainfile(filepath=str(TARGET if TARGET.exists() else BASELINE))
    existing_report = REPORT / 'vegetation-shading.json'
    if TARGET.exists() and existing_report.exists():
        previous = json.loads(existing_report.read_text())
        if hashlib.sha256(TARGET.read_bytes()).hexdigest() == previous['sourceModelSha256']:
            assert all(p.use_smooth for name in NAMES for p in bpy.data.objects[name].data.polygons)
            print('ENVIRONMENT157_ALREADY_CURRENT')
            return
    before = {o.name: geometry_digest(o.data) for o in bpy.data.objects if o.type == 'MESH'}
    records = []
    for name in NAMES:
        obj = bpy.data.objects[name]
        assert obj.type == 'MESH'
        assert all(m and 'plane foliage' in m.name.lower() for m in obj.data.materials)
        flat_before = sum(not p.use_smooth for p in obj.data.polygons)
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
        obj.data.update()
        for material in obj.data.materials:
            material.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .88
        records.append({'object': name, 'vertices': len(obj.data.vertices), 'faces': len(obj.data.polygons), 'flatFacesBefore': flat_before, 'smoothFacesAfter': sum(p.use_smooth for p in obj.data.polygons), 'geometrySha256': before[name]})
    assert before == {o.name: geometry_digest(o.data) for o in bpy.data.objects if o.type == 'MESH'}
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(TARGET))
    (REPORT / 'vegetation-shading.json').write_text(json.dumps({'version': 157, 'changedObjects': records, 'allMeshPositionsAndTopologyUnchanged': True, 'objects': len(bpy.data.objects), 'sourceModelSha256': hashlib.sha256(TARGET.read_bytes()).hexdigest(), 'interpretation': 'Smooth existing crown normals and matte leaf finish; no new botanical or geographic detail.'}, indent=2) + '\n')
    print('ENVIRONMENT157_SAVED', len(bpy.data.objects), len(records))


refine_environment()
