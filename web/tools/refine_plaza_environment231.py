"""Restore four photographed concrete tree containers at retained Watkins trees.

Fixed authoring script. The accepted230campus is read-only. Existing circular
0.69m tree-grate footprints register the four containers. Shapes and heights are
photographic estimates from official2022existing-condition audit, not a2026survey.
"""
from pathlib import Path
import sys,json,hashlib,math,collections
sys.dont_write_bytecode=True
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/plaza-environment231';DATA=ROOT/'data/collections/plaza-environment231'
BASE=ROOT/'result/blender/LSE_campus_detailed_v230.blend'
SHA='232793610db8d3ff488e7f10df9a4f96a239f7b870747777042b2332f242a0bf'
SOURCE='SITE_V47_Mapped_street_furniture';OWNER='03_PUBLIC_REALM'
RETAINED='SITE231_Mapped_furniture_without_Watkins_flat_grates'
STONE='SITE231_Watkins_four_concrete_tree_containers';SOIL='SITE231_Watkins_four_container_soil'
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import object_fingerprint,update_scene
from refine_portsmouth_exterior207 import material_fingerprint
from refine_ksw_exterior219 import modifier_state
from refine_streets230 import components,triangle_signatures,triangles,tree

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def state():
 spaces=json.loads((ROOT/'web/tools/building-metadata.json').read_text())['spaces']
 rooms={r['collection']:sorted(o.name for o in bpy.data.collections[r['collection']].all_objects)for r in spaces}
 return dict(objects={o.name:object_fingerprint(o)for o in bpy.data.objects},materials={m.name:material_fingerprint(m)for m in bpy.data.materials},owners={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects},modifiers={o.name:modifier_state(o)for o in bpy.data.objects},props={o.name:repr(sorted(o.items()))for o in bpy.data.objects},visibility={o.name:o.hide_render for o in bpy.data.objects},rooms=rooms)
def preserve(before):
 for n,v in before['objects'].items():assert object_fingerprint(bpy.data.objects[n])==v,n
 for n,v in before['materials'].items():assert material_fingerprint(bpy.data.materials[n])==v,n
 for n,v in before['owners'].items():assert sorted(c.name for c in bpy.data.objects[n].users_collection)==v,n
 for n,v in before['modifiers'].items():assert modifier_state(bpy.data.objects[n])==v,n
 for n,v in before['props'].items():assert repr(sorted(bpy.data.objects[n].items()))==v,n
 for n,v in before['visibility'].items():assert bpy.data.objects[n].hide_render==v,n
 for n,v in before['rooms'].items():assert sorted(o.name for o in bpy.data.collections[n].all_objects)==v,n
 assert sha(BASE)==SHA

def material(name,color):
 m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
 p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=m.diffuse_color;p.inputs['Roughness'].default_value=.9
 return m
class Batch:
 def __init__(self,name,mat):self.name=name;self.mat=mat;self.vertices=[];self.faces=[]
 def ring(self,xy,z0,z1,ro0,ro1,ri0,ri1):
  start=len(self.vertices);n=48
  for radius,z in [(ro0,z0),(ro1,z1),(ri0,z0),(ri1,z1)]:
   # Bottom perimeter lies exactly inside the original16-sided soil disc.
   radii=[radius*(math.cos(math.pi/16)/math.cos((k*math.tau/n)%(math.tau/16)-math.pi/16) if z==z0 and radius==ro0 else 1)for k in range(n)]
   self.vertices.extend((xy[0]+radii[k]*math.cos(k*math.tau/n),xy[1]+radii[k]*math.sin(k*math.tau/n),z)for k in range(n))
  for k in range(n):
   j=(k+1)%n
   self.faces.extend(tuple(start+i for i in f)for f in [(k,j,n+j,n+k),(2*n+j,2*n+k,3*n+k,3*n+j),(n+k,n+j,3*n+j,3*n+k),(j,k,2*n+k,2*n+j)])
 def soil(self,xy,z0,z1,r0,r1):
  start=len(self.vertices);n=48
  for radius,z in [(r0,z0),(r1,z1)]:self.vertices.extend((xy[0]+radius*math.cos(k*math.tau/n),xy[1]+radius*math.sin(k*math.tau/n),z)for k in range(n))
  self.faces.extend([tuple(start+k for k in range(n-1,-1,-1)),tuple(start+n+k for k in range(n))])
  for k in range(n):
   j=(k+1)%n;self.faces.append(tuple(start+i for i in [k,j,n+j,n+k]))
 def finish(self):
  m=bpy.data.meshes.new(self.name);m.from_pydata(self.vertices,[],self.faces);m.materials.append(self.mat);m.update()
  o=bpy.data.objects.new(self.name,m);bpy.data.collections[OWNER].objects.link(o)
  o['sourceReference']='Official2022PublicRealmStrategyPDF51,printed100–101,existingconditionphotos';o['dimensionsEstimated']=True;o['scope']='Four retained tree positions and original grate footprints; no new path or tree'
  return o

