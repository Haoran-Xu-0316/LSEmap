"""Photo-guided Peacock frontage and unequal upper volumes.
Run in Blender Text Editor. Dimensions and unseen elevations are estimates.
"""
from pathlib import Path
import bpy,json,sys,math,hashlib,array
from mathutils import Vector,Matrix
from mathutils.geometry import tessellate_polygon
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage62';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,Facade,materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v61.blend'));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];col=bpy.data.collections['PEA_EXTERIOR']
def protected():
 h=hashlib.sha256();excluded=set(col.all_objects)
 for o in sorted(bpy.data.objects,key=lambda o:o.name):
  if o in excluded:continue
  h.update(o.name.encode());h.update(str([list(r)for r in o.matrix_world]).encode())
  if o.type=='MESH':
   h.update(array.array('f',[c for v in o.data.vertices for c in v.co]).tobytes());h.update(array.array('i',[l.vertex_index for l in o.data.loops]).tobytes());h.update(str([m.name if m else None for m in o.data.materials]).encode())
 return h.hexdigest()
before=protected();hidden=[]
for o in list(col.all_objects):
 if o.type in {'MESH','FONT','CURVE'}:o.hide_render=True;o.hide_set(True);hidden.append(o.name)
profile=next(p for p in json.loads((ROOT/'result/blender/stage05/infill-geometry.json').read_text())if p['code']=='PEA');wall=next(w for w in profile['walls']if w['front']);groups={};f=Facade(profile,wall,groups);u=Vector((*f.u,0));n=Vector((*f.n,0));origin=Vector((*wall['p'],0));materials.clear()
colors={'stone':(.66,.65,.60),'panel':(.09,.105,.135),'frame':(.54,.56,.54),'dark':(.028,.033,.038),'glass':(.19,.23,.23),'gold':(.50,.36,.12),'brick':(.20,.13,.10),'display':(.69,.68,.61),'lamp':(.94,.62,.20),'white':(.78,.78,.72)}
for key,color in colors.items():
 m=bpy.data.materials.new('PEA_V62_'+key);m.use_nodes=True;m.diffuse_color=(*color,1);s=m.node_tree.nodes['Principled BSDF'];s.inputs['Base Color'].default_value=m.diffuse_color;s.inputs['Roughness'].default_value=.23 if key=='glass'else .65;s.inputs['Metallic'].default_value=.55 if key in {'gold','frame'}else 0
 if key=='lamp':s.inputs['Emission Color'].default_value=(*color,1);s.inputs['Emission Strength'].default_value=2
 if key=='brick':
  texture=m.node_tree.nodes.new('ShaderNodeTexBrick');texture.inputs['Scale'].default_value=1;texture.inputs['Brick Width'].default_value=.215;texture.inputs['Row Height'].default_value=.07;texture.inputs['Mortar Size'].default_value=.008;texture.inputs['Color1'].default_value=(*color,1);texture.inputs['Color2'].default_value=(.27,.19,.14,1);texture.inputs['Mortar'].default_value=(.13,.13,.12,1);uv=m.node_tree.nodes.new('ShaderNodeTexCoord');m.node_tree.links.new(uv.outputs['UV'],texture.inputs['Vector']);m.node_tree.links.new(texture.outputs['Color'],s.inputs['Base Color']);m['siteDetail']=True
 materials[key]=m
ring=[((Vector((*p,0))-origin).dot(u),(Vector((*p,0))-origin).dot(n))for p in profile['building']['rings'][0]]
# Clip the GIS footprint at the evidenced division between the upper wing and low side.
upper=[]
for a,b in zip(ring,ring[1:]+ring[:1]):
 if a[0]>=-1e-6:upper.append(a)
 if (a[0]<0)!=(b[0]<0):
  t=-a[0]/(b[0]-a[0]);upper.append((0,a[1]+t*(b[1]-a[1])))
# Remove consecutive coincident clipping vertices.
upper=[p for i,p in enumerate(upper)if math.dist(p,upper[i-1])>1e-5]
def mesh(name,key):
 k=name+'_'+key
 if k not in groups:groups[k]=Geometry('PEA','exterior62_'+k,key)
 return groups[k]
