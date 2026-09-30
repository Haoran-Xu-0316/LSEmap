"""Read-only verification of saved continuous Aldwych window belts."""
from pathlib import Path
import bpy,json
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v64.blend'));p=ROOT/'result/blender/stage64/aldwych-belts-audit.json';a=json.loads(p.read_text())
for key,count in a['removedMembers'].items():assert count==(144 if 'window_piers' in key else 72),(key,count)
pilaster=bpy.data.objects['61A_D5_belt64_continuous_pilaster_trim'];heights=[]
for i in range(0,len(pilaster.data.vertices),8):
 pts=[pilaster.matrix_world@v.co for v in pilaster.data.vertices[i:i+8]];height=max(v.z for v in pts)-min(v.z for v in pts);assert abs(height-10.8)<.0001;heights.append(height)
assert len(heights)==24
metal=bpy.data.objects['61A_D5_belt64_metal_spandrel_spandrel'];assert len(metal.data.vertices)//8==96
for i in range(0,len(metal.data.vertices),8):
 pts=[metal.matrix_world@v.co for v in metal.data.vertices[i:i+8]];assert min(v.z for v in pts)>7.79 and max(v.z for v in pts)<18.61
roof=bpy.data.objects['61A_D5_pavilion63_hip_roof'];assert len(roof.data.polygons)==8
profile=json.loads((ROOT/'result/blender/stage07/aldwych-geometry.json').read_text());joint=bpy.data.objects['61A_D5_belt64_clipped_stone_joint_shadow'];assert len(joint.data.vertices)//8==len(a['clippedJointSegments'])
for i,record in enumerate(a['clippedJointSegments']):
 w=profile['walls'][record['wall']];origin=Vector((*w['p'],0));u=Vector(((w['q'][0]-w['p'][0])/w['length'],(w['q'][1]-w['p'][1])/w['length'],0));points=[joint.matrix_world@v.co for v in joint.data.vertices[i*8:i*8+8]];lo=min((v-origin).dot(u)for v in points);hi=max((v-origin).dot(u)for v in points)
 assert abs(lo-record['start'])<.0001 and abs(hi-record['end'])<.0001
 if record['windowLow']<record['height']<record['windowHigh']:assert hi<=record['windowLeft']+.0001 or lo>=record['windowRight']-.0001
assert bpy.data.objects[a['hiddenOldJoint']].hide_render
a['savedMeasurements']={'continuousPilasters':len(heights),'pilasterHeights':heights,'metalSpandrels':96,'retainedPavilionFaces':8,'verifiedClippedJoints':len(a['clippedJointSegments'])};p.write_text(json.dumps(a,indent=2)+'\n');print('SAVED_ALDWYCH_BELTS_VERIFIED')
