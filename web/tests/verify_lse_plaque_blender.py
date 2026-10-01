"""Independently reopen vector plaques and measure geometry and mounting."""
from pathlib import Path
import array,hashlib,json
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage100'
audit=json.loads((OUT/'plaque-lettering-audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v100.blend'))
def fingerprint(obj):
    h=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type=='MESH':
        h.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
        h.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
    if obj.type=='FONT':h.update(str((obj.data.body,obj.data.size,obj.data.font.name,obj.data.extrude)).encode())
    h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return h.hexdigest()

for name,digest in audit['originalFingerprints'].items():assert fingerprint(bpy.data.objects[name])==digest,name
new={o.name for o in bpy.data.objects}-set(audit['originalFingerprints'])
assert new=={r['copy'] for r in audit['plaques']}
for r in audit['plaques']:
 old=bpy.data.objects[r['source']];obj=bpy.data.objects[r['copy']]
 assert old.hide_render and not obj.hide_render and obj.type=='MESH'
 horizontal,normal,center=[Vector(r[k]) for k in ['horizontal','normal','supportCenter']]
 points=[obj.matrix_world@v.co for v in obj.data.vertices]
 xs=[(p-center).dot(horizontal) for p in points];zs=[p.z-center.z for p in points];ds=[p.dot(normal)-r['frontDepth'] for p in points]
 assert abs(max(xs)+min(xs))<1e-5 and abs(max(zs)+min(zs))<1e-5
 # World-space float32 coordinates need a 0.03mm rounding tolerance.
 assert abs((max(xs)-min(xs))-r['width']*49.56/79.223)<.00003
 assert abs((max(zs)-min(zs))-r['height']*49.11/79.706)<.00003
 assert min(ds)>.0019 and max(ds)<.0081
 bm=bmesh.new();bm.from_mesh(obj.data)
 assert all(e.is_manifold for e in bm.edges),obj.name
 assert bm.calc_volume()>0,obj.name
 seen=set();count=0
 for v in bm.verts:
  if v in seen:continue
  count+=1;stack=[v];seen.add(v)
  while stack:
   p=stack.pop()
   for e in p.link_edges:
    q=e.other_vert(p)
    if q not in seen:seen.add(q);stack.append(q)
 assert count==3,(obj.name,count)
 bm.free()
audit['savedMeasurements']={'originalObjectsUnchanged':True,'allThreePlaquesMounted':True,'vectorPaddingVerified':True,'closedThreeLetterMeshes':True}
(OUT/'plaque-lettering-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print('SAVED_VECTOR_PLAQUES_VERIFIED',len(audit['plaques']))
