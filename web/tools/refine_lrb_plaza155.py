"""Replace only the mapped Plaza Café context block with a photo-based pavilion.

Open in Blender. The existing OSM footprint is retained. Heights, joinery and
furniture are photographic estimates; this is not a measured café interior.
"""
from pathlib import Path
import array,ast,hashlib,json,math,sys
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/lrb_plaza155';OUT.mkdir(parents=True,exist_ok=True)
WEB=ROOT/'result/web/lrb_plaza155';WEB.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v154.blend'
COMP=OUT/'lrb-plaza155-component.blend'
PREFIX='LRB_NEXT_PLAZA155_'
bpy.ops.wm.open_mainfile(filepath=str(BASE))
scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
for layer in scene.view_layers:layer.update()
assert hashlib.sha256(BASE.read_bytes()).hexdigest()=='2dbec0ee001ba3347de9de9ee50ed9e974401e301f4d4159a65b84b5c771f02c'
def fingerprint(obj):
 h=hashlib.sha256(str([list(row)for row in obj.matrix_world]).encode())
 if obj.type=='MESH':
  for data,field,kind,count in ((obj.data.vertices,'co','f',3),(obj.data.loops,'vertex_index','i',1),(obj.data.polygons,'material_index','i',1)):
   values=array.array(kind,[0])*(len(data)*count);data.foreach_get(field,values);h.update(values.tobytes())
  for layer in obj.data.uv_layers:
   values=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);h.update(values.tobytes())
 h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode());return h.hexdigest()
originals={o.name:fingerprint(o)for o in bpy.data.objects}
visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()]for o in bpy.data.objects}
site=json.loads((ROOT/'result/blender/site_geometry.json').read_text())
record=next(b for b in site['context']if b['id']=='way/310159572') if 'context' in site else None
if record is None:
 for key,value in site.items():
  if isinstance(value,list):
   record=next((b for b in value if isinstance(b,dict)and b.get('id')=='way/310159572'),None)
   if record:break
assert record and record['properties']['name']=='Plaza Café'
ring=[Vector((*xy,0))for xy in record['rings'][0]]
archives=[o.name for o in scene.objects if o.name.startswith('Context_way/310159572_')]
assert archives and all('310159572' in n for n in archives)
sourceObjects=[{'name':name,'fingerprint':originals[name],'vertexCount':len(bpy.data.objects[name].data.vertices),'bounds':[list(bpy.data.objects[name].matrix_world@Vector(v))for v in bpy.data.objects[name].bound_box]}for name in archives]
# Extract the production export functions into a private namespace, without
# executing its public-write top-level code or changing the exporter.
export_tree=ast.parse((ROOT/'web/tools/export_scene.py').read_text())
functions=[node for node in export_tree.body if isinstance(node,ast.FunctionDef)]
exporter={'bpy':bpy,'bmesh':__import__('bmesh'),'Vector':Vector,'hashlib':hashlib,'json':json,'struct':__import__('struct'),'OUTPUT':WEB,'material_cache':{},'full_detail':True}
exec(compile(ast.Module(body=functions,type_ignores=[]),'private-production-export','exec'),exporter)
def export_review(name):
 bpy.context.window.scene=scene
 bpy.context.view_layer.update();exporter['depsgraph']=bpy.context.evaluated_depsgraph_get();exporter['material_cache']={}
 objects=list(bpy.data.collections['LRB_EXTERIOR'].all_objects)+list(bpy.data.collections['LRB_PUBLIC_INTERIOR_study'].all_objects)+[bpy.data.objects[n]for n in archives]
 review=bpy.data.scenes.new('LRB_PLAZA155_PRIVATE_REVIEW_'+name)
 exporter['clone_group'](objects,'LRB',review,hide_basement=True)
 exporter['export_scene'](review,name+'.glb')
 for obj in list(review.objects):bpy.data.objects.remove(obj,do_unlink=True)
 bpy.data.scenes.remove(review);bpy.context.window.scene=scene
if not (WEB/'before.glb').exists():
 export_review('before')
 # glTF review evaluation can update source scene matrices in memory. Reload
 # the authoritative file before constructing/fingerprinting the component.
 bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
 for layer in scene.view_layers:layer.update()
 originals={o.name:fingerprint(o)for o in bpy.data.objects}
 visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()]for o in bpy.data.objects}
