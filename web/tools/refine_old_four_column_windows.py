"""Rebuild OLD's 24 photographed Houghton windows as four-column casements.
Run in Blender Text Editor. Window centres and openings retain estimated dimensions.
"""
from pathlib import Path
import array,hashlib,json,math,shutil,sys
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage85'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v84.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
frame=json.loads((ROOT/'result/blender/stage52/old-houghton-audit.json').read_text())
origin,right,outward=[Vector(frame[k])for k in ['origin','right','outward']]
def point(x,d,z):return origin+right*x+outward*d+Vector((0,0,z))
def local(o,v):
 d=o.matrix_world@v.co-origin
 return Vector((d.dot(right),d.dot(outward),d.z))
def fingerprint(o):
 h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
 if o.type=='MESH':
  h.update(array.array('f',[c for v in o.data.vertices for c in v.co]).tobytes())
  h.update(array.array('i',[l.vertex_index for l in o.data.loops]).tobytes())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode())
 return h.hexdigest()
before={o.name:fingerprint(o)for o in bpy.data.objects}
windows=[]
for x in [-6.7,6.7]:
 for z,h in [(2.6,2.65),(7.0,2.15)]:
  windows.append({'x':x,'z':z,'w':1.44,'h':h,'d':.13,'family':'main','rows':4,'heavyFraction':.75})
for x in [-6.7,-3.35,0,3.35,6.7]:
 for z,h in [(11.9,3),(16.2,2.2)]:
  windows.append({'x':x,'z':z,'w':1.62,'h':h,'d':.13,'family':'main','rows':4,'heavyFraction':.75})
for x in [-6.7,-3.35,0,3.35,6.7]:
 for d,z,rows,heavy in [(-1.89,23.2,4,.5),(-3.09,26.2,5,.6)]:
  windows.append({'x':x,'z':z,'w':1.54,'h':1.9,'d':d,'family':'mansard','rows':rows,'heavyFraction':heavy})
def in_window(points,w):
 return all(abs(p.x-w['x'])<=w['w']/2+.025 and abs(p.y-w['d'])<.10 and abs(p.z-w['z'])<=w['h']/2+.025 for p in points)
def components(bm):
 seen=set()
 for v in bm.verts:
  if v in seen or not v.link_faces:continue
  stack=[v];seen.add(v);group=[]
  while stack:
   a=stack.pop();group.append(a)
   for e in a.link_edges:
    b=e.other_vert(a)
    if b not in seen:seen.add(b);stack.append(b)
  yield group
# Preserve every original object and edit owned copies of the two shared batches.
retained=[];removed={}
for old in ['OLD_Window_sash_bars','OLD_V52_Houghton_blue']:
 original=bpy.data.objects[old]
 copy=original.copy();copy.data=original.data.copy()
 copy.name='OLD_D5_windows85_retained_'+old.removeprefix('OLD_')
 bpy.data.collections['OLD_EXTERIOR'].objects.link(copy)
 bm=bmesh.new();bm.from_mesh(copy.data);delete=[];count=0
 for group in components(bm):
  positions=[local(copy,v)for v in group]
  if any(in_window(positions,w)for w in windows):
   delete.extend(group);count+=1
 assert count>0,(old,count)
 bmesh.ops.delete(bm,geom=delete,context='VERTS')
 bm.to_mesh(copy.data);bm.free()
 retained.append(copy.name);removed[old]=count
hidden=['OLD_Window_sash_bars','OLD_V52_Houghton_blue',
 'OLD_D5_entablature77_dormer_muntin_blue','OLD_D5_portal79_Window_sash_bars','OLD_D5_portal79_V52_Houghton_blue']
for name in hidden:
 o=bpy.data.objects[name];o.hide_render=True;o.hide_set(True)
materials.clear()
materials['blue']=bpy.data.materials['OLD_Blue_painted_steel'].copy()
materials['blue'].name='OLD_V85_four_column_blue'
bars=Geometry('OLD','windows85_casements','blue')
angle=math.atan2(right.y,right.x)
members=[]
for i,w in enumerate(windows):
 for fraction,width in [(-.25,.025),(0,.048),(.25,.025)]:
  x=w['x']+fraction*w['w']
  bars.box(point(x,w['d'],w['z']),(width,.11,w['h']-.09),angle)
  members.append({'window':i,'kind':'vertical','centre':[x,w['d'],w['z']],'size':[width,.11,w['h']-.09]})
 for j in range(1,w['rows']):
  fraction=j/w['rows'];z=w['z']-w['h']/2+w['h']*fraction
  thickness=.065 if abs(fraction-w['heavyFraction'])<.001 else .025
  bars.box(point(w['x'],w['d']+.015,z),(w['w']-.12,.11,thickness),angle)
  members.append({'window':i,'kind':'horizontal','centre':[w['x'],w['d']+.015,z],'size':[w['w']-.12,.11,thickness]})
new=bars.finish()
for m in list(new.modifiers):new.modifiers.remove(m)
bm=bmesh.new();bm.from_mesh(new.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(new.data);bm.free()
assert len(windows)==24 and len(members)==149
assert all(fingerprint(bpy.data.objects[n])==v for n,v in before.items())
for name in ['room-studies.json','room-spaces.json','building-review.json']:shutil.copyfile(ROOT/'result/blender/stage84'/name,OUT/name)
shutil.copyfile(ROOT/'web/public/models/catalogue.json',OUT/'catalogue-before.json')
audit={'version':85,'baseline':84,'frame':frame,'windows':windows,'members':members,'hiddenObjects':hidden,'retainedObjects':retained,'newBars':new.name,'removedComponents':removed,'addedObjects':retained+[new.name],'baselineFingerprint':before,'referenceUrl':'https://webbyates.com/projects/the-old-building/','reference':'Damian Griffiths full frontal photograph, project completed 2024 and published in 2025 upload path; capture date unknown','limitations':['Four-column casements and horizontal hierarchy follow the full photo; dimensions, exact bar thickness and installation condition estimated','Window openings, centres, whole building, roof and interiors retained; overall massing and unseen elevations still require review']}
(OUT/'old-casement-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v85.blend'))
print('OLD_FOUR_COLUMN_WINDOWS_SAVED',len(windows),len(members),removed,flush=True)
