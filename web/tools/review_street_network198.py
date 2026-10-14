"""Inspect the visible native street network without changing the campus source.

Fixed project paths keep the audit reproducible in Blender's Text Editor.
The output supports footprint-level review rather than adding isolated props.
"""
from pathlib import Path
import hashlib
import json
import bpy

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'result/blender/LSE_campus_detailed_v197.blend'
OUTPUT = ROOT / 'result/blender/street-network198'


def review_streets():
    before = hashlib.sha256(BASE.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    bpy.context.window.scene = scene
    roads = []
    for obj in scene.objects:
        if obj.type != 'MESH' or obj.hide_render or not ('Road_' in obj.name or obj.name == 'Local_ground_datum'):
            continue
        points = [list(obj.matrix_world @ vertex.co) for vertex in obj.data.vertices]
        roads.append(dict(name=obj.name, vertices=points, faces=[list(face.vertices) for face in obj.data.polygons],
                          materials=[material.name if material else None for material in obj.data.materials],
                          properties={key:obj[key] for key in obj.keys() if isinstance(obj[key],(str,int,float,bool))},
                          collections=[collection.name for collection in obj.users_collection]))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    record = dict(baseline=str(BASE.relative_to(ROOT)), baselineSha256=before, roads=roads)
    (OUTPUT/'native-road-audit.json').write_text(json.dumps(record,indent=2)+'\n')
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == before
    print('STREET_NETWORK_AUDITED', len(roads), flush=True)


if __name__ == '__main__':
    review_streets()
