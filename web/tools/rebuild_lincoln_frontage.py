"""Rebuild Lincoln Chambers' street character from the 2025 LSE photograph.

Run in Blender's Text Editor. This is an isolated review candidate. Facade
registration, dimensions and roof pitches are estimates, not a measured survey.
"""
from pathlib import Path
import array, hashlib, json, math, sys
import bpy
from mathutils import Vector, Matrix
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web/tools'))
from facade_geometry import Geometry, Facade, materials
OUT=ROOT/'result/blender/stage42';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v41.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
for scene in bpy.data.scenes:
 for layer in scene.view_layers:layer.update()
collection=bpy.data.collections['LCH_EXTERIOR']
owned=set(collection.all_objects)
def fingerprint(obj):
 h=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
 if obj.type=='MESH':
  h.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
  h.update(array.array('i',[v.vertex_index for v in obj.data.loops]).tobytes())
 return h.hexdigest()
protected={o.name:fingerprint(o) for o in bpy.data.objects if o not in owned}
profile=next(p for p in json.loads((ROOT/'result/blender/stage05/infill-geometry.json').read_text()) if p['code']=='LCH')
ring=profile['building']['rings'][0]
p,q=Vector(ring[0]),Vector(ring[2]);u=(q-p).normalized();normal=Vector((-u.y,u.x))
groups={}
front=Facade(profile,{'p':list(p),'q':list(q),'length':(q-p).length,'outward':list(normal)},groups)
L=front.length;mid=L/2
old=profile['walls'][0];oldmid=(Vector(old['p'])+Vector(old['q']))/2
angle=front.angle-math.atan2(old['q'][1]-old['p'][1],old['q'][0]-old['p'][0])
newmid=(p+q)/2
transfer=Matrix.Translation(Vector((*newmid,0)))@Matrix.Rotation(angle,4,'Z')@Matrix.Translation(-Vector((*oldmid,0)))
# Preserve the established three-arch porch; replace only generic shell/shopwork.
remove_tags=['ground_shop','ground_stone_apron','ground_shop_head']
removed=[];preserved=[]
for obj in list(collection.all_objects):
 keep=obj.type=='FONT' or (obj.type=='MESH' and any(m and m.name.startswith('LCH12_') for m in obj.data.materials) and not any(tag in obj.name for tag in remove_tags))
 if keep:
  obj.matrix_world=transfer@obj.matrix_world;preserved.append(obj.name)
 elif obj.type=='CAMERA':
  obj.matrix_world=transfer@obj.matrix_world
 else:
  removed.append(obj.name);bpy.data.objects.remove(obj,do_unlink=True)
materials.clear()
for name,colour in {'brick':(.32,.16,.095),'stone':(.63,.61,.56),'frame':(.76,.75,.69),'glass':(.14,.16,.165),'slate':(.12,.145,.16),'metal':(.04,.045,.045)}.items():
 mat=bpy.data.materials.new('LCH_V42_'+name);mat.use_nodes=True;mat.diffuse_color=(*colour,1)
 shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=mat.diffuse_color
 shader.inputs['Roughness'].default_value=.28 if name=='glass' else .72
 materials[name]=mat
# Use the same metric brick shader contract as other native facade materials.
mat=materials['brick'];nodes=mat.node_tree.nodes;brick=nodes.new('ShaderNodeTexBrick')
for key,value in {'Color1':(.30,.14,.075,1),'Color2':(.39,.21,.13,1),'Mortar':(.17,.155,.13,1),'Scale':1,'Brick Width':.215,'Row Height':.075,'Mortar Size':.004}.items():brick.inputs[key].default_value=value
uv=nodes.new('ShaderNodeTexCoord');mat.node_tree.links.new(uv.outputs['UV'],brick.inputs['Vector']);mat.node_tree.links.new(brick.outputs['Color'],nodes['Principled BSDF'].inputs['Base Color'])
def box(name,mat,x,z,w,h,depth=.25,offset=-.12):
 front.box('V42_'+name,mat,x,z,w,h,depth,offset)
def window(x,lo,hi,w,depth=0,parts=1):
 box('window_glass','glass',x,(lo+hi)/2,w,hi-lo,.04,depth-.10)
 for xx in [x-w/2,x+w/2]:box('window_jamb','frame',xx,(lo+hi)/2,.075,hi-lo+.08,.12,depth)
 for zz in [lo,hi,(lo+hi)/2]:box('sash_rail','frame',x,zz,w,.065,.12,depth)
 for i in range(1,parts):box('window_mullion','frame',x-w/2+w*i/parts,(lo+hi)/2,.06,hi-lo,.12,depth)
 # Slender glazing bars in the upper sash.
 for xx in [x-w/6,x+w/6]:box('upper_glazing_bar','frame',xx,(lo+hi*3)/4,.022,(hi-lo)/2,.06,depth+.01)
 box('window_sill','stone',x,lo-.10,w+.24,.16,.42,depth)

