"""Photo-guided Pethick-Lawrence entrance, run in Blender Text Editor.
Existing tower mass, upper elevations and interiors are preserved estimates.
"""
from pathlib import Path
import bpy,bmesh,json,hashlib,array,sys,math
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage61';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,Facade,materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v60.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];col=bpy.data.collections['PEL_EXTERIOR']
def protected():
 h=hashlib.sha256();excluded=set(col.all_objects)
 for o in sorted(bpy.data.objects,key=lambda o:o.name):
  if o in excluded:continue
  h.update(o.name.encode());h.update(str([list(r)for r in o.matrix_world]).encode())
  if o.type=='MESH':
   h.update(array.array('f',[c for v in o.data.vertices for c in v.co]).tobytes());h.update(array.array('i',[l.vertex_index for l in o.data.loops]).tobytes());h.update(str([m.name if m else None for m in o.data.materials]).encode())
 return h.hexdigest()
before=protected();profile=next(p for p in json.loads((ROOT/'result/blender/stage05/infill-geometry.json').read_text())if p['code']=='PEL');wall=next(w for w in profile['walls']if w['front']);groups={};f=Facade(profile,wall,groups);origin=Vector((*wall['p'],0));u=Vector((*f.u,0));n=Vector((*f.n,0));removed={};hidden=[]
# Remove complete connected construction members in the photographed lower face.
# Preserve upper members and other elevations rather than masking them with a box.
for o in list(col.all_objects):
 if o.type=='FONT' or any(k in o.name for k in ['entrance_door','entrance_jambs','door_leaves','door_inset_glass','door_handles','threshold','yellow_portal','entrance_red_wayfinding_panel','wayfinding_mounting_plate']):
  o.hide_render=True;o.hide_set(True);hidden.append(o.name);continue
 if o.type!='MESH' or o.hide_render:continue
 bm=bmesh.new();bm.from_mesh(o.data);seen=set();delete=[]
 for v in list(bm.verts):
  if v in seen:continue
  stack=[v];component=[];seen.add(v)
  while stack:
   q=stack.pop();component.append(q)
   for e in q.link_edges:
    w=e.other_vert(q)
    if w not in seen:seen.add(w);stack.append(w)
  pts=[o.matrix_world@q.co for q in component];c=sum(pts,Vector())/len(pts);d=(c-origin).dot(n);x=(c-origin).dot(u)
  if max(p.z for p in pts)<6.78 and -.4<d<.5 and .01<x<f.length-.01:delete.extend(component)
 if delete:removed[o.name]=len(delete);bmesh.ops.delete(bm,geom=delete,context='VERTS');bm.to_mesh(o.data);o.data.update()
 bm.free()
materials.clear()
colors={'silver':(.57,.59,.58),'yellow':(.73,.48,.035),'dark':(.045,.052,.052),'glass':(.15,.20,.19),'white':(.8,.8,.76),'red':(.62,.015,.021)}
for key,color in colors.items():
 mat=bpy.data.materials.new('PEL_V61_'+key);mat.use_nodes=True;mat.diffuse_color=(*color,1);shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=mat.diffuse_color;shader.inputs['Roughness'].default_value=.28 if key in {'silver','glass'}else .64;shader.inputs['Metallic'].default_value=.6 if key=='silver'else .05
 materials[key]=mat
x=f.length/2;entry_width=5.0;lo=3.35;top=6.72;box_width=5.25;window_width=3.0;window_lo=4.07;window_hi=5.86
for side in [-1,1]:
 f.box('entry61_yellow_reveal','yellow',x+side*2.42,1.63,.22,3.26,.72,.39)
 f.box('entry61_box_cheek','silver',x+side*(box_width+window_width)/4,(lo+top)/2,(box_width-window_width)/2,top-lo,.78,.40)
 f.box('entry61_window_reveal','yellow',x+side*window_width/2,(window_lo+window_hi)/2,.08,window_hi-window_lo,.40,.61)