col=bpy.data.collections.new('LRB_PLAZA_EXTERIOR');bpy.data.collections['LRB_EXTERIOR'].children.link(col)
col['sourceFootprint']='OpenStreetMap way/310159572,2025-05-15';col['venue']='Plaza Café'
sys.path.insert(0,str(ROOT/'web/tools'));from facade_geometry import Geometry,materials
materials.clear()
def material(key,rgb,roughness=.6,metallic=0,transmission=0):
 mat=bpy.data.materials.new(PREFIX+key);mat.use_nodes=True;mat.diffuse_color=(*rgb,1)
 node=mat.node_tree.nodes.get('Principled BSDF');node.inputs['Base Color'].default_value=mat.diffuse_color;node.inputs['Roughness'].default_value=roughness;node.inputs['Metallic'].default_value=metallic;node.inputs['Transmission Weight'].default_value=transmission
 if transmission:mat['webOpacity']=.3
 materials[key]=mat
material('steel',(.035,.047,.043),.48,.32)
material('glass',(.36,.43,.425),.14,0,.85)
material('timber',(.24,.115,.053),.78)
material('stone',(.36,.35,.315),.88)
material('roof',(.075,.088,.077),.9)
material('greenroof',(.16,.20,.083),.98)
material('oak',(.63,.35,.08),.58)
material('silver',(.42,.45,.44),.28,.8)
batches={key:Geometry('LRB',PREFIX+key,key)for key in materials}
def box(key,center,size,angle=0):batches[key].box(center,size,angle)
def beam(key,a,b,width,height):
 a,b=Vector(a),Vector(b);box(key,(a+b)/2,((b-a).length,width,height),math.atan2(b.y-a.y,b.x-a.x))
# The two photographed public sides have a deep projecting timber soffit.
# Retain the exact wall footprint; only these roof edges project an estimated.65m.
signedArea=sum(a.x*b.y-b.x*a.y for a,b in zip(ring,ring[1:]+ring[:1]))
def cross2(a,b):return a.x*b.y-a.y*b.x
roofRing=[]
for index,vertex in enumerate(ring):
 previous=(index-1)%len(ring);before=vertex-ring[previous];after=ring[(index+1)%len(ring)]-vertex
 normalBefore=Vector((-before.y,before.x,0)).normalized();normalAfter=Vector((-after.y,after.x,0)).normalized()
 if signedArea>0:normalBefore=-normalBefore;normalAfter=-normalAfter
 first=vertex+normalBefore*(.65 if previous in [0,8] else 0);second=vertex+normalAfter*(.65 if index in [0,8] else 0)
 roofRing.append(first+before*(cross2(second-first,after)/cross2(before,after)))
def polygon_slab(key,bottom,top,outline=None):
 outline=outline or ring
 count=len(outline);verts=[(*v.xy,z)for z in [bottom,top]for v in outline]
 faces=[tuple(range(count-1,-1,-1)),tuple(range(count,count*2))]+[(i,(i+1)%count,(i+1)%count+count,i+count)for i in range(count)]
 batches[key].add(verts,faces)
polygon_slab('stone',.04,.12)
polygon_slab('roof',3.27,3.42,roofRing)
polygon_slab('greenroof',3.42,3.49,roofRing)
# Full-height glass on the mapped pavilion perimeter. Continuous dark frame and
# high clerestory follow both official café photographs; no enclosing back wall.
for edge,(a,b)in enumerate(zip(ring,ring[1:]+ring[:1])):
 direction=(b-a).normalized();span=(b-a).length;count=max(1,round(span/1.5));angle=math.atan2(direction.y,direction.x)
 for k in range(count):
  lo=span*k/count;hi=span*(k+1)/count;center=a+direction*((lo+hi)/2)
  box('glass',center+Vector((0,0,1.505)),(hi-lo-.085,.034,2.73),angle)
  box('glass',center+Vector((0,0,3.025)),(hi-lo-.085,.034,.265),angle)
 for k in range(count+1):
  center=a+direction*(span*k/count)
  box('steel',center+Vector((0,0,1.675)),(.075,.09,3.11),angle)
 for z,t in [(.155,.07),(2.91,.12),(3.235,.09)]:beam('steel',a+Vector((0,0,z)),b+Vector((0,0,z)),.13,t)
 beam('silver',roofRing[edge]+Vector((0,0,3.415)),roofRing[(edge+1)%len(ring)]+Vector((0,0,3.415)),.09,.09)
