"""Reconstruct LRB Portugal Street frontage from the April 2025 survey.
Run in Blender Text Editor. Width registration and unlabelled dimensions are estimates.
Keep the saved roof and all original object geometry; archive replaced facade strips.
"""
from pathlib import Path
import array, hashlib, json, math, shutil, sys
import bpy, bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage110';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v109.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
ring=next(b for b in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings'] if b['code']=='LRB')['rings'][0]
origin,end=[Vector((*ring[i],0))for i in [1,2]];axis=(end-origin).normalized()
# The GIS outline runs clockwise; the left-hand normal faces Portugal Street.
normal=Vector((-axis.y,axis.x,0));length=(end-origin).length;angle=math.atan2(axis.y,axis.x)
collection=bpy.data.collections['LRB_EXTERIOR']
def digest(o):
 h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
 if o.type=='MESH':
  vertices=array.array('f',[0])*(3*len(o.data.vertices));o.data.vertices.foreach_get('co',vertices)
  indices=array.array('i',[0])*len(o.data.loops);o.data.loops.foreach_get('vertex_index',indices)
  h.update(vertices.tobytes());h.update(indices.tobytes())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode());return h.hexdigest()
before={o.name:digest(o)for o in bpy.data.objects};visibility={o.name:o.hide_render for o in bpy.data.objects}
clipped=[]
# Bisect copies in world coordinates. Remove only the outside 0.7m strip along
# this elevation, leaving every other facade and the 2025 roof untouched.
for source in list(collection.all_objects):
 if source.hide_render or source.type!='MESH' or not source.name.startswith('LRB_V109_facade_'):continue
 points=[source.matrix_world@v.co-origin for v in source.data.vertices]
 if not points or max(p.dot(normal)for p in points)<-.70 or max(p.dot(axis)for p in points)<0 or min(p.dot(axis)for p in points)>length:continue
 mesh=source.data.copy();bm=bmesh.new();bm.from_mesh(mesh);inv=source.matrix_world.inverted()
 for p,n in [(origin-normal*.70,normal),(origin,axis),(end,axis)]:
  bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=inv@p,plane_no=source.matrix_world.to_3x3().transposed()@n,dist=1e-6)
 selected=[]
 for face in bm.faces:
  p=source.matrix_world@face.calc_center_median()-origin
  if -.00001<=p.dot(axis)<=length+.00001 and p.dot(normal)>=-.70001:selected.append(face)
 if not selected:bm.free();bpy.data.meshes.remove(mesh);continue
 bmesh.ops.delete(bm,geom=selected,context='FACES');bm.to_mesh(mesh);bm.free();mesh.update()
 source.hide_render=True;source.hide_set(True)
 record={'source':source.name,'removedFaces':len(selected),'copy':None}
 if len(mesh.polygons):
  new=source.copy();new.data=mesh;new.name=source.name.replace('V109_facade','V110_retained');collection.objects.link(new)
  new.hide_render=False;new.hide_set(False);record['copy']=new.name
 else:bpy.data.meshes.remove(mesh)
 clipped.append(record)
assert clipped
materials.clear()
for key,color,rough,metal in [('stone',(.66,.64,.59),.85,0),('brick',(.29,.15,.105),.86,0),('glass',(.17,.22,.235),.17,.08),('frame',(.12,.14,.14),.50,.12),('roof',(.29,.31,.315),.86,0),('rail',(.18,.20,.20),.55,.45)]:
 m=bpy.data.materials.new('LRB_V110_'+key);m.use_nodes=True;m.diffuse_color=(*color,1)
 p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=m.diffuse_color
 p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;materials[key]=m
# Reuse the established metric brick shader rather than adding image textures.
materials['brick']=bpy.data.materials['LRB_V35_warm_brown_brick'].copy();materials['brick'].name='LRB_V110_brick'
for key in ['glass','stone','frame','rail']:
 materials['roof_'+key]=materials[key].copy();materials['roof_'+key].name='LRB_V110_roof_'+key
batches={}
def batch(key):
 if key not in batches:batches[key]=Geometry('LRB','portugal110_'+key,key)
 return batches[key]
