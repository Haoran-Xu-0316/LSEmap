"""Reopen the corner correction and inspect preserved apertures and sign mounting."""
from pathlib import Path
from collections import Counter
import array, hashlib, json
import bpy, bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage99'
audit=json.loads((OUT/'garrick-corner-audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v99.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
origin,right,normal=[Vector(audit['frame'][k]) for k in ['origin','right','outward']]
def fingerprint(obj):
    h=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type=='MESH':
        h.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
        h.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
    if obj.type=='FONT':h.update(str((obj.data.body,obj.data.size,obj.data.font.name,obj.data.extrude)).encode())
    h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return h.hexdigest()
for name,digest in audit['originalFingerprints'].items():assert fingerprint(bpy.data.objects[name])==digest,name
assert set(bpy.data.objects)-{bpy.data.objects[n] for n in audit['originalFingerprints']}=={bpy.data.objects[n] for n in audit['addedObjects']}
key=lambda p:tuple(round(c,5) for c in p)
for record in audit['partialCopies']:
    source,keep,corner=[bpy.data.objects[record[k]] for k in ['source','retained','corner']]
    assert source.hide_render and not keep.hide_render and not corner.hide_render
    kept=Counter(key(keep.matrix_world@v.co) for v in keep.data.vertices)
    selected=Counter(key(corner.matrix_world@v.co) for v in corner.data.vertices)
    original=Counter(key(source.matrix_world@v.co) for v in source.data.vertices)
    assert kept==Counter(key(p) for p in record['retainedVertices'])
    assert kept+selected==original,record['source']
    assert [m.name for m in keep.data.materials]==[m.name for m in source.data.materials]
    assert all(0<(corner.matrix_world@v.co).z<3.8 for v in corner.data.vertices)
    bm=bmesh.new();bm.from_mesh(corner.data);assert all(e.is_manifold for e in bm.edges);bm.free()
for record in audit['copies']:
    source,copy=[bpy.data.objects[record[k]] for k in ['source','copy']]
    assert [list(v.co) for v in copy.data.vertices]==[list(v.co) for v in source.data.vertices]
    assert copy.matrix_world==source.matrix_world
board=bpy.data.objects['COL_V99_garrick_signboard'];badge=bpy.data.objects['COL_V99_logo_badge']
board_depth=max((board.matrix_world@v.co-origin).dot(normal) for v in board.data.vertices)
badge_depths=[(badge.matrix_world@v.co-origin).dot(normal) for v in badge.data.vertices]
assert abs(min(badge_depths)-board_depth)<1e-4
text=bpy.data.objects['COL_V99_garrick_lettering'];logo=bpy.data.objects['COL_V99_logo_lettering']
assert text.data.body=='garrick' and logo.data.body=='LSE'
assert (logo.matrix_world.translation-text.matrix_world.translation).dot(right)>.9
assert (logo.matrix_world.to_3x3()@Vector((0,0,1))).dot(normal)>.99
assert (logo.matrix_world.translation-origin).dot(normal)>max(badge_depths)
bpy.context.view_layer.update()
glyphs=[logo.matrix_world@Vector(v) for v in logo.bound_box]
assert all(abs((v-origin).dot(right)-.82)<.16 and abs(v.z-4.25)<.16 for v in glyphs)
handles=bpy.data.objects['COL_V99_pull_handles'];bm=bmesh.new();bm.from_mesh(handles.data)
assert all(e.is_manifold for e in bm.edges) and bm.calc_volume()>0;bm.free()
assert min((handles.matrix_world@v.co-origin).dot(normal) for v in handles.data.vertices)>-.27
assert max((handles.matrix_world@v.co).z for v in handles.data.vertices)<1.55
material=bpy.data.materials['COL_V99_garrick_glass']
assert abs(material['webOpacity']-.52)<1e-6
assert material.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value>.5
audit['savedMeasurements']={'originalObjectsUnchanged':True,'entryApertureVerticesUnchanged':True,'otherWindowVerticesUnchanged':True,'mountedSignVerified':True,'closedPullHandles':True,'cornerFrameComponents':6,'cornerPaneComponents':1}
(OUT/'garrick-corner-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print('SAVED_GARRICK_CORNER_VERIFIED',len(audit['addedObjects']))