def point(x,d,z):return Vector(f.point(x,z,d))
def cap(name,key,poly,z):
 g=mesh(name,key);pts=[point(x,d,z)for x,d in poly]
 for tri in tessellate_polygon([pts]):
  tri=[pts[v] if isinstance(v,int) else v for v in tri]
  if (tri[1]-tri[0]).cross(tri[2]-tri[0]).z<0:tri.reverse()
  g.add(tri,[(0,1,2)])
def box(name,key,x,z,w,h,depth=.25,offset=-.12):
 mesh(name,key).box(f.point(x,z,offset),(w,depth,h),f.angle)
# Low podium side/rear walls; photograph confirms pale side facing SAW.
for a,b in zip(ring,ring[1:]+ring[:1]):
 if abs(a[1])<.12 and abs(b[1])<.12:continue
 pts=[point(*a,z)for z in [0,6.58]]+[point(*b,z)for z in [6.58,0]];mesh('podium_side','stone').add(pts,[(0,1,2,3)])
cap('podium_roof','stone',ring,6.60)
# Upper wing side panel is dark brick within a pale edge, rather than extra windows.
for a,b in zip(upper,upper[1:]+upper[:1]):
 if abs(a[1])<.12 and abs(b[1])<.12:continue
 pts=[point(*a,z)for z in [6.60,19.5]]+[point(*b,z)for z in [19.5,6.60]];mesh('upper_side','brick'if abs(a[0])<.01 and abs(b[0])<.01 else 'stone').add(pts,[(0,1,2,3)])
cap('upper_roof','stone',upper,19.5)
left=f.length;right=-5.37;total=left-right;cx=(left+right)/2
# Continuous dark-blue frontage, pale ground entry and poster-lined right return.
box('podium_front','panel',cx,5.11,total,2.64,.20,.10)
box('canopy','panel',cx,3.48,total+.30,.63,2.02,.87)
box('canopy_soffit','dark',cx,3.15,total+.25,.04,2.0,.87)
entry_x=left*.46;entry_w=3.82
box('ground_dark','dark',cx,1.55,total,3.10,.15,-.04)
# Beige ticket office and entrance surround occupy the photographed left section.
for a,b in [(entry_x+entry_w/2,left),(entry_x-entry_w/2-1.12,entry_x-entry_w/2)]:
 if b>a:box('ground_stone','stone',(a+b)/2,1.56,b-a,3.12,.25,.04)
box('entry_glazing','glass',entry_x,1.42,entry_w,2.78,.035,.06)
for j in range(4):box('entry_mullion','dark',entry_x-entry_w/2+j*entry_w/3,1.42,.09,2.78,.10,.15)
for z in [.12,1.02,2.80]:box('entry_rail','dark',entry_x,z,entry_w,.08,.10,.15)
for j in range(3):box('door_handle','gold',entry_x-entry_w/2+(j+.5)*entry_w/3,1.22,.035,.35,.045,.22)
box('ticket_glass','glass',left-1.03,1.72,1.13,1.03,.035,.185)
for dx in [-.61,.61]:box('ticket_frame','dark',left-1.03+dx,1.72,.055,1.14,.08,.22)
for z in [1.17,2.27]:box('ticket_frame','dark',left-1.03,z,1.25,.055,.08,.22)
poster_xs=[right+1.0,right+2.45,right+3.90]
for x in poster_xs:
 box('poster_case','frame',x,1.78,1.06,1.76,.08,.08);box('poster_blank','display',x,1.78,.94,1.64,.015,.128)