# The photo at the narrow end shows a single central glazed entrance. Its
# width and location are estimated from the mapped 4.4m end wall.
a,b=ring[:2];direction=(b-a).normalized();middle=(a+b)/2;angle=math.atan2(direction.y,direction.x)
for offset in [-.56,.56]:box('steel',middle+direction*offset+Vector((0,0,1.39)),(.055,.13,2.55),angle)
beam('steel',middle-direction*.59+Vector((0,0,2.675)),middle+direction*.59+Vector((0,0,2.675)),.14,.065)
box('silver',middle+direction*.36+Vector((0,0,1.08)),(.026,.08,.24),angle)
# Wood strips occupy the actual pavilion footprint, with a few photograph-
# supported steel ceiling cross-members. Furniture represents only visible
# architectural scale, not a complete or surveyed seating plan.
def inside(point,outline=None):
 outline=outline or ring
 x,y=point;result=False
 for a,b in zip(outline,outline[1:]+outline[:1]):
  if (a.y>y)!=(b.y>y) and x<(b.x-a.x)*(y-a.y)/(b.y-a.y)+a.x:result=not result
 return result
roof_u=(ring[-1]-ring[0]).normalized();roof_v=Vector((-roof_u.y,roof_u.x,0));anchor=ring[0]
local=[((v-anchor).dot(roof_u),(v-anchor).dot(roof_v))for v in roofRing]
minx,maxx=min(v[0]for v in local),max(v[0]for v in local);miny,maxy=min(v[1]for v in local),max(v[1]for v in local)
for index in range(math.ceil((maxy-miny)/.16)):
 y=miny+index*.16+.08;segments=[]
 for k in range(math.ceil((maxx-minx)/.14)):
  x=minx+k*.14+.07;world=anchor+roof_u*x+roof_v*y
  if inside(world.xy,roofRing):segments.append(x)
 if segments:
  left,right=min(segments)-.07,max(segments)+.07
  beam('timber',anchor+roof_u*left+roof_v*y+Vector((0,0,3.24)),anchor+roof_u*right+roof_v*y+Vector((0,0,3.24)),.115,.045)
for x in [3.0,7.5,12.,16.5]:
 points=[anchor+roof_u*x+roof_v*y for y in [miny+.16,maxy-.16]]
 if all(inside(p.xy)for p in points):beam('steel',points[0]+Vector((0,0,3.13)),points[1]+Vector((0,0,3.13)),.12,.13)
# Round oak café tables and simple bent-metal chair forms visible in the official
# photo. Restrict them to a shallow row inside the long glazed front.
def disc(key,center,radius,height):
 steps=20;verts=[(center[0]+radius*math.cos(k*2*math.pi/steps),center[1]+radius*math.sin(k*2*math.pi/steps),center[2]+z)for z in [-height/2,height/2]for k in range(steps)]
 faces=[tuple(range(steps-1,-1,-1)),tuple(range(steps,steps*2))]+[(k,(k+1)%steps,(k+1)%steps+steps,k+steps)for k in range(steps)]
 batches[key].add(verts,faces)
furniture=[]
for x in [3.,6.3,9.6,12.9,16.2]:
 center=anchor+roof_u*x+roof_v*1.1
 if not inside(center.xy):continue
 disc('oak',center+Vector((0,0,.86)),.38,.045);disc('silver',center+Vector((0,0,.15)),.23,.035);box('silver',center+Vector((0,0,.49)),(.065,.065,.66));furniture.append(list(center))
 for offset in [-.62,.62]:
  chair=center+roof_u*offset
  if not inside(chair.xy):continue
  box('oak',chair+Vector((0,0,.56)),(.41,.41,.035),math.atan2(roof_u.y,roof_u.x))
  box('oak',chair+roof_v*.18+Vector((0,0,.755)),(.40,.035,.38),math.atan2(roof_u.y,roof_u.x))
  for dx in [-.16,.16]:
   for dy in [-.16,.16]:box('silver',chair+roof_u*dx+roof_v*dy+Vector((0,0,.335)),(.018,.018,.42))
owned=[]
for key,batch in batches.items():
 obj=batch.finish();obj.name=PREFIX+key;obj.data.name=obj.name;obj.modifiers.clear()
 for owner in list(obj.users_collection):owner.objects.unlink(obj)
 col.objects.link(obj);obj['sourceFootprint']=record['id'];obj['scope']='Plaza Café visible pavilion, metric footprint; heights and detailing estimated';owned.append(obj)
