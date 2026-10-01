"""Inspect saved KSW groove depth, preserved source objects and retained vertices."""
from pathlib import Path
import array,hashlib,json
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage90'
audit=json.loads((OUT/'kingsway-rustication-audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v90.blend'))
def fingerprint(obj):
    digest=hashlib.sha256(str([list(r)for r in obj.matrix_world]).encode())
    if obj.type=='MESH':
        digest.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
    digest.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return digest.hexdigest()
assert all(fingerprint(bpy.data.objects[n])==value for n,value in audit['baselineFingerprint'].items())
assert set(bpy.data.objects.keys())-set(audit['baselineFingerprint'])=={r['copy']for r in audit['copies']}
assert all(bpy.data.objects[n].hide_render for n in audit['hiddenObjects'])
origin,normal=[Vector(audit['frame'][key])for key in ['origin','normal']]
levels=audit['jointCentres']
measurements=[]
for record in audit['copies']:
    source=bpy.data.objects[record['source']]
    copy=bpy.data.objects[record['copy']]
    points=[copy.matrix_world@v.co for v in copy.data.vertices]
    retained=0
    for vertex in source.data.vertices:
        p=source.matrix_world@vertex.co
        if any(abs(p.z-z)<=audit['jointHalfWidth']+1e-5 for z in levels):
            continue
        assert min((p-q).length for q in points)<1e-5
        retained+=1
    mesh=bmesh.new();mesh.from_mesh(copy.data)
    assert all(edge.is_manifold for edge in mesh.edges)
    assert mesh.calc_volume(signed=True)>0
    volume=mesh.calc_volume(signed=True);mesh.free()
    assert set(m.name for m in copy.data.materials)=={'KSW_V90_red_block_face','KSW_V90_recessed_red_joint'}
    assert any(face.material_index==1 for face in copy.data.polygons)
    assert not copy.hide_render
    measurements.append({'name':copy.name,'retainedOriginalVertices':retained,'positiveVolume':volume})
# Straight pier fronts originally lie at depth zero. Test every groove, including
# both shoulder edges, independently of the builder's component records.
piers=bpy.data.objects['KSW_D5_rustic90_brick_lower_piers']
points=[piers.matrix_world@v.co for v in piers.data.vertices]
depths=[]
for z in levels:
    strip=[(p-origin).dot(normal)for p in points if abs(abs(p.z-z)-audit['jointHalfWidth'])<2e-5]
    outer=[(p-origin).dot(normal)for p in points if abs(abs(p.z-z)-(audit['jointHalfWidth']+audit['shoulderWidth']))<2e-5]
    assert strip and outer
    front=max(strip);shoulder=max(outer)
    assert abs((shoulder-front)-.055)<2e-5,(z,front,shoulder)
    depths.append({'height':z,'depth':shoulder-front})
audit['savedMeasurements']={'originalObjectsUnchanged':True,'retainedVerticesOutsideJoints':True,
                            'copies':measurements,'visibleGrooves':depths}
(OUT/'kingsway-rustication-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print('SAVED_KINGSWAY_RUSTICATION_VERIFIED',depths,flush=True)