for j in range(19):
 x=right+.42+j*(total-.84)/18
 for angle in [0,math.pi/2,math.pi/4,-math.pi/4]:
  # Decorative eight-point brass starbursts, four thin crossed strips.
  g=mesh('starburst','gold');v=Vector(f.point(x,5.14,.219));axis=u*math.cos(angle)+Vector((0,0,1))*math.sin(angle);cross=Vector((0,0,1))*math.cos(angle)-u*math.sin(angle)
  pts=[v+axis*a+cross*b+n*d for d in [-.008,.008]for a,b in [(-.12,-.008),(.12,-.008),(.12,.008),(-.12,.008)]];g.add(pts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
for j in range(1,12):box('panel_joint','dark',right+j*total/12,5.11,.012,2.62,.016,.211)
# Right-side roof louvres stop below the upper wing.
for j in range(4):box('roof_louvre','dark',right/2,6.81+j*.20,-right-.10,.09,.46,.04)
for x in [right+.08,right/2,-.08]:box('louvre_post','frame',x,7.14,.045,.86,.20,.17)
box('louvre_cap','stone',right/2,7.66,-right+.18,.18,.75,.09)
# Three upper rows, three single-light window columns with narrow fanlights.
for row in range(3):
 lo=7.16+row*3.82;hi=lo+2.62;pitch=left/3;width=1.48
 for j in range(3):
  x=(j+.5)*pitch
  for side in [-1,1]:box('upper_pier','stone',x+side*(pitch+width)/4,(lo+hi)/2,(pitch-width)/2,hi-lo,.30,-.10)
  box('upper_glass','glass',x,(lo+hi)/2,width,hi-lo,.035,-.165)
  for side in [-1,1]:box('window_jamb','frame',x+side*width/2,(lo+hi)/2,.045,hi-lo,.09,.065)
  for z in [lo,hi,hi-.46]:box('window_rail','frame',x,z,width,.045,.09,.065)
  box('sill','frame',x,lo-.035,width+.12,.065,.23,.015)
 a=6.60 if row==0 else lo-1.20
 box('upper_spandrel','stone',left/2,(a+lo)/2,left,lo-a,.30,-.10)
 if row==2:box('upper_spandrel','stone',left/2,(hi+19.5)/2,left,19.5-hi,.30,-.10)
# Pale trim on the exposed brick side along the top and front corner.
box('upper_corner','stone',.08,13.05,.22,12.9,.38,-.04)
box('upper_coping','stone',left/2,19.47,left+.08,.12,.42,.015)
box('vertical_sign','white',left-.22,12.01,.61,12.24,.37,.42)
# Warm canopy bulbs follow a perimeter row and dense central entrance rows.
for row in range(4):
 a,b=(right+.20,left-.20)if row==0 else(entry_x-entry_w/2,entry_x+entry_w/2)
 count=round((b-a)/.26)
 for j in range(count):box('canopy_bulb','lamp',a+(j+.5)*(b-a)/count,3.08,.04,.10,.04,1.81-row*.43)
for g in groups.values():
 o=g.finish()
 for modifier in list(o.modifiers):o.modifiers.remove(modifier)
def label(body,x,z,size,key,depth):
 c=bpy.data.curves.new('PEA_exterior62_sign','FONT');c.body=body;c.align_x='CENTER';c.size=size;c.extrude=.002;c.materials.append(materials[key]);o=bpy.data.objects.new(c.name,c);col.objects.link(o);o.location=f.point(x,z,depth);right_vec=Vector((0,0,1)).cross(n);o.rotation_euler=Matrix((right_vec,Vector((0,0,1)),n)).transposed().to_euler()
label('PEACOCK THEATRE',left*.45,3.36,.31,'gold',1.90);label('LSE',right+.46,3.36,.26,'gold',1.90)
for i,char in enumerate('PEACOCK THEATRE'):label(char,left-.22,17.50-i*.83,.44,'dark',.617)
assert protected()==before,'Other buildings or interiors changed'
for name in ['room-studies.json','room-spaces.json','building-review.json']:(OUT/name).write_bytes((ROOT/'result/blender/stage61'/name).read_bytes())
audit={'version':62,'baseline':61,'protectedBefore':before,'protectedAfter':protected(),'hiddenObjects':hidden,'frontWall':wall,'lowerFootprint':ring,'upperFootprint':upper,'podiumHeight':6.6,'upperHeight':19.5,'windowColumns':3,'windowRows':3,'starbursts':19,'posters':3,'limitations':['Mass division and all heights estimated from GIS and venue photography; not surveyed','Rear and party elevations lack independent photo confirmation','Adjacent SAW brick chimney not assigned to PEA; interiors retained unchanged'],'references':['data/建筑图片/PEA_Peacock Theatre/01_建筑实拍/campus_photos_round3_PEA_sadlers_gallery_03.jpg','data/collections/campus_photos_round3/images/PEA/PEA_sadlers_gallery_02.jpg'],'sourcePages':['https://www.sadlerswells.com/your-visit/peacock-theatre/','https://feixandmerlin.com/peacock-theatre-external/']}
(OUT/'peacock-exterior-audit.json').write_text(json.dumps(audit,indent=2)+'\n');bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v62.blend'));print('PEACOCK_EXTERIOR_SAVED')