def point(x,d,z):return origin+axis*x+normal*d+Vector((0,0,z))
def box(key,x,d,z,w,t,h):batch(key).box(point(x,d,z),(w,t,h),angle)
# Looking from Portugal Street, screen-right runs opposite the GIS edge.
def px(x):return length-(x-119)/1301*length
# Widths are registered proportionally to the retained GIS street segment.
# Heights use the drawing's labelled AOD datum and visually read window edges.
rows=[(5.72,9.16),(10.33,12.45),(13.91,16.06)]
corner=[140,176,212];singleton=302;triple_centres=[428,583,740,895,1050,1205,1360]
loft_centres=[301,396,461,554,617,708,773,864,929,1020,1084,1174,1239,1328,1393]
openings=[]
def window(x,w,lo,hi,cols,panerows,kind,depth=-.075,trim=True):
 finish=lambda key:'roof_'+key if kind=='loft' else key
 box(finish('glass'),x,depth,(lo+hi)/2,w,.04,hi-lo)
 for sign in [-1,1]:box(finish('frame'),x+sign*(w/2-.025),depth+.06,(lo+hi)/2,.05,.07,hi-lo)
 for z in [lo,hi]:box(finish('frame'),x,depth+.06,z,w,.07,.05)
 for i in range(1,cols):box(finish('frame'),x-w/2+w*i/cols,depth+.075,(lo+hi)/2,.035,.08,hi-lo)
 for i in range(1,panerows):box(finish('frame'),x,depth+.075,lo+(hi-lo)*i/panerows,w,.08,.035)
 if trim:
  for sign in [-1,1]:box(finish('stone'),x+sign*(w/2+.065),.075,(lo+hi)/2,.13,.23,hi-lo+.14)
  for z in [lo-.08,hi+.08]:box(finish('stone'),x,.09,z,w+.28,.27,.14)
 openings.append({'x':x,'width':w,'low':lo,'high':hi,'columns':cols,'rows':panerows,'kind':kind,'depth':depth})
# Three historic storeys: one narrow bay, seven triple-light bays and three
# separate corner lights. Nine light columns per wide bay replace generic grids.
for level,(lo,hi)in enumerate(rows):
 for c in corner:window(px(c),length*24/1301,lo,hi,2,6 if level==0 else 4,'corner')
 window(px(singleton),length*32/1301,lo,hi,3,6 if level==0 else 4,'single')
 for c in triple_centres:
  for offset in [-35,0,35]:window(px(c+offset),length*29/1301,lo,hi,3,6 if level==0 else 4,'triple')
# Ground-floor layout distinguishes historic lights, central entrance, louvres,
# and the two broad contemporary glazed openings shown in the existing survey.
window(px(302),length*32/1301,.65,4.43,3,6,'ground-single')
for c in triple_centres[:3]:window(px(c),length*106/1301,.65,4.43,9,6,'ground-historic')
window(px(895),length*106/1301,.10,2.6,4,1,'ground-entry',trim=False)
window(px(895),length*106/1301,2.95,4.4,2,1,'ground-entry-transom')
window(px(1050),length*106/1301,.3,2.9,3,2,'ground-service',trim=False)
for z in [3.10+.085*i for i in range(15)]:box('frame',px(1050),.04,z,length*106/1301,.13,.035)
for c in triple_centres[5:]:window(px(c),length*106/1301,.28,4.4,3,3,'ground-modern')
# Corner entrance is a recessed glazed opening with paired plain stone columns.
window(px(183),length*92/1301,.05,4.15,3,1,'corner-entry',depth=-.22,trim=False)
for c in [145,214]:
 box('stone',px(c),.16,2.21,.28,.52,4.16)
 for z in [.28,4.15]:box('stone',px(c),.20,z,.55,.60,.20)
# Partition wall panels around the actual openings. No opaque slab behind glass.
body=[o for o in openings if o['kind'] not in ['ground-entry-transom']]
# Include every opening, including the entry's separate upper lights.
body=list(openings)
levels=sorted({-.26,17.37,*[o[k]for o in body for k in ['low','high']]})
for lo,hi in zip(levels,levels[1:]):
 active=sorted((o['x']-o['width']/2-.015,o['x']+o['width']/2+.015)for o in body if o['low']<(lo+hi)/2<o['high'])
 cursor=0
 for a,b in active+[(length,length)]:
  a=max(0,a);b=min(length,b)
  if a>cursor+1e-5:box('brick',(cursor+a)/2,-.21,(lo+hi)/2,a-cursor,.42,hi-lo)
  cursor=max(cursor,b)