def rectangular_wall(x0,x1,lo,hi,openings,mat='brick',offset=-.12):
 # Openings are rectangular; wall pieces stop at their boundaries.
 cursor=x0
 for x,w,bottom,top in sorted(openings):
  left,right=x-w/2,x+w/2
  box('wall_piers',mat,(cursor+left)/2,(lo+hi)/2,left-cursor,hi-lo,.32,offset)
  box('wall_spandrel',mat,x,(lo+bottom)/2,w,bottom-lo,.32,offset)
  box('wall_head',mat,x,(top+hi)/2,w,hi-top,.32,offset)
  cursor=right
 box('wall_piers',mat,(cursor+x1)/2,(lo+hi)/2,x1-cursor,hi-lo,.32,offset)

# G: two wide white shop windows, small-paned upper lights and opaque risers.
for side in [-1,1]:
 x0,x1=(.18,mid-2.10) if side<0 else (mid+2.10,L-.18)
 x=(x0+x1)/2;w=x1-x0-.35
 rectangular_wall(x0,x1,0,4.25,[(x,w,.38,3.35)],'stone')
 box('shop_riser','frame',x,.68,w,.65,.10,.06)
 window(x,1.02,3.35,w,depth=.08,parts=3)
 box('shop_transom','frame',x,2.73,w,.10,.14,.1)
 for i in range(1,12):box('shop_upper_lights','frame',x-w/2+w*i/12,3.04,.026,.62,.08,.1)
box('ground_entablature','stone',mid,4.29,L,.22,.55,.05)
# Upper floors: canted outer bays, two flanking sash windows, central feature.
bay_width=2.70
for side in [-1,1]:
 x=.30+bay_width/2 if side<0 else L-.30-bay_width/2
 # Stone-faced projecting front with three lights; angled cheeks connect to brick.
 for lo,hi in [(4.45,7.55),(7.55,10.65)]:
  w=1.46;bottom=lo+.30;top=hi-.35
  rectangular_wall(x-w/2-.15,x+w/2+.15,lo,hi,[(x,w,bottom,top)],'stone',offset=.63)
  window(x,bottom,top,w,.80,parts=2)
  for sign in [-1,1]:
   start=Vector(front.point(x+sign*(w/2+.15),0,.78)[:2]);end=Vector(front.point(x+sign*bay_width/2,0,.04)[:2])
   tangent=(end-start).normalized();n=Vector((-tangent.y,tangent.x))
   if n.dot(normal)<0:n.negate()
   face=Facade(profile,{'p':list(start),'q':list(end),'length':(end-start).length,'outward':list(n)},groups)
   length=face.length
   # A narrow recessed light in each canted cheek.
   for xx in [.08,length-.08]:face.box('V42_bay_corner_stone','stone',xx,(lo+hi)/2,.16,hi-lo,.22,0)
   for zz,hh in [((lo+bottom)/2,bottom-lo),((top+hi)/2,hi-top)]:face.box('V42_bay_cheek_spandrel','stone',length/2,zz,length,hh,.22,0)
   face.box('V42_bay_cheek_glass','glass',length/2,(bottom+top)/2,length-.22,top-bottom,.035,-.025)
   for zz in [bottom,(bottom+top)/2,top]:face.box('V42_bay_cheek_rail','frame',length/2,zz,length-.18,.06,.1,.08)
  box('bay_floor_band','stone',x,hi,bay_width,.20,.94,.35)
 # Coped gable profile follows the listed feature; exact height is estimated.
 group=front.group('V42_bay_gable','stone')
 group.add([front.point(x-bay_width/2,10.70,.8),front.point(x+bay_width/2,10.70,.8),front.point(x,12.0,.8)],[(0,1,2)])
# Brick spandrels between projecting bays and central stone field.
central_width=3.80
for left,right in [(3.0,mid-central_width/2),(mid+central_width/2,L-3.0)]:
 x=(left+right)/2;w=min(1.05,right-left-.3)
 for lo,hi in [(4.45,7.55),(7.55,10.65)]:
  rectangular_wall(left,right,lo,hi,[(x,w,lo+.30,hi-.35)])
  window(x,lo+.30,hi-.35,w,parts=1)