for z,h in [((lo+window_lo)/2,window_lo-lo),((window_hi+top)/2,top-window_hi)]:f.box('entry61_box_spandrel','silver',x,z,box_width,h,.78,.40)
f.box('entry61_upper_glass','glass',x,(window_lo+window_hi)/2,window_width,window_hi-window_lo,.035,.49)
for z in [window_lo,window_hi]:f.box('entry61_window_reveal','yellow',x,z,window_width,.075,.40,.61)
for j in range(4):f.box('entry61_upper_mullion','dark',x-window_width/2+j*window_width/3,(window_lo+window_hi)/2,.045,window_hi-window_lo,.09,.55)
f.box('entry61_canopy_fascia','silver',x,3.36,5.68,.55,1.5,.85)
f.box('entry61_canopy_soffit','dark',x,3.10,5.65,.035,1.48,.85)
# Shallow dark perforation rows describe the photographed metal fascia economically.
for row in range(3):
 for j in range(40):f.box('entry61_fascia_slots','dark',x-2.72+j*.14,3.20+row*.14,.027,.05,.01,1.605)
for j in range(1,7):
 seam_x=x-box_width/2+j*box_width/7
 spans=[(lo,top)] if abs(seam_x-x)>window_width/2 else [(lo,window_lo),(window_hi,top)]
 for a,b in spans:f.box('entry61_box_panel_seam','dark',seam_x,(a+b)/2,.012,b-a,.015,.798)
# Glazed entry with a cylindrical revolving enclosure on the left and side door.
f.box('entry61_back_glass','glass',x,1.55,4.62,2.95,.04,.02)
for dx in [-2.3,.35,2.3]:f.box('entry61_entry_mullion','silver',x+dx,1.55,.07,2.95,.09,.13)
f.box('entry61_entry_transom','silver',x,2.70,4.62,.07,.10,.13)
center_x=x-.86;center_d=.49;radius=.99
shell=Geometry('PEL','entry61_revolving_glass','glass')
for j in range(20):
 a=math.pi*j/20;b=math.pi*(j+1)/20
 pts=[f.point(center_x+radius*math.cos(t),z,center_d+radius*math.sin(t))for z in [.15,2.68]for t in [a,b]]
 shell.add(pts,[(0,1,3,2)])
for t in [0,math.pi/3,2*math.pi/3,math.pi]:
 f.box('entry61_revolving_post','silver',center_x+radius*math.cos(t),1.415,.045,2.53,.045,center_d+radius*math.sin(t))
f.box('entry61_threshold','silver',x,.055,5.05,.11,1.75,.48)
f.box('entry61_side_door_handle','silver',x+1.7,1.23,.035,.48,.06,.23)
for g in list(groups.values())+[shell]:
 o=g.finish()
 for modifier in list(o.modifiers):o.modifiers.remove(modifier)
def label(body,px,pz,size,key,depth):
 curve=bpy.data.curves.new('PEL_entry61_sign','FONT');curve.body=body;curve.align_x='CENTER';curve.size=size;curve.extrude=.001;curve.materials.append(materials[key]);o=bpy.data.objects.new(curve.name,curve);col.objects.link(o);o.location=f.point(px,pz,depth);right=Vector((0,0,1)).cross(n);o.rotation_euler=Matrix((right,Vector((0,0,1)),n)).transposed().to_euler()
f.box('entry61_logo_board','red',x+2.25,3.38,.32,.32,.025,1.62)
# The logo block is finished after lettering because it was appended above.
groups['entry61_logo_board_red'].finish();label('LSE',x+2.25,3.30,.19,'white',1.642);label('Pethick-Lawrence House',x-.08,3.31,.22,'dark',1.642)
assert protected()==before,'Other buildings or interiors changed'
for filename in ['room-studies.json','room-spaces.json','building-review.json']:(OUT/filename).write_bytes((ROOT/'result/blender/stage60'/filename).read_bytes())
audit={'version':61,'baseline':60,'protectedBefore':before,'protectedAfter':protected(),'removedMembers':removed,'hiddenObjects':hidden,'frontWall':wall,'canopyWidth':5.68,'canopyFrontDepth':1.60,'boxHeight':[lo,top],'windowHeight':[window_lo,window_hi],'revolvingSegments':20,'reference':'data/建筑图片/PEL_Pethick-Lawrence House/01_建筑实拍/exteriors_lse_estate_023.jpg','limitations':['Undated low-resolution estate photo and 2021 public-realm photographs; dimensions and colors estimated','Existing upper tower windows, footprint, height and roof remain unverified','Interior preserved; not a complete floor-plan reconstruction']}
(OUT/'pethick-entrance-audit.json').write_text(json.dumps(audit,indent=2)+'\n');bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v61.blend'));print('PETHICK_ENTRANCE_SAVED',len(removed))
