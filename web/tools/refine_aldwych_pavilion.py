"""Photo-guided chamfered roof pavilion at 61 Aldwych.
Run in Blender Text Editor. Historic built photo, not the proposed LSE extension.
"""
from pathlib import Path
import bpy,json,sys,math,array,hashlib
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage63';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,Facade,materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v62.blend'));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];col=bpy.data.collections['61A_EXTERIOR']
def digest(o):
 h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
 if o.type=='MESH':h.update(array.array('f',[c for v in o.data.vertices for c in v.co]).tobytes());h.update(array.array('i',[l.vertex_index for l in o.data.loops]).tobytes())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode());return h.hexdigest()
before={o.name:digest(o)for o in bpy.data.objects};hidden=[]
for o in list(col.all_objects):
 if any(k in o.name for k in ['corner_pavilion','corner_roof','pavilion_glass','pavilion_posts','pavilion_band']):o.hide_render=True;o.hide_set(True);hidden.append(o.name)
assert len(hidden)>=5,hidden
materials.clear()
for key,color in {'stone':(.64,.62,.57),'trim':(.71,.69,.64),'glass':(.16,.21,.21),'bronze':(.12,.115,.085),'slate':(.14,.16,.17)}.items():
 m=bpy.data.materials.new('61A_V63_'+key);m.use_nodes=True;m.diffuse_color=(*color,1);s=m.node_tree.nodes['Principled BSDF'];s.inputs['Base Color'].default_value=m.diffuse_color;s.inputs['Roughness'].default_value=.22 if key=='glass'else .70;s.inputs['Metallic'].default_value=.4 if key=='bronze'else 0;materials[key]=m
profile=json.loads((ROOT/'result/blender/stage07/aldwych-geometry.json').read_text());angle=math.atan2(profile['front']['q'][1]-profile['front']['p'][1],profile['front']['q'][0]-profile['front']['p'][0]);cx,cy=-37.6,-120.;groups={}
def point(x,y,z):return Vector((cx+math.cos(angle)*x-math.sin(angle)*y,cy+math.sin(angle)*x+math.cos(angle)*y,z))
ring=[(-2.9,-4.5),(2.9,-4.5),(4.5,-2.9),(4.5,2.9),(2.9,4.5),(-2.9,4.5),(-4.5,2.9),(-4.5,-2.9)];roof=Geometry('61A','pavilion63_hip_roof','slate');edge_records=[]
for i,(a,b) in enumerate(zip(ring,ring[1:]+ring[:1])):
 p,q=point(*a,0),point(*b,0);length=(q-p).length;out=(p+q)/2-Vector((cx,cy,0));out.normalize();f=Facade(profile,{'p':list(p[:2]),'q':list(q[:2]),'length':length,'outward':list(out[:2])},groups);width=2.75 if i%2==0 else 1.30;x=length/2;lo,hi=30.62,32.55
 for side in [-1,1]:
  f.box('pavilion63_stone_pier','stone',x+side*(length+width)/4,(lo+hi)/2,(length-width)/2,hi-lo,.30,-.09)
  f.box('pavilion63_lower_jamb','bronze',x+side*width/2,(lo+hi)/2,.055,hi-lo,.12,.075)
 for z,h in [((29.80+lo)/2,lo-29.80),((hi+33.80)/2,33.80-hi)]:f.box('pavilion63_lower_band','stone',x,z,length,h,.30,-.09)
 f.box('pavilion63_lower_glass','glass',x,(lo+hi)/2,width,hi-lo,.035,-.12)
 for z in [lo,hi,hi-.46]:f.box('pavilion63_lower_rail','bronze',x,z,width,.055,.12,.075)
 if i%2==0:
  for fraction in [-1/6,1/6]:f.box('pavilion63_lower_mullion','bronze',x+width*fraction,(lo+hi)/2,.05,hi-lo,.10,.075)
 # The clerestory wraps all chamfered faces, rather than four square walls.
 f.box('pavilion63_clerestory_glass','glass',x,34.50,length-.16,1.24,.035,-.06)
 count=max(2,round(length/1.15))
 for j in range(count+1):f.box('pavilion63_clerestory_post','bronze',.08+j*(length-.16)/count,34.50,.075,1.40,.13,.045)
 for z in [33.83,35.20]:f.box('pavilion63_cornice','trim',x,z,length+.02,.16,.40,.05)
 # Continuous octagonal hip roof, preserving the native roof location and peak.
 pa,pb=point(a[0]*1.12,a[1]*1.12,35.35),point(b[0]*1.12,b[1]*1.12,35.35);peak=point(0,0,37.70);verts=[pa,pb,peak]
 if (pb-pa).cross(peak-pa).z<0:verts.reverse()
 roof.add(verts,[(0,1,2)]);edge_records.append({'side':i,'length':length,'windowWidth':width,'isChamfer':i%2==1})
 # A small stone base breaks the finial into a foot and taper, not a solid stick.
finial=Geometry('61A','pavilion63_finial','slate');finial.box(point(0,0,37.74),(.30,.30,.16),angle)
for z0,z1,r0,r1 in [(37.82,38.10,.13,.075),(38.10,38.48,.075,.008)]:
 for j in range(8):
  a,b=2*math.pi*j/8,2*math.pi*(j+1)/8;finial.add([point(r0*math.cos(a),r0*math.sin(a),z0),point(r0*math.cos(b),r0*math.sin(b),z0),point(r1*math.cos(b),r1*math.sin(b),z1),point(r1*math.cos(a),r1*math.sin(a),z1)],[(0,1,2,3)])
for g in list(groups.values())+[roof,finial]:
 o=g.finish()
 for m in list(o.modifiers):o.modifiers.remove(m)
changed=[o.name for o in bpy.data.objects if o.name in before and digest(o)!=before[o.name]];assert changed==[],changed
for name in ['room-studies.json','room-spaces.json','building-review.json']:(OUT/name).write_bytes((ROOT/'result/blender/stage62'/name).read_bytes())
audit={'version':63,'baseline':62,'changedExistingGeometry':changed,'hiddenObjects':hidden,'sides':edge_records,'center':[cx,cy],'angle':angle,'roofEave':35.35,'roofPeak':37.7,'lowerWindows':8,'reference':'data/建筑图片/61A_61 Aldwych/01_建筑实拍/campus_photos_round2_61A_aldwych_survey_01.jpg','limitations':['Built project photo is undated and not proof of 2026 site condition','Pavilion size and window divisions estimated; existing tower location and height retained','Main street facade, roof dormers, hidden elevations and LSE interior conversion still need review','2025 winning redevelopment renderings not treated as built architecture']};(OUT/'aldwych-pavilion-audit.json').write_text(json.dumps(audit,indent=2)+'\n');bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v63.blend'));print('ALDWYCH_PAVILION_SAVED')
