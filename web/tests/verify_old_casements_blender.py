"""Inspect saved SAW panes against the inherited folded masonry boundaries."""
from pathlib import Path
import array,hashlib,json,math
from collections import Counter
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage85'
a=json.loads((OUT/'old-casement-audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v85.blend'))
def fingerprint(o):
 h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
 if o.type=='MESH':
  h.update(array.array('f',[c for v in o.data.vertices for c in v.co]).tobytes())
  h.update(array.array('i',[l.vertex_index for l in o.data.loops]).tobytes())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode())
 return h.hexdigest()
assert all(fingerprint(bpy.data.objects[n])==v for n,v in a['baselineFingerprint'].items())
assert set(bpy.data.objects.keys())-set(a['baselineFingerprint'])==set(a['addedObjects'])
for n in a['hiddenObjects']:assert bpy.data.objects[n].hide_render
origin,right,outward=[Vector(a['frame'][k])for k in ['origin','right','outward']]
def local(o,v):
 p=o.matrix_world@v.co-origin
 return Vector((p.dot(right),p.dot(outward),p.z))
def groups(bm):
 seen=set()
 for v in bm.verts:
  if v in seen or not v.link_faces:continue
  seen.add(v);todo=[v];part=[]
  while todo:
   q=todo.pop();part.append(q)
   for e in q.link_edges:
    r=e.other_vert(q)
    if r not in seen:seen.add(r);todo.append(r)
  yield part
bars=bpy.data.objects[a['newBars']]
bm=bmesh.new();bm.from_mesh(bars.data)
parts=list(groups(bm));assert len(parts)==149
measured=[]
for part in parts:
 points=[local(bars,v)for v in part]
 lo=[min(p[i]for p in points)for i in range(3)];hi=[max(p[i]for p in points)for i in range(3)]
 measured.append({'centre':[(lo[i]+hi[i])/2 for i in range(3)],'size':[hi[i]-lo[i]for i in range(3)]})
for expected,actual in zip(a['members'],measured):
 assert all(abs(p-q)<.001 for p,q in zip(expected['centre'],actual['centre']))
 assert all(abs(p-q)<.001 for p,q in zip(expected['size'],actual['size']))
assert bm.calc_volume(signed=True)>0;bm.free()
for i,w in enumerate(a['windows']):
 actual=[m for m,e in zip(measured,a['members'])if e['window']==i]
 vertical=[m for m in actual if m['size'][2]>m['size'][0]]
 assert len(vertical)==3
 assert all(abs(m['centre'][0]-x)<.001 for m,x in zip(vertical,[w['x']-w['w']/4,w['x'],w['x']+w['w']/4]))
 horizontal=[m for m in actual if m['size'][0]>m['size'][2]]
 assert len(horizontal)==w['rows']-1
 thick=[m for m in horizontal if m['size'][2]>.05];assert len(thick)==1
 assert abs(thick[0]['centre'][2]-(w['z']-w['h']/2+w['h']*w['heavyFraction']))<.001
for n in a['retainedObjects']:
 o=bpy.data.objects[n];assert not o.hide_render
 bm=bmesh.new();bm.from_mesh(o.data)
 for part in groups(bm):
  positions=[local(o,v)for v in part]
  assert not any(all(abs(p.x-w['x'])<=w['w']/2+.025 and abs(p.y-w['d'])<.10 and abs(p.z-w['z'])<=w['h']/2+.025 for p in positions)for w in a['windows'])
 bm.free()
def face_signatures(o,exclude_windows):
 faces=[]
 for face in o.data.polygons:
  positions=[local(o,o.data.vertices[i])for i in face.vertices]
  if exclude_windows and any(all(abs(p.x-w['x'])<=w['w']/2+.025 and abs(p.y-w['d'])<.10 and abs(p.z-w['z'])<=w['h']/2+.025 for p in positions)for w in a['windows']):continue
  faces.append((face.material_index,tuple(sorted(tuple(round(float(c),6)for c in p)for p in positions))))
 return Counter(faces)
for n in a['retainedObjects']:
 source='OLD_'+n.removeprefix('OLD_D5_windows85_retained_')
 assert face_signatures(bpy.data.objects[n],False)==face_signatures(bpy.data.objects[source],True),source
a['savedMeasurements']={'originalGeometryAndMaterialsUnchanged':True,'windows':24,'fourColumnCasements':24,'verticalMembers':72,'horizontalMembers':77,'allHeavyTransomHeightsVerified':True,'oldWindowBarsRemoved':a['removedComponents'],'retainedOtherWindows':True}
(OUT/'old-casement-audit.json').write_text(json.dumps(a,indent=2)+'\n')
print('SAVED_OLD_CASEMENTS_VERIFIED',a['savedMeasurements'],flush=True)