for name in archives:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
for layer in scene.view_layers:layer.update()
assert all(fingerprint(bpy.data.objects[name])==value for name,value in originals.items()),[name for name,value in originals.items()if fingerprint(bpy.data.objects[name])!=value]
assert all([bpy.data.objects[name].hide_render,bpy.data.objects[name].hide_viewport,bpy.data.objects[name].hide_get()]==value for name,value in visibility.items()if name not in archives)
bpy.data.libraries.write(str(COMP),set(owned),fake_user=True)
sources=[]
for path,url,support in [
 ('data/collections/campus_photos_round2/images/LRB/LRB_food_head-to-plaza-cafe_01.jpg','https://food.lse.ac.uk/story/35941950/head-to-plaza-cafe','2024-08-07 publication; photo capture unknown; narrow glazed end door, timber slats, ceiling frame, round tables and oak chairs'),
 ('data/collections/campus_photos_round2/images/LRB/LRB_food_outlets_09.jpg','https://food.lse.ac.uk/outlets','Official café front photograph; capture unknown; dark frame, glass walls, clerestory and eaves'),
 ('data/collections/streets/derived/review_public_realm_pdf_page75.png','https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/2022-LSE-Public-Realm-Strategy.pdf','2021 photograph within 2022 report, PDF75; pavilion at end of plaza; proposed future interventions excluded'),
 ('data/collections/streets/raw/osm_map.osm','https://www.openstreetmap.org/way/310159572','2025-05-15 footprint and explicit Plaza Café name, single storey, black colour, flat roof'),
]:
 f=ROOT/path;sources.append({'path':path,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'url':url,'supports':support})
audit={'baseline':str(BASE.relative_to(ROOT)),'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'ownedObjects':[o.name for o in owned],'archivedObjects':archives,'originalFingerprints':originals,'originalVisibility':visibility,'sourceObjects':sourceObjects,'originalObjectCount':len(originals),'sourceFootprint':record,'estimatedRoofOutline':[list(v.xy)for v in roofRing],'sources':sources,'liveCrossCheck':{'date':'2026-10-04','urls':['https://info.lse.ac.uk/current-students/estates-division/facilities-guide/social-and-green-space','https://info.lse.ac.uk/current-students/estates-division/facilities-guide/food-and-drink'],'supports':'Official pages continue to identify a free-standing Plaza Café with green roof on John Watkins Plaza'},'changes':['Replace exact mapped café context walls and roof with one-storey black steel/glass pavilion','Retain mapped footprint; correct generic5m height to estimated3.49m green-roof top','Timber ceiling strips, clerestory, narrow-end glazed door, shallow photographed café furniture provide real pavilion depth'],'estimatedDimensions':{'eaves':3.27,'roofTop':3.49,'glassBottom':.12,'clerestoryBottom':2.97,'panePitchApprox':1.5,'doorWidth':1.12,'timberPitch':.16,'publicSideRoofProjection':.65,'tableCenters':furniture},'collection':'LRB_PLAZA_EXTERIOR child of LRB_EXTERIOR','limits':['Pavilion dimensions from OSM footprint; façade/roof heights and pane counts remain photograph estimates, not a site survey','Exact current doors, furnishings and counter arrangement unverified; only shallow photographed furniture is approximated','Green roof confirmed by current official page; species, surface texture and depth unverified','LRB entrance, other facades, library interior and roof untouched; surrounding context retained','Glass transmission belongs only to new physically open pavilion; no surrounding shells removed']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
# Reopen the independent component into the exact authoritative source.
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
with bpy.data.libraries.load(str(COMP),link=False)as(src,dst):dst.objects=src.objects
col=bpy.data.collections.new('LRB_PLAZA_EXTERIOR');bpy.data.collections['LRB_EXTERIOR'].children.link(col)
for obj in dst.objects:col.objects.link(obj)
for name in archives:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
for layer in scene.view_layers:layer.update()
assert all(fingerprint(bpy.data.objects[name])==value for name,value in originals.items()),[name for name,value in originals.items()if fingerprint(bpy.data.objects[name])!=value]
assert all([bpy.data.objects[name].hide_render,bpy.data.objects[name].hide_viewport,bpy.data.objects[name].hide_get()]==value for name,value in visibility.items()if name not in archives)
export_review('after')
verification={'componentSha256':hashlib.sha256(COMP.read_bytes()).hexdigest(),'savedComponentReopened':True,'originalGeometryPreserved':True,'unrelatedVisibilityPreserved':True,'originalObjectCount':len(originals),'fullModelSaved':False,'ownedObjectCount':len(owned),'archivedObjectCount':len(archives),'privateWebAssets':['result/web/lrb_plaza155/before.glb','result/web/lrb_plaza155/after.glb'],'candidateAcceptance':'Pending production-render visual comparison'}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
print('LRB_PLAZA155_COMPONENT',verification,flush=True);bpy.ops.wm.quit_blender()