def solids(o):
 rows=[]
 for index,part in enumerate(components(o)):
  selected=set(part);bm=bmesh.new();m=o.data.copy();bm.from_mesh(m);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index not in selected],context='VERTS');bm.normal_update()
  assert all(e.is_manifold for e in bm.edges),(o.name,index)
  volume=bm.calc_volume(signed=True);assert volume>0,(o.name,index,volume)
  rows.append(dict(component=index,volumeM3=volume,closed=True));bm.free();bpy.data.meshes.remove(m)
 return rows

def render(source,owned):
 s=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=s
 c=bpy.data.objects.new('PLAZA231_REVIEW_CAMERA',bpy.data.cameras.new('PLAZA231_REVIEW_CAMERA'));s.collection.objects.link(c);s.camera=c;c.data.clip_end=600;c.data.sensor_fit='VERTICAL'
 s.render.engine='BLENDER_EEVEE';s.render.resolution_x=1100;s.render.resolution_y=825;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG'
 for o in s.objects:
  if o.hide_render:o.hide_set(True)
 active=sorted(o.name for o in s.objects if not o.hide_render and o.name not in [SOURCE,c.name]+[x.name for x in owned])
 views=[dict(name='watkins-plaza',position=[19,3.1,-14],target=[46,1.2,10],fov=61),dict(name='watkins-tree-containers',position=[25,2.4,-10],target=[28,.45,-2],fov=58)]
 cameras=[]
 for v in views:
  eye=Vector((v['position'][0],-v['position'][2],v['position'][1]));target=Vector((v['target'][0],-v['target'][2],v['target'][1]));c.location=eye;c.rotation_euler=(target-eye).to_track_quat('-Z','Y').to_euler();c.data.lens=c.data.sensor_height/(2*math.tan(math.radians(v['fov'])/2))
  for phase in ['before','after']:
   source.hide_render=phase=='after';source.hide_set(phase=='after')
   for o in owned:o.hide_render=phase=='before';o.hide_set(phase=='before')
   update_scene();s.render.filepath=str(OUT/(phase+'-'+v['name']+'.png'));bpy.ops.render.render(write_still=True)
  cameras.append(dict(view=v,allNativeBuildingsAndCrownsRetained=True))
 source.hide_render=False;source.hide_set(False)
 for o in owned:o.hide_render=False;o.hide_set(False)
 bpy.data.objects.remove(c,do_unlink=True);bpy.data.cameras.remove(bpy.data.cameras['PLAZA231_REVIEW_CAMERA'])
 return cameras,dict(activeContextObjects=len(active),activeContextNamesSha256=hashlib.sha256('\n'.join(active).encode()).hexdigest(),allAcceptedBuildingsAndCrownsRetained=True)

