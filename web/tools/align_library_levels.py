"""Align LRB G to the entrance datum while preserving its estimated 4m pitch.

Run in Blender's Text Editor. This corrects the floor-label/datum relationship,
not surveyed elevations or the still-approximate horizontal atrium placement.
"""
from pathlib import Path
import array
import hashlib
import json
import shutil
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage37'
OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v36.blend'
DEST=OUT/'library-levels-candidate.blend'
bpy.ops.wm.open_mainfile(filepath=str(BASE))
# Evaluate every review scene before recording world transforms.
for scene in bpy.data.scenes:
 for layer in scene.view_layers:layer.update()
SHIFT=-4.0

def fingerprint(obj):
 digest=hashlib.sha256(array.array('f',[v for row in obj.matrix_world for v in row]).tobytes())
 if obj.type=='MESH':
  digest.update(array.array('f',[v for p in obj.data.vertices for v in p.co]).tobytes())
  digest.update(array.array('i',[v.vertex_index for v in obj.data.loops]).tobytes())
 return digest.hexdigest()

before={o.name:fingerprint(o) for o in bpy.data.objects}
collection=bpy.data.collections['LRB_PUBLIC_INTERIOR_study']
fixed={'LRB_lift_head_beam','LRB_lift_crossheads'}
continuous={'LRB_white_circular_columns','LRB_lift_guide_rails',
 'LRB_lift_stainless_front_rails','LRB_lift_dark_rear_panel','LRB_lift_cables'}
changes=[]
for obj in collection.all_objects:
 assert obj.parent is None, 'Unexpected hierarchy: avoid double translation'
 if obj.name in fixed:
  continue
 if obj.name in continuous:
  old=[obj.matrix_world@v.co for v in obj.data.vertices]
  low,high=min(p.z for p in old),max(p.z for p in old)
  inverse=obj.matrix_world.inverted()
  for vertex,point in zip(obj.data.vertices,old):
   point.z += SHIFT*(high-point.z)/(high-low)
   vertex.co=inverse@point
  obj.data.update()
  new=[obj.matrix_world@v.co for v in obj.data.vertices]
  assert abs(min(p.z for p in new)-(low+SHIFT))<1e-4
  assert abs(max(p.z for p in new)-high)<1e-4
  action='Extend continuous support downwards, retain roof/shaft top'
 else:
  obj.location.z += SHIFT
  action='Translate complete object and retain local geometry'
 changes.append({'name':obj.name,'action':action})
for scene in bpy.data.scenes:
 for layer in scene.view_layers:layer.update()
allowed={item['name'] for item in changes}
assert all(fingerprint(o)==before[o.name] for o in bpy.data.objects if o.name not in allowed)
for floor,index in [('LG',0),('G',1),('1',2),('2',3),('3',4),('4',5)]:
 objects=[o for o in collection.all_objects if o.get('floorId')==floor]
 assert objects, floor
 heights=[(o.matrix_world@v.co).z for o in objects for v in o.data.vertices]
 assert .32+4*index+SHIFT-.03 <= min(heights) < .32+4*index+SHIFT+.1, (floor,min(heights))
for name in ['room-studies.json','room-spaces.json','building-review.json']:
 shutil.copyfile(ROOT/'result/blender/stage36'/name,OUT/name)
path=OUT/'building-review.json'; review=json.loads(path.read_text())
lrb=next(b for b in review['buildings'] if b['code']=='LRB')
for section in lrb['interiorSections']:
 for key in ['minHeight','maxHeight']:section[key]=round(section[key]+SHIFT,2)
 for key in ['camera','target']:
  if key in section:section[key][2]+=SHIFT
 if section['id']=='LG':section['scope']='官方导览图支持电脑、分组学习与政府出版物区域。LG位于G层下方，地下深度按4米层高估算，非测绘标高。'
 if section['id']=='G':section['scope']='依据官方G层导览图布置LSE LIFE学习区，已移除无依据的通用书架；服务柜台与封闭房间尚未重建。'
lrb['interiorSectionScope']='LG、G、1、2、3、4共6层功能分区。G层对齐入口基准，LG位于其下；层高暂按4米估算。中庭平面位置、房间边界及家具尺度仍待校准，非实测布局。'
lrb['limitations']=[s for s in lrb['limitations'] if 'LG位于Z0.32' not in s]
lrb['limitations'].append('G层Z0.32、LG层Z-3.68，仅修正楼层相对关系；4米层高、顶层与屋顶关系均为估算。未复原5层员工空间。')
path.write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(DEST))
(OUT/'level-alignment-audit.json').write_text(json.dumps({
 'baseline':str(BASE.relative_to(ROOT)), 'candidate':str(DEST.relative_to(ROOT)),
 'source':'data/documents/library_floor_plans.pdf, pp2-7',
 'datumShift':SHIFT,'estimatedFloorPitch':4,'floorSurfaceZ':{f:round(.32+4*i+SHIFT,2) for i,f in enumerate(['LG','G','1','2','3','4'])},
 'changes':changes,'fixedShaftComponents':sorted(fixed),'unchangedObjects':len(before)-len(allowed),
 'checks':['Every floor furniture base follows the new datum','Other buildings and all exterior objects unchanged',
 'Continuous shaft and roof supports keep upper endpoints'],
 'limitations':lrb['limitations'],
 'publication':'Native candidate only; exterior export must omit subterranean interior geometry before promotion'
},ensure_ascii=False,indent=2)+'\n')
print('LIBRARY_LEVELS_ALIGNED',len(changes),'objects; G=0.32, LG=-3.68')