# Pale banded spandrels and projecting caps between the three storeys.
for z,h in [(5.10,.32),(9.55,.28),(12.91,.28),(17.05,.24),(17.34,.22)]:box('stone',length/2,.07,z,length,.55,h)
for c in triple_centres:
 for z in [9.69,13.07]:box('stone',px(c),.12,z,length*110/1301,.36,.14)
 for z in [9.94,13.33]:
  # Small circular bosses are drawn above these oriel bands; diameters estimated.
  for off in [-35,0,35]:
   x=px(c+off);r=.105;vs=[point(x+r*math.cos(i*math.tau/24),.16,z+r*math.sin(i*math.tau/24))for i in range(24)]
   batch('stone').add(vs,[tuple(range(24))])
# Specific historic mansard rather than reviving the discarded uniform roof.
# Sloped tile fields are cut around eighteen vertical dormer openings.
loft=[]
for c in corner+loft_centres:
 x=px(c);w=length*(25 if c in corner else 30)/1301
 window(x,w,17.75,20.04,3,5,'loft',depth=.015)
 loft.append((x,w))
roof_lo,roof_hi=17.37,20.59
# Build sloping outer tile panels around each dormer, keeping clear glass voids.
def roof_face(a,b,lo,hi):
 if b-a<1e-5:return
 def p(x,z):return point(x,.1-1.35*(z-roof_lo)/(roof_hi-roof_lo),z)
 v=[p(a,lo),p(b,lo),p(b,hi),p(a,hi)]
 if (v[1]-v[0]).cross(v[3]-v[0]).dot(normal)<0:v.reverse()
 batch('roof').add(v,[(0,1,2,3)])
for lo,hi in [(roof_lo,17.75),(17.75,20.04),(20.04,roof_hi)]:
 cursor=0
 active=sorted((x-w/2-.14,x+w/2+.14)for x,w in loft)if lo==17.75 else []
 for a,b in active+[(length,length)]:
  a=max(0,a);b=min(length,b)
  roof_face(cursor,a,lo,hi);cursor=max(cursor,b)
# Closed dormer cheeks connect the projecting windows to the sloping tile face.
for x,w in loft:
 for sign in [-1,1]:
  edge=x+sign*(w/2+.14)
  batch('roof_stone').add([point(edge,.015,17.70),point(edge,-.05,17.70),point(edge,-1.07,20.11),point(edge,.015,20.11)],[(0,1,2,3)])
 box('roof_stone',x,.08,20.15,w+.38,.40,.15)
box('roof_stone',length/2,-1.20,20.57,length,.40,.16)
# Repeated X-pattern terrace rail shown above the main mansard.
rail_start=0;rail_end=px(355);count=round((rail_end-rail_start)/1.5);pitch=(rail_end-rail_start)/count
for i in range(count+1):box('roof_rail',rail_start+i*pitch,-1.2,21.0,.045,.045,.90)
for z in [20.68,21.35]:box('roof_rail',(rail_start+rail_end)/2,-1.2,z,rail_end-rail_start,.045,.045)
for i in range(count):
 a=rail_start+i*pitch;b=a+pitch
 for z0,z1 in [(20.70,21.33),(21.33,20.70)]:
  v=[point(a,-1.2,z0-.015),point(b,-1.2,z1-.015),point(b,-1.2,z1+.015),point(a,-1.2,z0+.015)]
  batch('roof_rail').add(v,[(0,1,2,3)])
added=[]
for g in batches.values():
 o=g.finish();added.append(o.name)
 for modifier in list(o.modifiers):o.modifiers.remove(modifier)
 if 'roof' in o.name:o['sharedInteriorRoof']=True
assert all(digest(bpy.data.objects[n])==h for n,h in before.items())
for name in ['room-studies.json','room-spaces.json','building-review.json']:shutil.copyfile(ROOT/'result/blender/stage109'/name,OUT/name)
assert json.loads((OUT/'catalogue-before.json').read_text())['version']=='109'
audit={'version':110,'baseline':109,'originalFingerprints':before,'originalVisibility':visibility,'clipped':clipped,'addedObjects':added,'origin':list(origin),'axis':list(axis),'normal':list(normal),'length':length,'openings':openings,'roofHeights':[roof_lo,roof_hi],'source':'data/collections/library-roof-2025/existing-nw-elevation.pdf','drawing':'4556-FBR-LR-ZZ-DR-A-114 P01, 17 April 2025','limits':['Street width registered proportionally to retained GIS; not surveyed coordinates','Unlabelled window edges and ornament dimensions estimated from rendered elevation','Brick/stone palette retained from project-era photography; not calibrated 2026 colour','Rounded northeast corner, other elevations and full interior levels remain unverified']}
(OUT/'portugal-frontage-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v110.blend'))
print('LIBRARY_PORTUGAL_FRONTAGE_SAVED',len(openings),len(clipped),flush=True)
