"""Add reviewed stage-21 interiors without overwriting the edition-20 archive."""
from pathlib import Path
import hashlib,json,math
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
STAGE=ROOT/'result/blender/stage21'
BASE=ROOT/'result/blender/LSE_campus_detailed_v20.blend'
MODEL=ROOT/'result/blender/LSE_campus_detailed_v21.blend'
bpy.ops.wm.open_mainfile(filepath=str(BASE))
original=set(bpy.data.objects.keys())
review={b['code']:b for b in json.loads((ROOT/'result/blender/stage20/building-review.json').read_text())['buildings']}
for record in review.values():
 record.update(addedObjects=[],replacedObjects=[],changes=[],status='reviewed-no-change')
rooms=json.loads((ROOT/'result/blender/stage20/room-studies.json').read_text())['buildings']
for group in ['ocs','library','construction']:
 folder=STAGE/group
 records=json.loads((folder/'manifest.json').read_text())['buildings']
 objects=[o for r in records for o in r.get('addedObjects',[])]
 names=[o['name'] for o in objects]
 assert len(set(names))==len(names) and not set(names)&set(bpy.data.objects.keys())
 for record in records:
  assert not record.get('replacedObjects'), 'This additive pass must preserve existing geometry'
  code=record['code'];current=review[code]
  for field in ['changes','sources','limitations','addedObjects']:
   current.setdefault(field,[]).extend(record.get(field,[]))
  for key in ['interiorSections','interiorSectionScope','recommendedText']:
   if key in record:current[key]=record[key]
  if record.get('roomStudy'):
   study=record['roomStudy'];name=code+'_PUBLIC_INTERIOR_study'
   placeholder=bpy.data.collections.get(name)
   if placeholder:
    assert not placeholder.all_objects
    bpy.data.collections.remove(placeholder)
   col=bpy.data.collections.new(name);col['roomSample']=True;col['roomLabel']=study['label']
   scene=bpy.data.scenes.new('ROOM21_'+code);scene.collection.children.link(col)
   camera=bpy.data.objects.new(code+'_ROOM21_camera',bpy.data.cameras.new(code+'_ROOM21_camera'))
   scene.collection.objects.link(camera);camera.location=study['camera'];camera.rotation_euler=(Vector(study['target'])-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.lens=36;scene.camera=camera
   rooms.append({'code':code,**study,'sources':record.get('sources',[])})
 if names:
  with bpy.data.libraries.load(str(folder/'refined.blend'),link=False) as (available,imported):
   assert set(names)<=set(available.objects);imported.objects=names
  loaded={o.name:o for o in imported.objects}
  for entry in objects:
   obj=loaded[entry['name']];bpy.data.collections[entry['collection']].objects.link(obj)
   assert obj.type=='MESH' and obj.data.vertices and not obj.hide_render
   assert all(math.isfinite(x) for v in obj.data.vertices for x in v.co)
assert original<=set(bpy.data.objects.keys())
assert len(rooms)==19 and len({r['code'] for r in rooms})==19
campus=bpy.data.scenes['00_CAMPUS_COMPLETE']
for room in rooms:
 assert all(o.name not in campus.objects for o in bpy.data.collections[room['code']+'_PUBLIC_INTERIOR_study'].all_objects)
for record in review.values():
 record['status']='refined' if record['addedObjects'] else 'reviewed-no-change'
bpy.context.window.scene=campus
bpy.ops.wm.save_as_mainfile(filepath=str(MODEL))
report={'version':21,'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'sourceModelSha256':hashlib.sha256(MODEL.read_bytes()).hexdigest(),'buildings':list(review.values())}
(STAGE/'building-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(STAGE/'room-studies.json').write_text(json.dumps({'version':21,'buildings':rooms},ensure_ascii=False,indent=2)+'\n')
print('EDITION21_COMBINED',len(rooms),'room samples',flush=True)