# The central first-floor arch is a real opening, not glass over a solid wall.
radius=1.48;spring=5.48;bottom=4.70;top=7.55
for side in [-1,1]:box('central_arch_pier','stone',mid+side*(radius+(central_width/2-radius)/2),(4.45+top)/2,central_width/2-radius,top-4.45,.38,.03)
box('central_arch_sill_wall','stone',mid,(4.45+bottom)/2,2*radius,bottom-4.45,.38,.03)
arch_glass=front.group('V42_arch_glass','glass');arch_wall=front.group('V42_arch_spandrel','stone')
for i in range(48):
 a=math.pi*i/48;b=math.pi*(i+1)/48
 xa,za=mid+radius*math.cos(a),spring+radius*math.sin(a)
 xb,zb=mid+radius*math.cos(b),spring+radius*math.sin(b)
 arch_glass.add([front.point(xa,bottom,-.08),front.point(xb,bottom,-.08),front.point(xb,zb,-.08),front.point(xa,za,-.08)],[(0,1,2,3)])
 arch_wall.add([front.point(xa,za,.20),front.point(xb,zb,.20),front.point(xb,top,.20),front.point(xa,top,.20)],[(0,1,2,3)])
front.arch('V42_arch_stone','stone',mid,spring,radius,.16,.23)
front.arch('V42_arch_frame','frame',mid,spring,radius-.055,.055,.08)
for dx in [-radius,-.50,.50,radius]:
 height=spring+math.sqrt(max(0,radius*radius-dx*dx))-bottom
 box('arched_mullion','frame',mid+dx,bottom+height/2,.07,height,.13,.06)
box('arch_sash_transom','frame',mid,5.4,2*radius,.065,.12,.06)
# Second-floor tripartite window and the two short stone columns.
rectangular_wall(mid-central_width/2,mid+central_width/2,7.55,10.65,[(mid,2.96,7.93,10.25)],'stone',offset=.03)
window(mid,7.93,10.25,2.96,.16,parts=3)
for dx in [-.51,.51]:
 box('short_column','stone',mid+dx,9.09,.18,2.32,.26,.27)
 for z in [7.98,10.17]:box('column_capital','stone',mid+dx,z,.32,.16,.34,.27)
for x0,x1 in [(3.0,L-3.0)]:box('upper_cornice','stone',(x0+x1)/2,10.70,x1-x0,.25,.55,.10)
# Keep the mapped rear outline as a plain envelope, explicitly unresolved.
for a,b in zip(ring[2:],ring[3:]+ring[:1]):
 start,end=Vector(a),Vector(b);t=(end-start).normalized();n=Vector((t.y,-t.x))
 wall=Facade(profile,{'p':a,'q':b,'length':(end-start).length,'outward':list(n)},groups)
 wall.box('V42_unobserved_envelope','brick',wall.length/2,5.35,wall.length,10.70,.25,-.10)
roof=front.group('V42_estimated_slate_roof','slate');centre=Vector(profile['building']['center'])
low=[Vector(p) for p in ring];high=[centre+(p-centre)*.74 for p in low]
for i in range(len(low)):
 j=(i+1)%len(low)
 roof.add([(*low[i],10.83),(*low[j],10.83),(*high[j],13.5),(*high[i],13.5)],[(0,1,2,3)])
for tri in profile['building']['triangles']:
 roof.add([(*(centre+(Vector(p)-centre)*.74),13.5) for p in tri],[(0,1,2)])
for geometry in groups.values():geometry.finish()
for scene in bpy.data.scenes:
 for layer in scene.view_layers:layer.update()
assert all(fingerprint(bpy.data.objects[name])==value for name,value in protected.items())
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'lincoln-frontage-candidate.blend'))
# Preview GLB cannot transfer the brick node graph; retain its base tint.
brick_material=materials['brick']
base=brick_material.node_tree.nodes['Principled BSDF'].inputs['Base Color']
for link in list(base.links):brick_material.node_tree.links.remove(link)
base.default_value=brick_material.diffuse_color
for obj in bpy.context.scene.objects:obj.select_set(False)
for obj in collection.all_objects:obj.hide_set(False);obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'lch-preview.glb'),export_format='GLB',use_selection=True,use_active_scene=True,export_cameras=False,export_lights=False)
(OUT/'frontage-audit.json').write_text(json.dumps({'baseline':'LSE_campus_detailed_v41.blend','preservedPorchObjects':preserved,'removedGenericObjects':removed,'protectedObjectsUnchanged':len(protected),'frontageLengthEstimate':L,'porchShiftEstimate':list(newmid-oldmid),'references':'data/collections/lincoln-review/sources.json','limitations':['Full frontage registration remains photographic estimate','Rear envelope and roof are simplified; dormers not located','No interior added'],'publication':'Candidate only; visual review required'},ensure_ascii=False,indent=2)+'\n')
print('LINCOLN_FRONTAGE_CANDIDATE',len(groups))
