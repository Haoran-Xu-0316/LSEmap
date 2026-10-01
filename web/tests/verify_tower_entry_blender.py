"""Reopen the saved shared entrance and verify measurements and preserved parts."""
from pathlib import Path
import array,hashlib,json
from collections import Counter
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage88'
audit=json.loads((OUT/'tower-entry-audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v88.blend'))
def fingerprint(obj,materials=True):
    digest=hashlib.sha256(str([list(r) for r in obj.matrix_world]).encode())
    if obj.type=='MESH':
        digest.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
        digest.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
    if materials:
        digest.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return digest.hexdigest()
assert all(fingerprint(bpy.data.objects[n])==v for n,v in audit['baselineFingerprint'].items())
assert set(bpy.data.objects.keys())-set(audit['baselineFingerprint'])==set(audit['addedObjects'])
for name in audit['hiddenObjects']:
    assert bpy.data.objects[name].hide_render
for record in audit['doorCopies']:
    assert fingerprint(bpy.data.objects[record['source']],False)==fingerprint(bpy.data.objects[record['copy']],False)
origin,right,outward=[Vector(audit['frame'][k]) for k in ['origin','right','outward']]
def local(obj,v):
    p=obj.matrix_world@v.co-origin
    return Vector((p.dot(right),p.dot(outward),p.z))
def parts(mesh):
    seen=set()
    for v in mesh.verts:
        if v in seen or not v.link_faces:
            continue
        seen.add(v);todo=[v];group=[]
        while todo:
            p=todo.pop();group.append(p)
            for e in p.link_edges:
                q=e.other_vert(p)
                if q not in seen:
                    seen.add(q);todo.append(q)
        yield group
def measurements(obj):
    mesh=bmesh.new();mesh.from_mesh(obj.data)
    result=[]
    for group in parts(mesh):
        points=[local(obj,v) for v in group]
        lo=[min(p[i] for p in points) for i in range(3)]
        hi=[max(p[i] for p in points) for i in range(3)]
        result.append({'min':lo,'max':hi,'centre':[(lo[i]+hi[i])/2 for i in range(3)]})
    mesh.free()
    return result
frames=measurements(bpy.data.objects['PAN_D5_entry88_dark_door_frame'])
uprights=sorted([m for m in frames if m['max'][2]-m['min'][2]>3],key=lambda m:m['centre'][0])
assert len(uprights)==2
clear=uprights[1]['min'][0]-uprights[0]['max'][0]
assert abs(clear-.98)<.0001,clear
control=measurements(bpy.data.objects['PAN_D5_entry88_control_metal'])
assert len(control)==1 and abs(control[0]['centre'][2]-.78)<.0001
def signatures(obj,exclude):
    mesh=bmesh.new();mesh.from_mesh(obj.data)
    removed=set()
    for group in parts(mesh):
        points=[local(obj,v) for v in group]
        centre=sum(points,Vector())/len(points)
        if exclude(centre):
            removed.update(f for v in group for f in v.link_faces)
    result=Counter((f.material_index,tuple(sorted(tuple(round(float(c),6) for c in local(obj,v)) for v in f.verts))) for f in mesh.faces if f not in removed)
    mesh.free()
    return result
for family in ['ground_glass','ground_mullions']:
    source=bpy.data.objects['PAN_D3_'+family]
    retained=bpy.data.objects['PAN_D5_entry88_retained_'+family]
    def excluded(c):
        if family=='ground_glass':
            return abs(c.x-1.96)<.01 and abs(c.y+.15)<.01 and abs(c.z-1.99)<.01
        return min(abs(c.x-1.3),abs(c.x-2.6))<.01 and abs(c.y+.05)<.01 and abs(c.z-2)<.01
    assert signatures(source,excluded)==signatures(retained,lambda c:False),family
audit['savedMeasurements']={'originalObjectsUnchanged':True,'retainedGlazingAndFramesUnchanged':True,
                             'revolvingDoorGeometryUnchanged':True,'clearWidthMetres':clear,
                             'controlCentreMetres':control[0]['centre'][2]}
(OUT/'tower-entry-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print('SAVED_TOWER_ENTRY_VERIFIED',audit['savedMeasurements'],flush=True)