def build():
 OUT.mkdir(parents=True,exist_ok=True);DATA.mkdir(parents=True,exist_ok=True);assert sha(BASE)==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene();before=state();assert len(before['objects'])==8283
 assert len(before['rooms'])==31 and len(set().union(*(set(v)for v in before['rooms'].values())))==1273
 plan=json.loads((ROOT/'result/blender/stage47/street-plan.json').read_text());trees=[r for r in plan['objects']if r['kind']=='tree' and r['xy'][0]>0];assert len(trees)==4
 source=bpy.data.objects[SOURCE];assert sorted(c.name for c in source.users_collection)==[OWNER] and not source.hide_render
 groups=components(source);selected=set();selection=[]
 for r in trees:
  xy=r['xy'];parts=[]
  for p in groups:
   points=[source.matrix_world@source.data.vertices[i].co for i in p]
   if all(math.hypot(v.x-xy[0],v.y-xy[1])<.7001 and v.z<.051 for v in points):parts.append(p)
  assert len(parts)==20,(r,len(parts))
  selected.update(v for p in parts for v in p);selection.append(dict(**r,removedGrateComponents=len(parts)))
 retained=set(range(len(source.data.vertices)))-selected;expected=triangle_signatures(source,retained)
 clone=source.copy();clone.data=source.data.copy();clone.name=RETAINED;clone.data.name=RETAINED
 bm=bmesh.new();bm.from_mesh(clone.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.verts[i]for i in sorted(selected)],context='VERTS');bm.to_mesh(clone.data);bm.free();clone.data.update();bpy.data.collections[OWNER].objects.link(clone);assert triangle_signatures(clone)==expected
 stone=Batch(STONE,material('SITE231_pale_concrete',(.56,.57,.545)));soil=Batch(SOIL,material('SITE231_planter_soil',(.10,.085,.055)))
 # Active paved native surfaces support every outer-footprint sample. No datum sheet.
 s=bpy.context.scene;supports=[]
 paving=bpy.data.objects['SITE194_SITE_V47_John_Watkins_Plaza'];assert not paving.hide_render
 paving_tree=tree(triangles(paving))
 for r in trees:
  xy=r['xy'];heights=[]
  for k in range(48):
   a=k*math.tau/48;p=Vector((xy[0]+.69*math.cos(a),xy[1]+.69*math.sin(a),.15));hit=paving_tree.ray_cast(p,Vector((0,0,-1)),.2)
   assert hit[0] is not None,(r,k)
   assert .039< hit[0].z<.051;heights.append(hit[0].z)
  # Paving joints retain their genuine 10mm depth. Foundation starts at the
  # continuous original joint bed .04, meeting tiles without floating.
  bottom=.04;top=.65;soil_top=.59;inner_top=.46;inner_bottom=.55
  radius_soil=inner_bottom+(inner_top-inner_bottom)*(soil_top-bottom)/(top-bottom)
  stone.ring(xy,bottom,top,.69,.57,inner_bottom,inner_top);soil.soil(xy,bottom,soil_top,inner_bottom,radius_soil)
  supports.append(dict(xy=xy,nativeRimSamples=heights,bottom=bottom,top=top,soilTop=soil_top,foundation='Meets active original joint bedZ0.04,intersects retained slab edges by at most0.01m as a normal above-paving container footing',footprintRadius=.69,maximumNewFootprintOutsideExistingGrateM2=0))
 stone_obj=stone.finish();soil_obj=soil.finish();owned=[clone,stone_obj,soil_obj];update_scene()
 for o in [stone_obj,soil_obj]:
  for v in o.data.vertices:
   xy=min((r['xy']for r in trees),key=lambda c:math.hypot(v.co.x-c[0],v.co.y-c[1]));dx=v.co.x-xy[0];dy=v.co.y-xy[1];angle=math.atan2(dy,dx)%math.tau
   limit=.69*math.cos(math.pi/16)/math.cos(angle%(math.tau/16)-math.pi/16)
   assert math.hypot(dx,dy)<=limit+4e-6
 solid_report={o.name:solids(o)for o in [stone_obj,soil_obj]}
 # Furniture intersection tests use actual triangles. Trunk/soil rooting and
 # 10mmfooting contact with retained pavers are intentional and excluded.
 collision=[]
 for target in ['SITE174_John_Watkins_Plaza_picnic_seating','SITE230_Slatted_benches_retained_six',RETAINED]:
  hits=tree(triangles(stone_obj)).overlap(tree(triangles(bpy.data.objects[target])));assert not hits,(target,len(hits));collision.append(dict(object=target,stoneTriangleIntersections=0))
 bindings={o.name:[m.name for m in o.data.materials]for o in owned};fingerprints={o.name:object_fingerprint(o)for o in owned};preserve(before)
 component=OUT/'component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True);component_sha=sha(component)
 bpy.ops.wm.open_mainfile(filepath=str(component));assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items());assert triangle_signatures(bpy.data.objects[RETAINED])==expected
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
 with bpy.data.libraries.load(str(component),link=False)as(_,dst):dst.objects=list(fingerprints)
 owned=dst.objects
 for o in owned:
  for i,n in enumerate(bindings[o.name]):
   if n in before['materials']:o.data.materials[i]=bpy.data.materials[n]
  bpy.data.collections[OWNER].objects.link(o)
 update_scene();assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items());preserve(before)
 cameras,visibility=render(bpy.data.objects[SOURCE],owned);preserve(before)
 refs=[dict(path='data/collections/streets/raw/public_realm_strategy_2022.pdf',sha256=sha(ROOT/'data/collections/streets/raw/public_realm_strategy_2022.pdf'),url='https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/2022-LSE-Public-Realm-Strategy.pdf',pageOneBased=51,printedPages=[100,101],status='Existing-condition audit and real photographs,not proposed design; capture date unknown',supports='Explicit4trees in concreteplanters and photo01showing pale truncated-cone container'),dict(path='data/collections/plaza-environment231/official-strategy-existing-watkins.png',sha256=sha(DATA/'official-strategy-existing-watkins.png'),parent='officialPDF51',privateEvidenceOnly=True),dict(path='result/blender/stage47/street-plan.json',sha256=sha(ROOT/'result/blender/stage47/street-plan.json'),supports='Existing four native tree-grate centres and0.69m footprint registration; not a measured2026inventory')]
 write(DATA/'sources.json',dict(version=231,sources=refs,noSourcePhotoPixelsReused=True,limitations='No claim that2022audit photographs establishOctober2026condition. All planter heights/radii except retained0.69mgrate boundary are estimates. No additional trees,foliage,wall,stairs,ramp or furniture.'))
 write(OUT/'support-and-solid-proof.json',dict(supports=supports,solids=solid_report,collisions=collision,rootContact='Existing trunks pass through soil,as intentional planting; no trunk/crown changed',pathPolicy='All new XYgeometry lies inside existing four tree-grate footprints; original walking surface retained',selectedSource=selection))
 write(OUT/'audit.json',dict(version=231,baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=component_sha,targetCollection=OWNER,destinationCollection=OWNER,addedObjects=list(fingerprints),archivedObjects=[SOURCE],changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,sourceManifest='data/collections/plaza-environment231/sources.json',originalObject=SOURCE,retainedFixtureTriangles=sum(expected.values()),verification=dict(componentReopened=True,appendedComponentReopened=True,originalGeometryUVsTransformsBindingsNodesModifiersPropsOwnersAndVisibilityPreserved=True,originalObjectsVerified=len(before['objects']),originalMaterialsVerified=len(before['materials']),protectedSpacesVerified=len(before['rooms']),protectedRoomObjectsVerified=1273,retainedFixtureTrianglesExact=True,closedPositiveVolumeNewSolids=8,noPathChange=True,noNewFootprintBeyondExistingGrates=True,noFullNativeSaved=True),records=[dict(name=o.name,vertices=len(o.data.vertices),faces=len(o.data.polygons),triangles=len(triangles(o)))for o in owned],sourcePhotograph='Official2022existingconditionauditPDF51,printed100–101',sourceDate='unknown; publication2022',previews=[phase+'-'+r['view']['name']+'.png'for r in cameras for phase in ['before','after']],cameras=cameras,productionVisibility=visibility,scope='Replace four unsupported flush iron tree-grates with photographed pale concrete truncated-cone tree containers at same four registered trees,within original footprints. Retain unrelated mapped furniture exactly.',limitations=['Container height0.61m,top outerradius0.57m,inner taper and soilheight are photographic estimates,not site measurements.','Paving atZ0.04–0.05 retained; 10mmfooting/slab meeting is normal support,not furniture collision.','No current2026inventory or historical low-wall reconstruction claimed.']))
 assert sha(BASE)==SHA and sha(component)==component_sha
 print('PLAZA231_COMPLETE',component_sha,len(before['materials']),flush=True)
if __name__=='__main__':build()
