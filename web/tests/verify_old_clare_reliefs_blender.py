"""Inspect the saved Clare Market reliefs independently before export."""
from pathlib import Path
import array, hashlib, json
import bpy, bmesh
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage89'
audit = json.loads((OUT/'old-clare-reliefs-audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v89.blend'))
def fingerprint(obj):
    digest = hashlib.sha256(str([list(r) for r in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        digest.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return digest.hexdigest()
assert all(fingerprint(bpy.data.objects[n]) == value for n,value in audit['baselineFingerprint'].items())
assert set(bpy.data.objects.keys())-set(audit['baselineFingerprint']) == set(audit['addedObjects'])
origin,right,outward = [Vector(audit['frame'][k]) for k in ['origin','right','outward']]
measured = []
for record in audit['panels']:
    obj = bpy.data.objects[record['name']]
    vertices = [obj.matrix_world@v.co-origin for v in obj.data.vertices]
    horizontal = [v.dot(right)-record['centre'] for v in vertices]
    depths = [v.dot(outward) for v in vertices]
    heights = [v.z for v in vertices]
    assert max(map(abs,horizontal)) < audit['width']/2
    assert min(heights) > 5.34 and max(heights) < 6.37
    assert min(depths) >= .074-1e-4 and max(depths) < .24, (min(depths),max(depths))
    mesh = bmesh.new();mesh.from_mesh(obj.data)
    assert all(e.is_manifold for e in mesh.edges)
    seen=set();componentVolumes=[]
    for vertex in mesh.verts:
        if vertex in seen:
            continue
        todo=[vertex];seen.add(vertex);verticesInPart=[]
        while todo:
            current=todo.pop();verticesInPart.append(current)
            for edge in current.link_edges:
                other=edge.other_vert(current)
                if other not in seen:
                    seen.add(other);todo.append(other)
        faces={face for current in verticesInPart for face in current.link_faces}
        centre=sum((v.co for v in verticesInPart),Vector())/len(verticesInPart)
        signed=0
        for face in faces:
            points=[v.co-centre for v in face.verts]
            for j in range(1,len(points)-1):
                signed+=points[0].dot(points[j].cross(points[j+1]))/6
        assert signed > 0, (record['panel'],signed)
        componentVolumes.append(signed)
    volume = mesh.calc_volume(signed=True)
    assert volume > 0
    mesh.free()
    measured.append({'panel':record['panel'],'volume':volume,
                     'componentVolumes':componentVolumes,'vertexCount':len(vertices),'depthRange':[min(depths),max(depths)]})
# The five profiles must not be duplicated placeholders.
assert len({fingerprint(bpy.data.objects[n]) for n in audit['addedObjects']}) == 5
audit['savedMeasurements']={'originalObjectsUnchanged':True,'closedPositiveVolumes':measured,
                            'interpretedPanels':[1,2,3,4,5],'unresolvedPanels':['side']}
(OUT/'old-clare-reliefs-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print('SAVED_CLARE_RELIEFS_VERIFIED',measured,flush=True)
